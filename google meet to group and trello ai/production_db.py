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
            raise ImportError("PostgreSQL required for production but psycopg2 not installed")
        
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

# Global instance
production_db = None

def get_production_db() -> ProductionDatabaseManager:
    """Get global production database instance"""
    global production_db
    if production_db is None:
        production_db = ProductionDatabaseManager()
    return production_db