"""Schema for generated documentation content."""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class DocumentSection(BaseModel):
    """Section of a documentation file."""
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content")
    level: int = Field(1, description="Header level (1-6)")
    order: int = Field(..., description="Order in the document")

class DocumentMetadata(BaseModel):
    """Metadata for a documentation file."""
    generated_at: datetime = Field(default_factory=datetime.now)
    generator_version: str = Field(..., description="Version of the documentation generator")
    template_id: Optional[str] = Field(None, description="ID of template used")
    repository_type: str = Field(..., description="Type of repository documented")
    documentation_standard: str = Field(..., description="Documentation standard followed")

class DocumentFile(BaseModel):
    """Individual documentation file."""
    path: str = Field(..., description="File path relative to documentation root")
    content: str = Field(..., description="Full file content")
    sections: List[DocumentSection] = Field(..., description="Document sections")
    metadata: DocumentMetadata = Field(..., description="Document metadata")
    requires_review: bool = Field(True, description="Whether this file needs review")
    validation_status: Optional[str] = Field(None, description="Current validation status")

class GeneratedContent(BaseModel):
    """Complete generated documentation package."""
    id: str = Field(..., description="Unique identifier for this documentation package")
    repository_url: str = Field(..., description="Source repository URL")
    repository_type: str = Field(..., description="Repository type")
    files: Dict[str, DocumentFile] = Field(..., description="Generated documentation files")
    generation_timestamp: datetime = Field(default_factory=datetime.now)
    documentation_version: str = Field(..., description="Documentation version")
    complete: bool = Field(False, description="Whether documentation is complete")
    requires_review: bool = Field(True, description="Whether package needs review")
