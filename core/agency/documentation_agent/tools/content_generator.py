"""Tool for generating documentation content."""
from typing import Dict, List, Optional
from pathlib import Path
import logging
from datetime import datetime
from core.services.logging import setup_logger
from core.services.cache import cache_manager
from ..schemas.documentation_standard import DocumentationStandard, DocumentationTemplate
from ..schemas.generated_content import (
    DocumentSection,
    DocumentMetadata,
    DocumentFile,
    GeneratedContent
)

logger = setup_logger(__name__)

class ContentGenerator:
    """Generates documentation content based on templates and standards."""

    def __init__(self):
        """Initialize the content generator."""
        self.cache = cache_manager
        self._version = "1.0.0"  # Generator version

    async def generate_documentation(
        self,
        repository_path: str,
        repository_type: str,
        standard: DocumentationStandard,
        variables: Optional[Dict[str, str]] = None
    ) -> GeneratedContent:
        """Generate complete documentation for a repository."""
        try:
            logger.info(f"Generating documentation for {repository_path}")
            files: Dict[str, DocumentFile] = {}
            
            # Generate each required documentation file
            for template in standard.templates:
                if repository_type in template.applies_to:
                    doc_file = await self._generate_file(
                        template=template,
                        repo_path=repository_path,
                        variables=variables,
                        standard=standard
                    )
                    files[template.file_name] = doc_file

            # Create the complete documentation package
            content = GeneratedContent(
                repository_url=repository_path,
                repository_type=repository_type,
                files=files,
                documentation_version=self._version,
                complete=await self._validate_completeness(files, standard),
                requires_review=True
            )

            return content

        except Exception as e:
            logger.error(f"Error generating documentation: {str(e)}", exc_info=True)
            raise

    async def _generate_file(
        self,
        template: DocumentationTemplate,
        repo_path: str,
        variables: Optional[Dict[str, str]],
        standard: DocumentationStandard
    ) -> DocumentFile:
        """Generate a single documentation file from a template."""
        try:
            # Prepare template variables
            vars_dict = await self._prepare_variables(template, repo_path, variables)
            
            # Generate sections
            sections = await self._generate_sections(template, vars_dict, repo_path)
            
            # Combine sections into content
            content = "\n\n".join(section.content for section in sections)
            
            return DocumentFile(
                path=template.file_name,
                content=content,
                sections=sections,
                metadata=DocumentMetadata(
                    generator_version=self._version,
                    template_id=template.template_id,
                    repository_type=standard.repository_type,
                    documentation_standard=standard.name
                ),
                requires_review=True
            )

        except Exception as e:
            logger.error(f"Error generating file from template: {str(e)}")
            raise

    async def _prepare_variables(
        self,
        template: DocumentationTemplate,
        repo_path: str,
        custom_vars: Optional[Dict[str, str]]
    ) -> Dict[str, str]:
        """Prepare variables for template generation."""
        variables = {}
        
        # Add default values
        for var in template.variables:
            if var.default:
                variables[var.name] = var.default
        
        # Add custom variables
        if custom_vars:
            variables.update(custom_vars)
            
        # Extract repo-specific variables
        repo_vars = await self._extract_repo_variables(repo_path, template.variables)
        variables.update(repo_vars)
        
        return variables

    async def _extract_repo_variables(
        self,
        repo_path: str,
        required_vars: List
    ) -> Dict[str, str]:
        """Extract variables from repository content."""
        # This would analyze the repository to extract required information
        # Implementation depends on what variables need to be extracted
        return {}

    async def _generate_sections(
        self,
        template: DocumentationTemplate,
        variables: Dict[str, str],
        repo_path: str
    ) -> List[DocumentSection]:
        """Generate documentation sections from template."""
        sections = []
        order = 1
        
        # Parse template content into sections
        # This is a simplified implementation
        raw_sections = template.content.split("## ")
        
        for raw_section in raw_sections:
            if not raw_section.strip():
                continue
                
            # Extract title and content
            lines = raw_section.splitlines()
            title = lines[0].strip()
            content = "\n".join(lines[1:]).strip()
            
            # Apply variables
            for var_name, var_value in variables.items():
                content = content.replace(f"${var_name}", str(var_value))
            
            sections.append(DocumentSection(
                title=title,
                content=content,
                level=2,
                order=order
            ))
            order += 1
            
        return sections

    async def _validate_completeness(
        self,
        files: Dict[str, DocumentFile],
        standard: DocumentationStandard
    ) -> bool:
        """Validate if generated documentation is complete."""
        # Check all required files are present
        for required_file in standard.required_files:
            if required_file not in files:
                return False
                
        # Check all files have content
        for doc_file in files.values():
            if not doc_file.content.strip():
                return False
                
        return True