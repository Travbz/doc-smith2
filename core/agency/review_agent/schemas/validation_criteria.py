"""Schema for technical validation criteria and results."""
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime

class ValidationRule(BaseModel):
    """Individual validation rule."""
    rule_id: str = Field(..., description="Unique rule identifier")
    description: str = Field(..., description="Rule description")
    severity: str = Field(..., description="Rule severity (error/warning/info)")
    category: str = Field(..., description="Rule category")
    applies_to: List[str] = Field(..., description="Applicable repository types")
    validation_type: str = Field(..., description="Type of validation (syntax/content/structure)")

class TechnicalRequirement(BaseModel):
    """Technical requirement for validation."""
    requirement_id: str = Field(..., description="Unique requirement identifier")
    description: str = Field(..., description="Requirement description")
    validation_rules: List[ValidationRule] = Field(..., description="Associated validation rules")
    repository_types: List[str] = Field(..., description="Applicable repository types")
    required: bool = Field(True, description="Whether requirement is mandatory")

class ValidationContext(BaseModel):
    """Context for validation execution."""
    repository_type: str = Field(..., description="Repository type")
    file_path: str = Field(..., description="File being validated")
    content_type: str = Field(..., description="Content type (code/docs/config)")
    requirements: List[TechnicalRequirement] = Field(..., description="Applied requirements")
    validation_depth: str = Field("full", description="Validation depth (quick/full)")

class ValidationIssue(BaseModel):
    """Issue found during validation."""
    rule_id: str = Field(..., description="Rule that found the issue")
    severity: str = Field(..., description="Issue severity")
    message: str = Field(..., description="Issue description")
    location: Dict[str, Union[str, int]] = Field(..., description="Issue location")
    suggested_fix: Optional[str] = Field(None, description="Suggested fix if available")
    context: Optional[str] = Field(None, description="Relevant context")

class ValidationResult(BaseModel):
    """Result of validation for a single file."""
    file_path: str = Field(..., description="Validated file path")
    issues: List[ValidationIssue] = Field(default_factory=list, description="Found issues")
    pass_rate: float = Field(..., description="Percentage of passed validations")
    error_count: int = Field(0, description="Number of errors")
    warning_count: int = Field(0, description="Number of warnings")
    info_count: int = Field(0, description="Number of infos")
    validation_time: float = Field(..., description="Time taken for validation")

class TechnicalValidation(BaseModel):
    """Complete technical validation results."""
    repository_url: str = Field(..., description="Source repository URL")
    repository_type: str = Field(..., description="Repository type")
    validation_timestamp: datetime = Field(default_factory=datetime.now)
    results: Dict[str, ValidationResult] = Field(..., description="Validation results by file")
    overall_pass_rate: float = Field(..., description="Overall validation pass rate")
    blocking_issues: List[ValidationIssue] = Field(default_factory=list, description="Blocking issues")
    non_blocking_issues: List[ValidationIssue] = Field(default_factory=list, description="Non-blocking issues")
    validation_summary: str = Field(..., description="Summary of validation results")
    next_steps: List[str] = Field(..., description="Recommended next steps")
