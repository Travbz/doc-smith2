"""Cache manager for storing and retrieving results."""
from datetime import datetime, timedelta
import hashlib
import json
import pickle
from typing import Dict, Any, Optional
import logging
from core.services.logging.logging_service import setup_logger

logger = setup_logger(__name__)

class CacheManager:
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_expiry = timedelta(hours=1)
        self.validation_expiry = timedelta(days=1)  # Longer expiry for validation results

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key not in self.cache:
            return None
            
        entry = self.cache[key]
        if datetime.now() > entry["expires"]:
            del self.cache[key]
            return None
            
        return entry["value"]

    def set(self, key: str, value: Any, is_validation: bool = False) -> None:
        """Set value in cache with expiry."""
        # Use longer expiry for validation results
        expiry = self.validation_expiry if is_validation else self.default_expiry
        
        self.cache[key] = {
            "value": value,
            "expires": datetime.now() + expiry
        }

    def generate_key(self, *args: Any, **kwargs: Any) -> str:
        """Generate cache key from arguments."""
        # Convert args and kwargs to string and hash
        key_parts = [str(arg) for arg in args]
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key_str = "|".join(key_parts)
        
        return hashlib.md5(key_str.encode()).hexdigest()

    def clear_expired(self) -> None:
        """Remove expired entries from cache."""
        now = datetime.now()
        expired = [k for k, v in self.cache.items() if now > v["expires"]]
        for key in expired:
            del self.cache[key]

# Create singleton instance
cache_manager = CacheManager()