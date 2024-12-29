"""Core settings for the DocSmith system."""
from pathlib import Path
import os
import logging

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Required environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
OPENAI_ORG_ID = os.getenv("OPENAI_ORG_ID")  # Optional

# OpenAI Settings
DEFAULT_MODEL = "gpt-4-turbo-preview"  # Default fallback model
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 4000

# Agent-specific model configurations
AGENT_MODELS = {
    "tech_lead": "gpt-4-turbo-preview",  # Complex reasoning and coordination
    "code_analyst": "gpt-4-turbo-preview",  # Deep code analysis
    "doc_writer": "gpt-3.5-turbo",  # High context for documentation
    "doc_reviewer": "gpt-4-turbo-preview",  # Critical analysis
    "github": "gpt-3.5-turbo"  # Simple operations
}

AGENT_TEMPERATURES = {
    "tech_lead": 0.8,  # More creative for planning and coordination
    "code_analyst": 0.5,  # More precise for analysis
    "doc_writer": 0.7,  # Balanced for documentation
    "doc_reviewer": 0.6,  # More precise for review
    "github": 0.5  # More precise for git operations
}

AGENT_MAX_TOKENS = {
    "tech_lead": 4000,  # Complex planning needs more tokens
    "code_analyst": 4000,  # Code analysis needs more context
    "doc_writer": 4000,  # Documentation generation needs lots of context
    "doc_reviewer": 4000,  # Review needs good context
    "github": 2000  # Git operations need minimal context
}

TOKEN_BUFFER = 500
MAX_TOKENS_PER_REQUEST = 4000

# GitHub Settings
DEFAULT_BRANCH = "main"
GIT_DOCS_BRANCH_PREFIX = "docs/update-documentation"

# Documentation Settings
MAX_REVIEW_ITERATIONS = 3
DOC_REVIEW_MAX_CYCLES = 3  # Maximum number of review cycles per document
DOC_REVIEW_MIN_QUALITY_SCORE = 0.8  # Minimum quality score to pass review


# Review Types
REVIEW_TYPES = {
    "TECHNICAL": ["architecture", "api", "deployment"],
    "CONTENT": ["readme", "development", "tutorial"],
    "SECURITY": ["security", "api", "deployment"]
}

# I want to support any file type that could be committed to a git repository
SUPPORTED_FILE_TYPES = (
    '.py', '.js', '.ts', '.go', '.rs', '.java', '.kt', '.swift', '.rb', '.php',
    '.cs', '.html', '.css', '.sql', '.json', '.xml', '.yaml', '.yml', '.md',
    '.txt', '.csv', '.tsv', '.sh', '.bat', '.ps1', '.pl', '.r', '.matlab',
    '.mat', '.m', '.jl', '.hs', '.tf', '.tfvars', '.tfstate', '.tfstate.backup',
    '.hcl'
)

# Output Settings
DEFAULT_DOCS_PATH = "docs/"
DEFAULT_README = "README.md"

# Performance Settings
MAX_CONCURRENT_TASKS = 5
RATE_LIMIT_REQUESTS = 60  # requests per minute
RATE_LIMIT_TOKENS = 90000  # tokens per minute

# Error handling settings
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Logging Settings
LOG_LEVEL = logging.INFO  # Can be overridden by environment variable