"""Tool for validating technical accuracy of documentation."""
from typing import Dict, List, Optional
from datetime import datetime
from core.services.logging import setup_logger
from core.services.cache import cache_manager
from ..schemas.validation_criteria import (
    ValidationRule,
    TechnicalRequirement,
    ValidationContext,
    ValidationIssue,
    ValidationResult,
    TechnicalValidation
)
from core.agency.documentation_agent.schemas.generated_content import GeneratedContent, DocumentFile

logger = setup_logger(__name__)

class TechnicalValidator:
    """Validates technical accuracy of documentation."""

    def __init__(self):
        """Initialize the technical validator."""
        self.cache = cache_manager

    async def validate_documentation(
        self,
        documentation: GeneratedContent,
        repository_type: str
    ) -> TechnicalValidation:
        """Validate documentation for technical accuracy.
        
        Args:
            documentation: Generated documentation content
            repository_type: Type of repository
            
        Returns:
            Technical validation results
        """
        try:
            validation_results: Dict[str, ValidationResult] = {}
            start_time = datetime.now()

            for file_path, doc_file in documentation.files.items():
                # Create validation context
                context = ValidationContext(
                    repository_type=repository_type,
                    file_path=file_path,
                    content_type=self._determine_content_type(file_path),
                    requirements=await self._load_requirements(repository_type),
                    validation_depth="full",
                    start_time=start_time
                )

                # Validate file
                result = await self._validate_file(doc_file.content, context)
                validation_results[file_path] = result

            # Calculate overall validation metrics
            total_files = len(validation_results)
            total_issues = sum(r.error_count + r.warning_count for r in validation_results.values())
            overall_pass_rate = sum(r.pass_rate for r in validation_results.values()) / total_files

            return TechnicalValidation(
                repository_type=repository_type,
                validation_timestamp=datetime.now(),
                results=validation_results,
                overall_pass_rate=overall_pass_rate,
                blocking_issues=await self._collect_blocking_issues(validation_results),
                non_blocking_issues=await self._collect_non_blocking_issues(validation_results),
                validation_summary=await self._generate_summary(validation_results),
                next_steps=await self._determine_next_steps(validation_results)
            )

        except Exception as e:
            logger.error(f"Error validating documentation: {str(e)}")
            raise

    async def _validate_file(
        self,
        content: str,
        context: ValidationContext
    ) -> ValidationResult:
        """Validate a single documentation file."""
        issues: List[ValidationIssue] = []
        
        # Technical accuracy checks
        issues.extend(await self._check_technical_accuracy(content, context))
        
        # Code examples validation
        issues.extend(await self._validate_code_examples(content, context))
        
        # Completeness checks
        issues.extend(await self._check_completeness(content, context))
        
        # Repository requirement validation
        issues.extend(await self._validate_repository_requirements(content, context))
        
        # Calculate pass rate
        total_checks = len(context.requirements) * 4  # 4 types of checks per requirement
        failed_checks = len([i for i in issues if i.severity in ('error', 'warning')])
        pass_rate = (total_checks - failed_checks) / total_checks
        
        return ValidationResult(
            file_path=context.file_path,
            issues=issues,
            pass_rate=pass_rate,
            error_count=len([i for i in issues if i.severity == 'error']),
            warning_count=len([i for i in issues if i.severity == 'warning']),
            info_count=len([i for i in issues if i.severity == 'info']),
            validation_time=(datetime.now() - context.start_time).total_seconds()
        )

    async def _check_technical_accuracy(
        self,
        content: str,
        context: ValidationContext
    ) -> List[ValidationIssue]:
        """Check technical accuracy of documentation content."""
        issues = []
        for requirement in context.requirements:
            for rule in requirement.validation_rules:
                if rule.validation_type == 'technical_accuracy':
                    # Implement technical accuracy checks based on rules
                    pass
        return issues

    async def _validate_code_examples(
        self,
        content: str,
        context: ValidationContext
    ) -> List[ValidationIssue]:
        """Validate code examples in documentation."""
        issues = []
        # Extract and validate code blocks
        return issues

    async def _check_completeness(
        self,
        content: str,
        context: ValidationContext
    ) -> List[ValidationIssue]:
        """Check documentation completeness."""
        issues = []
        # Check for required sections and content
        return issues

    async def _validate_repository_requirements(
        self,
        content: str,
        context: ValidationContext
    ) -> List[ValidationIssue]:
        """Validate documentation against repository requirements."""
        issues = []
        # Check repository-specific requirements
        return issues

    async def _load_requirements(
        self,
        repository_type: str
    ) -> List[TechnicalRequirement]:
        """Load validation requirements for repository type."""
        # Load and return appropriate requirements
        return []

    def _determine_content_type(self, file_path: str) -> str:
        """Determine content type from file path."""
        if file_path.endswith('.md'):
            return 'docs'
        elif file_path.endswith(('.py', '.java', '.js')):
            return 'code'
        else:
            return 'unknown'

    async def _collect_blocking_issues(
        self,
        results: Dict[str, ValidationResult]
    ) -> List[ValidationIssue]:
        """Collect all blocking issues from validation results."""
        blocking = []
        for result in results.values():
            blocking.extend([i for i in result.issues if i.severity == 'error'])
        return blocking

    async def _collect_non_blocking_issues(
        self,
        results: Dict[str, ValidationResult]
    ) -> List[ValidationIssue]:
        """Collect all non-blocking issues from validation results."""
        non_blocking = []
        for result in results.values():
            non_blocking.extend([i for i in result.issues if i.severity != 'error'])
        return non_blocking

    async def _generate_summary(
        self,
        results: Dict[str, ValidationResult]
    ) -> str:
        """Generate validation summary."""
        summary = []
        # Generate summary based on validation results
        return "\n".join(summary)

    async def _determine_next_steps(
        self,
        results: Dict[str, ValidationResult]
    ) -> List[str]:
        """Determine next steps based on validation results."""
        next_steps = []
        # Determine next steps based on validation results
        return next_steps
