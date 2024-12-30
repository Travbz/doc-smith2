"""Tool for coordinating review cycles and managing iterations."""
from typing import Dict, List, Optional, Any
from datetime import datetime
from core.services.logging import setup_logger
from core.services.cache import cache_manager
from ..schemas.feedback import (
    ReviewSession,
    ReviewIteration,
    FeedbackItem,
    ReviewCycle
)
from core.agency.documentation_agent.schemas.generated_content import GeneratedContent

logger = setup_logger(__name__)

class ReviewCoordinator:
    """Coordinates review cycles and manages iterations."""

    def __init__(self):
        """Initialize the review coordinator."""
        self.cache = cache_manager
        self.active_sessions: Dict[str, ReviewSession] = {}
        self.MAX_ITERATIONS = 5
        self.MIN_QUALITY_IMPROVEMENT = 0.05

    async def start_review(
        self,
        documentation: GeneratedContent,
        repository_type: str,
        repository_url: str
    ) -> ReviewCycle:
        """Start a new review cycle."""
        try:
            # Create review sessions for each document
            sessions = {}
            for file_path, content in documentation.files.items():
                session = ReviewSession(
                    session_id=f"session_{len(sessions)}",
                    document_path=file_path,
                    iterations=[],
                    current_iteration=0,
                    status="started",
                    pending_feedback=[],
                    resolved_feedback=[]
                )
                sessions[file_path] = session

            # Initialize review cycle
            cycle = ReviewCycle(
                repository_url=repository_url,
                repository_type=repository_type,
                sessions=sessions,
                reviewers=[],
                overall_status="in_progress",
                completion_rate=0.0,
                quality_trend=[],
                next_actions=["Initial quality assessment", "Technical validation"]
            )

            # Cache the cycle and documentation
            self.cache.set(f"review_cycle_{repository_url}", cycle)
            self.cache.set(f"documentation_{repository_url}", documentation)

            return cycle

        except Exception as e:
            logger.error(f"Error starting review: {str(e)}")
            raise

    async def process_feedback(
        self,
        cycle_id: str,
        feedback_items: List[FeedbackItem],
        quality_score: float
    ) -> Dict[str, Any]:
        """Process feedback for a review iteration."""
        try:
            cycle = await self._get_cycle(cycle_id)
            if not cycle:
                raise ValueError(f"Review cycle not found: {cycle_id}")

            # Update quality trend
            cycle.quality_trend.append(quality_score)

            # Group feedback by document
            feedback_by_doc = {}
            for item in feedback_items:
                doc_path = item.location.get('file', 'general')
                if doc_path not in feedback_by_doc:
                    feedback_by_doc[doc_path] = []
                feedback_by_doc[doc_path].append(item)

            # Update sessions with feedback
            for doc_path, feedback in feedback_by_doc.items():
                if doc_path in cycle.sessions:
                    session = cycle.sessions[doc_path]
                    await self._update_session(session, feedback, quality_score)

            # Update cycle status
            await self._update_cycle_status(cycle)
            
            # Cache updated cycle
            self.cache.set(f"review_cycle_{cycle.repository_url}", cycle)

            return {
                "status": "success",
                "cycle_status": cycle.overall_status,
                "completion_rate": cycle.completion_rate,
                "requires_revision": cycle.overall_status != "completed",
                "documentation_ready": cycle.overall_status == "completed"
            }

        except Exception as e:
            logger.error(f"Error processing feedback: {str(e)}")
            raise

    async def get_documentation(self, repository_url: str) -> Optional[GeneratedContent]:
        """Get the documentation being reviewed."""
        return self.cache.get(f"documentation_{repository_url}")

    async def _update_session(
        self,
        session: ReviewSession,
        feedback: List[FeedbackItem],
        quality_score: float
    ) -> None:
        """Update a review session with new feedback."""
        try:
            # Create new iteration
            iteration = ReviewIteration(
                iteration_number=session.current_iteration + 1,
                reviewer="system",
                feedback_items=feedback,
                status="in_progress",
                quality_score=quality_score,
                timestamp=datetime.utcnow()
            )

            # Update session state
            session.iterations.append(iteration)
            session.current_iteration += 1
            session.pending_feedback = feedback
            
            # Check if we've reached max iterations
            if session.current_iteration >= self.MAX_ITERATIONS:
                session.status = "max_iterations_reached"
            
            # Check if quality is acceptable
            elif quality_score >= 0.85:
                session.status = "completed"
                
            # Check if we're making sufficient progress
            elif len(session.iterations) > 1:
                if quality_score - session.iterations[-2].quality_score < self.MIN_QUALITY_IMPROVEMENT:
                    session.status = "insufficient_progress"
            
        except Exception as e:
            logger.error(f"Error updating session: {str(e)}")
            raise

    async def _update_cycle_status(self, cycle: ReviewCycle) -> None:
        """Update overall cycle status based on sessions."""
        try:
            completed_sessions = sum(1 for s in cycle.sessions.values() 
                                   if s.status == "completed")
            total_sessions = len(cycle.sessions)
            
            cycle.completion_rate = completed_sessions / total_sessions if total_sessions > 0 else 0.0
            
            # Determine overall status
            if all(s.status == "completed" for s in cycle.sessions.values()):
                cycle.overall_status = "completed"
            elif any(s.status == "max_iterations_reached" for s in cycle.sessions.values()):
                cycle.overall_status = "max_iterations_reached"
            elif any(s.status == "insufficient_progress" for s in cycle.sessions.values()):
                cycle.overall_status = "insufficient_progress"
            else:
                cycle.overall_status = "in_progress"
            
            # Update next actions
            cycle.next_actions = await self._determine_next_actions(cycle)
            
        except Exception as e:
            logger.error(f"Error updating cycle status: {str(e)}")
            raise

    async def _determine_next_actions(self, cycle: ReviewCycle) -> List[str]:
        """Determine next actions based on cycle state."""
        actions = []
        
        if cycle.overall_status == "completed":
            actions.append("Create pull request with documentation")
        elif cycle.overall_status == "max_iterations_reached":
            actions.append("Manual review required - max iterations reached")
        elif cycle.overall_status == "insufficient_progress":
            actions.append("Review feedback patterns")
            actions.append("Consider alternative documentation approach")
        else:
            if cycle.completion_rate < 0.5:
                actions.append("Continue initial document reviews")
            else:
                actions.append("Focus on remaining issues")
                actions.append("Re-validate improved sections")
                
        return actions

    async def _get_cycle(self, cycle_id: str) -> Optional[ReviewCycle]:
        """Get a review cycle by ID."""
        return self.cache.get(f"review_cycle_{cycle_id}")

    async def cleanup(self) -> None:
        """Cleanup coordinator resources."""
        self.active_sessions.clear()
