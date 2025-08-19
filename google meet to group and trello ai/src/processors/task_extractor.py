"""
Task Extractor

Handles extraction of action items and tasks from meeting transcripts
using NLP techniques and pattern matching.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from agent import ActionItem

logger = logging.getLogger(__name__)

# Action item patterns
ACTION_PATTERNS = [
    r'(\w+)\s+will\s+(.+?)(?:\.|$)',
    r'(\w+)\s+should\s+(.+?)(?:\.|$)',
    r'(\w+)\s+needs\s+to\s+(.+?)(?:\.|$)',
    r'action\s+item:?\s*(.+?)(?:\.|$)',
    r'todo:?\s*(.+?)(?:\.|$)',
    r'task:?\s*(.+?)(?:\.|$)',
    r'(\w+)\s+is\s+responsible\s+for\s+(.+?)(?:\.|$)',
    r'(\w+)\s+takes\s+(.+?)(?:\.|$)',
    r'assign\s+(\w+)\s+to\s+(.+?)(?:\.|$)',
    r'(\w+)\s+owns\s+(.+?)(?:\.|$)'
]

# Date patterns
DATE_PATTERNS = [
    r'by\s+(\w+day)',
    r'by\s+(\d{1,2}/\d{1,2})',
    r'by\s+(\d{1,2}-\d{1,2})',
    r'deadline:?\s*(\d{1,2}/\d{1,2})',
    r'due:?\s*(\d{1,2}/\d{1,2})',
    r'by\s+end\s+of\s+(week|month)',
    r'next\s+(week|month)',
    r'by\s+(tomorrow|today)',
    r'in\s+(\d+)\s+(days?|weeks?|months?)'
]

# Priority indicators
PRIORITY_KEYWORDS = {
    'urgent': ['urgent', 'asap', 'immediately', 'critical', 'emergency'],
    'high': ['high priority', 'important', 'soon', 'quickly'],
    'medium': ['medium', 'normal', 'standard'],
    'low': ['low priority', 'when possible', 'eventually', 'nice to have']
}

# Common stop words to filter out
STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'this', 'that', 'these', 'those', 'i', 'you', 'he',
    'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
}


class TaskExtractor:
    """
    Extracts action items and tasks from meeting transcripts.
    
    Uses pattern matching, NLP techniques, and context analysis
    to identify actionable items with assignees and deadlines.
    """
    
    def __init__(self):
        self.action_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in ACTION_PATTERNS]
        self.date_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in DATE_PATTERNS]
    
    def extract_action_items(self, 
                           transcript_text: str,
                           participants: Optional[List[str]] = None) -> List[ActionItem]:
        """
        Extract action items from transcript text.
        
        Args:
            transcript_text: Raw transcript content
            participants: List of meeting participants
            
        Returns:
            List of ActionItem objects
        """
        participants = participants or []
        sentences = self._split_into_sentences(transcript_text)
        
        action_items = []
        
        for sentence in sentences:
            # Try to extract action items using patterns
            items = self._extract_from_sentence(sentence, participants)
            action_items.extend(items)
        
        # Remove duplicates and clean up
        unique_items = self._deduplicate_items(action_items)
        
        # Validate and filter
        valid_items = [item for item in unique_items if self._is_valid_action_item(item)]
        
        logger.info(f"Extracted {len(valid_items)} action items from transcript")
        return valid_items
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences for processing.
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        
        # Clean up sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Filter out very short fragments
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences
    
    def _extract_from_sentence(self, 
                              sentence: str, 
                              participants: List[str]) -> List[ActionItem]:
        """
        Extract action items from a single sentence.
        
        Args:
            sentence: Sentence to analyze
            participants: List of meeting participants
            
        Returns:
            List of ActionItem objects
        """
        items = []
        
        for pattern in self.action_patterns:
            matches = pattern.findall(sentence)
            
            for match in matches:
                if isinstance(match, tuple):
                    # Pattern with assignee and task
                    assignee = match[0] if len(match) > 1 else None
                    task = match[1] if len(match) > 1 else match[0]
                else:
                    # Pattern with just task
                    assignee = None
                    task = match
                
                # Validate assignee against participants
                if assignee and not self._is_valid_assignee(assignee, participants):
                    assignee = None
                
                # Extract deadline
                due_date = self._extract_deadline(sentence)
                
                # Determine priority
                priority = self._determine_priority(sentence)
                
                # Extract tags
                tags = self._extract_tags(sentence)
                
                # Create ActionItem
                try:
                    action_item = ActionItem(
                        description=self._clean_task_description(task),
                        assignee=assignee,
                        due_date=due_date,
                        priority=priority,
                        tags=tags
                    )
                    items.append(action_item)
                except Exception as e:
                    logger.warning(f"Failed to create action item: {e}")
        
        return items
    
    def _is_valid_assignee(self, assignee: str, participants: List[str]) -> bool:
        """
        Check if assignee is a valid participant.
        
        Args:
            assignee: Potential assignee name
            participants: List of meeting participants
            
        Returns:
            True if valid assignee
        """
        if not assignee or len(assignee) < 2:
            return False
        
        assignee_lower = assignee.lower()
        
        # Check exact matches
        for participant in participants:
            if assignee_lower == participant.lower():
                return True
        
        # Check partial matches (first name)
        for participant in participants:
            participant_parts = participant.lower().split()
            if assignee_lower in participant_parts:
                return True
        
        # Check if it's a common name (basic validation)
        common_names = {
            'john', 'jane', 'mike', 'sarah', 'david', 'lisa', 'tom', 'mary',
            'chris', 'alex', 'sam', 'anna', 'paul', 'emma', 'james', 'kate'
        }
        
        return assignee_lower in common_names or len(assignee) > 2
    
    def _extract_deadline(self, sentence: str) -> Optional[datetime]:
        """
        Extract deadline from sentence.
        
        Args:
            sentence: Sentence to analyze
            
        Returns:
            Deadline datetime or None
        """
        sentence_lower = sentence.lower()
        
        for pattern in self.date_patterns:
            match = pattern.search(sentence_lower)
            if match:
                date_str = match.group(1)
                return self._parse_date_string(date_str)
        
        return None
    
    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string into datetime object.
        
        Args:
            date_str: Date string to parse
            
        Returns:
            Parsed datetime or None
        """
        try:
            now = datetime.now()
            date_str = date_str.lower().strip()
            
            # Handle relative dates
            if date_str == 'today':
                return now
            elif date_str == 'tomorrow':
                return now + timedelta(days=1)
            elif 'monday' in date_str:
                days_ahead = 0 - now.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                return now + timedelta(days=days_ahead)
            elif 'tuesday' in date_str:
                days_ahead = 1 - now.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                return now + timedelta(days=days_ahead)
            elif 'wednesday' in date_str:
                days_ahead = 2 - now.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                return now + timedelta(days=days_ahead)
            elif 'thursday' in date_str:
                days_ahead = 3 - now.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                return now + timedelta(days=days_ahead)
            elif 'friday' in date_str:
                days_ahead = 4 - now.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                return now + timedelta(days=days_ahead)
            elif 'week' in date_str:
                return now + timedelta(weeks=1)
            elif 'month' in date_str:
                return now + timedelta(days=30)
            
            # Handle MM/DD format
            if '/' in date_str:
                parts = date_str.split('/')
                if len(parts) == 2:
                    month, day = int(parts[0]), int(parts[1])
                    year = now.year
                    # If date is in the past, assume next year
                    candidate_date = datetime(year, month, day)
                    if candidate_date < now:
                        candidate_date = datetime(year + 1, month, day)
                    return candidate_date
            
            # Handle MM-DD format
            if '-' in date_str:
                parts = date_str.split('-')
                if len(parts) == 2:
                    month, day = int(parts[0]), int(parts[1])
                    year = now.year
                    candidate_date = datetime(year, month, day)
                    if candidate_date < now:
                        candidate_date = datetime(year + 1, month, day)
                    return candidate_date
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return None
    
    def _determine_priority(self, sentence: str) -> str:
        """
        Determine priority level from sentence context.
        
        Args:
            sentence: Sentence to analyze
            
        Returns:
            Priority level string
        """
        sentence_lower = sentence.lower()
        
        # Check for priority keywords
        for priority, keywords in PRIORITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in sentence_lower:
                    return priority
        
        # Default priority
        return 'medium'
    
    def _extract_tags(self, sentence: str) -> List[str]:
        """
        Extract relevant tags from sentence.
        
        Args:
            sentence: Sentence to analyze
            
        Returns:
            List of tags
        """
        tags = []
        sentence_lower = sentence.lower()
        
        # Common project/task categories
        tag_keywords = {
            'development': ['develop', 'code', 'implement', 'build'],
            'design': ['design', 'mockup', 'wireframe', 'ui', 'ux'],
            'testing': ['test', 'qa', 'verify', 'validate'],
            'documentation': ['document', 'write', 'spec', 'manual'],
            'meeting': ['schedule', 'meet', 'call', 'discuss'],
            'review': ['review', 'check', 'approve', 'feedback'],
            'research': ['research', 'investigate', 'analyze', 'study'],
            'communication': ['email', 'notify', 'inform', 'update']
        }
        
        for tag, keywords in tag_keywords.items():
            for keyword in keywords:
                if keyword in sentence_lower:
                    tags.append(tag)
                    break
        
        return tags
    
    def _clean_task_description(self, task: str) -> str:
        """
        Clean and standardize task description.
        
        Args:
            task: Raw task description
            
        Returns:
            Cleaned task description
        """
        # Remove extra whitespace
        task = ' '.join(task.split())
        
        # Remove common prefixes
        prefixes_to_remove = ['to ', 'will ', 'should ', 'needs to ', 'going to ']
        task_lower = task.lower()
        for prefix in prefixes_to_remove:
            if task_lower.startswith(prefix):
                task = task[len(prefix):]
                break
        
        # Capitalize first letter
        if task:
            task = task[0].upper() + task[1:]
        
        # Ensure it ends with a period
        if task and not task.endswith(('.', '!', '?')):
            task += '.'
        
        return task
    
    def _deduplicate_items(self, items: List[ActionItem]) -> List[ActionItem]:
        """
        Remove duplicate action items.
        
        Args:
            items: List of action items
            
        Returns:
            Deduplicated list
        """
        seen_descriptions = set()
        unique_items = []
        
        for item in items:
            # Simple deduplication based on description similarity
            description_key = item.description.lower().strip()
            
            if description_key not in seen_descriptions:
                seen_descriptions.add(description_key)
                unique_items.append(item)
        
        return unique_items
    
    def _is_valid_action_item(self, item: ActionItem) -> bool:
        """
        Validate if an action item is meaningful.
        
        Args:
            item: ActionItem to validate
            
        Returns:
            True if valid
        """
        # Check description length
        if not item.description or len(item.description) < 5:
            return False
        
        # Check for meaningful content
        description_lower = item.description.lower()
        
        # Filter out common non-actionable phrases
        non_actionable = [
            'thank you', 'thanks', 'good morning', 'good afternoon',
            'hello', 'hi', 'bye', 'goodbye', 'see you', 'talk to you',
            'how are you', 'nice to meet', 'great', 'ok', 'okay',
            'yes', 'no', 'maybe', 'i think', 'i believe'
        ]
        
        for phrase in non_actionable:
            if phrase in description_lower:
                return False
        
        # Check for action verbs
        action_verbs = [
            'create', 'build', 'develop', 'implement', 'design', 'write',
            'send', 'schedule', 'review', 'test', 'analyze', 'prepare',
            'contact', 'follow up', 'research', 'investigate', 'update',
            'complete', 'finish', 'deliver', 'submit', 'approve'
        ]
        
        has_action_verb = any(verb in description_lower for verb in action_verbs)
        
        # Must have action verb or be assigned to someone
        return has_action_verb or item.assignee is not None
    
    def get_extraction_stats(self, items: List[ActionItem]) -> Dict[str, Any]:
        """
        Get statistics about extracted action items.
        
        Args:
            items: List of action items
            
        Returns:
            Statistics dictionary
        """
        if not items:
            return {'total': 0}
        
        stats = {
            'total': len(items),
            'with_assignee': len([item for item in items if item.assignee]),
            'with_deadline': len([item for item in items if item.due_date]),
            'priority_breakdown': {'low': 0, 'medium': 0, 'high': 0, 'urgent': 0},
            'common_tags': {},
            'average_description_length': sum(len(item.description) for item in items) / len(items)
        }
        
        # Priority breakdown
        for item in items:
            stats['priority_breakdown'][item.priority] += 1
        
        # Tag frequency
        for item in items:
            for tag in item.tags:
                stats['common_tags'][tag] = stats['common_tags'].get(tag, 0) + 1
        
        return stats
    
    def suggest_improvements(self, 
                           transcript_text: str, 
                           extracted_items: List[ActionItem]) -> List[str]:
        """
        Suggest improvements for better action item extraction.
        
        Args:
            transcript_text: Original transcript
            extracted_items: Extracted action items
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Check for missed opportunities
        transcript_lower = transcript_text.lower()
        
        # Look for unassigned actions
        unassigned_count = len([item for item in extracted_items if not item.assignee])
        if unassigned_count > len(extracted_items) * 0.5:
            suggestions.append(
                "Consider being more explicit about task assignments during meetings."
            )
        
        # Look for missing deadlines
        no_deadline_count = len([item for item in extracted_items if not item.due_date])
        if no_deadline_count > len(extracted_items) * 0.7:
            suggestions.append(
                "Consider setting specific deadlines for action items during meetings."
            )
        
        # Check for action keywords that might have been missed
        potential_actions = [
            'follow up', 'reach out', 'get back', 'circle back', 'check on',
            'look into', 'find out', 'figure out', 'work on'
        ]
        
        missed_actions = []
        for action in potential_actions:
            if action in transcript_lower:
                # Check if we captured it
                captured = any(action in item.description.lower() for item in extracted_items)
                if not captured:
                    missed_actions.append(action)
        
        if missed_actions:
            suggestions.append(
                f"Potential action items may have been missed involving: {', '.join(missed_actions[:3])}"
            )
        
        # Check transcript quality
        if len(transcript_text.split()) < 100:
            suggestions.append(
                "Transcript appears to be quite short. Consider longer meetings for better context."
            )
        
        return suggestions


if __name__ == "__main__":
    # Test the task extractor
    extractor = TaskExtractor()
    
    test_transcript = """
    John: We need to finish the project proposal by Friday.
    Sarah: I'll review the budget section and send feedback by tomorrow.
    Mike: Can someone schedule a follow-up meeting with the client?
    John: Mike, you should handle the client meeting. It's urgent.
    Sarah: I'll also prepare the presentation slides for next week.
    Action item: Update the project timeline.
    """
    
    participants = ["John", "Sarah", "Mike"]
    items = extractor.extract_action_items(test_transcript, participants)
    
    print(f"Extracted {len(items)} action items:")
    for i, item in enumerate(items, 1):
        print(f"{i}. {item.description}")
        if item.assignee:
            print(f"   Assigned to: {item.assignee}")
        if item.due_date:
            print(f"   Due: {item.due_date.strftime('%Y-%m-%d')}")
        print(f"   Priority: {item.priority}")
        if item.tags:
            print(f"   Tags: {', '.join(item.tags)}")
        print()