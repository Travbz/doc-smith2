"""Schema for review feedback and iteration management."""
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime

class FeedbackItem(BaseModel):
    """Individual piece of feedback."""
    item_id: str = Field(..., description="Unique feedback identifier")
    type: str = Field(..., description="Feedback type (issue/suggestion/praise)")
    category: str = Field(..., description="Feedback category")
    message: str = Field(..., description="Feedback message")
    location: Dict[str, Union[str, int]] = Field(..., description="Location in documentation")
    priority: str = Field(..., description="Feedback priority (high/medium/low)")
    requires_changes: bool = Field(..., description="Whether changes are required")
    suggested_changes: Optional[str] = Field(None, description="Suggested changes if any")

class ReviewIteration(BaseModel):
    """Single review iteration."""
    iteration_number: int = Field(..., description="Iteration number")
    reviewer: str = Field(..., description="Reviewer identifier")
    timestamp: datetime = Field(default_factory=datetime.now)
    feedback_items: List[FeedbackItem] = Field(..., description="Feedback from this iteration")
    status: str = Field(..., description="Iteration status")
    resolution: Optional[str] = Field(None, description="Resolution if completed")

class FeedbackResponse(BaseModel):
    """Response to feedback items."""
    feedback_id: str = Field(..., description="ID of feedback being responded to")
    response: str = Field(..., description="Response message")
    changes_made: Optional[str] = Field(None, description="Description of changes made")
    status: str = Field(..., description="Response status")
    resolution_type: Optional[str] = Field(None, description="How feedback was resolved")

class ReviewSession(BaseModel):
    """Complete review session for a document."""
    session_id: str = Field(..., description="Unique session identifier")
    document_path: str = Field(..., description="Path to reviewed document")
    iterations: List[ReviewIteration] = Field(..., description="Review iterations")
    current_iteration: int = Field(..., description="Current iteration number")
    status: str = Field(..., description="Session status")
    pending_feedback: List[FeedbackItem] = Field(default_factory=list, description="Unresolved feedback")
    resolved_feedback: List[FeedbackItem] = Field(default_factory=list, description="Resolved feedback")

class ReviewCycle(BaseModel):
    """Complete review cycle for a documentation package."""
    repository_url: str = Field(..., description="Source repository URL")
    repository_type: str = Field(..., description="Repository type")
    start_time: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)
    sessions: Dict[str, ReviewSession] = Field(..., description="Review sessions by document")
    reviewers: List[str] = Field(..., description="Participating reviewers")
    overall_status: str = Field(..., description="Overall review status")
    completion_rate: float = Field(0.0, description="Review completion percentage")
    quality_trend: List[float] = Field(default_factory=list, description="Quality scores over iterations")
    cycle_summary: Optional[str] = Field(None, description="Summary of review cycle")
    next_actions: List[str] = Field(default_factory=list, description="Required next actions")