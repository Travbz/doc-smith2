"""Main entry point for the Documentation Generator."""
import os
import sys
import asyncio
from typing import Dict, Any, List, Tuple
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).resolve().parent))

from core.agency.agency import Agency
from core.services.logging.logging_service import setup_logger
from core.settings import OPENAI_API_KEY, GITHUB_TOKEN, GITHUB_USERNAME

logger = setup_logger(__name__)

def get_communication_paths() -> List[Tuple[str, str]]:
    """Define allowed communication paths between agents."""
    return [
        ("documentation", "github"),
        ("documentation", "review"),
        ("review", "documentation"),
        ("review", "github"),
        ("github", "documentation"),
        ("github", "review")
    ]

def validate_environment() -> None:
    """Validate required environment variables."""
    required_vars = {
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "GITHUB_TOKEN": GITHUB_TOKEN,
        "GITHUB_USERNAME": GITHUB_USERNAME
    }
    
    missing = [var for var, value in required_vars.items() if not value]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

def print_help() -> None:
    """Print usage instructions."""
    print("""
Documentation Generator

Usage: python main.py <repository_url> [options]

Arguments:
  repository_url         GitHub repository URL or owner/repo format

Options:
  --type TYPE           Repository type (BE, FE, BC, python, unknown)
  --branch BRANCH       Branch to document (default: main)
  --help              Show this help message

Environment Variables:
  OPENAI_API_KEY      OpenAI API key
  GITHUB_TOKEN        GitHub personal access token
  GITHUB_USERNAME     GitHub username

Examples:
  python main.py octocat/Hello-World
  python main.py https://github.com/octocat/Hello-World --type BE
  python main.py octocat/Hello-World --branch develop
    """)

async def main() -> None:
    """Main execution flow."""
    try:
        # Parse arguments
        if len(sys.argv) < 2 or "--help" in sys.argv:
            print_help()
            sys.exit(0)
            
        repo_url = sys.argv[1]
        
        # Validate environment
        logger.info("Validating environment")
        validate_environment()
        
        # Initialize agency
        logger.info("Initializing documentation agency")
        agency = Agency(
            communication_paths=get_communication_paths(),
            shared_instructions="core/agency/shared_instructions.md"
        )
        
        await agency.initialize()
        
        # Process repository
        logger.info(f"Processing repository: {repo_url}")
        result = await agency.process_repository(repo_url)
        
        if result["status"] == "success":
            logger.info("Documentation generated successfully!")
            logger.info(f"Pull request: {result['data']['pull_request']['url']}")
            sys.exit(0)
        else:
            logger.error(f"Documentation generation failed: {result['error']}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        if 'agency' in locals():
            await agency.cleanup()

if __name__ == "__main__":
    asyncio.run(main())