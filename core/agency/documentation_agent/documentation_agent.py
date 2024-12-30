"""Documentation Agent for analyzing repositories and generating documentation."""
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

from core.services.logging import setup_logger
from core.services.event_bus import event_bus
from core.services.cache import cache_manager
from core.services.error_handling.error_handler import (
    with_error_handling,
    ErrorCategory,
    ErrorSeverity,
    DocSmithError
)
from core.agency.base_agent import BaseAgent

from .tools.repository_analyzer import RepositoryAnalyzer
from .tools.standard_selector import StandardSelector
from .tools.content_generator import ContentGenerator
from .tools.template_manager import TemplateManager
from .tools.feedback_processor import FeedbackProcessor
from .tools.content_reviser import ContentReviser

from .schemas.generated_content import GeneratedContent
from .schemas.documentation_standard import DocumentationStandard

logger = setup_logger(__name__)

class DocumentationError(DocSmithError):
    """Specific error class for documentation-related issues."""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
        super().__init__(
            message,
            category=ErrorCategory.DOC_GEN,
            severity=severity,
            recovery_hint="Try adjusting documentation parameters or reviewing input content"
        )

class DocumentationAgent(BaseAgent):
    """Agent responsible for documentation generation and management."""

    def __init__(self, agency):
        """Initialize the Documentation Agent."""
        super().__init__(agency, "documentation")
        self.current_repo: Optional[str] = None
        self.current_iteration: int = 0
        self.max_iterations: int = 5

    async def _initialize_tools(self) -> None:
        """Initialize documentation tools."""
        self._tools = {
            'repo_analyzer': RepositoryAnalyzer(),
            'standard_selector': StandardSelector(),
            'content_generator': ContentGenerator(),
            'template_manager': TemplateManager(),
            'feedback_processor': FeedbackProcessor(),
            'content_reviser': ContentReviser()
        }

    async def _subscribe_to_events(self) -> None:
        """Set up event subscriptions."""
        await self.register_event_handler("review.feedback_generated", self._handle_feedback)
        await self.register_event_handler("review.approved", self._handle_approval)
        await self.register_event_handler("review.rejected", self._handle_rejection)

    async def initialize(self) -> None:
        """Initialize the agent and its resources."""
        logger.info("Initializing Documentation Agent")
        await super().initialize()
        await self._subscribe_to_events()

    @with_error_handling(ErrorCategory.DOC_GEN, ErrorSeverity.HIGH)
    async def generate_documentation(
        self,
        repo_path: str,
        repo_name: Optional[str] = None,
        custom_rules: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Generate documentation for a repository.
        
        Args:
            repo_path: Local path to the cloned repository
            repo_name: Repository name (owner/repo format)
            custom_rules: Optional custom documentation rules
        """
        if not self.is_initialized:
            raise DocumentationError("Agent not initialized", ErrorSeverity.HIGH)

        self.current_repo = repo_name or repo_path
        self.current_iteration = 0

        try:
            # Get tools
            repo_analyzer = self.get_tool('repo_analyzer')
            if not repo_analyzer:
                raise DocumentationError("Repository analyzer tool not found", ErrorSeverity.HIGH)

            standard_selector = self.get_tool('standard_selector')
            if not standard_selector:
                raise DocumentationError("Standard selector tool not found", ErrorSeverity.HIGH)

            content_generator = self.get_tool('content_generator')
            if not content_generator:
                raise DocumentationError("Content generator tool not found", ErrorSeverity.HIGH)
            
            # Analyze repository
            analysis = await self.execute_task(
                'analyze_repo',
                repo_analyzer.analyze(repo_path)
            )
            if not analysis:
                raise DocumentationError("Repository analysis failed", ErrorSeverity.HIGH)
            
            # Select documentation standard
            standard = await self.execute_task(
                'select_standard',
                standard_selector.select(analysis, custom_rules)
            )
            if not standard:
                raise DocumentationError("Documentation standard selection failed", ErrorSeverity.HIGH)
            
            # Generate initial documentation
            try:
                documentation = await self.execute_task(
                    'generate_content',
                    content_generator.generate(analysis, standard)
                )
                if not documentation:
                    raise DocumentationError("Documentation generation failed", ErrorSeverity.HIGH)
            except Exception as e:
                logger.error(f"Error generating documentation: {str(e)}")
                raise DocumentationError(
                    f"Documentation generation failed: {str(e)}",
                    ErrorSeverity.HIGH
                ) from e
            
            # Submit for review
            await self._submit_for_review(documentation)
            
            return {"status": "submitted_for_review", "doc_id": documentation.id}
            
        except Exception as e:
            logger.error(f"Documentation generation error: {str(e)}")
            raise DocumentationError(
                f"Failed to generate documentation: {str(e)}",
                ErrorSeverity.HIGH
            ) from e

    @with_error_handling(ErrorCategory.DOC_GEN, ErrorSeverity.MEDIUM)
    async def _handle_feedback(self, event: Dict) -> None:
        """Handle feedback from review agent."""
        if not self.current_repo:
            raise DocumentationError("No active documentation process", ErrorSeverity.LOW)
            
        try:
            feedback_processor = self.get_tool('feedback_processor')
            content_reviser = self.get_tool('content_reviser')
            
            # Process feedback
            revision_plan = await self.execute_task(
                'process_feedback',
                feedback_processor.process(event['feedback'])
            )
            
            # Check iteration limit
            if self.current_iteration >= self.max_iterations:
                await self._notify_max_iterations_reached()
                return
                
            self.current_iteration += 1
            
            # Generate revised content
            revised_content = await self.execute_task(
                'revise_content',
                content_reviser.revise(revision_plan)
            )
            
            # Submit revised version
            await self._submit_for_review(revised_content)
            
        except Exception as e:
            raise DocumentationError(
                f"Failed to handle feedback: {str(e)}",
                ErrorSeverity.MEDIUM
            ) from e

    @with_error_handling(ErrorCategory.DOC_GEN, ErrorSeverity.LOW)
    async def _handle_approval(self, event: Dict) -> None:
        """Handle documentation approval."""
        if not self.current_repo:
            raise DocumentationError("No active documentation process", ErrorSeverity.LOW)
            
        try:
            # Publish success event
            await self._publish_event("documentation.completed", {
                "repo_path": self.current_repo,
                "iterations": self.current_iteration,
                "documentation_id": event['documentation_id']
            })
            
            # Reset state
            self.current_repo = None
            self.current_iteration = 0
            
        except Exception as e:
            raise DocumentationError(
                f"Failed to handle approval: {str(e)}",
                ErrorSeverity.LOW
            ) from e

    @with_error_handling(ErrorCategory.DOC_GEN, ErrorSeverity.MEDIUM)
    async def _handle_rejection(self, event: Dict) -> None:
        """Handle documentation rejection."""
        if not self.current_repo:
            raise DocumentationError("No active documentation process", ErrorSeverity.LOW)
            
        try:
            if self.current_iteration >= self.max_iterations:
                await self._notify_max_iterations_reached()
                return
                
            # Process rejection as feedback
            await self._handle_feedback({
                "feedback": event['rejection_reason'],
                "severity": "high"
            })
            
        except Exception as e:
            raise DocumentationError(
                f"Failed to handle rejection: {str(e)}",
                ErrorSeverity.MEDIUM
            ) from e

    @with_error_handling(ErrorCategory.DOC_GEN, ErrorSeverity.MEDIUM)
    async def _submit_for_review(self, documentation: GeneratedContent) -> None:
        """Submit documentation for review."""
        try:
            await self._publish_event("documentation.submitted", {
                "documentation": documentation,
                "repo_path": self.current_repo,
                "iteration": self.current_iteration
            })
        except Exception as e:
            raise DocumentationError(
                f"Failed to submit for review: {str(e)}",
                ErrorSeverity.MEDIUM
            ) from e

    @with_error_handling(ErrorCategory.DOC_GEN, ErrorSeverity.HIGH)
    async def _notify_max_iterations_reached(self) -> None:
        """Handle max iterations reached scenario."""
        try:
            await self._publish_event("documentation.max_iterations", {
                "repo_path": self.current_repo,
                "iterations": self.current_iteration
            })
            
            self.current_repo = None
            self.current_iteration = 0
            
        except Exception as e:
            raise DocumentationError(
                f"Failed to notify max iterations: {str(e)}",
                ErrorSeverity.HIGH
            ) from e

    async def cleanup(self) -> None:
        """Cleanup agent resources."""
        try:
            self.current_repo = None
            self.current_iteration = 0
            await super().cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            raise DocumentationError(
                f"Failed to cleanup: {str(e)}",
                ErrorSeverity.LOW
            ) from e
