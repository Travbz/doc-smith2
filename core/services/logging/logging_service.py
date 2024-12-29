"""Logging service for the application."""
import logging
from rich.logging import RichHandler
from rich.console import Console
from rich.traceback import install as install_rich_traceback
from core.settings import LOG_LEVEL

# Install rich traceback handler for better error display
install_rich_traceback(show_locals=True)
console = Console()

def setup_logger(name: str) -> logging.Logger:
    """Set up a logger with console output and rich formatting.
    
    Args:
        name: Name of the logger (usually __name__ of the calling module)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Console handler with rich formatting
    console_handler = RichHandler(
        rich_tracebacks=True,
        markup=True,
        show_time=True,
        show_path=True
    )
    console_handler.setLevel(LOG_LEVEL)
    logger.addHandler(console_handler)
    
    return logger

def log_exception(logger: logging.Logger, exc: Exception, context: str = ""):
    """Log an exception with rich formatting and context.
    
    Args:
        logger: Logger instance to use
        exc: Exception to log
        context: Optional context about where/why the exception occurred
    """
    console.print(f"[red]Exception in {context}:[/red]", style="bold red")
    console.print_exception()
    logger.error(f"Exception in {context}: {str(exc)}", exc_info=True)