"""Rate limiting service for API calls."""
from typing import Dict, Optional
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from ..logging.logging_service import setup_logger
from core.settings import RATE_LIMIT_REQUESTS, RATE_LIMIT_TOKENS

logger = setup_logger(__name__)

@dataclass
class RateLimitWindow:
    """Represents a rate limit time window."""
    requests: int = 0
    tokens: int = 0
    start_time: datetime = field(default_factory=datetime.now)

class RateLimiter:
    """Rate limiting service for managing API request rates."""
    
    def __init__(self, requests_per_minute: int = RATE_LIMIT_REQUESTS,
                 tokens_per_minute: int = RATE_LIMIT_TOKENS):
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        self.windows: Dict[str, RateLimitWindow] = {}
        
    async def acquire(self, model: str, tokens: int) -> None:
        """Acquire permission to make a request."""
        window = self._get_or_create_window(model)
        
        # Check if window needs to be reset
        if datetime.now() - window.start_time > timedelta(minutes=1):
            self._reset_window(model)
            window = self.windows[model]
        
        # Check rate limits
        if window.requests >= self.requests_per_minute:
            wait_time = 60 - (datetime.now() - window.start_time).seconds
            logger.warning(f"Rate limit reached for {model}. Waiting {wait_time} seconds.")
            await asyncio.sleep(wait_time)
            self._reset_window(model)
            window = self.windows[model]
            
        if window.tokens + tokens > self.tokens_per_minute:
            wait_time = 60 - (datetime.now() - window.start_time).seconds
            logger.warning(f"Token limit reached for {model}. Waiting {wait_time} seconds.")
            await asyncio.sleep(wait_time)
            self._reset_window(model)
            window = self.windows[model]
        
        # Update counters
        window.requests += 1
        window.tokens += tokens
        
    def _get_or_create_window(self, model: str) -> RateLimitWindow:
        """Get or create a rate limit window for a model."""
        if model not in self.windows:
            self.windows[model] = RateLimitWindow()
        return self.windows[model]
        
    def _reset_window(self, model: str) -> None:
        """Reset the rate limit window for a model."""
        self.windows[model] = RateLimitWindow()

# Create singleton instance
rate_limiter = RateLimiter()