"""Tool for selecting and configuring documentation standards."""
from typing import Dict, List, Optional
from pathlib import Path
import yaml
from core.services.logging import setup_logger
from core.services.cache.cache_manager import cache_manager
from core.services.error_handling.error_handler import (
    with_error_handling,
    ErrorCategory,
    ErrorSeverity,
    DocSmithError
)
from ..schemas.documentation_standard import (
    DocumentationRule,
    TemplateVariable,
    DocumentationTemplate,
    DocumentationStandard
)
from ..schemas.repository_analysis import RepositoryAnalysis

logger = setup_logger(__name__)

class StandardSelectionError(DocSmithError):
    """Specific error class for standard selection issues."""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
        super().__init__(
            message,
            category=ErrorCategory.DOC_GEN,
            severity=severity,
            recovery_hint="Verify standards directory exists and contains valid standard definitions"
        )

class StandardSelector:
    """Selects and configures documentation standards."""

    def __init__(self):
        """Initialize the standard selector."""
        self.cache = cache_manager
        self.standards_dir = Path(__file__).parent.parent.parent.parent / "util" / "standards"

    @with_error_handling(ErrorCategory.DOC_GEN, ErrorSeverity.HIGH)
    async def select(
        self,
        analysis: RepositoryAnalysis,
        custom_rules: Optional[List[Dict]] = None
    ) -> DocumentationStandard:
        """Select appropriate documentation standard."""
        try:
            # Get repository type
            repo_type = analysis.repository_type

            # Load standard for repository type
            standard = await self._load_standard(repo_type)
            if not standard:
                raise StandardSelectionError(
                    f"No standard found for repository type: {repo_type}",
                    ErrorSeverity.HIGH
                )

            # Apply custom rules if provided
            if custom_rules:
                standard = await self._apply_custom_rules(standard, custom_rules)

            return standard

        except Exception as e:
            if isinstance(e, StandardSelectionError):
                raise
            raise StandardSelectionError(
                f"Failed to select documentation standard: {str(e)}",
                ErrorSeverity.HIGH
            ) from e

    @with_error_handling(ErrorCategory.DOC_GEN, ErrorSeverity.HIGH)
    async def _load_standard(self, repo_type: str) -> Optional[DocumentationStandard]:
        """Load documentation standard from file."""
        try:
            # Check cache first
            cache_key = f"standard_{repo_type}"
            cached_standard = self.cache.get(cache_key)
            if cached_standard:
                return cached_standard

            # Load from file
            standard_file = self.standards_dir / f"{repo_type}.yaml"
            if not standard_file.exists():
                logger.warning(f"Standard file not found: {standard_file}")
                return None

            with open(standard_file, "r") as f:
                data = yaml.safe_load(f)

            # Create standard object
            standard = DocumentationStandard(
                name=data["name"],
                description=data["description"],
                version=data["version"],
                repository_type=data["repository_type"],
                required_files=data["required_files"],
                optional_files=data.get("optional_files", []),
                file_structure=data.get("file_structure", {}),
                templates=[
                    DocumentationTemplate(
                        template_id=t["template_id"],
                        name=t["name"],
                        description=t["description"],
                        content=t["content"],
                        variables=[
                            TemplateVariable(
                                name=v["name"],
                                description=v["description"],
                                required=v.get("required", True),
                                default=v.get("default")
                            )
                            for v in t["variables"]
                        ],
                        file_name=t["file_name"],
                        applies_to=t["applies_to"]
                    )
                    for t in data["templates"]
                ],
                rules=[
                    DocumentationRule(
                        rule_id=r["rule_id"],
                        description=r["description"],
                        required=r.get("required", True),
                        applies_to=r["applies_to"],
                        example=r.get("example")
                    )
                    for r in data["rules"]
                ]
            )

            # Cache the standard
            self.cache.set(cache_key, standard)
            return standard

        except Exception as e:
            raise StandardSelectionError(
                f"Failed to load standard: {str(e)}",
                ErrorSeverity.HIGH
            ) from e

    @with_error_handling(ErrorCategory.DOC_GEN, ErrorSeverity.MEDIUM)
    async def _apply_custom_rules(
        self,
        standard: DocumentationStandard,
        custom_rules: List[Dict]
    ) -> DocumentationStandard:
        """Apply custom rules to standard."""
        try:
            # Convert custom rules to DocumentationRule objects
            rules = [
                DocumentationRule(
                    name=r["name"],
                    type=r["type"],
                    applies_to=r["applies_to"],
                    criteria=r["criteria"]
                )
                for r in custom_rules
            ]

            # Add custom rules to standard
            standard.rules.extend(rules)
            return standard

        except Exception as e:
            raise StandardSelectionError(
                f"Failed to apply custom rules: {str(e)}",
                ErrorSeverity.MEDIUM
            ) from e