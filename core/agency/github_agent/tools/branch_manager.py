"""Tool for managing GitHub repository branches."""
from typing import Dict, List, Optional
from datetime import datetime
import re
from github import Github, GithubException
from core.services.logging import setup_logger
from core.services.cache import cache_manager

logger = setup_logger(__name__)

class BranchManager:
    """Manages branch operations for documentation generation."""

    def __init__(self, agent):
        """Initialize branch manager."""
        self.agent = agent
        self.cache = cache_manager

    async def create_documentation_branch(
        self,
        repo: str,
        base_branch: Optional[str] = None
    ) -> Dict:
        """
        Create a new branch for documentation updates.
        
        Args:
            repo: Repository full name (owner/repo)
            base_branch: Optional base branch name (defaults to repo default branch)
            
        Returns:
            Dict containing branch information
        """
        try:
            # Get repository
            github_repo = await self.agent.repo_manager._get_repository(repo)
            if not github_repo:
                raise ValueError(f"Repository not found: {repo}")

            # Get base branch
            if not base_branch:
                base_branch = github_repo.default_branch

            # Generate branch name
            timestamp = datetime.now().strftime('%Y-%m-%d-%H')
            repo_name = repo.split('/')[-1]
            branch_name = f"docs/{repo_name}-{timestamp}"

            # Get base branch reference
            base_ref = github_repo.get_branch(base_branch)
            
            try:
                # Create new branch
                ref = github_repo.create_git_ref(
                    ref=f"refs/heads/{branch_name}",
                    sha=base_ref.commit.sha
                )
                
                logger.info(f"Created documentation branch: {branch_name}")
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
                if e.status == 422:  # Branch already exists
                    # Append increment number to branch name
                    for i in range(1, 100):
                        try:
                            new_branch_name = f"{branch_name}-{i}"
                            ref = github_repo.create_git_ref(
                                ref=f"refs/heads/{new_branch_name}",
                                sha=base_ref.commit.sha
                            )
                            logger.info(f"Created documentation branch: {new_branch_name}")
                            return {
                                "status": "success",
                                "data": {
                                    "name": new_branch_name,
                                    "sha": ref.object.sha,
                                    "base_branch": base_branch,
                                    "url": f"https://github.com/{repo}/tree/{new_branch_name}"
                                }
                            }
                        except GithubException:
                            continue
                    raise ValueError("Could not create unique branch name")
                raise

        except Exception as e:
            logger.error(f"Error creating documentation branch: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def protect_branch(
        self,
        repo: str,
        branch_name: str,
        required_reviews: int = 1
    ) -> Dict:
        """
        Add protection rules to a branch.
        
        Args:
            repo: Repository full name
            branch_name: Branch to protect
            required_reviews: Number of required reviews
            
        Returns:
            Dict containing protection status
        """
        try:
            github_repo = await self.agent.repo_manager._get_repository(repo)
            if not github_repo:
                raise ValueError(f"Repository not found: {repo}")

            branch = github_repo.get_branch(branch_name)
            
            # Configure protection rules
            branch.edit_protection(
                strict=True,  # Require branches to be up to date
                required_approving_review_count=required_reviews,
                enforce_admins=True,
                dismissal_restrictions=None,
                user_push_restrictions=None,
                user_bypass_pull_request_allowances=None
            )
            
            logger.info(f"Added protection rules to branch: {branch_name}")
            return {
                "status": "success",
                "data": {
                    "branch": branch_name,
                    "protected": True,
                    "required_reviews": required_reviews
                }
            }

        except Exception as e:
            logger.error(f"Error protecting branch: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def cleanup_old_branches(
        self,
        repo: str,
        pattern: str = "docs/*/",
        days_old: int = 30
    ) -> Dict:
        """
        Clean up old documentation branches.
        
        Args:
            repo: Repository full name
            pattern: Branch name pattern to match
            days_old: Age in days to consider for cleanup
            
        Returns:
            Dict containing cleanup results
        """
        try:
            github_repo = await self.agent.repo_manager._get_repository(repo)
            if not github_repo:
                raise ValueError(f"Repository not found: {repo}")

            cutoff_date = datetime.now() - timedelta(days=days_old)
            branches_deleted = []
            branches_kept = []

            # Get all branches matching pattern
            for branch in github_repo.get_branches():
                if re.match(pattern, branch.name):
                    # Extract date from branch name
                    match = re.search(r'(\d{4}-\d{2}-\d{2})', branch.name)
                    if match:
                        branch_date = datetime.strptime(match.group(1), '%Y-%m-%d')
                        if branch_date < cutoff_date:
                            # Delete branch if old enough
                            ref = github_repo.get_git_ref(f"heads/{branch.name}")
                            ref.delete()
                            branches_deleted.append(branch.name)
                        else:
                            branches_kept.append(branch.name)

            logger.info(f"Cleaned up {len(branches_deleted)} old documentation branches")
            return {
                "status": "success",
                "data": {
                    "deleted_branches": branches_deleted,
                    "kept_branches": branches_kept
                }
            }

        except Exception as e:
            logger.error(f"Error cleaning up branches: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def merge_branch(
        self,
        repo: str,
        branch_name: str,
        base_branch: Optional[str] = None
    ) -> Dict:
        """
        Merge a documentation branch.
        
        Args:
            repo: Repository full name
            branch_name: Branch to merge
            base_branch: Target branch for merge
            
        Returns:
            Dict containing merge status
        """
        try:
            github_repo = await self.agent.repo_manager._get_repository(repo)
            if not github_repo:
                raise ValueError(f"Repository not found: {repo}")

            if not base_branch:
                base_branch = github_repo.default_branch

            # Create merge
            merge = github_repo.merge(
                base_branch,
                branch_name,
                f"docs: Merge documentation updates from {branch_name}"
            )
            
            logger.info(f"Merged branch {branch_name} into {base_branch}")
            return {
                "status": "success",
                "data": {
                    "sha": merge.sha,
                    "merged": True,
                    "message": f"Merged {branch_name} into {base_branch}"
                }
            }

        except Exception as e:
            logger.error(f"Error merging branch: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def sync_branch(
        self,
        repo: str,
        branch_name: str,
        base_branch: Optional[str] = None
    ) -> Dict:
        """
        Sync a branch with its base branch.
        
        Args:
            repo: Repository full name
            branch_name: Branch to sync
            base_branch: Base branch to sync from
            
        Returns:
            Dict containing sync status
        """
        try:
            github_repo = await self.agent.repo_manager._get_repository(repo)
            if not github_repo:
                raise ValueError(f"Repository not found: {repo}")

            if not base_branch:
                base_branch = github_repo.default_branch

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

        except Exception as e:
            logger.error(f"Error syncing branch: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }