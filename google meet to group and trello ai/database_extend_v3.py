"""
Database Schema Extensions for Team Tracker V3
Adds metrics, settings, templates, and history tables
"""

from datetime import datetime
from production_db import get_production_db

def extend_database():
    """Add new tables and columns for V3 features"""
    
    try:
        db = get_production_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        print("[V3] Extending database with V3 tables...")
        
        # 1. Card Metrics Table
        # Use SERIAL for PostgreSQL compatibility
        id_type = "SERIAL PRIMARY KEY" if db.is_postgres() else "INTEGER PRIMARY KEY AUTOINCREMENT"
        
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS card_metrics (
            id {id_type},
        card_id TEXT UNIQUE NOT NULL,
        current_list TEXT,
        list_entry_date TIMESTAMP,
        time_in_list_hours FLOAT DEFAULT 0,
        total_ignored_count INTEGER DEFAULT 0,
        last_response_date TIMESTAMP,
        last_reminder_sent TIMESTAMP,
        escalation_level INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (card_id) REFERENCES trello_cards(card_id)
    )
    ''')
    
    # 2. List History Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS list_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id TEXT NOT NULL,
        from_list TEXT,
        to_list TEXT,
        transition_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (card_id) REFERENCES trello_cards(card_id)
    )
    ''')
    
    # 3. WhatsApp Templates Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS whatsapp_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_name TEXT UNIQUE NOT NULL,
        template_type TEXT NOT NULL, -- 'reminder', 'escalation', 'welcome', 'overdue'
        template_text TEXT NOT NULL,
        variables TEXT, -- JSON array of variable names
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 4. Automation Settings Table  
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS automation_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_name TEXT UNIQUE NOT NULL,
        setting_value TEXT,
        setting_type TEXT, -- 'boolean', 'number', 'text', 'json'
        description TEXT,
        is_enabled BOOLEAN DEFAULT 1,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 5. Escalation Rules Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS escalation_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_name TEXT NOT NULL,
        hours_threshold INTEGER NOT NULL,
        action_type TEXT NOT NULL, -- 'notify_manager', 'reassign', 'alert_team'
        target_member TEXT,
        template_id INTEGER,
        is_active BOOLEAN DEFAULT 1,
        priority INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (template_id) REFERENCES whatsapp_templates(id)
    )
    ''')
    
    # 6. Response Tracking Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS response_tracking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id TEXT NOT NULL,
        team_member TEXT NOT NULL,
        reminder_sent_at TIMESTAMP,
        response_received_at TIMESTAMP,
        response_time_hours FLOAT,
        ignored BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (card_id) REFERENCES trello_cards(card_id)
    )
    ''')
    
    # Add indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_card_id ON card_metrics(card_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_list_history_card_id ON list_history(card_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_response_tracking_card_id ON response_tracking(card_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_response_tracking_member ON response_tracking(team_member)')
    
    # Insert default WhatsApp templates
    default_templates = [
        ('reminder_24h', 'reminder', 
         'Hi {name}! 👋\n\nPlease provide an update on:\n*{card_name}*\n\nThis card has been in {list_name} for {hours} hours.\n\nPlease reply with your progress update. Thanks! 🙏',
         '["name", "card_name", "list_name", "hours"]'),
        
        ('escalation_48h', 'escalation',
         '⚠️ URGENT: {name}, this card needs immediate attention:\n\n*{card_name}*\n\nNo update received for {hours} hours.\nThis will be escalated to management if not updated within 2 hours.',
         '["name", "card_name", "hours"]'),
        
        ('overdue', 'overdue',
         '🚨 OVERDUE TASK\n\n{name}, the following card is overdue:\n*{card_name}*\n\nDue date was: {due_date}\nPlease provide immediate status update.',
         '["name", "card_name", "due_date"]'),
        
        ('reassignment', 'reassignment',
         'Hi {name}! You\'ve been assigned a new card:\n\n*{card_name}*\nList: {list_name}\n\nPrevious assignee: {previous_assignee}\n\nPlease acknowledge receipt. 👍',
         '["name", "card_name", "list_name", "previous_assignee"]')
    ]
    
    for template in default_templates:
        cursor.execute('''
            INSERT OR IGNORE INTO whatsapp_templates 
            (template_name, template_type, template_text, variables)
            VALUES (?, ?, ?, ?)
        ''', template)
    
    # Insert default automation settings
    default_settings = [
        ('auto_reminder_enabled', 'true', 'boolean', 'Enable automatic 24h reminders'),
        ('reminder_hour', '9', 'number', 'Hour of day to send reminders (24h format)'),
        ('escalation_enabled', 'true', 'boolean', 'Enable automatic escalation'),
        ('escalation_hours', '48', 'number', 'Hours before escalation'),
        ('weekend_reminders', 'false', 'boolean', 'Send reminders on weekends'),
        ('max_reminders_per_card', '3', 'number', 'Maximum reminders before escalation'),
        ('ignored_threshold_hours', '24', 'number', 'Hours to consider response ignored'),
        ('manager_whatsapp', '', 'text', 'Manager WhatsApp for escalations')
    ]
    
    for setting in default_settings:
        cursor.execute('''
            INSERT OR IGNORE INTO automation_settings
            (setting_name, setting_value, setting_type, description)
            VALUES (?, ?, ?, ?)
        ''', setting)
    
    # Insert default escalation rules
    default_rules = [
        ('24h_no_response', 24, 'notify_manager', None, 1),
        ('48h_critical', 48, 'reassign', None, 2),
        ('72h_alert_all', 72, 'alert_team', None, 3)
    ]
    
    for rule_name, hours, action, target, template_id in default_rules:
        cursor.execute('''
            INSERT OR IGNORE INTO escalation_rules
            (rule_name, hours_threshold, action_type, target_member, template_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (rule_name, hours, action, target, template_id))
    
        conn.commit()
        conn.close()
        
        print("[OK] Database extended with V3 features")
        print("[INFO] New tables created:")
        print("  - card_metrics: Track card performance metrics")
        print("  - list_history: Track card movements")
        print("  - whatsapp_templates: Customizable message templates")
        print("  - automation_settings: Control automation behavior")
        print("  - escalation_rules: Define escalation triggers")
        print("  - response_tracking: Track response times")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to extend database: {e}")
        return False

if __name__ == '__main__':
    extend_database()