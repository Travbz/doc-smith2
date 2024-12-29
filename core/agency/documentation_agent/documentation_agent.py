"""Documentation Agent for analyzing repositories and generating documentation."""
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

from core.services.logging import setup_logger
from core.services.event_bus import event_bus
from core.services.cache import cache_manager

from .tools.repository_analyzer import RepositoryAnalyzer
from .tools.standard_selector import StandardSelector
from .tools.content_generator import ContentGenerator
from .tools.template_manager import TemplateManager
from .tools.feedback_processor import FeedbackProcessor
from .tools.content_reviser import ContentReviser

from .schemas.generated_content import GeneratedContent
from .schemas.documentation_standard import DocumentationStandard

logger = setup_logger(__name__)

class DocumentationAgent:
    """Agent responsible for documentation generation and management."""

    def __init__(self, agency):
        """Initialize the Documentation Agent."""
        self.agency = agency
        self.cache = cache_manager
        
        # Initialize tools
        self.repo_analyzer = RepositoryAnalyzer()
        self.standard_selector = StandardSelector()
        self.content_generator = ContentGenerator()
        self.template_manager = TemplateManager()
        self.feedback_processor = FeedbackProcessor()
        self.content_reviser = ContentReviser()
        
        # Track current processing state
        self.current_repo: Optional[str] = None
        self.current_iteration: int = 0
        self.max_iterations: int = 5

    async def initialize(self) -> None:
        """Initialize the agent and its resources."""
        logger.info("Initializing Documentation Agent")
        try:
            # Subscribe to relevant events
            event_bus.subscribe("review.feedback_generated", self._handle_feedback)
            event_bus.subscribe("review.approved", self._handle_approval)
            event_bus.subscribe("review.rejected", self._handle_rejection)
            
            # Load standards and templates
            await self.standard_selector.load_standards()
            await self.template_manager.load_templates()
            
            logger.info("Documentation Agent initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Documentation Agent: {str(e)}")
            raise

    async def generate_documentation(
        self,
        repo_path: str,
        repo_type: Optional[str] = None,
        custom_rules: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Generate documentation for a repository.
        
        Args:
            repo_path: Path to the repository
            repo_type: Optional repository type override
            custom_rules: Optional custom documentation rules
            
        Returns:
            Generated documentation content
        """
        try:
            self.current_repo = repo_path
            self.current_iteration = 0
            
            # Analyze repository
            repo_analysis = await self.repo_analyzer.analyze_repository(repo_path)
            detected_type = repo_type or repo_analysis.repository_type
            
            # Select documentation standard
            standard = await self.standard_selector.select_standard(
                detected_type,
                custom_rules
            )
            
            # Validate standard can be applied
            if not await self.standard_selector.validate_standard(standard, repo_path):
                raise ValueError(f"Selected standard cannot be applied to repository: {repo_path}")
            
            # Generate initial documentation
            documentation = await self.content_generator.generate_documentation(
                repository_path=repo_path,
                repository_type=detected_type,
                standard=standard
            )
            
            # Submit for review
            await self._submit_for_review(documentation)
            
            return {
                "status": "success",
                "message": "Documentation submitted for review",
                "data": {
                    "repository_type": detected_type,
                    "documentation_id": documentation.documentation_version
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating documentation: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def _handle_feedback(self, event: Dict) -> None:
        """Handle feedback received from review agent."""
        try:
            self.current_iteration += 1
            
            if self.current_iteration > self.max_iterations:
                logger.warning("Maximum revision iterations reached")
                await self._notify_max_iterations_reached()
                return
                
            # Get current documentation
            documentation_id = event['data'].get('documentation_id')
            documentation = self.cache.get(f"documentation_{documentation_id}")
            
            if not documentation:
                raise ValueError(f"Documentation not found: {documentation_id}")
                
            # Process feedback
            feedback = await self.feedback_processor.process_feedback(
                event['data']['feedback_items'],
                documentation
            )
            
            # Revise content
            revised_docs = await self.content_reviser.revise_content(
                documentation,
                feedback,
                self.current_iteration
            )
            
            # Submit revised documentation for review
            await self._submit_for_review(revised_docs)
            
        except Exception as e:
            logger.error(f"Error handling feedback: {str(e)}")
            await event_bus.publish({
                "type": "documentation.error",
                "source": "documentation_agent",
                "data": {
                    "error": str(e),
                    "documentation_id": event['data'].get('documentation_id')
                }
            })

    async def _handle_approval(self, event: Dict) -> None:
        """Handle documentation approval."""
        try:
            documentation_id = event['data'].get('documentation_id')
            
            # Get final documentation
            documentation = self.cache.get(f"documentation_{documentation_id}")
            
            if not documentation:
                raise ValueError(f"Documentation not found: {documentation_id}")
                
            # Notify success
            await event_bus.publish({
                "type": "documentation.completed",
                "source": "documentation_agent",
                "data": {
                    "documentation_id": documentation_id,
                    "repository": self.current_repo,
                    "iterations": self.current_iteration,
                    "documentation": documentation.dict()
                }
            })
            
            # Clear current state
            self.current_repo = None
            self.current_iteration = 0
            
        except Exception as e:
            logger.error(f"Error handling approval: {str(e)}")

    async def _handle_rejection(self, event: Dict) -> None:
        """Handle documentation rejection."""
        try:
            documentation_id = event['data'].get('documentation_id')
            reason = event['data'].get('reason', 'Unknown reason')
            
            logger.warning(f"Documentation rejected: {reason}")
            
            # Notify rejection
            await event_bus.publish({
                "type": "documentation.rejected",
                "source": "documentation_agent",
                "data": {
                    "documentation_id": documentation_id,
                    "repository": self.current_repo,
                    "reason": reason,
                    "iterations": self.current_iteration
                }
            })
            
            # Clear current state
            self.current_repo = None
            self.current_iteration = 0
            
        except Exception as e:
            logger.error(f"Error handling rejection: {str(e)}")

    async def _submit_for_review(self, documentation: GeneratedContent) -> None:
        """Submit documentation for review."""
        try:
            # Cache current documentation
            cache_key = f"documentation_{documentation.documentation_version}"
            self.cache.set(cache_key, documentation)
            
            # Submit for review
            await event_bus.publish({
                "type": "documentation.submitted",
                "source": "documentation_agent",
                "data": {
                    "documentation_id": documentation.documentation_version,
                    "repository": self.current_repo,
                    "iteration": self.current_iteration,
                    "documentation": documentation.dict()
                }
            })
            
        except Exception as e:
            logger.error(f"Error submitting for review: {str(e)}")
            raise

    async def _notify_max_iterations_reached(self) -> None:
        """Notify that maximum iterations have been reached."""
        try:
            await event_bus.publish({
                "type": "documentation.max_iterations",
                "source": "documentation_agent",
                "data": {
                    "repository": self.current_repo,
                    "iterations": self.current_iteration
                }
            })
        except Exception as e:
            logger.error(f"Error sending max iterations notification: {str(e)}")

    async def cleanup(self) -> None:
        """Cleanup agent resources."""
        try:
            # Clear current state
            self.current_repo = None
            self.current_iteration = 0
            
            # Clear caches if needed
            # Any other cleanup needed
            
            logger.info("Documentation Agent cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
