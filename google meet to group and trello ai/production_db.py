"""
Production Database Manager - Handles PostgreSQL for Render deployment
Provides compatibility layer for both SQLite (local) and PostgreSQL (production)
"""

import os
import json
import sqlite3
from urllib.parse import urlparse
from typing import Optional, List, Dict, Any

try:
    import psycopg2
    import psycopg2.extras
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    print("[DB] PostgreSQL not available - using SQLite fallback")

class ProductionDatabaseManager:
    """Database manager that works with both SQLite (local) and PostgreSQL (production)"""
    
    def __init__(self, db_path='gmail_tracker.db'):
        self.db_path = db_path
        self.is_production = self._is_production_environment()
        self.db_url = os.getenv('DATABASE_URL')
        
        if self.is_production and not POSTGRES_AVAILABLE:
            print("[DB] WARNING: PostgreSQL not available, falling back to SQLite")
            self.is_production = False  # Force SQLite fallback
        
        self.init_database()
    
    def _is_production_environment(self) -> bool:
        """Check if running in production environment"""
        return bool(os.getenv('DATABASE_URL') or os.getenv('RENDER'))
    
    def get_connection(self):
        """Get database connection - PostgreSQL for production, SQLite for local"""
        if self.is_production and self.db_url:
            # Production: PostgreSQL
            return psycopg2.connect(self.db_url)
        else:
            # Local: SQLite
            return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize database tables for both PostgreSQL and SQLite"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if self.is_production:
            # PostgreSQL schemas
            self._create_postgres_tables(cursor)
        else:
            # SQLite schemas  
            self._create_sqlite_tables(cursor)
        
        conn.commit()
        conn.close()
        print(f"[DB] Database initialized ({'PostgreSQL' if self.is_production else 'SQLite'})")
    
    def _create_postgres_tables(self, cursor):
        """Create PostgreSQL tables"""
        # Email history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_history (
                id SERIAL PRIMARY KEY,
                email_id TEXT UNIQUE,
                subject TEXT,
                sender TEXT,
                recipient TEXT,
                category TEXT,
                assigned_to TEXT,
                whatsapp_sent BOOLEAN DEFAULT FALSE,
                processed_at TEXT,
                email_content TEXT,
                priority INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Gmail tokens table (for persistent token storage)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gmail_tokens (
                id SERIAL PRIMARY KEY,
                token_type VARCHAR(50) DEFAULT 'gmail_oauth' UNIQUE,
                token_data JSONB,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Watch rules table (replaces JSON file)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watch_rules (
                id SERIAL PRIMARY KEY,
                rule_name VARCHAR(100) DEFAULT 'default' UNIQUE,
                rule_data JSONB,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Team members table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_members (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                categories JSONB,
                role TEXT,
                active BOOLEAN DEFAULT TRUE,
                notification_settings JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Team tracker card status
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_tracker_cards (
                id SERIAL PRIMARY KEY,
                card_id TEXT UNIQUE NOT NULL,
                card_name TEXT NOT NULL,
                assignee_name TEXT NOT NULL,
                assignee_phone TEXT,
                last_assignee_comment_date TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                last_message_sent TIMESTAMP,
                escalation_level INTEGER DEFAULT 0,
                next_message_due TIMESTAMP,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Team tracker messages with response tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_tracker_messages (
                id SERIAL PRIMARY KEY,
                card_id TEXT NOT NULL,
                assignee_name TEXT NOT NULL,
                message_content TEXT,
                sent_at TIMESTAMP DEFAULT NOW(),
                response_detected_at TIMESTAMP,
                escalation_level INTEGER DEFAULT 1,
                next_followup_due TIMESTAMP,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
    
    def _create_sqlite_tables(self, cursor):
        """Create SQLite tables (existing logic)"""
        # Email history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id TEXT UNIQUE,
                subject TEXT,
                sender TEXT,
                recipient TEXT,
                category TEXT,
                assigned_to TEXT,
                whatsapp_sent BOOLEAN DEFAULT FALSE,
                processed_at TEXT,
                email_content TEXT,
                priority INTEGER DEFAULT 1
            )
        ''')
        
        # Gmail tokens table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gmail_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_type TEXT DEFAULT 'gmail_oauth',
                token_data TEXT,
                expires_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Watch rules table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watch_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_data TEXT,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Team members table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                categories TEXT,
                role TEXT,
                active BOOLEAN DEFAULT TRUE,
                notification_settings TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Team tracker card status
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_tracker_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id TEXT UNIQUE NOT NULL,
                card_name TEXT NOT NULL,
                assignee_name TEXT NOT NULL,
                assignee_phone TEXT,
                last_assignee_comment_date TEXT,
                message_count INTEGER DEFAULT 0,
                last_message_sent TEXT,
                escalation_level INTEGER DEFAULT 0,
                next_message_due TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Team tracker messages with response tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_tracker_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id TEXT NOT NULL,
                assignee_name TEXT NOT NULL,
                message_content TEXT,
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                response_detected_at TEXT,
                escalation_level INTEGER DEFAULT 1,
                next_followup_due TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def store_gmail_token(self, token_data: Dict) -> bool:
        """Store Gmail OAuth token in database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            token_json = json.dumps(token_data)
            
            if self.is_production:
                # PostgreSQL
                cursor.execute('''
                    INSERT INTO gmail_tokens (token_type, token_data, updated_at) 
                    VALUES (%s, %s, NOW()) 
                    ON CONFLICT (token_type) DO UPDATE SET 
                    token_data = EXCLUDED.token_data, updated_at = NOW()
                ''', ('gmail_oauth', token_json))
            else:
                # SQLite
                cursor.execute('''
                    INSERT OR REPLACE INTO gmail_tokens (id, token_data, updated_at) 
                    VALUES (1, ?, datetime('now'))
                ''', (token_json,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[DB] Error storing Gmail token: {e}")
            return False
    
    def get_gmail_token(self) -> Optional[Dict]:
        """Retrieve Gmail OAuth token from database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT token_data FROM gmail_tokens ORDER BY updated_at DESC LIMIT 1')
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return json.loads(result[0])
            return None
        except Exception as e:
            print(f"[DB] Error retrieving Gmail token: {e}")
            return None
    
    def store_watch_rules(self, rules_data: Dict) -> bool:
        """Store watch rules in database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            rules_json = json.dumps(rules_data)
            
            if self.is_production:
                # PostgreSQL
                cursor.execute('''
                    INSERT INTO watch_rules (rule_name, rule_data, updated_at) 
                    VALUES (%s, %s, NOW()) 
                    ON CONFLICT (rule_name) DO UPDATE SET 
                    rule_data = EXCLUDED.rule_data, updated_at = NOW()
                ''', ('default', rules_json))
            else:
                # SQLite  
                cursor.execute('''
                    INSERT OR REPLACE INTO watch_rules (id, rule_data, updated_at) 
                    VALUES (1, ?, datetime('now'))
                ''', (rules_json,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[DB] Error storing watch rules: {e}")
            return False
    
    def get_watch_rules(self) -> Dict:
        """Retrieve watch rules from database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT rule_data FROM watch_rules WHERE active = TRUE ORDER BY updated_at DESC LIMIT 1')
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return json.loads(result[0])
            return {}
        except Exception as e:
            print(f"[DB] Error retrieving watch rules: {e}")
            return {}
    
    def store_email_history(self, email_id: str, subject: str, sender: str, recipient: str, 
                           category: str, assigned_to: str, content: str, priority: int, processed_at: str) -> bool:
        """Store email history record"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.is_production:
                # PostgreSQL
                cursor.execute('''
                    INSERT INTO email_history 
                    (email_id, subject, sender, recipient, category, assigned_to, email_content, priority, processed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (email_id) DO UPDATE SET
                    assigned_to = EXCLUDED.assigned_to, processed_at = EXCLUDED.processed_at
                ''', (email_id, subject, sender, recipient, category, assigned_to, content, priority, processed_at))
            else:
                # SQLite
                cursor.execute('''
                    INSERT OR REPLACE INTO email_history 
                    (email_id, subject, sender, recipient, category, assigned_to, email_content, priority, processed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (email_id, subject, sender, recipient, category, assigned_to, content, priority, processed_at))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[DB] Error storing email history: {e}")
            return False
    
    def get_email_history(self, limit: int = 50) -> List[Dict]:
        """Get email history records"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT email_id, subject, sender, category, assigned_to, 
                       whatsapp_sent, processed_at, priority
                FROM email_history 
                ORDER BY id DESC 
                LIMIT %s
            ''' if self.is_production else '''
                SELECT email_id, subject, sender, category, assigned_to, 
                       whatsapp_sent, processed_at, priority
                FROM email_history 
                ORDER BY id DESC 
                LIMIT ?
            ''', (limit,))
            
            results = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'email_id': row[0],
                    'subject': row[1],
                    'sender': row[2],
                    'category': row[3],
                    'assigned_to': row[4],
                    'whatsapp_sent': bool(row[5]),
                    'processed_at': row[6] or 'Unknown',
                    'priority': row[7]
                }
                for row in results
            ]
        except Exception as e:
            print(f"[DB] Error getting email history: {e}")
            return []
    
    def update_team_tracker_card(self, card_id: str, card_name: str, assignee_name: str, 
                                 assignee_phone: str, last_comment_date: str = None) -> bool:
        """Update or create team tracker card record"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.is_production:
                # PostgreSQL
                cursor.execute('''
                    INSERT INTO team_tracker_cards 
                    (card_id, card_name, assignee_name, assignee_phone, last_assignee_comment_date, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (card_id) DO UPDATE SET
                    card_name = EXCLUDED.card_name,
                    assignee_name = EXCLUDED.assignee_name,
                    assignee_phone = EXCLUDED.assignee_phone,
                    last_assignee_comment_date = COALESCE(EXCLUDED.last_assignee_comment_date, team_tracker_cards.last_assignee_comment_date),
                    updated_at = NOW()
                ''', (card_id, card_name, assignee_name, assignee_phone, last_comment_date))
            else:
                # SQLite
                cursor.execute('''
                    INSERT OR REPLACE INTO team_tracker_cards 
                    (card_id, card_name, assignee_name, assignee_phone, last_assignee_comment_date, updated_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                ''', (card_id, card_name, assignee_name, assignee_phone, last_comment_date))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[DB] Error updating team tracker card: {e}")
            return False
    
    def get_team_tracker_card(self, card_id: str) -> Optional[Dict]:
        """Get team tracker card status"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT card_id, card_name, assignee_name, assignee_phone, 
                       last_assignee_comment_date, message_count, last_message_sent,
                       escalation_level, next_message_due, status
                FROM team_tracker_cards 
                WHERE card_id = %s
            ''' if self.is_production else '''
                SELECT card_id, card_name, assignee_name, assignee_phone, 
                       last_assignee_comment_date, message_count, last_message_sent,
                       escalation_level, next_message_due, status
                FROM team_tracker_cards 
                WHERE card_id = ?
            ''', (card_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'card_id': result[0],
                    'card_name': result[1],
                    'assignee_name': result[2],
                    'assignee_phone': result[3],
                    'last_assignee_comment_date': result[4],
                    'message_count': result[5],
                    'last_message_sent': result[6],
                    'escalation_level': result[7],
                    'next_message_due': result[8],
                    'status': result[9]
                }
            return None
        except Exception as e:
            print(f"[DB] Error getting team tracker card: {e}")
            return None
    
    def log_team_tracker_message(self, card_id: str, assignee_name: str, message_content: str,
                                 escalation_level: int = 1, next_followup_hours: int = 24) -> bool:
        """Log a team tracker message and update card status"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Calculate next followup time
            if self.is_production:
                next_followup_sql = "NOW() + INTERVAL '%s hours'"
                now_sql = "NOW()"
                params = (card_id, assignee_name, message_content, escalation_level, next_followup_hours)
            else:
                next_followup_sql = "datetime('now', '+%s hours')"
                now_sql = "datetime('now')"
                params = (card_id, assignee_name, message_content, escalation_level, next_followup_hours)
            
            # Log the message
            cursor.execute(f'''
                INSERT INTO team_tracker_messages 
                (card_id, assignee_name, message_content, escalation_level, next_followup_due)
                VALUES ({'%s, %s, %s, %s, ' + next_followup_sql if self.is_production else '?, ?, ?, ?, ' + next_followup_sql})
            ''', params)
            
            # Update card message count and status
            if self.is_production:
                cursor.execute('''
                    UPDATE team_tracker_cards 
                    SET message_count = message_count + 1,
                        escalation_level = %s,
                        last_message_sent = NOW(),
                        next_message_due = NOW() + INTERVAL '%s hours',
                        updated_at = NOW()
                    WHERE card_id = %s
                ''', (escalation_level, next_followup_hours, card_id))
            else:
                cursor.execute('''
                    UPDATE team_tracker_cards 
                    SET message_count = message_count + 1,
                        escalation_level = ?,
                        last_message_sent = datetime('now'),
                        next_message_due = datetime('now', '+' || ? || ' hours'),
                        updated_at = datetime('now')
                    WHERE card_id = ?
                ''', (escalation_level, next_followup_hours, card_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[DB] Error logging team tracker message: {e}")
            return False
    
    def mark_team_tracker_response(self, card_id: str) -> bool:
        """Mark that assignee has responded to a card"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Reset escalation and message count
            if self.is_production:
                cursor.execute('''
                    UPDATE team_tracker_cards 
                    SET escalation_level = 0,
                        message_count = 0,
                        last_assignee_comment_date = NOW(),
                        next_message_due = NULL,
                        status = 'responded',
                        updated_at = NOW()
                    WHERE card_id = %s
                ''', (card_id,))
                
                cursor.execute('''
                    UPDATE team_tracker_messages 
                    SET response_detected_at = NOW(),
                        status = 'responded'
                    WHERE card_id = %s AND status = 'pending'
                ''', (card_id,))
            else:
                cursor.execute('''
                    UPDATE team_tracker_cards 
                    SET escalation_level = 0,
                        message_count = 0,
                        last_assignee_comment_date = datetime('now'),
                        next_message_due = NULL,
                        status = 'responded',
                        updated_at = datetime('now')
                    WHERE card_id = ?
                ''', (card_id,))
                
                cursor.execute('''
                    UPDATE team_tracker_messages 
                    SET response_detected_at = datetime('now'),
                        status = 'responded'
                    WHERE card_id = ? AND status = 'pending'
                ''', (card_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[DB] Error marking team tracker response: {e}")
            return False
    
    def get_team_members(self) -> Dict[str, str]:
        """Get team members from database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.is_production:
                cursor.execute("SELECT name, whatsapp FROM team_members WHERE active = true")
            else:
                cursor.execute("SELECT name, whatsapp FROM team_members WHERE active = 1")
            
            rows = cursor.fetchall()
            conn.close()
            
            return {row[0]: row[1] for row in rows}
        except Exception as e:
            print(f"[DB] Error getting team members: {e}")
            return {}
    
    def update_team_member(self, name: str, whatsapp: str, active: bool = True) -> bool:
        """Update or insert team member"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.is_production:
                cursor.execute("""
                    INSERT INTO team_members (name, whatsapp, active, created_at, updated_at) 
                    VALUES (%s, %s, %s, NOW(), NOW())
                    ON CONFLICT (name) DO UPDATE SET 
                    whatsapp = EXCLUDED.whatsapp, 
                    active = EXCLUDED.active,
                    updated_at = NOW()
                """, (name, whatsapp, active))
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO team_members (name, whatsapp, active, created_at, updated_at)
                    VALUES (?, ?, ?, datetime('now'), datetime('now'))
                """, (name, whatsapp, int(active)))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[DB] Error updating team member: {e}")
            return False
    
    def delete_team_member(self, name: str) -> bool:
        """Mark team member as inactive"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.is_production:
                cursor.execute("UPDATE team_members SET active = false WHERE name = %s", (name,))
            else:
                cursor.execute("UPDATE team_members SET active = 0 WHERE name = ?", (name,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[DB] Error deleting team member: {e}")
            return False
    
    def init_team_members_table(self):
        """Initialize team members table"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.is_production:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS team_members (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) UNIQUE NOT NULL,
                        whatsapp VARCHAR(50) NOT NULL,
                        active BOOLEAN DEFAULT true,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                """)
            else:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS team_members (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        whatsapp TEXT NOT NULL,
                        active INTEGER DEFAULT 1,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            
            # Check if whatsapp column exists, if not add it (migration)
            cursor.execute("PRAGMA table_info(team_members)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'whatsapp' not in columns:
                print("[DB] Migrating team_members table - adding whatsapp column")
                cursor.execute("ALTER TABLE team_members ADD COLUMN whatsapp TEXT")
                cursor.execute("UPDATE team_members SET whatsapp = '' WHERE whatsapp IS NULL")
            
            conn.commit()
            conn.close()
            print("[DB] Team members table initialized")
        except Exception as e:
            print(f"[DB] Error initializing team members table: {e}")
    
    def clear_all_cards(self):
        """Clear ONLY team tracker cards - preserves Gmail data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # ONLY clear team tracker tables - NEVER touch Gmail tables
            cursor.execute("DELETE FROM team_tracker_cards")
            cursor.execute("DELETE FROM team_tracker_messages")
            
            # Explicitly preserve Gmail tables:
            # - email_watches (Gmail watches)
            # - email_history (Gmail tracker data)
            # - team_member_rules (Gmail rules)
            # - gmail_tracker (if exists)
            # - gmail_rules (if exists)
            # - gmail_whatsapp_sends (if exists)
            
            conn.commit()
            conn.close()
            print("[DB] Cleared ONLY team tracker cards/messages - Gmail data preserved")
            return True
        except Exception as e:
            print(f"[DB] Error clearing cards: {e}")
            return False
    
    def delete_card(self, card_id: str) -> bool:
        """Delete a specific card from tracking"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM team_tracker_cards WHERE card_id = ?", (card_id,))
            cursor.execute("DELETE FROM team_tracker_messages WHERE card_id = ?", (card_id,))
            conn.commit()
            rows_deleted = cursor.rowcount
            conn.close()
            print(f"[DB] Deleted card {card_id} ({rows_deleted} rows)")
            return rows_deleted > 0
        except Exception as e:
            print(f"[DB] Error deleting card: {e}")
            return False
    
    def get_all_cards(self) -> List[Dict]:
        """Get all tracked cards from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM team_tracker_cards
                ORDER BY last_updated DESC
            """)
            
            cards = []
            for row in cursor.fetchall():
                cards.append({
                    'card_id': row[0],
                    'card_name': row[1],
                    'list_name': row[2],
                    'assigned_user': row[3],
                    'assigned_whatsapp': row[4],
                    'last_comment_date': row[5],
                    'hours_since_assigned_update': row[6],
                    'needs_update': bool(row[7]),
                    'last_message_sent': row[8],
                    'message_count': row[9],
                    'next_message_due': row[10],
                    'response_detected': bool(row[11]),
                    'last_updated': row[12]
                })
            
            conn.close()
            return cards
        except Exception as e:
            print(f"[DB] Error getting all cards: {e}")
            return []
    
    def clear_team_members(self):
        """Clear all team members from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM team_members")
            conn.commit()
            conn.close()
            print("[DB] Cleared all team members")
            return True
        except Exception as e:
            print(f"[DB] Error clearing team members: {e}")
            return False
    
    def seed_team_members(self):
        """Seed initial team members (current active team)"""
        try:
            initial_members = {
                'Lancey': '639264438378@c.us',
                'Levy': '237659250977@c.us', 
                'Wendy': '237677079267@c.us',
                'Forka': '237652275097@c.us',
                'Brayan': '237676267420@c.us',
                'Breyden': '13179979692@c.us'
            }
            
            for name, whatsapp in initial_members.items():
                self.update_team_member(name, whatsapp, True)
            
            print(f"[DB] Seeded {len(initial_members)} team members")
        except Exception as e:
            print(f"[DB] Error seeding team members: {e}")

# Global instance
production_db = None

def get_production_db() -> ProductionDatabaseManager:
    """Get global production database instance"""
    global production_db
    if production_db is None:
        production_db = ProductionDatabaseManager()
    return production_db