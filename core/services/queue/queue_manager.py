"""Task queue manager with priority support, rate limiting, and error handling."""
from typing import Dict, Any, Optional, List, Callable, Union, TypeVar
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
from core.services.logging.logging_service import setup_logger
from core.services.event_bus.event_bus import event_bus, Event
from core.services.rate_limiting.rate_limiter import rate_limiter
from core.services.error_handling.error_handler import (
    with_error_handling,
    ErrorCategory,
    ErrorSeverity,
    error_handler,
    DocSmithError,
    QueueProcessingError,
    RateLimitError
)

logger = setup_logger(__name__)

T = TypeVar('T')

class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4

class TaskStatus(Enum):
    """Possible task states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"

@dataclass
class TaskResult:
    """Result of a task execution."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@dataclass
class TaskMetrics:
    """Metrics for task execution."""
    retry_count: int = 0
    execution_time: float = 0.0
    queue_time: float = 0.0
    error_count: int = 0

@dataclass
class Task:
    """Represents a system task with enhanced metadata."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = field()
    priority: TaskPriority = field(default=TaskPriority.NORMAL)
    data: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = field(default=TaskStatus.PENDING)
    correlation_id: Optional[str] = field(default=None)
    max_retries: int = field(default=3)
    retry_delay: float = field(default=1.0)
    timeout: float = field(default=300.0)  # 5 minutes default timeout
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = field(default=None)
    completed_at: Optional[datetime] = field(default=None)
    error: Optional[str] = field(default=None)
    metrics: TaskMetrics = field(default_factory=TaskMetrics)
    
    def __lt__(self, other: 'Task') -> bool:
        """Compare tasks for priority queue ordering."""
        return (self.priority.value, self.created_at) < (other.priority.value, other.created_at)

class QueueManager:
    """Enhanced task queue manager with advanced features."""
    
    def __init__(self, 
                 max_concurrent_tasks: int = 5,
                 default_timeout: float = 300.0,
                 task_handlers: Optional[Dict[str, Callable]] = None):
        """Initialize the queue manager."""
        self.max_concurrent_tasks = max_concurrent_tasks
        self.default_timeout = default_timeout
        self.task_handlers = task_handlers or {}
        
        # Initialize queues and state
        self.tasks: Dict[str, Task] = {}
        self.queue = asyncio.PriorityQueue()
        self.running_tasks: List[str] = []
        self._running = False
        self._workers: List[asyncio.Task] = []
        
        # Correlation tracking
        self.correlated_tasks: Dict[str, List[str]] = {}
        
        # Metrics
        self.metrics: Dict[str, Any] = {
            'processed_tasks': 0,
            'failed_tasks': 0,
            'retry_count': 0,
            'avg_processing_time': 0.0
        }
        
    @with_error_handling(ErrorCategory.QUEUE, ErrorSeverity.HIGH)
    async def start(self) -> None:
        """Start the queue manager and worker tasks."""
        try:
            logger.info("Starting queue manager")
            self._running = True
            
            # Start worker tasks
            for _ in range(self.max_concurrent_tasks):
                worker = asyncio.create_task(self._process_tasks())
                self._workers.append(worker)
                
            await event_bus.publish(Event(
                type="queue_manager.started",
                source="queue_manager",
                data={"max_concurrent_tasks": self.max_concurrent_tasks}
            ))
        except Exception as e:
            raise QueueProcessingError(
                "Failed to start queue manager",
                context={"max_concurrent_tasks": self.max_concurrent_tasks},
                recovery_hint="Check system resources and try restarting"
            ) from e
        
    @with_error_handling(ErrorCategory.QUEUE, ErrorSeverity.HIGH)
    async def stop(self) -> None:
        """Stop the queue manager and cleanup."""
        try:
            logger.info("Stopping queue manager")
            self._running = False
            
            # Wait for queue to empty
            await self.queue.join()
            
            # Cancel all workers
            for worker in self._workers:
                worker.cancel()
                
            # Wait for workers to finish
            await asyncio.gather(*self._workers, return_exceptions=True)
            self._workers.clear()
            
            await event_bus.publish(Event(
                type="queue_manager.stopped",
                source="queue_manager",
                data={"metrics": self.metrics}
            ))
        except Exception as e:
            raise QueueProcessingError(
                "Failed to stop queue manager gracefully",
                context={"active_workers": len(self._workers)},
                recovery_hint="Force stop may be required"
            ) from e
        
    @with_error_handling(ErrorCategory.QUEUE, ErrorSeverity.MEDIUM)
    async def enqueue_task(self,
                          task_type: str,
                          data: Dict[str, Any],
                          priority: TaskPriority = TaskPriority.NORMAL,
                          correlation_id: Optional[str] = None,
                          timeout: Optional[float] = None,
                          max_retries: Optional[int] = None) -> str:
        """Add a task to the queue with specified parameters."""
        if not self._running:
            raise QueueProcessingError(
                "Cannot enqueue task - queue manager is not running",
                recovery_hint="Start queue manager before enqueueing tasks"
            )
            
        task = Task(
            type=task_type,
            data=data,
            priority=priority,
            correlation_id=correlation_id,
            timeout=timeout or self.default_timeout,
            max_retries=max_retries if max_retries is not None else 3
        )
        
        logger.debug(f"Enqueueing task: {task.id} of type {task_type}")
        self.tasks[task.id] = task
        
        # Track correlated tasks
        if correlation_id:
            if correlation_id not in self.correlated_tasks:
                self.correlated_tasks[correlation_id] = []
            self.correlated_tasks[correlation_id].append(task.id)
        
        await self.queue.put(task)
        
        await event_bus.publish(Event(
            type="queue_manager.task_queued",
            source="queue_manager",
            data={
                "task_id": task.id,
                "task_type": task_type,
                "priority": priority.name,
                "correlation_id": correlation_id
            }
        ))
        
        return task.id
        
    async def _execute_task(self, task: Task) -> TaskResult:
        """Execute a task with error handling."""
        try:
            # Apply rate limiting if needed
            try:
                await rate_limiter.acquire(task.type, 1)
            except Exception as e:
                raise RateLimitError(
                    str(e),
                    retry_after=60,
                    context={"task_type": task.type}
                )
            
            # Get task handler
            handler = self.task_handlers.get(task.type)
            if not handler:
                raise QueueProcessingError(
                    f"No handler registered for task type: {task.type}",
                    context={"available_handlers": list(self.task_handlers.keys())}
                )
            
            # Execute with timeout
            async with asyncio.timeout(task.timeout):
                start_time = datetime.now()
                result = await handler(task.data)
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # Update metrics
                task.metrics.execution_time = execution_time
                
                return TaskResult(success=True, data=result)
                
        except asyncio.TimeoutError:
            error_msg = f"Task {task.id} timed out after {task.timeout} seconds"
            logger.error(error_msg)
            raise QueueProcessingError(
                error_msg,
                context={
                    "task_id": task.id,
                    "timeout": task.timeout
                },
                recovery_hint="Consider increasing timeout or optimizing task"
            )
            
        except Exception as e:
            logger.error(f"Error executing task {task.id}: {str(e)}", exc_info=True)
            task.metrics.error_count += 1
            
            if isinstance(e, (QueueProcessingError, RateLimitError)):
                raise
            
            raise QueueProcessingError(
                f"Task execution failed: {str(e)}",
                context={
                    "task_id": task.id,
                    "task_type": task.type,
                    "error_count": task.metrics.error_count
                }
            ) from e
            
    @with_error_handling(ErrorCategory.QUEUE, ErrorSeverity.HIGH)
    async def _process_tasks(self) -> None:
        """Process tasks from the queue with error handling."""
        while self._running:
            try:
                # Get next task
                task = await self.queue.get()
                
                if task.status == TaskStatus.CANCELLED:
                    self.queue.task_done()
                    continue
                
                # Update task state
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()
                task.metrics.queue_time = (task.started_at - task.created_at).total_seconds()
                self.running_tasks.append(task.id)
                
                try:
                    await event_bus.publish(Event(
                        type="queue_manager.task_started",
                        source="queue_manager",
                        data={
                            "task_id": task.id,
                            "task_type": task.type,
                            "correlation_id": task.correlation_id
                        }
                    ))
                    
                    # Execute task
                    result = await self._execute_task(task)
                    
                    if result.success:
                        task.status = TaskStatus.COMPLETED
                        self.metrics['processed_tasks'] += 1
                        
                        # Update average processing time
                        current_avg = self.metrics['avg_processing_time']
                        processed_count = self.metrics['processed_tasks']
                        self.metrics['avg_processing_time'] = (
                            (current_avg * (processed_count - 1) + task.metrics.execution_time)
                            / processed_count
                        )
                        
                        await event_bus.publish(Event(
                            type="queue_manager.task_completed",
                            source="queue_manager",
                            data={
                                "task_id": task.id,
                                "result": result.data,
                                "metrics": task.metrics.__dict__,
                                "correlation_id": task.correlation_id
                            }
                        ))
                        
                except Exception as e:
                    if task.metrics.retry_count < task.max_retries:
                        # Retry task
                        task.status = TaskStatus.RETRY
                        task.metrics.retry_count += 1
                        self.metrics['retry_count'] += 1
                        
                        # Add back to queue with delay
                        await asyncio.sleep(task.retry_delay * (2 ** task.metrics.retry_count))
                        await self.queue.put(task)
                        
                        await event_bus.publish(Event(
                            type="queue_manager.task_retry",
                            source="queue_manager",
                            data={
                                "task_id": task.id,
                                "retry_count": task.metrics.retry_count,
                                "error": str(e),
                                "correlation_id": task.correlation_id
                            }
                        ))
                        
                    else:
                        # Mark as failed after max retries
                        task.status = TaskStatus.FAILED
                        task.error = str(e)
                        self.metrics['failed_tasks'] += 1
                        
                        await event_bus.publish(Event(
                            type="queue_manager.task_failed",
                            source="queue_manager",
                            data={
                                "task_id": task.id,
                                "error": str(e),
                                "metrics": task.metrics.__dict__,
                                "correlation_id": task.correlation_id
                            }
                        ))
                
                finally:
                    task.completed_at = datetime.now()
                    if task.id in self.running_tasks:
                        self.running_tasks.remove(task.id)
                    self.queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in task processor: {str(e)}", exc_info=True)
                await error_handler.handle_error(
                    QueueProcessingError(
                        "Task processor error",
                        context={"error": str(e)},
                        recovery_hint="Check system resources and logs"
                    )
                )
                continue

# Create singleton instance
queue_manager = QueueManager()