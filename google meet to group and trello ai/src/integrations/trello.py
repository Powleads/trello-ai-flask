"""
Trello Integration

Handles finding existing Trello cards mentioned in meetings and adding
discussion notes as comments. Uses intelligent card matching and context analysis.
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from difflib import SequenceMatcher

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from agent import ActionItem, MeetingSummary

logger = logging.getLogger(__name__)

# Trello API base URL
TRELLO_API_BASE = "https://api.trello.com/1"

# Priority label colors
PRIORITY_COLORS = {
    'low': 'green',
    'medium': 'yellow', 
    'high': 'orange',
    'urgent': 'red'
}


class TrelloClient:
    """
    Trello client for finding existing cards and adding meeting notes.
    
    Supports card matching by title/description and adding contextual comments.
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 token: Optional[str] = None):
        """
        Initialize Trello client.
        
        Args:
            api_key: Trello API key
            token: Trello OAuth token
        """
        self.api_key = api_key or os.getenv('TRELLO_API_KEY')
        self.token = token or os.getenv('TRELLO_TOKEN')
        
        if not self.api_key or not self.token:
            raise ValueError("Trello API credentials not provided")
        
        self.session = None
        self.board_id = os.getenv('TRELLO_BOARD_ID')
        self.default_list_id = os.getenv('TRELLO_DEFAULT_LIST_ID')
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _make_request(self, 
                           endpoint: str,
                           method: str = 'GET',
                           params: Optional[Dict] = None,
                           data: Optional[Dict] = None) -> Any:
        """
        Make HTTP request to Trello API.
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            params: Query parameters
            data: Request data
            
        Returns:
            Response data
        """
        session = await self._get_session()
        url = f"{TRELLO_API_BASE}/{endpoint}"
        
        # Add authentication
        auth_params = {
            'key': self.api_key,
            'token': self.token
        }
        
        if params:
            auth_params.update(params)
        
        try:
            if method.upper() == 'POST':
                async with session.post(url, params=auth_params, json=data) as response:
                    response.raise_for_status()
                    return await response.json()
            elif method.upper() == 'PUT':
                async with session.put(url, params=auth_params, json=data) as response:
                    response.raise_for_status()
                    return await response.json()
            else:
                async with session.get(url, params=auth_params) as response:
                    response.raise_for_status()
                    return await response.json()
                    
        except aiohttp.ClientError as e:
            logger.error(f"Trello API request failed: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Trello API.
        
        Returns:
            User information
        """
        try:
            user = await self._make_request('members/me')
            logger.info(f"Trello connection successful: {user.get('fullName')}")
            return user
        except Exception as e:
            logger.error(f"Trello connection test failed: {e}")
            raise
    
    async def get_boards(self) -> List[Dict[str, Any]]:
        """
        Get user's Trello boards.
        
        Returns:
            List of board information
        """
        return await self._make_request('members/me/boards')
    
    async def get_board_lists(self, board_id: str) -> List[Dict[str, Any]]:
        """
        Get lists from a Trello board.
        
        Args:
            board_id: Board ID
            
        Returns:
            List of board lists
        """
        return await self._make_request(f'boards/{board_id}/lists')
    
    async def get_board_cards(self, board_id: str) -> List[Dict[str, Any]]:
        """
        Get cards from a Trello board.
        
        Args:
            board_id: Board ID
            
        Returns:
            List of board cards
        """
        return await self._make_request(f'boards/{board_id}/cards')
    
    async def create_card(self, 
                         action_item: ActionItem,
                         list_id: Optional[str] = None,
                         board_id: Optional[str] = None) -> Optional[str]:
        """
        Create a Trello card from an action item.
        
        Args:
            action_item: ActionItem to create card for
            list_id: Target list ID
            board_id: Target board ID
            
        Returns:
            Created card ID
        """
        target_board = board_id or self.board_id
        target_list = list_id or self.default_list_id
        
        if not target_board:
            boards = await self.get_boards()
            if boards:
                target_board = boards[0]['id']
                logger.info(f"Using first available board: {boards[0]['name']}")
            else:
                raise ValueError("No Trello board available")
        
        if not target_list:
            lists = await self.get_board_lists(target_board)
            if lists:
                # Try to find "NEW TASKS" list first
                for list_item in lists:
                    if list_item['name'].upper() == 'NEW TASKS':
                        target_list = list_item['id']
                        logger.info(f"Found 'NEW TASKS' list: {list_item['name']}")
                        break
                
                # Fallback to first list if NEW TASKS not found
                if not target_list:
                    target_list = lists[0]['id']
                    logger.info(f"Using first available list: {lists[0]['name']}")
            else:
                raise ValueError("No Trello list available")
        
        # Check for duplicates
        existing_card = await self._find_duplicate_card(action_item, target_board)
        if existing_card:
            logger.info(f"Duplicate card found: {existing_card['name']}")
            return existing_card['id']
        
        # Create card data
        card_data = {
            'name': action_item.description[:255],  # Trello name limit
            'desc': self._format_card_description(action_item),
            'idList': target_list
        }
        
        # Add due date if specified
        if action_item.due_date:
            card_data['due'] = action_item.due_date.isoformat()
        
        try:
            card = await self._make_request('cards', 'POST', data=card_data)
            card_id = card['id']
            
            logger.info(f"Created Trello card: {card['name']}")
            
            # Add labels for priority
            await self._add_priority_label(card_id, action_item.priority, target_board)
            
            # Add member if assignee specified
            if action_item.assignee:
                await self._assign_member(card_id, action_item.assignee, target_board)
            
            return card_id
            
        except Exception as e:
            logger.error(f"Failed to create Trello card: {e}")
            raise
    
    async def _find_duplicate_card(self, 
                                  action_item: ActionItem,
                                  board_id: str,
                                  similarity_threshold: float = 0.8) -> Optional[Dict[str, Any]]:
        """
        Find potential duplicate cards using fuzzy matching.
        
        Args:
            action_item: ActionItem to check for duplicates
            board_id: Board to search in
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            Duplicate card if found
        """
        try:
            cards = await self.get_board_cards(board_id)
            
            for card in cards:
                similarity = SequenceMatcher(
                    None, 
                    action_item.description.lower(),
                    card['name'].lower()
                ).ratio()
                
                if similarity >= similarity_threshold:
                    logger.info(f"Found similar card: {card['name']} (similarity: {similarity:.2f})")
                    return card
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking for duplicate cards: {e}")
            return None
    
    def _format_card_description(self, action_item: ActionItem) -> str:
        """
        Format action item as Trello card description.
        
        Args:
            action_item: ActionItem to format
            
        Returns:
            Formatted description
        """
        description = f"**Action Item**: {action_item.description}\n\n"
        
        if action_item.assignee:
            description += f"**Assigned to**: {action_item.assignee}\n"
        
        description += f"**Priority**: {action_item.priority.upper()}\n"
        
        if action_item.due_date:
            description += f"**Due Date**: {action_item.due_date.strftime('%Y-%m-%d')}\n"
        
        if action_item.tags:
            description += f"**Tags**: {', '.join(action_item.tags)}\n"
        
        description += f"\n**Created**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        description += "**Source**: Meeting Automation Tool"
        
        return description
    
    async def _add_priority_label(self, 
                                 card_id: str, 
                                 priority: str,
                                 board_id: str):
        """
        Add priority label to card.
        
        Args:
            card_id: Card ID
            priority: Priority level
            board_id: Board ID
        """
        try:
            # Get board labels
            labels = await self._make_request(f'boards/{board_id}/labels')
            
            # Find or create priority label
            label_color = PRIORITY_COLORS.get(priority.lower(), 'yellow')
            label_name = f"Priority: {priority.upper()}"
            
            target_label = None
            for label in labels:
                if label.get('name') == label_name:
                    target_label = label
                    break
            
            if not target_label:
                # Create new label
                label_data = {
                    'name': label_name,
                    'color': label_color
                }
                target_label = await self._make_request(
                    f'boards/{board_id}/labels', 
                    'POST', 
                    data=label_data
                )
            
            # Add label to card
            await self._make_request(
                f'cards/{card_id}/idLabels',
                'POST',
                data={'value': target_label['id']}
            )
            
            logger.info(f"Added priority label '{label_name}' to card")
            
        except Exception as e:
            logger.error(f"Failed to add priority label: {e}")
    
    async def _assign_member(self, 
                           card_id: str, 
                           assignee_name: str,
                           board_id: str):
        """
        Assign a member to a card by name.
        
        Args:
            card_id: Card ID
            assignee_name: Name of person to assign
            board_id: Board ID
        """
        try:
            # Get board members
            members = await self._make_request(f'boards/{board_id}/members')
            
            # Find member by name (fuzzy match)
            target_member = None
            best_match = 0
            
            for member in members:
                full_name = member.get('fullName', '').lower()
                username = member.get('username', '').lower()
                assignee_lower = assignee_name.lower()
                
                # Check full name match
                name_similarity = SequenceMatcher(None, assignee_lower, full_name).ratio()
                username_similarity = SequenceMatcher(None, assignee_lower, username).ratio()
                
                max_similarity = max(name_similarity, username_similarity)
                
                if max_similarity > best_match and max_similarity > 0.6:
                    best_match = max_similarity
                    target_member = member
            
            if target_member:
                # Add member to card
                await self._make_request(
                    f'cards/{card_id}/idMembers',
                    'POST',
                    data={'value': target_member['id']}
                )
                
                logger.info(f"Assigned card to {target_member['fullName']}")
            else:
                logger.warning(f"Could not find member: {assignee_name}")
                
        except Exception as e:
            logger.error(f"Failed to assign member: {e}")
    
    async def update_card(self, 
                         card_id: str, 
                         updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a Trello card.
        
        Args:
            card_id: Card ID to update
            updates: Dictionary of updates
            
        Returns:
            Updated card data
        """
        return await self._make_request(f'cards/{card_id}', 'PUT', data=updates)
    
    async def move_card(self, 
                       card_id: str, 
                       list_id: str) -> Dict[str, Any]:
        """
        Move a card to a different list.
        
        Args:
            card_id: Card ID
            list_id: Target list ID
            
        Returns:
            Updated card data
        """
        return await self.update_card(card_id, {'idList': list_id})
    
    async def add_comment(self, 
                         card_id: str, 
                         comment: str) -> Dict[str, Any]:
        """
        Add a comment to a card.
        
        Args:
            card_id: Card ID
            comment: Comment text
            
        Returns:
            Comment data
        """
        return await self._make_request(
            f'cards/{card_id}/actions/comments',
            'POST',
            data={'text': comment}
        )
    
    async def find_and_update_cards_from_meeting(self, 
                                               meeting_summary: MeetingSummary,
                                               board_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Find existing Trello cards mentioned in the meeting and add discussion notes.
        
        Args:
            meeting_summary: MeetingSummary with discussion content
            board_id: Target board ID
            
        Returns:
            Dictionary with results of card updates
        """
        target_board = board_id or self.board_id
        if not target_board:
            boards = await self.get_boards()
            if boards:
                target_board = boards[0]['id']
            else:
                raise ValueError("No Trello board available")
        
        # Extract card references from meeting content
        card_references = await self._extract_card_references(meeting_summary)
        
        # Find matching cards on the board
        board_cards = await self.get_board_cards(target_board)
        matched_cards = []
        
        for reference in card_references:
            matching_card = await self._find_matching_card(reference, board_cards)
            if matching_card:
                matched_cards.append({
                    'reference': reference,
                    'card': matching_card,
                    'discussed_content': reference['context']
                })
        
        # Add comments to matched cards
        updated_cards = []
        for match in matched_cards:
            try:
                comment = await self._format_meeting_comment(
                    meeting_summary, 
                    match['discussed_content']
                )
                
                await self.add_comment(match['card']['id'], comment)
                updated_cards.append({
                    'card_id': match['card']['id'],
                    'card_name': match['card']['name'],
                    'comment_added': True
                })
                
                logger.info(f"Added meeting notes to card: {match['card']['name']}")
                
            except Exception as e:
                logger.error(f"Failed to add comment to card {match['card']['id']}: {e}")
                updated_cards.append({
                    'card_id': match['card']['id'],
                    'card_name': match['card']['name'],
                    'comment_added': False,
                    'error': str(e)
                })
        
        return {
            'cards_found': len(matched_cards),
            'cards_updated': len([c for c in updated_cards if c.get('comment_added')]),
            'updated_cards': updated_cards,
            'references_found': len(card_references)
        }
    
    async def _extract_card_references(self, meeting_summary: MeetingSummary) -> List[Dict[str, Any]]:
        """
        Extract references to Trello cards from meeting content.
        
        Args:
            meeting_summary: Meeting summary to analyze
            
        Returns:
            List of card references with context
        """
        references = []
        full_content = meeting_summary.summary
        
        # Common patterns for referencing cards/tasks
        card_patterns = [
            r'card[:\s]+([^.!?\n]{5,50})',
            r'task[:\s]+([^.!?\n]{5,50})',
            r'ticket[:\s]+([^.!?\n]{5,50})',
            r'issue[:\s]+([^.!?\n]{5,50})',
            r'working on[:\s]+([^.!?\n]{5,50})',
            r'update on[:\s]+([^.!?\n]{5,50})',
            r'progress on[:\s]+([^.!?\n]{5,50})',
            r'about[:\s]+([^.!?\n]{5,50})',
            r'regarding[:\s]+([^.!?\n]{5,50})'
        ]
        
        import re
        
        for pattern in card_patterns:
            matches = re.finditer(pattern, full_content, re.IGNORECASE)
            for match in matches:
                card_title = match.group(1).strip()
                
                # Get surrounding context (sentence containing the reference)
                start = max(0, match.start() - 100)
                end = min(len(full_content), match.end() + 100)
                context = full_content[start:end].strip()
                
                references.append({
                    'title': card_title,
                    'context': context,
                    'pattern_matched': pattern,
                    'confidence': self._calculate_reference_confidence(card_title, context)
                })
        
        # Remove duplicates and low-confidence references
        unique_references = []
        seen_titles = set()
        
        for ref in references:
            title_key = ref['title'].lower().strip()
            if (title_key not in seen_titles and 
                ref['confidence'] > 0.3 and 
                len(ref['title']) > 3):
                seen_titles.add(title_key)
                unique_references.append(ref)
        
        # Sort by confidence
        unique_references.sort(key=lambda x: x['confidence'], reverse=True)
        
        return unique_references[:10]  # Limit to top 10 most confident matches
    
    def _calculate_reference_confidence(self, title: str, context: str) -> float:
        """
        Calculate confidence score for a card reference.
        
        Args:
            title: Potential card title
            context: Context where reference was found
            
        Returns:
            Confidence score between 0 and 1
        """
        confidence = 0.5  # Base confidence
        
        # Increase confidence for action words in context
        action_words = ['working', 'update', 'progress', 'completed', 'finished', 'reviewing']
        for word in action_words:
            if word in context.lower():
                confidence += 0.1
        
        # Increase confidence for specific indicators
        if any(word in context.lower() for word in ['trello', 'board', 'card']):
            confidence += 0.2
        
        # Decrease confidence for very generic titles
        generic_words = ['it', 'this', 'that', 'something', 'anything', 'everything']
        if title.lower().strip() in generic_words:
            confidence -= 0.5
        
        # Increase confidence for longer, more specific titles
        if len(title) > 10:
            confidence += 0.1
        if len(title) > 20:
            confidence += 0.1
        
        return min(1.0, max(0.0, confidence))
    
    async def _find_matching_card(self, reference: Dict[str, Any], board_cards: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find the best matching card for a reference.
        
        Args:
            reference: Card reference from meeting
            board_cards: List of cards on the board
            
        Returns:
            Best matching card or None
        """
        reference_title = reference['title'].lower().strip()
        best_match = None
        best_score = 0.0
        
        for card in board_cards:
            card_name = card['name'].lower().strip()
            card_desc = card.get('desc', '').lower().strip()
            
            # Calculate similarity scores
            name_similarity = SequenceMatcher(None, reference_title, card_name).ratio()
            desc_similarity = SequenceMatcher(None, reference_title, card_desc).ratio() if card_desc else 0
            
            # Check for partial matches
            partial_name_match = 0.0
            if reference_title in card_name or card_name in reference_title:
                partial_name_match = 0.7
            
            partial_desc_match = 0.0
            if card_desc and (reference_title in card_desc or any(word in card_desc for word in reference_title.split() if len(word) > 3)):
                partial_desc_match = 0.5
            
            # Calculate overall score
            overall_score = max(
                name_similarity,
                desc_similarity,
                partial_name_match,
                partial_desc_match
            )
            
            # Boost score based on reference confidence
            overall_score *= reference['confidence']
            
            if overall_score > best_score and overall_score > 0.4:  # Minimum threshold
                best_score = overall_score
                best_match = card
        
        return best_match
    
    async def _format_meeting_comment(self, meeting_summary: MeetingSummary, discussed_content: str) -> str:
        """
        Format a comment for adding to a Trello card.
        
        Args:
            meeting_summary: Meeting summary
            discussed_content: Content discussed about this card
            
        Returns:
            Formatted comment string
        """
        comment = f"**Meeting Discussion - {meeting_summary.date.strftime('%Y-%m-%d %H:%M')}**\\n\\n"
        comment += f"**Meeting:** {meeting_summary.title}\\n"
        comment += f"**Participants:** {', '.join(meeting_summary.participants)}\\n\\n"
        comment += f"**Discussion:**\\n{discussed_content}\\n\\n"
        
        # Add any related decisions
        if meeting_summary.key_decisions:
            related_decisions = [d for d in meeting_summary.key_decisions 
                               if any(word in discussed_content.lower() 
                                     for word in d.lower().split() if len(word) > 3)]
            if related_decisions:
                comment += f"**Related Decisions:**\\n"
                for decision in related_decisions:
                    comment += f"• {decision}\\n"
                comment += "\\n"
        
        comment += f"*Added by Meeting Automation Tool*"
        
        return comment
    
    async def get_card_stats(self, board_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about cards on the board.
        
        Args:
            board_id: Board ID to analyze
            
        Returns:
            Statistics dictionary
        """
        target_board = board_id or self.board_id
        if not target_board:
            raise ValueError("No board ID specified")
        
        try:
            cards = await self.get_board_cards(target_board)
            
            stats = {
                'total_cards': len(cards),
                'overdue_cards': 0,
                'due_today': 0,
                'due_this_week': 0,
                'priority_counts': {'low': 0, 'medium': 0, 'high': 0, 'urgent': 0}
            }
            
            today = datetime.now().date()
            week_end = today + timedelta(days=7)
            
            for card in cards:
                # Check due dates
                if card.get('due'):
                    due_date = datetime.fromisoformat(card['due'].replace('Z', '+00:00')).date()
                    
                    if due_date < today:
                        stats['overdue_cards'] += 1
                    elif due_date == today:
                        stats['due_today'] += 1
                    elif due_date <= week_end:
                        stats['due_this_week'] += 1
                
                # Check priority labels
                for label in card.get('labels', []):
                    label_name = label.get('name', '').lower()
                    for priority in stats['priority_counts']:
                        if priority in label_name:
                            stats['priority_counts'][priority] += 1
                            break
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get card statistics: {e}")
            raise


# Utility functions
async def setup_trello_client() -> TrelloClient:
    """
    Set up and test Trello client.
    
    Returns:
        Configured TrelloClient instance
    """
    async with TrelloClient() as client:
        # Test connection
        user = await client.test_connection()
        logger.info(f"Trello user: {user.get('fullName')}")
        
        # Get boards
        boards = await client.get_boards()
        logger.info(f"Available boards: {len(boards)}")
        
        return client


if __name__ == "__main__":
    # Test the Trello client
    async def test_client():
        async with TrelloClient() as client:
            user = await client.test_connection()
            print(f"Connected as: {user.get('fullName')}")
            
            boards = await client.get_boards()
            print(f"Boards: {len(boards)}")
            for board in boards[:3]:
                print(f"  - {board['name']}")
    
    asyncio.run(test_client())