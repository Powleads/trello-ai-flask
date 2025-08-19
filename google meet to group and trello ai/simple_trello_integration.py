#!/usr/bin/env python3
"""
Simple Trello Integration using direct API calls
Bypasses issues with py-trello library and CloudFront blocking
"""

import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class SimpleTrelloIntegration:
    """Simple Trello client using direct API calls."""
    
    def __init__(self):
        """Initialize with API credentials."""
        self.api_key = os.environ.get('TRELLO_API_KEY')
        self.token = os.environ.get('TRELLO_TOKEN')
        self.base_url = 'https://api.trello.com/1'
        
        if not all([self.api_key, self.token]):
            raise ValueError("Missing Trello API credentials")
        
        # Common headers to avoid CloudFront issues
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Cache for API responses
        self._boards_cache = {}
        self._members_cache = {}
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make authenticated API request."""
        if params is None:
            params = {}
        
        # Add authentication
        params.update({
            'key': self.api_key,
            'token': self.token
        })
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response text: {e.response.text[:200]}...")
            raise
    
    def get_all_boards(self) -> List[Dict]:
        """Get all accessible boards."""
        try:
            boards_data = self._make_request('/members/me/boards', {'filter': 'open'})
            
            boards = []
            for board in boards_data:
                if not board.get('closed', True):  # Only open boards
                    board_info = {
                        'id': board['id'],
                        'name': board['name'],
                        'url': board['url'],
                        'description': board.get('desc', ''),
                        'closed': board.get('closed', False)
                    }
                    boards.append(board_info)
                    self._boards_cache[board['id']] = board
            
            return boards
            
        except Exception as e:
            print(f"Error fetching boards: {e}")
            return []
    
    def get_board_lists(self, board_id: str) -> List[Dict]:
        """Get all lists in a board."""
        try:
            lists_data = self._make_request(f'/boards/{board_id}/lists', {'filter': 'open'})
            
            lists = []
            for list_obj in lists_data:
                if not list_obj.get('closed', True):
                    list_info = {
                        'id': list_obj['id'],
                        'name': list_obj['name'],
                        'pos': list_obj.get('pos', 0),
                        'closed': list_obj.get('closed', False)
                    }
                    lists.append(list_info)
            
            return lists
            
        except Exception as e:
            print(f"Error fetching lists for board {board_id}: {e}")
            return []
    
    def get_list_cards(self, list_id: str) -> List[Dict]:
        """Get all cards in a list."""
        try:
            cards_data = self._make_request(f'/lists/{list_id}/cards', {'filter': 'open'})
            
            cards = []
            for card in cards_data:
                if not card.get('closed', True):
                    card_info = {
                        'id': card['id'],
                        'name': card['name'],
                        'url': card['url'],
                        'desc': card.get('desc', ''),
                        'due': card.get('due'),
                        'member_ids': card.get('idMembers', []),
                        'labels': [label.get('name', '') for label in card.get('labels', []) if label.get('name')],
                        'pos': card.get('pos', 0),
                        'closed': card.get('closed', False)
                    }
                    cards.append(card_info)
            
            return cards
            
        except Exception as e:
            print(f"Error fetching cards for list {list_id}: {e}")
            return []
    
    def get_board_members(self, board_id: str) -> Dict[str, Dict]:
        """Get all members of a board."""
        try:
            members_data = self._make_request(f'/boards/{board_id}/members')
            
            members = {}
            for member in members_data:
                member_info = {
                    'id': member['id'],
                    'username': member['username'],
                    'full_name': member['fullName'],
                    'initials': member.get('initials', member['fullName'][:2].upper())
                }
                members[member['id']] = member_info
                self._members_cache[member['id']] = member_info
            
            return members
            
        except Exception as e:
            print(f"Error fetching board members for {board_id}: {e}")
            return {}
    
    def get_card_actions(self, card_id: str, action_filter: str = 'commentCard') -> List[Dict]:
        """Get actions (comments) for a card."""
        try:
            actions_data = self._make_request(f'/cards/{card_id}/actions', {
                'filter': action_filter,
                'limit': 50
            })
            
            actions = []
            for action in actions_data:
                if action['type'] == 'commentCard':
                    action_info = {
                        'id': action['id'],
                        'type': action['type'],
                        'date': action['date'],
                        'text': action['data']['text'],
                        'member_creator': {
                            'id': action['memberCreator']['id'],
                            'username': action['memberCreator']['username'],
                            'full_name': action['memberCreator']['fullName']
                        }
                    }
                    actions.append(action_info)
            
            # Sort by date (newest first)
            actions.sort(key=lambda x: x['date'], reverse=True)
            return actions
            
        except Exception as e:
            print(f"Error fetching actions for card {card_id}: {e}")
            return []
    
    def scan_cards_needing_updates(self, board_ids: List[str] = None, hours_threshold: int = 24) -> List[Dict]:
        """Scan cards that need updates."""
        if board_ids is None:
            boards = self.get_all_boards()
            board_ids = [board['id'] for board in boards]
        
        cards_needing_updates = []
        
        for board_id in board_ids:
            try:
                # Get board info
                board_info = None
                if board_id in self._boards_cache:
                    board_info = self._boards_cache[board_id]
                else:
                    boards = self.get_all_boards()
                    for board in boards:
                        if board['id'] == board_id:
                            board_info = board
                            break
                
                if not board_info:
                    continue
                
                # Get board members
                board_members = self.get_board_members(board_id)
                
                # Get all lists and cards
                lists = self.get_board_lists(board_id)
                
                for list_obj in lists:
                    cards = self.get_list_cards(list_obj['id'])
                    
                    for card in cards:
                        # Get assigned members
                        assigned_members = []
                        for member_id in card['member_ids']:
                            if member_id in board_members:
                                assigned_members.append(board_members[member_id]['full_name'])
                        
                        # Skip unassigned cards for now
                        if not assigned_members:
                            continue
                        
                        # Get card comments
                        comments = self.get_card_actions(card['id'])
                        
                        # Check last comment time
                        last_comment_date = None
                        last_comment_by = None
                        
                        if comments:
                            last_comment = comments[0]  # Already sorted by date desc
                            last_comment_date = datetime.fromisoformat(last_comment['date'].replace('Z', '+00:00'))
                            last_comment_by = last_comment['member_creator']['full_name']
                        
                        # Calculate time since last comment
                        now = datetime.now()
                        if last_comment_date:
                            time_since_comment = now - last_comment_date.replace(tzinfo=None)
                            hours_since_comment = time_since_comment.total_seconds() / 3600
                            days_since_comment = time_since_comment.days
                        else:
                            hours_since_comment = float('inf')
                            days_since_comment = 999
                        
                        # Check if update is needed
                        if hours_since_comment > hours_threshold:
                            card_data = {
                                'id': card['id'],
                                'name': card['name'],
                                'url': card['url'],
                                'list_name': list_obj['name'],
                                'board_name': board_info['name'],
                                'board_id': board_id,
                                'assigned_members': assigned_members,
                                'due_date': card['due'],
                                'labels': card['labels'],
                                'last_comment_date': last_comment_date.isoformat() if last_comment_date else None,
                                'last_comment_by': last_comment_by,
                                'hours_since_comment': hours_since_comment,
                                'days_since_comment': days_since_comment,
                                'total_comments': len(comments),
                                'needs_update': True
                            }
                            cards_needing_updates.append(card_data)
            
            except Exception as e:
                print(f"Error scanning board {board_id}: {e}")
                continue
        
        return cards_needing_updates
    
    def get_unassigned_cards(self, board_ids: List[str] = None) -> List[Dict]:
        """Get cards with no assigned members."""
        if board_ids is None:
            boards = self.get_all_boards()
            board_ids = [board['id'] for board in boards]
        
        unassigned_cards = []
        
        for board_id in board_ids:
            try:
                board_info = None
                if board_id in self._boards_cache:
                    board_info = self._boards_cache[board_id]
                else:
                    boards = self.get_all_boards()
                    for board in boards:
                        if board['id'] == board_id:
                            board_info = board
                            break
                
                if not board_info:
                    continue
                
                lists = self.get_board_lists(board_id)
                
                for list_obj in lists:
                    cards = self.get_list_cards(list_obj['id'])
                    
                    for card in cards:
                        if not card['member_ids']:  # No assigned members
                            card_data = {
                                'id': card['id'],
                                'name': card['name'],
                                'url': card['url'],
                                'list_name': list_obj['name'],
                                'board_name': board_info['name'],
                                'board_id': board_id,
                                'due_date': card['due'],
                                'labels': card['labels']
                            }
                            unassigned_cards.append(card_data)
            
            except Exception as e:
                print(f"Error scanning unassigned cards in board {board_id}: {e}")
                continue
        
        return unassigned_cards

def test_simple_trello():
    """Test the simple Trello integration."""
    try:
        trello = SimpleTrelloIntegration()
        
        print("Testing simple Trello integration...")
        
        # Test getting boards
        boards = trello.get_all_boards()
        print(f"Found {len(boards)} boards:")
        for board in boards:
            print(f"  - {board['name']} ({board['id']})")
        
        if boards:
            # Test scanning for cards needing updates
            cards_needing_updates = trello.scan_cards_needing_updates(
                board_ids=[boards[0]['id']], 
                hours_threshold=24
            )
            print(f"Found {len(cards_needing_updates)} cards needing updates")
            
            # Test getting unassigned cards
            unassigned_cards = trello.get_unassigned_cards(board_ids=[boards[0]['id']])
            print(f"Found {len(unassigned_cards)} unassigned cards")
        
        return True
        
    except Exception as e:
        print(f"Simple Trello integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_simple_trello():
        print("✅ Simple Trello integration test passed")
    else:
        print("❌ Simple Trello integration test failed")