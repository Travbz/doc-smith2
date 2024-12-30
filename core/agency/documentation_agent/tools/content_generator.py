"""Tool for generating documentation content."""
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
from core.services.logging import setup_logger
from core.services.cache import cache_manager
from core.services.error_handling.error_handler import (
    with_error_handling,
    ErrorCategory,
    ErrorSeverity,
    DocSmithError
)
from ..schemas.documentation_standard import DocumentationStandard, DocumentationTemplate
from ..schemas.generated_content import (
    DocumentSection,
    DocumentMetadata,
    DocumentFile,
    GeneratedContent
)
from ..schemas.repository_analysis import RepositoryAnalysis, DirectoryInfo

logger = setup_logger(__name__)

class ContentGenerationError(DocSmithError):
    """Specific error class for content generation issues."""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
        super().__init__(
            message,
            category=ErrorCategory.DOC_GEN,
            severity=severity,
            recovery_hint="Check template validity and ensure all required variables are provided"
        )

class ContentGenerator:
    """Generates documentation content based on templates and standards."""

    def __init__(self):
        """Initialize the content generator."""
        self.cache = cache_manager
        self._version = "1.0.0"  # Generator version

    @with_error_handling(ErrorCategory.DOC_GEN, ErrorSeverity.HIGH)
    async def generate(
        self,
        analysis: RepositoryAnalysis,
        standard: DocumentationStandard,
        variables: Optional[Dict[str, str]] = None
    ) -> GeneratedContent:
        """Generate documentation content."""
        try:
            logger.info(f"Generating documentation using standard: {standard.name}")
            
            # Validate inputs
            if not standard.templates:
                raise ContentGenerationError(
                    "Documentation standard contains no templates",
                    ErrorSeverity.HIGH
                )

            # Initialize content structure
            try:
                content = GeneratedContent(
                    id=f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    repository_url=analysis.repository_path,
                    repository_type=analysis.repository_type,
                    documentation_version=self._version,
                    metadata=DocumentMetadata(
                        generator_version=self._version,
                        repository_type=analysis.repository_type,
                        documentation_standard=standard.name,
                        generated_at=datetime.now(),
                        template_id=None
                    ),
                    files={}
                )
            except Exception as e:
                logger.error(f"Error creating GeneratedContent: {str(e)}")
                raise ContentGenerationError(
                    f"Failed to create GeneratedContent: {str(e)}",
                    ErrorSeverity.HIGH
                ) from e

            # Generate each document
            for template in standard.templates:
                if analysis.repository_type in template.applies_to:
                    try:
                        doc_file = await self._generate_file(
                            template=template,
                            analysis=analysis,
                            variables=variables
                        )
                        content.files[template.file_name] = doc_file
                    except Exception as e:
                        logger.error(f"Error generating file {template.file_name}: {str(e)}")
                        raise ContentGenerationError(
                            f"Failed to generate file {template.file_name}: {str(e)}",
                            ErrorSeverity.HIGH
                        ) from e

            if not content.files:
                raise ContentGenerationError(
                    "No applicable templates found for repository type",
                    ErrorSeverity.MEDIUM
                )

            return content

        except Exception as e:
            logger.error(f"Error generating documentation: {str(e)}")
            if isinstance(e, ContentGenerationError):
                raise
            raise ContentGenerationError(
                f"Failed to generate documentation: {str(e)}",
                ErrorSeverity.HIGH
            ) from e

    @with_error_handling(ErrorCategory.DOC_GEN, ErrorSeverity.MEDIUM)
    async def _generate_file(
        self,
        template: DocumentationTemplate,
        analysis: RepositoryAnalysis,
        variables: Optional[Dict[str, str]] = None
    ) -> DocumentFile:
        """Generate a single documentation file."""
        try:
            vars_dict = variables or {}

            # Add standard variables
            vars_dict.update({
                "project_name": analysis.repository_path.split('/')[-1],
                "repository_type": analysis.repository_type,
                "generation_date": datetime.now().strftime("%Y-%m-%d"),
                "generator_version": self._version
            })

            # Add repository-specific variables
            vars_dict.update(await self._analyze_repository(analysis))

            # Add template-specific variables
            if template.template_id == "readme":
                vars_dict.update(await self._get_readme_variables(analysis))
            elif template.template_id == "module_doc":
                vars_dict.update(await self._get_module_variables(analysis))
            elif template.template_id == "config_doc":
                vars_dict.update(await self._get_config_variables(analysis))

            # Process template content with variables
            content = template.content
            for var_name, var_value in vars_dict.items():
                placeholder = "{" + var_name + "}"
                if placeholder in content:
                    content = content.replace(placeholder, str(var_value))

            # Create document section
            section = DocumentSection(
                title=template.name,
                content=content,
                level=1,
                order=1
            )

            return DocumentFile(
                path=template.file_name,
                content=content,
                sections=[section],
                metadata=DocumentMetadata(
                    generator_version=self._version,
                    repository_type=analysis.repository_type,
                    documentation_standard=template.name,
                    generated_at=datetime.now(),
                    template_id=template.template_id
                ),
                requires_review=True
            )

        except Exception as e:
            raise ContentGenerationError(
                f"Failed to generate file {template.file_name}: {str(e)}",
                ErrorSeverity.MEDIUM
            ) from e

    async def _analyze_repository(self, analysis: RepositoryAnalysis) -> Dict[str, str]:
        """Extract repository-specific variables."""
        variables = {}

        # Get project description from repository files
        description = await self._extract_project_description(analysis)
        if description:
            variables["project_description"] = description

        # Get license information
        license_info = await self._extract_license_info(analysis)
        if license_info:
            variables["license_info"] = license_info

        return variables

    async def _get_readme_variables(self, analysis: RepositoryAnalysis) -> Dict[str, str]:
        """Get variables for README template."""
        variables = {}

        # Project structure
        structure_lines = []
        def format_structure(directory: DirectoryInfo, level: int = 0):
            indent = "  " * level
            structure_lines.append(f"{indent}- {directory.name}/")
            for file in directory.files:
                structure_lines.append(f"{indent}  - {file.name}")
            for subdir in directory.subdirectory_info:
                format_structure(subdir, level + 1)

        format_structure(analysis.structure)
        variables["project_structure"] = "\n".join(structure_lines)

        # Usage example
        if analysis.repository_type == "python":
            variables["usage_example"] = """
import example

# Initialize the client
client = example.Client()

# Make a request
response = client.get_data()
"""
        else:
            variables["usage_example"] = "# Add usage example here"

        # Contributing guidelines
        variables["contributing_guidelines"] = """
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request
"""

        return variables

    async def _get_module_variables(self, analysis: RepositoryAnalysis) -> Dict[str, str]:
        """Get variables for module documentation template."""
        variables = {
            "module_name": "example",
            "class_name": "ExampleClass",
            "class_description": "Example class description",
            "attributes": "example_attr: str - Example attribute",
            "methods": "example_method() - Example method"
        }
        return variables

    async def _get_config_variables(self, analysis: RepositoryAnalysis) -> Dict[str, str]:
        """Get variables for configuration documentation template."""
        variables = {
            "config_name": "example",
            "config_description": "Example configuration",
            "config_options": "example_option: Example option description",
            "config_defaults": "example_option: default_value"
        }
        return variables

    async def _extract_project_description(self, analysis: RepositoryAnalysis) -> str:
        """Extract project description from repository files."""
        # Try to get description from README.md
        for file in analysis.structure.files:
            if file.name.lower() == "readme.md":
                try:
                    with open(Path(analysis.repository_path) / file.name, 'r') as f:
                        content = f.read()
                        # Look for first paragraph after title
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if line.startswith('#'):
                                # Skip title and empty lines
                                i += 1
                                while i < len(lines) and not lines[i].strip():
                                    i += 1
                                # Get first non-empty paragraph
                                description = []
                                while i < len(lines) and lines[i].strip():
                                    description.append(lines[i].strip())
                                    i += 1
                                if description:
                                    return ' '.join(description)
                except Exception as e:
                    logger.warning(f"Failed to read README.md: {str(e)}")

        # Try to get description from setup.py or pyproject.toml
        for file in analysis.structure.files:
            if file.name == "setup.py":
                try:
                    with open(Path(analysis.repository_path) / file.name, 'r') as f:
                        content = f.read()
                        if 'description=' in content:
                            start = content.find('description=') + len('description=')
                            end = content.find(',', start)
                            if end == -1:
                                end = content.find(')', start)
                            if end != -1:
                                description = content[start:end].strip("'\"")
                                if description:
                                    return description
                except Exception as e:
                    logger.warning(f"Failed to read setup.py: {str(e)}")

        # Default description
        return f"Documentation for {analysis.repository_type} repository"

    async def _extract_license_info(self, analysis: RepositoryAnalysis) -> str:
        """Extract license information from repository files."""
        # Try to get license from LICENSE file
        for file in analysis.structure.files:
            if file.name.lower() == "license" or file.name.lower() == "license.md":
                try:
                    with open(Path(analysis.repository_path) / file.name, 'r') as f:
                        content = f.read()
                        # Get first line as license type
                        license_type = content.split('\n')[0].strip()
                        if license_type:
                            return license_type
                except Exception as e:
                    logger.warning(f"Failed to read LICENSE file: {str(e)}")

        # Try to get license from setup.py
        for file in analysis.structure.files:
            if file.name == "setup.py":
                try:
                    with open(Path(analysis.repository_path) / file.name, 'r') as f:
                        content = f.read()
                        if 'license=' in content:
                            start = content.find('license=') + len('license=')
                            end = content.find(',', start)
                            if end == -1:
                                end = content.find(')', start)
                            if end != -1:
                                license_type = content[start:end].strip("'\"")
                                if license_type:
                                    return license_type
                except Exception as e:
                    logger.warning(f"Failed to read setup.py: {str(e)}")

        # Default license info
        return "License information not found"

    async def _generate_project_structure(self, analysis: RepositoryAnalysis) -> str:
        """Generate a tree view of the project structure."""
        structure = "```\n"
        structure += self._format_directory_tree(analysis.structure)
        structure += "```"
        return structure

    def _format_directory_tree(self, directory: DirectoryInfo, prefix: str = "") -> str:
        """Format directory tree recursively."""
        tree = ""
        
        # Add files
        for file in directory.files:
            if not file.name.startswith('.'):
                tree += f"{prefix}├── {file.name}\n"
                
        # Add subdirectories
        for subdir in directory.subdirectory_info:
            if not subdir.name.startswith('.'):
                tree += f"{prefix}├── {subdir.name}/\n"
                tree += self._format_directory_tree(subdir, prefix + "│   ")
                
        return tree

    async def _extract_usage_example(self, analysis: RepositoryAnalysis) -> str:
        """Extract usage example from repository."""
        # Look for example code in examples directory or docstrings
        example = """from docsmith import DocumentationGenerator

generator = DocumentationGenerator()
docs = generator.generate("my_project")
print(f"Documentation generated: {docs.id}")"""
        return example

    async def _load_contributing_template(self) -> str:
        """Load contributing guidelines template."""
        try:
            template_path = Path(__file__).parent.parent / "templates" / "python" / "contributing.md"
            with open(template_path, "r") as f:
                return f.read()
        except Exception:
            return "Please see CONTRIBUTING.md for guidelines on how to contribute to this project."

    async def _extract_module_documentation(self, analysis: RepositoryAnalysis) -> str:
        """Extract module documentation from repository."""
        modules = "### Core Modules\n\n"
        for file in analysis.structure.files:
            if file.type == "py" and not file.name.startswith("__"):
                modules += f"- `{file.name}`: Core module for {file.name.replace('.py', '')}\n"
        return modules

    async def _extract_class_documentation(self, analysis: RepositoryAnalysis) -> str:
        """Extract class documentation from repository."""
        classes = "### Main Classes\n\n"
        # This would normally parse Python files and extract class documentation
        classes += "- `DocumentationGenerator`: Main class for generating documentation\n"
        classes += "- `RepositoryAnalyzer`: Analyzes repository structure\n"
        return classes

    async def _extract_function_documentation(self, analysis: RepositoryAnalysis) -> str:
        """Extract function documentation from repository."""
        functions = "### Public Functions\n\n"
        # This would normally parse Python files and extract function documentation
        functions += "- `generate_docs(repo_path: str) -> Dict`: Generate documentation for a repository\n"
        functions += "- `analyze_repo(repo_path: str) -> Analysis`: Analyze repository structure\n"
        return functions

    async def _extract_environment_variables(self, analysis: RepositoryAnalysis) -> str:
        """Extract environment variable documentation."""
        env_vars = "### Required Environment Variables\n\n"
        env_vars += "- `GITHUB_TOKEN`: GitHub API token for repository access\n"
        env_vars += "- `OPENAI_API_KEY`: OpenAI API key for content generation\n"
        return env_vars

    async def _extract_config_files(self, analysis: RepositoryAnalysis) -> str:
        """Extract configuration file documentation."""
        config = "### Configuration Files\n\n"
        for file in analysis.structure.files:
            if file.name in ["config.yaml", "settings.py", ".env.example"]:
                config += f"- `{file.name}`: Configuration file for {file.name.split('.')[0]}\n"
        return config

    async def _extract_dependencies(self, analysis: RepositoryAnalysis) -> str:
        """Extract dependency information."""
        deps = "### Dependencies\n\n"
        # Look for requirements.txt or setup.py
        for file in analysis.structure.files:
            if file.name == "requirements.txt":
                deps += "Install dependencies from requirements.txt:\n"
                deps += "```bash\npip install -r requirements.txt\n```\n"
                break
        return deps

    @with_error_handling(ErrorCategory.DOC_GEN, ErrorSeverity.LOW)
    async def _generate_section(
        self,
        section_template: str,
        analysis: Dict,
        variables: Dict[str, str]
    ) -> DocumentSection:
        """Generate a single documentation section."""
        try:
            # Process template with variables
            content = section_template
            for var_name, var_value in variables.items():
                content = content.replace(f"${{{var_name}}}", str(var_value))

            return DocumentSection(
                content=content,
                metadata={
                    "template_version": self._version,
                    "variables_used": list(variables.keys())
                }
            )

        except Exception as e:
            raise ContentGenerationError(
                f"Failed to generate section: {str(e)}",
                ErrorSeverity.LOW
            ) from e