"""Agent responsible for reviewing documentation."""
from typing import Dict, Any, Optional
from core.services.logging import setup_logger
from core.services.event_bus import Event
from core.agency.base_agent import BaseAgent
from core.agency.documentation_agent.schemas.generated_content import GeneratedContent

logger = setup_logger(__name__)

class ReviewAgent(BaseAgent):
    """Agent responsible for reviewing documentation."""

    def __init__(self, agency):
        """Initialize the review agent."""
        super().__init__(agency, agent_type="review")
        self.active_reviews = {}

    async def _initialize_tools(self) -> None:
        """Initialize review tools."""
        # No tools needed for the simplified review process
        pass

    async def initialize(self) -> None:
        """Initialize the review agent."""
        await super().initialize()
        await self._initialize_tools()
        await self.register_event_handler("documentation.submitted", self._handle_documentation_submitted)

    async def _handle_documentation_submitted(self, event: Dict) -> None:
        """Handle documentation submitted for review."""
        try:
            documentation = event.get("documentation")
            repo_path = event.get("repo_path")
            iteration = event.get("iteration", 0)

            if not documentation or not repo_path:
                logger.error("Missing required data in documentation.submitted event")
                return

            # Store active review
            review_id = f"review_{repo_path}_{iteration}"
            self.active_reviews[review_id] = {
                "documentation": documentation,
                "repo_path": repo_path,
                "iteration": iteration,
                "quality_trend": [],
                "overall_status": "pending"
            }

            # Review documentation
            review_result = await self._review_documentation(documentation)
            self.active_reviews[review_id]["quality_trend"].append(review_result["quality_score"])

            if review_result["quality_score"] >= 0.8:
                # Documentation meets quality standards
                self.active_reviews[review_id]["overall_status"] = "approved"
                await self._publish_event(
                    "documentation.ready",
                    {
                        "documentation": documentation,
                        "repository_url": repo_path,
                        "review_cycle": self.active_reviews[review_id]
                    }
                )
            else:
                # Documentation needs improvement
                self.active_reviews[review_id]["overall_status"] = "needs_improvement"
                await self._publish_event(
                    "review.feedback_generated",
                    {
                        "documentation": documentation,
                        "repository_url": repo_path,
                        "feedback": review_result["feedback"],
                        "quality_score": review_result["quality_score"]
                    }
                )

        except Exception as e:
            logger.error(f"Error handling documentation submitted: {str(e)}")
            await self._publish_event(
                "review.failed",
                {
                    "repository_url": repo_path,
                    "error": str(e)
                }
            )

    async def _review_documentation(self, documentation: GeneratedContent) -> Dict[str, Any]:
        """Review documentation and provide feedback."""
        try:
            quality_score = 1.0  # Start with perfect score
            feedback = []

            # Check for required files
            if not documentation.files:
                quality_score -= 0.3
                feedback.append("Documentation is missing required files")

            # Check content quality for each file
            for file_path, doc_file in documentation.files.items():
                if not doc_file.content:
                    quality_score -= 0.2
                    feedback.append(f"Empty content in {file_path}")
                    continue

                # Check content length
                if len(doc_file.content) < 100:
                    quality_score -= 0.1
                    feedback.append(f"Content in {file_path} is too short")

                # Check for placeholders
                if "{" in doc_file.content and "}" in doc_file.content:
                    quality_score -= 0.1
                    feedback.append(f"Unresolved placeholders in {file_path}")

                # Check sections
                if not doc_file.sections:
                    quality_score -= 0.1
                    feedback.append(f"No sections defined in {file_path}")

            # Ensure quality score is between 0 and 1
            quality_score = max(0.0, min(1.0, quality_score))

            return {
                "quality_score": quality_score,
                "feedback": feedback
            }

        except Exception as e:
            logger.error(f"Error reviewing documentation: {str(e)}")
            return {
                "quality_score": 0.0,
                "feedback": [f"Review failed: {str(e)}"]
            }

    async def cleanup(self) -> None:
        """Cleanup agent resources."""
        await super().cleanup()
        self.active_reviews.clear()
