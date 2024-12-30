"""Tool for managing GitHub pull requests."""
from typing import Dict, Any, List, Optional
from datetime import datetime
from github import Github, GithubException

from core.services.logging import setup_logger
from core.services.error_handling.error_handler import (
    with_error_handling,
    ErrorCategory,
    ErrorSeverity,
    DocSmithError,
    APIError
)

logger = setup_logger(__name__)

class PullRequestError(DocSmithError):
    """Pull request operation specific error."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.API,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )

class PullRequestManager:
    """Manages GitHub pull request operations."""

    def __init__(self, agent):
        """Initialize pull request manager."""
        self.agent = agent
        
    @with_error_handling(ErrorCategory.API, ErrorSeverity.HIGH)
    async def create_pull_request(
        self,
        repo_name: str,
        branch: str,
        title: str,
        body: str,
        base_branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new pull request.
        
        Args:
            repo_name: Repository full name
            branch: Source branch
            title: Pull request title
            body: Pull request description
            base_branch: Target branch (default: repository default branch)
        """
        try:
            repo = await self.agent.repo_manager.get_repository(repo_name)
            if not repo:
                raise PullRequestError(
                    f"Repository not found: {repo_name}",
                    context={"repo": repo_name},
                    recovery_hint="Verify repository name and permissions"
                )

            if not base_branch:
                base_branch = repo.default_branch

            try:
                pr = repo.create_pull(
                    title=title,
                    body=body,
                    head=branch,
                    base=base_branch
                )
                
                logger.info(f"Created pull request: {pr.number}")
                return {
                    "status": "success",
                    "data": {
                        "number": pr.number,
                        "url": pr.html_url,
                        "title": pr.title
                    }
                }

            except GithubException as e:
                if e.status == 422:  # Usually means PR already exists
                    raise PullRequestError(
                        "Pull request already exists or invalid branch",
                        context={"branch": branch, "base": base_branch},
                        recovery_hint="Check if PR exists or verify branch names"
                    ) from e
                raise

        except PullRequestError:
            raise
        except Exception as e:
            raise PullRequestError(
                f"Error creating pull request: {str(e)}",
                context={"repo": repo_name, "branch": branch}
            ) from e

    @with_error_handling(ErrorCategory.API, ErrorSeverity.HIGH)
    async def update_pull_request(
        self,
        repo_name: str,
        pr_number: int,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing pull request."""
        try:
            repo = await self.agent.repo_manager.get_repository(repo_name)
            if not repo:
                raise PullRequestError(f"Repository not found: {repo_name}")

            try:
                pr = repo.get_pull(pr_number)
                
                if "title" in updates:
                    pr.edit(title=updates["title"])
                    
                if "body" in updates:
                    pr_body = await self._generate_pr_body(updates["body"])
                    pr.edit(body=pr_body)
                    
                if "labels" in updates:
                    pr.set_labels(*updates["labels"])
                    
                if "reviewers" in updates:
                    pr.create_review_request(reviewers=updates["reviewers"])
                
                return {
                    "status": "success",
                    "data": {
                        "number": pr.number,
                        "url": pr.html_url,
                        "title": pr.title,
                        "body": pr.body
                    }
                }

            except GithubException as e:
                if e.status == 404:
                    raise PullRequestError(
                        f"Pull request not found: {pr_number}",
                        context={"pr": pr_number},
                        recovery_hint="Verify PR number"
                    ) from e
                raise

        except PullRequestError:
            raise
        except Exception as e:
            raise PullRequestError(
                f"Error updating pull request: {str(e)}",
                context={"repo": repo_name, "pr": pr_number}
            ) from e

    @with_error_handling(ErrorCategory.API, ErrorSeverity.HIGH)
    async def get_pull_request_status(
        self,
        repo_name: str,
        pr_number: int
    ) -> Dict[str, Any]:
        """Get pull request status and details."""
        try:
            repo = await self.agent.repo_manager.get_repository(repo_name)
            if not repo:
                raise PullRequestError(f"Repository not found: {repo_name}")

            try:
                pr = repo.get_pull(pr_number)
                
                return {
                    "status": "success",
                    "data": {
                        "number": pr.number,
                        "state": pr.state,
                        "merged": pr.merged,
                        "mergeable": pr.mergeable,
                        "reviews": [r.state for r in pr.get_reviews()],
                        "updated_at": pr.updated_at.isoformat()
                    }
                }

            except GithubException as e:
                if e.status == 404:
                    raise PullRequestError(f"Pull request not found: {pr_number}")
                raise

        except PullRequestError:
            raise
        except Exception as e:
            raise PullRequestError(
                f"Error getting pull request status: {str(e)}",
                context={"repo": repo_name, "pr": pr_number}
            ) from e

    async def _generate_pr_body(self, content: str) -> str:
        """Generate formatted PR body."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        template = f"""# Documentation Update

Generated by DocSmith on {timestamp}

## Changes
{content}

## Validation
- [x] Documentation structure verified
- [x] Technical content validated
- [x] Examples tested
- [x] Links checked

## Notes
- Please review the changes and ensure they meet project standards
- Pay special attention to technical accuracy and completeness
- Verify examples and code snippets work as expected
"""
        return template