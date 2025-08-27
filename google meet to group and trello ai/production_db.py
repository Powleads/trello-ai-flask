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
        
        # Try to use PostgreSQL database first
        self.db_url = os.getenv('DATABASE_URL')
        
        # If no DATABASE_URL, use the specific PostgreSQL connection details
        if not self.db_url and POSTGRES_AVAILABLE:
            pg_host = 'dpg-d2mlsijuibrs73bihl8g-a.frankfurt-postgres.render.com'
            pg_user = 'eesystem_database_for_ai_tools_user'
            pg_pass = 'j5urZLu6RTcLnUPmUZE8AGv4sxJjyXc7'
            pg_db = 'eesystem_database_for_ai_tools'
            
            self.db_url = f"postgresql://{pg_user}:{pg_pass}@{pg_host}/{pg_db}"
            print("[DB] Using specific PostgreSQL connection details")
        
        # Test PostgreSQL connection
        print(f"[DB] POSTGRES_AVAILABLE: {POSTGRES_AVAILABLE}")
        print(f"[DB] DATABASE_URL from env: {os.getenv('DATABASE_URL', 'NOT SET')}")
        print(f"[DB] Constructed db_url: {self.db_url}")
        
        if self.db_url and POSTGRES_AVAILABLE:
            try:
                # Fix postgres:// to postgresql://
                if self.db_url.startswith('postgres://'):
                    self.db_url = self.db_url.replace('postgres://', 'postgresql://', 1)
                
                print(f"[DB] Attempting PostgreSQL connection to: {self.db_url}")
                # Test connection
                conn = psycopg2.connect(self.db_url)
                conn.close()
                self.is_production = True
                print("[DB] ✅ PostgreSQL connection successful - using PostgreSQL database")
            except Exception as e:
                print(f"[DB] PostgreSQL connection failed: {e}")
                print("[DB] Falling back to SQLite")
                self.is_production = False
                self.db_url = None
        else:
            self.is_production = False
            if not POSTGRES_AVAILABLE:
                print("[DB] psycopg2 not available, using SQLite")
            elif not self.db_url:
                print("[DB] No database URL configured, using SQLite")
            else:
                print("[DB] Unknown issue, using SQLite")
        
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
    
    def init_settings_table(self):
        """Initialize settings table for persistent configuration"""
        try:
            if self.is_production:
                # PostgreSQL
                cursor = self.conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS app_settings (
                        id SERIAL PRIMARY KEY,
                        setting_key TEXT UNIQUE NOT NULL,
                        setting_value TEXT NOT NULL,
                        setting_type TEXT DEFAULT 'string',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                ''')
                self.conn.commit()
            else:
                # SQLite
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS app_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        setting_key TEXT UNIQUE NOT NULL,
                        setting_value TEXT NOT NULL,
                        setting_type TEXT DEFAULT 'string',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
                conn.close()
            
            print("[DB] Settings table initialized")
            return True
        except Exception as e:
            print(f"[DB] Error initializing settings table: {e}")
            return False

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
        
        # Team members table (updated schema to match SQLite)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_members (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                whatsapp TEXT NOT NULL,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Migration: Check if we need to migrate from old schema (phone -> whatsapp)
        try:
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'team_members'")
            columns = [row[0] for row in cursor.fetchall()]
            
            if 'phone' in columns and 'whatsapp' not in columns:
                print("[DB] PostgreSQL: Migrating team_members schema (phone -> whatsapp)")
                cursor.execute("ALTER TABLE team_members RENAME COLUMN phone TO whatsapp")
                print("[DB] PostgreSQL: Schema migration completed")
            elif 'whatsapp' not in columns:
                print("[DB] PostgreSQL: Adding whatsapp column")
                cursor.execute("ALTER TABLE team_members ADD COLUMN whatsapp TEXT")
        except Exception as e:
            print(f"[DB] PostgreSQL migration warning: {e}")
            # Continue anyway - table will be created fresh if needed
        
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
        """Get team members from database with retry logic"""
        import time
        max_retries = 3
        
        for retry in range(max_retries):
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Simple query - table should be properly initialized by now
                if self.is_production:
                    cursor.execute("SELECT name, whatsapp FROM team_members WHERE active = true")
                else:
                    cursor.execute("SELECT name, whatsapp FROM team_members WHERE active = 1")
                
                rows = cursor.fetchall()
                conn.close()
                
                members = {row[0]: row[1] for row in rows if row[1]}  # Only include if whatsapp exists
                print(f"[DB] Loaded {len(members)} team members from database")
                return members
                
            except Exception as e:
                if "database is locked" in str(e).lower() and retry < max_retries - 1:
                    print(f"[DB] Database locked while getting members, retrying ({retry + 1}/{max_retries})...")
                    time.sleep(0.5 * (retry + 1))
                    continue
                elif "no such table" in str(e).lower():
                    print("[DB] Team members table doesn't exist, initializing...")
                    self.init_team_members_table()
                    continue
                print(f"[DB] Error getting team members: {e}")
                if conn:
                    conn.close()
                return {}
        
        return {}
    
    def update_team_member(self, name: str, whatsapp: str, active: bool = True) -> bool:
        """Update or insert team member with retry logic"""
        import time
        max_retries = 3
        
        for retry in range(max_retries):
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Always use simple INSERT OR REPLACE for SQLite
                if not self.is_production:
                    cursor.execute("""
                        INSERT OR REPLACE INTO team_members (name, whatsapp, active, created_at, updated_at)
                        VALUES (?, ?, ?, datetime('now'), datetime('now'))
                    """, (name, whatsapp, int(active)))
                else:
                    cursor.execute("""
                        INSERT INTO team_members (name, whatsapp, active, created_at, updated_at) 
                        VALUES (%s, %s, %s, NOW(), NOW())
                        ON CONFLICT (name) DO UPDATE SET 
                        whatsapp = EXCLUDED.whatsapp, 
                        active = EXCLUDED.active,
                        updated_at = NOW()
                    """, (name, whatsapp, active))
                
                conn.commit()
                conn.close()
                print(f"[DB] Updated team member: {name}")
                return True
                
            except Exception as e:
                if "database is locked" in str(e).lower() and retry < max_retries - 1:
                    print(f"[DB] Database locked, retrying ({retry + 1}/{max_retries})...")
                    time.sleep(0.5 * (retry + 1))
                    continue
                print(f"[DB] Error updating team member {name}: {e}")
                if conn:
                    conn.close()
                return False
        
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
        """Initialize team members table with retry logic and schema fixes"""
        import time
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Check if table exists and what columns it has
                cursor.execute("PRAGMA table_info(team_members)")
                existing_columns = {col[1]: col for col in cursor.fetchall()}
                
                if existing_columns:
                    # Table exists - check for schema issues
                    print(f"[DB] Existing team_members columns: {list(existing_columns.keys())}")
                    
                    # Handle phone vs whatsapp column issue
                    if 'phone' in existing_columns and 'whatsapp' not in existing_columns:
                        print("[DB] Fixing schema: renaming 'phone' to 'whatsapp'")
                        # Drop and recreate with correct schema
                        cursor.execute("DROP TABLE IF EXISTS team_members_old")
                        cursor.execute("ALTER TABLE team_members RENAME TO team_members_old")
                        cursor.execute("""
                            CREATE TABLE team_members (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT UNIQUE NOT NULL,
                                whatsapp TEXT NOT NULL,
                                active INTEGER DEFAULT 1,
                                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                            )
                        """)
                        # Copy data, using phone as whatsapp
                        cursor.execute("""
                            INSERT INTO team_members (name, whatsapp, active)
                            SELECT name, phone, COALESCE(active, 1) 
                            FROM team_members_old
                        """)
                        cursor.execute("DROP TABLE team_members_old")
                        print("[DB] Schema fixed: phone renamed to whatsapp")
                    
                    # Add missing columns if needed
                    elif 'whatsapp' not in existing_columns:
                        print("[DB] Adding missing whatsapp column")
                        cursor.execute("ALTER TABLE team_members ADD COLUMN whatsapp TEXT DEFAULT ''")
                    
                    # Ensure all required columns exist
                    for col in ['active', 'created_at', 'updated_at']:
                        if col not in existing_columns:
                            print(f"[DB] Adding missing {col} column")
                            if col == 'active':
                                cursor.execute("ALTER TABLE team_members ADD COLUMN active INTEGER DEFAULT 1")
                            else:
                                cursor.execute(f"ALTER TABLE team_members ADD COLUMN {col} TEXT DEFAULT CURRENT_TIMESTAMP")
                    
                else:
                    # Table doesn't exist - create it fresh
                    print("[DB] Creating new team_members table")
                    if self.is_production:
                        cursor.execute("""
                            CREATE TABLE team_members (
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
                            CREATE TABLE team_members (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT UNIQUE NOT NULL,
                                whatsapp TEXT NOT NULL,
                                active INTEGER DEFAULT 1,
                                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                            )
                        """)
                
                conn.commit()
                conn.close()
                print("[DB] Team members table initialized successfully")
                return True
                
            except Exception as e:
                if "database is locked" in str(e).lower():
                    retry_count += 1
                    if retry_count < max_retries:
                        print(f"[DB] Database locked, retrying ({retry_count}/{max_retries})...")
                        time.sleep(0.5 * retry_count)  # Exponential backoff
                        continue
                print(f"[DB] Error initializing team members table: {e}")
                if conn:
                    conn.close()
                return False
        
        print("[DB] Failed to initialize team members table after retries")
        return False
    
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
                SELECT 
                    card_id,
                    card_name,
                    '' as list_name,
                    assignee_name,
                    assignee_phone,
                    last_assignee_comment_date,
                    0 as hours_since_assigned_update,
                    CASE WHEN message_count > 0 THEN 1 ELSE 0 END as needs_update,
                    last_message_sent,
                    message_count,
                    next_message_due,
                    0 as response_detected,
                    updated_at
                FROM team_tracker_cards
                ORDER BY updated_at DESC
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
    
    def save_setting(self, key: str, value: str, setting_type: str = 'string'):
        """Save a setting to the database"""
        try:
            if self.is_production:
                cursor = self.conn.cursor()
                cursor.execute('''
                    INSERT INTO app_settings (setting_key, setting_value, setting_type)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (setting_key) 
                    DO UPDATE SET setting_value = EXCLUDED.setting_value,
                                  setting_type = EXCLUDED.setting_type,
                                  updated_at = NOW()
                ''', (key, value, setting_type))
                self.conn.commit()
            else:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO app_settings (setting_key, setting_value, setting_type)
                    VALUES (?, ?, ?)
                ''', (key, value, setting_type))
                conn.commit()
                conn.close()
            
            return True
        except Exception as e:
            print(f"[DB] Error saving setting {key}: {e}")
            return False

    def get_setting(self, key: str, default=None):
        """Get a setting from the database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if self.is_production:
                cursor.execute('SELECT setting_value, setting_type FROM app_settings WHERE setting_key = %s', (key,))
            else:
                cursor.execute('SELECT setting_value, setting_type FROM app_settings WHERE setting_key = ?', (key,))
            
            result = cursor.fetchone()
            
            if not self.is_production:
                conn.close()
            
            if result:
                value, setting_type = result
                # Convert based on type
                if setting_type == 'json':
                    import json
                    return json.loads(value)
                elif setting_type == 'int':
                    return int(value)
                elif setting_type == 'float':
                    return float(value)
                elif setting_type == 'bool':
                    return value.lower() == 'true'
                else:
                    return value
            
            return default
        except Exception as e:
            print(f"[DB] Error getting setting {key}: {e}")
            return default

    def get_all_settings(self):
        """Get all settings from the database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT setting_key, setting_value, setting_type FROM app_settings')
            results = cursor.fetchall()
            
            if not self.is_production:
                conn.close()
            
            settings = {}
            for key, value, setting_type in results:
                if setting_type == 'json':
                    import json
                    settings[key] = json.loads(value)
                elif setting_type == 'int':
                    settings[key] = int(value)
                elif setting_type == 'float':
                    settings[key] = float(value) 
                elif setting_type == 'bool':
                    settings[key] = value.lower() == 'true'
                else:
                    settings[key] = value
            
            return settings
        except Exception as e:
            print(f"[DB] Error getting all settings: {e}")
            return {}

    def seed_team_members(self):
        """Seed initial team members (current active team) with proper error handling"""
        try:
            # First ensure table is properly initialized
            if not hasattr(self, '_table_initialized'):
                self.init_team_members_table()
                self._table_initialized = True
            
            initial_members = {
                'Lancey': '639264438378@c.us',
                'Levy': '237659250977@c.us', 
                'Wendy': '237677079267@c.us',
                'Forka': '237652275097@c.us',
                'Brayan': '237676267420@c.us',
                'Breyden': '13179979692@c.us'
            }
            
            success_count = 0
            for name, whatsapp in initial_members.items():
                if self.update_team_member(name, whatsapp, True):
                    success_count += 1
                else:
                    print(f"[DB] Failed to seed member: {name}")
            
            print(f"[DB] Successfully seeded {success_count}/{len(initial_members)} team members")
            return success_count > 0
        except Exception as e:
            print(f"[DB] Error seeding team members: {e}")
            return False

# Global instance
production_db = None

def get_production_db() -> ProductionDatabaseManager:
    """Get global production database instance"""
    global production_db
    if production_db is None:
        production_db = ProductionDatabaseManager()
    return production_db