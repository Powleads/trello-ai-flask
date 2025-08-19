#!/usr/bin/env python3
"""
Multi-App Web Interface with AI Features
Unified platform for Google Meet to Trello AI and Team Update Tracker
"""

import asyncio
import sys
import os
import re
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread
import schedule

# Add src to path
sys.path.insert(0, 'src')

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from dotenv import load_dotenv
import requests
from trello import TrelloClient

# Import AI modules
try:
    from speaker_analysis import SpeakerAnalyzer
    from recurring_task_tracker import RecurringTaskTracker
    print("AI modules loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import AI modules: {e}")
    SpeakerAnalyzer = None
    RecurringTaskTracker = None

# Load environment
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Team member data from blueprint
TEAM_MEMBERS = {
    'Criselle': '639494048499@c.us',
    'Lancey': '639264438378@c.us',
    'Ezechiel': '23754071907@c.us',
    'Levy': '237659250977@c.us',
    'Wendy': '237677079267@c.us',
    'Forka': '237652275097@c.us',
    'Breyden': '13179979692@c.us',
    'Brayan': '237676267420@c.us'
}

GREEN_API_CONFIG = {
    'instance_id': '7105263120',
    'group_chat': '447916991875@c.us'
}

# Global data storage (in production, use a database)
app_data = {
    'cards_needing_updates': [],
    'update_request_counts': {},
    'analytics_data': {},
    'settings': {
        'auto_schedule': False,
        'schedule_time': '09:00',
        'schedule_days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
    },
    'speaker_analyses': [],
    'recurring_tasks': [],
    'demo_data': {
        'sample_transcript': """
John: Good morning everyone. Let's start with our updates. Sarah, how's the progress on the WordPress site?

Sarah: The WordPress site is going well. I've been working on the main landing page and we should have the initial version ready for review by Friday.

Mike: Great! What about the task for reaching out to onboarded clients?

Sarah: Yes, I've been working on that too. The reach out task is about 60% complete.

John: Perfect. Any blockers on the Center Name projects?

Mike: Actually yes. For the Vitality Energy Healing project, I'm waiting for approval on the logo design.
"""
    }
}

# Initialize Trello client
trello_client = None
try:
    trello_client = TrelloClient(
        api_key=os.environ.get('TRELLO_API_KEY'),
        api_secret=os.environ.get('TRELLO_API_SECRET'),
        token=os.environ.get('TRELLO_TOKEN')
    )
except Exception as e:
    print(f"Warning: Trello client initialization failed: {e}")

# ===== MAIN ROUTES =====

@app.route('/')
def index():
    """Main dashboard with app selection."""
    return render_template('dashboard.html')

@app.route('/google-meet')
def google_meet_app():
    """Google Meet to Trello AI app."""
    return render_template('google_meet_app.html')

@app.route('/team-tracker')
def team_tracker_app():
    """Team Update Tracker app."""
    return render_template('team_tracker.html', 
                         cards=app_data['cards_needing_updates'],
                         team_members=TEAM_MEMBERS,
                         settings=app_data['settings'])

# ===== UTILITY FUNCTIONS =====

def extract_google_doc_id(url):
    """Extract document ID from Google Docs URL."""
    pattern = r'/document/d/([a-zA-Z0-9-_]+)'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_google_doc_text(doc_id):
    """Extract text from Google Docs using export URL."""
    try:
        export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
        response = requests.get(export_url, timeout=30)
        
        if response.status_code == 200:
            text = response.text
            transcript_indicators = ['transcript', ':', 'said', 'meeting', 'discussion']
            
            if any(indicator.lower() in text.lower() for indicator in transcript_indicators):
                return text
            else:
                return None
        else:
            return None
    except Exception as e:
        print(f"Error fetching Google Doc: {e}")
        return None

def send_whatsapp_message(chat_id, message):
    """Send WhatsApp message via Green API."""
    try:
        # This is a placeholder - implement your actual Green API call here
        print(f"Sending message to {chat_id}: {message}")
        return True
    except Exception as e:
        print(f"Error sending WhatsApp message: {e}")
        return False

# ===== GOOGLE MEET APP API ROUTES =====

@app.route('/api/process-transcript', methods=['POST'])
def process_transcript():
    """Process Google Docs transcript (existing functionality)."""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'success': False, 'error': 'No URL provided'})
        
        doc_id = extract_google_doc_id(url)
        if not doc_id:
            return jsonify({'success': False, 'error': 'Invalid Google Docs URL'})
        
        # Get document text
        text = get_google_doc_text(doc_id)
        if not text:
            return jsonify({'success': False, 'error': 'Could not fetch document or not a transcript'})
        
        # Here you would add your existing transcript processing logic
        return jsonify({
            'success': True,
            'message': 'Transcript processed successfully',
            'doc_id': doc_id,
            'text_preview': text[:200] + '...' if len(text) > 200 else text
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/demo-analyze', methods=['POST'])
def demo_analyze():
    """Analyze demo transcript data."""
    try:
        # Use the demo data
        transcript = app_data['demo_data']['sample_transcript']
        
        if not SpeakerAnalyzer:
            return jsonify({
                'success': False, 
                'error': 'Speaker analysis module not available'
            })
        
        analyzer = SpeakerAnalyzer()
        result = analyzer.analyze_transcript(transcript)
        
        if result['success']:
            # Store analysis
            app_data['speaker_analyses'].append({
                'timestamp': datetime.now().isoformat(),
                'analysis': result,
                'source': 'demo'
            })
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/analyze-speakers', methods=['POST'])
def analyze_speakers():
    """Analyze speakers from provided transcript."""
    try:
        data = request.get_json()
        transcript = data.get('transcript', '').strip()
        
        if not transcript:
            return jsonify({'success': False, 'error': 'No transcript provided'})
        
        if not SpeakerAnalyzer:
            return jsonify({
                'success': False, 
                'error': 'Speaker analysis module not available'
            })
        
        analyzer = SpeakerAnalyzer()
        result = analyzer.analyze_transcript(transcript)
        
        if result['success']:
            # Store analysis
            app_data['speaker_analyses'].append({
                'timestamp': datetime.now().isoformat(),
                'analysis': result,
                'source': 'manual'
            })
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/generate-summary', methods=['POST'])
def generate_summary():
    """Generate meeting summary with action items."""
    try:
        data = request.get_json()
        transcript = data.get('transcript', '').strip()
        
        if not transcript:
            return jsonify({'success': False, 'error': 'No transcript provided'})
        
        # Extract action items and key points
        lines = transcript.split('\n')
        action_items = []
        key_points = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for action-oriented language
            if any(phrase in line.lower() for phrase in ['will do', "i'll", 'let me', 'i can', "i'll take", "i'll handle", 'next step']):
                action_items.append(line)
            
            # Look for key decision points
            if any(phrase in line.lower() for phrase in ['decided', 'agreed', 'conclusion', 'important', 'priority']):
                key_points.append(line)
        
        summary = {
            'action_items': action_items[:10],  # Limit to 10
            'key_points': key_points[:10],      # Limit to 10
            'meeting_duration': 'Estimated 15-30 minutes',
            'participants': list(set(re.findall(r'^([A-Za-z][A-Za-z\s]+?)\s*[-:]', transcript, re.MULTILINE))),
            'generated_at': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/send-whatsapp', methods=['POST'])
def send_individual_whatsapp():
    """Send individual WhatsApp messages with speaker analysis insights."""
    try:
        data = request.get_json()
        suggestions = data.get('suggestions', {})
        
        if not suggestions:
            return jsonify({'success': False, 'error': 'No suggestions provided'})
        
        messages_sent = 0
        
        for person, suggestion_list in suggestions.items():
            if person in TEAM_MEMBERS:
                phone_number = TEAM_MEMBERS[person]
                
                # Create personalized message
                message = f"""Hi {person}! 👋

Meeting Insights from JGV EEsystems AI:

"""
                
                for suggestion in suggestion_list[:3]:  # Limit to 3 suggestions
                    message += f"• {suggestion}\n"
                
                message += "\nKeep up the great work! 🚀"
                
                # Send message (placeholder for actual implementation)
                if send_whatsapp_message(phone_number, message):
                    messages_sent += 1
        
        return jsonify({
            'success': True,
            'messages_sent': messages_sent,
            'total_recipients': len(suggestions)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ===== TEAM TRACKER APP API ROUTES =====

@app.route('/api/scan-cards', methods=['POST'])
def scan_cards():
    """Scan Trello cards for assignments and recent comments."""
    try:
        if not trello_client:
            return jsonify({'success': False, 'error': 'Trello client not initialized'})
        
        # Get boards (you'll need to specify your board IDs)
        boards = trello_client.list_boards()
        cards_needing_updates = []
        
        for board in boards:
            cards = board.list_cards()
            
            for card in cards:
                # Check if card has assigned members
                if card.member_ids:
                    # Get card members
                    members = [member.full_name for member in card.members]
                    
                    # Check recent comments
                    comments = card.comments
                    last_comment_date = None
                    
                    if comments:
                        # Get the most recent comment
                        last_comment = max(comments, key=lambda x: x['date'])
                        last_comment_date = datetime.fromisoformat(last_comment['date'].replace('Z', '+00:00'))
                    
                    # Check if update is needed (no comment in last 24 hours)
                    needs_update = False
                    if not last_comment_date:
                        needs_update = True
                    else:
                        time_since_comment = datetime.now() - last_comment_date.replace(tzinfo=None)
                        needs_update = time_since_comment > timedelta(hours=24)
                    
                    if needs_update:
                        cards_needing_updates.append({
                            'id': card.id,
                            'name': card.name,
                            'url': card.url,
                            'assigned_members': members,
                            'last_comment_date': last_comment_date.isoformat() if last_comment_date else None,
                            'days_since_comment': (datetime.now() - last_comment_date.replace(tzinfo=None)).days if last_comment_date else 999,
                            'board_name': board.name
                        })
        
        app_data['cards_needing_updates'] = cards_needing_updates
        
        return jsonify({
            'success': True,
            'cards_found': len(cards_needing_updates),
            'cards': cards_needing_updates
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/send-updates', methods=['POST'])
def send_update_requests():
    """Send WhatsApp update requests to selected team members."""
    try:
        data = request.get_json()
        selected_cards = data.get('selected_cards', [])
        
        if not selected_cards:
            return jsonify({'success': False, 'error': 'No cards selected'})
        
        messages_sent = 0
        unassigned_cards = []
        
        for card_id in selected_cards:
            # Find the card
            card = next((c for c in app_data['cards_needing_updates'] if c['id'] == card_id), None)
            if not card:
                continue
            
            if not card['assigned_members']:
                unassigned_cards.append(card)
                continue
            
            # Send message to each assigned member
            for member_name in card['assigned_members']:
                if member_name in TEAM_MEMBERS:
                    phone_number = TEAM_MEMBERS[member_name]
                    
                    # Create update request message
                    message = f"""Hello {member_name}, This is the JGV EEsystems AI Trello bot

Here are the tasks today that you are assigned to and have not had a comment recently:

• {card['name']}
{card['url']}

Please click the link to open Trello and write a comment. If there is an issue, please contact James in the EEsystems group chat.

Thanks"""
                    
                    # Send WhatsApp message via Green API
                    if send_whatsapp_message(phone_number, message):
                        messages_sent += 1
                        
                        # Track request count
                        key = f"{card_id}_{member_name}"
                        app_data['update_request_counts'][key] = app_data['update_request_counts'].get(key, 0) + 1
        
        # Handle unassigned cards
        if unassigned_cards:
            unassigned_list = "\n".join([f"• {card['name']}: {card['url']}" for card in unassigned_cards])
            group_message = f"""⚠️ URGENT: Unassigned Tasks Requiring Attention

The following cards need to be assigned immediately:
{unassigned_list}

Please assign these tasks as soon as possible."""
            
            send_whatsapp_message(GREEN_API_CONFIG['group_chat'], group_message)
        
        return jsonify({
            'success': True,
            'messages_sent': messages_sent,
            'unassigned_cards': len(unassigned_cards)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/settings', methods=['GET', 'POST'])
def manage_settings():
    """Manage app settings."""
    if request.method == 'GET':
        return jsonify(app_data['settings'])
    
    try:
        data = request.get_json()
        app_data['settings'].update(data)
        
        # If auto-schedule is enabled, set up the scheduler
        if app_data['settings']['auto_schedule']:
            setup_scheduler()
        
        return jsonify({'success': True, 'settings': app_data['settings']})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/analytics')
def get_analytics():
    """Get team performance analytics."""
    try:
        # Calculate analytics
        analytics = {
            'total_cards_tracked': len(app_data['cards_needing_updates']),
            'update_requests_sent': sum(app_data['update_request_counts'].values()),
            'team_performance': {},
            'response_rates': {}
        }
        
        # Calculate team member performance
        for member, phone in TEAM_MEMBERS.items():
            member_requests = sum(1 for key in app_data['update_request_counts'].keys() if member in key)
            analytics['team_performance'][member] = {
                'requests_sent': member_requests,
                'assigned_cards': len([c for c in app_data['cards_needing_updates'] if member in c.get('assigned_members', [])])
            }
        
        return jsonify(analytics)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ===== SCHEDULER FUNCTIONS =====

def setup_scheduler():
    """Set up automated scanning schedule."""
    schedule.clear()
    
    schedule_time = app_data['settings']['schedule_time']
    schedule_days = app_data['settings']['schedule_days']
    
    for day in schedule_days:
        getattr(schedule.every(), day.lower()).at(schedule_time).do(automated_scan)

def automated_scan():
    """Automated card scanning and update sending."""
    with app.app_context():
        # Trigger card scan
        scan_cards()
        
        # Send updates for all cards needing updates
        if app_data['cards_needing_updates']:
            card_ids = [card['id'] for card in app_data['cards_needing_updates']]
            send_update_requests({'selected_cards': card_ids})

def run_scheduler():
    """Run the scheduler in a separate thread."""
    while True:
        schedule.run_pending()
        time.sleep(60)

# ===== APPLICATION STARTUP =====

if __name__ == '__main__':
    print("Starting Multi-App Web Interface with AI Features...")
    print(f"AI modules available: SpeakerAnalyzer={SpeakerAnalyzer is not None}, RecurringTaskTracker={RecurringTaskTracker is not None}")
    
    # Start scheduler thread if auto-schedule is enabled
    if app_data['settings']['auto_schedule']:
        scheduler_thread = Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
    
    app.run(debug=True, host='0.0.0.0', port=5000)