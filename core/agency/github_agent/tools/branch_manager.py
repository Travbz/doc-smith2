"""Tool for managing GitHub repository branches."""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import re
from github import Github, GithubException
from core.services.logging import setup_logger
from core.services.cache import cache_manager
from core.services.error_handling.error_handler import (
    with_error_handling,
    ErrorCategory,
    ErrorSeverity,
    DocSmithError,
    APIError,
)

logger = setup_logger(__name__)

class BranchError(DocSmithError):
    """Branch operation specific error."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.API,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )

class BranchManager:
    """Manages GitHub repository branch operations."""

    def __init__(self, agent):
        """Initialize branch manager."""
        self.agent = agent
        self.cache = cache_manager

    @with_error_handling(ErrorCategory.API, ErrorSeverity.HIGH)
    async def create_branch(
        self,
        repo: str,
        branch_name: str,
        base_branch: Optional[str] = None
    ) -> Dict:
        """Create a new branch in the repository.
        
        Args:
            repo: Repository full name (owner/repo)
            branch_name: Name for new branch
            base_branch: Base branch to create from (default: repo default branch)
            
        Returns:
            Dictionary containing branch information
        """
        try:
            # Get repository
            github_repo = await self.agent.repo_manager.get_repository(repo)
            if not github_repo:
                raise BranchError(
                    f"Repository not found: {repo}",
                    context={"repo": repo},
                    recovery_hint="Verify repository name and permissions"
                )

            # Get base branch
            if not base_branch:
                base_branch = github_repo.default_branch

            # Get base branch reference
            try:
                base_ref = github_repo.get_branch(base_branch)
            except GithubException as e:
                raise BranchError(
                    f"Base branch {base_branch} not found",
                    context={
                        "repo": repo,
                        "base_branch": base_branch
                    },
                    recovery_hint="Verify base branch exists"
                ) from e

            try:
                # Create new branch
                ref = github_repo.create_git_ref(
                    ref=f"refs/heads/{branch_name}",
                    sha=base_ref.commit.sha
                )
                
                logger.info(f"Created branch: {branch_name}")
                return {
                    "status": "success",
                    "data": {
                        "name": branch_name,
                        "sha": ref.object.sha,
                        "base_branch": base_branch,
                        "url": f"https://github.com/{repo}/tree/{branch_name}"
                    }
                }

            except GithubException as e:
                if e.status == 422:  # Branch exists
                    raise BranchError(
                        f"Branch {branch_name} already exists",
                        context={"branch": branch_name},
                        recovery_hint="Use a different branch name"
                    ) from e
                raise

        except BranchError:
            raise
        except Exception as e:
            raise BranchError(
                f"Error creating branch: {str(e)}",
                context={"repo": repo, "branch": branch_name}
            ) from e

    @with_error_handling(ErrorCategory.API, ErrorSeverity.HIGH)
    async def delete_branch(
        self,
        repo: str,
        branch_name: str
    ) -> Dict:
        """Delete a branch from the repository."""
        try:
            github_repo = await self.agent.repo_manager.get_repository(repo)
            if not github_repo:
                raise BranchError(f"Repository not found: {repo}")

            try:
                ref = github_repo.get_git_ref(f"heads/{branch_name}")
                ref.delete()
                
                logger.info(f"Deleted branch: {branch_name}")
                return {
                    "status": "success",
                    "data": {
                        "branch": branch_name,
                        "deleted": True
                    }
                }

            except GithubException as e:
                if e.status == 404:
                    raise BranchError(
                        f"Branch {branch_name} not found",
                        context={"branch": branch_name},
                        recovery_hint="Verify branch name"
                    ) from e
                raise

        except BranchError:
            raise
        except Exception as e:
            raise BranchError(
                f"Error deleting branch: {str(e)}",
                context={"repo": repo, "branch": branch_name}
            ) from e

    @with_error_handling(ErrorCategory.API, ErrorSeverity.HIGH)
    async def protect_branch(
        self,
        repo: str,
        branch_name: str,
        required_reviews: int = 1,
        enforce_admins: bool = True
    ) -> Dict:
        """Add protection rules to a branch."""
        try:
            github_repo = await self.agent.repo_manager.get_repository(repo)
            if not github_repo:
                raise BranchError(f"Repository not found: {repo}")

            try:
                branch = github_repo.get_branch(branch_name)
                branch.edit_protection(
                    strict=True,
                    required_approving_review_count=required_reviews,
                    enforce_admins=enforce_admins
                )
                
                logger.info(f"Protected branch: {branch_name}")
                return {
                    "status": "success",
                    "data": {
                        "branch": branch_name,
                        "protected": True,
                        "required_reviews": required_reviews,
                        "enforce_admins": enforce_admins
                    }
                }

            except GithubException as e:
                if e.status == 404:
                    raise BranchError(f"Branch {branch_name} not found") from e
                raise

        except BranchError:
            raise
        except Exception as e:
            raise BranchError(
                f"Error protecting branch: {str(e)}",
                context={"repo": repo, "branch": branch_name}
            ) from e

    @with_error_handling(ErrorCategory.API, ErrorSeverity.MEDIUM)
    async def sync_branch(
        self,
        repo: str,
        branch_name: str,
        base_branch: Optional[str] = None
    ) -> Dict:
        """Synchronize a branch with its base branch."""
        try:
            github_repo = await self.agent.repo_manager.get_repository(repo)
            if not github_repo:
                raise BranchError(f"Repository not found: {repo}")

            if not base_branch:
                base_branch = github_repo.default_branch

            try:
                # Get latest commit from base branch
                base = github_repo.get_branch(base_branch)
                branch = github_repo.get_branch(branch_name)

                # Create a merge to sync
                merge = github_repo.merge(
                    branch_name,
                    base_branch,
                    f"chore: Sync {branch_name} with {base_branch}"
                )
                
                logger.info(f"Synced branch {branch_name} with {base_branch}")
                return {
                    "status": "success",
                    "data": {
                        "sha": merge.sha,
                        "synced": True,
                        "base_branch": base_branch
                    }
                }

            except GithubException as e:
                if e.status == 404:
                    raise BranchError(
                        f"Branch not found: {branch_name} or {base_branch}",
                        context={"branch": branch_name, "base": base_branch}
                    ) from e
                raise

        except BranchError:
            raise
        except Exception as e:
            raise BranchError(
                f"Error syncing branch: {str(e)}",
                context={
                    "repo": repo,
                    "branch": branch_name,
                    "base_branch": base_branch
                }
            ) from e
