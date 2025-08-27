"""
Trello Sync Service - Hourly synchronization of Trello cards and comments
Runs independently to populate team_tracker_v2.db with all card data
"""

import os
import sys
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
import re
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import Trello client
from trello import TrelloClient

# Import database connection
from database_schema_v2 import get_db_connection

class TrelloSyncService:
    def __init__(self):
        """Initialize the sync service with Trello credentials"""
        self.api_key = os.environ.get('TRELLO_API_KEY')
        self.api_secret = os.environ.get('TRELLO_API_SECRET')
        self.token = os.environ.get('TRELLO_TOKEN')
        
        if not all([self.api_key, self.token]):
            raise ValueError("Missing Trello credentials in environment variables")
        
        # Initialize Trello client
        self.client = TrelloClient(
            api_key=self.api_key,
            api_secret=self.api_secret,
            token=self.token
        )
        
        # Get team members from production database
        self.team_members = self.load_team_members()
        
        print(f"[INIT] Trello Sync Service initialized")
        print(f"[INFO] Loaded {len(self.team_members)} team members")
    
    def load_team_members(self) -> Dict[str, str]:
        """Load team members from production database"""
        team_members = {}
        
        try:
            # Try to load from production_db.py if it exists
            import production_db
            conn = production_db.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT name, whatsapp_number FROM team_members WHERE is_active = TRUE')
            for name, whatsapp in cursor.fetchall():
                if name and whatsapp:
                    team_members[name] = whatsapp
            conn.close()
        except:
            # Fallback to environment variables
            env_members = {
                'Lancey': os.environ.get('TEAM_MEMBER_LANCEY'),
                'Levy': os.environ.get('TEAM_MEMBER_LEVY'),
                'Wendy': os.environ.get('TEAM_MEMBER_WENDY'),
                'Forka': os.environ.get('TEAM_MEMBER_FORKA'),
                'Brayan': os.environ.get('TEAM_MEMBER_BRAYAN'),
                'Breyden': os.environ.get('TEAM_MEMBER_BREYDEN'),
            }
            team_members = {k: v for k, v in env_members.items() if v}
        
        return team_members
    
    def sync_all_cards(self, board_id: str = None) -> Dict:
        """Main sync function - fetches all cards and their comments"""
        
        sync_stats = {
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
            # Get all boards if no board_id specified
            if not board_id:
                boards = self.client.list_boards()
                # Look for the EEsystems board
                target_board = None
                for board in boards:
                    if 'eesystem' in board.name.lower() or 'jgv' in board.name.lower():
                        target_board = board
                        break
                
                if not target_board:
                    raise ValueError("Could not find EEsystems/JGV board")
            else:
                target_board = self.client.get_board(board_id)
            
            print(f"[SYNC] Processing board: {target_board.name}")
            
            # Get all lists on the board
            lists = target_board.list_lists()
            list_map = {lst.id: lst.name for lst in lists}
            
            # Get all cards on the board
            cards = target_board.get_cards(card_filter='all')
            print(f"[INFO] Found {len(cards)} total cards on board")
            
            for card in cards:
                try:
                    # Sync card data
                    self.sync_card(card, list_map.get(card.list_id, 'Unknown'), target_board.name, target_board.id)
                    sync_stats['cards_synced'] += 1
                    
                    # Sync comments for this card
                    comments_synced = self.sync_card_comments(card)
                    sync_stats['comments_synced'] += comments_synced
                    
                    # Detect and store assignment
                    assignment = self.detect_assignment(card)
                    if assignment:
                        self.store_assignment(card.id, assignment)
                        sync_stats['assignments_detected'] += 1
                    
                except Exception as e:
                    error_msg = f"Error syncing card {card.name}: {str(e)}"
                    print(f"[ERROR] {error_msg}")
                    sync_stats['errors'].append(error_msg)
            
            # Update sync history
            cursor.execute('''
                UPDATE sync_history 
                SET completed_at = ?, cards_synced = ?, comments_synced = ?, 
                    assignments_detected = ?, errors = ?, status = ?
                WHERE id = ?
            ''', (
                datetime.now(),
                sync_stats['cards_synced'],
                sync_stats['comments_synced'],
                sync_stats['assignments_detected'],
                json.dumps(sync_stats['errors']) if sync_stats['errors'] else None,
                'completed',
                sync_id
            ))
            conn.commit()
            
        except Exception as e:
            # Mark sync as failed
            cursor.execute('''
                UPDATE sync_history 
                SET completed_at = ?, errors = ?, status = ?
                WHERE id = ?
            ''', (datetime.now(), str(e), 'failed', sync_id))
            conn.commit()
            raise
        
        finally:
            conn.close()
        
        print(f"[COMPLETE] Sync finished: {sync_stats['cards_synced']} cards, {sync_stats['comments_synced']} comments")
        return sync_stats
    
    def sync_card(self, card, list_name: str, board_name: str, board_id: str):
        """Sync individual card to database"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Extract labels
        labels = json.dumps([{'id': l.id, 'name': l.name, 'color': l.color} for l in card.labels]) if card.labels else None
        
        # Upsert card data
        cursor.execute('''
            INSERT OR REPLACE INTO trello_cards (
                card_id, name, description, list_id, list_name, 
                board_id, board_name, due_date, labels, closed, url, last_synced
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            card.id,
            card.name,
            card.description,
            card.list_id,
            list_name,
            board_id,
            board_name,
            card.due_date,
            labels,
            card.closed,
            card.short_url,
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
    
    def sync_card_comments(self, card) -> int:
        """Fetch and store all comments for a card"""
        conn = get_db_connection()
        cursor = conn.cursor()
        comments_synced = 0
        
        try:
            # Fetch comments via API
            url = f"https://api.trello.com/1/cards/{card.id}/actions"
            params = {
                'filter': 'commentCard',
                'limit': 50,  # Get last 50 comments
                'key': self.api_key,
                'token': self.token
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                comments = response.json()
                
                for comment in comments:
                    try:
                        comment_id = comment.get('id')
                        comment_text = comment.get('data', {}).get('text', '')
                        commenter_name = comment.get('memberCreator', {}).get('fullName', '')
                        commenter_id = comment.get('memberCreator', {}).get('id', '')
                        comment_date = comment.get('date', '')
                        
                        # Check if comment is an update request from admin
                        is_update_request = self.is_update_request(comment_text, commenter_name)
                        
                        # Convert date
                        if comment_date:
                            comment_datetime = datetime.fromisoformat(comment_date.replace('Z', '+00:00'))
                        else:
                            comment_datetime = None
                        
                        # Insert or update comment
                        cursor.execute('''
                            INSERT OR REPLACE INTO card_comments (
                                card_id, comment_id, commenter_name, commenter_id,
                                comment_text, comment_date, is_update_request
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            card.id,
                            comment_id,
                            commenter_name,
                            commenter_id,
                            comment_text,
                            comment_datetime,
                            is_update_request
                        ))
                        comments_synced += 1
                        
                    except Exception as e:
                        print(f"[WARN] Could not sync comment: {e}")
                
                conn.commit()
                
        except Exception as e:
            print(f"[ERROR] Failed to fetch comments for card {card.name}: {e}")
        
        finally:
            conn.close()
        
        return comments_synced
    
    def is_update_request(self, comment_text: str, commenter_name: str) -> bool:
        """Check if a comment is an update request from admin"""
        admin_names = ['admin', 'criselle', 'james']
        
        if not any(name in commenter_name.lower() for name in admin_names):
            return False
        
        update_patterns = [
            'update',
            'status',
            'progress',
            'where are we',
            'how is this',
            'any updates',
            'please update',
            '?'  # Questions from admin often mean update request
        ]
        
        comment_lower = comment_text.lower()
        return any(pattern in comment_lower for pattern in update_patterns)
    
    def detect_assignment(self, card) -> Optional[Dict]:
        """Detect who is assigned to a card using multiple methods"""
        
        assignment = {
            'team_member': None,
            'whatsapp_number': None,
            'method': None,
            'confidence': 0.0
        }
        
        # Method 1: Check Trello card members (highest confidence)
        try:
            if hasattr(card, 'member_ids') and card.member_ids:
                # Get member details
                for member_id in card.member_ids:
                    # Match with team members by fetching member details
                    member_url = f"https://api.trello.com/1/members/{member_id}"
                    response = requests.get(member_url, params={'key': self.api_key, 'token': self.token})
                    if response.status_code == 200:
                        member_data = response.json()
                        member_name = member_data.get('fullName', '')
                        
                        # Match with our team members
                        for team_name, whatsapp in self.team_members.items():
                            if team_name.lower() in member_name.lower():
                                assignment['team_member'] = team_name
                                assignment['whatsapp_number'] = whatsapp
                                assignment['method'] = 'trello_member'
                                assignment['confidence'] = 1.0
                                return assignment
        except Exception as e:
            print(f"[WARN] Could not check card members: {e}")
        
        # Method 2: Parse card description for @mentions (high confidence)
        if card.description:
            for team_name, whatsapp in self.team_members.items():
                patterns = [
                    f"@{team_name.lower()}",
                    f"assigned to {team_name.lower()}",
                    f"owner: {team_name.lower()}",
                    f"assignee: {team_name.lower()}"
                ]
                
                for pattern in patterns:
                    if pattern in card.description.lower():
                        assignment['team_member'] = team_name
                        assignment['whatsapp_number'] = whatsapp
                        assignment['method'] = 'description_mention'
                        assignment['confidence'] = 0.9
                        return assignment
        
        # Method 3: Check recent comments for assignment patterns (medium confidence)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT comment_text, commenter_name 
            FROM card_comments 
            WHERE card_id = ? 
            ORDER BY comment_date DESC 
            LIMIT 10
        ''', (card.id,))
        
        recent_comments = cursor.fetchall()
        conn.close()
        
        for comment_text, commenter_name in recent_comments:
            comment_lower = comment_text.lower() if comment_text else ''
            
            for team_name, whatsapp in self.team_members.items():
                # Check if team member is mentioned in assignment context
                assignment_patterns = [
                    f"@{team_name.lower()}",
                    f"{team_name.lower()} please",
                    f"{team_name.lower()} can you",
                    f"assign.*{team_name.lower()}",
                    f"{team_name.lower()}.*take this",
                    f"{team_name.lower()}.*handle"
                ]
                
                for pattern in assignment_patterns:
                    if re.search(pattern, comment_lower):
                        assignment['team_member'] = team_name
                        assignment['whatsapp_number'] = whatsapp
                        assignment['method'] = 'comment_pattern'
                        assignment['confidence'] = 0.7
                        return assignment
        
        # Method 4: List-based defaults (low confidence)
        list_defaults = {
            'mobile': 'Wendy',
            'app': 'Wendy',
            'website': 'Lancey',
            'web': 'Lancey',
            'landing': 'Lancey',
            'wordpress': 'Lancey',
            'seo': 'Levy',
            'content': 'Levy',
            'social': 'Brayan',
            'automation': 'Forka'
        }
        
        # Get list name
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT list_name FROM trello_cards WHERE card_id = ?', (card.id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            list_name = result[0].lower() if result[0] else ''
            card_name = card.name.lower()
            
            for keyword, default_member in list_defaults.items():
                if keyword in list_name or keyword in card_name:
                    if default_member in self.team_members:
                        assignment['team_member'] = default_member
                        assignment['whatsapp_number'] = self.team_members[default_member]
                        assignment['method'] = 'list_default'
                        assignment['confidence'] = 0.4
                        return assignment
        
        return None if not assignment['team_member'] else assignment
    
    def store_assignment(self, card_id: str, assignment: Dict):
        """Store detected assignment in database"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Deactivate previous assignments for this card
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

def run_sync_job():
    """Job function to run the sync"""
    print(f"\n[SYNC] Starting scheduled sync at {datetime.now()}")
    try:
        service = TrelloSyncService()
        stats = service.sync_all_cards()
        print(f"[SYNC] Completed: {stats}")
    except Exception as e:
        print(f"[ERROR] Sync failed: {e}")

def start_scheduler():
    """Start the background scheduler for hourly syncs"""
    scheduler = BackgroundScheduler()
    
    # Run sync every hour
    scheduler.add_job(
        func=run_sync_job,
        trigger=IntervalTrigger(hours=1),
        id='trello_sync_job',
        name='Hourly Trello Sync',
        replace_existing=True
    )
    
    # Also run immediately on startup
    scheduler.add_job(
        func=run_sync_job,
        trigger='date',
        run_date=datetime.now() + timedelta(seconds=5),
        id='initial_sync',
        name='Initial Sync on Startup'
    )
    
    scheduler.start()
    print(f"[SCHEDULER] Started - will sync every hour")
    
    return scheduler

if __name__ == '__main__':
    print("[START] Trello Sync Service")
    
    # Run immediate sync
    try:
        service = TrelloSyncService()
        stats = service.sync_all_cards()
        print(f"\n[RESULTS] Initial sync complete:")
        print(f"  Cards synced: {stats['cards_synced']}")
        print(f"  Comments synced: {stats['comments_synced']}")
        print(f"  Assignments detected: {stats['assignments_detected']}")
        if stats['errors']:
            print(f"  Errors: {len(stats['errors'])}")
    except Exception as e:
        print(f"[ERROR] Initial sync failed: {e}")
    
    # Start scheduler for continuous operation
    if '--daemon' in sys.argv:
        scheduler = start_scheduler()
        try:
            # Keep the script running
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n[STOP] Shutting down scheduler")
            scheduler.shutdown()