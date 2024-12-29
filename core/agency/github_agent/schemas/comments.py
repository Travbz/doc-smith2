"""Schema for GitHub comments and review feedback."""
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime

class CommentLocation(BaseModel):
    """Location information for a comment."""
    file: Optional[str] = Field(None, description="File being commented on")
    line: Optional[int] = Field(None, description="Line number for the comment")
    position: Optional[int] = Field(None, description="Position in the diff")
    commit_id: Optional[str] = Field(None, description="Commit SHA for the comment")

class CommentContent(BaseModel):
    """Content of a comment."""
    body: str = Field(..., description="Comment text")
    type: str = Field("comment", description="Comment type (comment/suggestion/question)")
    resolve_type: Optional[str] = Field(None, description="How to resolve (fix/update/consider)")
    code_snippet: Optional[str] = Field(None, description="Related code if any")
    suggestions: Optional[List[str]] = Field(None, description="Suggested changes")

class ReviewComment(BaseModel):
    """A comment as part of a review."""
    location: CommentLocation = Field(..., description="Comment location")
    content: CommentContent = Field(..., description="Comment content")
    id: Optional[int] = Field(None, description="Comment ID if existing")
    in_reply_to: Optional[int] = Field(None, description="ID of parent comment if reply")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

class Review(BaseModel):
    """A complete review with comments."""
    comments: List[ReviewComment] = Field(default_factory=list, description="Review comments")
    summary: str = Field(..., description="Review summary")
    event: str = Field(..., description="Review event (APPROVE/REQUEST_CHANGES/COMMENT)")
    commit_id: str = Field(..., description="Commit SHA being reviewed")
    
class CommentThread(BaseModel):
    """A thread of related comments."""
    original_comment: ReviewComment = Field(..., description="Original comment")
    replies: List[ReviewComment] = Field(default_factory=list, description="Reply comments")
    status: str = Field("open", description="Thread status (open/resolved)")
    resolution: Optional[str] = Field(None, description="Resolution if resolved")

class CommentOperation(BaseModel):
    """Operation to perform with comments."""
    operation_type: str = Field(..., description="Operation type (create/update/delete)")
    pull_request_number: int = Field(..., description="PR number")
    repository: str = Field(..., description="Repository full name")
    comments: Union[ReviewComment, Review, List[ReviewComment]] = Field(
        ..., 
        description="Comments to operate on"
    )
    update_related: bool = Field(False, description="Whether to update related comments")
