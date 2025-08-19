#!/usr/bin/env python3
"""
Enhanced Trello Integration Module
Handles all Trello API operations for Team Update Tracker
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv
from trello import TrelloClient
import requests

load_dotenv()

class TrelloIntegration:
    """Enhanced Trello client for team update tracking."""
    
    def __init__(self):
        """Initialize Trello client with environment credentials."""
        self.api_key = os.environ.get('TRELLO_API_KEY')
        self.api_secret = os.environ.get('TRELLO_API_SECRET')
        self.token = os.environ.get('TRELLO_TOKEN')
        
        if not all([self.api_key, self.api_secret, self.token]):
            raise ValueError("Missing Trello credentials in environment variables")
        
        self.client = TrelloClient(
            api_key=self.api_key,
            api_secret=self.api_secret,
            token=self.token
        )
        
        # Cache for boards and members
        self._boards_cache = {}
        self._members_cache = {}
    
    def get_all_boards(self) -> List[Dict]:
        """Get all accessible Trello boards."""
        try:
            boards = self.client.list_boards()
            board_data = []
            
            for board in boards:
                if board.closed:  # Skip closed boards
                    continue
                    
                board_info = {
                    'id': board.id,
                    'name': board.name,
                    'url': board.url,
                    'description': board.description or '',
                    'closed': board.closed
                }
                board_data.append(board_info)
                self._boards_cache[board.id] = board
            
            return board_data
            
        except Exception as e:
            print(f"Error fetching boards: {e}")
            return []
    
    def get_board_members(self, board_id: str) -> Dict[str, Dict]:
        """Get all members of a specific board."""
        try:
            if board_id in self._boards_cache:
                board = self._boards_cache[board_id]
            else:
                board = self.client.get_board(board_id)
                self._boards_cache[board_id] = board
            
            members = {}
            for member in board.get_members():
                members[member.id] = {
                    'id': member.id,
                    'username': member.username,
                    'full_name': member.full_name,
                    'initials': member.initials
                }
                self._members_cache[member.id] = member
            
            return members
            
        except Exception as e:
            print(f"Error fetching board members for {board_id}: {e}")
            return {}
    
    def get_card_comments(self, card_id: str) -> List[Dict]:
        """Get all comments for a specific card."""
        try:
            url = f"https://api.trello.com/1/cards/{card_id}/actions"
            params = {
                'key': self.api_key,
                'token': self.token,
                'filter': 'commentCard',
                'limit': 50
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            comments = []
            for action in response.json():
                if action['type'] == 'commentCard':
                    comment_data = {
                        'id': action['id'],
                        'text': action['data']['text'],
                        'date': action['date'],
                        'member_creator': {
                            'id': action['memberCreator']['id'],
                            'username': action['memberCreator']['username'],
                            'full_name': action['memberCreator']['fullName']
                        }
                    }
                    comments.append(comment_data)
            
            # Sort by date (newest first)
            comments.sort(key=lambda x: x['date'], reverse=True)
            return comments
            
        except Exception as e:
            print(f"Error fetching comments for card {card_id}: {e}")
            return []
    
    def analyze_card_for_updates(self, card: Dict, hours_threshold: int = 24) -> Dict:
        """Analyze a card to determine if it needs updates."""
        card_id = card['id']
        
        # Get comments
        comments = self.get_card_comments(card_id)
        
        # Find most recent comment
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
        
        # Determine if update is needed
        needs_update = hours_since_comment > hours_threshold
        
        return {
            'card_id': card_id,
            'needs_update': needs_update,
            'last_comment_date': last_comment_date.isoformat() if last_comment_date else None,
            'last_comment_by': last_comment_by,
            'hours_since_comment': hours_since_comment,
            'days_since_comment': days_since_comment,
            'total_comments': len(comments)
        }
    
    def scan_cards_needing_updates(self, board_ids: List[str] = None, hours_threshold: int = 24) -> List[Dict]:
        """Scan all cards and identify those needing updates."""
        if board_ids is None:
            boards = self.get_all_boards()
            board_ids = [board['id'] for board in boards]
        
        cards_needing_updates = []
        
        for board_id in board_ids:
            try:
                if board_id in self._boards_cache:
                    board = self._boards_cache[board_id]
                else:
                    board = self.client.get_board(board_id)
                    self._boards_cache[board_id] = board
                
                # Get board members for name mapping
                board_members = self.get_board_members(board_id)
                
                # Get all lists and cards
                for list_obj in board.list_lists():
                    if list_obj.closed:
                        continue
                    
                    for card in list_obj.list_cards():
                        if card.closed:
                            continue
                        
                        # Get assigned members
                        assigned_members = []
                        for member_id in card.member_ids:
                            if member_id in board_members:
                                assigned_members.append(board_members[member_id]['full_name'])
                        
                        # Skip unassigned cards for now (handle separately)
                        if not assigned_members:
                            continue
                        
                        # Analyze card for updates
                        card_data = {
                            'id': card.id,
                            'name': card.name,
                            'url': card.url,
                            'list_name': list_obj.name,
                            'board_name': board.name,
                            'board_id': board_id,
                            'assigned_members': assigned_members,
                            'due_date': card.due_date.isoformat() if card.due_date else None,
                            'labels': [label.name for label in card.labels if label.name]
                        }
                        
                        update_analysis = self.analyze_card_for_updates(card_data, hours_threshold)
                        
                        if update_analysis['needs_update']:
                            # Merge card data with analysis
                            card_data.update(update_analysis)
                            cards_needing_updates.append(card_data)
            
            except Exception as e:
                print(f"Error scanning board {board_id}: {e}")
                continue
        
        return cards_needing_updates
    
    def get_unassigned_cards(self, board_ids: List[str] = None) -> List[Dict]:
        """Get all cards that have no assigned members."""
        if board_ids is None:
            boards = self.get_all_boards()
            board_ids = [board['id'] for board in boards]
        
        unassigned_cards = []
        
        for board_id in board_ids:
            try:
                if board_id in self._boards_cache:
                    board = self._boards_cache[board_id]
                else:
                    board = self.client.get_board(board_id)
                    self._boards_cache[board_id] = board
                
                for list_obj in board.list_lists():
                    if list_obj.closed:
                        continue
                    
                    for card in list_obj.list_cards():
                        if card.closed:
                            continue
                        
                        # Check if card has no assigned members
                        if not card.member_ids:
                            card_data = {
                                'id': card.id,
                                'name': card.name,
                                'url': card.url,
                                'list_name': list_obj.name,
                                'board_name': board.name,
                                'board_id': board_id,
                                'due_date': card.due_date.isoformat() if card.due_date else None,
                                'labels': [label.name for label in card.labels if label.name]
                            }
                            unassigned_cards.append(card_data)
            
            except Exception as e:
                print(f"Error scanning unassigned cards in board {board_id}: {e}")
                continue
        
        return unassigned_cards
    
    def get_team_performance_metrics(self, board_ids: List[str] = None, days_back: int = 30) -> Dict:
        """Calculate team performance metrics."""
        if board_ids is None:
            boards = self.get_all_boards()
            board_ids = [board['id'] for board in boards]
        
        metrics = {
            'team_stats': {},
            'board_stats': {},
            'overall_stats': {
                'total_cards': 0,
                'assigned_cards': 0,
                'unassigned_cards': 0,
                'cards_with_recent_activity': 0
            }
        }
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        for board_id in board_ids:
            try:
                if board_id in self._boards_cache:
                    board = self._boards_cache[board_id]
                else:
                    board = self.client.get_board(board_id)
                    self._boards_cache[board_id] = board
                
                board_members = self.get_board_members(board_id)
                board_stats = {
                    'total_cards': 0,
                    'assigned_cards': 0,
                    'active_cards': 0
                }
                
                for list_obj in board.list_lists():
                    if list_obj.closed:
                        continue
                    
                    for card in list_obj.list_cards():
                        if card.closed:
                            continue
                        
                        board_stats['total_cards'] += 1
                        metrics['overall_stats']['total_cards'] += 1
                        
                        if card.member_ids:
                            board_stats['assigned_cards'] += 1
                            metrics['overall_stats']['assigned_cards'] += 1
                            
                            # Check for recent activity
                            comments = self.get_card_comments(card.id)
                            has_recent_activity = False
                            
                            for comment in comments:
                                comment_date = datetime.fromisoformat(comment['date'].replace('Z', '+00:00'))
                                if comment_date.replace(tzinfo=None) > cutoff_date:
                                    has_recent_activity = True
                                    break
                            
                            if has_recent_activity:
                                board_stats['active_cards'] += 1
                                metrics['overall_stats']['cards_with_recent_activity'] += 1
                            
                            # Track individual member stats
                            for member_id in card.member_ids:
                                if member_id in board_members:
                                    member_name = board_members[member_id]['full_name']
                                    if member_name not in metrics['team_stats']:
                                        metrics['team_stats'][member_name] = {
                                            'assigned_cards': 0,
                                            'active_cards': 0,
                                            'response_rate': 0
                                        }
                                    
                                    metrics['team_stats'][member_name]['assigned_cards'] += 1
                                    if has_recent_activity:
                                        metrics['team_stats'][member_name]['active_cards'] += 1
                        else:
                            metrics['overall_stats']['unassigned_cards'] += 1
                
                metrics['board_stats'][board.name] = board_stats
                
            except Exception as e:
                print(f"Error calculating metrics for board {board_id}: {e}")
                continue
        
        # Calculate response rates
        for member_name, stats in metrics['team_stats'].items():
            if stats['assigned_cards'] > 0:
                stats['response_rate'] = (stats['active_cards'] / stats['assigned_cards']) * 100
            else:
                stats['response_rate'] = 0
        
        return metrics

def test_trello_integration():
    """Test Trello integration functionality."""
    try:
        trello = TrelloIntegration()
        
        print("Testing Trello integration...")
        
        # Test getting boards
        boards = trello.get_all_boards()
        print(f"Found {len(boards)} boards")
        
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
            
            # Test performance metrics
            metrics = trello.get_team_performance_metrics(board_ids=[boards[0]['id']])
            print(f"Team performance metrics calculated for {len(metrics['team_stats'])} members")
        
        return True
        
    except Exception as e:
        print(f"Trello integration test failed: {e}")
        return False

if __name__ == "__main__":
    if test_trello_integration():
        print("✅ Trello integration test passed")
    else:
        print("❌ Trello integration test failed")