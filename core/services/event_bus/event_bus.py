"""Event bus for inter-agent communication."""
from typing import Dict, List, Callable, Any, Optional
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from core.services.logging.logging_service import setup_logger

logger = setup_logger(__name__)

@dataclass
class Event:
    """Event data structure."""
    type: str
    source: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class EventBus:
    """Event bus for handling inter-agent communication."""
    
    def __init__(self):
        """Initialize event bus."""
        self._subscribers: Dict[str, List[Callable]] = {}
        self._running = False
        self._queue: asyncio.Queue = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the event bus."""
        if self._running:
            return
            
        self._running = True
        self._task = asyncio.create_task(self._process_events())
        logger.info("Event bus started")
        
    async def stop(self):
        """Stop the event bus."""
        if not self._running:
            return
            
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Event bus stopped")
        
    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.info(f"Subscribed to {event_type} with callback {callback.__qualname__}")
        return callback  # Return the callback for chaining
        
    def unsubscribe(self, event_type: str, callback: Callable):
        """Unsubscribe from an event type."""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(callback)
            if not self._subscribers[event_type]:
                del self._subscribers[event_type]
            logger.info(f"Unsubscribed from {event_type} with callback {callback.__qualname__}")
        
    async def publish(self, event: Event):
        """Publish an event."""
        await self._queue.put(event)
        logger.info(f"Published event: {event.type} from {event.source} with data: {event.data}")
        
    async def _process_events(self):
        """Process events from the queue."""
        while self._running:
            try:
                event = await self._queue.get()
                subscribers = self._subscribers.get(event.type, [])
                logger.info(f"Processing event: {event.type} with {len(subscribers)} subscribers")
                
                for callback in subscribers:
                    try:
                        logger.info(f"Calling handler {callback.__qualname__} for event {event.type}")
                        await callback(event.data)
                    except Exception as e:
                        logger.error(f"Error in event handler {callback.__qualname__} for event {event.type}: {str(e)}")
                        
                self._queue.task_done()
                logger.info(f"Finished processing event: {event.type}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event: {str(e)}")
                
        logger.info("Event processing stopped")

# Create singleton instance
event_bus = EventBus()