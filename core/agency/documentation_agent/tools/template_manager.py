"""Tool for managing documentation templates."""
from typing import Dict, List, Optional
from pathlib import Path
import yaml
from datetime import datetime
from core.services.logging import setup_logger
from core.services.cache import cache_manager
from ..schemas.documentation_standard import DocumentationTemplate, TemplateVariable

logger = setup_logger(__name__)

class TemplateManager:
    """Manages documentation templates and their application."""

    def __init__(self, templates_path: str = "templates"):
        """Initialize the template manager."""
        self.templates_path = Path(templates_path)
        self.cache = cache_manager
        self._templates: Dict[str, DocumentationTemplate] = {}

    async def load_templates(self) -> None:
        """Load all templates from the templates directory."""
        try:
            # Check cache first
            cached_templates = self.cache.get("documentation_templates")
            if cached_templates:
                self._templates = cached_templates
                return

            for template_file in self.templates_path.glob("*.yaml"):
                try:
                    with open(template_file, 'r') as f:
                        data = yaml.safe_load(f)
                        template = DocumentationTemplate(**data)
                        self._templates[template.template_id] = template
                except Exception as e:
                    logger.error(f"Error loading template from {template_file}: {str(e)}")

            # Cache the templates
            self.cache.set("documentation_templates", self._templates)

        except Exception as e:
            logger.error(f"Error loading templates: {str(e)}")
            raise

    async def get_template(self, template_id: str) -> Optional[DocumentationTemplate]:
        """Get a specific template by ID."""
        if not self._templates:
            await self.load_templates()
        return self._templates.get(template_id)

    async def validate_template(
        self,
        template: DocumentationTemplate,
        variables: Dict[str, str]
    ) -> bool:
        """
        Validate that all required template variables are provided.
        
        Args:
            template: Template to validate
            variables: Provided variables
            
        Returns:
            True if all required variables are provided
        """
        try:
            for var in template.variables:
                if var.required and var.name not in variables:
                    if not var.default:  # No default value available
                        logger.warning(f"Required variable missing: {var.name}")
                        return False
            return True

        except Exception as e:
            logger.error(f"Error validating template: {str(e)}")
            return False

    async def apply_template(
        self,
        template: DocumentationTemplate,
        variables: Dict[str, str]
    ) -> str:
        """
        Apply variables to a template.
        
        Args:
            template: Template to apply
            variables: Variables to substitute
            
        Returns:
            Processed template content
        """
        try:
            # Validate variables first
            if not await self.validate_template(template, variables):
                raise ValueError("Template validation failed")

            content = template.content
            
            # Apply variables
            for var_name, var_value in variables.items():
                content = content.replace(f"${var_name}", str(var_value))
                
            # Apply any default values for missing variables
            for var in template.variables:
                if var.name not in variables and var.default:
                    content = content.replace(f"${var.name}", str(var.default))
                    
            return content

        except Exception as e:
            logger.error(f"Error applying template: {str(e)}")
            raise

    async def create_template(
        self,
        template_id: str,
        content: str,
        variables: List[TemplateVariable],
        file_name: str,
        applies_to: List[str],
        save: bool = True
    ) -> DocumentationTemplate:
        """
        Create a new documentation template.
        
        Args:
            template_id: Unique template identifier
            content: Template content
            variables: Template variables
            file_name: Target file name
            applies_to: Repository types this template applies to
            save: Whether to save the template to disk
            
        Returns:
            Created DocumentationTemplate
        """
        try:
            template = DocumentationTemplate(
                template_id=template_id,
                name=f"Template {template_id}",
                description=f"Documentation template for {', '.join(applies_to)}",
                content=content,
                variables=variables,
                file_name=file_name,
                applies_to=applies_to
            )
            
            if save:
                # Save to templates directory
                template_path = self.templates_path / f"{template_id}.yaml"
                template_data = yaml.dump(template.dict())
                
                template_path.write_text(template_data)
                
                # Update cache
                self._templates[template_id] = template
                self.cache.set("documentation_templates", self._templates)
                
            return template

        except Exception as e:
            logger.error(f"Error creating template: {str(e)}")
            raise

    async def update_template(
        self,
        template_id: str,
        updates: Dict
    ) -> DocumentationTemplate:
        """
        Update an existing template.
        
        Args:
            template_id: Template to update
            updates: Fields to update
            
        Returns:
            Updated DocumentationTemplate
        """
        try:
            template = await self.get_template(template_id)
            if not template:
                raise ValueError(f"Template not found: {template_id}")
                
            # Update template fields
            template_dict = template.dict()
            template_dict.update(updates)
            
            updated_template = DocumentationTemplate(**template_dict)
            
            # Save updates
            template_path = self.templates_path / f"{template_id}.yaml"
            template_data = yaml.dump(updated_template.dict())
            
            template_path.write_text(template_data)
            
            # Update cache
            self._templates[template_id] = updated_template
            self.cache.set("documentation_templates", self._templates)
            
            return updated_template

        except Exception as e:
            logger.error(f"Error updating template: {str(e)}")
            raise