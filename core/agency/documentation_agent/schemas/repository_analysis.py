"""Schema for repository analysis results."""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class FileInfo(BaseModel):
    """Information about a specific file in the repository."""
    name: str = Field(..., description="Name of the file")
    path: str = Field(..., description="Path to the file relative to repository root")
    type: str = Field(..., description="File type/extension")
    size: int = Field(..., description="File size in bytes")
    last_modified: str = Field(..., description="Last modification timestamp")

class DirectoryInfo(BaseModel):
    """Information about a directory in the repository."""
    name: str = Field(..., description="Name of the directory")
    path: str = Field(..., description="Path to directory relative to repository root")
    files: List[FileInfo] = Field(default_factory=list, description="Files in this directory")
    subdirectories: List[str] = Field(default_factory=list, description="Names of subdirectories")
    subdirectory_info: List["DirectoryInfo"] = Field(default_factory=list, description="Detailed information about subdirectories")

DirectoryInfo.model_rebuild()

class RepositoryPatterns(BaseModel):
    """Detected patterns in the repository."""
    repository_type: str = Field(..., description="Type of repository detected")
    common_files: List[str] = Field(default_factory=list, description="Common files found for the repository type")
    detected_languages: Dict[str, int] = Field(default_factory=dict, description="Programming languages detected and their line counts")

class RepositoryAnalysis(BaseModel):
    """Complete repository analysis results."""
    repository_path: str = Field(..., description="Path to the repository")
    repository_type: str = Field(..., description="Detected repository type")
    structure: DirectoryInfo = Field(..., description="Repository directory structure")
    patterns: RepositoryPatterns = Field(..., description="Detected repository patterns")
