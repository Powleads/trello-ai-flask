"""
Team Tracker V2 Database Schema and Setup
Creates isolated database for Trello card tracking with comment history
"""

import sqlite3
from datetime import datetime
import os

def create_database():
    """Create the team_tracker_v2.db with all required tables"""
    
    # Use a separate database from other apps
    db_path = 'team_tracker_v2.db'
    
    # Remove old database if exists for fresh start
    if os.path.exists(db_path):
        print(f"Backing up existing database to {db_path}.backup")
        os.rename(db_path, f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Table 1: Trello Cards with full metadata
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
        labels TEXT,  -- JSON string of labels
        closed BOOLEAN DEFAULT 0,
        url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Table 2: Card Comments with full history
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS card_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id TEXT NOT NULL,
        comment_id TEXT UNIQUE,
        commenter_name TEXT,
        commenter_id TEXT,
        comment_text TEXT,
        comment_date TIMESTAMP,
        is_update_request BOOLEAN DEFAULT 0,  -- If admin asking for update
        processed BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (card_id) REFERENCES trello_cards(card_id)
    )
    ''')
    
    # Table 3: Card Assignments with confidence scoring
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS card_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id TEXT NOT NULL,
        team_member TEXT,
        whatsapp_number TEXT,
        assignment_method TEXT,  -- 'trello_member', 'description_mention', 'comment_pattern', 'list_default', 'manual'
        confidence_score FLOAT,  -- 0.0 to 1.0
        is_active BOOLEAN DEFAULT 1,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        assigned_by TEXT,  -- 'system' or username for manual
        notes TEXT,
        FOREIGN KEY (card_id) REFERENCES trello_cards(card_id)
    )
    ''')
    
    # Table 4: Update Notifications tracking
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS update_notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id TEXT NOT NULL,
        team_member TEXT,
        whatsapp_number TEXT,
        last_comment_date TIMESTAMP,
        hours_since_last_comment FLOAT,
        notification_type TEXT,  -- 'no_update_24h', 'admin_request', 'deadline_approaching'
        notification_sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending',  -- 'pending', 'sent', 'failed', 'cancelled'
        error_message TEXT,
        response_received BOOLEAN DEFAULT 0,
        FOREIGN KEY (card_id) REFERENCES trello_cards(card_id)
    )
    ''')
    
    # Table 5: Sync History for tracking sync operations
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sync_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sync_type TEXT,  -- 'full', 'incremental', 'manual'
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        cards_synced INTEGER DEFAULT 0,
        comments_synced INTEGER DEFAULT 0,
        assignments_detected INTEGER DEFAULT 0,
        notifications_sent INTEGER DEFAULT 0,
        errors TEXT,
        status TEXT DEFAULT 'running'  -- 'running', 'completed', 'failed'
    )
    ''')
    
    # Table 6: Team Members (cached from database)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS team_members_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        whatsapp_number TEXT,
        email TEXT,
        trello_username TEXT,
        default_lists TEXT,  -- JSON array of list names this person usually works on
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create indexes for better query performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_list_name ON trello_cards(list_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_closed ON trello_cards(closed)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_comments_card_id ON card_comments(card_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_comments_date ON card_comments(comment_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_assignments_card_id ON card_assignments(card_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_assignments_active ON card_assignments(is_active)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_status ON update_notifications(status)')
    
    conn.commit()
    
    print(f"[OK] Database created successfully: {db_path}")
    print("[INFO] Tables created:")
    print("  - trello_cards: Store all card metadata")
    print("  - card_comments: Full comment history")
    print("  - card_assignments: Track who's assigned with confidence")
    print("  - update_notifications: WhatsApp notification tracking")
    print("  - sync_history: Track sync operations")
    print("  - team_members_cache: Cache team member data")
    
    return conn

def get_db_connection():
    """Get a connection to the team tracker database"""
    return sqlite3.connect('team_tracker_v2.db', 
                          detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

def test_database():
    """Test database creation and basic operations"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Test insert
    cursor.execute('''
        INSERT INTO trello_cards (card_id, name, list_name, board_id)
        VALUES (?, ?, ?, ?)
    ''', ('test_card_1', 'Test Card', 'To Do', 'test_board'))
    
    # Test select
    cursor.execute('SELECT * FROM trello_cards WHERE card_id = ?', ('test_card_1',))
    result = cursor.fetchone()
    
    if result:
        print(f"[OK] Database test successful: Found test card: {result[2]}")
    
    # Clean up test data
    cursor.execute('DELETE FROM trello_cards WHERE card_id = ?', ('test_card_1',))
    conn.commit()
    conn.close()
    
    return True

if __name__ == '__main__':
    # Create the database
    conn = create_database()
    conn.close()
    
    # Test it
    test_database()
    
    print("\n[READY] Database setup complete! Ready for Trello sync service.")