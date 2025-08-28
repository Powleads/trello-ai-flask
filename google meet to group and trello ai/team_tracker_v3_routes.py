"""
Team Tracker V3 - Enhanced Routes with Modal Support

🗄️ DATA PERSISTENCE ARCHITECTURE:
- All data stored in PostgreSQL database (not browser cache)
- Browser clearing/refreshing does NOT affect data
- Team members, cards, assignments, templates all persist
- Automatic table initialization on startup
- Database migrations handle schema updates

📊 PERSISTENT TABLES:
- trello_cards: Card data and metadata
- card_comments: Comments and system messages  
- card_assignments: Assignment history and tracking
- card_metrics: Performance metrics and escalation
- team_members_cache: Team member info and WhatsApp
- whatsapp_templates: Message templates
- automation_settings: System preferences

✅ BROWSER-INDEPENDENT: All settings and data survive:
- Browser refresh/reload
- Cache clearing
- Application restart
- Server redeployment
"""

from flask import Blueprint, render_template, jsonify, request
from datetime import datetime, timedelta
import json
import re
import os
from production_db import get_production_db
from green_api_integration import GreenAPIClient

team_tracker_v3_bp = Blueprint('team_tracker_v3', __name__)

def get_db_connection():
    """Get database connection using production database manager"""
    db = get_production_db()
    return db.get_connection()

def is_postgres_db():
    """Check if we're using PostgreSQL database"""
    db = get_production_db()
    return hasattr(db, 'is_production') and db.is_production

def get_param_placeholder():
    """Get the appropriate SQL parameter placeholder"""
    return '%s' if is_postgres_db() else '?'

def initialize_v3_tables(cursor, conn):
    """Initialize V3 tables if they don't exist"""
    try:
        # Use appropriate primary key syntax
        if is_postgres_db():
            id_field = "SERIAL PRIMARY KEY"
            bool_field = "BOOLEAN"
            default_true = "TRUE"
        else:
            id_field = "INTEGER PRIMARY KEY AUTOINCREMENT"
            bool_field = "INTEGER"
            default_true = "1"
        
        param_placeholder = get_param_placeholder()
        
        # Create tables with compatible syntax
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS team_members_cache (
                id {id_field},
                name TEXT NOT NULL,
                whatsapp_number TEXT,
                email TEXT,
                trello_username TEXT,
                is_active {bool_field} DEFAULT {default_true},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Seed team members if table is empty
        cursor.execute('SELECT COUNT(*) FROM team_members_cache')
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Insert the known team members
            # Personal WhatsApp numbers from .env.example (correct format)
            team_members = [
                ('Lancey', '639264438378@c.us', 'lancey@example.com', 'lancey'),
                ('Levy', '237659250977@c.us', 'levy@example.com', 'levy'), 
                ('Wendy', '237677079267@c.us', 'wendy@example.com', 'wendy'),
                ('Forka', '237652275097@c.us', 'forka@example.com', 'forka'),
                ('Brayan', '237676267420@c.us', 'brayan@example.com', 'brayan'),
                ('Breyden', '13179979692@c.us', 'breyden@example.com', 'breyden')
            ]
            
            for name, whatsapp, email, trello_username in team_members:
                cursor.execute(f'''
                    INSERT INTO team_members_cache (name, whatsapp_number, email, trello_username, is_active)
                    VALUES ({param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, {default_true})
                ''', (name, whatsapp, email, trello_username))
                
            print(f"[V3] Seeded {len(team_members)} team members into team_members_cache")
        
        # Migration: Fix existing wrong WhatsApp numbers (group IDs → personal numbers)
        print("[V3] Migrating WhatsApp numbers from group IDs to personal numbers...")
        cursor.execute("SELECT id, name, whatsapp_number FROM team_members_cache WHERE whatsapp_number LIKE '%@g.us'")
        wrong_numbers = cursor.fetchall()
        
        if wrong_numbers:
            print(f"[V3] Found {len(wrong_numbers)} team members with group IDs instead of personal numbers")
            
            # Correct WhatsApp numbers mapping
            correct_numbers = {
                'Lancey': '639264438378@c.us',
                'Levy': '237659250977@c.us',
                'Wendy': '237677079267@c.us',
                'Forka': '237652275097@c.us',
                'Brayan': '237676267420@c.us',
                'Breyden': '13179979692@c.us'
            }
            
            for member_id, name, old_number in wrong_numbers:
                if name in correct_numbers:
                    new_number = correct_numbers[name]
                    cursor.execute(f"UPDATE team_members_cache SET whatsapp_number = {param_placeholder} WHERE id = {param_placeholder}", 
                                 (new_number, member_id))
                    print(f"[V3] Updated {name}: {old_number} -> {new_number}")
                else:
                    print(f"[V3] No correct number found for {name}")
            
            conn.commit()
            print("[V3] WhatsApp number migration completed!")
        
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS whatsapp_templates (
                id {id_field},
                template_name TEXT UNIQUE NOT NULL,
                template_type TEXT NOT NULL,
                template_text TEXT NOT NULL,
                variables TEXT,
                is_active {bool_field} DEFAULT {default_true},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS automation_settings (
                id {id_field},
                setting_name TEXT UNIQUE NOT NULL,
                setting_value TEXT,
                setting_type TEXT,
                description TEXT,
                is_enabled {bool_field} DEFAULT {default_true},
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create core Trello tables that V3 depends on
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS trello_cards (
                id {id_field},
                card_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                list_id TEXT,
                list_name TEXT,
                board_id TEXT,
                board_name TEXT,
                due_date TIMESTAMP,
                labels TEXT,
                closed {bool_field} DEFAULT FALSE,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS card_comments (
                id {id_field},
                card_id TEXT NOT NULL,
                comment_id TEXT UNIQUE NOT NULL,
                comment_text TEXT,
                commenter_name TEXT,
                commenter_id TEXT,
                comment_date TIMESTAMP,
                is_update_request {bool_field} DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS card_assignments (
                id {id_field},
                card_id TEXT NOT NULL,
                team_member TEXT NOT NULL,
                whatsapp_number TEXT,
                assignment_method TEXT,
                confidence_score REAL,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assigned_by TEXT,
                is_active {bool_field} DEFAULT {default_true}
            )
        ''')
        
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS card_metrics (
                id {id_field},
                card_id TEXT UNIQUE NOT NULL,
                time_in_list_hours REAL DEFAULT 0,
                total_ignored_count INTEGER DEFAULT 0,
                last_response_date TIMESTAMP,
                escalation_level INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS list_history (
                id {id_field},
                card_id TEXT NOT NULL,
                from_list TEXT,
                to_list TEXT,
                transition_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Seed WhatsApp templates if table is empty
        cursor.execute('SELECT COUNT(*) FROM whatsapp_templates')
        template_count = cursor.fetchone()[0]
        
        if template_count == 0:
            # Insert default WhatsApp templates
            default_templates = [
                (
                    'Individual Member message 1',
                    'individual',
                    'Hi [name], its been 24 hours since you wrote a comment on the trello card "[card_name]"\n\ncan you go here [card_url] and quickly right a comment, even just "working on it" or the system will message again\n\nmake sure its in the right list! if you are not the one working on it comment "assign [members name]"',
                    '["name", "card_name", "card_url"]'
                ),
                (
                    'Individual Member message 2',
                    'individual',
                    'Hey its been 48 hours now since you commented on the trello card "[card_name]" go here [card_url] and add a comment\nif you are not the one working on it comment "assign [members name]"',
                    '["name", "card_name", "card_url"]'
                ),
                (
                    'Individual Member message 3 FINAL WARNING',
                    'individual',
                    'LAST WARNING! Hey its been 72 hours now since you commented on the trello card "[card_name]"\n\nif there is no comment in the next 24 hours a message in the main group will be sent and you will get aa strike\n\ngo here now and comment with an update or move the card to the right area.\n[card_url]',
                    '["name", "card_name", "card_url"]'
                ),
                (
                    'Group Daily Report',
                    'group',
                    'Quick report on tasks:\nNew tasks made today: [new_tasks]\nNumber of tasks needing an update: [needs_update]\nNumber of cards in review needed: [review_count]\nNumber of tasks in blocked: [blocked_count]\nNumber of notifications sent to members: [notifications_sent]',
                    '["new_tasks", "needs_update", "review_count", "blocked_count", "notifications_sent"]'
                ),
                (
                    'Group Escalation',
                    'group',
                    '[member_name] has not updated their Trello task in 4 days!\n\ncard name: [card_name]\ncard url: [card_url]\n\nplease explain why this has happened?\nif the assigned is wrong then someone comment "assign (name)" so the system reassigns',
                    '["member_name", "card_name", "card_url"]'
                )
            ]
            
            for name, template_type, text, variables in default_templates:
                cursor.execute(f'''
                    INSERT INTO whatsapp_templates (template_name, template_type, template_text, variables, is_active)
                    VALUES ({param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, {default_true})
                ''', (name, template_type, text, variables))
                
            print(f"[V3] Seeded {len(default_templates)} WhatsApp templates")

        # Seed automation settings if table is empty
        cursor.execute('SELECT COUNT(*) FROM automation_settings')
        settings_count = cursor.fetchone()[0]
        
        if settings_count == 0:
            # Insert default automation settings
            default_settings = [
                ('whatsapp_notifications', 'true', 'boolean', 'Enable WhatsApp notifications for card updates', 1),
                ('auto_assignment', 'true', 'boolean', 'Enable automatic card assignment to team members', 1),
                ('escalation_hours', '72', 'number', 'Hours before escalation (3 messages * 24h)', 1),
                ('comment_monitoring', 'true', 'boolean', 'Monitor card comments for team member updates', 1),
                ('daily_reports', 'false', 'boolean', 'Send daily progress reports to team', 0),
                ('sync_frequency_minutes', '30', 'number', 'How often to sync Trello data (minutes)', 1),
                ('message_timing_hours', '24', 'number', 'Hours between automated reminder messages', 1),
                ('combine_messages', 'true', 'boolean', 'Combine multiple WhatsApp messages into one', 1),
                ('automation_lists', 'DOING - IN PROGRESS', 'text', 'Lists where automated WhatsApp messages apply (comma separated)', 1)
            ]
            
            for name, value, setting_type, description, enabled in default_settings:
                # Convert enabled integer to boolean for PostgreSQL compatibility
                enabled_bool = bool(enabled) if is_postgres_db() else enabled
                cursor.execute(f'''
                    INSERT INTO automation_settings (setting_name, setting_value, setting_type, description, is_enabled)
                    VALUES ({param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder})
                ''', (name, value, setting_type, description, enabled_bool))
                
            print(f"[V3] Seeded {len(default_settings)} automation settings")
        
        # Commit all changes
        conn.commit()
        
    except Exception as e:
        print(f"[V3] Warning: Could not create some tables: {e}")
        pass

@team_tracker_v3_bp.route('/team-tracker-v3')
def team_tracker_v3():
    """Enhanced team tracker with modals and metrics"""
    return render_template('team_tracker_v3.html')

@team_tracker_v3_bp.route('/api/v3/dashboard-data')
def get_dashboard_data():
    """Get all data for dashboard"""
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Initialize V3 tables if they don't exist - CRITICAL: Must be called first
        initialize_v3_tables(cursor, conn)
        
        # Get cards with assignments and metrics
        cursor.execute('''
        SELECT 
            c.card_id,
            c.name,
            c.description,
            c.list_name,
            c.url,
            c.last_synced,
            a.team_member,
            a.assignment_method,
            a.confidence_score,
            m.time_in_list_hours,
            m.total_ignored_count,
            m.last_response_date,
            (
                SELECT comment_text || ' | ' || commenter_name
                FROM card_comments cc
                WHERE cc.card_id = c.card_id
                ORDER BY comment_date DESC
                LIMIT 1
            ) as latest_comment,
            (
                SELECT comment_date
                FROM card_comments cc2
                WHERE cc2.card_id = c.card_id
                ORDER BY comment_date DESC
                LIMIT 1
            ) as latest_comment_date
        FROM trello_cards c
        LEFT JOIN card_assignments a ON c.card_id = a.card_id AND a.is_active = 1
        LEFT JOIN card_metrics m ON c.card_id = m.card_id
        WHERE c.closed = 0
          AND c.list_name IN ('NEW TASKS', 'DOING - IN PROGRESS', 'BLOCKED', 'REVIEW - APPROVAL', 'FOREVER TASKS')
          AND (m.escalation_level IS NULL OR m.escalation_level != -1)
        ORDER BY 
            CASE c.list_name
                WHEN 'DOING - IN PROGRESS' THEN 1
                WHEN 'NEW TASKS' THEN 2
                WHEN 'BLOCKED' THEN 3
                WHEN 'REVIEW - APPROVAL' THEN 4
                WHEN 'FOREVER TASKS' THEN 5
            END
        ''')
        
        cards = []
        for row in cursor.fetchall():
            # Calculate hours since last comment with proper timezone handling
            hours_since_comment = None
            if row[13]:  # latest_comment_date
                try:
                    if isinstance(row[13], str):
                        # Handle different timestamp formats
                        date_str = row[13]
                        # Remove timezone info if present for consistent parsing
                        date_str = date_str.replace('+00:00', '').replace('Z', '')
                        # Handle microseconds
                        if '.' in date_str:
                            comment_date = datetime.fromisoformat(date_str)
                        else:
                            comment_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    else:
                        comment_date = row[13]
                        # Remove timezone info if it's a timezone-aware datetime
                        if comment_date.tzinfo is not None:
                            comment_date = comment_date.replace(tzinfo=None)
                    
                    # Calculate hours difference
                    hours_since_comment = (datetime.now() - comment_date).total_seconds() / 3600
                except (ValueError, TypeError) as e:
                    print(f"[V3] Error parsing comment date {row[13]}: {e}")
                    hours_since_comment = None
            
            cards.append({
                'id': row[0],
                'name': row[1],
                'description': row[2][:200] if row[2] else '',
                'list': row[3],
                'url': row[4],
                'assigned_to': row[6] or 'Unassigned',
                'assignment_method': row[7],
                'confidence': row[8],
                'time_in_list': row[9] or 0,
                'ignored_count': row[10] or 0,
                'latest_comment': row[12],
                'hours_since_comment': round(hours_since_comment, 1) if hours_since_comment else None,
                'needs_update': hours_since_comment > 24 if hours_since_comment else False
            })
        
        # Get team members
        cursor.execute('SELECT name, whatsapp_number FROM team_members_cache WHERE is_active = 1')
        team_members = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Get automation settings
        cursor.execute('SELECT setting_name, setting_value FROM automation_settings')
        settings = {row[0]: row[1] for row in cursor.fetchall()}
    
        return jsonify({
            'cards': cards,
            'team_members': team_members,
            'settings': settings
        })
        
    except Exception as e:
        print(f"[V3] Error in dashboard-data: {e}")
        # Return empty data structure on error
        return jsonify({
            'cards': [],
            'team_members': {},
            'settings': {}
        })
    finally:
        if 'conn' in locals():
            conn.close()

@team_tracker_v3_bp.route('/api/v3/card-details/<card_id>')
def get_card_details(card_id):
    """Get detailed information for a specific card"""
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Initialize V3 tables if they don't exist
        initialize_v3_tables(cursor, conn)
    
        # Get card info
        cursor.execute('''
            SELECT name, description, list_name, url, created_at, last_synced
            FROM trello_cards WHERE card_id = ?
        ''', (card_id,))
        
        card_row = cursor.fetchone()
        if not card_row:
            return jsonify({'error': 'Card not found'}), 404
        
        card_data = {
            'name': card_row[0],
            'description': card_row[1],
            'list': card_row[2],
            'url': card_row[3],
            'created_at': card_row[4].isoformat() if isinstance(card_row[4], datetime) else card_row[4],
            'last_synced': card_row[5].isoformat() if isinstance(card_row[5], datetime) else card_row[5]
        }
        
        # Get assignment history
        try:
            cursor.execute('''
                SELECT team_member, assignment_method, confidence_score, assigned_at, is_active
                FROM card_assignments
                WHERE card_id = ?
                ORDER BY assigned_at DESC
            ''', (card_id,))
            
            assignments = []
            for row in cursor.fetchall():
                assignments.append({
                    'member': row[0],
                    'method': row[1],
                    'confidence': row[2],
                    'date': row[3].isoformat() if isinstance(row[3], datetime) else row[3],
                    'is_active': row[4]
                })
        except Exception as e:
            print(f"[V3] Error getting assignments for {card_id}: {e}")
            assignments = []
        
        # Get comments
        try:
            cursor.execute('''
                SELECT commenter_name, comment_text, comment_date, is_update_request
                FROM card_comments
                WHERE card_id = ?
                ORDER BY comment_date DESC
                LIMIT 50
            ''', (card_id,))
            
            comment_rows = cursor.fetchall()
            print(f"[V3] Found {len(comment_rows)} comments for card {card_id}")
            
            comments = []
            for row in comment_rows:
                comments.append({
                    'commenter': row[0],
                    'text': row[1],
                    'date': row[2].isoformat() if isinstance(row[2], datetime) else row[2],
                    'is_request': row[3]
                })
                print(f"[V3] Comment: {row[0]} - {row[1][:50]}...")
        except Exception as e:
            print(f"[V3] Error getting comments for {card_id}: {e}")
            comments = []
        
        # Get list history
        try:
            cursor.execute('''
                SELECT from_list, to_list, transition_date
                FROM list_history
                WHERE card_id = ?
                ORDER BY transition_date DESC
                LIMIT 10
            ''', (card_id,))
            
            list_history = []
            for row in cursor.fetchall():
                list_history.append({
                    'from': row[0],
                    'to': row[1],
                    'date': row[2].isoformat() if isinstance(row[2], datetime) else row[2]
                })
        except Exception as e:
            print(f"[V3] Error getting list history for {card_id}: {e}")
            list_history = []
        
        # Get metrics
        try:
            cursor.execute('''
                SELECT time_in_list_hours, total_ignored_count, last_response_date, escalation_level
                FROM card_metrics
                WHERE card_id = ?
            ''', (card_id,))
            
            metrics_row = cursor.fetchone()
            metrics = {
                'time_in_list': metrics_row[0] if metrics_row else 0,
                'ignored_count': metrics_row[1] if metrics_row else 0,
                'last_response': metrics_row[2].isoformat() if metrics_row and isinstance(metrics_row[2], datetime) else (metrics_row[2] if metrics_row else None),
                'escalation_level': metrics_row[3] if metrics_row else 0
            }
        except Exception as e:
            print(f"[V3] Error getting metrics for {card_id}: {e}")
            metrics = {
                'time_in_list': 0,
                'ignored_count': 0,
                'last_response': None,
                'escalation_level': 0
            }
        
        return jsonify({
            'card': card_data,
            'assignments': assignments,
            'comments': comments,
            'list_history': list_history,
            'metrics': metrics
        })
        
    except Exception as e:
        print(f"[V3] Error in card-details for {card_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        if conn:
            conn.close()

@team_tracker_v3_bp.route('/api/v3/reassign-card', methods=['POST'])
def reassign_card():
    """Reassign a card to a different team member"""
    
    data = request.json
    card_id = data.get('card_id')
    new_member = data.get('team_member')
    
    if not card_id or not new_member:
        return jsonify({'error': 'Missing parameters'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Initialize V3 tables if they don't exist
    initialize_v3_tables(cursor, conn)
    
    # Get team member's WhatsApp
    cursor.execute(f'SELECT whatsapp_number FROM team_members_cache WHERE name = {get_param_placeholder()}', (new_member,))
    result = cursor.fetchone()
    
    if not result:
        return jsonify({'error': 'Team member not found'}), 404
    
    whatsapp = result[0]
    
    # Deactivate old assignments
    cursor.execute(f'UPDATE card_assignments SET is_active = 0 WHERE card_id = {get_param_placeholder()}', (card_id,))
    
    # Create new assignment
    param_placeholder = get_param_placeholder()
    cursor.execute(f'''
        INSERT INTO card_assignments 
        (card_id, team_member, whatsapp_number, assignment_method, confidence_score, assigned_by)
        VALUES ({param_placeholder}, {param_placeholder}, {param_placeholder}, 'manual_reassignment', 1.0, 'user')
    ''', (card_id, new_member, whatsapp))
    
    # Track list history if reassignment changes status
    cursor.execute(f'''
        INSERT INTO list_history (card_id, from_list, to_list)
        SELECT card_id, list_name, list_name
        FROM trello_cards WHERE card_id = {param_placeholder}
    ''', (card_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': f'Card reassigned to {new_member}'})

@team_tracker_v3_bp.route('/api/v3/team-members')
def get_team_members():
    """Get all team members"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Initialize V3 tables if they don't exist
    initialize_v3_tables(cursor, conn)
    
    cursor.execute('''
        SELECT id, name, whatsapp_number, email, trello_username, is_active
        FROM team_members_cache
        ORDER BY name
    ''')
    
    members = []
    for row in cursor.fetchall():
        members.append({
            'id': row[0],
            'name': row[1],
            'whatsapp': row[2],
            'email': row[3],
            'trello_username': row[4],
            'is_active': row[5]
        })
    
    conn.close()
    
    return jsonify({'members': members})

@team_tracker_v3_bp.route('/api/v3/update-team-member', methods=['POST'])
def update_team_member():
    """Update team member details"""
    
    data = request.json
    member_id = data.get('id')
    
    if not member_id:
        return jsonify({'error': 'Member ID required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build update query dynamically
    updates = []
    params = []
    
    if 'name' in data:
        updates.append('name = ?')
        params.append(data['name'])
    
    if 'whatsapp' in data:
        updates.append('whatsapp_number = ?')
        params.append(data['whatsapp'] or None)
    
    if 'email' in data:
        updates.append('email = ?')
        params.append(data['email'] or None)
    
    if 'is_active' in data:
        updates.append('is_active = ?')
        params.append(data['is_active'])
    
    if updates:
        updates.append('updated_at = ?')
        params.append(datetime.now())
        params.append(member_id)
        
        query = f"UPDATE team_members_cache SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
    
    conn.close()
    
    return jsonify({'success': True})

@team_tracker_v3_bp.route('/api/v3/whatsapp-templates')
def get_templates():
    """Get all WhatsApp templates"""
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Initialize V3 tables if they don't exist
        initialize_v3_tables(cursor, conn)
        
        cursor.execute('''
            SELECT id, template_name, template_type, template_text, variables, is_active
            FROM whatsapp_templates
            ORDER BY template_type, template_name
        ''')
        
        templates = []
        for row in cursor.fetchall():
            templates.append({
                'id': row[0],
                'name': row[1],
                'type': row[2],
                'text': row[3],
                'variables': json.loads(row[4]) if row[4] else [],
                'is_active': row[5]
            })
        
        return jsonify({'templates': templates})
        
    except Exception as e:
        print(f"[V3] Error in get_templates: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'templates': []}), 500
    finally:
        if conn:
            conn.close()

@team_tracker_v3_bp.route('/api/v3/update-template', methods=['POST'])
def update_template():
    """Update WhatsApp template"""
    
    data = request.json
    template_id = data.get('id')
    
    if not template_id:
        return jsonify({'error': 'Template ID required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE whatsapp_templates
        SET template_text = ?, updated_at = ?
        WHERE id = ?
    ''', (data.get('text'), datetime.now(), template_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@team_tracker_v3_bp.route('/api/v3/automation-settings')
def get_automation_settings():
    """Get automation settings"""
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Initialize V3 tables if they don't exist
        initialize_v3_tables(cursor, conn)
        
        cursor.execute('''
            SELECT id, setting_name, setting_value, setting_type, description, is_enabled
            FROM automation_settings
            ORDER BY setting_name
        ''')
        
        settings = []
        for row in cursor.fetchall():
            settings.append({
                'id': row[0],
                'name': row[1],
                'value': row[2],
                'type': row[3],
                'description': row[4],
                'enabled': row[5]
            })
        
        return jsonify({'settings': settings})
        
    except Exception as e:
        print(f"[V3] Error in get_automation_settings: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'settings': []}), 500
    finally:
        if conn:
            conn.close()

@team_tracker_v3_bp.route('/api/v3/update-setting', methods=['POST'])
def update_setting():
    """Update automation setting"""
    
    data = request.json
    setting_id = data.get('id')
    
    if not setting_id:
        return jsonify({'error': 'Setting ID required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE automation_settings
        SET setting_value = ?, is_enabled = ?, updated_at = ?
        WHERE id = ?
    ''', (data.get('value'), data.get('enabled', True), datetime.now(), setting_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@team_tracker_v3_bp.route('/api/v3/scan-cards', methods=['POST'])
def scan_cards():
    """Trigger card scanning/syncing with real Trello data"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Initialize tables first
        initialize_v3_tables(cursor, conn)
        
        # Import and run the existing enhanced team tracker
        try:
            from enhanced_team_tracker import EnhancedTeamTracker
            import requests
            
            tracker = EnhancedTeamTracker()
            
            # Get EEInteractive board cards only, excluding COMPLETED list
            if not (tracker.api_key and tracker.token):
                raise Exception('Trello API credentials not configured')
            
            # First, find the EEInteractive board ID
            boards_url = f"https://api.trello.com/1/members/me/boards?key={tracker.api_key}&token={tracker.token}"
            boards_response = requests.get(boards_url, timeout=30)
            boards_response.raise_for_status()
            boards = boards_response.json()
            
            eeinteractive_board = None
            for board in boards:
                if 'eeinteractive' in board['name'].lower():
                    eeinteractive_board = board
                    break
            
            if not eeinteractive_board:
                raise Exception('EEInteractive board not found')
            
            board_id = eeinteractive_board['id']
            print(f"[V3] Found EEInteractive board: {eeinteractive_board['name']} ({board_id})")
            
            # Get lists from EEInteractive board
            lists_url = f"https://api.trello.com/1/boards/{board_id}/lists?key={tracker.api_key}&token={tracker.token}"
            lists_response = requests.get(lists_url, timeout=30)
            lists_response.raise_for_status()
            lists = lists_response.json()
            
            # Filter out COMPLETED/COMPLETE lists
            active_lists = [l for l in lists if not any(word in l['name'].upper() for word in ['COMPLETED', 'COMPLETE', 'DONE', 'FINISHED'])]
            print(f"[V3] Scanning {len(active_lists)} lists (excluding COMPLETED)")
            
            cards_synced = 0
            comments_synced = 0
            assignments_created = 0
            
            # Define admin users (modify as needed)
            admin_users = ['james', 'admin', 'powleads']
            
            for trello_list in active_lists:
                list_id = trello_list['id']
                list_name = trello_list['name']
                
                # Get cards from this list
                cards_url = f"https://api.trello.com/1/lists/{list_id}/cards?key={tracker.api_key}&token={tracker.token}"
                cards_response = requests.get(cards_url, timeout=30)
                cards_response.raise_for_status()
                cards = cards_response.json()
                
                for card in cards:
                    if card['closed']:
                        continue
                    
                    card_id = card['id']
                    
                    # Store/update card in database (preserve existing data on update)
                    cursor.execute(f'SELECT card_id FROM trello_cards WHERE card_id = {get_param_placeholder()}', (card_id,))
                    existing_card = cursor.fetchone()
                    
                    if existing_card:
                        # Update existing card but preserve tracked data
                        cursor.execute('''
                            UPDATE trello_cards 
                            SET name = ?, description = ?, list_id = ?, list_name = ?, 
                                board_id = ?, board_name = ?, due_date = ?, labels = ?, 
                                url = ?, updated_at = ?, last_synced = ?
                            WHERE card_id = ?
                        ''', (
                            card['name'], card.get('desc', ''), list_id, list_name, 
                            board_id, eeinteractive_board['name'], card.get('due'), 
                            str(card.get('labels', [])), card['url'], datetime.now(), 
                            datetime.now(), card_id
                        ))
                    else:
                        # Insert new card
                        cursor.execute('''
                            INSERT INTO trello_cards 
                            (card_id, name, description, list_id, list_name, board_id, board_name, 
                             due_date, labels, closed, url, created_at, updated_at, last_synced)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            card_id, card['name'], card.get('desc', ''),
                            list_id, list_name, board_id, eeinteractive_board['name'],
                            card.get('due'), str(card.get('labels', [])),
                            0, card['url'], datetime.now(), datetime.now(), datetime.now()
                        ))
                    
                    cards_synced += 1
                    
                    # Get and sync comments for this card
                    try:
                        comments_url = f"https://api.trello.com/1/cards/{card_id}/actions?filter=commentCard&key={tracker.api_key}&token={tracker.token}"
                        comments_response = requests.get(comments_url, timeout=30)
                        comments_response.raise_for_status()
                        comments = comments_response.json()
                        
                        # Process comments for assignment logic
                        assigned_member = None
                        assignment_method = None
                        assignment_confidence = 0.0
                        
                        print(f"[V3] Processing {len(comments)} comments for card {card['name']}")
                        
                        # Sort comments by date (oldest first) for proper assignment logic
                        comments_sorted = sorted(comments, key=lambda x: x['date'])
                        
                        for comment in comments_sorted:
                            comment_id = comment['id']
                            comment_text = comment['data']['text']
                            commenter_name = comment['memberCreator']['fullName']
                            commenter_username = comment['memberCreator']['username']
                            comment_date = datetime.fromisoformat(comment['date'].replace('Z', '+00:00'))
                            
                            # Store comment in database
                            cursor.execute('''
                                INSERT OR REPLACE INTO card_comments 
                                (card_id, comment_id, comment_text, commenter_name, commenter_id, comment_date, is_update_request)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                card_id, comment_id, comment_text, commenter_name,
                                commenter_username, comment_date, 0
                            ))
                            comments_synced += 1
                            print(f"[V3] 💬 Saved comment by {commenter_name}: {comment_text[:30]}...")
                            
                            # Assignment logic
                            comment_lower = comment_text.lower()
                            
                            print(f"[V3] Comment by {commenter_name} ({commenter_username}): {comment_text[:50]}...")
                            
                            # Check for explicit assignment (e.g., "assign: lancey" or "assign lancey")
                            import re
                            assign_match = re.search(r'assign[:\s]+(\w+)', comment_lower)
                            if assign_match:
                                assigned_name = assign_match.group(1).title()
                                print(f"[V3] Found assignment command: {assigned_name}")
                                # Check if this is a valid team member
                                cursor.execute('SELECT name FROM team_members_cache WHERE LOWER(name) = ?', (assigned_name.lower(),))
                                member_result = cursor.fetchone()
                                if member_result:
                                    assigned_member = member_result[0]
                                    assignment_method = 'explicit_assignment'
                                    assignment_confidence = 1.0
                                    print(f"[V3] ✅ Explicit assignment: {assigned_member} for card {card['name']}")
                                else:
                                    print(f"[V3] ❌ Assignment target '{assigned_name}' not found in team members")
                            
                            # If no explicit assignment and commenter is not admin, this is the assignee
                            elif not assigned_member and commenter_username.lower() not in [u.lower() for u in admin_users]:
                                print(f"[V3] Checking if {commenter_name} ({commenter_username}) is a team member...")
                                
                                # Try exact match first
                                cursor.execute('SELECT name FROM team_members_cache WHERE LOWER(name) = ? OR LOWER(trello_username) = ?', 
                                             (commenter_name.lower(), commenter_username.lower()))
                                team_member = cursor.fetchone()
                                
                                # If no exact match, try fuzzy matching (partial name match)
                                if not team_member:
                                    cursor.execute('SELECT name FROM team_members_cache')
                                    all_members = cursor.fetchall()
                                    
                                    for member_row in all_members:
                                        member_name = member_row[0]
                                        # Check if any part of the member name is in the commenter name or vice versa
                                        if (member_name.lower() in commenter_name.lower() or 
                                            any(part.lower() in commenter_name.lower() for part in member_name.split() if len(part) > 2) or
                                            any(part.lower() in member_name.lower() for part in commenter_name.split() if len(part) > 2)):
                                            team_member = (member_name,)
                                            print(f"[V3] 🔍 Fuzzy match: '{commenter_name}' → '{member_name}'")
                                            break
                                
                                if team_member:
                                    assigned_member = team_member[0]
                                    assignment_method = 'first_comment'
                                    assignment_confidence = 0.8
                                    print(f"[V3] ✅ First comment assignment: {assigned_member} for card {card['name']}")
                                else:
                                    print(f"[V3] ❌ Commenter {commenter_name} ({commenter_username}) not found in team members")
                            else:
                                if commenter_username.lower() in [u.lower() for u in admin_users]:
                                    print(f"[V3] Skipping admin user: {commenter_username}")
                        
                        # Create/update assignment if found
                        if assigned_member:
                            print(f"[V3] Creating assignment for {card['name']} → {assigned_member}")
                            # Get WhatsApp number
                            cursor.execute('SELECT whatsapp_number FROM team_members_cache WHERE name = ?', (assigned_member,))
                            whatsapp_result = cursor.fetchone()
                            whatsapp_number = whatsapp_result[0] if whatsapp_result else None
                            
                            # Deactivate old assignments
                            cursor.execute('UPDATE card_assignments SET is_active = 0 WHERE card_id = ?', (card_id,))
                            
                            # Create new assignment
                            cursor.execute('''
                                INSERT INTO card_assignments 
                                (card_id, team_member, whatsapp_number, assignment_method, confidence_score, assigned_by)
                                VALUES (?, ?, ?, ?, ?, 'auto_scan')
                            ''', (card_id, assigned_member, whatsapp_number, assignment_method, assignment_confidence))
                            assignments_created += 1
                            print(f"[V3] ✅ Assignment created: {assigned_member} for {card['name']}")
                            
                            # Initialize metrics for this card
                            cursor.execute('''
                                INSERT OR IGNORE INTO card_metrics 
                                (card_id, time_in_list_hours, total_ignored_count, escalation_level)
                                VALUES (?, 0, 0, 0)
                            ''', (card_id,))
                        else:
                            print(f"[V3] ❌ No assignment found for card: {card['name']}")
                    
                    except Exception as comment_error:
                        print(f"[V3] Error syncing comments for card {card_id}: {comment_error}")
                        continue
                
                print(f"[V3] Synced {len([c for c in cards if not c['closed']])} cards from {list_name}")
            
            conn.commit()
            
            # Count final cards
            cursor.execute('SELECT COUNT(*) FROM trello_cards WHERE closed = 0 AND board_name LIKE ?', 
                          (f'%{eeinteractive_board["name"]}%',))
            total_cards = cursor.fetchone()[0]
            
            conn.close()
            
            return jsonify({
                'success': True,
                'message': f'EEInteractive board sync completed! Found {total_cards} active cards',
                'board_name': eeinteractive_board['name'],
                'cards_synced': cards_synced,
                'comments_synced': comments_synced,
                'assignments_created': assignments_created,
                'lists_scanned': len(active_lists),
                'excluded_lists': ['COMPLETED', 'COMPLETE', 'DONE', 'FINISHED']
            })
            
        except ImportError as e:
            # Fallback: Call the existing sync endpoint internally
            import requests
            import os
            
            # Get the current server URL
            base_url = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:5000')
            
            try:
                response = requests.post(f'{base_url}/api/sync-cards', 
                                       headers={'Content-Type': 'application/json'},
                                       timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Count cards after sync
                    cursor.execute('SELECT COUNT(*) FROM trello_cards WHERE closed = 0')
                    total_cards = cursor.fetchone()[0]
                    
                    conn.close()
                    
                    return jsonify({
                        'success': True,
                        'message': f'Trello sync completed via API! Found {total_cards} active cards',
                        'cards_found': total_cards,
                        'cards_synced': data.get('cards_synced', 0),
                        'comments_synced': data.get('comments_synced', 0)
                    })
                else:
                    raise Exception(f'Sync API returned status {response.status_code}')
                    
            except Exception as api_error:
                print(f"[V3] API sync failed: {api_error}")
                raise Exception(f'Both direct import and API sync failed: {str(e)}, {str(api_error)}')
        
    except Exception as e:
        print(f"[V3] Card scanning error: {e}")
        return jsonify({
            'success': False,
            'error': f'Card scanning failed: {str(e)}. Please check if Trello API credentials are configured.'
        }), 500

@team_tracker_v3_bp.route('/api/v3/add-team-member', methods=['POST'])
def add_team_member():
    """Add a new team member"""
    
    data = request.json
    name = data.get('name', '').strip()
    whatsapp = data.get('whatsapp', '').strip()
    email = data.get('email', '').strip()
    
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if member already exists
        cursor.execute('SELECT COUNT(*) FROM team_members_cache WHERE name = ?', (name,))
        if cursor.fetchone()[0] > 0:
            return jsonify({'error': f'Team member "{name}" already exists'}), 400
        
        # Insert new team member
        cursor.execute('''
            INSERT INTO team_members_cache (name, whatsapp_number, email, trello_username, is_active)
            VALUES (?, ?, ?, ?, 1)
        ''', (name, whatsapp or None, email or None, name.lower().replace(' ', '_')))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Team member "{name}" added successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to add team member: {str(e)}'
        }), 500

@team_tracker_v3_bp.route('/api/v3/toggle-ignore-card', methods=['POST'])
def toggle_ignore_card():
    """Toggle ignore status for a card"""
    
    data = request.json
    card_id = data.get('card_id')
    
    if not card_id:
        return jsonify({'error': 'Card ID is required'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Initialize V3 tables if they don't exist
        initialize_v3_tables(cursor, conn)
        
        # Check current ignore status
        cursor.execute('SELECT * FROM card_metrics WHERE card_id = ?', (card_id,))
        metrics = cursor.fetchone()
        
        if metrics:
            # Toggle ignore status (we'll use escalation_level = -1 to indicate ignored)
            current_ignored = metrics[4] == -1  # escalation_level column
            new_ignored = not current_ignored
            
            cursor.execute('''
                UPDATE card_metrics 
                SET escalation_level = ?, updated_at = ?
                WHERE card_id = ?
            ''', (-1 if new_ignored else 0, datetime.now(), card_id))
        else:
            # Create new metrics record with ignored status
            cursor.execute('''
                INSERT INTO card_metrics 
                (card_id, time_in_list_hours, total_ignored_count, escalation_level, updated_at)
                VALUES (?, 0, 0, -1, ?)
            ''', (card_id, datetime.now()))
            new_ignored = True
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'ignored': new_ignored,
            'message': 'Card ignored' if new_ignored else 'Card un-ignored'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to toggle ignore: {str(e)}'
        }), 500

@team_tracker_v3_bp.route('/api/v3/send-custom-whatsapp', methods=['POST'])
def send_custom_whatsapp():
    """Send custom WhatsApp message to assigned member"""
    
    try:
        data = request.json
        print(f"[V3] 📥 Custom WhatsApp request data: {data}")
        
        card_id = data.get('card_id')
        member_name = data.get('member_name')
        message = data.get('message')
        
        print(f"[V3] 📋 Parsed parameters: card_id={card_id}, member_name={member_name}, message_length={len(message) if message else 0}")
        
        if not all([card_id, member_name, message]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Initialize V3 tables if they don't exist
        initialize_v3_tables(cursor, conn)
        
        # Get member's WhatsApp number
        cursor.execute('SELECT whatsapp_number FROM team_members_cache WHERE name = ?', (member_name,))
        result = cursor.fetchone()
        
        if not result or not result[0]:
            return jsonify({'error': f'WhatsApp number not found for {member_name}'}), 404
        
        whatsapp_number = result[0]
        
        # Get card details for context
        cursor.execute('SELECT name, url FROM trello_cards WHERE card_id = ?', (card_id,))
        card_result = cursor.fetchone()
        
        if not card_result:
            return jsonify({'error': 'Card not found'}), 404
        
        card_name, card_url = card_result
        
        # Send WhatsApp message via Green API
        try:
            green_api = GreenAPIClient()
            
            # Use the WhatsApp number as stored (should already be in correct @c.us format)
            if whatsapp_number.endswith('@c.us'):
                chat_id = whatsapp_number
            else:
                # Fallback: format as personal number if not already formatted
                clean_number = ''.join(filter(str.isdigit, whatsapp_number))
                chat_id = f"{clean_number}@c.us"
            
            print(f"[V3] 📱 Attempting WhatsApp send to {member_name}")
            print(f"[V3] Original number: {whatsapp_number}")
            print(f"[V3] Formatted chat_id: {chat_id}")
            print(f"[V3] Message: {message}")
            
            # Send the actual WhatsApp message
            send_result = green_api.send_message(chat_id, message)
            
            # Log the message send attempt based on result
            if 'error' not in send_result:
                cursor.execute('''
                    INSERT INTO card_comments 
                    (card_id, comment_id, comment_text, commenter_name, commenter_id, comment_date, is_update_request)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    card_id, f'manual_whatsapp_{datetime.now().isoformat()}', 
                    f'✅ WhatsApp sent to {member_name}: {message}', 'System', 'system',
                    datetime.now(), 0
                ))
            else:
                cursor.execute('''
                    INSERT INTO card_comments 
                    (card_id, comment_id, comment_text, commenter_name, commenter_id, comment_date, is_update_request)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    card_id, f'manual_whatsapp_failed_{datetime.now().isoformat()}', 
                    f'❌ WhatsApp failed to {member_name}: {send_result.get("error", "Unknown error")}', 'System', 'system',
                    datetime.now(), 0
                ))
        except Exception as e:
            # Log error if Green API fails
            cursor.execute('''
                INSERT INTO card_comments 
                (card_id, comment_id, comment_text, commenter_name, commenter_id, comment_date, is_update_request)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                card_id, f'manual_whatsapp_error_{datetime.now().isoformat()}', 
                f'❌ WhatsApp error: {str(e)}', 'System', 'system',
                datetime.now(), 0
            ))
            send_result = {'error': str(e)}
        
        # Update metrics
        cursor.execute('''
            UPDATE card_metrics 
            SET total_ignored_count = total_ignored_count + 1, updated_at = ?
            WHERE card_id = ?
        ''', (datetime.now(), card_id))
        
        conn.commit()
        conn.close()
        
        if 'error' not in send_result:
            print(f"[V3] ✅ WhatsApp sent to {member_name} ({chat_id}): {message}")
            print(f"[V3] Card context: {card_name} - {card_url}")
            return jsonify({
                'success': True,
                'message': f'WhatsApp message sent to {member_name}',
                'whatsapp_number': chat_id
            })
        else:
            print(f"[V3] ❌ WhatsApp failed to {member_name}: {send_result.get('error')}")
            return jsonify({
                'success': False,
                'error': f'Failed to send WhatsApp: {send_result.get("error", "Unknown error")}'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to send message: {str(e)}'
        }), 500

@team_tracker_v3_bp.route('/api/v3/send-assign-request', methods=['POST'])
def send_assign_request():
    """Send assignment request message to group"""
    
    data = request.json
    card_id = data.get('card_id')
    card_name = data.get('card_name')
    card_url = data.get('card_url')
    
    if not all([card_id, card_name, card_url]):
        return jsonify({'error': 'Missing required parameters'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Initialize V3 tables if they don't exist
        initialize_v3_tables(cursor, conn)
        
        # Create the group message
        group_message = f'Can someone assign this new task by going to {card_url} and commenting "assign (persons name)", thanks'
        
        # Send to WhatsApp group via Green API
        try:
            green_api = GreenAPIClient()
            
            # Get the group chat ID from environment or database
            group_chat_id = os.environ.get('WHATSAPP_GROUP_ID', '120363044057367718@g.us')  # Default group ID
            
            # Send the actual WhatsApp message to group
            send_result = green_api.send_message(group_chat_id, group_message)
            
            # Log the assign request based on result
            if 'error' not in send_result:
                cursor.execute('''
                    INSERT INTO card_comments 
                    (card_id, comment_id, comment_text, commenter_name, commenter_id, comment_date, is_update_request)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    card_id, f'assign_request_{datetime.now().isoformat()}', 
                    f'✅ Assignment request sent to group: {group_message}', 'System', 'system',
                    datetime.now(), 1
                ))
                print(f"[V3] ✅ Group assign request sent for card: {card_name}")
            else:
                cursor.execute('''
                    INSERT INTO card_comments 
                    (card_id, comment_id, comment_text, commenter_name, commenter_id, comment_date, is_update_request)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    card_id, f'assign_request_failed_{datetime.now().isoformat()}', 
                    f'❌ Failed to send assignment request to group: {send_result.get("error", "Unknown error")}', 'System', 'system',
                    datetime.now(), 1
                ))
                print(f"[V3] ❌ Failed to send group assign request: {send_result.get('error')}")
        except Exception as e:
            cursor.execute('''
                INSERT INTO card_comments 
                (card_id, comment_id, comment_text, commenter_name, commenter_id, comment_date, is_update_request)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                card_id, f'assign_request_error_{datetime.now().isoformat()}', 
                f'❌ Assignment request error: {str(e)}', 'System', 'system',
                datetime.now(), 1
            ))
            send_result = {'error': str(e)}
        
        conn.commit()
        conn.close()
        
        print(f"[V3] Message: {group_message}")
        
        return jsonify({
            'success': True,
            'message': 'Assignment request sent to group',
            'group_message': group_message
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to send assign request: {str(e)}'
        }), 500

@team_tracker_v3_bp.route('/api/v3/delete-team-member', methods=['POST'])
def delete_team_member():
    """Delete a team member"""
    
    data = request.json
    member_id = data.get('id')
    
    if not member_id:
        return jsonify({'error': 'Member ID is required'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if member exists
        cursor.execute('SELECT name FROM team_members_cache WHERE id = ?', (member_id,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify({'error': 'Team member not found'}), 404
        
        member_name = result[0]
        
        # Delete the team member
        cursor.execute('DELETE FROM team_members_cache WHERE id = ?', (member_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Team member "{member_name}" deleted successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to delete team member: {str(e)}'
        }), 500

@team_tracker_v3_bp.route('/api/v3/whatsapp-templates/<int:template_id>', methods=['PUT'])
def update_whatsapp_template(template_id):
    """Update WhatsApp template"""
    
    try:
        data = request.json
        print(f"[V3] 📝 Template update request: template_id={template_id}, data={data}")
        
        name = data.get('name')
        template_type = data.get('type')
        text = data.get('text')
        
        print(f"[V3] 📋 Parsed template data: name={name}, type={template_type}, text_length={len(text) if text else 0}")
        
        if not all([name, template_type, text]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Initialize V3 tables if they don't exist
        initialize_v3_tables(cursor, conn)
        
        # Check if template exists
        cursor.execute('SELECT id FROM whatsapp_templates WHERE id = ?', (template_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Template not found'}), 404
        
        # Update the template
        cursor.execute('''
            UPDATE whatsapp_templates 
            SET template_name = ?, template_type = ?, template_text = ?, updated_at = ?
            WHERE id = ?
        ''', (name, template_type, text, datetime.now(), template_id))
        
        rows_affected = cursor.rowcount
        print(f"[V3] 📝 Template update completed: rows_affected={rows_affected}")
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Template updated successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to update template: {str(e)}'
        }), 500

@team_tracker_v3_bp.route('/api/v3/whatsapp-templates/<int:template_id>', methods=['DELETE'])
def delete_whatsapp_template(template_id):
    """Delete WhatsApp template"""
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if template exists
        cursor.execute('SELECT template_name FROM whatsapp_templates WHERE id = ?', (template_id,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify({'error': 'Template not found'}), 404
        
        template_name = result[0]
        
        # Delete the template
        cursor.execute('DELETE FROM whatsapp_templates WHERE id = ?', (template_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Template "{template_name}" deleted successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to delete template: {str(e)}'
        }), 500