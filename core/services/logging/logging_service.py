"""Logging service for the application."""
import logging
import sys
from datetime import datetime
from typing import Optional
from pathlib import Path
from core.settings import LOGS_PATH, LOG_LEVEL

def setup_logger(name: str, level: int = LOG_LEVEL) -> logging.Logger:
    """Set up a logger with the specified name and level."""
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create console handler with formatting
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        # Add console handler to logger
        logger.addHandler(console_handler)
        
        # Create file handler
        file_handler = logging.FileHandler(
            LOGS_PATH / f"{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        
        # Add file handler to logger
        logger.addHandler(file_handler)

    return logger

def log_exception(error: Exception, logger: Optional[logging.Logger] = None) -> None:
    """Log an exception with full traceback."""
    if logger is None:
        logger = logging.getLogger('error_handler')
    
    logger.error(
        f"Exception occurred: {str(error)}",
        exc_info=True,
        extra={
            'error_type': type(error).__name__,
            'timestamp': datetime.now().isoformat()
        }
    )