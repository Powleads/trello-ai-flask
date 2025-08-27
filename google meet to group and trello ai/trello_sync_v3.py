"""
Trello Sync V3 - Improved assignment detection and efficient updates
Assignment based on first non-admin commenter or explicit assignment
"""

import os
import sqlite3
import requests
from datetime import datetime
import re
from dotenv import load_dotenv
from custom_trello import CustomTrelloClient

load_dotenv()

class TrelloSyncV3:
    def __init__(self):
        self.api_key = os.environ.get('TRELLO_API_KEY')
        self.token = os.environ.get('TRELLO_TOKEN')
        self.client = CustomTrelloClient(api_key=self.api_key, token=self.token)
        
        # Admin names to exclude from auto-assignment
        self.admin_names = ['admin', 'criselle', 'james', 'james taylor']
        
        # Team members for assignment
        self.team_members = {
            'Lancey': '639264438378@c.us',
            'Levy': '237659250977@c.us',
            'Wendy': '237677079267@c.us',
            'Forka': '237652275097@c.us',
            'Brayan': '237676267420@c.us',
            'Breyden': '13179979692@c.us',
        }
        
        print(f"[INIT] Trello Sync V3 initialized")
    
    def get_db_connection(self):
        return sqlite3.connect('team_tracker_v2.db', 
                              detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    
    def sync_board(self):
        """Main sync function - efficient updates"""
        
        # Target lists
        TARGET_LISTS = [
            'NEW TASKS',
            'DOING - IN PROGRESS', 
            'BLOCKED',
            'REVIEW - APPROVAL',
            'FOREVER TASKS'
        ]
        
        # Find EEInteractive board
        boards = self.client.list_boards()
        target_board = None
        
        for board in boards:
            if 'eeinteractive' in board.name.lower():
                target_board = board
                break
        
        if not target_board:
            raise Exception("EEInteractive board not found")
        
        print(f"[BOARD] Found: {target_board.name}")
        
        # Get lists
        lists = target_board.get_lists()
        target_list_map = {}
        
        for lst in lists:
            if lst.name in TARGET_LISTS:
                target_list_map[lst.id] = lst.name
        
        print(f"[LISTS] Monitoring {len(target_list_map)} lists: {list(target_list_map.values())}")
        
        # Get all cards
        all_cards = target_board.list_cards()
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Start sync record
        cursor.execute('''
            INSERT INTO sync_history (sync_type, started_at, status)
            VALUES (?, ?, ?)
        ''', ('smart', datetime.now(), 'running'))
        sync_id = cursor.lastrowid
        conn.commit()
        
        stats = {
            'new_cards': 0,
            'updated_cards': 0,
            'new_comments': 0,
            'new_assignments': 0,
            'list_changes': 0
        }
        
        # Process each card
        for card in all_cards:
            if card.list_id not in target_list_map:
                continue  # Skip cards not in target lists
            
            list_name = target_list_map[card.list_id]
            
            # Check if card exists
            cursor.execute('SELECT list_name, last_synced FROM trello_cards WHERE card_id = ?', (card.id,))
            existing = cursor.fetchone()
            
            if existing:
                old_list = existing[0]
                
                # Update card (track list movement)
                if old_list != list_name:
                    stats['list_changes'] += 1
                    print(f"[MOVED] {card.name}: {old_list} -> {list_name}")
                
                cursor.execute('''
                    UPDATE trello_cards 
                    SET name = ?, description = ?, list_name = ?, list_id = ?, 
                        closed = ?, last_synced = ?
                    WHERE card_id = ?
                ''', (card.name, card.desc, list_name, card.list_id, 
                      card.closed, datetime.now(), card.id))
                stats['updated_cards'] += 1
                
            else:
                # New card - insert
                cursor.execute('''
                    INSERT INTO trello_cards (
                        card_id, name, description, list_id, list_name,
                        board_id, board_name, closed, url, created_at, last_synced
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    card.id, card.name, card.desc, card.list_id, list_name,
                    target_board.id, target_board.name, card.closed, card.url,
                    datetime.now(), datetime.now()
                ))
                stats['new_cards'] += 1
                print(f"[NEW] {card.name} in {list_name}")
            
            # Commit changes so far to avoid locks
            conn.commit()
            
            # Sync comments and detect assignment
            comment_stats = self.sync_card_comments(card.id)
            stats['new_comments'] += comment_stats['new_comments']
            
            # Detect and update assignment
            assignment = self.detect_assignment(card.id)
            if assignment:
                if self.update_assignment(card.id, assignment):
                    stats['new_assignments'] += 1
        
        # Complete sync
        cursor.execute('''
            UPDATE sync_history 
            SET completed_at = ?, cards_synced = ?, comments_synced = ?, 
                assignments_detected = ?, status = ?
            WHERE id = ?
        ''', (datetime.now(), stats['updated_cards'] + stats['new_cards'],
              stats['new_comments'], stats['new_assignments'], 'completed', sync_id))
        
        conn.commit()
        conn.close()
        
        print(f"\n[COMPLETE] Sync Summary:")
        print(f"  New cards: {stats['new_cards']}")
        print(f"  Updated cards: {stats['updated_cards']}")
        print(f"  List changes: {stats['list_changes']}")
        print(f"  New comments: {stats['new_comments']}")
        print(f"  New assignments: {stats['new_assignments']}")
        
        return stats
    
    def sync_card_comments(self, card_id):
        """Sync comments for a card - only new ones"""
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Get latest comment date we have
        cursor.execute('''
            SELECT MAX(comment_date) FROM card_comments WHERE card_id = ?
        ''', (card_id,))
        result = cursor.fetchone()
        
        # Handle both string and datetime results
        if result[0]:
            if isinstance(result[0], str):
                try:
                    # Try to parse as ISO format
                    latest_date = datetime.fromisoformat(result[0].replace('Z', '+00:00'))
                except:
                    latest_date = datetime(2020, 1, 1)
            else:
                latest_date = result[0]
        else:
            latest_date = datetime(2020, 1, 1)
        
        # Ensure latest_date is timezone-naive for comparison
        if hasattr(latest_date, 'tzinfo') and latest_date.tzinfo:
            latest_date = latest_date.replace(tzinfo=None)
        
        # Fetch comments from API
        url = f"https://api.trello.com/1/cards/{card_id}/actions"
        params = {
            'filter': 'commentCard',
            'limit': 50,
            'key': self.api_key,
            'token': self.token
        }
        
        stats = {'new_comments': 0}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                comments = response.json()
                
                for comment in comments:
                    comment_date_str = comment.get('date', '')
                    
                    # Parse date
                    if comment_date_str:
                        comment_date = datetime.fromisoformat(comment_date_str.replace('Z', '+00:00'))
                        # Make timezone-naive for comparison
                        if comment_date.tzinfo:
                            comment_date = comment_date.replace(tzinfo=None)
                    else:
                        continue
                    
                    # Only process new comments  
                    if comment_date <= latest_date:
                        continue
                    
                    comment_id = comment.get('id')
                    comment_text = comment.get('data', {}).get('text', '')
                    commenter_name = comment.get('memberCreator', {}).get('fullName', '')
                    commenter_id = comment.get('memberCreator', {}).get('id', '')
                    
                    # Check if it's an update request
                    is_update_request = False
                    if any(admin in commenter_name.lower() for admin in self.admin_names):
                        update_keywords = ['update', 'status', 'progress', '?', 'where', 'how']
                        if any(kw in comment_text.lower() for kw in update_keywords):
                            is_update_request = True
                    
                    # Insert comment
                    cursor.execute('''
                        INSERT OR REPLACE INTO card_comments (
                            card_id, comment_id, commenter_name, commenter_id,
                            comment_text, comment_date, is_update_request
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (card_id, comment_id, commenter_name, commenter_id,
                          comment_text, comment_date, is_update_request))
                    
                    stats['new_comments'] += 1
                
                conn.commit()
                
        except Exception as e:
            print(f"[ERROR] Failed to sync comments for {card_id}: {e}")
        
        finally:
            conn.close()
        
        return stats
    
    def detect_assignment(self, card_id):
        """
        Detect assignment based on:
        1. Explicit "assign {name}" in comments (INCLUDING from admin)
        2. First non-admin commenter
        """
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Get all comments ordered by date DESC to get latest assignment first
        cursor.execute('''
            SELECT commenter_name, comment_text, comment_date
            FROM card_comments
            WHERE card_id = ?
            ORDER BY comment_date DESC
        ''', (card_id,))
        
        comments = cursor.fetchall()
        conn.close()
        
        if not comments:
            return None
        
        # First check for explicit assignment (INCLUDING admin comments)
        # Check most recent first in case of reassignment
        for commenter_name, comment_text, comment_date in comments:
            comment_lower = comment_text.lower() if comment_text else ''
            
            # Check for "assign {name}" pattern - works even from admin
            assign_match = re.search(r'assign[s]?\s+(\w+)', comment_lower)
            if assign_match:
                assigned_name = assign_match.group(1)
                
                # Match with team members
                for team_name, whatsapp in self.team_members.items():
                    if team_name.lower() == assigned_name or assigned_name in team_name.lower():
                        print(f"[ASSIGN] Explicit assignment found: {team_name}")
                        return {
                            'team_member': team_name,
                            'whatsapp_number': whatsapp,
                            'method': 'explicit_assignment',
                            'confidence': 1.0
                        }
        
        # Then check for first non-admin commenter
        # Need to reverse the list since we got them DESC for assignment check
        for commenter_name, comment_text, comment_date in reversed(comments):
            commenter_lower = commenter_name.lower() if commenter_name else ''
            
            # Skip admin comments
            if any(admin in commenter_lower for admin in self.admin_names):
                continue
            
            # Match commenter with team members
            for team_name, whatsapp in self.team_members.items():
                if team_name.lower() in commenter_lower:
                    print(f"[ASSIGN] First commenter assignment: {team_name}")
                    return {
                        'team_member': team_name,
                        'whatsapp_number': whatsapp,
                        'method': 'first_commenter',
                        'confidence': 0.9
                    }
            
            # If commenter doesn't match known team members but isn't admin,
            # still record them
            if commenter_name and commenter_name.strip():
                print(f"[ASSIGN] Unknown commenter (not in team list): {commenter_name}")
                # You might want to add this person to team_members_cache
                
        return None
    
    def update_assignment(self, card_id, assignment):
        """Update card assignment if changed"""
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Check current assignment
        cursor.execute('''
            SELECT team_member, assignment_method
            FROM card_assignments
            WHERE card_id = ? AND is_active = 1
        ''', (card_id,))
        
        current = cursor.fetchone()
        
        # Only update if different or new
        if not current or current[0] != assignment['team_member']:
            # Deactivate old assignments
            cursor.execute('''
                UPDATE card_assignments SET is_active = 0 WHERE card_id = ?
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
            
            # Get card name for logging
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT name FROM trello_cards WHERE card_id = ?', (card_id,))
            card_name = cursor.fetchone()[0]
            conn.close()
            
            print(f"[UPDATE] {card_name} -> {assignment['team_member']} ({assignment['method']})")
            return True
        
        conn.close()
        return False

if __name__ == '__main__':
    print("=== Trello Sync V3 - Starting ===\n")
    
    try:
        sync = TrelloSyncV3()
        stats = sync.sync_board()
        
    except Exception as e:
        print(f"[FATAL] Sync failed: {e}")
        import traceback
        traceback.print_exc()