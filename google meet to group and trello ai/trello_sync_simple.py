"""
Simple Trello Sync Service - Uses direct API calls like web_app.py
Fetches all cards and stores them in the database for processing
"""

import os
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import database connection
from database_schema_v2 import get_db_connection

# Import the custom Trello client that works in web_app.py
from custom_trello import CustomTrelloClient

class SimpleTrelloSync:
    def __init__(self):
        """Initialize with Trello credentials"""
        self.api_key = os.environ.get('TRELLO_API_KEY')
        self.token = os.environ.get('TRELLO_TOKEN')
        
        if not all([self.api_key, self.token]):
            raise ValueError("Missing TRELLO_API_KEY or TRELLO_TOKEN in environment")
        
        # Initialize CustomTrelloClient
        self.client = CustomTrelloClient(api_key=self.api_key, token=self.token)
        
        # Test connection
        if not self.client.test_connection():
            raise ValueError("Failed to connect to Trello API")
        
        # Get team members
        self.team_members = self.load_team_members()
        
        print(f"[INIT] Simple Sync Service initialized")
        print(f"[INFO] Loaded {len(self.team_members)} team members")
    
    def load_team_members(self) -> Dict[str, str]:
        """Load active team members"""
        team_members = {}
        
        # Load from environment variables
        env_members = {
            'Lancey': os.environ.get('TEAM_MEMBER_LANCEY'),
            'Levy': os.environ.get('TEAM_MEMBER_LEVY'),
            'Wendy': os.environ.get('TEAM_MEMBER_WENDY'),
            'Forka': os.environ.get('TEAM_MEMBER_FORKA'),
            'Brayan': os.environ.get('TEAM_MEMBER_BRAYAN'),
            'Breyden': os.environ.get('TEAM_MEMBER_BREYDEN'),
        }
        
        for name, whatsapp in env_members.items():
            if whatsapp:
                team_members[name] = whatsapp
                # Also cache in database
                self.cache_team_member(name, whatsapp)
        
        return team_members
    
    def cache_team_member(self, name: str, whatsapp: str):
        """Cache team member in database"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO team_members_cache (name, whatsapp_number)
            VALUES (?, ?)
        ''', (name, whatsapp))
        
        conn.commit()
        conn.close()
    
    def get_board_id(self) -> Optional[str]:
        """Get the JGV/EEsystems board ID"""
        
        # First check if we have a cached board ID
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT board_id FROM trello_cards LIMIT 1')
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            print(f"[INFO] Using cached board ID: {result[0]}")
            return result[0]
        
        # Otherwise, find it via API - using CustomTrelloClient
        try:
            boards = self.client.list_boards()
            
            # Look for EEinteractive or JGV board (same as web_app.py)
            for board in boards:
                board_name = board.name.lower()
                if 'eeinteractive' in board_name or 'jgv' in board_name:
                    print(f"[FOUND] Board: {board.name} (ID: {board.id})")
                    return board.id
            
            # If not found by name, just use the first board
            if boards:
                print(f"[INFO] Using first board: {boards[0].name} (ID: {boards[0].id})")
                return boards[0].id
                
        except Exception as e:
            print(f"[ERROR] Could not fetch boards: {e}")
        
        return None
    
    def sync_all_cards(self) -> Dict:
        """Sync all cards from the board"""
        
        stats = {
            'cards_synced': 0,
            'comments_synced': 0,
            'assignments_detected': 0,
            'errors': []
        }
        
        # Start sync record
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sync_history (sync_type, started_at, status)
            VALUES (?, ?, ?)
        ''', ('full', datetime.now(), 'running'))
        sync_id = cursor.lastrowid
        conn.commit()
        
        try:
            # Use CustomTrelloClient
            boards = self.client.list_boards()
            target_board = None
            
            for board in boards:
                board_name = board.name.lower()
                if 'eeinteractive' in board_name or 'jgv' in board_name:
                    target_board = board
                    print(f"[FOUND] Board: {board.name}")
                    break
            
            if not target_board and boards:
                target_board = boards[0]
                print(f"[INFO] Using first board: {target_board.name}")
            
            if not target_board:
                raise Exception("No boards found")
            
            board_id = target_board.id
            
            # Get all lists on the board
            lists = target_board.get_lists()
            list_map = {lst.id: lst.name for lst in lists}
            print(f"[INFO] Found {len(lists)} lists on board")
            
            # Get all cards on the board
            cards = target_board.list_cards()
            print(f"[INFO] Found {len(cards)} cards on board")
            
            # Process each card
            for card in cards:
                try:
                    # Get list name
                    list_name = list_map.get(card.list_id, 'Unknown')
                    
                    # Convert card object to dict for storage
                    card_dict = {
                        'id': card.id,
                        'name': card.name,
                        'desc': card.desc,
                        'idList': card.list_id,
                        'due': None,  # Will need to fetch separately if needed
                        'closed': card.closed,
                        'shortUrl': card.url,
                        'labels': [],  # Will need to fetch separately if needed
                        'members': []
                    }
                    
                    # Get card members
                    try:
                        if hasattr(card, 'member_ids') and card.member_ids:
                            for member_id in card.member_ids:
                                member_url = f"https://api.trello.com/1/members/{member_id}"
                                response = requests.get(member_url, params={'key': self.api_key, 'token': self.token})
                                if response.status_code == 200:
                                    member_data = response.json()
                                    card_dict['members'].append({
                                        'id': member_id,
                                        'fullName': member_data.get('fullName', ''),
                                        'username': member_data.get('username', '')
                                    })
                    except:
                        pass
                    
                    # Store card in database
                    self.store_card(card_dict, list_name, board_id)
                    stats['cards_synced'] += 1
                    
                    # Fetch and store comments
                    comments_count = self.sync_card_comments(card.id)
                    stats['comments_synced'] += comments_count
                    
                    # Detect assignment
                    assignment = self.detect_assignment(card_dict)
                    if assignment:
                        self.store_assignment(card.id, assignment)
                        stats['assignments_detected'] += 1
                    
                    print(f"[SYNC] Card: {card.name[:50]} - List: {list_name} - Assigned: {assignment['team_member'] if assignment else 'None'}")
                    
                except Exception as e:
                    error_msg = f"Error processing card {card.name}: {e}"
                    print(f"[ERROR] {error_msg}")
                    stats['errors'].append(error_msg)
            
            # Update sync history
            cursor.execute('''
                UPDATE sync_history 
                SET completed_at = ?, cards_synced = ?, comments_synced = ?, 
                    assignments_detected = ?, errors = ?, status = ?
                WHERE id = ?
            ''', (
                datetime.now(),
                stats['cards_synced'],
                stats['comments_synced'],
                stats['assignments_detected'],
                json.dumps(stats['errors'][:10]) if stats['errors'] else None,
                'completed',
                sync_id
            ))
            conn.commit()
            
        except Exception as e:
            cursor.execute('''
                UPDATE sync_history 
                SET completed_at = ?, errors = ?, status = ?
                WHERE id = ?
            ''', (datetime.now(), str(e), 'failed', sync_id))
            conn.commit()
            print(f"[ERROR] Sync failed: {e}")
        
        finally:
            conn.close()
        
        return stats
    
    def store_card(self, card: Dict, list_name: str, board_id: str):
        """Store card in database"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Parse due date if exists
        due_date = None
        if card.get('due'):
            try:
                due_date = datetime.fromisoformat(card['due'].replace('Z', '+00:00'))
            except:
                pass
        
        # Extract labels
        labels = None
        if card.get('labels'):
            labels = json.dumps(card['labels'])
        
        # Upsert card
        cursor.execute('''
            INSERT OR REPLACE INTO trello_cards (
                card_id, name, description, list_id, list_name,
                board_id, due_date, labels, closed, url, last_synced
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            card['id'],
            card.get('name', ''),
            card.get('desc', ''),
            card.get('idList'),
            list_name,
            board_id,
            due_date,
            labels,
            card.get('closed', False),
            card.get('shortUrl', ''),
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
    
    def sync_card_comments(self, card_id: str) -> int:
        """Fetch and store comments for a card"""
        
        url = f"https://api.trello.com/1/cards/{card_id}/actions"
        params = {
            'filter': 'commentCard',
            'limit': 25,
            'key': self.api_key,
            'token': self.token
        }
        
        conn = get_db_connection()
        cursor = conn.cursor()
        comments_count = 0
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                comments = response.json()
                
                for comment in comments:
                    try:
                        comment_id = comment.get('id')
                        comment_text = comment.get('data', {}).get('text', '')
                        commenter_name = comment.get('memberCreator', {}).get('fullName', '')
                        commenter_id = comment.get('memberCreator', {}).get('id', '')
                        comment_date_str = comment.get('date', '')
                        
                        # Parse date
                        comment_date = None
                        if comment_date_str:
                            comment_date = datetime.fromisoformat(comment_date_str.replace('Z', '+00:00'))
                        
                        # Check if update request
                        is_update_request = False
                        if 'admin' in commenter_name.lower() or 'criselle' in commenter_name.lower():
                            update_keywords = ['update', 'status', 'progress', '?']
                            is_update_request = any(kw in comment_text.lower() for kw in update_keywords)
                        
                        # Store comment
                        cursor.execute('''
                            INSERT OR REPLACE INTO card_comments (
                                card_id, comment_id, commenter_name, commenter_id,
                                comment_text, comment_date, is_update_request
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            card_id, comment_id, commenter_name, commenter_id,
                            comment_text, comment_date, is_update_request
                        ))
                        comments_count += 1
                        
                    except Exception as e:
                        print(f"[WARN] Could not store comment: {e}")
                
                conn.commit()
                
        except Exception as e:
            print(f"[WARN] Could not fetch comments for card {card_id}: {e}")
        
        finally:
            conn.close()
        
        return comments_count
    
    def detect_assignment(self, card: Dict) -> Optional[Dict]:
        """Detect assignment from card data"""
        
        assignment = None
        
        # Check card members first
        if card.get('members'):
            for member in card['members']:
                member_name = member.get('fullName', '').strip()
                
                # Match with team members
                for team_name, whatsapp in self.team_members.items():
                    if team_name.lower() in member_name.lower():
                        assignment = {
                            'team_member': team_name,
                            'whatsapp_number': whatsapp,
                            'method': 'trello_member',
                            'confidence': 1.0
                        }
                        return assignment
        
        # Check description for mentions
        desc = card.get('desc', '').lower()
        name = card.get('name', '').lower()
        
        for team_name, whatsapp in self.team_members.items():
            patterns = [
                f"@{team_name.lower()}",
                f"assigned to {team_name.lower()}",
                f"{team_name.lower()} -",
                f"owner: {team_name.lower()}"
            ]
            
            for pattern in patterns:
                if pattern in desc or pattern in name:
                    assignment = {
                        'team_member': team_name,
                        'whatsapp_number': whatsapp,
                        'method': 'description_mention',
                        'confidence': 0.8
                    }
                    return assignment
        
        # Check recent comments
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT comment_text FROM card_comments 
            WHERE card_id = ? 
            ORDER BY comment_date DESC 
            LIMIT 5
        ''', (card['id'],))
        
        comments = cursor.fetchall()
        conn.close()
        
        for (comment_text,) in comments:
            if comment_text:
                comment_lower = comment_text.lower()
                
                for team_name, whatsapp in self.team_members.items():
                    if f"@{team_name.lower()}" in comment_lower or f"{team_name.lower()} please" in comment_lower:
                        assignment = {
                            'team_member': team_name,
                            'whatsapp_number': whatsapp,
                            'method': 'comment_pattern',
                            'confidence': 0.6
                        }
                        return assignment
        
        return assignment
    
    def store_assignment(self, card_id: str, assignment: Dict):
        """Store assignment in database"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Deactivate old assignments
        cursor.execute('''
            UPDATE card_assignments 
            SET is_active = 0 
            WHERE card_id = ? AND is_active = 1
        ''', (card_id,))
        
        # Insert new assignment
        cursor.execute('''
            INSERT INTO card_assignments (
                card_id, team_member, whatsapp_number,
                assignment_method, confidence_score, assigned_by
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            card_id,
            assignment['team_member'],
            assignment['whatsapp_number'],
            assignment['method'],
            assignment['confidence'],
            'system'
        ))
        
        conn.commit()
        conn.close()

if __name__ == '__main__':
    print("[START] Simple Trello Sync")
    
    try:
        sync = SimpleTrelloSync()
        stats = sync.sync_all_cards()
        
        print(f"\n[COMPLETE] Sync Results:")
        print(f"  Cards synced: {stats['cards_synced']}")
        print(f"  Comments synced: {stats['comments_synced']}")
        print(f"  Assignments detected: {stats['assignments_detected']}")
        if stats['errors']:
            print(f"  Errors: {len(stats['errors'])}")
            
    except Exception as e:
        print(f"[FATAL] {e}")