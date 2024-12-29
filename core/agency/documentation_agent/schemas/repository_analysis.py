"""Schema for repository analysis results."""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class FileInfo(BaseModel):
    """Information about a specific file in the repository."""
    path: str = Field(..., description="Path to the file relative to repository root")
    type: str = Field(..., description="File type/extension")
    size: int = Field(..., description="File size in bytes")
    last_modified: str = Field(..., description="Last modification timestamp")

class DirectoryInfo(BaseModel):
    """Information about a directory in the repository."""
    path: str = Field(..., description="Path to directory relative to repository root")
    files: List[FileInfo] = Field(default_factory=list, description="Files in this directory")
    subdirectories: List[str] = Field(default_factory=list, description="Subdirectory names")

class RepositoryPatterns(BaseModel):
    """Detected patterns in the repository."""
    spring_boot_patterns: List[str] = Field(default_factory=list, description="Spring Boot related files/patterns")
    nginx_patterns: List[str] = Field(default_factory=list, description="NGINX related files/patterns")
    bounded_context_patterns: List[str] = Field(default_factory=list, description="Helm/Terraform related patterns")
    python_patterns: List[str] = Field(default_factory=list, description="Python related files/patterns")
    unknown_patterns: List[str] = Field(default_factory=list, description="Unrecognized patterns")

class RepositoryAnalysis(BaseModel):
    """Complete repository analysis results."""
    repository_type: str = Field(..., description="Detected repository type")
    root_directory: DirectoryInfo = Field(..., description="Repository root directory info")
    detected_patterns: RepositoryPatterns = Field(..., description="Detected repository patterns")
    languages: Dict[str, int] = Field(default_factory=dict, description="Languages and their line counts")
    primary_language: Optional[str] = Field(None, description="Primary repository language")
    total_files: int = Field(..., description="Total number of files")
    total_size: int = Field(..., description="Total repository size in bytes")
    analysis_timestamp: str = Field(..., description="Timestamp of analysis")
