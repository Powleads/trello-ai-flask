#!/usr/bin/env python3
"""
Initialize Team Tracker Database
Run this on deployment to ensure database exists
"""

import os
import sqlite3
from datetime import datetime

def init_database():
    """Initialize the team_tracker_v2.db if it doesn't exist"""
    
    db_path = 'team_tracker_v2.db'
    
    # Check if database exists
    if os.path.exists(db_path):
        print(f"Database already exists: {db_path}")
        return True
    
    print(f"Creating new database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create all tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trello_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        list_id TEXT,
        list_name TEXT,
        board_id TEXT,
        board_name TEXT,
        due_date TIMESTAMP,
        labels TEXT,
        closed BOOLEAN DEFAULT 0,
        url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS card_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id TEXT NOT NULL,
        comment_id TEXT UNIQUE,
        commenter_name TEXT,
        commenter_id TEXT,
        comment_text TEXT,
        comment_date TIMESTAMP,
        is_update_request BOOLEAN DEFAULT 0,
        processed BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (card_id) REFERENCES trello_cards(card_id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS card_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id TEXT NOT NULL,
        team_member TEXT,
        whatsapp_number TEXT,
        assignment_method TEXT,
        confidence_score FLOAT,
        is_active BOOLEAN DEFAULT 1,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        assigned_by TEXT,
        notes TEXT,
        FOREIGN KEY (card_id) REFERENCES trello_cards(card_id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS update_notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id TEXT NOT NULL,
        team_member TEXT,
        whatsapp_number TEXT,
        last_comment_date TIMESTAMP,
        hours_since_last_comment FLOAT,
        notification_type TEXT,
        notification_sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending',
        error_message TEXT,
        response_received BOOLEAN DEFAULT 0,
        FOREIGN KEY (card_id) REFERENCES trello_cards(card_id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sync_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sync_type TEXT,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        cards_synced INTEGER DEFAULT 0,
        comments_synced INTEGER DEFAULT 0,
        assignments_detected INTEGER DEFAULT 0,
        notifications_sent INTEGER DEFAULT 0,
        errors TEXT,
        status TEXT DEFAULT 'running'
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS team_members_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        whatsapp_number TEXT,
        email TEXT,
        trello_username TEXT,
        default_lists TEXT,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_list_name ON trello_cards(list_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_closed ON trello_cards(closed)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_comments_card_id ON card_comments(card_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_assignments_card_id ON card_assignments(card_id)')
    
    # Add initial sync record
    cursor.execute('''
        INSERT INTO sync_history (sync_type, completed_at, status)
        VALUES (?, ?, ?)
    ''', ('initial', datetime.now(), 'completed'))
    
    conn.commit()
    conn.close()
    
    print("Database created successfully!")
    return True

if __name__ == '__main__':
    init_database()
    
    # Test the database
    conn = sqlite3.connect('team_tracker_v2.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print("\nTables created:")
    for table in tables:
        print(f"  - {table[0]}")
    
    conn.close()