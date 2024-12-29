"""Tool for revising documentation content based on feedback."""
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import difflib
from core.services.logging import setup_logger
from core.services.cache import cache_manager
from ..schemas.generated_content import GeneratedContent, DocumentFile

logger = setup_logger(__name__)

class ContentReviser:
    """Revises documentation content based on feedback."""

    def __init__(self):
        """Initialize the content reviser."""
        self.cache = cache_manager
        self.revision_history: Dict[str, List[Dict]] = {}

    async def revise_content(
        self,
        documentation: GeneratedContent,
        feedback: Dict[str, List[Dict]],
        iteration: int
    ) -> GeneratedContent:
        """
        Revise documentation content based on feedback.
        
        Args:
            documentation: Current documentation content
            feedback: Organized feedback by file
            iteration: Current revision iteration
            
        Returns:
            Updated documentation content
        """
        try:
            # Create a copy of the documentation to modify
            revised_docs = GeneratedContent(**documentation.dict())
            
            for file_path, feedback_items in feedback.items():
                if file_path == 'general':
                    # Handle general feedback that applies to all files
                    await self._apply_general_feedback(revised_docs, feedback_items)
                    continue
                    
                if file_path in revised_docs.files:
                    # Revise specific file
                    revised_file = await self._revise_file(
                        revised_docs.files[file_path],
                        feedback_items,
                        iteration
                    )
                    revised_docs.files[file_path] = revised_file
                    
            # Update metadata
            revised_docs.documentation_version = f"{documentation.documentation_version}-rev{iteration}"
            
            return revised_docs

        except Exception as e:
            logger.error(f"Error revising content: {str(e)}")
            raise

    async def _revise_file(
        self,
        doc_file: DocumentFile,
        feedback_items: List[Dict],
        iteration: int
    ) -> DocumentFile:
        """Revise a single documentation file."""
        try:
            # Create working copy
            revised_file = DocumentFile(**doc_file.dict())
            original_content = doc_file.content
            
            # Apply feedback items in priority order
            for item in feedback_items:
                revised_content = await self._apply_feedback_item(
                    revised_file.content,
                    item
                )
                revised_file.content = revised_content
                
            # Update sections if content changed
            if revised_file.content != original_content:
                revised_file.sections = await self._update_sections(
                    revised_file.content
                )
                
            # Track revision
            await self._track_revision(
                doc_file.path,
                original_content,
                revised_file.content,
                feedback_items,
                iteration
            )
            
            return revised_file

        except Exception as e:
            logger.error(f"Error revising file: {str(e)}")
            raise

    async def _apply_general_feedback(
        self,
        documentation: GeneratedContent,
        feedback_items: List[Dict]
    ) -> None:
        """Apply general feedback that affects all documentation."""
        try:
            for item in feedback_items:
                for file_path in documentation.files:
                    doc_file = documentation.files[file_path]
                    revised_content = await self._apply_feedback_item(
                        doc_file.content,
                        item
                    )
                    if revised_content != doc_file.content:
                        doc_file.content = revised_content
                        doc_file.sections = await self._update_sections(revised_content)
        except Exception as e:
            logger.error(f"Error applying general feedback: {str(e)}")
            raise

    async def _apply_feedback_item(
        self,
        content: str,
        feedback: Dict
    ) -> str:
        """Apply a single feedback item to content."""
        try:
            if feedback.get('suggested_changes'):
                # Apply specific suggested changes
                return await self._apply_suggested_changes(
                    content,
                    feedback['suggested_changes'],
                    feedback.get('location', {})
                )
            elif feedback.get('type') == 'issue':
                # Handle issues without specific suggestions
                return await self._handle_issue(
                    content,
                    feedback
                )
            else:
                # Handle other feedback types
                return await self._handle_general_feedback(
                    content,
                    feedback
                )

        except Exception as e:
            logger.error(f"Error applying feedback item: {str(e)}")
            return content

    async def _apply_suggested_changes(
        self,
        content: str,
        suggestions: str,
        location: Dict
    ) -> str:
        """Apply suggested changes to specific location in content."""
        try:
            lines = content.splitlines()
            
            if 'line' in location:
                # Apply change to specific line
                line_num = location['line']
                if 0 <= line_num < len(lines):
                    lines[line_num] = suggestions
            else:
                # Try to find the best location for the change
                content_blocks = content.split('\n\n')
                best_block = self._find_best_match(suggestions, content_blocks)
                if best_block is not None:
                    content_blocks[best_block] = suggestions
                    return '\n\n'.join(content_blocks)
                    
            return '\n'.join(lines)

        except Exception as e:
            logger.error(f"Error applying suggested changes: {str(e)}")
            return content

    async def _handle_issue(
        self,
        content: str,
        feedback: Dict
    ) -> str:
        """Handle issue-type feedback without specific suggestions."""
        try:
            # Extract the issue area if location is provided
            if 'location' in feedback:
                location = feedback['location']
                if 'line' in location:
                    lines = content.splitlines()
                    line_num = location['line']
                    if 0 <= line_num < len(lines):
                        # Attempt to fix common issues
                        fixed_line = await self._fix_common_issues(
                            lines[line_num],
                            feedback['message']
                        )
                        lines[line_num] = fixed_line
                        return '\n'.join(lines)
            
            # If no location or can't fix specifically, apply general improvements
            return await self._improve_content(content, feedback['message'])
            
        except Exception as e:
            logger.error(f"Error handling issue: {str(e)}")
            return content

    async def _handle_general_feedback(
        self,
        content: str,
        feedback: Dict
    ) -> str:
        """Handle general improvement feedback."""
        try:
            feedback_type = feedback.get('type', '')
            message = feedback.get('message', '')
            
            if 'clarity' in feedback_type.lower():
                return await self._improve_clarity(content)
            elif 'structure' in feedback_type.lower():
                return await self._improve_structure(content)
            elif 'completeness' in feedback_type.lower():
                return await self._improve_completeness(content, message)
            else:
                return await self._improve_content(content, message)
                
        except Exception as e:
            logger.error(f"Error handling general feedback: {str(e)}")
            return content

    async def _update_sections(
        self,
        content: str
    ) -> List:
        """Update section breakdown after content changes."""
        sections = []
        current_section = None
        order = 1
        
        for line in content.splitlines():
            if line.startswith('#'):
                if current_section:
                    sections.append(current_section)
                
                # Start new section
                level = len(line.split()[0])  # Count # symbols
                title = line.lstrip('#').strip()
                current_section = {
                    'title': title,
                    'content': line + '\n',
                    'level': level,
                    'order': order
                }
                order += 1
            elif current_section:
                current_section['content'] += line + '\n'
                
        if current_section:
            sections.append(current_section)
            
        return sections

    def _find_best_match(
        self,
        text: str,
        blocks: List[str]
    ) -> Optional[int]:
        """Find the best matching block for text insertion."""
        if not blocks:
            return None
            
        # Use difflib to find closest match
        matcher = difflib.get_close_matches(text, blocks, n=1, cutoff=0.3)
        if matcher:
            return blocks.index(matcher[0])
            
        return None

    async def _track_revision(
        self,
        file_path: str,
        original: str,
        revised: str,
        feedback_items: List[Dict],
        iteration: int
    ) -> None:
        """Track revision history for a file."""
        if file_path not in self.revision_history:
            self.revision_history[file_path] = []
            
        revision = {
            'timestamp': datetime.now().isoformat(),
            'iteration': iteration,
            'feedback_items': feedback_items,
            'changes': await self._compute_changes(original, revised)
        }
        
        self.revision_history[file_path].append(revision)
        
        # Cache revision history
        cache_key = f"revision_history_{file_path}"
        self.cache.set(cache_key, self.revision_history[file_path])

    async def _compute_changes(
        self,
        original: str,
        revised: str
    ) -> List[Dict]:
        """Compute detailed changes between versions."""
        changes = []
        
        # Split into lines and compute diff
        original_lines = original.splitlines()
        revised_lines = revised.splitlines()
        differ = difflib.unified_diff(
            original_lines,
            revised_lines,
            lineterm=''
        )
        
        # Process diff output
        current_section = None
        for line in differ:
            if line.startswith('---') or line.startswith('+++'):
                continue
                
            if line.startswith('@@'):
                # New section of changes
                if current_section:
                    changes.append(current_section)
                current_section = {
                    'type': 'section',
                    'changes': []
                }
                continue
                
            if current_section is None:
                continue
                
            if line.startswith('-'):
                current_section['changes'].append({
                    'type': 'removal',
                    'content': line[1:].strip()
                })
            elif line.startswith('+'):
                current_section['changes'].append({
                    'type': 'addition',
                    'content': line[1:].strip()
                })
            else:
                current_section['changes'].append({
                    'type': 'context',
                    'content': line[1:].strip()
                })
                
        # Add final section
        if current_section:
            changes.append(current_section)
            
        return changes

    async def _fix_common_issues(self, line: str, issue_message: str) -> str:
        """Fix common documentation issues in a line."""
        # This would implement specific fixes for common issues
        # based on the issue message
        return line

    async def _improve_clarity(self, content: str) -> str:
        """Improve content clarity."""
        # This would implement clarity improvements
        return content

    async def _improve_structure(self, content: str) -> str:
        """Improve content structure."""
        # This would implement structure improvements
        return content

    async def _improve_completeness(self, content: str, message: str) -> str:
        """Improve content completeness."""
        # This would implement completeness improvements
        return content

    async def _improve_content(self, content: str, message: str) -> str:
        """Apply general content improvements."""
        # This would implement general improvements based on feedback
        return content