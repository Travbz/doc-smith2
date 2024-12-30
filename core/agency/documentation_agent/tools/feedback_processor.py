"""Tool for processing review feedback and managing revisions."""
from typing import Dict, List, Optional
from datetime import datetime
from core.services.logging import setup_logger
from core.services.cache.cache_manager import cache_manager
from ..schemas.generated_content import GeneratedContent, DocumentFile

logger = setup_logger(__name__)

class FeedbackProcessor:
    """Processes and manages documentation feedback."""

    def __init__(self):
        """Initialize the feedback processor."""
        self.cache = cache_manager

    async def process_feedback(
        self,
        feedback_items: List[Dict],
        documentation: GeneratedContent
    ) -> Dict[str, List[Dict]]:
        """
        Process feedback items and organize them by file and priority.
        
        Args:
            feedback_items: List of feedback items from review
            documentation: Current documentation content
            
        Returns:
            Organized feedback items by file
        """
        try:
            organized_feedback: Dict[str, List[Dict]] = {}
            
            for item in feedback_items:
                file_path = item.get('location', {}).get('file', 'general')
                
                if file_path not in organized_feedback:
                    organized_feedback[file_path] = []
                    
                # Add metadata to feedback item
                processed_item = {
                    **item,
                    'processed_at': datetime.now().isoformat(),
                    'status': 'pending',
                    'priority_score': await self._calculate_priority(item)
                }
                
                organized_feedback[file_path].append(processed_item)
                
            # Sort feedback items by priority
            for file_path in organized_feedback:
                organized_feedback[file_path].sort(
                    key=lambda x: x['priority_score'],
                    reverse=True
                )
                
            return organized_feedback

        except Exception as e:
            logger.error(f"Error processing feedback: {str(e)}")
            raise

    async def _calculate_priority(self, feedback_item: Dict) -> float:
        """Calculate priority score for a feedback item."""
        base_priority = {
            'high': 1.0,
            'medium': 0.6,
            'low': 0.3
        }.get(feedback_item.get('priority', 'low'), 0.1)
        
        # Adjust priority based on feedback type
        type_multiplier = {
            'issue': 1.2,
            'suggestion': 0.8,
            'praise': 0.5
        }.get(feedback_item.get('type', 'suggestion'), 1.0)
        
        # Adjust if changes are required
        required_multiplier = 1.5 if feedback_item.get('requires_changes', False) else 1.0
        
        return base_priority * type_multiplier * required_multiplier

    async def track_changes(
        self,
        file_path: str,
        original_content: str,
        updated_content: str,
        feedback_item: Dict
    ) -> Dict:
        """
        Track changes made in response to feedback.
        
        Args:
            file_path: Path to the changed file
            original_content: Original file content
            updated_content: Updated file content
            feedback_item: Related feedback item
            
        Returns:
            Change tracking information
        """
        try:
            # Record the change
            change_record = {
                'feedback_id': feedback_item['item_id'],
                'file_path': file_path,
                'timestamp': datetime.now().isoformat(),
                'changes_made': True,
                'content_length_diff': len(updated_content) - len(original_content),
                'sections_changed': await self._detect_changed_sections(
                    original_content,
                    updated_content
                )
            }

            # Cache the change record
            cache_key = f"change_record_{feedback_item['item_id']}"
            self.cache.set(cache_key, change_record)

            return change_record

        except Exception as e:
            logger.error(f"Error tracking changes: {str(e)}")
            raise

    async def _detect_changed_sections(
        self,
        original: str,
        updated: str
    ) -> List[str]:
        """Detect which sections were changed."""
        # Split content into sections and compare
        org_sections = original.split('\n\n')
        upd_sections = updated.split('\n\n')
        
        changed_sections = []
        
        for i, (org, upd) in enumerate(zip(org_sections, upd_sections)):
            if org != upd:
                # Try to extract section title
                lines = org.split('\n')
                title = lines[0] if lines else f"Section {i+1}"
                changed_sections.append(title)
                
        return changed_sections

    async def validate_improvements(
        self,
        feedback_item: Dict,
        original_content: str,
        updated_content: str
    ) -> Dict:
        """
        Validate that changes address the feedback.
        
        Args:
            feedback_item: Original feedback item
            original_content: Original content
            updated_content: Updated content
            
        Returns:
            Validation results
        """
        try:
            # Initialize validation result
            validation = {
                'feedback_id': feedback_item['item_id'],
                'timestamp': datetime.now().isoformat(),
                'changes_detected': original_content != updated_content,
                'addresses_feedback': False,
                'validation_details': []
            }

            if not validation['changes_detected']:
                validation['validation_details'].append(
                    "No changes detected in content"
                )
                return validation

            # Check if suggested changes were implemented
            if feedback_item.get('suggested_changes'):
                implemented = await self._check_suggested_changes(
                    feedback_item['suggested_changes'],
                    updated_content
                )
                validation['suggestions_implemented'] = implemented
                validation['validation_details'].append(
                    f"Suggested changes implemented: {implemented}"
                )

            # Check if the feedback target area was modified
            if 'location' in feedback_item:
                target_modified = await self._check_target_modified(
                    feedback_item['location'],
                    original_content,
                    updated_content
                )
                validation['target_modified'] = target_modified
                validation['validation_details'].append(
                    f"Target area modified: {target_modified}"
                )

            # Determine if feedback was addressed
            validation['addresses_feedback'] = (
                validation.get('suggestions_implemented', False) or
                validation.get('target_modified', False)
            )

            return validation

        except Exception as e:
            logger.error(f"Error validating improvements: {str(e)}")
            raise

    async def _check_suggested_changes(
        self,
        suggestions: str,
        content: str
    ) -> bool:
        """Check if suggested changes were implemented."""
        # This is a simplified check - in practice, you'd want more sophisticated
        # text comparison logic
        return suggestions.lower() in content.lower()

    async def _check_target_modified(
        self,
        location: Dict,
        original: str,
        updated: str
    ) -> bool:
        """Check if the target location was modified."""
        try:
            if 'line' in location:
                # Extract the relevant lines
                org_lines = original.splitlines()
                upd_lines = updated.splitlines()
                
                line_num = location['line']
                if 0 <= line_num < len(org_lines) and line_num < len(upd_lines):
                    return org_lines[line_num] != upd_lines[line_num]
                    
            return False
            
        except Exception:
            return False