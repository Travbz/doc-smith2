"""Agency for managing agent communication and documentation generation workflow."""
from typing import Dict, List, Tuple, Any, Optional
import asyncio
from pathlib import Path
import os

from core.services.event_bus import event_bus
from core.services.logging import setup_logger
from core.services.cache import cache_manager

logger = setup_logger(__name__)

class Agency:
    """Main agency class for coordinating documentation generation."""
    
    REPO_TYPES = {
        "spring_boot": ["pom.xml", "build.gradle", "src/main/java", "application.properties", "application.yml"],
        "nginx": ["nginx.conf", "default.conf"],
        "bounded_context": ["helm", "terraform"],
        "python": ["requirements.txt", "setup.py", "pyproject.toml", "src", "main.py"]
    }

    def __init__(self, 
                 communication_paths: List[Tuple[str, str]],
                 shared_instructions: str = None,
                 temperature: float = 0.5,
                 max_prompt_tokens: int = 4000):
        """Initialize the agency with communication paths and settings."""
        self.paths = set(communication_paths)
        self.shared_instructions = self._load_instructions(shared_instructions)
        self.temperature = temperature
        self.max_tokens = max_prompt_tokens
        self.agents = {}
        
    async def initialize(self):
        """Initialize the agency and its services."""
        logger.info("Initializing agency")
        await event_bus.start()
        await self._initialize_agents()
        
    def _load_instructions(self, path: str) -> str:
        """Load shared instructions from file."""
        if not path:
            return ""
        try:    
            with open(path, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading instructions: {e}")
            return ""

    async def _initialize_agents(self):
        """Initialize all required agents."""
        from core.agency.documentation_agent.documentation_agent import DocumentationAgent
        from core.agency.github_agent.github_agent import GitHubAgent
        from core.agency.review_agent.review_agent import ReviewAgent
        
        self.agents = {
            "documentation": DocumentationAgent(self),
            "github": GitHubAgent(self),
            "review": ReviewAgent(self)
        }
        
        for agent in self.agents.values():
            await agent.initialize()

    def _detect_repo_type(self, repo_path: str) -> str:
        """Detect repository type based on file structure."""
        for repo_type, patterns in self.REPO_TYPES.items():
            matches = 0
            for pattern in patterns:
                if Path(repo_path, pattern).exists():
                    matches += 1
            if matches >= 2:  # Require at least 2 matching patterns
                return repo_type
        return "unknown"

    async def process_repository(self, repo_url: str) -> Dict[str, Any]:
        """Process repository and generate documentation."""
        logger.info(f"Processing repository: {repo_url}")
        
        try:
            # Clone repository using GitHub agent
            clone_result = await self.agents["github"].clone_repository(repo_url)
            if clone_result.get("status") != "success":
                raise RuntimeError(f"Repository cloning failed: {clone_result.get('error')}")
            
            repo_path = clone_result["data"]["local_path"]
            
            # Detect repository type
            repo_type = self._detect_repo_type(repo_path)
            logger.info(f"Detected repository type: {repo_type}")
            
            # Generate documentation based on repository type
            doc_result = await self.agents["documentation"].generate_documentation(
                repo_path=repo_path,
                repo_type=repo_type,
                repo_url=repo_url
            )
            
            if doc_result.get("status") != "success":
                raise RuntimeError(f"Documentation generation failed: {doc_result.get('error')}")
            
            # Review documentation
            review_result = await self.agents["review"].review_documentation(
                documentation=doc_result["data"]["documentation"],
                repo_type=repo_type
            )
            
            if review_result.get("status") != "success":
                raise RuntimeError(f"Documentation review failed: {review_result.get('error')}")
            
            # Create pull request with documentation
            pr_result = await self.agents["github"].create_documentation_pr(
                documentation=doc_result["data"]["documentation"],
                repo_url=repo_url,
                repo_type=repo_type
            )
            
            return {
                "status": "success",
                "data": {
                    "repo_type": repo_type,
                    "documentation": doc_result["data"]["documentation"],
                    "review": review_result["data"],
                    "pull_request": pr_result["data"]
                }
            }
            
        except Exception as e:
            logger.error(f"Repository processing failed: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }

    async def cleanup(self):
        """Cleanup agency resources."""
        logger.info("Cleaning up agency resources")
        for agent in self.agents.values():
            await agent.cleanup()
        await event_bus.stop()