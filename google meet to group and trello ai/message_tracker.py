#!/usr/bin/env python3
"""
Message Tracking System - SQLite database for tracking WhatsApp messages and preventing duplicates
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class MessageTracker:
    """Tracks WhatsApp messages sent to team members about Trello cards."""
    
    def __init__(self, db_path: str = "message_tracker.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Message logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS message_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_id TEXT NOT NULL,
                    card_name TEXT NOT NULL,
                    assignee_name TEXT NOT NULL,
                    assignee_phone TEXT,
                    message_content TEXT,
                    sent_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    delivery_status TEXT DEFAULT 'sent',
                    created_date DATE DEFAULT (DATE('now'))
                )
            ''')
            
            # Card interactions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS card_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_id TEXT NOT NULL,
                    card_name TEXT NOT NULL,
                    assignee_name TEXT NOT NULL,
                    assignee_phone TEXT,
                    message_count INTEGER DEFAULT 1,
                    last_message_sent DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_comment_timestamp DATETIME,
                    response_received BOOLEAN DEFAULT FALSE,
                    created_date DATE DEFAULT (DATE('now')),
                    UNIQUE(card_id, assignee_name)
                )
            ''')
            
            # Daily analytics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_analytics (
                    date DATE PRIMARY KEY,
                    total_messages_sent INTEGER DEFAULT 0,
                    unique_cards_messaged INTEGER DEFAULT 0,
                    unique_assignees_messaged INTEGER DEFAULT 0,
                    response_rate REAL DEFAULT 0.0
                )
            ''')
            
            conn.commit()
            print("Message tracking database initialized successfully")
    
    def log_message(self, card_id: str, card_name: str, assignee_name: str, 
                   assignee_phone: str, message_content: str, delivery_status: str = 'sent') -> int:
        """
        Log a sent message.
        
        Returns:
            Message log ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert message log
            cursor.execute('''
                INSERT INTO message_logs 
                (card_id, card_name, assignee_name, assignee_phone, message_content, delivery_status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (card_id, card_name, assignee_name, assignee_phone, message_content, delivery_status))
            
            message_id = cursor.lastrowid
            
            # Update or insert card interaction
            cursor.execute('''
                INSERT OR REPLACE INTO card_interactions 
                (card_id, card_name, assignee_name, assignee_phone, message_count, last_message_sent, response_received)
                VALUES (
                    ?, ?, ?, ?, 
                    COALESCE((SELECT message_count FROM card_interactions WHERE card_id = ? AND assignee_name = ?), 0) + 1,
                    CURRENT_TIMESTAMP,
                    FALSE
                )
            ''', (card_id, card_name, assignee_name, assignee_phone, card_id, assignee_name))
            
            # Update daily analytics
            today = datetime.now().date()
            cursor.execute('''
                INSERT OR REPLACE INTO daily_analytics (date, total_messages_sent, unique_cards_messaged, unique_assignees_messaged)
                VALUES (
                    ?, 
                    COALESCE((SELECT total_messages_sent FROM daily_analytics WHERE date = ?), 0) + 1,
                    (SELECT COUNT(DISTINCT card_id) FROM message_logs WHERE DATE(sent_timestamp) = ?),
                    (SELECT COUNT(DISTINCT assignee_name) FROM message_logs WHERE DATE(sent_timestamp) = ?)
                )
            ''', (today, today, today, today))
            
            conn.commit()
            return message_id
    
    def can_send_message(self, card_id: str, assignee_name: str, cooldown_hours: int = 24) -> Tuple[bool, Optional[str]]:
        """
        Check if a message can be sent to an assignee about a card.
        
        Returns:
            (can_send, reason_if_not)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT last_message_sent, message_count, response_received
                FROM card_interactions 
                WHERE card_id = ? AND assignee_name = ?
            ''', (card_id, assignee_name))
            
            result = cursor.fetchone()
            
            if not result:
                return True, None  # No previous messages
            
            last_sent_str, message_count, response_received = result
            last_sent = datetime.fromisoformat(last_sent_str)
            now = datetime.now()
            
            hours_since_last = (now - last_sent).total_seconds() / 3600
            
            if hours_since_last < cooldown_hours:
                remaining_hours = cooldown_hours - hours_since_last
                return False, f"Cooldown active: {remaining_hours:.1f} hours remaining"
            
            # Check if too many messages without response
            if message_count >= 3 and not response_received:
                return False, f"Already sent {message_count} messages without response"
            
            return True, None
    
    def get_card_message_status(self, card_id: str, assignee_name: str) -> Dict:
        """Get message status for a specific card-assignee combination."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT message_count, last_message_sent, response_received, last_comment_timestamp
                FROM card_interactions 
                WHERE card_id = ? AND assignee_name = ?
            ''', (card_id, assignee_name))
            
            result = cursor.fetchone()
            
            if not result:
                return {
                    'has_been_messaged': False,
                    'message_count': 0,
                    'last_message_sent': None,
                    'response_received': False,
                    'can_send': True,
                    'cooldown_remaining': 0
                }
            
            message_count, last_sent_str, response_received, last_comment_str = result
            last_sent = datetime.fromisoformat(last_sent_str)
            now = datetime.now()
            
            hours_since_last = (now - last_sent).total_seconds() / 3600
            cooldown_remaining = max(0, 24 - hours_since_last)
            
            can_send, reason = self.can_send_message(card_id, assignee_name)
            
            return {
                'has_been_messaged': True,
                'message_count': message_count,
                'last_message_sent': last_sent.isoformat(),
                'response_received': bool(response_received),
                'last_comment_timestamp': last_comment_str,
                'can_send': can_send,
                'cooldown_remaining': cooldown_remaining,
                'reason_if_blocked': reason if not can_send else None
            }
    
    def mark_response_received(self, card_id: str, assignee_name: str, comment_timestamp: datetime = None):
        """Mark that an assignee has responded to messages about a card."""
        if comment_timestamp is None:
            comment_timestamp = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE card_interactions 
                SET response_received = TRUE, last_comment_timestamp = ?
                WHERE card_id = ? AND assignee_name = ?
            ''', (comment_timestamp, card_id, assignee_name))
            
            conn.commit()
    
    def get_daily_analytics(self, date: datetime.date = None) -> Dict:
        """Get analytics for a specific date (default: today)."""
        if date is None:
            date = datetime.now().date()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT total_messages_sent, unique_cards_messaged, unique_assignees_messaged, response_rate
                FROM daily_analytics 
                WHERE date = ?
            ''', (date,))
            
            result = cursor.fetchone()
            
            if not result:
                return {
                    'date': date.isoformat(),
                    'total_messages_sent': 0,
                    'unique_cards_messaged': 0,
                    'unique_assignees_messaged': 0,
                    'response_rate': 0.0
                }
            
            total_sent, unique_cards, unique_assignees, response_rate = result
            
            return {
                'date': date.isoformat(),
                'total_messages_sent': total_sent or 0,
                'unique_cards_messaged': unique_cards or 0,
                'unique_assignees_messaged': unique_assignees or 0,
                'response_rate': response_rate or 0.0
            }
    
    def get_week_analytics(self) -> List[Dict]:
        """Get analytics for the past 7 days."""
        analytics = []
        today = datetime.now().date()
        
        for i in range(7):
            date = today - timedelta(days=i)
            day_analytics = self.get_daily_analytics(date)
            day_analytics['day_name'] = date.strftime('%A')
            analytics.append(day_analytics)
        
        return list(reversed(analytics))  # Most recent first
    
    def get_card_message_history(self, card_id: str, limit: int = 10) -> List[Dict]:
        """Get message history for a specific card."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT assignee_name, assignee_phone, message_content, sent_timestamp, delivery_status
                FROM message_logs 
                WHERE card_id = ?
                ORDER BY sent_timestamp DESC
                LIMIT ?
            ''', (card_id, limit))
            
            results = cursor.fetchall()
            
            return [
                {
                    'assignee_name': row[0],
                    'assignee_phone': row[1],
                    'message_content': row[2],
                    'sent_timestamp': row[3],
                    'delivery_status': row[4]
                }
                for row in results
            ]
    
    def get_assignee_stats(self, assignee_name: str) -> Dict:
        """Get statistics for a specific assignee."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total messages sent to this assignee
            cursor.execute('''
                SELECT COUNT(*) FROM message_logs WHERE assignee_name = ?
            ''', (assignee_name,))
            total_messages = cursor.fetchone()[0]
            
            # Cards they've been messaged about
            cursor.execute('''
                SELECT COUNT(DISTINCT card_id) FROM message_logs WHERE assignee_name = ?
            ''', (assignee_name,))
            cards_messaged_about = cursor.fetchone()[0]
            
            # Response rate (cards where they've responded)
            cursor.execute('''
                SELECT COUNT(*) FROM card_interactions 
                WHERE assignee_name = ? AND response_received = TRUE
            ''', (assignee_name,))
            responses_given = cursor.fetchone()[0]
            
            response_rate = (responses_given / cards_messaged_about * 100) if cards_messaged_about > 0 else 0
            
            return {
                'assignee_name': assignee_name,
                'total_messages_received': total_messages,
                'cards_messaged_about': cards_messaged_about,
                'responses_given': responses_given,
                'response_rate': round(response_rate, 1)
            }


def test_message_tracker():
    """Test the message tracker functionality."""
    print("=== Message Tracker Test ===")
    
    tracker = MessageTracker("test_tracker.db")
    
    # Test logging messages
    message_id = tracker.log_message(
        card_id="card123",
        card_name="Test Card",
        assignee_name="John Doe",
        assignee_phone="+1234567890",
        message_content="Please update this card with your progress."
    )
    print(f"Logged message ID: {message_id}")
    
    # Test cooldown check
    can_send, reason = tracker.can_send_message("card123", "John Doe")
    print(f"Can send again immediately: {can_send}, Reason: {reason}")
    
    # Test status check
    status = tracker.get_card_message_status("card123", "John Doe")
    print(f"Card message status: {status}")
    
    # Test analytics
    analytics = tracker.get_daily_analytics()
    print(f"Today's analytics: {analytics}")
    
    # Test marking response
    tracker.mark_response_received("card123", "John Doe")
    print("Marked response as received")
    
    # Test status after response
    status = tracker.get_card_message_status("card123", "John Doe")
    print(f"Status after response: {status}")
    
    # Cleanup
    Path("test_tracker.db").unlink(missing_ok=True)
    print("Test completed successfully!")


if __name__ == "__main__":
    test_message_tracker()