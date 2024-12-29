from typing import Type, Callable, Any, Optional
import functools
import asyncio
from datetime import datetime
from core.services.logging.logging_service import setup_logger, log_exception
from core.settings import MAX_RETRIES, RETRY_DELAY


logger = setup_logger(__name__)

class DocSmithError(Exception):
    """Base exception class for DocSmith."""
    pass

class RateLimitError(DocSmithError):
    """Raised when rate limits are exceeded."""
    pass

class TokenLimitError(DocSmithError):
    """Raised when token limits are exceeded."""
    pass

class ModelError(DocSmithError):
    """Raised when there's an error with the model."""
    pass

class APIError(DocSmithError):
    """Raised when there's an API error."""
    pass

def retry_with_exponential_backoff(
    max_retries: int = MAX_RETRIES,
    base_delay: float = RETRY_DELAY,
    exponential_base: float = 2,
    max_delay: float = 60,
    allowed_exceptions: tuple = (RateLimitError, APIError)
):
    """Decorator for retrying functions with exponential backoff."""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                    
                except allowed_exceptions as e:
                    last_exception = e
                    if attempt == max_retries - 1:
                        raise
                        
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}. "
                        f"Retrying in {delay} seconds..."
                    )
                    await asyncio.sleep(delay)
                    
                except Exception as e:
                    log_exception(logger, e, f"Error in {func.__name__}")
                    raise
                    
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator

class ErrorTracker:
    """Track and analyze errors for monitoring and debugging."""
    
    def __init__(self):
        self.errors = []
        
    def record_error(
        self,
        error: Exception,
        context: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> None:
        """Record an error with context and metadata."""
        error_entry = {
            'timestamp': datetime.now(),
            'error_type': type(error).__name__,
            'message': str(error),
            'context': context,
            'metadata': metadata or {}
        }
        self.errors.append(error_entry)
        
    def get_error_summary(self) -> dict:
        """Get a summary of recorded errors."""
        if not self.errors:
            return {'total_errors': 0}
            
        error_types = {}
        for error in self.errors:
            error_type = error['error_type']
            error_types[error_type] = error_types.get(error_type, 0) + 1
            
        return {
            'total_errors': len(self.errors),
            'error_types': error_types,
            'latest_error': self.errors[-1]
        }
        
    def clear_errors(self) -> None:
        """Clear recorded errors."""
        self.errors.clear()

# Create singleton instance
error_tracker = ErrorTracker()