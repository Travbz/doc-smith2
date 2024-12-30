"""Tool for managing GitHub comments and review feedback."""
from typing import Dict, List, Optional, Union, Any
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

class CommentError(DocSmithError):
    """Comment operation specific error."""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.API,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )

class CommentManager:
    """Manages GitHub comments and review feedback."""

    def __init__(self, agent):
        """Initialize comment manager."""
        self.agent = agent
        self.active_reviews: Dict[str, Dict] = {}

    @with_error_handling(ErrorCategory.API, ErrorSeverity.MEDIUM)
    async def create_review_comment(
        self,
        repo_name: str,
        pr_number: int,
        comment: str,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a review comment on a pull request.
        
        Args:
            repo_name: Repository full name
            pr_number: Pull request number
            comment: Comment content
            file_path: File to comment on
            line_number: Line number to comment on
        """
        try:
            repo = await self.agent.repo_manager.get_repository(repo_name)
            if not repo:
                raise CommentError(
                    f"Repository not found: {repo_name}",
                    context={"repo": repo_name},
                    recovery_hint="Verify repository name and permissions"
                )

            try:
                pr = repo.get_pull(pr_number)
                
                if file_path and line_number:
                    # Create a comment on a specific line
                    commit = list(pr.get_commits())[-1]
                    comment = pr.create_review_comment(
                        body=comment,
                        commit_id=commit.sha,
                        path=file_path,
                        line=line_number
                    )
                else:
                    # Create a general PR comment
                    comment = pr.create_issue_comment(comment)
                
                return {
                    "status": "success",
                    "data": {
                        "id": comment.id,
                        "body": comment.body,
                        "created_at": comment.created_at.isoformat()
                    }
                }

            except GithubException as e:
                if e.status == 404:
                    raise CommentError(
                        f"Pull request not found: {pr_number}",
                        context={"pr": pr_number},
                        recovery_hint="Verify PR number"
                    ) from e
                raise

        except CommentError:
            raise
        except Exception as e:
            raise CommentError(
                f"Error creating comment: {str(e)}",
                context={
                    "repo": repo_name,
                    "pr": pr_number,
                    "file": file_path,
                    "line": line_number
                }
            ) from e

    @with_error_handling(ErrorCategory.API, ErrorSeverity.MEDIUM)
    async def create_review(
        self,
        repo_name: str,
        pr_number: int,
        review_comments: List[Dict[str, Any]],
        review_body: str,
        event: str = "COMMENT"
    ) -> Dict[str, Any]:
        """Create a complete review with multiple comments.
        
        Args:
            repo_name: Repository full name
            pr_number: Pull request number
            review_comments: List of review comments with file and line info
            review_body: Overall review message
            event: Review event (COMMENT/APPROVE/REQUEST_CHANGES)
        """
        try:
            repo = await self.agent.repo_manager.get_repository(repo_name)
            if not repo:
                raise CommentError(f"Repository not found: {repo_name}")

            try:
                pr = repo.get_pull(pr_number)
                commit = list(pr.get_commits())[-1]
                
                # Create the review with comments
                review = pr.create_review(
                    commit=commit,
                    body=review_body,
                    event=event,
                    comments=[{
                        'body': c['comment'],
                        'path': c['file_path'],
                        'line': c['line_number'],
                        'position': c.get('position')
                    } for c in review_comments if 'file_path' in c and 'line_number' in c]
                )
                
                return {
                    "status": "success",
                    "data": {
                        "id": review.id,
                        "state": review.state,
                        "submitted_at": review.submitted_at.isoformat() if review.submitted_at else None
                    }
                }

            except GithubException as e:
                if e.status == 404:
                    raise CommentError(f"Pull request not found: {pr_number}")
                raise

        except CommentError:
            raise
        except Exception as e:
            raise CommentError(
                f"Error creating review: {str(e)}",
                context={"repo": repo_name, "pr": pr_number}
            ) from e

    @with_error_handling(ErrorCategory.API, ErrorSeverity.LOW)
    async def get_review_comments(
        self,
        repo_name: str,
        pr_number: int
    ) -> Dict[str, Any]:
        """Get all review comments from a pull request."""
        try:
            repo = await self.agent.repo_manager.get_repository(repo_name)
            if not repo:
                raise CommentError(f"Repository not found: {repo_name}")

            try:
                pr = repo.get_pull(pr_number)
                comments = []
                
                for comment in pr.get_review_comments():
                    comments.append({
                        "id": comment.id,
                        "body": comment.body,
                        "path": comment.path,
                        "line": comment.line,
                        "created_at": comment.created_at.isoformat(),
                        "updated_at": comment.updated_at.isoformat()
                    })
                
                return {
                    "status": "success",
                    "data": {"comments": comments}
                }

            except GithubException as e:
                if e.status == 404:
                    raise CommentError(f"Pull request not found: {pr_number}")
                raise

        except CommentError:
            raise
        except Exception as e:
            raise CommentError(
                f"Error getting review comments: {str(e)}",
                context={"repo": repo_name, "pr": pr_number}
            ) from e

    @with_error_handling(ErrorCategory.API, ErrorSeverity.LOW)
    async def update_comment(
        self,
        repo_name: str,
        comment_id: int,
        body: str
    ) -> Dict[str, Any]:
        """Update an existing comment."""
        try:
            repo = await self.agent.repo_manager.get_repository(repo_name)
            if not repo:
                raise CommentError(f"Repository not found: {repo_name}")

            try:
                comment = repo.get_comment(comment_id)
                comment.edit(body)
                
                return {
                    "status": "success",
                    "data": {
                        "id": comment.id,
                        "body": comment.body,
                        "updated_at": comment.updated_at.isoformat()
                    }
                }

            except GithubException as e:
                if e.status == 404:
                    raise CommentError(
                        f"Comment not found: {comment_id}",
                        context={"comment_id": comment_id},
                        recovery_hint="Verify comment ID"
                    ) from e
                raise

        except CommentError:
            raise
        except Exception as e:
            raise CommentError(
                f"Error updating comment: {str(e)}",
                context={"repo": repo_name, "comment_id": comment_id}
            ) from e

    @with_error_handling(ErrorCategory.API, ErrorSeverity.LOW)
    async def resolve_conversation(
        self,
        repo_name: str,
        pr_number: int,
        thread_id: int
    ) -> Dict[str, Any]:
        """Resolve a comment thread/conversation."""
        try:
            repo = await self.agent.repo_manager.get_repository(repo_name)
            if not repo:
                raise CommentError(f"Repository not found: {repo_name}")

            try:
                pr = repo.get_pull(pr_number)
                thread = pr.get_review_comment(thread_id)
                
                # Mark thread as resolved by adding a resolution comment
                resolution_comment = thread.create_reply(
                    "✅ Resolved by DocSmith review agent"
                )
                
                return {
                    "status": "success",
                    "data": {
                        "thread_id": thread_id,
                        "resolved_at": datetime.now().isoformat(),
                        "resolution_comment_id": resolution_comment.id
                    }
                }

            except GithubException as e:
                if e.status == 404:
                    raise CommentError(f"Thread not found: {thread_id}")
                raise

        except CommentError:
            raise
        except Exception as e:
            raise CommentError(
                f"Error resolving conversation: {str(e)}",
                context={
                    "repo": repo_name,
                    "pr": pr_number,
                    "thread": thread_id
                }
            ) from e
