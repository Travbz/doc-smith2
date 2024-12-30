"""Enhanced error handling system with recovery mechanisms and reporting."""
from typing import Type, Callable, Any, Optional, Dict, List, Union
import functools
import asyncio
from datetime import datetime, timedelta
from enum import Enum
import json
import traceback
from core.services.logging.logging_service import setup_logger, log_exception
from core.settings import MAX_RETRIES, RETRY_DELAY

logger = setup_logger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels."""
    CRITICAL = "critical"  # System-wide failure, immediate attention required
    HIGH = "high"         # Service disruption, needs prompt attention
    MEDIUM = "medium"     # Degraded service, needs attention soon
    LOW = "low"          # Minor issue, can be addressed later

class ErrorCategory(Enum):
    """Categories of errors for better organization."""
    QUEUE = "queue"               # Queue processing errors
    EVENT_BUS = "event_bus"       # Event bus communication errors
    RATE_LIMIT = "rate_limit"     # Rate limiting and throttling
    API = "api"                   # External API errors
    DOC_GEN = "doc_gen"          # Documentation generation
    DATABASE = "database"         # Database operations
    NETWORK = "network"          # Network connectivity
    SYSTEM = "system"            # System-level errors
    UNKNOWN = "unknown"          # Uncategorized errors

class DocSmithError(Exception):
    """Enhanced base exception class for DocSmith."""
    def __init__(self, 
                message: str,
                category: ErrorCategory = ErrorCategory.UNKNOWN,
                severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                context: Optional[Dict] = None,
                recovery_hint: Optional[str] = None):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.recovery_hint = recovery_hint
        self.timestamp = datetime.now()

class APIError(DocSmithError):
    """Error class for API-related issues."""
    def __init__(self, 
                message: str,
                severity: ErrorSeverity = ErrorSeverity.HIGH,
                context: Optional[Dict] = None,
                recovery_hint: Optional[str] = None):
        super().__init__(
            message,
            category=ErrorCategory.API,
            severity=severity,
            context=context,
            recovery_hint=recovery_hint or "Check API credentials and endpoint availability"
        )

async def publish_error_event(error: DocSmithError):
    """Publish error event to event bus."""
    # Import here to avoid circular import
    from core.services.event_bus.event_bus import event_bus, Event
    
    await event_bus.publish(Event(
        type="error.occurred",
        source="error_handler",
        data={
            "message": str(error),
            "category": error.category.value,
            "severity": error.severity.value,
            "context": error.context,
            "recovery_hint": error.recovery_hint,
            "timestamp": error.timestamp.isoformat(),
            "traceback": traceback.format_exc()
        }
    ))

def with_error_handling(category: ErrorCategory, severity: ErrorSeverity):
    """Decorator for handling errors in async functions."""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if isinstance(e, DocSmithError):
                    error = e
                else:
                    error = DocSmithError(
                        message=str(e),
                        category=category,
                        severity=severity,
                        context={"args": args, "kwargs": kwargs}
                    )
                
                # Log the error
                log_exception(error)
                
                # Publish error event
                await publish_error_event(error)
                
                # Handle based on severity
                if error.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
                    # Attempt recovery for critical errors
                    for attempt in range(MAX_RETRIES):
                        try:
                            await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                            return await func(*args, **kwargs)
                        except Exception as retry_error:
                            last_error = retry_error
                            continue
                    
                    # If all retries failed, raise the last error
                    if last_error:
                        if isinstance(last_error, DocSmithError):
                            raise last_error
                        raise DocSmithError(
                            message=str(last_error),
                            category=category,
                            severity=severity,
                            context={"args": args, "kwargs": kwargs}
                        ) from last_error
                
                raise error
                
        return wrapper
    return decorator