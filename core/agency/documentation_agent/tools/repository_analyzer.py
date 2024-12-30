"""Tool for analyzing repository structure and determining type."""
from typing import Dict, List, Optional
from pathlib import Path
import os
from datetime import datetime
from core.services.logging import setup_logger
from core.services.cache.cache_manager import cache_manager
from core.services.error_handling.error_handler import (
    with_error_handling,
    ErrorCategory,
    ErrorSeverity,
    DocSmithError
)
from ..schemas.repository_analysis import (
    FileInfo,
    DirectoryInfo,
    RepositoryPatterns,
    RepositoryAnalysis
)

logger = setup_logger(__name__)

class RepositoryAnalysisError(DocSmithError):
    """Specific error class for repository analysis issues."""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
        super().__init__(
            message,
            category=ErrorCategory.DOC_GEN,
            severity=severity,
            recovery_hint="Verify repository path and permissions, ensure repository structure is valid"
        )

class RepositoryAnalyzer:
    """Analyzes repository structure and determines repository type."""

    REPO_TYPE_PATTERNS = {
        "spring_boot": [
            "pom.xml",
            "build.gradle",
            "src/main/java",
            "application.properties",
            "application.yml"
        ],
        "nginx": [
            "nginx.conf",
            "default.conf",
            "sites-available",
            "sites-enabled"
        ],
        "bounded_context": [
            "helm",
            "terraform",
            "values.yaml",
            "main.tf"
        ],
        "python": [
            "setup.py",
            "requirements.txt",
            "pyproject.toml",
            "__init__.py"
        ]
    }

    def __init__(self):
        """Initialize the repository analyzer."""
        self.cache = cache_manager

    @with_error_handling(ErrorCategory.DOC_GEN, ErrorSeverity.HIGH)
    async def analyze(self, repo_path: str, repo_type: Optional[str] = None) -> RepositoryAnalysis:
        """Analyze repository structure and determine type."""
        if not os.path.exists(repo_path):
            raise RepositoryAnalysisError(
                f"Repository path does not exist: {repo_path}",
                ErrorSeverity.HIGH
            )

        try:
            # Check cache first
            cache_key = f"repo_analysis_{repo_path}"
            cached_analysis = self.cache.get(cache_key)
            if cached_analysis and not repo_type:
                return cached_analysis

            # Analyze directory structure
            structure = await self._analyze_directory(Path(repo_path))
            
            # Determine repository type
            detected_type = repo_type or await self._detect_repo_type(structure)
            if not detected_type:
                detected_type = "unknown"  # Default to unknown if type cannot be determined

            # Create analysis result
            analysis = RepositoryAnalysis(
                repository_path=repo_path,
                repository_type=detected_type,
                structure=structure,
                patterns=await self._extract_patterns(structure, detected_type)
            )

            # Cache the result
            self.cache.set(cache_key, analysis)
            return analysis

        except Exception as e:
            if isinstance(e, RepositoryAnalysisError):
                raise
            raise RepositoryAnalysisError(
                f"Failed to analyze repository: {str(e)}",
                ErrorSeverity.HIGH
            ) from e

    @with_error_handling(ErrorCategory.DOC_GEN, ErrorSeverity.MEDIUM)
    async def _analyze_directory(self, path: Path) -> DirectoryInfo:
        """Analyze directory structure recursively."""
        try:
            files = []
            subdirectories = []
            subdirectory_info = []

            for item in path.iterdir():
                if item.is_file():
                    stat = item.stat()
                    files.append(FileInfo(
                        name=item.name,
                        path=str(item.relative_to(path)),
                        size=stat.st_size,
                        type=item.suffix[1:] if item.suffix else "unknown",
                        last_modified=datetime.fromtimestamp(stat.st_mtime).isoformat()
                    ))
                elif item.is_dir() and not item.name.startswith('.'):
                    subdirectories.append(item.name)
                    subdirectory_info.append(await self._analyze_directory(item))

            return DirectoryInfo(
                name=path.name,
                path=str(path),
                files=files,
                subdirectories=subdirectories,
                subdirectory_info=subdirectory_info
            )

        except Exception as e:
            raise RepositoryAnalysisError(
                f"Failed to analyze directory {path}: {str(e)}",
                ErrorSeverity.MEDIUM
            ) from e

    @with_error_handling(ErrorCategory.DOC_GEN, ErrorSeverity.MEDIUM)
    async def _detect_repo_type(self, structure: DirectoryInfo) -> Optional[str]:
        """Detect repository type based on file patterns."""
        try:
            matches = {repo_type: 0 for repo_type in self.REPO_TYPE_PATTERNS}
            
            for pattern_type, patterns in self.REPO_TYPE_PATTERNS.items():
                for pattern in patterns:
                    if self._find_pattern(structure, pattern):
                        matches[pattern_type] += 1

            # Find type with most matches
            if matches:
                best_match = max(matches.items(), key=lambda x: x[1])
                if best_match[1] > 0:
                    return best_match[0]

            return None

        except Exception as e:
            raise RepositoryAnalysisError(
                f"Failed to detect repository type: {str(e)}",
                ErrorSeverity.MEDIUM
            ) from e

    @with_error_handling(ErrorCategory.DOC_GEN, ErrorSeverity.LOW)
    async def _extract_patterns(self, structure: DirectoryInfo, repo_type: str) -> RepositoryPatterns:
        """Extract common patterns for the repository type."""
        try:
            # Get patterns for the repository type, or use an empty list if type is unknown
            type_patterns = self.REPO_TYPE_PATTERNS.get(repo_type, [])
            
            return RepositoryPatterns(
                repository_type=repo_type,
                common_files=[p for p in type_patterns if self._find_pattern(structure, p)],
                detected_languages=await self._detect_languages(structure)
            )

        except Exception as e:
            raise RepositoryAnalysisError(
                f"Failed to extract patterns: {str(e)}",
                ErrorSeverity.LOW
            ) from e

    def _find_pattern(self, structure: DirectoryInfo, pattern: str) -> bool:
        """Find if a pattern exists in the directory structure."""
        for file in structure.files:
            if pattern in file.path or pattern == file.name:
                return True
        
        for directory in structure.subdirectory_info:
            if pattern in directory.path or pattern == directory.name:
                return True
            if self._find_pattern(directory, pattern):
                return True
                
        return False

    @with_error_handling(ErrorCategory.DOC_GEN, ErrorSeverity.LOW)
    async def _detect_languages(self, structure: DirectoryInfo) -> Dict[str, int]:
        """Detect programming languages used in the repository."""
        try:
            languages = {}
            for file in structure.files:
                if file.type in ["py", "java", "js", "ts", "go", "rb", "php", "cs"]:
                    languages[file.type] = languages.get(file.type, 0) + 1
            
            for directory in structure.subdirectory_info:
                subdir_languages = await self._detect_languages(directory)
                for lang, count in subdir_languages.items():
                    languages[lang] = languages.get(lang, 0) + count
            
            return languages

        except Exception as e:
            raise RepositoryAnalysisError(
                f"Failed to detect languages: {str(e)}",
                ErrorSeverity.LOW
            ) from e