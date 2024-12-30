"""Base agent class with common functionality."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
import asyncio

from core.services.logging import setup_logger
from core.services.event_bus import event_bus
from core.services.error_handling.error_handler import (
    with_error_handling,
    ErrorCategory,
    ErrorSeverity,
    DocSmithError
)

logger = setup_logger(__name__)

class BaseAgent(ABC):
    """Base agent class with common functionality."""

    def __init__(self, agency, agent_type: str):
        """Initialize base agent.
        
        Args:
            agency: Parent agency instance
            agent_type: Type of agent (e.g. 'documentation', 'review', 'github')
        """
        self.agency = agency
        self.agent_type = agent_type
        self._tools: Dict[str, Any] = {}
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._initialized = False
        self._event_handlers: Dict[str, Callable] = {}

    @property
    def is_initialized(self) -> bool:
        """Check if agent is initialized."""
        return self._initialized

    def get_tool(self, tool_name: str) -> Optional[Any]:
        """Get a tool by name."""
        return self._tools.get(tool_name)

    async def initialize(self) -> None:
        """Initialize the agent."""
        if self._initialized:
            logger.warning(f"{self.agent_type} agent already initialized")
            return
            
        try:
            logger.info(f"Initializing {self.agent_type} agent")
            await self._initialize_tools()
            await self._subscribe_to_events()
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Error initializing {self.agent_type} agent: {str(e)}")
            raise

    @abstractmethod
    async def _initialize_tools(self) -> None:
        """Initialize agent-specific tools."""
        pass

    async def _subscribe_to_events(self) -> None:
        """Subscribe to events.
        
        Should be overridden by agents that need to handle events.
        """
        pass

    async def cleanup(self) -> None:
        """Cleanup agent resources.
        
        Can be overridden by agents that need custom cleanup logic.
        """
        try:
            logger.info(f"Cleaning up {self.agent_type} agent")
            
            # Cancel any active tasks
            for task_id, task in self._active_tasks.items():
                if not task.done():
                    logger.debug(f"Cancelling task {task_id}")
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            self._active_tasks.clear()
            self._initialized = False
            
        except Exception as e:
            logger.error(f"Error during {self.agent_type} agent cleanup: {str(e)}")
            raise

    @with_error_handling(ErrorCategory.SYSTEM, ErrorSeverity.HIGH)
    async def execute_task(self, task_id: str, coroutine) -> Any:
        """Execute a task and track it.
        
        Args:
            task_id: Unique identifier for the task
            coroutine: Coroutine to execute
            
        Returns:
            Result of the task execution
        """
        if not self._initialized:
            raise RuntimeError(f"{self.agent_type} agent not initialized")
            
        try:
            task = asyncio.create_task(coroutine)
            self._active_tasks[task_id] = task
            try:
                result = await task
                return result
            except Exception as e:
                logger.error(f"Error executing task {task_id}: {str(e)}")
                raise
            
        finally:
            if task_id in self._active_tasks:
                del self._active_tasks[task_id]

    async def _publish_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish an event to the event bus."""
        from core.services.event_bus import Event
        await event_bus.publish(Event(
            type=event_type,
            source=self.agent_type,
            data=data
        ))

    async def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """Register an event handler.
        
        Args:
            event_type: Type of event to handle
            handler: Async function to handle the event
        """
        logger.info(f"Registering handler {handler.__qualname__} for event {event_type}")
        self._event_handlers[event_type] = handler
        event_bus.subscribe(event_type, handler)
