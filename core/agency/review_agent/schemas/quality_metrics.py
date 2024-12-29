"""Schema for documentation quality metrics and assessment."""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, confloat
from datetime import datetime

class ContentMetrics(BaseModel):
    """Metrics for documentation content quality."""
    readability_score: confloat(ge=0, le=1) = Field(..., description="Readability score")
    technical_accuracy: confloat(ge=0, le=1) = Field(..., description="Technical accuracy score")
    completeness: confloat(ge=0, le=1) = Field(..., description="Completeness score")
    consistency: confloat(ge=0, le=1) = Field(..., description="Consistency score")
    example_quality: confloat(ge=0, le=1) = Field(..., description="Quality of examples")
    
class StructureMetrics(BaseModel):
    """Metrics for documentation structure."""
    organization: confloat(ge=0, le=1) = Field(..., description="Organization score")
    formatting: confloat(ge=0, le=1) = Field(..., description="Formatting score")
    hierarchy: confloat(ge=0, le=1) = Field(..., description="Hierarchy clarity")
    linking: confloat(ge=0, le=1) = Field(..., description="Internal/external linking")
    
class CodeMetrics(BaseModel):
    """Metrics for code examples and snippets."""
    syntax_correctness: confloat(ge=0, le=1) = Field(..., description="Syntax correctness")
    style_consistency: confloat(ge=0, le=1) = Field(..., description="Style consistency")
    example_completeness: confloat(ge=0, le=1) = Field(..., description="Example completeness")
    documentation_match: confloat(ge=0, le=1) = Field(..., description="Match with documentation")

class SectionMetrics(BaseModel):
    """Quality metrics for a documentation section."""
    section_path: str = Field(..., description="Path to the section in the document")
    content: ContentMetrics = Field(..., description="Content quality metrics")
    structure: StructureMetrics = Field(..., description="Structure quality metrics")
    code: Optional[CodeMetrics] = Field(None, description="Code quality metrics if applicable")
    section_score: confloat(ge=0, le=1) = Field(..., description="Overall section score")
    issues_found: List[str] = Field(default_factory=list, description="Issues found in section")

class DocumentMetrics(BaseModel):
    """Quality metrics for an entire document."""
    file_path: str = Field(..., description="Path to the documentation file")
    sections: Dict[str, SectionMetrics] = Field(..., description="Section-wise metrics")
    overall_content: ContentMetrics = Field(..., description="Overall content metrics")
    overall_structure: StructureMetrics = Field(..., description="Overall structure metrics")
    overall_code: Optional[CodeMetrics] = Field(None, description="Overall code metrics")
    document_score: confloat(ge=0, le=1) = Field(..., description="Overall document score")
    critical_issues: List[str] = Field(default_factory=list, description="Critical issues found")
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")

class QualityAssessment(BaseModel):
    """Complete quality assessment for a documentation package."""
    repository_url: str = Field(..., description="Source repository URL")
    repository_type: str = Field(..., description="Repository type")
    documents: Dict[str, DocumentMetrics] = Field(..., description="Document-wise metrics")
    overall_score: confloat(ge=0, le=1) = Field(..., description="Overall documentation score")
    assessment_timestamp: datetime = Field(default_factory=datetime.now)
    meets_standards: bool = Field(..., description="Whether documentation meets quality standards")
    required_revisions: List[str] = Field(default_factory=list, description="Required revisions")
    optional_improvements: List[str] = Field(default_factory=list, description="Optional improvements")
