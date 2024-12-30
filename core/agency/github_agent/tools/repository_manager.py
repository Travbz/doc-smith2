"""Tool for managing GitHub repository operations."""
from typing import Dict, Any, Optional, List
import os
import tempfile
from pathlib import Path
import subprocess
from datetime import datetime

from core.services.logging import setup_logger
from core.services.cache import cache_manager
from core.services.error_handling.error_handler import (
    with_error_handling,
    ErrorCategory,
    ErrorSeverity,
    DocSmithError,
    APIError
)

logger = setup_logger(__name__)

class RepositoryError(DocSmithError):
    """Repository operation specific error."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.API,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )

class RepositoryManager:
    """Manages GitHub repository operations."""

    def __init__(self, agent):
        """Initialize repository manager."""
        self.agent = agent
        self.cache = cache_manager
        self._repos = {}
        self._cloned_repos = {}

    @with_error_handling(ErrorCategory.API, ErrorSeverity.HIGH)
    async def clone_repository(self, repo_url: str) -> Dict[str, Any]:
        """Clone a repository locally.
        
        Args:
            repo_url: Repository URL or owner/name format
            
        Returns:
            Dictionary containing repository information
        """
        try:
            # Parse repository information
            repo_name = self._parse_repo_url(repo_url)
            if not repo_name:
                raise RepositoryError(
                    f"Invalid repository URL: {repo_url}",
                    context={"url": repo_url},
                    recovery_hint="Use format owner/repo or full GitHub URL"
                )

            # Create temporary directory for clone
            clone_dir = tempfile.mkdtemp(prefix="docsmith_")
            
            try:
                # Construct clone URL
                clone_url = f"https://github.com/{repo_name}.git"
                
                # Clone repository using git CLI
                result = subprocess.run(
                    ["git", "clone", clone_url, clone_dir],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                if result.returncode != 0:
                    raise RepositoryError(
                        f"Git clone failed: {result.stderr}",
                        context={"repo": repo_name, "error": result.stderr},
                        recovery_hint="Check repository permissions and network connection"
                    )
                
                # Get default branch using git CLI
                result = subprocess.run(
                    ["git", "-C", clone_dir, "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                default_branch = result.stdout.strip()
                
                # Track cloned repository
                self._cloned_repos[repo_name] = {
                    "path": clone_dir,
                    "cloned_at": datetime.now()
                }
                
                logger.info(f"Cloned repository: {repo_name}")
                return {
                    "success": True,
                    "data": {
                        "local_path": clone_dir,
                        "default_branch": default_branch,
                        "full_name": repo_name
                    }
                }
                
            except subprocess.CalledProcessError as e:
                raise RepositoryError(
                    f"Git operation failed: {e.stderr}",
                    context={"repo": repo_name, "error": e.stderr},
                    recovery_hint="Check git command output for details"
                ) from e
                
        except Exception as e:
            if isinstance(e, RepositoryError):
                raise
            raise RepositoryError(
                f"Repository operation failed: {str(e)}",
                context={"repo": repo_url},
                recovery_hint="Check repository URL and permissions"
            ) from e

    def _parse_repo_url(self, repo_url: str) -> Optional[str]:
        """Parse repository URL into owner/name format."""
        if "/" not in repo_url:
            return None
            
        if "github.com" in repo_url:
            parts = repo_url.split("/")
            if len(parts) < 2:
                return None
            return f"{parts[-2]}/{parts[-1].replace('.git', '')}"
            
        return repo_url

    @with_error_handling(ErrorCategory.API, ErrorSeverity.HIGH)
    async def create_branch(self, repo_path: str, branch_name: str) -> None:
        """Create and checkout a new branch.
        
        Args:
            repo_path: Local repository path
            branch_name: Name of the branch to create
        """
        try:
            # Create and checkout branch
            result = subprocess.run(
                ["git", "-C", repo_path, "checkout", "-b", branch_name],
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.returncode != 0:
                raise RepositoryError(
                    f"Failed to create branch: {result.stderr}",
                    context={"branch": branch_name, "error": result.stderr}
                )
                
            logger.info(f"Created branch: {branch_name}")
            
        except subprocess.CalledProcessError as e:
            raise RepositoryError(
                f"Git operation failed: {e.stderr}",
                context={"branch": branch_name, "error": e.stderr}
            ) from e

    @with_error_handling(ErrorCategory.API, ErrorSeverity.HIGH)
    async def write_file(self, repo_path: str, file_path: str, content: str) -> None:
        """Write content to a file in the repository.
        
        Args:
            repo_path: Local repository path
            file_path: Path to the file relative to repo root
            content: File content to write
        """
        try:
            full_path = os.path.join(repo_path, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w') as f:
                f.write(content)
                
            logger.info(f"Wrote file: {file_path}")
            
        except Exception as e:
            raise RepositoryError(
                f"Failed to write file: {str(e)}",
                context={"file": file_path, "error": str(e)}
            ) from e

    @with_error_handling(ErrorCategory.API, ErrorSeverity.HIGH)
    async def commit_changes(self, repo_path: str, message: str, files: Optional[List[str]] = None) -> None:
        """Commit changes to the repository.
        
        Args:
            repo_path: Local repository path
            message: Commit message
            files: Optional list of files to commit (commits all if None)
        """
        try:
            # Add files
            if files:
                for file_path in files:
                    result = subprocess.run(
                        ["git", "-C", repo_path, "add", file_path],
                        capture_output=True,
                        text=True,
                        check=True
                    )
            else:
                result = subprocess.run(
                    ["git", "-C", repo_path, "add", "."],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
            if result.returncode != 0:
                raise RepositoryError(
                    f"Failed to stage changes: {result.stderr}",
                    context={"error": result.stderr}
                )
                
            # Commit changes
            result = subprocess.run(
                ["git", "-C", repo_path, "commit", "-m", message],
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.returncode != 0:
                raise RepositoryError(
                    f"Failed to commit changes: {result.stderr}",
                    context={"error": result.stderr}
                )
                
            logger.info("Committed changes")
            
        except subprocess.CalledProcessError as e:
            raise RepositoryError(
                f"Git operation failed: {e.stderr}",
                context={"error": e.stderr}
            ) from e

    @with_error_handling(ErrorCategory.API, ErrorSeverity.HIGH)
    async def push_changes(self, repo_path: str, branch_name: str) -> None:
        """Push changes to remote repository.
        
        Args:
            repo_path: Local repository path
            branch_name: Name of the branch to push
        """
        try:
            result = subprocess.run(
                ["git", "-C", repo_path, "push", "origin", branch_name],
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.returncode != 0:
                raise RepositoryError(
                    f"Failed to push changes: {result.stderr}",
                    context={"branch": branch_name, "error": result.stderr}
                )
                
            logger.info(f"Pushed changes to {branch_name}")
            
        except subprocess.CalledProcessError as e:
            raise RepositoryError(
                f"Git operation failed: {e.stderr}",
                context={"branch": branch_name, "error": e.stderr}
            ) from e

    async def cleanup(self) -> None:
        """Cleanup temporary repositories."""
        for repo_info in self._cloned_repos.values():
            try:
                if os.path.exists(repo_info["path"]):
                    subprocess.run(
                        ["rm", "-rf", repo_info["path"]],
                        check=True
                    )
            except Exception as e:
                logger.error(f"Error cleaning up repository: {str(e)}")
                
        self._cloned_repos.clear()
