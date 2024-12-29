"""Schema for GitHub pull request operations."""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime

class CommitInfo(BaseModel):
    """Information about a commit."""
    sha: str = Field(..., description="Commit SHA")
    message: str = Field(..., description="Commit message")
    author: str = Field(..., description="Commit author")
    timestamp: datetime = Field(..., description="Commit timestamp")
    
class FileChange(BaseModel):
    """Information about a changed file."""
    path: str = Field(..., description="File path")
    content: str = Field(..., description="File content")
    sha: Optional[str] = Field(None, description="File SHA if existing")
    operation: str = Field(..., description="Change operation (create/update/delete)")
    
class ReviewerInfo(BaseModel):
    """Information about a PR reviewer."""
    username: str = Field(..., description="Reviewer username")
    role: str = Field("reviewer", description="Reviewer role")
    required: bool = Field(False, description="Whether review is required")
    
class PullRequestConfig(BaseModel):
    """Configuration for pull request creation/update."""
    title: str = Field(..., description="Pull request title")
    body: str = Field(..., description="Pull request description")
    base_branch: str = Field(..., description="Base branch")
    head_branch: str = Field(..., description="Head branch")
    draft: bool = Field(False, description="Whether PR is draft")
    maintainer_can_modify: bool = Field(True, description="Allow maintainer modifications")
    reviewers: List[ReviewerInfo] = Field(default_factory=list, description="PR reviewers")
    labels: List[str] = Field(default_factory=list, description="PR labels")
    
class PullRequestOperation(BaseModel):
    """Complete pull request operation details."""
    repository: str = Field(..., description="Repository full name")
    config: PullRequestConfig = Field(..., description="Pull request configuration")
    files: List[FileChange] = Field(..., description="Files to change")
    commits: List[CommitInfo] = Field(default_factory=list, description="Commits in the PR")
    operation_type: str = Field(..., description="Operation type (create/update)")
    auto_merge: bool = Field(False, description="Whether to enable auto-merge")
    dependencies: Optional[List[str]] = Field(None, description="Dependencies on other PRs")
    
class PullRequestStatus(BaseModel):
    """Status of a pull request."""
    number: int = Field(..., description="PR number")
    url: HttpUrl = Field(..., description="PR URL")
    state: str = Field(..., description="PR state")
    mergeable: bool = Field(..., description="Whether PR is mergeable")
    merged: bool = Field(False, description="Whether PR is merged")
    reviews: List[Dict[str, str]] = Field(default_factory=list, description="Review status")
    checks: List[Dict[str, str]] = Field(default_factory=list, description="Check status")
    last_updated: datetime = Field(..., description="Last update timestamp")
