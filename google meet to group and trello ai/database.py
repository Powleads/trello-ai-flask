#!/usr/bin/env python3
"""
Database module for Google Meet to Trello AI application
Provides SQLite-based persistence for application data
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

class DatabaseManager:
    """Manages SQLite database operations for the application."""
    
    def __init__(self, db_path: str = "meetingai.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Transcripts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transcripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    source_type VARCHAR(50) DEFAULT 'manual',
                    source_url TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT  -- JSON string for additional data
                )
            """)
            
            # Speaker analyses table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS speaker_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transcript_id INTEGER,
                    speaker_name VARCHAR(255),
                    word_count INTEGER DEFAULT 0,
                    percentage REAL DEFAULT 0.0,
                    engagement_score REAL DEFAULT 0.0,
                    tone VARCHAR(50),
                    feedback TEXT,
                    analysis_data TEXT,  -- JSON string for full analysis
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (transcript_id) REFERENCES transcripts (id)
                )
            """)
            
            # Meeting summaries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meeting_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transcript_id INTEGER,
                    summary_text TEXT,
                    action_items TEXT,  -- JSON array
                    key_points TEXT,    -- JSON array
                    participants TEXT,  -- JSON array
                    meeting_type VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (transcript_id) REFERENCES transcripts (id)
                )
            """)
            
            # Recurring tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recurring_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_signature VARCHAR(255) UNIQUE,
                    mention_count INTEGER DEFAULT 1,
                    first_mentioned TIMESTAMP,
                    last_mentioned TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'ongoing',
                    urgency VARCHAR(50) DEFAULT 'normal',
                    task_data TEXT,  -- JSON string for full task data
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # WhatsApp messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS whatsapp_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipient_name VARCHAR(255),
                    recipient_number VARCHAR(50),
                    message_content TEXT,
                    message_type VARCHAR(50) DEFAULT 'feedback',
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'sent',
                    transcript_id INTEGER,
                    FOREIGN KEY (transcript_id) REFERENCES transcripts (id)
                )
            """)
            
            # Trello cards tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trello_updates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_id VARCHAR(100),
                    card_name VARCHAR(500),
                    board_name VARCHAR(255),
                    update_content TEXT,
                    update_type VARCHAR(50) DEFAULT 'comment',
                    transcript_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (transcript_id) REFERENCES transcripts (id)
                )
            """)
            
            # Application settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key VARCHAR(255) PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Analytics data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name VARCHAR(255),
                    metric_value REAL,
                    metric_data TEXT,  -- JSON string for additional data
                    date_recorded DATE DEFAULT (date('now')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
        finally:
            conn.close()
    
    # === TRANSCRIPT OPERATIONS ===
    
    def save_transcript(self, content: str, source_type: str = 'manual', 
                       source_url: str = None, metadata: Dict = None) -> int:
        """Save a transcript and return its ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transcripts (content, source_type, source_url, metadata)
                VALUES (?, ?, ?, ?)
            """, (content, source_type, source_url, json.dumps(metadata) if metadata else None))
            conn.commit()
            return cursor.lastrowid
    
    def get_transcript(self, transcript_id: int) -> Optional[Dict]:
        """Get a transcript by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM transcripts WHERE id = ?", (transcript_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                if result['metadata']:
                    result['metadata'] = json.loads(result['metadata'])
                return result
        return None
    
    def get_recent_transcripts(self, limit: int = 10) -> List[Dict]:
        """Get recent transcripts."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM transcripts 
                ORDER BY processed_at DESC 
                LIMIT ?
            """, (limit,))
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                if result['metadata']:
                    result['metadata'] = json.loads(result['metadata'])
                results.append(result)
            return results
    
    # === SPEAKER ANALYSIS OPERATIONS ===
    
    def save_speaker_analysis(self, transcript_id: int, analyses: List[Dict]) -> List[int]:
        """Save speaker analysis data."""
        ids = []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for analysis in analyses:
                cursor.execute("""
                    INSERT INTO speaker_analyses 
                    (transcript_id, speaker_name, word_count, percentage, 
                     engagement_score, tone, feedback, analysis_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    transcript_id,
                    analysis.get('speaker'),
                    analysis.get('word_count', 0),
                    analysis.get('percentage', 0.0),
                    analysis.get('engagement_score', 0.0),
                    analysis.get('tone', 'neutral'),
                    analysis.get('feedback', ''),
                    json.dumps(analysis)
                ))
                ids.append(cursor.lastrowid)
            conn.commit()
        return ids
    
    def get_speaker_analyses(self, transcript_id: int) -> List[Dict]:
        """Get speaker analyses for a transcript."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM speaker_analyses 
                WHERE transcript_id = ?
                ORDER BY engagement_score DESC
            """, (transcript_id,))
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                if result['analysis_data']:
                    result['analysis_data'] = json.loads(result['analysis_data'])
                results.append(result)
            return results
    
    # === MEETING SUMMARY OPERATIONS ===
    
    def save_meeting_summary(self, transcript_id: int, summary_text: str,
                           action_items: List[str], key_points: List[str],
                           participants: List[str], meeting_type: str = 'general') -> int:
        """Save meeting summary."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO meeting_summaries 
                (transcript_id, summary_text, action_items, key_points, 
                 participants, meeting_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                transcript_id, summary_text,
                json.dumps(action_items),
                json.dumps(key_points),
                json.dumps(participants),
                meeting_type
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_meeting_summary(self, transcript_id: int) -> Optional[Dict]:
        """Get meeting summary for a transcript."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM meeting_summaries 
                WHERE transcript_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (transcript_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['action_items'] = json.loads(result['action_items'])
                result['key_points'] = json.loads(result['key_points'])
                result['participants'] = json.loads(result['participants'])
                return result
        return None
    
    # === RECURRING TASKS OPERATIONS ===
    
    def save_recurring_task(self, task_signature: str, task_data: Dict) -> int:
        """Save or update a recurring task."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if task already exists
            cursor.execute("""
                SELECT id, mention_count FROM recurring_tasks 
                WHERE task_signature = ?
            """, (task_signature,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing task
                cursor.execute("""
                    UPDATE recurring_tasks 
                    SET mention_count = mention_count + 1,
                        last_mentioned = CURRENT_TIMESTAMP,
                        status = ?,
                        urgency = ?,
                        task_data = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE task_signature = ?
                """, (
                    task_data.get('status', 'ongoing'),
                    task_data.get('urgency', 'normal'),
                    json.dumps(task_data),
                    task_signature
                ))
                return existing['id']
            else:
                # Insert new task
                cursor.execute("""
                    INSERT INTO recurring_tasks 
                    (task_signature, first_mentioned, last_mentioned, 
                     status, urgency, task_data)
                    VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?, ?, ?)
                """, (
                    task_signature,
                    task_data.get('status', 'ongoing'),
                    task_data.get('urgency', 'normal'),
                    json.dumps(task_data)
                ))
                conn.commit()
                return cursor.lastrowid
    
    def get_recurring_tasks(self, status: str = None) -> List[Dict]:
        """Get recurring tasks, optionally filtered by status."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute("""
                    SELECT * FROM recurring_tasks 
                    WHERE status = ?
                    ORDER BY mention_count DESC, last_mentioned DESC
                """, (status,))
            else:
                cursor.execute("""
                    SELECT * FROM recurring_tasks 
                    ORDER BY mention_count DESC, last_mentioned DESC
                """)
            
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                if result['task_data']:
                    result['task_data'] = json.loads(result['task_data'])
                results.append(result)
            return results
    
    # === WHATSAPP MESSAGES OPERATIONS ===
    
    def save_whatsapp_message(self, recipient_name: str, recipient_number: str,
                            message_content: str, transcript_id: int = None,
                            message_type: str = 'feedback') -> int:
        """Save WhatsApp message log."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO whatsapp_messages 
                (recipient_name, recipient_number, message_content, 
                 message_type, transcript_id)
                VALUES (?, ?, ?, ?, ?)
            """, (recipient_name, recipient_number, message_content, 
                  message_type, transcript_id))
            conn.commit()
            return cursor.lastrowid
    
    def get_whatsapp_messages(self, transcript_id: int = None, limit: int = 50) -> List[Dict]:
        """Get WhatsApp message history."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if transcript_id:
                cursor.execute("""
                    SELECT * FROM whatsapp_messages 
                    WHERE transcript_id = ?
                    ORDER BY sent_at DESC
                    LIMIT ?
                """, (transcript_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM whatsapp_messages 
                    ORDER BY sent_at DESC
                    LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # === SETTINGS OPERATIONS ===
    
    def set_setting(self, key: str, value: Any):
        """Set an application setting."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO app_settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, json.dumps(value) if not isinstance(value, str) else value))
            conn.commit()
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get an application setting."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row['value'])
                except json.JSONDecodeError:
                    return row['value']
            return default
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all application settings."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM app_settings")
            settings = {}
            for row in cursor.fetchall():
                try:
                    settings[row['key']] = json.loads(row['value'])
                except json.JSONDecodeError:
                    settings[row['key']] = row['value']
            return settings
    
    # === ANALYTICS OPERATIONS ===
    
    def record_metric(self, metric_name: str, metric_value: float, 
                     metric_data: Dict = None, date_recorded: str = None):
        """Record an analytics metric."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO analytics (metric_name, metric_value, metric_data, date_recorded)
                VALUES (?, ?, ?, COALESCE(?, date('now')))
            """, (
                metric_name, metric_value,
                json.dumps(metric_data) if metric_data else None,
                date_recorded
            ))
            conn.commit()
    
    def get_metrics(self, metric_name: str = None, days: int = 30) -> List[Dict]:
        """Get analytics metrics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if metric_name:
                cursor.execute("""
                    SELECT * FROM analytics 
                    WHERE metric_name = ? 
                    AND date_recorded >= date('now', '-{} days')
                    ORDER BY date_recorded DESC, created_at DESC
                """.format(days), (metric_name,))
            else:
                cursor.execute("""
                    SELECT * FROM analytics 
                    WHERE date_recorded >= date('now', '-{} days')
                    ORDER BY date_recorded DESC, created_at DESC
                """.format(days))
            
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                if result['metric_data']:
                    result['metric_data'] = json.loads(result['metric_data'])
                results.append(result)
            return results
    
    # === UTILITY OPERATIONS ===
    
    def cleanup_old_data(self, days: int = 90):
        """Clean up old data beyond specified days."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Clean up old transcripts and related data
            cursor.execute("""
                DELETE FROM transcripts 
                WHERE processed_at < datetime('now', '-{} days')
            """.format(days))
            
            # Clean up orphaned records (SQLite doesn't enforce foreign keys by default)
            cursor.execute("""
                DELETE FROM speaker_analyses 
                WHERE transcript_id NOT IN (SELECT id FROM transcripts)
            """)
            
            cursor.execute("""
                DELETE FROM meeting_summaries 
                WHERE transcript_id NOT IN (SELECT id FROM transcripts)
            """)
            
            cursor.execute("""
                DELETE FROM whatsapp_messages 
                WHERE transcript_id NOT IN (SELECT id FROM transcripts)
            """)
            
            conn.commit()
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            tables = ['transcripts', 'speaker_analyses', 'meeting_summaries', 
                     'recurring_tasks', 'whatsapp_messages', 'trello_updates', 
                     'app_settings', 'analytics']
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                stats[table] = cursor.fetchone()['count']
            
            return stats

def test_database():
    """Test database operations."""
    print("Testing database operations...")
    
    # Initialize database
    db = DatabaseManager('test_meetingai.db')
    
    # Test transcript operations
    transcript_id = db.save_transcript(
        content="Test meeting transcript",
        source_type="test",
        metadata={"test": True}
    )
    print(f"Saved transcript with ID: {transcript_id}")
    
    # Test speaker analysis
    analyses = [
        {"speaker": "John", "word_count": 150, "percentage": 45.0, "engagement_score": 8.5},
        {"speaker": "Sarah", "word_count": 100, "percentage": 30.0, "engagement_score": 7.2},
    ]
    db.save_speaker_analysis(transcript_id, analyses)
    print("Saved speaker analyses")
    
    # Test settings
    db.set_setting("test_setting", {"auto_schedule": True})
    setting = db.get_setting("test_setting")
    print(f"Retrieved setting: {setting}")
    
    # Test metrics
    db.record_metric("test_metric", 42.5, {"source": "test"})
    print("Recorded test metric")
    
    # Get stats
    stats = db.get_database_stats()
    print(f"Database stats: {stats}")
    
    # Cleanup test database
    os.remove('test_meetingai.db')
    print("Database test completed successfully!")

if __name__ == "__main__":
    test_database()