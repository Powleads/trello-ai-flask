#!/usr/bin/env python3
"""
Enhanced Team Tracker - Improved assignee comment detection and database tracking
Fixes the core issue of not properly detecting assignee-specific comments
"""

import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from production_db import get_production_db
import pytz

class EnhancedTeamTracker:
    """Enhanced team tracker with proper assignee comment detection and database tracking"""
    
    def __init__(self):
        self.db = get_production_db()
        # Initialize team members table and seed if needed
        self.db.init_team_members_table()
        self.team_members = self._load_team_members()
        self.api_key = os.environ.get('TRELLO_API_KEY')
        self.token = os.environ.get('TRELLO_TOKEN')
        self.vegas_tz = pytz.timezone('America/Los_Angeles')
        
    def _load_team_members(self) -> Dict[str, str]:
        """Load team members - prioritize database over environment variables"""
        team_members = {}
        
        # Priority 1: Database team members (overrides everything)
        try:
            db_team_members = self.db.get_team_members()
            if db_team_members:
                team_members = db_team_members
                print(f"[ENHANCED] Using database team members: {len(team_members)} members")
                
                # Seed database if empty on first run
                if not team_members:
                    self.db.seed_team_members()
                    team_members = self.db.get_team_members()
                    print(f"[ENHANCED] Seeded database with {len(team_members)} team members")
                    
                return team_members
        except Exception as e:
            print(f"[ENHANCED] Error loading from database: {e}")
        
        # Priority 2: Environment variables (legacy support)  
        for key, value in os.environ.items():
            if key.startswith('TEAM_MEMBER_'):
                name = key.replace('TEAM_MEMBER_', '').replace('_', ' ').title()
                team_members[name] = value
        
        if team_members:
            print(f"[ENHANCED] Using environment variables: {len(team_members)} members")
            return team_members
        
        # Priority 3: Global TEAM_MEMBERS from web_app
        try:
            from web_app import TEAM_MEMBERS
            team_members = TEAM_MEMBERS.copy()
            print(f"[ENHANCED] Using global TEAM_MEMBERS from web_app")
            return team_members
        except ImportError:
            pass
        
        # Priority 4: Ultimate fallback (current active team only)
        team_members = {
            'Lancey': '639264438378@c.us',
            'Levy': '237659250977@c.us', 
            'Wendy': '237677079267@c.us',
            'Forka': '237652275097@c.us',
            'Brayan': '237676267420@c.us',
            'Breyden': '13179979692@c.us'
            # NOTE: Removed James Taylor, Dustin Salinas, Ezechiel per user request
        }
        print(f"[ENHANCED] Using fallback team members (active team only): {len(team_members)} members")
        
        return team_members
    
    def get_board_members_mapping(self):
        """Get board member mapping using same board detection as scan_cards."""
        try:
            if not self.api_key or not self.token:
                print(f"[ENHANCED] Missing Trello credentials")
                return {}
            
            # Import trello_client from web_app - use same board detection
            from web_app import trello_client
            
            if not trello_client:
                print(f"[ENHANCED] Trello client not available")
                return {}
            
            # Use SAME board detection logic as scan_cards function
            boards = trello_client.list_boards()
            eeinteractive_board = None
            
            for board in boards:
                if board.closed:
                    continue
                if 'eeinteractive' in board.name.lower():
                    eeinteractive_board = board
                    break
            
            if not eeinteractive_board:
                print(f"[ENHANCED] EEInteractive board not found")
                return {}
            
            board_id = eeinteractive_board.id
            print(f"[ENHANCED] Using board '{eeinteractive_board.name}' (ID: {board_id})")
            
            # Get board members
            url = f"https://api.trello.com/1/boards/{board_id}/members"
            params = {
                'key': self.api_key,
                'token': self.token,
                'fields': 'id,fullName,username'
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                print(f"[ENHANCED] Failed to get board members: {response.status_code}")
                return {}
            
            board_members = response.json()
            print(f"[ENHANCED] Found {len(board_members)} board members")
            member_mapping = {}
            
            # Debug: Show all board members and team members
            print(f"[ENHANCED] Available board members:")
            for member in board_members:
                member_name = member.get('fullName', '').strip()
                member_id = member.get('id', '')
                print(f"  - {member_name} (ID: {member_id})")
            
            print(f"[ENHANCED] Team members to match:")
            for team_name, whatsapp in self.team_members.items():
                print(f"  - {team_name} -> {whatsapp}")
            
            # Create mapping from Trello member ID to team member info
            for member in board_members:
                member_name = member.get('fullName', '').strip()
                member_id = member.get('id', '')
                
                if not member_name or not member_id:
                    continue
                    
                # Match to our team members with name variations
                matched = False
                for team_name, whatsapp in self.team_members.items():
                    if matched:
                        break
                        
                    team_lower = team_name.lower()
                    member_lower = member_name.lower()
                    
                    # Enhanced fuzzy matching with variations and word-based matching
                    name_variations = [
                        team_lower,
                        team_lower.replace('ey', 'y'),  # Lancey -> Lancy
                        team_lower.replace('y', 'ey'),  # Lancy -> Lancey
                        team_lower.replace(' ', ''),    # Remove spaces
                    ]
                    
                    print(f"[ENHANCED] Checking '{member_name}' vs '{team_name}'")
                    
                    # Method 1: Direct variations matching
                    for variation in name_variations:
                        if (variation in member_lower or 
                            member_lower in variation or
                            any(part in member_lower for part in variation.split() if len(part) > 2)):
                            member_mapping[member_id] = {
                                'team_name': team_name,
                                'trello_name': member_name,
                                'whatsapp': whatsapp
                            }
                            print(f"[ENHANCED] ✅ MATCHED {member_name} ({member_id}) -> {team_name} (direct)")
                            matched = True
                            break
                    
                    # Method 2: Fuzzy word-based matching for full names
                    if not matched:
                        member_words = member_lower.split()
                        team_words = team_lower.split()
                        
                        # Check if team name appears as first word or substring in member name
                        for team_word in team_words:
                            if len(team_word) > 2:  # Skip short words
                                for member_word in member_words:
                                    if (team_word in member_word or 
                                        member_word in team_word or
                                        abs(len(team_word) - len(member_word)) <= 2):  # Allow 2 char difference
                                        # Additional fuzzy check for similar names
                                        similar_chars = sum(1 for a, b in zip(team_word, member_word) if a == b)
                                        if similar_chars >= max(3, len(team_word) - 2):  # Allow 2 char mismatch
                                            member_mapping[member_id] = {
                                                'team_name': team_name,
                                                'trello_name': member_name,
                                                'whatsapp': whatsapp
                                            }
                                            print(f"[ENHANCED] ✅ MATCHED {member_name} ({member_id}) -> {team_name} (fuzzy)")
                                            matched = True
                                            break
                                if matched:
                                    break
                    
                    if not matched:
                        print(f"[ENHANCED] ❌ No match for '{member_name}' with '{team_name}'")
            
            print(f"[ENHANCED] Final mapping has {len(member_mapping)} members")
            
            return member_mapping
            
        except Exception as e:
            print(f"[ENHANCED] Error getting board members: {e}")
            return {}

    def get_assignee_last_comment_date(self, card_id: str, assignee_name: str) -> Optional[datetime]:
        """Get the date of the last comment by the specific assignee using board member ID matching"""
        try:
            if not self.api_key or not self.token:
                print(f"[ENHANCED] No Trello API credentials available")
                return None
            
            # Get board member mapping for accurate matching
            member_mapping = self.get_board_members_mapping()
            
            # Find the assignee's member ID
            assignee_member_id = None
            for member_id, member_info in member_mapping.items():
                if member_info['team_name'].lower() == assignee_name.lower():
                    assignee_member_id = member_id
                    print(f"[ENHANCED] Found member ID for {assignee_name}: {member_id}")
                    break
                
            comments_url = f"https://api.trello.com/1/cards/{card_id}/actions"
            params = {
                'filter': 'commentCard',
                'limit': 100,  # Get more comments to find assignee's last comment
                'key': self.api_key,
                'token': self.token
            }
            
            response = requests.get(comments_url, params=params)
            if response.status_code != 200:
                print(f"[ENHANCED] Failed to fetch comments: {response.status_code}")
                return None
                
            comments = response.json()
            
            # Find the most recent comment by the assignee
            for comment in comments:
                commenter_id = comment.get('memberCreator', {}).get('id', '')
                commenter_name = comment.get('memberCreator', {}).get('fullName', '').lower()
                
                # Skip admin comments
                if 'admin' in commenter_name or 'criselle' in commenter_name:
                    continue
                
                # First try exact member ID match (most accurate)
                if assignee_member_id and commenter_id == assignee_member_id:
                    print(f"[ENHANCED] Found comment by {assignee_name} using member ID match")
                    is_assignee_comment = True
                else:
                    # Fallback to enhanced name matching
                    assignee_lower = assignee_name.lower()
                    assignee_variations = [
                        assignee_lower,
                        assignee_lower.replace('ey', 'y'),  # Lancey -> Lancy
                        assignee_lower.replace('y', 'ey'),  # Lancy -> Lancey
                        assignee_lower.replace(' ', ''),    # Remove spaces
                    ]
                    
                    # Check if this comment is from the assignee using enhanced matching
                    is_assignee_comment = False
                    for variation in assignee_variations:
                        if (variation in commenter_name or 
                            commenter_name in variation or
                            any(part in commenter_name for part in variation.split() if len(part) > 2)):
                            is_assignee_comment = True
                            print(f"[ENHANCED] Found comment by {assignee_name} using name matching")
                            break
                
                if is_assignee_comment:
                    
                    comment_date_str = comment.get('date', '')
                    if comment_date_str:
                        try:
                            comment_date = datetime.fromisoformat(comment_date_str.replace('Z', '+00:00'))
                            print(f"[ENHANCED] Found last comment by {assignee_name}: {comment_date}")
                            return comment_date
                        except Exception as e:
                            print(f"[ENHANCED] Error parsing comment date: {e}")
                            continue
            
            print(f"[ENHANCED] No comments found by assignee: {assignee_name}")
            return None
            
        except Exception as e:
            print(f"[ENHANCED] Error getting assignee last comment: {e}")
            return None
    
    def calculate_escalation_schedule(self, message_count: int) -> int:
        """Calculate hours to wait before next message based on escalation level"""
        escalation_schedule = {
            0: 24,  # First message -> wait 24 hours
            1: 12,  # Second message -> wait 12 hours  
            2: 6,   # Third message -> wait 6 hours
            3: 4,   # Fourth message -> wait 4 hours (escalate to manager)
        }
        return escalation_schedule.get(message_count, 24)  # Default 24h
    
    def should_send_message(self, card_id: str, assignee_name: str) -> Tuple[bool, str, Dict]:
        """Determine if we should send a message based on database tracking and assignee comments"""
        try:
            # Get card status from database
            card_status = self.db.get_team_tracker_card(card_id)
            
            # Get assignee's last comment date
            last_comment_date = self.get_assignee_last_comment_date(card_id, assignee_name)
            
            now = datetime.now(self.vegas_tz)
            
            # If no card status in database, this is first time seeing this card
            if not card_status:
                # If assignee has commented recently (within 24h), don't send message
                if last_comment_date:
                    hours_since_comment = (now.replace(tzinfo=last_comment_date.tzinfo) - last_comment_date).total_seconds() / 3600
                    if hours_since_comment < 24:
                        return False, f"Assignee commented {hours_since_comment:.1f}h ago", {}
                
                # First message - send it
                return True, "First message to assignee", {
                    'escalation_level': 1,
                    'next_followup_hours': 24,
                    'last_comment_date': last_comment_date
                }
            
            # Card exists in database - check if assignee has commented since last message
            last_message_sent = card_status.get('last_message_sent')
            last_tracked_comment = card_status.get('last_assignee_comment_date')
            
            # If assignee has commented since our last message, reset everything
            if last_comment_date and last_message_sent:
                try:
                    last_message_dt = datetime.fromisoformat(last_message_sent.replace('Z', '+00:00'))
                    
                    if last_comment_date > last_message_dt:
                        # Assignee responded! Mark as responded
                        self.db.mark_team_tracker_response(card_id)
                        return False, f"Assignee responded after last message", {}
                        
                except Exception as e:
                    print(f"[ENHANCED] Error comparing dates: {e}")
            
            # Check if it's time for next message based on escalation schedule
            next_message_due = card_status.get('next_message_due')
            if next_message_due:
                try:
                    next_due_dt = datetime.fromisoformat(next_message_due.replace('Z', '+00:00'))
                    if now.replace(tzinfo=next_due_dt.tzinfo) < next_due_dt:
                        hours_remaining = (next_due_dt - now.replace(tzinfo=next_due_dt.tzinfo)).total_seconds() / 3600
                        return False, f"Next message due in {hours_remaining:.1f}h", {}
                except Exception as e:
                    print(f"[ENHANCED] Error parsing next message due date: {e}")
            
            # Time to send escalated message
            current_level = card_status.get('escalation_level', 0)
            message_count = card_status.get('message_count', 0)
            
            if message_count >= 4:
                return False, "Maximum messages reached - escalate to manager", {}
            
            return True, f"Escalated message #{message_count + 1}", {
                'escalation_level': current_level + 1,
                'next_followup_hours': self.calculate_escalation_schedule(message_count),
                'message_count': message_count
            }
            
        except Exception as e:
            print(f"[ENHANCED] Error in should_send_message: {e}")
            return False, f"Error: {e}", {}
    
    def update_card_tracking(self, card_id: str, card_name: str, assignee_name: str, assignee_phone: str):
        """Update card tracking in database"""
        last_comment_date = self.get_assignee_last_comment_date(card_id, assignee_name)
        last_comment_str = last_comment_date.isoformat() if last_comment_date else None
        
        self.db.update_team_tracker_card(
            card_id=card_id,
            card_name=card_name,
            assignee_name=assignee_name,
            assignee_phone=assignee_phone,
            last_comment_date=last_comment_str
        )
    
    def log_message_sent(self, card_id: str, assignee_name: str, message_content: str, 
                        escalation_level: int, next_followup_hours: int):
        """Log that a message was sent"""
        return self.db.log_team_tracker_message(
            card_id=card_id,
            assignee_name=assignee_name,
            message_content=message_content,
            escalation_level=escalation_level,
            next_followup_hours=next_followup_hours
        )
    
    def get_cards_needing_messages(self, cards: List) -> List[Dict]:
        """Filter cards that need messages based on enhanced logic"""
        cards_needing_messages = []
        
        for card in cards:
            if card.get('assigned_user') and card.get('assigned_whatsapp'):
                card_id = card['card'].id if hasattr(card['card'], 'id') else card.get('card_id')
                assignee_name = card['assigned_user']
                
                # Update card tracking first
                self.update_card_tracking(
                    card_id=card_id,
                    card_name=card['card'].name if hasattr(card['card'], 'name') else card.get('card_name', ''),
                    assignee_name=assignee_name,
                    assignee_phone=card['assigned_whatsapp']
                )
                
                # Check if we should send message
                should_send, reason, message_data = self.should_send_message(card_id, assignee_name)
                
                if should_send:
                    card['message_data'] = message_data
                    card['send_reason'] = reason
                    
                    # Remove the raw card object to make it JSON serializable
                    card_copy = card.copy()
                    if 'card' in card_copy:
                        # Keep only essential data from the card object
                        trello_card = card_copy['card']
                        card_copy['card_id'] = card_id
                        card_copy['card_url'] = getattr(trello_card, 'url', '')
                        del card_copy['card']  # Remove the non-serializable object
                    
                    cards_needing_messages.append(card_copy)
                    print(f"[ENHANCED] SEND MESSAGE: {assignee_name} -> {card.get('name', 'Unknown')} ({reason})")
                else:
                    print(f"[ENHANCED] SKIP MESSAGE: {assignee_name} -> {card.get('name', 'Unknown')} ({reason})")
        
        return cards_needing_messages

# Global instance
enhanced_team_tracker = EnhancedTeamTracker()