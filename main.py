"""Main entry point for the documentation generation system."""
import os
import sys
import asyncio
import argparse
from typing import Optional, List, Tuple
from datetime import datetime

from core.services.logging import setup_logger
from core.agency.agency import Agency

logger = setup_logger(__name__)

def validate_environment() -> None:
    """Validate required environment variables and dependencies."""
    logger.info("Validating environment")
    required_vars = [
        "GITHUB_TOKEN",
        "OPENAI_API_KEY"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

async def main() -> None:
    """Main entry point."""
    try:
        # Parse arguments
        parser = argparse.ArgumentParser(description="Generate documentation for a repository")
        parser.add_argument("repo_url", help="Repository URL or owner/name")
        args = parser.parse_args()
        
        # Validate environment
        validate_environment()
        
        # Initialize agency
        logger.info("Initializing documentation agency")
        agency = Agency()
        await agency.initialize()
        
        # Process repository
        logger.info(f"Processing repository: {args.repo_url}")
        result = await agency.process_repository(args.repo_url)
        
        if result and result.get("doc_id"):
            logger.info("Documentation generated successfully!")
            logger.info(f"Documentation ID: {result['doc_id']}")
        else:
            logger.error("Documentation generation failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        sys.exit(1)
        
    finally:
        if 'agency' in locals():
            logger.info("Cleaning up agency resources")
            await agency.cleanup()

if __name__ == "__main__":
    asyncio.run(main())