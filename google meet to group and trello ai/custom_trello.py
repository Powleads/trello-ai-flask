#!/usr/bin/env python3
"""
Custom Trello Client
Replacement for py-trello library with direct HTTP requests
"""

import requests
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class TrelloCard:
    """Represents a Trello card."""
    
    def __init__(self, card_data: Dict):
        self.id = card_data.get('id', '')
        self.name = card_data.get('name', '')
        self.desc = card_data.get('desc', '')
        self.url = card_data.get('url', '')
        self.closed = card_data.get('closed', False)
        self.date_last_activity = card_data.get('dateLastActivity', '')
        self.member_ids = card_data.get('idMembers', [])
        self.list_id = card_data.get('idList', '')
        self.board_id = card_data.get('idBoard', '')
        self._members = None
        self._actions = None
        
    @property
    def description(self):
        return self.desc
    
    def get_members(self, api_key: str, token: str) -> List[Dict]:
        """Get card members."""
        if self._members is None and self.member_ids:
            try:
                members = []
                for member_id in self.member_ids:
                    url = f"https://api.trello.com/1/members/{member_id}"
                    params = {'key': api_key, 'token': token}
                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code == 200:
                        members.append(response.json())
                self._members = members
            except Exception as e:
                print(f"Error getting members for card {self.name}: {e}")
                self._members = []
        return self._members or []
    
    def get_actions(self, api_key: str, token: str, filter_types: List[str] = None) -> List[Dict]:
        """Get card actions/activities."""
        if self._actions is None:
            try:
                url = f"https://api.trello.com/1/cards/{self.id}/actions"
                params = {
                    'key': api_key, 
                    'token': token,
                    'limit': 50
                }
                if filter_types:
                    params['filter'] = ','.join(filter_types)
                
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    self._actions = response.json()
                else:
                    self._actions = []
            except Exception as e:
                print(f"Error getting actions for card {self.name}: {e}")
                self._actions = []
        return self._actions or []
    
    @property
    def members(self):
        """Property to maintain compatibility with py-trello."""
        return [Member(m) for m in (self._members or [])]
    
    def fetch_actions(self, api_key: str, token: str, action_filter: str = 'commentCard', limit: int = 50) -> List[Dict]:
        """Fetch card actions/comments."""
        try:
            url = f"https://api.trello.com/1/cards/{self.id}/actions"
            params = {
                'key': api_key,
                'token': token,
                'filter': action_filter,
                'limit': limit
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error fetching actions for card {self.name}: {e}")
        return []

class Member:
    """Represents a Trello member."""
    
    def __init__(self, member_data: Dict):
        self.id = member_data.get('id', '')
        self.full_name = member_data.get('fullName', '')
        self.username = member_data.get('username', '')

class TrelloList:
    """Represents a Trello list."""
    
    def __init__(self, list_data: Dict):
        self.id = list_data.get('id', '')
        self.name = list_data.get('name', '')
        self.closed = list_data.get('closed', False)

class TrelloBoard:
    """Represents a Trello board."""
    
    def __init__(self, board_data: Dict, api_key: str, token: str):
        self.id = board_data.get('id', '')
        self.name = board_data.get('name', '')
        self.closed = board_data.get('closed', False)
        self.api_key = api_key
        self.token = token
        self._cards = None
        self._lists = None
    
    def list_cards(self) -> List[TrelloCard]:
        """Get all cards in this board."""
        if self._cards is None:
            try:
                url = f"https://api.trello.com/1/boards/{self.id}/cards"
                params = {
                    'key': self.api_key,
                    'token': self.token,
                    'filter': 'open'  # Only get open cards
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    cards_data = response.json()
                    self._cards = [TrelloCard(card) for card in cards_data]
                else:
                    print(f"Error getting cards for board {self.name}: {response.status_code}")
                    self._cards = []
            except Exception as e:
                print(f"Error getting cards for board {self.name}: {e}")
                self._cards = []
        return self._cards or []
    
    def all_cards(self) -> List[TrelloCard]:
        """Get all cards (open and closed)."""
        try:
            url = f"https://api.trello.com/1/boards/{self.id}/cards"
            params = {
                'key': self.api_key,
                'token': self.token,
                'filter': 'all'  # Get all cards
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                cards_data = response.json()
                return [TrelloCard(card) for card in cards_data]
        except Exception as e:
            print(f"Error getting all cards for board {self.name}: {e}")
        return []
    
    def get_lists(self) -> List[TrelloList]:
        """Get all lists in this board."""
        if self._lists is None:
            try:
                url = f"https://api.trello.com/1/boards/{self.id}/lists"
                params = {
                    'key': self.api_key,
                    'token': self.token
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    lists_data = response.json()
                    self._lists = [TrelloList(list_data) for list_data in lists_data]
                else:
                    self._lists = []
            except Exception as e:
                print(f"Error getting lists for board {self.name}: {e}")
                self._lists = []
        return self._lists or []

class CustomTrelloClient:
    """Custom Trello client using direct HTTP requests."""
    
    def __init__(self, api_key: str = None, token: str = None):
        self.api_key = api_key or os.environ.get('TRELLO_API_KEY')
        self.token = token or os.environ.get('TRELLO_TOKEN')
        
        if not self.api_key or not self.token:
            raise ValueError("Trello API key and token are required")
    
    def test_connection(self) -> bool:
        """Test if the API connection works."""
        try:
            url = "https://api.trello.com/1/members/me"
            params = {'key': self.api_key, 'token': self.token}
            response = requests.get(url, params=params, timeout=10)
            return response.status_code == 200
        except Exception:
            return False
    
    def list_boards(self) -> List[TrelloBoard]:
        """Get all boards for the authenticated user."""
        try:
            url = "https://api.trello.com/1/members/me/boards"
            params = {
                'key': self.api_key,
                'token': self.token,
                'filter': 'open'  # Only get open boards
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                boards_data = response.json()
                return [TrelloBoard(board, self.api_key, self.token) for board in boards_data]
            else:
                print(f"Error getting boards: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"Error getting boards: {e}")
            return []
    
    def get_board(self, board_id: str) -> Optional[TrelloBoard]:
        """Get a specific board by ID."""
        try:
            url = f"https://api.trello.com/1/boards/{board_id}"
            params = {'key': self.api_key, 'token': self.token}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                board_data = response.json()
                return TrelloBoard(board_data, self.api_key, self.token)
        except Exception as e:
            print(f"Error getting board {board_id}: {e}")
        return None
    
    def add_comment_to_card(self, card_id: str, comment: str) -> bool:
        """Add a comment to a card."""
        try:
            url = f"https://api.trello.com/1/cards/{card_id}/actions/comments"
            data = {
                'key': self.api_key,
                'token': self.token,
                'text': comment
            }
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Error adding comment to card {card_id}: {e}")
            return False

# Test function
def test_custom_trello():
    """Test the custom Trello client."""
    try:
        client = CustomTrelloClient()
        print("Testing custom Trello client...")
        
        if not client.test_connection():
            print("[FAIL] Connection test failed")
            return False
        
        print("[PASS] Connection test passed")
        
        boards = client.list_boards()
        print(f"[PASS] Found {len(boards)} boards")
        
        for board in boards[:3]:  # Test first 3 boards
            print(f"  Board: {board.name} (ID: {board.id})")
            cards = board.list_cards()
            print(f"    Cards: {len(cards)}")
            
            # Test getting members for first few cards
            for card in cards[:2]:
                if card.member_ids:
                    members = card.get_members(client.api_key, client.token)
                    print(f"      Card '{card.name}' has {len(members)} members")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Custom Trello client test failed: {e}")
        return False

if __name__ == "__main__":
    test_custom_trello()