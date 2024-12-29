"""GitHub Agent for managing repository operations."""
from typing import Dict, Any
from datetime import datetime

from core.services.logging import setup_logger
from core.services.event_bus import event_bus

from .tools.repository_manager import RepositoryManager
from .tools.pull_request_manager import PullRequestManager
from .tools.branch_manager import BranchManager

logger = setup_logger(__name__)

class GitHubAgent:
    """Agent responsible for GitHub documentation operations."""

    def __init__(self, agency):
        """Initialize the GitHub Agent."""
        self.agency = agency
        
        # Initialize tools
        self.repo_manager = RepositoryManager(self)
        self.pr_manager = PullRequestManager(self)
        self.branch_manager = BranchManager(self)

    async def initialize(self) -> None:
        """Initialize the agent."""
        logger.info("Initializing GitHub Agent")
        try:
            # Subscribe to relevant events
            event_bus.subscribe("documentation.ready", self._handle_documentation_ready)
            logger.info("GitHub Agent initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing GitHub Agent: {str(e)}")
            raise

    async def process_repository(self, repo_url: str) -> Dict[str, Any]:
        """Process a repository for documentation."""
        try:
            # Clone repository
            clone_result = await self.repo_manager.clone_repository(repo_url)
            if clone_result["status"] != "success":
                raise ValueError(f"Failed to clone repository: {clone_result.get('error')}")

            return {
                "status": "success",
                "data": clone_result["data"]
            }

        except Exception as e:
            logger.error(f"Error processing repository: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def _handle_documentation_ready(self, event: Dict) -> None:
        """Handle documentation ready for PR creation."""
        try:
            documentation = event["data"]["documentation"]
            repo_info = event["data"]["repository"]
            
            # Create PR with documentation
            pr_result = await self.pr_manager.create_documentation_pr(
                documentation,
                repo_info
            )
            
            if pr_result["status"] == "success":
                # Notify PR created
                await event_bus.publish({
                    "type": "github.pr_created",
                    "source": "github_agent",
                    "data": pr_result["data"]
                })

        except Exception as e:
            logger.error(f"Error handling documentation ready: {str(e)}")
            await event_bus.publish({
                "type": "github.error",
                "source": "github_agent",
                "data": {"error": str(e)}
            })