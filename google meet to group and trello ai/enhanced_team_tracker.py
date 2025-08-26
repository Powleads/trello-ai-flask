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
        self.team_members = self._load_team_members()
        self.api_key = os.environ.get('TRELLO_API_KEY')
        self.token = os.environ.get('TRELLO_TOKEN')
        self.vegas_tz = pytz.timezone('America/Los_Angeles')
        
    def _load_team_members(self) -> Dict[str, str]:
        """Load team members from environment variables or database"""
        team_members = {}
        
        # Load from environment variables (production)
        for key, value in os.environ.items():
            if key.startswith('TEAM_MEMBER_'):
                name = key.replace('TEAM_MEMBER_', '').replace('_', ' ').title()
                team_members[name] = value
        
        # Fallback to hardcoded values if no env vars
        if not team_members:
            team_members = {
                'James Taylor': '19056064550@c.us',
                'Levy': '237659250977@c.us', 
                'Wendy': '237677079267@c.us',
                'Forka': '237652275097@c.us',
                'Brayan': '237676267420@c.us',
                'Ezechiel': '23754071907@c.us',
                'Dustin Salinas': '19054251997@c.us',
                'Breyden': '13179979692@c.us'
            }
        
        print(f"[ENHANCED] Loaded {len(team_members)} team members")
        return team_members
    
    def get_assignee_last_comment_date(self, card_id: str, assignee_name: str) -> Optional[datetime]:
        """Get the date of the last comment by the specific assignee"""
        try:
            if not self.api_key or not self.token:
                print(f"[ENHANCED] No Trello API credentials available")
                return None
                
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
            assignee_lower = assignee_name.lower()
            
            # Find the most recent comment by the assignee
            for comment in comments:
                commenter_name = comment.get('memberCreator', {}).get('fullName', '').lower()
                
                # Enhanced name matching with variations
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