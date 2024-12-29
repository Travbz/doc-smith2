"""Task queue manager for handling concurrent operations."""
from typing import Dict, Any, Optional, List
import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from core.services.logging.logging_service import setup_logger
from core.services.events.event_bus import event_bus, Event

logger = setup_logger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Task:
    """Represents a system task."""
    id: str
    type: str
    priority: int
    data: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = datetime.now()
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

class QueueManager:
    """Manages task queues and execution."""
    
    def __init__(self, max_concurrent_tasks: int = 5):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.tasks: Dict[str, Task] = {}
        self.queue = asyncio.PriorityQueue()
        self.running_tasks: List[str] = []
        self._running = False
        
    async def start(self):
        """Start processing tasks."""
        self._running = True
        asyncio.create_task(self._process_tasks())
        
    async def stop(self):
        """Stop processing tasks."""
        self._running = False
        await self.queue.join()
        
    async def enqueue_task(self, task: Task):
        """Add a task to the queue."""
        logger.debug(f"Enqueueing task: {task.id} of type {task.type}")
        self.tasks[task.id] = task
        await self.queue.put((task.priority, task.id))
        await event_bus.publish(Event(
            type="task_queued",
            source="queue_manager",
            data={"task_id": task.id}
        ))
        
    async def get_task_status(self, task_id: str) -> Optional[Task]:
        """Get the status of a task."""
        return self.tasks.get(task_id)
        
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                await event_bus.publish(Event(
                    type="task_cancelled",
                    source="queue_manager",
                    data={"task_id": task_id}
                ))
                return True
        return False
        
    async def _process_tasks(self):
        """Process tasks from the queue."""
        while self._running:
            if len(self.running_tasks) >= self.max_concurrent_tasks:
                await asyncio.sleep(0.1)
                continue
                
            try:
                _, task_id = await self.queue.get()
                task = self.tasks[task_id]
                
                if task.status == TaskStatus.CANCELLED:
                    self.queue.task_done()
                    continue
                    
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()
                self.running_tasks.append(task_id)
                
                await event_bus.publish(Event(
                    type="task_started",
                    source="queue_manager",
                    data={"task_id": task_id}
                ))
                
                # Execute task (this will be implemented by the task handler)
                try:
                    result = await self._execute_task(task)
                    task.status = TaskStatus.COMPLETED
                    await event_bus.publish(Event(
                        type="task_completed",
                        source="queue_manager",
                        data={"task_id": task_id, "result": result}
                    ))
                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    await event_bus.publish(Event(
                        type="task_failed",
                        source="queue_manager",
                        data={"task_id": task_id, "error": str(e)}
                    ))
                
                task.completed_at = datetime.now()
                self.running_tasks.remove(task_id)
                self.queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing task: {str(e)}")
                
    async def _execute_task(self, task: Task) -> Dict[str, Any]:
        """Execute a task. This should be overridden by the task handler."""
        raise NotImplementedError

# Create singleton instance
queue_manager = QueueManager()