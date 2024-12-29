"""Model configurations for different agents and workflows."""
from typing import Dict, Any
from core.llm.model_config import ModelConfig
from core.settings import (
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    AGENT_MODELS,
    AGENT_TEMPERATURES,
    AGENT_MAX_TOKENS,
    MAX_TOKENS_PER_REQUEST
)

def get_workflow_model(workflow_type: str) -> ModelConfig:
    """Get model configuration for workflow type.
    
    Different workflows may require different model configurations based on their complexity:
    - documentation: Higher tokens for comprehensive documentation generation
    - api_documentation: Balanced settings for API documentation
    - review: Lower temperature for precise review tasks
    - git: Lower tokens for simple git operations
    
    Args:
        workflow_type: Type of workflow requiring model configuration
        
    Returns:
        ModelConfig instance with appropriate settings for the workflow
    """
    configs = {
        "documentation": ModelConfig(
            model=AGENT_MODELS.get("doc_writer", DEFAULT_MODEL),
            max_tokens=AGENT_MAX_TOKENS.get("doc_writer", DEFAULT_MAX_TOKENS),
            temperature=AGENT_TEMPERATURES.get("doc_writer", DEFAULT_TEMPERATURE)
        ),
        "api_documentation": ModelConfig(
            model=AGENT_MODELS.get("doc_writer", DEFAULT_MODEL),
            max_tokens=AGENT_MAX_TOKENS.get("doc_writer", DEFAULT_MAX_TOKENS),
            temperature=0.6  # Slightly lower for more precise API docs
        ),
        "review": ModelConfig(
            model=AGENT_MODELS.get("doc_reviewer", DEFAULT_MODEL),
            max_tokens=AGENT_MAX_TOKENS.get("doc_reviewer", DEFAULT_MAX_TOKENS),
            temperature=AGENT_TEMPERATURES.get("doc_reviewer", DEFAULT_TEMPERATURE)
        ),
        "git": ModelConfig(
            model=AGENT_MODELS.get("github", DEFAULT_MODEL),
            max_tokens=AGENT_MAX_TOKENS.get("github", DEFAULT_MAX_TOKENS),
            temperature=AGENT_TEMPERATURES.get("github", DEFAULT_TEMPERATURE)
        )
    }
    
    return configs.get(workflow_type, ModelConfig(
        model=DEFAULT_MODEL,
        max_tokens=DEFAULT_MAX_TOKENS,
        temperature=DEFAULT_TEMPERATURE
    ))

def get_agent_model(agent_type: str) -> ModelConfig:
    """Get model configuration for agent type.
    
    Different agents may require different model configurations based on their specific needs:
    - tech_lead: Higher temperature for more creative planning and coordination
    - code_analyst: Lower temperature for more precise code analysis
    - doc_reviewer: Balanced settings for documentation review
    - github: Lower tokens and temperature for focused repository management
    
    Args:
        agent_type: Type of agent requiring model configuration
        
    Returns:
        ModelConfig instance with appropriate settings for the agent
    """
    return ModelConfig(
        model=AGENT_MODELS.get(agent_type, DEFAULT_MODEL),
        max_tokens=AGENT_MAX_TOKENS.get(agent_type, DEFAULT_MAX_TOKENS),
        temperature=AGENT_TEMPERATURES.get(agent_type, DEFAULT_TEMPERATURE)
    )