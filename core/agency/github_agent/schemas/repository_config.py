"""Schema for GitHub repository configuration and operations."""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime

class RepositoryRef(BaseModel):
    """Reference to a GitHub repository."""
    owner: str = Field(..., description="Repository owner (user or organization)")
    name: str = Field(..., description="Repository name")
    full_name: str = Field(..., description="Full repository name (owner/name)")
    url: HttpUrl = Field(..., description="Repository URL")
    default_branch: str = Field("main", description="Default branch name")
    
class LocalRepositoryConfig(BaseModel):
    """Configuration for local repository clone."""
    local_path: str = Field(..., description="Local path where repository is cloned")
    remote_url: HttpUrl = Field(..., description="Remote repository URL")
    current_branch: str = Field(..., description="Currently checked out branch")
    base_branch: str = Field(..., description="Base branch for operations")
    last_synced: datetime = Field(..., description="Last sync with remote")
    
class BranchConfig(BaseModel):
    """Configuration for branch operations."""
    name: str = Field(..., description="Branch name")
    base_branch: str = Field(..., description="Base branch to create from")
    tracking: bool = Field(True, description="Whether to track remote branch")
    protected: bool = Field(False, description="Whether branch is protected")
    
class RepositoryOperations(BaseModel):
    """Configuration for repository operations."""
    clone_depth: Optional[int] = Field(None, description="Depth for shallow clones")
    include_submodules: bool = Field(False, description="Whether to include submodules")
    cleanup_after: bool = Field(True, description="Whether to cleanup after operations")
    timeout: int = Field(300, description="Operation timeout in seconds")
    
class RepositoryConfig(BaseModel):
    """Complete repository configuration."""
    repository: RepositoryRef = Field(..., description="Repository reference")
    local_config: LocalRepositoryConfig = Field(..., description="Local repository configuration")
    branch_config: BranchConfig = Field(..., description="Branch configuration")
    operations: RepositoryOperations = Field(
        default_factory=RepositoryOperations,
        description="Repository operations configuration"
    )
    credentials: Optional[Dict[str, str]] = Field(None, description="Repository credentials if needed")
    workspace_config: Optional[Dict[str, str]] = Field(None, description="Workspace-specific configuration")
