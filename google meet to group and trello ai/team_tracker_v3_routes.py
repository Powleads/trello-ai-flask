"""
Team Tracker V3 - Enhanced Routes with Modal Support
"""

from flask import Blueprint, render_template, jsonify, request
from datetime import datetime, timedelta
import json
import re
from production_db import get_production_db

team_tracker_v3_bp = Blueprint('team_tracker_v3', __name__)

def get_db_connection():
    """Get database connection using production database manager"""
    db = get_production_db()
    return db.get_connection()

def initialize_v3_tables(cursor):
    """Initialize V3 tables if they don't exist"""
    try:
        # Check if we can determine database type
        from production_db import get_production_db
        db = get_production_db()
        
        # Use appropriate primary key syntax
        if hasattr(db, 'is_postgres') and db.is_postgres():
            id_field = "SERIAL PRIMARY KEY"
            bool_field = "BOOLEAN"
        else:
            id_field = "INTEGER PRIMARY KEY AUTOINCREMENT"
            bool_field = "INTEGER"
        
        # Create tables with compatible syntax
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS team_members_cache (
                id {id_field},
                name TEXT NOT NULL,
                whatsapp_number TEXT,
                email TEXT,
                trello_username TEXT,
                is_active {bool_field} DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS whatsapp_templates (
                id {id_field},
                template_name TEXT UNIQUE NOT NULL,
                template_type TEXT NOT NULL,
                template_text TEXT NOT NULL,
                variables TEXT,
                is_active {bool_field} DEFAULT 1,
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
                is_enabled {bool_field} DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
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
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Initialize V3 tables if they don't exist
        initialize_v3_tables(cursor)
        
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
        # Calculate hours since last comment
        hours_since_comment = None
        if row[13]:  # latest_comment_date
            if isinstance(row[13], str):
                comment_date = datetime.fromisoformat(row[13].replace('Z', '+00:00').replace('+00:00', ''))
            else:
                comment_date = row[13]
            hours_since_comment = (datetime.now() - comment_date).total_seconds() / 3600
        
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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
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
        'created_at': card_row[4].isoformat() if card_row[4] else None,
        'last_synced': card_row[5].isoformat() if isinstance(card_row[5], datetime) else card_row[5]
    }
    
    # Get assignment history
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
            'date': row[3].isoformat() if row[3] else None,
            'is_active': row[4]
        })
    
    # Get comments
    cursor.execute('''
        SELECT commenter_name, comment_text, comment_date, is_update_request
        FROM card_comments
        WHERE card_id = ?
        ORDER BY comment_date DESC
        LIMIT 50
    ''', (card_id,))
    
    comments = []
    for row in cursor.fetchall():
        comments.append({
            'commenter': row[0],
            'text': row[1],
            'date': row[2].isoformat() if row[2] else None,
            'is_request': row[3]
        })
    
    # Get list history
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
            'date': row[2].isoformat() if row[2] else None
        })
    
    # Get metrics
    cursor.execute('''
        SELECT time_in_list_hours, total_ignored_count, last_response_date, escalation_level
        FROM card_metrics
        WHERE card_id = ?
    ''', (card_id,))
    
    metrics_row = cursor.fetchone()
    metrics = {
        'time_in_list': metrics_row[0] if metrics_row else 0,
        'ignored_count': metrics_row[1] if metrics_row else 0,
        'last_response': metrics_row[2].isoformat() if metrics_row and metrics_row[2] else None,
        'escalation_level': metrics_row[3] if metrics_row else 0
    }
    
    conn.close()
    
    return jsonify({
        'card': card_data,
        'assignments': assignments,
        'comments': comments,
        'list_history': list_history,
        'metrics': metrics
    })

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
    
    # Get team member's WhatsApp
    cursor.execute('SELECT whatsapp_number FROM team_members_cache WHERE name = ?', (new_member,))
    result = cursor.fetchone()
    
    if not result:
        return jsonify({'error': 'Team member not found'}), 404
    
    whatsapp = result[0]
    
    # Deactivate old assignments
    cursor.execute('UPDATE card_assignments SET is_active = 0 WHERE card_id = ?', (card_id,))
    
    # Create new assignment
    cursor.execute('''
        INSERT INTO card_assignments 
        (card_id, team_member, whatsapp_number, assignment_method, confidence_score, assigned_by)
        VALUES (?, ?, ?, 'manual_reassignment', 1.0, 'user')
    ''', (card_id, new_member, whatsapp))
    
    # Track list history if reassignment changes status
    cursor.execute('''
        INSERT INTO list_history (card_id, from_list, to_list)
        SELECT card_id, list_name, list_name
        FROM trello_cards WHERE card_id = ?
    ''', (card_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': f'Card reassigned to {new_member}'})

@team_tracker_v3_bp.route('/api/v3/team-members')
def get_team_members():
    """Get all team members"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
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
    
    if 'whatsapp' in data:
        updates.append('whatsapp_number = ?')
        params.append(data['whatsapp'])
    
    if 'email' in data:
        updates.append('email = ?')
        params.append(data['email'])
    
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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
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
    
    conn.close()
    
    return jsonify({'templates': templates})

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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
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
    
    conn.close()
    
    return jsonify({'settings': settings})

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