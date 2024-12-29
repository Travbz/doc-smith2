"""OpenAI client for interacting with the OpenAI API."""
from typing import Dict, List, Optional, AsyncGenerator
import asyncio
import openai
from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletion

from core.services.caching.cache_manager import cache_manager
from core.services.rate_limiting.rate_limiter import rate_limiter
from core.services.error_handling.error_handler import error_tracker, retry_with_exponential_backoff
from core.services.logging.logging_service import setup_logger

from core.settings import OPENAI_API_KEY, OPENAI_ORG_ID
from .model_config import ModelConfig
from .token_counter import count_tokens
from .cost_calculator import calculate_cost, cost_tracker

# Custom error classes
class APIError(Exception):
    """Base class for OpenAI API errors."""
    pass

class RateLimitError(APIError):
    """Raised when rate limit is exceeded."""
    pass

class TokenLimitError(APIError):
    """Raised when token limit is exceeded."""
    pass

class ModelError(APIError):
    """Raised when there's an issue with the model."""
    pass

logger = setup_logger(__name__)

class OpenAIClient:
    def __init__(self):
        # Initialize clients with or without org ID
        client_args = {"api_key": OPENAI_API_KEY}
        if OPENAI_ORG_ID:
            client_args["organization"] = OPENAI_ORG_ID
            
        self.client = OpenAI(**client_args)
        self.async_client = AsyncOpenAI(**client_args)
        
    @retry_with_exponential_backoff()
    async def get_completion(
        self,
        prompt: str,
        model_config: ModelConfig,
        cache_key: Optional[str] = None,
        stream: bool = False
    ) -> ChatCompletion:
        """Get a completion from OpenAI with retry logic and caching."""
        # Check cache first
        if cache_key and not stream:
            cached_response = cache_manager.get(cache_key)
            if cached_response is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_response

        # Count tokens and validate against model's limit
        token_count = count_tokens(prompt, model_config.model)
        if token_count > model_config.max_tokens:
            error = TokenLimitError(
                f"Prompt exceeds token limit: {token_count} > {model_config.max_tokens}"
            )
            error_tracker.record_error(error, "Token limit exceeded")
            raise error

        # Apply rate limiting
        await rate_limiter.acquire(model_config.model, token_count)

        # Calculate estimated cost
        estimated_cost = calculate_cost(token_count, model_config.model)
        if token_count > 100:  # Only log cost for significant operations
            logger.info(f"Estimated cost for completion: ${estimated_cost:.4f}")

        try:
            response = await self._make_request(prompt, model_config, stream)
            
            # Track actual usage and cost
            if not stream and hasattr(response, 'usage'):
                cost_tracker.add_request(
                    model_config.model,
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens
                )
            
            # Cache the response if appropriate
            if cache_key and not stream:
                cache_manager.set(cache_key, response)
            
            return response
            
        except Exception as e:
            error_context = {
                "model": model_config.model,
                "token_count": token_count,
                "estimated_cost": estimated_cost
            }
            error_tracker.record_error(e, "OpenAI API request failed", error_context)
            
            if "rate limit" in str(e).lower():
                raise RateLimitError(str(e))
            elif "token limit" in str(e).lower():
                raise TokenLimitError(str(e))
            elif "model" in str(e).lower():
                raise ModelError(str(e))
            else:
                raise APIError(str(e))

    async def _make_request(
        self,
        prompt: str,
        model_config: ModelConfig,
        stream: bool = False
    ) -> ChatCompletion:
        """Make the actual API request to OpenAI."""
        messages = [{"role": "user", "content": prompt}]
        
        response = await self.async_client.chat.completions.create(
            messages=messages,
            stream=stream,
            **model_config.to_dict()
        )
        
        return response

    async def get_stream_completion(
        self,
        prompt: str,
        model_config: ModelConfig
    ) -> AsyncGenerator[str, None]:
        """Get a streaming completion."""
        async for response in await self._make_request(prompt, model_config, stream=True):
            if response.choices[0].delta.content is not None:
                yield response.choices[0].delta.content

# Create singleton instance
openai_client = OpenAIClient()