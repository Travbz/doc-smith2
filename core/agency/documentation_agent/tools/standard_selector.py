"""Tool for selecting and configuring documentation standards."""
from typing import Dict, List, Optional
from pathlib import Path
import yaml
from core.services.logging import setup_logger
from core.services.cache import cache_manager
from ..schemas.documentation_standard import (
    DocumentationRule,
    TemplateVariable,
    DocumentationTemplate,
    DocumentationStandard
)

logger = setup_logger(__name__)

class StandardSelector:
    """Selects and configures documentation standards based on repository type."""

    def __init__(self, standards_path: str = "standards"):
        """Initialize the standard selector."""
        self.standards_path = Path(standards_path)
        self.cache = cache_manager
        self._standards: Dict[str, DocumentationStandard] = {}

    async def load_standards(self) -> None:
        """Load all documentation standards from files."""
        try:
            # Check cache first
            cached_standards = self.cache.get("documentation_standards")
            if cached_standards:
                self._standards = cached_standards
                return

            for standard_file in self.standards_path.glob("*.yaml"):
                try:
                    with open(standard_file, 'r') as f:
                        data = yaml.safe_load(f)
                        standard = DocumentationStandard(**data)
                        self._standards[standard.repository_type] = standard
                except Exception as e:
                    logger.error(f"Error loading standard from {standard_file}: {str(e)}")

            # Cache the standards
            self.cache.set("documentation_standards", self._standards)

        except Exception as e:
            logger.error(f"Error loading standards: {str(e)}")
            raise

    async def select_standard(
        self, 
        repo_type: str,
        custom_rules: Optional[List[DocumentationRule]] = None
    ) -> DocumentationStandard:
        """
        Select appropriate documentation standard for a repository type.
        
        Args:
            repo_type: Type of repository
            custom_rules: Optional custom documentation rules
            
        Returns:
            Selected DocumentationStandard
        """
        try:
            # Ensure standards are loaded
            if not self._standards:
                await self.load_standards()

            # Get base standard
            base_standard = self._standards.get(repo_type)
            if not base_standard:
                logger.warning(f"No standard found for {repo_type}, using unknown type standard")
                base_standard = self._standards.get("unknown")
                if not base_standard:
                    raise ValueError("No default standard available")

            # Apply custom rules if provided
            if custom_rules:
                logger.info("Applying custom documentation rules")
                rules = list(base_standard.rules)  # Create copy of base rules
                rules.extend(custom_rules)
                return DocumentationStandard(
                    **{**base_standard.dict(), "rules": rules}
                )

            return base_standard

        except Exception as e:
            logger.error(f"Error selecting standard: {str(e)}")
            raise

    async def validate_standard(
        self, 
        standard: DocumentationStandard,
        repo_path: str
    ) -> bool:
        """
        Validate that a documentation standard can be applied to a repository.
        
        Args:
            standard: Documentation standard to validate
            repo_path: Path to repository
            
        Returns:
            True if standard is valid for repository
        """
        try:
            repo_path = Path(repo_path)
            
            # Check required files exist
            for required_file in standard.required_files:
                if not (repo_path / required_file).exists():
                    logger.warning(f"Required file missing: {required_file}")
                    return False

            # Validate template variables
            for template in standard.templates:
                for variable in template.variables:
                    if variable.required:
                        # Here we would check if we can extract the required variable
                        # from the repository. This is a simplified check.
                        pass

            return True

        except Exception as e:
            logger.error(f"Error validating standard: {str(e)}")
            return False

    async def customize_standard(
        self,
        base_standard: DocumentationStandard,
        customizations: Dict
    ) -> DocumentationStandard:
        """
        Customize a documentation standard with specific requirements.
        
        Args:
            base_standard: Base documentation standard
            customizations: Custom settings to apply
            
        Returns:
            Customized DocumentationStandard
        """
        try:
            # Create copy of base standard
            custom_standard = DocumentationStandard(**base_standard.dict())
            
            # Apply customizations
            if "rules" in customizations:
                custom_rules = [DocumentationRule(**rule) for rule in customizations["rules"]]
                custom_standard.rules.extend(custom_rules)
                
            if "templates" in customizations:
                custom_templates = [DocumentationTemplate(**template) 
                                  for template in customizations["templates"]]
                custom_standard.templates.extend(custom_templates)
                
            if "required_files" in customizations:
                custom_standard.required_files.extend(customizations["required_files"])
                
            if "file_structure" in customizations:
                custom_standard.file_structure.update(customizations["file_structure"])
                
            return custom_standard

        except Exception as e:
            logger.error(f"Error customizing standard: {str(e)}")
            raise

    def get_template(
        self,
        standard: DocumentationStandard,
        template_id: str
    ) -> Optional[DocumentationTemplate]:
        """Get a specific template from a standard."""
        return next((t for t in standard.templates if t.template_id == template_id), None)