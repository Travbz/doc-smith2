"""Event bus for agent and workflow communication."""
from typing import Dict, List, Callable, Any, Optional
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from core.services.logging.logging_service import setup_logger

logger = setup_logger(__name__)

@dataclass
class Event:
    """Represents a system event."""
    type: str
    source: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    id: Optional[str] = None

    def __getitem__(self, key):
        """Allow dictionary-like access to data field."""
        return self.data[key]

    def get(self, key, default=None):
        """Allow dictionary-like get access to data field."""
        return self.data.get(key, default)

class EventBus:
    """Central event bus for system-wide communication."""
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.event_history: List[Event] = []
        self._queue = asyncio.Queue()
        self._running = False
        self._task = None
        
    async def start(self):
        """Start processing events."""
        logger.info("Starting event bus")
        self._running = True
        self._task = asyncio.create_task(self._process_events())
        
    async def stop(self):
        """Stop processing events."""
        logger.info("Stopping event bus")
        self._running = False
        if self._task:
            try:
                await self._queue.join()
                self._task.cancel()
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Event bus stopped")
        
    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        if not isinstance(event, Event):
            event = Event(**event if isinstance(event, dict) else {"type": str(event), "source": "unknown", "data": {}})
            
        logger.debug(f"Publishing event: {event.type} from {event.source}")
        self.event_history.append(event)
        await self._queue.put(event)
        
    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Subscribe to events of a specific type."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        if callback not in self.subscribers[event_type]:
            self.subscribers[event_type].append(callback)
            logger.debug(f"Added subscriber for {event_type}")
        
    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """Unsubscribe from events of a specific type."""
        if event_type in self.subscribers and callback in self.subscribers[event_type]:
            self.subscribers[event_type].remove(callback)
            logger.debug(f"Removed subscriber for {event_type}")
            
    async def _process_events(self) -> None:
        """Process events from the queue."""
        while self._running:
            try:
                event = await self._queue.get()
                if event.type in self.subscribers:
                    subscribers = self.subscribers[event.type].copy()  # Create a copy to avoid modification during iteration
                    for callback in subscribers:
                        try:
                            await callback(event)
                        except Exception as e:
                            logger.error(f"Error in event handler: {str(e)}", exc_info=True)
                            
                self._queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event: {str(e)}", exc_info=True)
                continue

    def get_event_history(self) -> List[Event]:
        """Get the history of processed events."""
        return self.event_history.copy()

    def clear_history(self) -> None:
        """Clear the event history."""
        self.event_history.clear()

# Create singleton instance
event_bus = EventBus()