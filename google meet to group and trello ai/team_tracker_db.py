"""
Team Tracker Database UI
Shows Trello cards from the synced database with enhanced features
"""

import sqlite3
from datetime import datetime, timedelta
from flask import Blueprint, render_template, jsonify, request
import json

# Create blueprint
team_tracker_bp = Blueprint('team_tracker_db', __name__)

def get_db_connection():
    """Get connection to team_tracker_v2.db"""
    return sqlite3.connect('team_tracker_v2.db', 
                          detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)

@team_tracker_bp.route('/team-tracker-v2')
def team_tracker_v2():
    """Enhanced team tracker using database"""
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
    except Exception as e:
        # If database doesn't exist or is corrupted, show error page
        return f"""
        <html>
        <head><title>Team Tracker Setup Required</title></head>
        <body style="font-family: sans-serif; padding: 40px; max-width: 800px; margin: 0 auto;">
            <h1>Team Tracker v2 - Setup Required</h1>
            <p style="color: red;">Database not initialized: {str(e)}</p>
            <h2>To set up the Team Tracker:</h2>
            <ol>
                <li>Run: <code>python database_schema_v2.py</code></li>
                <li>Run: <code>python trello_sync_simple.py</code></li>
                <li>Refresh this page</li>
            </ol>
            <p><a href="/team-tracker">Use original team tracker</a></p>
        </body>
        </html>
        """, 500
    
    # Get all active cards with assignments and latest comments
    query = '''
        SELECT 
            c.card_id,
            c.name,
            c.description,
            c.list_name,
            c.url,
            c.due_date,
            c.last_synced,
            a.team_member,
            a.assignment_method,
            a.confidence_score,
            (
                SELECT comment_text || ' - ' || commenter_name || ' (' || 
                       ROUND((julianday('now') - julianday(comment_date)) * 24, 1) || 'h ago)'
                FROM card_comments cc
                WHERE cc.card_id = c.card_id
                ORDER BY comment_date DESC
                LIMIT 1
            ) as latest_comment,
            (
                SELECT ROUND((julianday('now') - julianday(comment_date)) * 24, 1)
                FROM card_comments cc2
                WHERE cc2.card_id = c.card_id
                  AND cc2.commenter_name LIKE '%' || a.team_member || '%'
                ORDER BY comment_date DESC
                LIMIT 1
            ) as hours_since_team_update
        FROM trello_cards c
        LEFT JOIN card_assignments a ON c.card_id = a.card_id AND a.is_active = 1
        WHERE c.closed = 0
        ORDER BY 
            CASE c.list_name
                WHEN 'DOING - IN PROGRESS' THEN 1
                WHEN 'TO DO - NEW' THEN 2
                WHEN 'BLOCKED - HELP NEEDED' THEN 3
                WHEN 'REVIEW - APPROVAL' THEN 4
                ELSE 5
            END,
            c.name
    '''
    
    cursor.execute(query)
    cards = cursor.fetchall()
    
    # Organize cards by list
    cards_by_list = {}
    needs_update = []
    no_assignment = []
    
    for card in cards:
        (card_id, name, description, list_name, url, due_date, last_synced,
         team_member, assignment_method, confidence_score, latest_comment, 
         hours_since_update) = card
        
        card_data = {
            'id': card_id,
            'name': name,
            'description': description[:200] if description else '',
            'list': list_name,
            'url': url,
            'due_date': due_date,
            'assigned_to': team_member or 'Unassigned',
            'assignment_method': assignment_method,
            'confidence': f"{int(confidence_score * 100)}%" if confidence_score else 'N/A',
            'latest_comment': latest_comment or 'No comments',
            'hours_since_update': hours_since_update,
            'needs_update': False
        }
        
        # Check if needs update
        if list_name in ['DOING - IN PROGRESS', 'TO DO - NEW']:
            if not team_member:
                no_assignment.append(card_data)
            elif hours_since_update is None or hours_since_update > 24:
                card_data['needs_update'] = True
                needs_update.append(card_data)
        
        # Group by list
        if list_name not in cards_by_list:
            cards_by_list[list_name] = []
        cards_by_list[list_name].append(card_data)
    
    # Get sync status
    cursor.execute('''
        SELECT sync_type, started_at, completed_at, cards_synced, comments_synced, status
        FROM sync_history
        ORDER BY started_at DESC
        LIMIT 1
    ''')
    
    last_sync = cursor.fetchone()
    sync_status = {
        'last_sync': last_sync[2] if last_sync else None,
        'cards_synced': last_sync[3] if last_sync else 0,
        'comments_synced': last_sync[4] if last_sync else 0,
        'status': last_sync[5] if last_sync else 'Never synced'
    }
    
    # Get team members
    cursor.execute('''
        SELECT name, whatsapp_number FROM team_members_cache WHERE is_active = 1
    ''')
    team_members = {row[0]: row[1] for row in cursor.fetchall()}
    
    conn.close()
    
    try:
        return render_template('team_tracker_v2.html',
                         cards_by_list=cards_by_list,
                         needs_update=needs_update,
                         no_assignment=no_assignment,
                         sync_status=sync_status,
                         team_members=team_members,
                         total_cards=len(cards))
    except Exception as e:
        # Template not found or other rendering error
        return jsonify({
            'error': 'Template rendering failed',
            'message': str(e),
            'cards_found': len(cards),
            'sync_status': sync_status,
            'suggestion': 'The database is working but the template may be missing'
        }), 500

@team_tracker_bp.route('/api/sync-cards', methods=['POST'])
def sync_cards():
    """Trigger manual card sync"""
    try:
        from trello_sync_simple import SimpleTrelloSync
        
        sync = SimpleTrelloSync()
        stats = sync.sync_all_cards()
        
        return jsonify({
            'success': True,
            'cards_synced': stats['cards_synced'],
            'comments_synced': stats['comments_synced'],
            'assignments_detected': stats['assignments_detected']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@team_tracker_bp.route('/api/update-assignment', methods=['POST'])
def update_assignment():
    """Manual assignment override"""
    data = request.json
    card_id = data.get('card_id')
    team_member = data.get('team_member')
    
    if not card_id or not team_member:
        return jsonify({'success': False, 'error': 'Missing parameters'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get WhatsApp number for team member
        cursor.execute('SELECT whatsapp_number FROM team_members_cache WHERE name = ?', (team_member,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify({'success': False, 'error': 'Team member not found'}), 404
        
        whatsapp = result[0]
        
        # Deactivate old assignments
        cursor.execute('UPDATE card_assignments SET is_active = 0 WHERE card_id = ?', (card_id,))
        
        # Create new assignment
        cursor.execute('''
            INSERT INTO card_assignments 
            (card_id, team_member, whatsapp_number, assignment_method, confidence_score, assigned_by)
            VALUES (?, ?, ?, 'manual', 1.0, 'user')
        ''', (card_id, team_member, whatsapp))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@team_tracker_bp.route('/api/card-history/<card_id>')
def card_history(card_id):
    """Get comment history for a card"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all comments for the card
    cursor.execute('''
        SELECT commenter_name, comment_text, comment_date, is_update_request
        FROM card_comments
        WHERE card_id = ?
        ORDER BY comment_date DESC
        LIMIT 20
    ''', (card_id,))
    
    comments = []
    for row in cursor.fetchall():
        comment_date = row[2]
        if comment_date:
            hours_ago = (datetime.now() - comment_date).total_seconds() / 3600
        else:
            hours_ago = 999
        
        comments.append({
            'commenter': row[0],
            'text': row[1],
            'date': comment_date.isoformat() if comment_date else None,
            'hours_ago': round(hours_ago, 1),
            'is_request': row[3]
        })
    
    conn.close()
    
    return jsonify({'comments': comments})

@team_tracker_bp.route('/api/send-reminders', methods=['POST'])
def send_reminders():
    """Send WhatsApp reminders to team members who need to update"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Find cards that need updates
    query = '''
        SELECT 
            c.card_id,
            c.name,
            c.list_name,
            a.team_member,
            a.whatsapp_number,
            (
                SELECT ROUND((julianday('now') - julianday(comment_date)) * 24, 1)
                FROM card_comments cc
                WHERE cc.card_id = c.card_id
                  AND cc.commenter_name LIKE '%' || a.team_member || '%'
                ORDER BY comment_date DESC
                LIMIT 1
            ) as hours_since_update
        FROM trello_cards c
        INNER JOIN card_assignments a ON c.card_id = a.card_id AND a.is_active = 1
        WHERE c.closed = 0
          AND c.list_name IN ('DOING - IN PROGRESS', 'TO DO - NEW')
          AND a.team_member IS NOT NULL
          AND a.whatsapp_number IS NOT NULL
    '''
    
    cursor.execute(query)
    cards_needing_updates = cursor.fetchall()
    
    sent_count = 0
    errors = []
    
    for card in cards_needing_updates:
        card_id, card_name, list_name, team_member, whatsapp, hours_since = card
        
        # Check if update is needed (no update in 24 hours)
        if hours_since is None or hours_since > 24:
            try:
                # Send WhatsApp message
                try:
                    from whatsapp_integration import send_whatsapp_message
                except ImportError:
                    # Fallback to direct API call
                    def send_whatsapp_message(phone, msg):
                        import os
                        import requests
                        url = f"https://api.greenapi.com/waInstance{os.environ.get('GREEN_API_INSTANCE')}/sendMessage/{os.environ.get('GREEN_API_TOKEN')}"
                        payload = {
                            "chatId": phone,
                            "message": msg
                        }
                        try:
                            response = requests.post(url, json=payload, timeout=10)
                            return response.status_code == 200
                        except:
                            return False
                
                message = f"Hi {team_member}! 👋\\n\\n"
                message += f"Please provide an update on:\\n*{card_name}*\\n\\n"
                
                if hours_since:
                    message += f"Your last update was {int(hours_since)} hours ago.\\n"
                else:
                    message += "No updates found for this card yet.\\n"
                
                message += f"\\nCurrent status: {list_name}\\n"
                message += "Please reply with your progress update. Thanks! 🙏"
                
                result = send_whatsapp_message(whatsapp, message)
                
                if result:
                    # Record notification sent
                    cursor.execute('''
                        INSERT INTO update_notifications 
                        (card_id, team_member, whatsapp_number, hours_since_last_comment, 
                         notification_type, status)
                        VALUES (?, ?, ?, ?, 'no_update_24h', 'sent')
                    ''', (card_id, team_member, whatsapp, hours_since or 999))
                    sent_count += 1
                else:
                    errors.append(f"Failed to send to {team_member}")
                    
            except Exception as e:
                errors.append(f"Error sending to {team_member}: {str(e)}")
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'sent': sent_count,
        'errors': errors
    })