"""Schema for documentation standards and guidelines."""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class DocumentationRule(BaseModel):
    """Individual documentation rule or guideline."""
    rule_id: str = Field(..., description="Unique identifier for the rule")
    description: str = Field(..., description="Description of the rule")
    required: bool = Field(default=True, description="Whether this rule is required")
    applies_to: List[str] = Field(..., description="File types/patterns this rule applies to")
    example: Optional[str] = Field(None, description="Example of correct documentation")

class TemplateVariable(BaseModel):
    """Variable that can be used in documentation templates."""
    name: str = Field(..., description="Variable name")
    description: str = Field(..., description="Variable description")
    required: bool = Field(default=True, description="Whether this variable is required")
    default: Optional[str] = Field(None, description="Default value if any")

class DocumentationTemplate(BaseModel):
    """Template for generating documentation."""
    template_id: str = Field(..., description="Unique identifier for the template")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    content: str = Field(..., description="Template content with variables")
    variables: List[TemplateVariable] = Field(..., description="Template variables")
    file_name: str = Field(..., description="Target file name (can include variables)")
    applies_to: List[str] = Field(..., description="Repository types this template applies to")

class DocumentationStandard(BaseModel):
    """Standard for documentation generation."""
    name: str = Field(..., description="Standard name")
    description: str = Field(..., description="Standard description")
    version: str = Field(..., description="Standard version")
    repository_type: str = Field(..., description="Type of repository this standard applies to")
    required_files: List[str] = Field(..., description="Required files for this standard")
    optional_files: List[str] = Field(default_factory=list, description="Optional files for this standard")
    file_structure: Dict[str, str] = Field(default_factory=dict, description="Expected file structure")
    templates: List[DocumentationTemplate] = Field(..., description="Documentation templates")
    rules: List[DocumentationRule] = Field(..., description="Documentation rules")
