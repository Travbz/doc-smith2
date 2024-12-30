"""Agency for managing agent communication and documentation generation workflow."""
from typing import Dict, List, Tuple, Any, Optional
import asyncio
from pathlib import Path
import os

from core.services.event_bus import event_bus
from core.services.logging import setup_logger
from core.services.cache import cache_manager
from core.services.error_handling.error_handler import (
    with_error_handling,
    ErrorCategory,
    ErrorSeverity,
    DocSmithError
)
from core.agency.documentation_agent.documentation_agent import DocumentationAgent
from core.agency.review_agent.review_agent import ReviewAgent
from core.agency.github_agent.github_agent import GitHubAgent

logger = setup_logger(__name__)

class AgencyError(DocSmithError):
    """Specific error class for agency-level issues."""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
        super().__init__(
            message,
            category=ErrorCategory.SYSTEM,
            severity=severity,
            recovery_hint="Check agency configuration and ensure all required services are available"
        )

class Agency:
    """Main agency class coordinating all agents."""

    def __init__(self):
        """Initialize the agency."""
        self.documentation_agent = None
        self.review_agent = None
        self.github_agent = None
        self._initialized = False
        self._event_processing = False
        self._event_processing_task = None

    async def initialize(self) -> None:
        """Initialize the agency and its agents."""
        if self._initialized:
            logger.warning("Agency already initialized")
            return

        try:
            logger.info("Initializing agency")
            
            # Start event bus
            await event_bus.start()
            
            # Initialize agents
            logger.info("Initializing documentation agent")
            self.documentation_agent = DocumentationAgent(self)
            await self.documentation_agent.initialize()
            
            logger.info("Initializing review agent")
            self.review_agent = ReviewAgent(self)
            await self.review_agent.initialize()
            
            logger.info("Initializing github agent")
            self.github_agent = GitHubAgent(self)
            await self.github_agent.initialize()
            
            self._initialized = True
            logger.info("Agency initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing agency: {str(e)}")
            await self.cleanup()
            raise AgencyError(f"Failed to initialize agency: {str(e)}", ErrorSeverity.HIGH)

    async def process_repository(self, repo_url: str) -> Dict[str, Any]:
        """Process a repository for documentation generation.
        
        Args:
            repo_url: Repository URL or owner/name format
            
        Returns:
            Dictionary containing processing results
        """
        try:
            # Clone repository
            clone_result = await self.github_agent.repository_manager.clone_repository(repo_url)
            if not clone_result["success"]:
                raise AgencyError(
                    f"Failed to clone repository: {clone_result.get('error')}",
                    ErrorSeverity.HIGH
                )
                
            # Start event processing
            self._event_processing = True
            self._event_processing_task = asyncio.create_task(self._process_events())
                
            # Generate documentation
            doc_result = await self.documentation_agent.generate_documentation(
                repo_path=clone_result["data"]["local_path"],
                repo_name=clone_result["data"]["full_name"]
            )
            
            # Wait for event processing to complete (5 minute timeout)
            try:
                await asyncio.wait_for(self._event_processing_task, timeout=300)
            except asyncio.TimeoutError:
                logger.warning("Event processing timed out after 5 minutes")
            finally:
                self._event_processing = False
            
            return doc_result
            
        except Exception as e:
            raise AgencyError(f"Failed to process repository: {str(e)}", ErrorSeverity.HIGH) from e

    async def _process_events(self) -> None:
        """Process events until completion."""
        while self._event_processing:
            if event_bus._queue.empty():
                # No more events to process, check if we're done
                if not any(agent._active_tasks for agent in [self.documentation_agent, self.review_agent, self.github_agent]):
                    break
            await asyncio.sleep(0.1)  # Small delay to prevent busy waiting

    async def cleanup(self) -> None:
        """Cleanup agency resources."""
        try:
            logger.info("Cleaning up agency resources")
            
            # Stop event processing
            self._event_processing = False
            if self._event_processing_task:
                try:
                    await asyncio.wait_for(self._event_processing_task, timeout=5)
                except asyncio.TimeoutError:
                    logger.warning("Event processing cleanup timed out")
            
            # Cleanup agents
            if self.documentation_agent:
                await self.documentation_agent.cleanup()
            if self.review_agent:
                await self.review_agent.cleanup()
            if self.github_agent:
                await self.github_agent.cleanup()
                
            # Stop event bus
            await event_bus.stop()
            
            self._initialized = False
            
        except Exception as e:
            logger.error(f"Error during agency cleanup: {str(e)}")
            raise AgencyError(f"Failed to cleanup agency: {str(e)}", ErrorSeverity.HIGH)