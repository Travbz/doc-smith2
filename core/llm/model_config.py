"""Model configuration class for language models."""
from typing import Dict, Any

class ModelConfig:
    """Configuration class for language models."""
    
    def __init__(self, model: str, max_tokens: int = 4000, temperature: float = 0.7):
        """Initialize model configuration.
        
        Args:
            model: The model identifier (e.g. "gpt-4-turbo-preview")
            max_tokens: Maximum tokens for model response
            temperature: Temperature for response generation (0.0-1.0)
        """
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        } 