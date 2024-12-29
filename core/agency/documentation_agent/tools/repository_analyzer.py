"""Tool for analyzing repository structure and determining type."""
from typing import Dict, List, Optional
from pathlib import Path
import os
import logging
from core.services.logging import setup_logger
from core.services.cache import cache_manager
from ..schemas.repository_analysis import (
    FileInfo,
    DirectoryInfo,
    RepositoryPatterns,
    RepositoryAnalysis
)

logger = setup_logger(__name__)

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

    async def analyze_repository(self, repo_path: str) -> RepositoryAnalysis:
        """
        Analyze a repository and determine its type and structure.
        
        Args:
            repo_path: Path to the repository root
            
        Returns:
            RepositoryAnalysis object with analysis results
        """
        logger.info(f"Analyzing repository at: {repo_path}")
        
        try:
            # Check cache first
            cache_key = f"repo_analysis_{repo_path}"
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.info("Using cached repository analysis")
                return cached_result

            # Get repository structure
            root_dir = await self._analyze_directory(Path(repo_path))
            
            # Detect patterns
            patterns = await self._detect_patterns(repo_path)
            
            # Determine repository type
            repo_type = await self._determine_repo_type(patterns)
            
            # Get language statistics
            languages = await self._analyze_languages(repo_path)
            
            # Create analysis result
            analysis = RepositoryAnalysis(
                repository_type=repo_type,
                root_directory=root_dir,
                detected_patterns=patterns,
                languages=languages,
                primary_language=max(languages.items(), key=lambda x: x[1])[0] if languages else None,
                total_files=sum(1 for _ in Path(repo_path).rglob("*") if _.is_file()),
                total_size=sum(_.stat().st_size for _ in Path(repo_path).rglob("*") if _.is_file()),
                analysis_timestamp=str(datetime.now())
            )
            
            # Cache the result
            self.cache.set(cache_key, analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing repository: {str(e)}", exc_info=True)
            raise

    async def _analyze_directory(self, path: Path) -> DirectoryInfo:
        """Analyze a directory and its contents."""
        files = []
        subdirs = []
        
        for item in path.iterdir():
            if item.is_file():
                files.append(FileInfo(
                    path=str(item.relative_to(path.parent)),
                    type=item.suffix,
                    size=item.stat().st_size,
                    last_modified=str(datetime.fromtimestamp(item.stat().st_mtime))
                ))
            elif item.is_dir() and not item.name.startswith('.'):
                subdirs.append(item.name)
                
        return DirectoryInfo(
            path=str(path.relative_to(path.parent)),
            files=files,
            subdirectories=subdirs
        )

    async def _detect_patterns(self, repo_path: str) -> RepositoryPatterns:
        """Detect repository patterns."""
        patterns = RepositoryPatterns()
        repo_path = Path(repo_path)
        
        for repo_type, type_patterns in self.REPO_TYPE_PATTERNS.items():
            detected = []
            for pattern in type_patterns:
                pattern_path = repo_path / pattern
                if pattern_path.exists():
                    detected.append(pattern)
                    
            if repo_type == "spring_boot":
                patterns.spring_boot_patterns = detected
            elif repo_type == "nginx":
                patterns.nginx_patterns = detected
            elif repo_type == "bounded_context":
                patterns.bounded_context_patterns = detected
            elif repo_type == "python":
                patterns.python_patterns = detected
                
        return patterns

    async def _determine_repo_type(self, patterns: RepositoryPatterns) -> str:
        """Determine repository type based on detected patterns."""
        pattern_counts = {
            "spring_boot": len(patterns.spring_boot_patterns),
            "nginx": len(patterns.nginx_patterns),
            "bounded_context": len(patterns.bounded_context_patterns),
            "python": len(patterns.python_patterns)
        }
        
        # Require at least 2 matching patterns for a type
        matches = {k: v for k, v in pattern_counts.items() if v >= 2}
        
        if not matches:
            return "unknown"
            
        return max(matches.items(), key=lambda x: x[1])[0]

    async def _analyze_languages(self, repo_path: str) -> Dict[str, int]:
        """Analyze programming languages used in the repository."""
        extensions = {
            ".py": "Python",
            ".java": "Java",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".go": "Go",
            ".rb": "Ruby",
            ".php": "PHP",
            ".cs": "C#",
            ".cpp": "C++",
            ".rs": "Rust",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".scala": "Scala",
            ".html": "HTML",
            ".css": "CSS",
            ".sql": "SQL",
            ".sh": "Shell",
            ".tf": "Terraform",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".json": "JSON",
            ".md": "Markdown"
        }
        
        language_lines = {}
        repo_path = Path(repo_path)
        
        for ext, lang in extensions.items():
            line_count = 0
            for file_path in repo_path.rglob(f"*{ext}"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        line_count += sum(1 for _ in f)
                except Exception:
                    continue
                    
            if line_count > 0:
                language_lines[lang] = line_count
                
        return language_lines