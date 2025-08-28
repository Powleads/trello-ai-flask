#!/usr/bin/env python3
"""
Complete Web App - With Google Docs reading and Trello commenting
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
from custom_trello import CustomTrelloClient
from message_tracker import MessageTracker
from gmail_tracker import GmailTracker, GmailScheduler, initialize_gmail_tracker
from gmail_oauth import gmail_oauth
from production_db import get_production_db
from google_meet_analytics import google_meet_analytics
from enhanced_team_tracker import enhanced_team_tracker
from team_tracker_db import team_tracker_bp
from team_tracker_v3_routes import team_tracker_v3_bp

# Import AI modules
try:
    from speaker_analysis import SpeakerAnalyzer
    print("Speaker analysis module loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import speaker analysis: {e}")
    SpeakerAnalyzer = None

try:
    from recurring_task_tracker import RecurringTaskTracker
    print("Recurring task tracker module loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import recurring task tracker: {e}")
    RecurringTaskTracker = None

try:
    from database import DatabaseManager
    print("Database module loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import database module: {e}")
    DatabaseManager = None

# Load environment
load_dotenv()

# Initialize production database
production_db = get_production_db()

# Reminder Tracking System
REMINDER_TRACKING_FILE = 'reminder_tracking.json'

def load_reminder_tracking():
    """Load reminder tracking data from JSON file."""
    try:
        if os.path.exists(REMINDER_TRACKING_FILE):
            with open(REMINDER_TRACKING_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading reminder tracking: {e}")
    return {}

def save_reminder_tracking(data):
    """Save reminder tracking data to JSON file."""
    try:
        with open(REMINDER_TRACKING_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving reminder tracking: {e}")

def increment_reminder_count(card_id, assigned_user):
    """Increment reminder count for a card and user."""
    tracking_data = load_reminder_tracking()
    key = f"{card_id}_{assigned_user}"
    
    if key not in tracking_data:
        tracking_data[key] = {
            'card_id': card_id,
            'assigned_user': assigned_user,
            'reminder_count': 0,
            'first_reminder_date': datetime.now().isoformat(),
            'last_reminder_date': None,
            'status': 'active',
            'escalated': False
        }
    
    tracking_data[key]['reminder_count'] += 1
    tracking_data[key]['last_reminder_date'] = datetime.now().isoformat()
    
    # Mark as escalated if 3+ reminders
    if tracking_data[key]['reminder_count'] >= 3:
        tracking_data[key]['status'] = 'escalated'
        tracking_data[key]['escalated'] = True
    
    save_reminder_tracking(tracking_data)
    return tracking_data[key]

def get_reminder_status(card_id, assigned_user):
    """Get reminder status for a card and user."""
    tracking_data = load_reminder_tracking()
    key = f"{card_id}_{assigned_user}"
    return tracking_data.get(key, {
        'reminder_count': 0,
        'escalated': False,
        'status': 'new'
    })

def mark_card_resolved(card_id, assigned_user):
    """Mark a card as resolved (user finally updated)."""
    tracking_data = load_reminder_tracking()
    key = f"{card_id}_{assigned_user}"
    
    if key in tracking_data:
        tracking_data[key]['status'] = 'resolved'
        tracking_data[key]['resolved_date'] = datetime.now().isoformat()
        save_reminder_tracking(tracking_data)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Register blueprints
app.register_blueprint(google_meet_analytics)
app.register_blueprint(team_tracker_bp)
app.register_blueprint(team_tracker_v3_bp)

# Initialize team tracker database if needed
try:
    from init_team_tracker import init_database
    init_database()
except Exception as e:
    print(f"Warning: Could not initialize team tracker database: {e}")

# Initialize message tracker and Gmail tracker
message_tracker = MessageTracker("message_tracker.db")
# Initialize Gmail tracker with production support
gmail_tracker = initialize_gmail_tracker()

# Initialize Gmail OAuth handler
gmail_oauth.init_app(app)
gmail_scheduler = None

# Production initialization will happen at the end of the file

# Enhanced Security Authentication System
from functools import wraps
import bcrypt
import hashlib
from collections import defaultdict

# Secure session configuration
app.config.update(
    SESSION_COOKIE_SECURE=True,  # HTTPS only
    SESSION_COOKIE_HTTPONLY=True,  # No JS access
    SESSION_COOKIE_SAMESITE='Lax',  # CSRF protection
    PERMANENT_SESSION_LIFETIME=timedelta(hours=4),  # Auto logout
)

# Login credentials with hashed password storage
LOGIN_USERNAME = os.environ.get('LOGIN_USERNAME', 'admin@justgoingviral.com')
LOGIN_PASSWORD_RAW = os.environ.get('LOGIN_PASSWORD', '2Talon3Gemm4')

# Generate secure password hash (do this once)
LOGIN_PASSWORD_HASH = bcrypt.hashpw(LOGIN_PASSWORD_RAW.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Rate limiting for brute force protection
login_attempts = defaultdict(list)
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 300  # 5 minutes

def is_rate_limited(ip_address):
    """Check if IP is rate limited."""
    now = time.time()
    attempts = login_attempts[ip_address]
    
    # Remove old attempts
    login_attempts[ip_address] = [attempt for attempt in attempts if now - attempt < LOCKOUT_DURATION]
    
    return len(login_attempts[ip_address]) >= MAX_LOGIN_ATTEMPTS

def record_failed_attempt(ip_address):
    """Record failed login attempt."""
    login_attempts[ip_address].append(time.time())

def verify_password(provided_password, stored_hash):
    """Securely verify password using bcrypt with timing attack protection."""
    try:
        # Always perform hashing to prevent timing attacks
        return bcrypt.checkpw(provided_password.encode('utf-8'), stored_hash.encode('utf-8'))
    except Exception:
        # Timing attack protection - still do some work
        bcrypt.hashpw(b'dummy', bcrypt.gensalt())
        return False

def login_required(f):
    """Enhanced decorator with session security."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or not session.get('username'):
            session.clear()  # Clear potentially corrupted session
            return redirect(url_for('login'))
        
        # Refresh session for active users
        session.permanent = True
        
        return f(*args, **kwargs)
    return decorated_function

# Team member data - REMOVED, now using database-driven team management
# All team members are loaded from the database via enhanced_team_tracker
TEAM_MEMBERS = {}  # Empty - will be populated from database

# Initialize database
db = DatabaseManager() if DatabaseManager else None

# Initialize V3 database tables
try:
    from database_extend_v3 import extend_database
    extend_database()
    print("[V3] Database tables initialized successfully")
except Exception as e:
    print(f"[V3] Warning: Could not initialize V3 database tables: {e}")

# Global data storage
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
    'recurring_tasks': []
}

# Initialize Trello client
trello_client = None
try:
    trello_client = CustomTrelloClient(
        api_key=os.environ.get('TRELLO_API_KEY'),
        token=os.environ.get('TRELLO_TOKEN')
    )
    print("Custom Trello client initialized successfully")
except Exception as e:
    print(f"Warning: Trello client initialization failed: {e}")

# ===== AUTHENTICATION ROUTES =====

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Get client IP for rate limiting
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    if client_ip:
        client_ip = client_ip.split(',')[0].strip()
    
    if request.method == 'POST':
        # Check rate limiting first
        if is_rate_limited(client_ip):
            return render_template('login.html', 
                error='Too many failed attempts. Please try again in 5 minutes.'), 429
        
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Input validation
        if not username or not password:
            record_failed_attempt(client_ip)
            return render_template('login.html', error='Please enter both username and password.')
        
        # Secure credential verification
        username_valid = username.lower() == LOGIN_USERNAME.lower()
        password_valid = verify_password(password, LOGIN_PASSWORD_HASH)
        
        if username_valid and password_valid:
            # Clear any previous failed attempts
            if client_ip in login_attempts:
                del login_attempts[client_ip]
            
            # Create secure session
            session.permanent = True
            session['logged_in'] = True
            session['username'] = username
            session['login_time'] = time.time()
            session['client_ip'] = client_ip  # Session hijacking protection
            
            print(f"Successful login: {username} from {client_ip}")
            return redirect(url_for('index'))
        else:
            # Record failed attempt
            record_failed_attempt(client_ip)
            print(f"Failed login attempt: {username} from {client_ip}")
            
            # Generic error message to prevent username enumeration
            return render_template('login.html', error='Invalid credentials. Please try again.')
    
    # If already logged in, redirect to dashboard
    if session.get('logged_in'):
        # Verify session integrity
        if session.get('client_ip') == client_ip:
            return redirect(url_for('index'))
        else:
            # Potential session hijacking - clear session
            session.clear()
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ===== MAIN ROUTES =====

@app.route('/')
@login_required
def index():
    return render_template('dashboard.html')

@app.route('/google-meet')
@login_required
def google_meet_app():
    return render_template('google_meet_analytics.html')

@app.route('/team-tracker')
@login_required
def team_tracker_app():
    # Redirect to enhanced version
    return render_template('team_tracker_enhanced.html')

@app.route('/team-tracker/legacy')
@login_required  
def legacy_team_tracker_app():
    """Legacy team tracker page"""
    return render_template('team_tracker.html', 
                         cards=app_data['cards_needing_updates'],
                         team_members=TEAM_MEMBERS,
                         settings=app_data['settings'])

@app.route('/gmail-tracker')
@login_required
def gmail_tracker_app():
    return render_template('gmail_tracker.html')

@app.route('/onboarding-analysis')
@login_required
def onboarding_analysis_app():
    return render_template('onboarding_analysis.html')

@app.route('/api/send-selected-emails', methods=['POST'])
@login_required
def send_selected_emails():
    """Send WhatsApp notifications for selected emails with duplicate tracking"""
    try:
        data = request.get_json()
        selected_emails = data.get('emails', [])
        
        if not selected_emails:
            return jsonify({'success': False, 'error': 'No emails provided'})
        
        if not gmail_tracker:
            return jsonify({'success': False, 'error': 'Gmail tracker not initialized'})
        
        sent_count = 0
        skipped_count = 0
        errors = []
        
        for email in selected_emails:
            try:
                email_id = email.get('id')
                if not email_id:
                    continue
                
                # Check if already sent today
                if production_db.is_email_sent_today(email_id):
                    print(f"[MANUAL] Skipping email {email_id} - already sent today")
                    skipped_count += 1
                    continue
                
                # Process and send the email
                analysis = gmail_tracker.categorize_email_with_ai(
                    email['subject'],
                    email.get('content', ''),
                    email['sender'],
                    email
                )
                
                # Send WhatsApp notifications
                success = gmail_tracker.send_whatsapp_notifications(email, analysis)
                
                if success:
                    # Mark as sent today
                    production_db.mark_email_sent_today(email_id)
                    sent_count += 1
                    print(f"[MANUAL] Successfully sent WhatsApp for email: {email['subject'][:50]}...")
                else:
                    errors.append(f"Failed to send WhatsApp for: {email['subject'][:30]}...")
                    
            except Exception as e:
                errors.append(f"Error processing email {email.get('subject', 'Unknown')[:30]}...: {str(e)}")
                print(f"[MANUAL] Error processing email: {e}")
        
        result = {
            'success': True,
            'sent_count': sent_count,
            'skipped_count': skipped_count,
            'total_processed': len(selected_emails)
        }
        
        if errors:
            result['errors'] = errors
            result['message'] = f'Sent {sent_count}, skipped {skipped_count}, {len(errors)} errors'
        else:
            result['message'] = f'Successfully sent {sent_count} notifications' + (f', skipped {skipped_count} already sent today' if skipped_count > 0 else '')
        
        return jsonify(result)
        
    except Exception as e:
        print(f"[MANUAL] ERROR in send_selected_emails: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/upload-csv-rules', methods=['POST'])
@login_required
def upload_csv_rules():
    """Create multiple watch rules from CSV upload"""
    try:
        data = request.get_json()
        rules = data.get('rules', [])
        
        if not rules:
            return jsonify({'success': False, 'error': 'No rules provided'})
        
        # Get existing watch rules
        watch_rules_data = production_db.get_watch_rules()
        existing_rules = watch_rules_data.get('watchRules', []) if watch_rules_data else []
        
        created_count = 0
        
        for rule in rules:
            # Validate rule structure
            if not rule.get('subject') and not rule.get('sender') and not rule.get('body'):
                continue  # Skip empty rules
            
            # Add the new rule
            new_rule = {
                'subject': rule.get('subject', ''),
                'sender': rule.get('sender', ''),
                'body': rule.get('body', ''),
                'category': rule.get('category', 'other'),
                'assignees': rule.get('assignees', []),
                'notifications': 'individual',  # Default notification setting
                'isActive': True
            }
            
            existing_rules.append(new_rule)
            created_count += 1
            
            print(f"[CSV] Created rule: {rule.get('subject') or rule.get('sender') or rule.get('body')} -> {rule.get('category')}")
        
        if created_count == 0:
            return jsonify({'success': False, 'error': 'No valid rules found in CSV data'})
        
        # Save updated rules back to database
        updated_settings = {
            'enableAutoScan': watch_rules_data.get('enableAutoScan', False) if watch_rules_data else False,
            'scanInterval': watch_rules_data.get('scanInterval', 30) if watch_rules_data else 30,
            'watchRules': existing_rules
        }
        
        success = production_db.save_watch_rules(updated_settings)
        
        if success:
            return jsonify({
                'success': True,
                'created_count': created_count,
                'message': f'Successfully created {created_count} watch rules from CSV'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to save rules to database'})
        
    except Exception as e:
        print(f"[CSV] ERROR in upload_csv_rules: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

# ===== AUTOMATED SCHEDULER =====

import threading
import time
from datetime import datetime, timedelta

def reset_reminder_count(card_id, assigned_user):
    """Reset reminder count when user comments on card."""
    tracking_data = load_reminder_tracking()
    key = f"{card_id}_{assigned_user}"
    
    if key in tracking_data:
        tracking_data[key]['reminder_count'] = 0
        tracking_data[key]['escalated'] = False
        tracking_data[key]['status'] = 'active'
        tracking_data[key]['last_comment_date'] = datetime.now().isoformat()
        save_reminder_tracking(tracking_data)
        print(f"Reset reminder count for {assigned_user} on card {card_id}")
        return tracking_data[key]
    
    return None

def automated_daily_scan():
    """Automated daily scanner that runs in background thread."""
    while True:
        try:
            # Wait for next scan time (check every 6 hours, scan at 9 AM)
            now = datetime.now()
            target_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
            
            # If it's past 9 AM today, schedule for tomorrow
            if now.time() > target_time.time():
                target_time += timedelta(days=1)
            
            sleep_seconds = (target_time - now).total_seconds()
            print(f"[AUTO] Next automated scan scheduled for: {target_time}")
            time.sleep(sleep_seconds)
            
            # Perform automated scan
            print("[AUTO] AUTOMATED SCAN: Starting daily team tracker scan...")
            perform_automated_scan()
            
        except Exception as e:
            print(f"Error in automated scanner: {e}")
            time.sleep(3600)  # Wait 1 hour before retrying

def perform_automated_scan():
    """Perform the actual automated scan and send reminders."""
    try:
        # Scan for overdue cards
        scan_result = scan_trello_cards_for_updates()
        if not scan_result.get('success'):
            print(f"Automated scan failed: {scan_result.get('error')}")
            return
        
        overdue_cards = scan_result.get('cards_needing_updates', [])
        if not overdue_cards:
            print("[AUTO] No overdue cards found in automated scan.")
            return
        
        print(f"[AUTO] Found {len(overdue_cards)} overdue cards in automated scan.")
        
        # Group cards by user
        user_cards = {}
        for card in overdue_cards:
            assigned_user = card.get('assigned_user')
            assigned_whatsapp = card.get('assigned_whatsapp')
            
            if not assigned_user or not assigned_whatsapp:
                continue
            
            if assigned_user not in user_cards:
                user_cards[assigned_user] = []
            user_cards[assigned_user].append(card)
        
        # Send reminders and check for escalations
        group_escalations = []
        
        for assigned_user, cards in user_cards.items():
            # Check if any cards need escalation
            escalated_cards = []
            regular_cards = []
            
            for card in cards:
                reminder_status = get_reminder_status(card['id'], assigned_user)
                if reminder_status['escalated'] or reminder_status['reminder_count'] >= 3:
                    escalated_cards.append(card)
                    group_escalations.append({
                        'card_name': card['name'],
                        'assigned_user': assigned_user,
                        'reminder_count': reminder_status['reminder_count'],
                        'card_url': card['url'],
                        'hours_since_update': card.get('hours_since_assigned_update', 0) or 0
                    })
                else:
                    regular_cards.append(card)
            
            # Send regular reminders for non-escalated cards
            if regular_cards:
                send_automated_reminder(assigned_user, regular_cards)
        
        # Send group escalation if needed
        if group_escalations:
            send_group_escalation(group_escalations)
        
    except Exception as e:
        print(f"Error in automated scan: {e}")

def send_automated_reminder(assigned_user, cards):
    """Send automated reminder to user."""
    try:
        whatsapp_number = TEAM_MEMBERS.get(assigned_user)
        if not whatsapp_number:
            print(f"[AUTO] No WhatsApp number for {assigned_user}")
            return
        
        # Create message
        message = f"""🤖 AUTOMATED REMINDER: Hey {assigned_user}, these cards need updates (over 24 hours). Please comment with your progress or these will escalate to the main group after 3 reminders.

📋 Cards requiring updates ({len(cards)}):

"""
        
        for i, card in enumerate(cards, 1):
            hours = card.get('hours_since_assigned_update', 0)
            reminder_status = get_reminder_status(card['id'], assigned_user)
            reminder_count = reminder_status['reminder_count']
            
            if hours > 72:
                urgency_icon = "🔴"
            elif hours > 48:
                urgency_icon = "🟡"
            else:
                urgency_icon = "🟢"
            
            days = int(hours / 24)
            reminder_text = f" (Reminder #{reminder_count + 1})" if reminder_count > 0 else ""
            
            message += f"{urgency_icon} {i}. *{card['name']}*{reminder_text}\n"
            message += f"   ⏰ {days} days without update\n"
            message += f"   🔗 {card['url']}\n\n"
        
        message += "Please update these cards with your current progress. Thanks! 🚀\n\n- JGV EEsystems Auto-Tracker"
        
        # Send via Green API
        green_api_instance = os.environ.get('GREEN_API_INSTANCE')
        green_api_token = os.environ.get('GREEN_API_TOKEN')
        
        if not green_api_instance or not green_api_token:
            print("[AUTO] Green API credentials not configured for automated reminders")
            return
        
        green_api_url = f"https://api.green-api.com/waInstance{green_api_instance}/sendMessage/{green_api_token}"
        
        payload = {
            "chatId": whatsapp_number,
            "message": message
        }
        
        response = requests.post(green_api_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            # Increment reminder count for each card
            for card in cards:
                reminder_data = increment_reminder_count(card['id'], assigned_user)
                print(f"[AUTO] Incremented reminder count for {assigned_user} on card {card['name']}: {reminder_data['reminder_count']}")
            
            print(f"[AUTO] Sent reminder to {assigned_user} for {len(cards)} cards")
        else:
            print(f"[AUTO] Failed to send reminder to {assigned_user}: {response.status_code}")
        
    except Exception as e:
        print(f"Error sending automated reminder to {assigned_user}: {e}")

def send_group_escalation(escalated_cards):
    """Send escalation message to group chat."""
    try:
        group_chat_id = os.environ.get('WHATSAPP_GROUP_CHAT_ID', '120363401025025313@g.us')
        
        escalation_message = """🚨 AUTOMATED ESCALATION: Cards Requiring Immediate Attention 🚨

The following team members have not responded to 3+ reminders about their assigned cards:

"""
        
        # Group by user
        escalated_by_user = {}
        for card in escalated_cards:
            user = card['assigned_user']
            if user not in escalated_by_user:
                escalated_by_user[user] = []
            escalated_by_user[user].append(card)
        
        for user, user_cards in escalated_by_user.items():
            escalation_message += f"\n👤 *{user}* ({len(user_cards)} cards):\n"
            for card in user_cards:
                days = int(card['hours_since_update'] / 24)
                escalation_message += f"   🔴 {card['card_name']} ({days} days, {card['reminder_count']} reminders)\n"
                escalation_message += f"       🔗 {card['card_url']}\n"
        
        escalation_message += "\n⚠️ Please follow up with these team members immediately or reassign these cards.\n\n- JGV EEsystems Auto-Tracker"
        
        # Send to group
        green_api_instance = os.environ.get('GREEN_API_INSTANCE')
        green_api_token = os.environ.get('GREEN_API_TOKEN')
        
        if not green_api_instance or not green_api_token:
            print("[AUTO] Green API credentials not configured for group escalation")
            return
        
        green_api_url = f"https://api.green-api.com/waInstance{green_api_instance}/sendMessage/{green_api_token}"
        
        payload = {
            "chatId": group_chat_id,
            "message": escalation_message
        }
        
        response = requests.post(green_api_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            print(f"[AUTO] Sent group escalation for {len(escalated_cards)} cards")
        else:
            print(f"[AUTO] Failed to send group escalation: {response.status_code}")
        
    except Exception as e:
        print(f"Error sending group escalation: {e}")

# Start automated scanner in background thread
auto_scanner_thread = None

def start_automated_scanner():
    """Start the automated scanner thread."""
    global auto_scanner_thread
    if auto_scanner_thread is None or not auto_scanner_thread.is_alive():
        auto_scanner_thread = threading.Thread(target=automated_daily_scan, daemon=True)
        auto_scanner_thread.start()
        print("[AUTO] Automated daily scanner started")

# ===== UTILITY FUNCTIONS =====

def extract_google_doc_id(url):
    """Extract document ID from Google Docs URL."""
    pattern = r'/document/d/([a-zA-Z0-9-_]+)'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_google_doc_text(doc_id):
    """Extract text from Google Docs using proper Google Drive API authentication."""
    try:
        print(f"Attempting to fetch Google Doc: {doc_id}")
        
        # Try to use the Google Drive integration first (only if properly configured)
        google_client_id = os.getenv('GOOGLE_CLIENT_ID')
        if google_client_id and google_client_id != 'your_google_client_id_here':
            try:
                from src.integrations.google_drive import GoogleDriveClient
                
                # Initialize Google Drive client with proper authentication
                drive_client = GoogleDriveClient(
                    credentials_file=os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json'),
                    token_file=os.getenv('GOOGLE_TOKEN_FILE', 'token.pickle')
                )
                
                # Use the Google Drive API to get document content
                text = drive_client.get_document_text(doc_id)
                if text and text.strip():
                    try:
                        print(f"✅ Retrieved text from Google Drive API: {len(text)} chars")
                    except UnicodeEncodeError:
                        print(f"Retrieved text from Google Drive API: {len(text)} chars")
                    return text
                else:
                    print("Google Drive API returned empty content")
                    
            except Exception as e:
                try:
                    print(f"❌ Google Drive API failed: {e}")
                except UnicodeEncodeError:
                    print(f"Google Drive API failed: [Unicode Error]")
        else:
            print("Google API credentials not configured, using fallback method only")
        
        # Fallback to public URL method (for publicly shared docs)
        print("Trying fallback public URL method...")
        export_urls = [
            f"https://docs.google.com/document/d/{doc_id}/export?format=txt",
            f"https://docs.google.com/document/u/0/d/{doc_id}/export?format=txt"
        ]
        
        for i, url in enumerate(export_urls):
            try:
                print(f"Trying fallback URL method {i+1}: {url}")
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
                print(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    # Handle encoding properly
                    response.encoding = 'utf-8'  # Ensure proper UTF-8 encoding
                    text = response.text
                    print(f"Retrieved text length: {len(text)}")
                    
                    # Clean text of problematic characters for Windows console
                    try:
                        # Test if text can be printed safely
                        safe_text_sample = text[:200].encode('ascii', errors='replace').decode('ascii')
                        print(f"Sample content: {safe_text_sample}...")
                    except:
                        print("Content contains special characters (safe processing)")
                    
                    # Check if it's actual content
                    if len(text) > 50 and not text.startswith('<!DOCTYPE'):
                        content_indicators = ['transcript', ':', 'said', 'meeting', 'discussion']
                        
                        if any(indicator.lower() in text.lower() for indicator in content_indicators) or len(text) > 200:
                            print("Valid transcript content detected via fallback")
                            return text
                        else:
                            print("Text found but doesn't appear to be transcript content")
                    else:
                        print("Response appears to be HTML error page or too short")
                else:
                    print(f"Failed with status code: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"Timeout on method {i+1}")
                continue
            except Exception as e:
                print(f"Error on method {i+1}: {e}")
                continue
        
        print("All methods failed")
        return None
        
    except Exception as e:
        # Safe print to handle Unicode characters in error messages
        try:
            print(f"Critical error fetching Google Doc: {e}")
        except UnicodeEncodeError:
            print(f"Critical error fetching Google Doc: [Unicode Error - Document may contain special characters]")
        return None

# ===== ENHANCED ASSIGNMENT DETECTION SYSTEM =====

def get_board_members_mapping():
    """Get all board members and create mapping to team members - using same board detection as scan_cards."""
    try:
        api_key = os.environ.get('TRELLO_API_KEY')
        token = os.environ.get('TRELLO_TOKEN')
        
        if not api_key or not token:
            print("  BOARD_MEMBERS: Missing Trello API credentials")
            return {}
        
        if not trello_client:
            print("  BOARD_MEMBERS: Trello client not available")
            return {}
        
        # Use SAME board detection logic as scan_cards function
        boards = trello_client.list_boards()
        eeinteractive_board = None
        
        for board in boards:
            if board.closed:
                continue
            if 'eeinteractive' in board.name.lower():
                eeinteractive_board = board
                break
        
        if not eeinteractive_board:
            print("  BOARD_MEMBERS: EEInteractive board not found")
            return {}
        
        board_id = eeinteractive_board.id
        print(f"  BOARD_MEMBERS: Using board '{eeinteractive_board.name}' (ID: {board_id})")
        
        # Get board members
        url = f"https://api.trello.com/1/boards/{board_id}/members"
        params = {
            'key': api_key,
            'token': token,
            'fields': 'id,fullName,username'
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            print(f"  BOARD_MEMBERS: API error {response.status_code}")
            return {}
        
        board_members = response.json()
        print(f"  BOARD_MEMBERS: Found {len(board_members)} board members")
        member_mapping = {}
        
        # Debug: Show all board members and team members
        print(f"  BOARD_MEMBERS: Available board members:")
        for member in board_members:
            member_name = member.get('fullName', '').strip()
            member_id = member.get('id', '')
            print(f"    - {member_name} (ID: {member_id})")
        
        print(f"  BOARD_MEMBERS: Team members to match:")
        for team_name, whatsapp in TEAM_MEMBERS.items():
            print(f"    - {team_name} -> {whatsapp}")
        
        # Create mapping from Trello member ID to team member info
        for member in board_members:
            member_name = member.get('fullName', '').strip()
            member_id = member.get('id', '')
            
            if not member_name or not member_id:
                continue
                
            # Match to our team members with name variations
            matched = False
            for team_name, whatsapp in TEAM_MEMBERS.items():
                if matched:
                    break
                    
                team_lower = team_name.lower()
                member_lower = member_name.lower()
                
                # Enhanced fuzzy matching with variations and word-based matching
                name_variations = [
                    team_lower,
                    team_lower.replace('ey', 'y'),  # Lancey -> Lancy
                    team_lower.replace('y', 'ey'),  # Lancy -> Lancey
                    team_lower.replace(' ', ''),    # Remove spaces
                ]
                
                print(f"  BOARD_MEMBERS: Checking '{member_name}' vs '{team_name}'")
                
                # Method 1: Direct variations matching
                for variation in name_variations:
                    if (variation in member_lower or 
                        member_lower in variation or
                        any(part in member_lower for part in variation.split() if len(part) > 2)):
                        member_mapping[member_id] = {
                            'team_name': team_name,
                            'trello_name': member_name,
                            'whatsapp': whatsapp
                        }
                        print(f"  BOARD_MEMBERS: ✅ MATCHED {member_name} ({member_id}) -> {team_name} (direct)")
                        matched = True
                        break
                
                # Method 2: Fuzzy word-based matching for full names
                if not matched:
                    member_words = member_lower.split()
                    team_words = team_lower.split()
                    
                    # Check if team name appears as first word or substring in member name
                    for team_word in team_words:
                        if len(team_word) > 2:  # Skip short words
                            for member_word in member_words:
                                if (team_word in member_word or 
                                    member_word in team_word or
                                    abs(len(team_word) - len(member_word)) <= 2):  # Allow 2 char difference
                                    # Additional fuzzy check for similar names
                                    similar_chars = sum(1 for a, b in zip(team_word, member_word) if a == b)
                                    if similar_chars >= max(3, len(team_word) - 2):  # Allow 2 char mismatch
                                        member_mapping[member_id] = {
                                            'team_name': team_name,
                                            'trello_name': member_name,
                                            'whatsapp': whatsapp
                                        }
                                        print(f"  BOARD_MEMBERS: ✅ MATCHED {member_name} ({member_id}) -> {team_name} (fuzzy)")
                                        matched = True
                                        break
                            if matched:
                                break
                
                if not matched:
                    print(f"  BOARD_MEMBERS: ❌ No match for '{member_name}' with '{team_name}'")
        
        print(f"  BOARD_MEMBERS: Final mapping has {len(member_mapping)} members")
        
        return member_mapping
        
    except Exception as e:
        print(f"Error getting board members: {e}")
        return {}

def get_card_checklists(card_id):
    """Read Trello card checklists to find assignments."""
    try:
        api_key = os.environ.get('TRELLO_API_KEY')
        token = os.environ.get('TRELLO_TOKEN')
        
        if not api_key or not token:
            print(f"  CHECKLISTS: Missing Trello API credentials")
            return []
        
        # Get board member mapping first
        member_mapping = get_board_members_mapping()
        
        # Get checklists for the card
        url = f"https://api.trello.com/1/cards/{card_id}/checklists"
        params = {
            'key': api_key,
            'token': token,
            'fields': 'name,checkItems'
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            print(f"  CHECKLISTS: API error {response.status_code}")
            return []
        
        checklists = response.json()
        assigned_members = []
        
        for checklist in checklists:
            checklist_name = checklist.get('name', '').lower()
            check_items = checklist.get('checkItems', [])
            
            # Look for assignment-related checklists - prioritize "assigned" checklist specifically
            if ('assigned' in checklist_name or 
                any(keyword in checklist_name for keyword in ['assign', 'team', 'member', 'responsible'])):
                print(f"  CHECKLISTS: Found assignment checklist: {checklist['name']}")
                
                for item in check_items:
                    item_text = item.get('name', '').lower()
                    item_state = item.get('state', 'incomplete')
                    
                    # Check if item contains team member names using board member mapping
                    for member_id, member_info in member_mapping.items():
                        team_name = member_info['team_name']
                        trello_name = member_info['trello_name']
                        whatsapp = member_info['whatsapp']
                        
                        # Skip admin and criselle
                        if team_name.lower() in ['admin', 'criselle']:
                            continue
                        
                        # Enhanced name matching - use both team name and Trello name variations
                        name_variations = [
                            team_name.lower(),
                            trello_name.lower(),
                            team_name.lower().replace('ey', 'y'),  # Lancey -> Lancy
                            team_name.lower().replace('y', 'ey'),  # Lancy -> Lancey
                            trello_name.lower().replace('ey', 'y'),
                            trello_name.lower().replace('y', 'ey'),
                        ]
                        
                        # Check if member is mentioned in checklist item
                        is_mentioned = (
                            any(variation in item_text for variation in name_variations) or
                            any(f"@{variation}" in item_text for variation in name_variations) or
                            member_id in item_text  # Check for Trello member ID
                        )
                        
                        if is_mentioned:
                            # Higher confidence for "assigned" checklist and checked items
                            confidence = 95 if 'assigned' in checklist_name else 90
                            if item_state == 'complete':
                                confidence += 5
                            
                            assigned_members.append({
                                'name': team_name,
                                'whatsapp': whatsapp,
                                'source': f"Checklist: {checklist['name']} - {item['name']} ({item_state})",
                                'confidence': confidence,
                                'member_id': member_id,
                                'trello_name': trello_name
                            })
                            print(f"  CHECKLISTS: Found {team_name} ({trello_name}) in checklist item: {item['name']} ({item_state})")
            
            # Also check regular checklists for team member mentions
            else:
                for item in check_items:
                    item_text = item.get('name', '').lower()
                    
                    for team_member, whatsapp in TEAM_MEMBERS.items():
                        member_lower = team_member.lower()
                        
                        if member_lower in ['admin', 'criselle']:
                            continue
                        
                        # Look for assignment patterns in any checklist item
                        assignment_patterns = [
                            f"@{member_lower}",
                            f"{member_lower} -",
                            f"{member_lower}:",
                            f"assigned to {member_lower}",
                            f"{member_lower} responsible",
                            f"{member_lower} handle"
                        ]
                        
                        if any(pattern in item_text for pattern in assignment_patterns):
                            assigned_members.append({
                                'name': team_member,
                                'whatsapp': whatsapp,
                                'source': f"Checklist item: {item['name']}",
                                'confidence': 85
                            })
                            print(f"  CHECKLISTS: Found {team_member} in item: {item['name']}")
        
        return assigned_members
        
    except Exception as e:
        print(f"  CHECKLISTS: Error reading checklists: {e}")
        return []

def get_last_non_admin_commenter(card_id):
    """Find the last person to comment on a card (excluding admin/criselle)."""
    try:
        api_key = os.environ.get('TRELLO_API_KEY')
        token = os.environ.get('TRELLO_TOKEN')
        
        if not api_key or not token:
            return None
        
        # Get board member mapping first
        member_mapping = get_board_members_mapping()
        
        # Get recent comments
        url = f"https://api.trello.com/1/cards/{card_id}/actions"
        params = {
            'filter': 'commentCard',
            'limit': 50,  # Increased limit to find more comments
            'key': api_key,
            'token': token
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return None
        
        comments = response.json()
        
        for comment in comments:
            commenter_id = comment.get('memberCreator', {}).get('id', '')
            commenter_name = comment.get('memberCreator', {}).get('fullName', '').lower()
            
            # Skip admin and criselle by name
            if 'admin' in commenter_name or 'criselle' in commenter_name:
                continue
            
            # First try to match by Trello member ID (most accurate)
            if commenter_id in member_mapping:
                member_info = member_mapping[commenter_id]
                return {
                    'name': member_info['team_name'],
                    'whatsapp': member_info['whatsapp'],
                    'source': f"Last commenter: {member_info['trello_name']} (ID matched)",
                    'confidence': 95,  # High confidence for ID match
                    'comment_date': comment.get('date', ''),
                    'member_id': commenter_id,
                    'trello_name': member_info['trello_name']
                }
            
            # Fallback to name matching if ID not found
            for member_id, member_info in member_mapping.items():
                team_name = member_info['team_name']
                trello_name = member_info['trello_name']
                
                name_variations = [
                    team_name.lower(),
                    trello_name.lower(),
                    team_name.lower().replace('ey', 'y'),
                    team_name.lower().replace('y', 'ey'),
                    trello_name.lower().replace('ey', 'y'),
                    trello_name.lower().replace('y', 'ey'),
                ]
                
                if any(variation in commenter_name or commenter_name in variation 
                       for variation in name_variations):
                    return {
                        'name': team_name,
                        'whatsapp': member_info['whatsapp'],
                        'source': f"Last commenter: {trello_name} (name matched)",
                        'confidence': 80,  # Lower confidence for name match
                        'comment_date': comment.get('date', ''),
                        'member_id': commenter_id,
                        'trello_name': trello_name
                    }
        
        return None
        
    except Exception as e:
        print(f"  LAST COMMENTER: Error: {e}")
        return None

def extract_transcript_assignments(transcript_text, card_name):
    """AI-powered assignment detection from meeting conversations."""
    try:
        assignments = []
        lines = transcript_text.split('\n')
        card_name_lower = card_name.lower()
        
        # Look for assignment patterns around card mentions
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Check if this line or nearby lines mention the card
            card_mentioned = any(word in line.lower() for word in card_name_lower.split() if len(word) > 3)
            
            if card_mentioned:
                # Look in current line and next few lines for assignment patterns
                context_lines = lines[max(0, i-2):min(len(lines), i+5)]
                context_text = ' '.join(context_lines).lower()
                
                # Assignment patterns to look for
                for team_member, whatsapp in TEAM_MEMBERS.items():
                    member_lower = team_member.lower()
                    
                    # Skip admin and criselle
                    if member_lower in ['admin', 'criselle']:
                        continue
                    
                    assignment_patterns = [
                        f"{member_lower}, can you",
                        f"{member_lower}, please",
                        f"{member_lower}, take",
                        f"{member_lower} can handle",
                        f"{member_lower} will work on",
                        f"{member_lower} is assigned",
                        f"assign this to {member_lower}",
                        f"assign {member_lower}",
                        f"{member_lower} should",
                        f"{member_lower}, you",
                        f"@{member_lower}"
                    ]
                    
                    for pattern in assignment_patterns:
                        if pattern in context_text:
                            assignments.append({
                                'name': team_member,
                                'whatsapp': whatsapp,
                                'source': f"Transcript assignment pattern: '{pattern}'",
                                'confidence': 80,
                                'context': context_text[:200]
                            })
                            print(f"  TRANSCRIPT: Found assignment '{pattern}' for {team_member}")
                            break
        
        # Remove duplicates (same person assigned multiple times)
        unique_assignments = {}
        for assignment in assignments:
            name = assignment['name']
            if name not in unique_assignments or assignment['confidence'] > unique_assignments[name]['confidence']:
                unique_assignments[name] = assignment
        
        return list(unique_assignments.values())
        
    except Exception as e:
        print(f"  TRANSCRIPT: Error extracting assignments: {e}")
        return []

def apply_default_assignments(card_name, card_description=""):
    """Apply Wendy/Levy defaults when no assignment found."""
    try:
        card_content = f"{card_name.lower()} {card_description.lower()}".lower()
        
        # Content-based default assignments
        mobile_keywords = ['mobile', 'app', 'ios', 'android', 'flutter', 'react native']
        web_keywords = ['website', 'web', 'wordpress', 'landing', 'page', 'frontend', 'html', 'css']
        
        if any(keyword in card_content for keyword in mobile_keywords):
            return {
                'name': 'Wendy',
                'whatsapp': TEAM_MEMBERS.get('Wendy'),
                'source': 'Default assignment: Mobile/App content',
                'confidence': 60
            }
        elif any(keyword in card_content for keyword in web_keywords):
            return {
                'name': 'Levy',
                'whatsapp': TEAM_MEMBERS.get('Levy'),
                'source': 'Default assignment: Web content',
                'confidence': 60
            }
        else:
            # Random default between Wendy and Levy
            import random
            default_assignee = random.choice(['Wendy', 'Levy'])
            return {
                'name': default_assignee,
                'whatsapp': TEAM_MEMBERS.get(default_assignee),
                'source': f'Default assignment: Random fallback',
                'confidence': 50
            }
    
    except Exception as e:
        print(f"  DEFAULTS: Error applying defaults: {e}")
        return None

def get_enhanced_card_assignment(card, transcript_text=None):
    """Enhanced assignment detection using all available methods."""
    try:
        print(f"ENHANCED ASSIGNMENT: Processing card {card.name}")
        all_assignments = []
        
        # Method 1: Check checklists (highest priority)
        checklist_assignments = get_card_checklists(card.id)
        all_assignments.extend(checklist_assignments)
        print(f"  Method 1 - Checklists: Found {len(checklist_assignments)} assignments")
        
        # Method 2: Get last non-admin commenter
        last_commenter = get_last_non_admin_commenter(card.id)
        if last_commenter:
            all_assignments.append(last_commenter)
            print(f"  Method 2 - Last commenter: {last_commenter['name']}")
        
        # Method 3: Transcript analysis (if available)
        if transcript_text:
            transcript_assignments = extract_transcript_assignments(transcript_text, card.name)
            all_assignments.extend(transcript_assignments)
            print(f"  Method 3 - Transcript: Found {len(transcript_assignments)} assignments")
        
        # Method 4: Existing description/name patterns (from original code)
        card_description = (card.description or '').lower()
        card_name_lower = card.name.lower()
        
        for member_name, whatsapp_num in TEAM_MEMBERS.items():
            member_lower = member_name.lower()
            
            if member_lower in ['admin', 'criselle']:
                continue
            
            patterns_to_check = [
                f"@{member_lower}",
                f"@ {member_lower}",
                member_lower,
                f"assigned to {member_lower}",
            ]
            
            for pattern in patterns_to_check:
                if pattern in card_description or pattern in card_name_lower:
                    all_assignments.append({
                        'name': member_name,
                        'whatsapp': whatsapp_num,
                        'source': f'Description/name pattern: {pattern}',
                        'confidence': 70
                    })
                    print(f"  Method 4 - Patterns: Found {member_name}")
                    break
        
        # Select best assignment (highest confidence, prioritize checklists)
        if all_assignments:
            # Sort by confidence, prioritize checklist sources
            sorted_assignments = sorted(all_assignments, key=lambda x: (
                100 if 'checklist' in x['source'].lower() else x['confidence']
            ), reverse=True)
            
            best_assignment = sorted_assignments[0]
            print(f"  SELECTED: {best_assignment['name']} (confidence: {best_assignment['confidence']}, source: {best_assignment['source']})")
            
            return best_assignment['name'], best_assignment['whatsapp'], all_assignments
        
        # Method 5: Apply defaults if nothing found
        default_assignment = apply_default_assignments(card.name, card.description)
        if default_assignment:
            print(f"  FALLBACK: {default_assignment['name']} (default assignment)")
            return default_assignment['name'], default_assignment['whatsapp'], [default_assignment]
        
        print(f"  RESULT: No assignment found for card {card.name}")
        return None, None, []
        
    except Exception as e:
        print(f"Enhanced assignment error for {card.name}: {e}")
        return None, None, []

# ===== OPTIMIZED TRANSCRIPT PROCESSING =====

def extract_cards_from_notes(trello_review_text):
    """Extract card names/tasks from Trello Board Review section in Notes."""
    try:
        if not trello_review_text:
            return []
        
        cards_mentioned = []
        lines = trello_review_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for task-like patterns
            line_lower = line.lower()
            
            # Skip headers and metadata
            if any(skip in line_lower for skip in ['trello', 'board', 'review', 'task', 'assignment', '---', '===', 'section']):
                continue
                
            # Look for bullet points, numbered items, or task descriptions
            if (line.startswith('•') or line.startswith('-') or line.startswith('*') or 
                any(char.isdigit() for char in line[:3]) or
                any(keyword in line_lower for keyword in ['organize', 'create', 'update', 'fix', 'build', 'center', 'mobile', 'app', 'wordpress', 'court', 'document'])):
                
                # Clean up the line
                clean_line = line
                for prefix in ['•', '-', '*', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.']:
                    if clean_line.startswith(prefix):
                        clean_line = clean_line[len(prefix):].strip()
                        break
                
                if len(clean_line) > 10:  # Meaningful task description
                    cards_mentioned.append(clean_line)
        
        try:
            safe_cards = [card.encode('ascii', errors='replace').decode('ascii') for card in cards_mentioned]
            print(f"Extracted cards from Notes: {safe_cards}")
        except:
            print(f"Extracted {len(cards_mentioned)} cards from Notes")
        return cards_mentioned
        
    except Exception as e:
        print(f"Error extracting cards from notes: {e}")
        return []

def match_notes_cards_to_trello(notes_cards, transcript_text):
    """Match cards from Notes against Trello board and find transcript discussions."""
    try:
        if not notes_cards or not trello_client:
            return []
        
        # Get Trello cards
        boards = trello_client.list_boards()
        eeinteractive_board = None
        for board in boards:
            if 'eeinteractive' in board.name.lower():
                eeinteractive_board = board
                break
        
        if not eeinteractive_board:
            print("EEInteractive board not found")
            return []
        
        trello_cards = eeinteractive_board.list_cards()
        matched_cards = []
        
        for notes_card in notes_cards:
            notes_card_lower = notes_card.lower()
            best_match = None
            best_confidence = 0
            
            for trello_card in trello_cards:
                if trello_card.closed:
                    continue
                
                # Skip READ - RULES card
                if 'READ - RULES WHEN ADDING TASK - DO NOT DELETE' in trello_card.name:
                    continue
                
                # Calculate similarity
                trello_name_lower = trello_card.name.lower()
                confidence = 0
                
                # Word overlap scoring
                notes_words = set(word for word in notes_card_lower.split() if len(word) > 2)
                trello_words = set(word for word in trello_name_lower.split() if len(word) > 2)
                
                if notes_words and trello_words:
                    overlap = len(notes_words.intersection(trello_words))
                    confidence = (overlap / len(notes_words.union(trello_words))) * 100
                
                # Boost confidence for exact substring matches
                if notes_card_lower in trello_name_lower or trello_name_lower in notes_card_lower:
                    confidence += 50
                
                # Check for partial matches of key terms
                key_terms = ['mobile', 'app', 'court', 'document', 'wordpress', 'center', 'organize']
                for term in key_terms:
                    if term in notes_card_lower and term in trello_name_lower:
                        confidence += 20
                
                if confidence > best_confidence and confidence >= 40:
                    best_confidence = confidence
                    best_match = {
                        'id': trello_card.id,
                        'name': trello_card.name,
                        'url': trello_card.url,
                        'confidence': confidence,
                        'description': trello_card.description[:200] if trello_card.description else '',
                        'board_name': eeinteractive_board.name,
                        'match_type': 'notes_to_trello',
                        'notes_reference': notes_card
                    }
            
            if best_match:
                try:
                    safe_notes = notes_card.encode('ascii', errors='replace').decode('ascii')
                    safe_name = best_match['name'].encode('ascii', errors='replace').decode('ascii')
                    print(f"NOTES MATCH: '{safe_notes}' → '{safe_name}' (confidence: {best_confidence:.1f}%)")
                except:
                    print(f"NOTES MATCH: [card with special chars] → [trello card] (confidence: {best_confidence:.1f}%)")
                
                # Now find transcript discussion for this card using meeting parser
                try:
                    from meeting_parser import MeetingStructureParser
                    parser = MeetingStructureParser()
                    mock_cards = [{'name': best_match['name']}]
                    card_discussions = parser.extract_card_discussions(transcript_text, mock_cards)
                    
                    if card_discussions.get(best_match['name']):
                        discussion_data = card_discussions[best_match['name']]
                        best_match['transcript_discussion'] = discussion_data.get('discussion', '')
                        best_match['discussion_summary'] = discussion_data.get('summary', '')
                        best_match['discussion_confidence'] = discussion_data.get('confidence', 0)
                        print(f"Found transcript discussion for '{best_match['name']}'")
                    
                except Exception as parser_error:
                    print(f"Meeting parser error for {best_match['name']}: {parser_error}")
                
                matched_cards.append(best_match)
        
        return matched_cards
        
    except Exception as e:
        print(f"Error matching notes cards to Trello: {e}")
        return []

def enhanced_card_matching_no_ai(transcript_text, doc_content=None):
    """Enhanced card matching without OpenAI dependency using multiple strategies."""
    try:
        if not trello_client:
            return []
        
        # Get Trello board
        boards = trello_client.list_boards()
        eeinteractive_board = None
        for board in boards:
            if 'eeinteractive' in board.name.lower():
                eeinteractive_board = board
                break
        
        if not eeinteractive_board:
            return []
        
        cards = eeinteractive_board.list_cards()
        matched_cards = []
        
        # Combine all available text sources
        all_text = transcript_text.lower()
        if doc_content:
            if doc_content.get('notes_tab_content'):
                all_text += " " + doc_content['notes_tab_content'].lower()
            if doc_content.get('raw_text'):
                all_text += " " + doc_content['raw_text'].lower()
        
        print(f"Enhanced matching using {len(all_text)} characters of content")
        
        # Enhanced keyword sets for better matching
        keyword_groups = {
            'mobile': ['mobile', 'app', 'ios', 'android', 'flutter', 'react native'],
            'web': ['website', 'web', 'wordpress', 'landing', 'page', 'frontend', 'html', 'css'],
            'court': ['court', 'legal', 'document', 'evidence', 'case', 'organize'],
            'center': ['center', 'centre', 'vitality', 'quantum', 'healing', 'energy'],
            'eesystem': ['eesystem', 'ee system', 'scalar', 'wellness'],
            'design': ['design', 'logo', 'brand', 'graphics', 'visual'],
            'funnel': ['funnel', 'landing', 'page', 'ghl', 'gohighlevel'],
            'calendar': ['calendar', 'schedule', 'booking', 'appointment'],
            'social': ['social', 'media', 'facebook', 'instagram', 'marketing']
        }
        
        for card in cards:
            if card.closed or 'READ - RULES WHEN ADDING TASK - DO NOT DELETE' in card.name:
                continue
            
            card_name_lower = card.name.lower()
            confidence = 0
            
            # Strategy 1: Direct name matching
            if card_name_lower in all_text:
                confidence += 80
            
            # Strategy 2: Word overlap with higher scoring
            card_words = set(word for word in card_name_lower.split() if len(word) > 2)
            text_words = set(all_text.split())
            
            if card_words and text_words:
                overlap = len(card_words.intersection(text_words))
                word_score = (overlap / len(card_words)) * 60
                confidence += word_score
            
            # Strategy 3: Keyword group matching
            for group_name, keywords in keyword_groups.items():
                card_has_group = any(keyword in card_name_lower for keyword in keywords)
                text_has_group = any(keyword in all_text for keyword in keywords)
                
                if card_has_group and text_has_group:
                    confidence += 40
                    print(f"Keyword group match '{group_name}': {card.name}")
            
            # Strategy 4: Partial substring matching
            for word in card_name_lower.split():
                if len(word) > 4:
                    if word in all_text:
                        confidence += 25
            
            # Strategy 5: Common task patterns
            task_patterns = ['organize', 'create', 'update', 'fix', 'build', 'improve', 'add', 'upload']
            card_has_task = any(pattern in card_name_lower for pattern in task_patterns)
            text_has_task = any(pattern in all_text for pattern in task_patterns)
            
            if card_has_task and text_has_task:
                confidence += 20
            
            if confidence >= 30:  # Lower threshold for enhanced matching
                matched_cards.append({
                    'id': card.id,
                    'name': card.name,
                    'url': card.url,
                    'confidence': min(100, confidence),
                    'description': card.description[:200] if card.description else '',
                    'board_name': eeinteractive_board.name,
                    'match_type': 'enhanced_no_ai'
                })
                print(f"ENHANCED MATCH: '{card.name}' (confidence: {confidence:.1f}%)")
        
        # Sort by confidence
        matched_cards.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        return matched_cards[:15]  # Return top 15 matches
        
    except Exception as e:
        print(f"Enhanced matching error: {e}")
        return []

def scan_trello_cards_fast(transcript_text):
    """Fast Trello card matching with timeout protection."""
    matched_cards = []
    
    if not trello_client:
        print("No Trello client available")
        return matched_cards
    
    try:
        print("Starting fast card scan...")
        start_time = time.time()
        
        # Get only the EEInteractive board
        boards = trello_client.list_boards()
        eeinteractive_board = None
        
        for board in boards:
            if board.closed:
                continue
            if 'eeinteractive' in board.name.lower():
                eeinteractive_board = board
                break
        
        if not eeinteractive_board:
            print("EEInteractive board not found")
            return matched_cards
        
        print(f"Found board: {eeinteractive_board.name}")
        
        # Get cards - use basic list_cards() instead of all_cards() to avoid heavy API calls
        cards = eeinteractive_board.list_cards()
        print(f"Retrieved {len(cards)} cards in {time.time() - start_time:.2f}s")
        
        # Debug: show first few card names
        if cards:
            print(f"Sample cards: {[card.name[:50] for card in cards[:5]]}")
        else:
            print("WARNING: No cards retrieved from board!")
        
        # Use enhanced AI for intelligent matching if available
        try:
            from enhanced_ai import EnhancedAI
            ai_engine = EnhancedAI()
            
            # Prepare simplified card data (no member/action calls that can hang)
            simple_cards = []
            for card in cards[:20]:  # Limit to 20 cards for speed
                if not card.closed and 'READ - RULES WHEN ADDING TASK - DO NOT DELETE' not in card.name:
                    simple_cards.append({
                        'id': card.id,
                        'name': card.name,
                        'description': card.description[:200] if card.description else '',
                        'url': card.url,
                        'board_name': eeinteractive_board.name
                    })
            
            print(f"Prepared {len(simple_cards)} cards for AI matching")
            
            # AI matching with timeout
            ai_start = time.time()
            ai_matches = ai_engine.match_trello_cards_intelligent(transcript_text, simple_cards)
            ai_time = time.time() - ai_start
            
            matched_cards.extend(ai_matches)
            print(f"AI matched {len(ai_matches)} cards in {ai_time:.2f}s")
            
        except Exception as e:
            print(f"AI matching failed, using basic matching: {e}")
        
        # Fallback to basic keyword matching if needed
        if len(matched_cards) < 3:
            print(f"Using fallback keyword matching... (currently have {len(matched_cards)} matches)")
            
            transcript_lower = transcript_text.lower()
            
            for card in cards[:30]:  # Limit for speed
                if card.closed:
                    continue
                
                # Skip READ - RULES card
                if 'READ - RULES WHEN ADDING TASK - DO NOT DELETE' in card.name:
                    continue
                
                # Skip if already matched by AI
                if any(match.get('id') == card.id for match in matched_cards):
                    continue
                
                confidence = 0
                card_name_lower = card.name.lower()
                
                # Direct name matching
                if card_name_lower in transcript_lower:
                    confidence += 70
                
                # Word-by-word matching with improved logic
                card_words = card_name_lower.split()
                for word in card_words:
                    if len(word) > 2:  # Reduced from 3 to 2 for better matching
                        if word in transcript_lower:
                            confidence += 15
                        # Also check for partial matches in longer words
                        elif len(word) > 4:
                            for transcript_word in transcript_lower.split():
                                if word in transcript_word or transcript_word in word:
                                    confidence += 8
                                    break
                
                if confidence >= 25:  # Even lower threshold for better matching
                    print(f"MATCHED: '{card.name}' with confidence {confidence}")
                    matched_cards.append({
                        'id': card.id,
                        'name': card.name,
                        'url': card.url,
                        'confidence': min(100, confidence),
                        'description': card.description[:200] if card.description else '',
                        'board_name': eeinteractive_board.name,
                        'match_type': 'keyword_fallback'
                    })
                elif confidence > 0:
                    print(f"LOW CONFIDENCE: '{card.name}' with confidence {confidence} (below threshold)")
        
        # Sort by confidence
        matched_cards.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        total_time = time.time() - start_time
        print(f"Card matching completed in {total_time:.2f}s, found {len(matched_cards)} matches")
        
        return matched_cards[:10]  # Return top 10 matches
        
    except Exception as e:
        print(f"Error in fast card matching: {e}")
        return []

def extract_google_doc_content(doc_url):
    """Extract comprehensive content from Google Doc including notes and context."""
    try:
        doc_id = extract_google_doc_id(doc_url)
        if not doc_id:
            return None
        
        doc_content = get_google_doc_text(doc_id)
        if not doc_content:
            return None
            
        # Parse structured content including Notes and Transcript tabs
        content = {
            'raw_text': doc_content,
            'key_points': [],
            'decisions': [],
            'action_items': [],
            'objectives': [],
            'notes_tab_content': '',
            'transcript_tab_content': '',
            'trello_board_review': '',
            'meeting_summary': ''
        }
        
        lines = doc_content.split('\n')
        current_section = 'general'
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            line_lower = line.lower()
            
            # Detect document tabs and sections
            if 'notes:' in line_lower or line_lower.startswith('notes'):
                current_section = 'notes_tab_content'
                print("Found Notes tab section")
                continue
            elif 'transcript:' in line_lower or line_lower.startswith('transcript'):
                current_section = 'transcript_tab_content'
                print("Found Transcript tab section")
                continue
            elif 'trello board review' in line_lower and 'task assignments' in line_lower:
                current_section = 'trello_board_review'
                print("Found Trello Board Review section")
                continue
            elif any(keyword in line_lower for keyword in ['meeting summary', 'summary', 'overall summary']):
                current_section = 'meeting_summary'
                continue
            elif any(keyword in line_lower for keyword in ['key points', 'main points', 'highlights']):
                current_section = 'key_points'
                continue
            elif any(keyword in line_lower for keyword in ['decisions', 'resolved', 'agreed']):
                current_section = 'decisions'
                continue
            elif any(keyword in line_lower for keyword in ['action items', 'next steps', 'todo']):
                current_section = 'action_items'
                continue
            elif any(keyword in line_lower for keyword in ['objectives', 'goals', 'purpose']):
                current_section = 'objectives'
                continue
                
            # Extract content based on section
            if current_section in ['notes_tab_content', 'meeting_summary', 'transcript_tab_content', 'trello_board_review']:
                # For tabs and summaries, capture all content as continuous text
                if content[current_section]:
                    content[current_section] += f"\n{line}"
                else:
                    content[current_section] = line
            elif line.startswith('•') or line.startswith('-') or line.startswith('*'):
                if current_section in content and isinstance(content[current_section], list):
                    content[current_section].append(line[1:].strip())
            elif any(char.isdigit() and char in line[:3] for char in line[:3]):
                if current_section in content and isinstance(content[current_section], list):
                    content[current_section].append(line.strip())
            elif current_section == 'general' and len(line) > 20:
                content['key_points'].append(line)
                
        return content
        
    except Exception as e:
        print(f"Error extracting Google Doc content: {e}")
        return None

def analyze_meeting_transcript(transcript, doc_content=None):
    """Perform comprehensive AI analysis of meeting transcript and notes."""
    try:
        analysis = {
            'participants': [],
            'key_discussions': [],
            'decisions_made': [],
            'action_items': [],
            'meeting_purpose': '',
            'outcomes': [],
            'follow_ups': []
        }
        
        # Extract participants
        participants = extract_participants_fast(transcript)
        analysis['participants'] = participants
        
        # Find key discussion points
        lines = transcript.split('\n')
        current_topic = ''
        discussion_blocks = []
        
        for line in lines:
            line = line.strip()
            if not line or '[' in line:
                continue
                
            # Detect new topics
            if any(keyword in line.lower() for keyword in ['discuss', 'talk about', 'review', 'look at']):
                if current_topic:
                    discussion_blocks.append(current_topic)
                current_topic = line
            elif current_topic:
                current_topic += ' ' + line
                
        if current_topic:
            discussion_blocks.append(current_topic)
            
        analysis['key_discussions'] = discussion_blocks[:5]  # Top 5 discussions
        
        # Extract decisions and outcomes
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['decided', 'agreed', 'resolved', 'concluded']):
                analysis['decisions_made'].append(line.strip())
            elif any(keyword in line_lower for keyword in ['will do', 'next step', 'follow up', 'action']):
                analysis['action_items'].append(line.strip())
        
        # Integrate Google Doc content if available
        if doc_content:
            analysis['meeting_purpose'] = ' '.join(doc_content.get('objectives', []))[:200]
            analysis['outcomes'].extend(doc_content.get('decisions', [])[:3])
            analysis['follow_ups'].extend(doc_content.get('action_items', [])[:5])
            analysis['key_discussions'].extend(doc_content.get('key_points', [])[:3])
        
        return analysis
        
    except Exception as e:
        print(f"Error in meeting transcript analysis: {e}")
        return {
            'participants': extract_participants_fast(transcript),
            'key_discussions': [],
            'decisions_made': [],
            'action_items': [],
            'meeting_purpose': 'Meeting analysis',
            'outcomes': [],
            'follow_ups': []
        }

def calculate_speaker_metrics(transcript):
    """Calculate detailed speaking metrics for each participant."""
    try:
        metrics = {}
        lines = transcript.split('\n')
        current_speaker = None
        
        for line in lines:
            line = line.strip()
            if not line or '[' in line:
                continue
                
            # Extract speaker name (assumes format "Speaker: message")
            if ':' in line:
                speaker_part = line.split(':', 1)[0].strip()
                message_part = line.split(':', 1)[1].strip()
                
                if speaker_part and len(speaker_part) < 50:  # Reasonable speaker name length
                    current_speaker = speaker_part
                    
                    if current_speaker not in metrics:
                        metrics[current_speaker] = {
                            'total_words': 0,
                            'total_messages': 0,
                            'avg_message_length': 0,
                            'questions_asked': 0,
                            'decisions_made': 0,
                            'engagement_score': 0
                        }
                    
                    word_count = len(message_part.split())
                    metrics[current_speaker]['total_words'] += word_count
                    metrics[current_speaker]['total_messages'] += 1
                    
                    # Count questions
                    if '?' in message_part:
                        metrics[current_speaker]['questions_asked'] += 1
                    
                    # Count decision language
                    if any(word in message_part.lower() for word in ['decide', 'agree', 'resolve', 'conclude']):
                        metrics[current_speaker]['decisions_made'] += 1
        
        # Calculate derived metrics
        total_words = sum(m['total_words'] for m in metrics.values())
        
        for speaker, data in metrics.items():
            if data['total_messages'] > 0:
                data['avg_message_length'] = round(data['total_words'] / data['total_messages'], 1)
            
            if total_words > 0:
                data['participation_percentage'] = round((data['total_words'] / total_words) * 100, 1)
            else:
                data['participation_percentage'] = 0
                
            # Engagement score (0-100)
            engagement = 0
            engagement += min(data['participation_percentage'] * 2, 40)  # Speaking participation (max 40)
            engagement += min(data['questions_asked'] * 10, 30)  # Questions (max 30)
            engagement += min(data['decisions_made'] * 15, 30)  # Decision-making (max 30)
            
            data['engagement_score'] = min(round(engagement), 100)
        
        return metrics
        
    except Exception as e:
        print(f"Error calculating speaker metrics: {e}")
        return {}

def generate_participant_feedback(speaker_data, transcript):
    """Generate personalized improvement feedback for each participant."""
    try:
        feedback = {}
        
        for speaker, metrics in speaker_data.items():
            participant_feedback = {
                'strengths': [],
                'improvements': [],
                'specific_suggestions': [],
                'engagement_level': 'Medium'
            }
            
            participation = metrics.get('participation_percentage', 0)
            questions = metrics.get('questions_asked', 0)
            avg_length = metrics.get('avg_message_length', 0)
            engagement = metrics.get('engagement_score', 0)
            
            # Determine engagement level
            if engagement >= 70:
                participant_feedback['engagement_level'] = 'High'
            elif engagement >= 40:
                participant_feedback['engagement_level'] = 'Medium'
            else:
                participant_feedback['engagement_level'] = 'Low'
            
            # Identify strengths
            if participation > 25:
                participant_feedback['strengths'].append('Active participation in discussions')
            if questions > 2:
                participant_feedback['strengths'].append('Good questioning and curiosity')
            if metrics.get('decisions_made', 0) > 0:
                participant_feedback['strengths'].append('Contributing to decision-making')
            if avg_length > 15:
                participant_feedback['strengths'].append('Providing detailed explanations')
            
            # Suggest improvements
            if participation < 10:
                participant_feedback['improvements'].append('Increase participation in discussions')
                participant_feedback['specific_suggestions'].append('Try to share your thoughts on at least 2-3 topics per meeting')
            
            if questions == 0:
                participant_feedback['improvements'].append('Ask more clarifying questions')
                participant_feedback['specific_suggestions'].append('When unsure about requirements, ask specific questions rather than staying silent')
            
            if avg_length < 5:
                participant_feedback['improvements'].append('Provide more detailed responses')
                participant_feedback['specific_suggestions'].append('Expand on your answers with examples or reasoning')
            
            if participation > 50:
                participant_feedback['improvements'].append('Allow others more speaking time')
                participant_feedback['specific_suggestions'].append('After sharing your point, ask "What does everyone else think?"')
            
            # Skip admin and Criselle from feedback
            if speaker.lower() not in ['admin', 'criselle']:
                feedback[speaker] = participant_feedback
        
        return feedback
        
    except Exception as e:
        print(f"Error generating participant feedback: {e}")
        return {}

def create_comprehensive_summary(transcript, doc_content=None, assignments=None):
    """Create concise meeting summary with key points only."""
    try:
        today = datetime.now().strftime('%d/%m/%Y')
        
        # Check if we have Notes tab content - prioritize this for group summary
        if doc_content and doc_content.get('notes_tab_content'):
            notes_content = doc_content['notes_tab_content'].strip()
            if notes_content and len(notes_content) > 10:
                print("Using Notes tab content for group summary")
                
                # Truncate long notes content
                max_notes_length = 250
                if len(notes_content) > max_notes_length:
                    notes_content = notes_content[:max_notes_length] + "..."
                
                return f"""🎯 Meeting Summary - {today}

{notes_content}

✅ Team members updated on action items"""
        
        # Fallback to simple auto-generated summary
        return f"""🎯 Meeting Summary - {today}

📋 Key topics discussed and action items assigned
👥 Team members updated on their tasks

✅ Trello cards updated with meeting notes"""
        
    except Exception as e:
        print(f"Error creating summary: {e}")
        today = datetime.now().strftime('%d/%m/%Y')
        return f"""🎯 Meeting Summary - {today}

📋 Meeting completed successfully
✅ Team members notified of updates"""

def generate_meeting_comment(transcript_text, card_name, match_context="", card_id=None, doc_content=None, meeting_analysis=None):
    """Generate enhanced structured comment for Trello card using meeting structure parsing."""
    try:
        from meeting_parser import MeetingStructureParser
        
        # Use the new meeting parser to get card-specific discussion
        parser = MeetingStructureParser()
        
        # Create a mock card list with just this card for parsing
        mock_cards = [{'name': card_name}]
        card_discussions = parser.extract_card_discussions(transcript_text, mock_cards)
        
        # Get the specific discussion for this card
        card_discussion = card_discussions.get(card_name, {})
        relevant_discussion = card_discussion.get('discussion', '')
        discussion_summary = card_discussion.get('summary', '')
        discussion_speakers = card_discussion.get('speakers', [])
        parser_confidence = card_discussion.get('confidence', 0)
        
        # Get enhanced assignment information
        assignment_info = []
        if card_id:
            try:
                # Create a mock card object for assignment detection
                class MockCard:
                    def __init__(self, card_id, name, description=""):
                        self.id = card_id
                        self.name = name
                        self.description = description
                
                mock_card = MockCard(card_id, card_name, "")
                assigned_user, assigned_whatsapp, all_assignments = get_enhanced_card_assignment(mock_card, transcript_text)
                
                if all_assignments:
                    assignment_info.append("**🎯 Assignment Analysis:**")
                    for i, assignment in enumerate(all_assignments[:3], 1):  # Top 3 assignments
                        confidence_emoji = "🎯" if assignment['confidence'] >= 85 else "📝" if assignment['confidence'] >= 70 else "💭"
                        assignment_info.append(f"{confidence_emoji} **{assignment['name']}** - {assignment['source']} ({assignment['confidence']}% confidence)")
                    assignment_info.append("")
                    
                    # Highlight primary assignee
                    if assigned_user:
                        assignment_info.append(f"**📌 Primary Assignee:** {assigned_user}")
                        assignment_info.append("")
                        
            except Exception as e:
                print(f"Error in assignment detection for comment: {e}")
        
        # Extract relevant meeting context
        context_info = []
        if meeting_analysis:
            # Add meeting purpose if relevant to this card
            if meeting_analysis.get('meeting_purpose') and any(word in meeting_analysis['meeting_purpose'].lower() for word in card_name.lower().split() if len(word) > 3):
                context_info.append(f"**📋 Meeting Context:** {meeting_analysis['meeting_purpose']}")
                context_info.append("")
        
        # Build the comment
        comment_parts = []
        
        # Header
        today = datetime.now().strftime('%B %d, %Y')
        comment_parts.append(f"📅 **Meeting Update - {today}**")
        comment_parts.append("")
        
        # Assignment information
        if assignment_info:
            comment_parts.extend(assignment_info)
        
        # Meeting context
        if context_info:
            comment_parts.extend(context_info)
        
        # Card-specific discussion from meeting parser
        if relevant_discussion and parser_confidence > 50:
            comment_parts.append("**💬 Card-Specific Discussion:**")
            if discussion_speakers:
                comment_parts.append(f"*Participants: {', '.join(discussion_speakers)}*")
            comment_parts.append("")
            
            # Use the structured summary if available
            if discussion_summary:
                comment_parts.append(discussion_summary)
            else:
                # Fallback to raw discussion with formatting
                discussion_lines = relevant_discussion.split('\n')
                for line in discussion_lines[:4]:  # Limit to first 4 lines
                    if line.strip():
                        comment_parts.append(f"> {line}")
            comment_parts.append("")
        elif not relevant_discussion and parser_confidence < 30:
            # No specific discussion found for this card
            comment_parts.append("**💬 Discussion Status:**")
            comment_parts.append("> This card was mentioned in the meeting but no specific discussion was captured.")
            comment_parts.append("> Please check with the team for any updates or decisions made.")
            comment_parts.append("")
        
        # Google Doc insights (Notes tab content should be used here in future)
        if doc_content:
            card_keywords = [word for word in card_name.lower().split() if len(word) > 3]
            doc_insights = []
            # Check if any doc content relates to this card
            for key_point in doc_content.get('key_points', [])[:2]:
                if any(keyword in key_point.lower() for keyword in card_keywords):
                    doc_insights.append(key_point)
            
            if doc_insights:
                comment_parts.append("**📄 Additional Notes:**")
                for insight in doc_insights:
                    comment_parts.append(f"• {insight}")
                comment_parts.append("")
        
        # Action required
        comment_parts.append("**🔄 Action Required:**")
        comment_parts.append("Please update this card with:")
        comment_parts.append("• Current status and progress")
        comment_parts.append("• Next steps and timeline")
        comment_parts.append("• Any blockers or support needed")
        comment_parts.append("")
        
        # Footer
        comment_parts.append("---")
        comment_parts.append("*Auto-generated from Google Meet transcript analysis*")
        
        return "\n".join(comment_parts)
        
    except Exception as e:
        print(f"Error generating enhanced comment: {e}")
        return f"📅 Meeting Update - {datetime.now().strftime('%B %d, %Y')}\n\nThis card was discussed in today's team meeting. Enhanced assignment detection encountered an error.\n\nPlease update with current status and confirm assignment.\n\n---\n*Auto-generated from meeting transcript*"

@app.route('/api/process-transcript', methods=['POST'])
@login_required
def process_transcript():
    """Complete transcript processing with Google Docs and Trello commenting."""
    try:
        print("Processing transcript request...")
        start_time = time.time()
        
        data = request.get_json()
        transcript_text = ""
        source_type = "unknown"
        source_url = None
        
        # Handle Google Docs URL input
        if 'url' in data:
            url = data.get('url', '').strip()
            if not url:
                return jsonify({'success': False, 'error': 'No URL provided'})
            
            doc_id = extract_google_doc_id(url)
            if not doc_id:
                return jsonify({'success': False, 'error': 'Invalid Google Docs URL'})
            
            # Get document content with tab parsing
            doc_content = extract_google_doc_content(url)
            if not doc_content:
                return jsonify({'success': False, 'error': 'Could not fetch document or document is empty'})
            
            # ENHANCED: Use best available content source
            if doc_content.get('transcript_tab_content') and len(doc_content['transcript_tab_content']) > 500:
                transcript_text = doc_content['transcript_tab_content']
                print("Using Transcript tab content for analysis")
            elif doc_content.get('raw_text'):
                transcript_text = doc_content['raw_text']
                print("Using full document content for analysis (transcript tab too short)")
            else:
                transcript_text = ""
                print("No usable content found in document")
                
            if not transcript_text:
                return jsonify({'success': False, 'error': 'No transcript content found in document'})
            
            source_type = "google_docs"
            source_url = url
            
        # Handle direct text input
        elif 'direct_text' in data:
            transcript_text = data.get('direct_text', '').strip()
            if not transcript_text:
                return jsonify({'success': False, 'error': 'No transcript text provided'})
            source_type = "direct_text"
        else:
            return jsonify({'success': False, 'error': 'No transcript source provided. Use "url" or "direct_text".'})
        
        print(f"Transcript received: {len(transcript_text)} characters from {source_type}")
        
        # Safe preview of transcript content  
        try:
            safe_preview = transcript_text[:200].encode('ascii', errors='replace').decode('ascii')
            print(f"First 200 characters: {safe_preview}...")
        except Exception as e:
            print(f"First 200 characters: [contains special characters] - {e}")
            
        # Safe word detection
        try:
            text_lower = transcript_text.lower() if transcript_text else ""
            print(f"Contains common words: Mobile={('mobile' in text_lower)}, App={('app' in text_lower)}, Center={('center' in text_lower)}, Court={('court' in text_lower)}")
        except Exception as e:
            print(f"Word detection failed: {e}")
        
        # Initialize comprehensive analysis results
        analysis_results = {}
        doc_content = None
        meeting_analysis = None
        speaker_metrics = {}
        participant_feedback = {}
        
        # Add doc_content to analysis if available from Google Docs
        if doc_content:
            analysis_results['doc_content'] = {
                'key_points': len(doc_content.get('key_points', [])),
                'decisions': len(doc_content.get('decisions', [])),
                'action_items': len(doc_content.get('action_items', [])),
                'notes_tab_available': bool(doc_content.get('notes_tab_content')),
                'transcript_tab_available': bool(doc_content.get('transcript_tab_content')),
                'trello_review_available': bool(doc_content.get('trello_board_review'))
            }
            print(f"Google Doc tabs: Notes={bool(doc_content.get('notes_tab_content'))}, Transcript={bool(doc_content.get('transcript_tab_content'))}, Trello Review={bool(doc_content.get('trello_board_review'))}")
            
            # DEBUG: Show content lengths
            print(f"DEBUG Content lengths:")
            print(f"  - notes_tab_content: {len(doc_content.get('notes_tab_content', ''))}")
            print(f"  - transcript_tab_content: {len(doc_content.get('transcript_tab_content', ''))}")
            print(f"  - trello_board_review: {len(doc_content.get('trello_board_review', ''))}")
            print(f"  - raw_text: {len(doc_content.get('raw_text', ''))}")
            
            # DEBUG: Show sample content
            if doc_content.get('trello_board_review'):
                try:
                    sample = doc_content['trello_board_review'][:300].encode('ascii', errors='replace').decode('ascii')
                    print(f"DEBUG Trello Review sample: {sample}...")
                except:
                    print(f"DEBUG Trello Review length: {len(doc_content['trello_board_review'])}")
        
        # NEW: Comprehensive meeting analysis
        try:
            print("Performing comprehensive meeting analysis...")
            meeting_analysis = analyze_meeting_transcript(transcript_text, doc_content)
            analysis_results['meeting_analysis'] = {
                'participants': len(meeting_analysis.get('participants', [])),
                'key_discussions': len(meeting_analysis.get('key_discussions', [])),
                'decisions_made': len(meeting_analysis.get('decisions_made', [])),
                'action_items': len(meeting_analysis.get('action_items', [])),
                'meeting_purpose': meeting_analysis.get('meeting_purpose', '')[:100]
            }
            print(f"Meeting analysis completed")
        except Exception as e:
            print(f"Meeting analysis failed: {e}")
            analysis_results['meeting_analysis_error'] = str(e)
        
        # NEW: Speaker metrics and participation analysis
        try:
            print("Calculating speaker metrics...")
            speaker_metrics = calculate_speaker_metrics(transcript_text)
            if speaker_metrics:
                analysis_results['speaker_metrics'] = {
                    speaker: {
                        'participation_percentage': data.get('participation_percentage', 0),
                        'engagement_score': data.get('engagement_score', 0),
                        'questions_asked': data.get('questions_asked', 0)
                    }
                    for speaker, data in speaker_metrics.items()
                }
                print(f"Speaker metrics calculated for {len(speaker_metrics)} participants")
        except Exception as e:
            print(f"Speaker metrics calculation failed: {e}")
        
        # NEW: Generate participant feedback
        try:
            if speaker_metrics:
                print("Generating participant feedback...")
                participant_feedback = generate_participant_feedback(speaker_metrics, transcript_text)
                analysis_results['participant_feedback_count'] = len(participant_feedback)
                print(f"Participant feedback generated for {len(participant_feedback)} people")
        except Exception as e:
            print(f"Participant feedback generation failed: {e}")
        
        # Legacy speaker analysis (keeping for compatibility)
        if SpeakerAnalyzer:
            try:
                analyzer = SpeakerAnalyzer()
                speaker_analysis = analyzer.analyze_transcript(transcript_text)
                analysis_results['legacy_speaker_analysis'] = speaker_analysis
                print(f"Legacy speaker analysis completed")
            except Exception as e:
                print(f"Legacy speaker analysis failed: {e}")
                analysis_results['legacy_speaker_analysis'] = {'error': str(e)}
        
        # Fast AI analysis with timeout protection
        try:
            from enhanced_ai import EnhancedAI
            ai_engine = EnhancedAI()
            
            # Only do essential AI analysis to avoid timeouts
            sentiment_result = ai_engine.analyze_meeting_sentiment(transcript_text)
            analysis_results['sentiment_analysis'] = {
                'summary': sentiment_result.summary,
                'insights': sentiment_result.insights,
                'confidence': sentiment_result.confidence
            }
            print(f"AI analysis completed")
            
        except Exception as e:
            print(f"AI analysis failed: {e}")
            analysis_results['enhanced_ai_error'] = str(e)
        
        # Enhanced card matching: Notes → Transcript workflow with non-OpenAI backup
        matched_cards = []
        try:
            if doc_content and doc_content.get('trello_board_review'):
                print("Using Notes-first card matching workflow")
                # Step 1: Extract card names from Notes (Trello Board Review section)
                notes_cards = extract_cards_from_notes(doc_content['trello_board_review'])
                print(f"Found {len(notes_cards)} cards mentioned in Notes")
                
                # Step 2: Match against Trello board
                matched_cards = match_notes_cards_to_trello(notes_cards, transcript_text)
                print(f"Matched {len(matched_cards)} cards from Notes to Trello")
            else:
                print("No Trello Board Review found, using enhanced fallback matching")
                # Enhanced fallback without OpenAI dependency
                matched_cards = enhanced_card_matching_no_ai(transcript_text, doc_content)
            
            # If still no matches, use basic fallback
            if len(matched_cards) == 0:
                print("Using basic keyword matching as final fallback")
                matched_cards = scan_trello_cards_fast(transcript_text)
            
            print(f"Card matching completed: {len(matched_cards)} matches")
        except Exception as e:
            print(f"Card matching failed: {e}")
            # Ultimate fallback
            try:
                matched_cards = scan_trello_cards_fast(transcript_text)
            except:
                matched_cards = []
        
        # Add comments to matched cards (NEW FEATURE)
        comments_posted = 0
        comment_errors = []
        
        if matched_cards and trello_client:
            try:
                print("Adding comments to matched cards...")
                
                for card_match in matched_cards[:5]:  # Limit to top 5 matches
                    card_id = card_match.get('id')
                    card_name = card_match.get('name', 'Unknown')
                    
                    if not card_id:
                        continue
                    
                    # Generate enhanced comment with comprehensive analysis
                    comment_text = generate_meeting_comment(
                        transcript_text, 
                        card_name, 
                        card_match.get('context', ''),
                        card_id,  # Pass card_id for enhanced assignment detection
                        doc_content,  # Pass Google Doc content for richer context
                        meeting_analysis  # Pass meeting analysis for better insights
                    )
                    
                    # Post comment
                    try:
                        success = trello_client.add_comment_to_card(card_id, comment_text)
                        if success:
                            comments_posted += 1
                            print(f"Added comment to card: {card_name}")
                            # Add comment status to card match
                            card_match['comment_posted'] = True
                            card_match['comment_text'] = comment_text
                        else:
                            comment_errors.append(f"Failed to post comment to {card_name}")
                            card_match['comment_posted'] = False
                    except Exception as comment_error:
                        comment_errors.append(f"Error posting to {card_name}: {str(comment_error)}")
                        card_match['comment_posted'] = False
                        print(f"Error posting comment to {card_name}: {comment_error}")
                
                print(f"Posted {comments_posted} comments to Trello cards")
                
            except Exception as e:
                print(f"Error in comment posting process: {e}")
                comment_errors.append(f"Comment posting failed: {str(e)}")
        
        # NEW: Comprehensive summary generation
        summary_data = {}
        group_message_summary = ""
        try:
            print("Creating comprehensive meeting summary...")
            
            # Collect assignment information from matched cards
            card_assignments = {}
            for card_match in matched_cards[:10]:  # Process top 10 matches
                card_id = card_match.get('id')
                card_name = card_match.get('name', 'Unknown')
                
                if card_id:
                    # Create mock card for assignment detection
                    class MockCard:
                        def __init__(self, card_id, name):
                            self.id = card_id
                            self.name = name
                            self.description = ""
                    
                    mock_card = MockCard(card_id, card_name)
                    assigned_user, assigned_whatsapp, all_assignments = get_enhanced_card_assignment(mock_card, transcript_text)
                    
                    if assigned_user:
                        card_assignments[card_name] = {
                            'assigned_user': assigned_user,
                            'assigned_whatsapp': assigned_whatsapp,
                            'confidence': all_assignments[0]['confidence'] if all_assignments else 0
                        }
            
            # Create comprehensive group message summary
            group_message_summary = create_comprehensive_summary(
                transcript_text,
                doc_content,
                card_assignments
            )
            
            # Legacy summary data for compatibility
            participants = extract_participants_fast(transcript_text)
            action_items = extract_action_items_fast(transcript_text)
            
            summary_data = {
                'comprehensive_summary': group_message_summary,
                'participants': participants,
                'action_items': action_items,
                'word_count': len(transcript_text.split()),
                'meeting_duration_estimate': estimate_duration_fast(transcript_text),
                'comments_posted': comments_posted,
                'comment_errors': comment_errors,
                'card_assignments': card_assignments,
                'doc_content_available': doc_content is not None,
                'meeting_analysis_complete': meeting_analysis is not None,
                'speaker_metrics_count': len(speaker_metrics),
                'participant_feedback_count': len(participant_feedback)
            }
            print(f"Comprehensive summary generation completed")
            
        except Exception as e:
            print(f"Summary generation failed: {e}")
            summary_data = {'error': str(e), 'fallback_summary': f"Meeting processed with {comments_posted} card updates"}
        
        # Store results
        app_data['speaker_analyses'].append({
            'timestamp': datetime.now().isoformat(),
            'source_type': source_type,
            'source_url': source_url,
            'analysis': analysis_results,
            'summary': summary_data,
            'matched_cards': matched_cards,
            'speaker_metrics': speaker_metrics,
            'participant_feedback': participant_feedback,
            'doc_content': doc_content,
            'meeting_analysis': meeting_analysis
        })
        
        total_time = time.time() - start_time
        print(f"Total processing time: {total_time:.2f}s")
        
        # Return response
        response_data = {
            'success': True,
            'message': f'Transcript processed successfully. Posted {comments_posted} comments to Trello cards.',
            'source_type': source_type,
            'source_url': source_url,
            'word_count': len(transcript_text.split()),
            'analysis_results': analysis_results,
            'summary': summary_data,
            'matched_cards': matched_cards,
            'cards_found': len(matched_cards),
            'comments_posted': comments_posted,
            'comment_errors': comment_errors,
            'processing_time': total_time,
            'comprehensive_summary': group_message_summary,
            'speaker_metrics_available': len(speaker_metrics) > 0,
            'participant_feedback_available': len(participant_feedback) > 0,
            'doc_content_processed': doc_content is not None,
            'enhancement_features': {
                'google_doc_integration': doc_content is not None,
                'comprehensive_analysis': meeting_analysis is not None,
                'speaker_participation_tracking': len(speaker_metrics) > 0,
                'participant_feedback_system': len(participant_feedback) > 0
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in process_transcript: {e}")
        return jsonify({'success': False, 'error': f'Processing failed: {str(e)}'})

# ===== FAST UTILITY FUNCTIONS =====

def extract_participants_fast(transcript_text):
    """Fast participant extraction."""
    participants = set()
    lines = transcript_text.split('\n')
    
    for line in lines[:50]:  # Limit to first 50 lines for speed
        line = line.strip()
        if not line:
            continue
        
        speaker_match = re.match(r'^([A-Za-z][A-Za-z\s]+?):\s*(.+)$', line)
        if speaker_match:
            speaker = speaker_match.group(1).strip()
            if len(speaker) <= 20:
                participants.add(speaker.title())
        
        if len(participants) >= 10:  # Stop after finding 10 speakers
            break
    
    return sorted(list(participants))

def extract_action_items_fast(transcript_text):
    """Fast action item extraction."""
    action_items = []
    lines = transcript_text.split('\n')
    
    action_patterns = [
        r'(\w+)\s+(?:will|should|must)\s+([^.!?]+)',
        r'(\w+)\s+is\s+going\s+to\s+([^.!?]+)',
        r'(\w+)\s+can\s+(?:take|handle)\s+([^.!?]+)'
    ]
    
    for line in lines[:100]:  # Limit for speed
        line = line.strip()
        if not line:
            continue
        
        for pattern in action_patterns:
            matches = re.findall(pattern, line, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    action_items.append({
                        'assignee': match[0].title(),
                        'task': match[1].strip()
                    })
        
        if len(action_items) >= 10:  # Stop after finding 10 items
            break
    
    return action_items

def estimate_duration_fast(transcript_text):
    """Fast duration estimation."""
    word_count = len(transcript_text.split())
    estimated_minutes = max(5, word_count // 150)  # 150 words per minute
    
    return {
        'minutes': int(estimated_minutes),
        'formatted': f"{int(estimated_minutes)}m" if estimated_minutes < 60 else f"{int(estimated_minutes // 60)}h {int(estimated_minutes % 60)}m",
        'word_count': word_count
    }

# Add demo route
@app.route('/api/test-models', methods=['GET'])
def test_openai_models():
    """Test what OpenAI models are available with current API key."""
    try:
        from openai import OpenAI
        import os
        
        # Initialize OpenAI client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return jsonify({'error': 'No OpenAI API key found'})
        
        client = OpenAI(api_key=api_key)
        
        # List available models
        models = client.models.list()
        
        # Filter for GPT models
        gpt_models = []
        for model in models.data:
            if 'gpt' in model.id.lower():
                gpt_models.append({
                    'id': model.id,
                    'created': model.created,
                    'owned_by': model.owned_by
                })
        
        # Sort by creation date (newest first)
        gpt_models.sort(key=lambda x: x['created'], reverse=True)
        
        # Check if GPT-5 exists
        gpt5_available = any('gpt-5' in model['id'] for model in gpt_models)
        
        return jsonify({
            'success': True,
            'api_key_valid': True,
            'gpt5_available': gpt5_available,
            'available_gpt_models': gpt_models[:10],  # Top 10 newest
            'total_gpt_models': len(gpt_models)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'api_key_valid': False
        })

@app.route('/api/demo-analyze', methods=['POST'])
def demo_analyze():
    """Demo analysis endpoint."""
    try:
        sample_transcript = """
Sarah Chen: Good morning everyone. Let's start with our updates. Sarah, how's the progress on the WordPress site?
Mike Johnson: The WordPress site is going well. I've been working on the main landing page.
Emily Rodriguez: Great! What about the task for reaching out to onboarded clients?
David Kim: Yes, that's about 60% complete.
        """
        
        if not SpeakerAnalyzer:
            return jsonify({'success': False, 'error': 'Speaker analysis module not available'})
        
        analyzer = SpeakerAnalyzer()
        result = analyzer.analyze_transcript(sample_transcript)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/recent-activity', methods=['POST'])
def get_recent_activity():
    """Get recent activity from Trello cards with complete history."""
    try:
        data = request.json or {}
        days = data.get('days', 7)  # Default to 7 days of history
        
        if not trello_client:
            return jsonify({'success': False, 'error': 'Trello client not available'})
        
        # Get only the EEInteractive board
        boards = trello_client.list_boards()
        eeinteractive_board = None
        
        for board in boards:
            if board.closed:
                continue
            if 'eeinteractive' in board.name.lower():
                eeinteractive_board = board
                break
        
        if not eeinteractive_board:
            return jsonify({'success': False, 'error': 'EEInteractive board not found'})
        
        activities = []
        
        # Get recent actions from the board
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            # Use the Trello client API directly to get actions
            import requests
            board_id = eeinteractive_board.id
            url = f"https://api.trello.com/1/boards/{board_id}/actions"
            params = {
                'key': trello_client.api_key,
                'token': trello_client.api_secret,
                'limit': 50,
                'filter': 'all'
            }
            
            response = requests.get(url, params=params)
            board_actions = response.json() if response.status_code == 200 else []
            
            for action in board_actions:
                action_date = datetime.fromisoformat(action['date'].replace('Z', '+00:00'))
                
                if action_date < cutoff_date.replace(tzinfo=action_date.tzinfo):
                    continue
                
                activity = {
                    'date': action['date'],
                    'type': 'unknown',
                    'description': '',
                    'card_name': '',
                    'member': action.get('memberCreator', {}).get('fullName', 'Unknown')
                }
                
                # Parse different action types - focus on requested activity types
                action_type = action.get('type', '')
                action_data = action.get('data', {})
                member_name = action.get('memberCreator', {}).get('fullName', 'Unknown')
                
                # Only show activities from assigned users (not admin/criselle)
                if 'admin' in member_name.lower() or 'criselle' in member_name.lower():
                    # Skip admin activities unless it's card creation/assignment
                    if action_type not in ['createCard', 'addMemberToCard', 'addChecklistToCard']:
                        continue
                
                if action_type == 'updateCard':
                    # Card movements between lists
                    if 'listBefore' in action_data and 'listAfter' in action_data:
                        activity['type'] = 'card_moved'
                        activity['card_name'] = action_data.get('card', {}).get('name', 'Unknown card')
                        activity['description'] = f"Moved '{activity['card_name']}' from '{action_data['listBefore']['name']}' to '{action_data['listAfter']['name']}'"
                    elif 'old' in action_data and 'due' in action_data['old']:
                        activity['type'] = 'due_date_set'
                        activity['card_name'] = action_data.get('card', {}).get('name', 'Unknown card')
                        activity['description'] = f"Updated due date on '{activity['card_name']}'"
                    else:
                        continue
                elif action_type == 'commentCard':
                    # Comments from assigned users only
                    activity['type'] = 'comment'
                    activity['card_name'] = action_data.get('card', {}).get('name', 'Unknown card')
                    comment_text = action_data.get('text', '')[:100]
                    activity['description'] = f"Commented on '{activity['card_name']}': {comment_text}..."
                elif action_type == 'createCard':
                    # New tasks created
                    activity['type'] = 'card_created'
                    activity['card_name'] = action_data.get('card', {}).get('name', 'Unknown card')
                    activity['description'] = f"Created new task '{activity['card_name']}'"
                elif action_type == 'addMemberToCard':
                    # New assignments
                    activity['type'] = 'member_added'
                    activity['card_name'] = action_data.get('card', {}).get('name', 'Unknown card')
                    assigned_member = action_data.get('member', {}).get('name', 'someone')
                    activity['description'] = f"Assigned {assigned_member} to '{activity['card_name']}'"
                elif action_type == 'addChecklistToCard':
                    # New assignments via checklist
                    activity['type'] = 'assignment_added'
                    activity['card_name'] = action_data.get('card', {}).get('name', 'Unknown card')
                    checklist_name = action_data.get('checklist', {}).get('name', 'checklist')
                    activity['description'] = f"Added assignment checklist '{checklist_name}' to '{activity['card_name']}'"
                elif action_type == 'removeMemberFromCard':
                    activity['type'] = 'member_removed'
                    activity['card_name'] = action_data.get('card', {}).get('name', 'Unknown card')
                    removed_member = action_data.get('member', {}).get('name', 'someone')
                    activity['description'] = f"Removed {removed_member} from '{activity['card_name']}'"
                else:
                    continue  # Skip unknown action types
                
                activities.append(activity)
            
        except Exception as e:
            print(f"Error fetching board actions: {e}")
            # Fall back to card-based activity
            board_cards = eeinteractive_board.list_cards()
            
            for card in board_cards[:20]:  # Limit to recent cards
                if card.closed:
                    continue
                
                try:
                    if card.date_last_activity:
                        activity_date = datetime.fromisoformat(card.date_last_activity.replace('Z', '+00:00'))
                        if activity_date >= cutoff_date.replace(tzinfo=activity_date.tzinfo):
                            activities.append({
                                'date': card.date_last_activity,
                                'type': 'card_activity',
                                'card_name': card.name,
                                'description': f"Activity on '{card.name}'",
                                'member': 'Team'
                            })
                except Exception as e:
                    print(f"Error processing card activity: {e}")
        
        # Sort activities by date (most recent first)
        activities.sort(key=lambda x: x['date'], reverse=True)
        
        return jsonify({
            'success': True,
            'activities': activities[:20]  # Limit to 20 most recent
        })
        
    except Exception as e:
        print(f"Error getting recent activity: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/scan-cards', methods=['POST'])
@login_required
def scan_cards():
    """Scan Trello cards for team tracker - EEInteractive board only, DOING/IN PROGRESS lists."""
    print("=== SCAN CARDS ROUTE CALLED ===")
    try:
        # Check if force refresh requested and scan mode
        data = request.get_json() or {}
        force_refresh = data.get('force_refresh', False)
        scan_all_lists = data.get('scan_all', False)  # Option to scan all lists
        
        print(f"=== SCANNING TRELLO CARDS FOR TEAM TRACKER (force_refresh={force_refresh}) ===")
        start_time = time.time()
        
        # If force refresh, clear ONLY team tracker cards (Gmail data preserved)
        if force_refresh and enhanced_team_tracker and enhanced_team_tracker.db:
            print("FORCE REFRESH: Clearing ONLY team tracker cards (Gmail data preserved)")
            enhanced_team_tracker.db.clear_all_cards()  # This only clears team_tracker tables
        
        if not trello_client:
            return jsonify({'success': False, 'error': 'Trello client not available'})
        
        # Get only the EEInteractive board
        boards = trello_client.list_boards()
        eeinteractive_board = None
        
        for board in boards:
            if board.closed:
                continue
            if 'eeinteractive' in board.name.lower():
                eeinteractive_board = board
                break
        
        if not eeinteractive_board:
            return jsonify({'success': False, 'error': 'EEInteractive board not found'})
        
        # Get lists for this board to get list names
        board_lists = eeinteractive_board.get_lists()
        list_names = {lst.id: lst.name for lst in board_lists}
        
        # Determine which lists to scan based on mode
        if scan_all_lists:
            # Full scan mode - get everything for complete history
            target_lists = [lst.id for lst in board_lists]
            active_lists = target_lists
            print(f"FULL SCAN MODE: Scanning all {len(board_lists)} lists")
        else:
            # Default mode - only scan active lists (DOING/IN PROGRESS)
            target_lists = []
            active_lists = []
            
            print(f"Available lists on board:")
            for lst in board_lists:
                print(f"  - {lst.name} (ID: {lst.id})")
                list_name_lower = lst.name.lower()
                
                # Only scan DOING/IN PROGRESS lists by default
                if 'doing' in list_name_lower or 'in progress' in list_name_lower or 'in-progress' in list_name_lower:
                    target_lists.append(lst.id)
                    active_lists.append(lst.id)
                    print(f"TARGET: Will scan and track: {lst.name}")
            
            if not target_lists:
                print("WARNING: No DOING/IN PROGRESS lists found, scanning all non-archived lists")
                excluded = ['done', 'completed', 'archive', 'archived']
                for lst in board_lists:
                    if not any(keyword in lst.name.lower() for keyword in excluded):
                        target_lists.append(lst.id)
                        active_lists.append(lst.id)
        
        all_cards = []
        cards_needing_updates = []
        
        # Get cards from EEInteractive board only
        try:
            board_cards = eeinteractive_board.list_cards()
            total_cards = len(board_cards)
            print(f"Total cards to process: {total_cards}")
        except Exception as e:
            print(f"ERROR: Failed to get cards: {e}")
            return jsonify({'success': False, 'error': f'Failed to get cards: {str(e)}'})
        
        # Process cards in batches to prevent timeouts
        BATCH_SIZE = 5  # Process 5 cards at a time
        processed_count = 0
        
        for i, card in enumerate(board_cards):
            # Add a small delay every batch to prevent API rate limiting
            if i > 0 and i % BATCH_SIZE == 0:
                print(f"Processed {i}/{total_cards} cards...")
                time.sleep(0.2)  # Small delay
            
            try:  # Wrap each card processing in try-catch
                if card.closed:
                    print(f"SKIP: Closed card: {card.name}")
                    continue
                
                # Debug: Show which list each card is in
                card_list_name = list_names.get(card.list_id, 'Unknown')
                print(f"CARD: '{card.name}' is in list: {card_list_name}")
                
                # Skip cards not in target lists
                if card.list_id not in target_lists:
                    continue
                
                # Determine if card needs active tracking
                card_needs_tracking = card.list_id in active_lists
                
                if not card_needs_tracking:
                    print(f"HISTORY: Card '{card.name}' in non-active list - minimal processing")
                
                print(f"PROCESS: Processing card: {card.name}")
                
                # Calculate hours since last activity (general card activity)
                hours_since_activity = 0
                needs_update = False
                try:
                    if card.date_last_activity:
                        from datetime import datetime
                        activity_date = datetime.fromisoformat(card.date_last_activity.replace('Z', '+00:00'))
                        hours_since_activity = (datetime.now().replace(tzinfo=activity_date.tzinfo) - activity_date).total_seconds() / 3600
                    else:
                        hours_since_activity = 999  # Very high number
                except Exception as e:
                    print(f"Error parsing date for card {card.name}: {e}")
                    hours_since_activity = 999
                
                # Extract assigned user from checklists and comments using enhanced tracker
                assigned_user = None
                assigned_whatsapp = None
                
                try:
                    print(f"SEARCH: Looking for assigned user for card: {card.name}")
                    
                    # Get current team members from enhanced tracker (database-first)
                    current_team_members = {}
                    if enhanced_team_tracker:
                        current_team_members = enhanced_team_tracker.team_members
                        print(f"  ENHANCED TRACKER: Using {len(current_team_members)} database team members: {list(current_team_members.keys())}")
                    else:
                        current_team_members = TEAM_MEMBERS
                        print(f"  FALLBACK: Using {len(current_team_members)} environment team members: {list(current_team_members.keys())}")
                    
                    # Method 1: Check card description for team member names and @mentions
                    card_description = (card.description or '').lower()
                    card_name_lower = card.name.lower()
                    print(f"  DESCRIPTION: '{card_description[:100]}...'")
                    print(f"  CARD NAME: '{card_name_lower}'")
                    
                    # Check for @mentions and direct name references
                    for member_name, whatsapp_num in current_team_members.items():
                        member_lower = member_name.lower()
                        
                        # Skip admin and criselle from being assigned tasks
                        if member_lower in ['admin', 'criselle']:
                            continue
                    
                    # Check various patterns:
                    patterns_to_check = [
                        f"@{member_lower}",  # @wendy
                        f"@ {member_lower}",  # @ wendy  
                        member_lower,  # wendy
                        f"assigned to {member_lower}",  # assigned to wendy
                        f"assign to {member_lower}",  # assign to wendy
                        f"{member_lower} is",  # wendy is working on
                        f"{member_lower} will",  # wendy will handle
                        f"{member_lower} to",  # wendy to complete
                    ]
                    
                    # Check in description
                    for pattern in patterns_to_check:
                        if pattern in card_description:
                            assigned_user = member_name
                            assigned_whatsapp = whatsapp_num
                            print(f"FOUND: Assigned user in description pattern '{pattern}': {member_name}")
                            break
                    
                    if assigned_user:
                        break
                    
                    # Also check card name for assignments
                    if member_lower in card_name_lower:
                        assigned_user = member_name
                        assigned_whatsapp = whatsapp_num
                        print(f"FOUND: Assigned user in card name: {member_name}")
                        break
                    
                    # Method 2: Check actual Trello card members
                    if not assigned_user:
                        try:
                            card_members = getattr(card, 'members', [])
                            print(f"  MEMBERS: Found {len(card_members)} Trello members")
                            
                            for member in card_members:
                                member_name_lower = member.full_name.lower()
                                print(f"    Trello member: {member.full_name}")
                                
                                # Skip admin and Criselle
                                if 'admin' in member_name_lower or 'criselle' in member_name_lower:
                                    print(f"      SKIP: admin/criselle member")
                                    continue
                                
                                # Check if this member matches our team (partial matching)
                                for team_member_name, whatsapp_num in current_team_members.items():
                                    if team_member_name.lower() in member_name_lower or member_name_lower in team_member_name.lower():
                                        assigned_user = team_member_name
                                        assigned_whatsapp = whatsapp_num
                                        print(f"FOUND: Assigned user from Trello members: {team_member_name}")
                                        break
                                if assigned_user:
                                    break
                                
                        except Exception as e:
                            print(f"  MEMBERS: Could not access Trello members: {e}")
                    
                    # Method 2.5: Use enhanced tracker's sophisticated assignee detection
                    # Skip enhanced detection if we have too many cards to prevent timeouts
                    USE_ENHANCED_DETECTION = total_cards < 30  # Only use for smaller boards
                    
                    if not assigned_user and enhanced_team_tracker and USE_ENHANCED_DETECTION and card_needs_tracking:
                        print(f"  ENHANCED DETECTION: Using sophisticated assignee detection for card ID: {card.id}")
                        try:
                            # Set a timeout for the enhanced detection
                            import signal
                            
                            def timeout_handler(signum, frame):
                                raise TimeoutError("Enhanced detection timed out")
                            
                            # Only on non-Windows systems
                            if hasattr(signal, 'SIGALRM'):
                                signal.signal(signal.SIGALRM, timeout_handler)
                                signal.alarm(3)  # 3 second timeout
                            
                            try:
                                assignee_result = enhanced_team_tracker.get_assignee_for_card(card.id)
                                if assignee_result:
                                    assigned_user = assignee_result['name']
                                    assigned_whatsapp = assignee_result['whatsapp']
                                    print(f"FOUND: Enhanced tracker detected assignee: {assigned_user}")
                            finally:
                                if hasattr(signal, 'SIGALRM'):
                                    signal.alarm(0)  # Cancel the alarm
                                    
                        except TimeoutError:
                            print(f"  ENHANCED DETECTION: Timed out after 3 seconds")
                        except Exception as e:
                            print(f"  ENHANCED DETECTION: Error: {e}")

                    # Method 3: Check comments for assignment mentions (recent comments only)
                    if not assigned_user:
                        try:
                            print(f"  COMMENT ASSIGNMENT: Checking recent comments for assignments...")
                            api_key = os.environ.get('TRELLO_API_KEY')
                            token = os.environ.get('TRELLO_TOKEN')
                            
                            if api_key and token:
                                comments_url = f"https://api.trello.com/1/cards/{card.id}/actions"
                                params = {
                                    'filter': 'commentCard',
                                    'limit': 10,  # Recent comments only
                                    'key': api_key,
                                    'token': token
                                }
                                response = requests.get(comments_url, params=params)
                                if response.status_code == 200:
                                    recent_comments = response.json()
                                    for comment in recent_comments[:5]:  # Check last 5 comments
                                        comment_text = comment.get('data', {}).get('text', '').lower()
                                        commenter = comment.get('memberCreator', {}).get('fullName', '').lower()
                                        
                                        # Look for assignment patterns in comments
                                        for team_member_name, whatsapp_num in current_team_members.items():
                                            member_lower = team_member_name.lower()
                                            
                                            if member_lower in ['admin', 'criselle']:
                                                continue
                                            
                                            assignment_patterns = [
                                                f"@{member_lower}",
                                                f"assign this to {member_lower}",
                                                f"assigned to {member_lower}",
                                                f"{member_lower} please",
                                                f"{member_lower} can you",
                                                f"{member_lower} take this",
                                                f"{member_lower} handle this",
                                            ]
                                            
                                            for pattern in assignment_patterns:
                                                if pattern in comment_text:
                                                    assigned_user = team_member_name
                                                    assigned_whatsapp = whatsapp_num
                                                    print(f"FOUND: Assignment in comment '{pattern}': {team_member_name}")
                                                    break
                                            
                                            if assigned_user:
                                                break
                                    
                                        if assigned_user:
                                            break
                                        
                        except Exception as e:
                            print(f"  COMMENT ASSIGNMENT: Could not check comments: {e}")
                    
                    # Method 4: Smart defaults based on card content/type
                    if not assigned_user:
                        print(f"  SMART DEFAULTS: Attempting to assign based on card content...")
                        card_content = f"{card.name.lower()} {card_description}".lower()
                        
                        # Content-based assignments (only if team members exist in current team)
                        if any(keyword in card_content for keyword in ['mobile', 'app', 'ios', 'android']):
                            if 'Wendy' in current_team_members:
                                assigned_user = 'Wendy'
                                assigned_whatsapp = current_team_members.get('Wendy')
                                print(f"FOUND: Mobile/App content assigned to Wendy")
                        elif any(keyword in card_content for keyword in ['website', 'web', 'wordpress', 'landing', 'page']):
                            if 'Lancey' in current_team_members:
                                assigned_user = 'Lancey'
                                assigned_whatsapp = current_team_members.get('Lancey')
                                print(f"FOUND: Website content assigned to Lancey")
                        elif any(keyword in card_content for keyword in ['design', 'logo', 'brand', 'graphics']):
                            if 'Breyden' in current_team_members:
                                assigned_user = 'Breyden'
                                assigned_whatsapp = current_team_members.get('Breyden')
                                print(f"FOUND: Design content assigned to Breyden")
                        elif any(keyword in card_content for keyword in ['automation', 'integration', 'api', 'webhook']):
                            # Skip Ezechiel as he's been removed from team
                            print(f"SKIP: Automation content (Ezechiel no longer in team)")
                    
                    # Check if we found an assigned user
                    if not assigned_user:
                        print(f"ERROR: No assigned user found for card: {card.name}")
                        print(f"   Available team members: {list(current_team_members.keys())}")
                        continue
                    else:
                        print(f"SUCCESS: Assigned user found: {assigned_user} -> {assigned_whatsapp}")
                    
                except Exception as e:
                    print(f"ERROR: Failed to detect assigned user for card {card.name}: {e}")
                    # Continue with no assigned user
                
                # AI-powered analysis to determine if assigned user has provided updates
                assigned_user_last_update_hours = None  # Start with None, will be set if found
                # Only mark as needing update if in active list
                needs_update = card_needs_tracking  # Only active cards need updates
                
                if assigned_user:
                    try:
                        print(f"AI ANALYSIS: Checking if {assigned_user} has provided updates...")
                        
                        # Get comments from the card using different methods
                        card_comments = []
                        try:
                            # Try to get comments via API
                            import requests
                            api_key = os.environ.get('TRELLO_API_KEY')
                            token = os.environ.get('TRELLO_TOKEN')
                            
                            if api_key and token:
                                comments_url = f"https://api.trello.com/1/cards/{card.id}/actions"
                                params = {
                                    'filter': 'commentCard',
                                    'limit': 50,
                                    'key': api_key,
                                    'token': token
                                }
                                response = requests.get(comments_url, params=params)
                                if response.status_code == 200:
                                    card_comments = response.json()
                                    print(f"  API: Retrieved {len(card_comments)} comments")
                        except Exception as e:
                            print(f"  API: Could not fetch comments via API: {e}")
                        
                        # Analyze comments using AI
                        if card_comments:
                            # Filter comments by assigned user
                            assigned_user_comments = []
                            admin_comments = []
                            other_comments = []
                            
                            from datetime import datetime, timedelta
                            now = datetime.now()
                            
                            for comment in card_comments:
                                commenter_name = comment.get('memberCreator', {}).get('fullName', '').lower()
                                comment_text = comment.get('data', {}).get('text', '')
                                comment_date = comment.get('date', '')
                                
                                # Parse comment date
                                try:
                                    comment_datetime = datetime.fromisoformat(comment_date.replace('Z', '+00:00'))
                                    hours_ago = (now.replace(tzinfo=comment_datetime.tzinfo) - comment_datetime).total_seconds() / 3600
                                except:
                                    hours_ago = 999
                                
                                if assigned_user.lower() in commenter_name:
                                    assigned_user_comments.append({
                                        'text': comment_text,
                                        'hours_ago': hours_ago,
                                        'date': comment_date
                                    })
                                elif 'admin' in commenter_name or 'criselle' in commenter_name:
                                    admin_comments.append({
                                        'text': comment_text,
                                        'hours_ago': hours_ago,
                                        'date': comment_date
                                    })
                                else:
                                    other_comments.append({
                                        'text': comment_text,
                                        'hours_ago': hours_ago,
                                        'commenter': commenter_name
                                    })
                            
                            print(f"  COMMENTS: {assigned_user}: {len(assigned_user_comments)}, Admin: {len(admin_comments)}, Others: {len(other_comments)}")
                            
                            # Use simple AI logic to determine if update is needed
                            if assigned_user_comments:
                                # Find most recent comment from assigned user
                                most_recent = min(assigned_user_comments, key=lambda x: x['hours_ago'])
                                assigned_user_last_update_hours = most_recent['hours_ago']
                                
                                # Simple AI analysis: Check if the comment contains meaningful update content
                                recent_comment_text = most_recent['text'].lower()
                                update_keywords = ['progress', 'completed', 'working on', 'finished', 'done', 'update', 'status', 'started', 'implementing', 'fixed', 'issue', 'blocker', 'challenge', 'estimate', 'timeline', 'percentage', '%']
                                
                                has_meaningful_update = any(keyword in recent_comment_text for keyword in update_keywords)
                                
                                if assigned_user_last_update_hours < 24 and has_meaningful_update:
                                    needs_update = False
                                    print(f"  AI: {assigned_user} provided meaningful update {assigned_user_last_update_hours:.1f}h ago - NO UPDATE NEEDED")
                                elif assigned_user_last_update_hours < 24 and len(recent_comment_text) > 20:
                                    needs_update = False  # Any substantial comment counts
                                    print(f"  AI: {assigned_user} provided substantial comment {assigned_user_last_update_hours:.1f}h ago - NO UPDATE NEEDED")
                                else:
                                    needs_update = True
                                    print(f"  AI: {assigned_user} last update {assigned_user_last_update_hours:.1f}h ago - NEEDS UPDATE")
                            else:
                                print(f"  AI: {assigned_user} has NO comments - NEEDS UPDATE")
                                needs_update = True
                                # Keep as None if no comments found
                    
                    except Exception as e:
                        print(f"AI ANALYSIS ERROR for {card.name}: {e}")
                        needs_update = True  # Default to needs update on error
                
                card_data = {
                    'id': card.id,
                    'name': card.name,
                    'description': card.description[:200] if card.description else '',
                    'url': card.url,
                    'board_name': eeinteractive_board.name,
                    'list_name': list_names.get(card.list_id, 'Unknown'),
                    'assigned_user': assigned_user,
                    'assigned_whatsapp': assigned_whatsapp,
                    'members': [assigned_user] if assigned_user else [],
                    'assigned_members': [assigned_user] if assigned_user else [],
                    'hours_since_activity': round(hours_since_activity, 1),  # General card activity
                    'hours_since_assigned_update': round(assigned_user_last_update_hours, 1) if assigned_user_last_update_hours is not None else 999,  # Assigned user activity
                    'days_since_comment': round(assigned_user_last_update_hours / 24, 1) if assigned_user_last_update_hours is not None else 999,  # Based on assigned user
                    'needs_update': needs_update,  # AI-determined
                    'last_activity': card.date_last_activity,
                    'priority': 'high' if assigned_user_last_update_hours is not None and assigned_user_last_update_hours > 72 else 'medium' if assigned_user_last_update_hours is not None and assigned_user_last_update_hours > 24 else 'normal'
                }
                
                all_cards.append(card_data)
            
                # Update database with fresh card data
                if enhanced_team_tracker and enhanced_team_tracker.db and assigned_user:
                    try:
                        print(f"  DB UPDATE: Storing card {card.name} -> {assigned_user}")
                        # Use the enhanced tracker's method which handles comment dates correctly
                        enhanced_team_tracker.update_card_tracking(
                            card_id=card.id,
                            card_name=card.name,
                            assignee_name=assigned_user,
                            assignee_phone=assigned_whatsapp or ''
                        )
                        print(f"  DB UPDATE: Successfully stored card {card.id}")
                    except Exception as e:
                        print(f"  DB UPDATE ERROR: Could not update card {card.id}: {e}")
                        import traceback
                        print(f"  DB UPDATE TRACEBACK: {traceback.format_exc()}")
                
                # Add to cards needing updates - but we'll filter with enhanced logic later
                if needs_update:
                    # Store the card object for enhanced processing
                    card_data['card'] = card  # Keep reference to original card object
                    cards_needing_updates.append(card_data)
                    
            except Exception as e:
                print(f"ERROR: Failed to process card {card.name if hasattr(card, 'name') else 'unknown'}: {e}")
                continue  # Skip this card and continue with others
        
        print(f"[ENHANCED] Found {len(cards_needing_updates)} cards with potential updates needed")
        
        # Use enhanced team tracker to filter cards that actually need messages
        final_cards_needing_updates = enhanced_team_tracker.get_cards_needing_messages(cards_needing_updates)
        
        print(f"[ENHANCED] After enhanced filtering: {len(final_cards_needing_updates)} cards need messages")
        
        # Clean up any remaining card objects from the original cards_needing_updates
        # (The enhanced tracker should have cleaned them, but let's be safe)
        for card in cards_needing_updates:
            if 'card' in card:
                del card['card']
        
        # Sort by hours since assigned user update (most urgent first)
        all_cards.sort(key=lambda x: x.get('hours_since_assigned_update', 0) or 0, reverse=True)
        final_cards_needing_updates.sort(key=lambda x: x.get('hours_since_assigned_update', 0) or 0, reverse=True)
        
        # Store in app_data for other endpoints
        app_data['all_cards'] = all_cards
        app_data['cards_needing_updates'] = final_cards_needing_updates  # Use enhanced filtered results
        
        processing_time = time.time() - start_time
        print(f"Scanned {len(all_cards)} cards from EEInteractive board in {processing_time:.2f}s")
        
        return jsonify({
            'success': True,
            'cards': all_cards,
            'total_cards': len(all_cards),
            'processing_time': processing_time
        })
        
    except Exception as e:
        print(f"Error scanning cards: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/preview-updates', methods=['POST'])
def preview_updates():
    """Generate grouped preview messages for selected cards by assigned user."""
    try:
        data = request.json or {}
        selected_card_ids = data.get('selected_cards', [])
        
        if not selected_card_ids:
            return jsonify({'success': False, 'error': 'No cards selected'})
        
        # Get cards from app_data (check both sources)
        all_cards = app_data.get('all_cards', [])
        cards_needing_updates = app_data.get('cards_needing_updates', [])
        
        # Use cards_needing_updates first, fall back to all_cards
        available_cards = cards_needing_updates if cards_needing_updates else all_cards
        
        if not available_cards:
            return jsonify({'success': False, 'error': 'No cards data available. Please scan cards first.'})
        
        print(f"PREVIEW: Looking for {len(selected_card_ids)} selected cards in {len(available_cards)} available cards")
        
        # Group cards by assigned user
        user_cards = {}
        
        for card_id in selected_card_ids:
            # Find the card in our data
            card_data = None
            for card in available_cards:
                if card['id'] == card_id:
                    card_data = card
                    print(f"PREVIEW: Found card {card['name']} assigned to {card.get('assigned_user')}")
                    break
            
            if not card_data:
                continue
            
            assigned_user = card_data.get('assigned_user')
            assigned_whatsapp = card_data.get('assigned_whatsapp')
            
            if not assigned_user or not assigned_whatsapp:
                continue
            
            if assigned_user not in user_cards:
                user_cards[assigned_user] = {
                    'assigned_user': assigned_user,
                    'assigned_whatsapp': assigned_whatsapp,
                    'cards': []
                }
            
            user_cards[assigned_user]['cards'].append({
                'id': card_data['id'],
                'name': card_data['name'],
                'url': card_data['url'],
                'hours_since_update': card_data.get('hours_since_assigned_update', 0) or 0,
                'priority': card_data.get('priority', 'medium')
            })
        
        if not user_cards:
            return jsonify({'success': False, 'error': 'No messages to preview - no valid team members found for selected cards'})
        
        # Generate combined messages for each user
        previews = []
        escalated_cards = []  # Track cards that need group escalation
        
        for assigned_user, user_data in user_cards.items():
            cards = user_data['cards']
            card_count = len(cards)
            
            # Check reminder status for each card and prepare escalation data
            escalated_user_cards = []
            regular_cards = []
            
            for card in cards:
                reminder_status = get_reminder_status(card['id'], assigned_user)
                card['reminder_count'] = reminder_status['reminder_count']
                card['is_escalated'] = reminder_status['escalated']
                
                if reminder_status['escalated']:
                    escalated_user_cards.append(card)
                    escalated_cards.append({
                        'card_name': card['name'],
                        'assigned_user': assigned_user,
                        'reminder_count': reminder_status['reminder_count'],
                        'card_url': card['url'],
                        'hours_since_update': card['hours_since_update']
                    })
                else:
                    regular_cards.append(card)
            
            # Only create preview for regular (non-escalated) cards
            if regular_cards:
                # Create combined message for regular cards
                message = f"""Hey {assigned_user}, these are cards that need an update as over 24 hours have passed. If its ongoing just comment that and what has been done in the last 24 hours. You will be reminded 3 times about this and if no comment is made then it will be posted in the main group.

📋 Cards requiring updates ({len(regular_cards)}):

"""
                
                for i, card in enumerate(regular_cards, 1):
                    hours = card['hours_since_update']
                    reminder_count = card['reminder_count']
                    
                    if hours > 72:
                        urgency_icon = "🔴"
                    elif hours > 48:
                        urgency_icon = "🟡"
                    else:
                        urgency_icon = "🟢"
                    
                    days = int(hours / 24)
                    reminder_text = f" (Reminder #{reminder_count + 1})" if reminder_count > 0 else ""
                    
                    message += f"{urgency_icon} {i}. *{card['name']}*{reminder_text}\n"
                    message += f"   ⏰ {days} days without update\n"
                    message += f"   🔗 {card['url']}\n\n"
                
                message += "Please update these cards with your current progress. Thanks! 🚀\n\n- JGV EEsystems Team Tracker"
                
                preview_data = {
                    'assigned_user': assigned_user,
                    'assigned_whatsapp': user_data['assigned_whatsapp'],
                    'card_count': len(regular_cards),
                    'cards': regular_cards,
                    'message': message,
                    'urgency': 'high' if any((c.get('hours_since_update', 0) or 0) > 72 for c in regular_cards) else 'medium',
                    'message_type': 'regular'
                }
                
                previews.append(preview_data)
        
        # Add escalation message if there are escalated cards
        if escalated_cards:
            escalation_message = """🚨 URGENT: Cards Requiring Immediate Attention 🚨

The following team members have not responded to 3+ reminders about their assigned cards. These cards need immediate updates:

"""
            
            # Group escalated cards by user
            escalated_by_user = {}
            for card in escalated_cards:
                user = card['assigned_user']
                if user not in escalated_by_user:
                    escalated_by_user[user] = []
                escalated_by_user[user].append(card)
            
            for user, user_escalated_cards in escalated_by_user.items():
                escalation_message += f"\n👤 *{user}* ({len(user_escalated_cards)} cards):\n"
                for card in user_escalated_cards:
                    days = int(card['hours_since_update'] / 24)
                    escalation_message += f"   🔴 {card['card_name']} ({days} days, {card['reminder_count']} reminders)\n"
                    escalation_message += f"       🔗 {card['card_url']}\n"
            
            escalation_message += "\n⚠️ Please follow up with these team members immediately or reassign these cards.\n\n- JGV EEsystems Team Tracker (AUTO-ESCALATION)"
            
            # Add escalation preview (this would go to group/admin)
            previews.append({
                'assigned_user': 'GROUP ESCALATION',
                'assigned_whatsapp': 'GROUP_CHAT_ID',  # Replace with actual group chat ID
                'card_count': len(escalated_cards),
                'cards': escalated_cards,
                'message': escalation_message,
                'urgency': 'critical',
                'message_type': 'escalation'
            })
        
        return jsonify({
            'success': True,
            'previews': previews,
            'total_messages': len(previews),
            'total_users': len(user_cards)
        })
        
    except Exception as e:
        print(f"Error generating message previews: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/send-whatsapp-updates', methods=['POST'])
def send_whatsapp_updates():
    """Send WhatsApp messages using Green API."""
    try:
        data = request.json or {}
        previews = data.get('previews', [])
        
        if not previews:
            return jsonify({'success': False, 'error': 'No messages to send'})
        
        # Green API configuration
        green_api_instance = os.environ.get('GREEN_API_INSTANCE')
        green_api_token = os.environ.get('GREEN_API_TOKEN')
        
        if not green_api_instance or not green_api_token:
            return jsonify({'success': False, 'error': 'Green API credentials not configured'})
        
        sent_messages = []
        failed_messages = []
        
        for preview in previews:
            assigned_user = preview.get('assigned_user')
            whatsapp_number = preview.get('assigned_whatsapp')
            message = preview.get('message')
            
            if not whatsapp_number or not message:
                failed_messages.append({
                    'user': assigned_user,
                    'error': 'Missing WhatsApp number or message'
                })
                continue
            
            try:
                # Send message via Green API
                green_api_url = f"https://api.green-api.com/waInstance{green_api_instance}/sendMessage/{green_api_token}"
                
                payload = {
                    "chatId": whatsapp_number,
                    "message": message
                }
                
                response = requests.post(green_api_url, json=payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Increment reminder count for each card in this message
                    if preview.get('message_type') == 'regular':
                        cards = preview.get('cards', [])
                        for card in cards:
                            reminder_data = increment_reminder_count(card['id'], assigned_user)
                            print(f"Incremented reminder count for {assigned_user} on card {card['name']}: {reminder_data['reminder_count']}")
                    
                    sent_messages.append({
                        'user': assigned_user,
                        'whatsapp': whatsapp_number,
                        'message_id': result.get('idMessage'),
                        'card_count': preview.get('card_count', 1),
                        'message_type': preview.get('message_type', 'regular')
                    })
                    print(f"WhatsApp sent to {assigned_user} ({whatsapp_number}): {result}")
                else:
                    failed_messages.append({
                        'user': assigned_user,
                        'error': f"Green API error: {response.status_code} - {response.text}"
                    })
                    print(f"Failed to send to {assigned_user}: {response.status_code} - {response.text}")
                    
            except Exception as e:
                failed_messages.append({
                    'user': assigned_user,
                    'error': f"Network error: {str(e)}"
                })
                print(f"Error sending to {assigned_user}: {e}")
        
        return jsonify({
            'success': True,
            'sent_count': len(sent_messages),
            'failed_count': len(failed_messages),
            'sent_messages': sent_messages,
            'failed_messages': failed_messages,
            'total_attempted': len(previews)
        })
        
    except Exception as e:
        print(f"Error sending WhatsApp updates: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/send-participant-feedback', methods=['POST'])
def send_participant_feedback():
    """Send personalized improvement feedback to meeting participants via WhatsApp."""
    try:
        data = request.get_json()
        analysis_id = data.get('analysis_id')  # ID from stored analyses
        
        if not analysis_id:
            return jsonify({'success': False, 'error': 'Analysis ID required'})
        
        # Find the analysis data
        analysis_data = None
        for analysis in app_data['speaker_analyses']:
            if analysis.get('timestamp') == analysis_id:
                analysis_data = analysis
                break
        
        if not analysis_data:
            return jsonify({'success': False, 'error': 'Analysis not found'})
        
        participant_feedback = analysis_data.get('participant_feedback', {})
        
        if not participant_feedback:
            return jsonify({'success': False, 'error': 'No participant feedback available'})
        
        # Send feedback messages
        messages_sent = []
        failed_messages = []
        
        for participant, feedback_data in participant_feedback.items():
            # Find participant's WhatsApp number
            whatsapp_number = None
            participant_lower = participant.lower()
            
            for team_member, phone_number in TEAM_MEMBERS.items():
                if team_member.lower() in participant_lower or participant_lower in team_member.lower():
                    whatsapp_number = phone_number
                    break
            
            if not whatsapp_number:
                failed_messages.append({
                    'participant': participant,
                    'error': 'WhatsApp number not found'
                })
                continue
            
            # Generate feedback message
            feedback_message = generate_feedback_message(participant, feedback_data)
            
            # Send WhatsApp message
            try:
                whatsapp_response = requests.post(
                    WHATSAPP_API_URL,
                    headers={'Authorization': f'Bearer {GREEN_API_TOKEN}'},
                    json={
                        'chatId': f'{whatsapp_number}@c.us',
                        'message': feedback_message
                    },
                    timeout=10
                )
                
                if whatsapp_response.status_code == 200:
                    messages_sent.append({
                        'participant': participant,
                        'phone': whatsapp_number,
                        'message': feedback_message[:100] + "..." if len(feedback_message) > 100 else feedback_message
                    })
                    print(f"Sent feedback to {participant}: {whatsapp_number}")
                else:
                    failed_messages.append({
                        'participant': participant,
                        'error': f"WhatsApp API error: {whatsapp_response.status_code}"
                    })
                    print(f"Failed to send to {participant}: {whatsapp_response.status_code} - {whatsapp_response.text}")
                    
            except Exception as e:
                failed_messages.append({
                    'participant': participant,
                    'error': f"Network error: {str(e)}"
                })
                print(f"Error sending to {participant}: {e}")
        
        return jsonify({
            'success': True,
            'messages_sent': len(messages_sent),
            'messages_failed': len(failed_messages),
            'sent_details': messages_sent,
            'failed_details': failed_messages
        })
        
    except Exception as e:
        print(f"Error sending participant feedback: {e}")
        return jsonify({'success': False, 'error': str(e)})

def generate_feedback_message(participant, feedback_data):
    """Generate personalized feedback message for a participant."""
    try:
        engagement_level = feedback_data.get('engagement_level', 'Medium')
        strengths = feedback_data.get('strengths', [])
        improvements = feedback_data.get('improvements', [])
        suggestions = feedback_data.get('specific_suggestions', [])
        
        message_parts = []
        
        # Header
        message_parts.append(f"🎯 Meeting Performance Feedback for {participant}")
        message_parts.append("")
        
        # Engagement level
        engagement_emoji = "🔥" if engagement_level == "High" else "⚡" if engagement_level == "Medium" else "🌱"
        message_parts.append(f"{engagement_emoji} Engagement Level: {engagement_level}")
        message_parts.append("")
        
        # Strengths
        if strengths:
            message_parts.append("✅ Your Strengths:")
            for strength in strengths[:3]:
                message_parts.append(f"  • {strength}")
            message_parts.append("")
        
        # Areas for improvement
        if improvements:
            message_parts.append("📈 Growth Opportunities:")
            for improvement in improvements[:3]:
                message_parts.append(f"  • {improvement}")
            message_parts.append("")
        
        # Specific suggestions
        if suggestions:
            message_parts.append("💡 Specific Tips:")
            for suggestion in suggestions[:2]:
                message_parts.append(f"  • {suggestion}")
            message_parts.append("")
        
        # Encouragement
        if engagement_level == "High":
            message_parts.append("🌟 Excellent participation! Keep up the great work.")
        elif engagement_level == "Medium":
            message_parts.append("👍 Good participation! Try the tips above to shine even more.")
        else:
            message_parts.append("🚀 Every voice matters! These tips will help you contribute more confidently.")
        
        message_parts.append("")
        message_parts.append("---")
        message_parts.append("*AI-generated feedback from meeting analysis*")
        
        return "\\n".join(message_parts)
        
    except Exception as e:
        print(f"Error generating feedback message for {participant}: {e}")
        return f"🎯 Meeting Feedback\\n\\nHi {participant}! Thank you for participating in today's meeting. Your engagement and contributions are valued. Keep up the great work!\\n\\n---\\n*AI-generated feedback*"

@app.route('/api/send-updates', methods=['POST'])
@login_required
def send_updates():
    """Send WhatsApp updates to selected team members about their assigned cards."""
    try:
        data = request.json or {}
        selected_card_ids = data.get('selected_cards', [])
        
        if not selected_card_ids:
            return jsonify({'success': False, 'error': 'No cards selected'})
        
        # Green API configuration
        green_api_instance = os.environ.get('GREEN_API_INSTANCE')
        green_api_token = os.environ.get('GREEN_API_TOKEN')
        
        if not green_api_instance or not green_api_token:
            return jsonify({'success': False, 'error': 'WhatsApp API not configured'})
        
        # Get current cards data to find selected cards
        if not trello_client:
            return jsonify({'success': False, 'error': 'Trello client not available'})
        
        # Get EEInteractive board and current cards (reuse scan logic)
        boards = trello_client.list_boards()
        eeinteractive_board = None
        
        for board in boards:
            if board.closed:
                continue
            if 'eeinteractive' in board.name.lower():
                eeinteractive_board = board
                break
        
        if not eeinteractive_board:
            return jsonify({'success': False, 'error': 'EEInteractive board not found'})
        
        # Get board cards and find selected ones
        board_cards = eeinteractive_board.list_cards()
        selected_cards = [card for card in board_cards if card.id in selected_card_ids]
        
        if not selected_cards:
            return jsonify({'success': False, 'error': 'Selected cards not found'})
        
        # Use global TEAM_MEMBERS instead of hardcoded duplicate
        # (Removed hardcoded dictionary that was causing inconsistencies)
        
        sent_messages = []
        failed_messages = []
        
        for card in selected_cards:
            try:
                # Find assigned user using advanced logic from scan_cards
                assigned_user = None
                assigned_whatsapp = None
                
                # Method 1: Check for direct assignment patterns in description
                card_desc = card.description.lower() if card.description else ''
                card_name = card.name.lower()
                
                # Look for assignment patterns like found in scan_cards
                assignment_patterns = [
                    (r'levy', 'Levy'),
                    (r'lancey', 'Lancey'), 
                    (r'wendy', 'Wendy'),
                    (r'@levy', 'Levy'),
                    (r'@lancey', 'Lancey'),
                    (r'@wendy', 'Wendy'),
                    (r'assigned.*levy', 'Levy'),
                    (r'assigned.*lancey', 'Lancey'),
                    (r'assigned.*wendy', 'Wendy')
                ]
                
                import re
                for pattern, member in assignment_patterns:
                    if re.search(pattern, card_desc) or re.search(pattern, card_name):
                        assigned_user = member
                        assigned_whatsapp = TEAM_MEMBERS[member]
                        break
                
                # Method 2: Check card comments for assignments (like scan_cards does)
                if not assigned_user:
                    try:
                        comments_url = f"https://api.trello.com/1/cards/{card.id}/actions"
                        params = {
                            'key': trello_client.api_key,
                            'token': trello_client.token,
                            'filter': 'commentCard',
                            'limit': 50
                        }
                        comments_response = requests.get(comments_url, params=params, timeout=10)
                        
                        if comments_response.status_code == 200:
                            comments = comments_response.json()
                            
                            # Look for assignments in recent comments
                            for comment in comments[:10]:  # Check last 10 comments
                                comment_text = comment.get('data', {}).get('text', '').lower()
                                
                                for pattern, member in assignment_patterns:
                                    if re.search(pattern, comment_text):
                                        assigned_user = member
                                        assigned_whatsapp = TEAM_MEMBERS[member]
                                        break
                                
                                if assigned_user:
                                    break
                    except Exception as e:
                        print(f"Error checking comments for card {card.name}: {e}")
                
                if not assigned_user:
                    failed_messages.append({
                        'card': card.name,
                        'error': 'No assigned user found'
                    })
                    continue
                
                # Generate update message
                message = f"""🔔 Task Update Reminder

Hi {assigned_user}! 

You have a task that needs an update:

📋 Task: {card.name}
🔗 Link: {card.url}

Please provide a status update or comment on this card when you have a moment.

Thanks! 🙏"""
                
                # Send WhatsApp message via Green API
                api_url = f"https://api.green-api.com/waInstance{green_api_instance}/sendMessage/{green_api_token}"
                
                payload = {
                    "chatId": assigned_whatsapp,
                    "message": message
                }
                
                response = requests.post(api_url, json=payload, timeout=10)
                
                if response.status_code == 200:
                    sent_messages.append({
                        'card': card.name,
                        'user': assigned_user,
                        'phone': assigned_whatsapp
                    })
                    print(f"Sent update reminder to {assigned_user} for card: {card.name}")
                else:
                    failed_messages.append({
                        'card': card.name,
                        'user': assigned_user,
                        'error': f"WhatsApp API error: {response.status_code}"
                    })
                    print(f"Failed to send to {assigned_user}: {response.status_code} - {response.text}")
                    
            except Exception as e:
                failed_messages.append({
                    'card': card.name,
                    'error': f"Error: {str(e)}"
                })
                print(f"Error processing card {card.name}: {e}")
        
        return jsonify({
            'success': True,
            'messages_sent': len(sent_messages),
            'messages_failed': len(failed_messages),
            'sent_details': sent_messages,
            'failed_details': failed_messages
        })
        
    except Exception as e:
        print(f"Error in send_updates: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ===== MESSAGE TRACKING API ENDPOINTS =====

@app.route('/api/message-stats', methods=['GET'])
@login_required
def get_message_stats():
    """Get daily message statistics and analytics."""
    try:
        # Get today's analytics
        today_stats = message_tracker.get_daily_analytics()
        
        # Get week analytics
        week_stats = message_tracker.get_week_analytics()
        
        return jsonify({
            'success': True,
            'today': today_stats,
            'week': week_stats
        })
        
    except Exception as e:
        print(f"Error in message stats: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/card-message-status', methods=['POST'])
@login_required
def get_card_message_status():
    """Get message status for specific cards and assignees."""
    try:
        data = request.get_json()
        requests_list = data.get('requests', [])  # [{'card_id': 'x', 'assignee': 'y'}, ...]
        
        statuses = {}
        for req in requests_list:
            card_id = req.get('card_id')
            assignee = req.get('assignee')
            
            if card_id and assignee:
                status = message_tracker.get_card_message_status(card_id, assignee)
                statuses[f"{card_id}_{assignee}"] = status
        
        return jsonify({
            'success': True,
            'statuses': statuses
        })
        
    except Exception as e:
        print(f"Error in card message status: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/check-card-comments', methods=['POST'])
@login_required
def check_card_comments():
    """Check for new comments on cards and reset reminder counts."""
    try:
        data = request.json or {}
        card_id = data.get('card_id')
        
        if not card_id:
            return jsonify({'success': False, 'error': 'Card ID required'})
        
        # Get card comments from Trello API
        api_key = os.environ.get('TRELLO_API_KEY')
        token = os.environ.get('TRELLO_TOKEN')
        
        if not api_key or not token:
            return jsonify({'success': False, 'error': 'Trello API credentials not configured'})
        
        # Get card actions (comments)
        url = f"https://api.trello.com/1/cards/{card_id}/actions"
        params = {
            'key': api_key,
            'token': token,
            'filter': 'commentCard',
            'limit': 50
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return jsonify({'success': False, 'error': f'Trello API error: {response.status_code}'})
        
        comments = response.json()
        
        # Check for recent comments (within last 24 hours)
        now = datetime.now()
        recent_comments = []
        
        for comment in comments:
            comment_date = datetime.fromisoformat(comment['date'].replace('Z', '+00:00'))
            hours_since_comment = (now - comment_date.replace(tzinfo=None)).total_seconds() / 3600
            
            if hours_since_comment <= 24:  # Comment within last 24 hours
                member_id = comment['memberCreator']['id']
                recent_comments.append({
                    'member_id': member_id,
                    'member_name': comment['memberCreator']['fullName'],
                    'comment_text': comment['data']['text'],
                    'comment_date': comment['date']
                })
        
        # Reset reminder counts for users who commented recently
        resets_performed = []
        if recent_comments:
            for comment in recent_comments:
                member_name = comment['member_name']
                # Try to match with team members
                for team_member in TEAM_MEMBERS.keys():
                    if team_member.lower() in member_name.lower() or member_name.lower() in team_member.lower():
                        reset_result = reset_reminder_count(card_id, team_member)
                        if reset_result:
                            resets_performed.append({
                                'team_member': team_member,
                                'comment_by': member_name,
                                'comment_date': comment['comment_date']
                            })
                        break
        
        return jsonify({
            'success': True,
            'recent_comments': len(recent_comments),
            'resets_performed': resets_performed
        })
        
    except Exception as e:
        print(f"Error checking card comments: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/manual-scan', methods=['POST'])
@login_required
def manual_scan():
    """Manually trigger automated scan for testing."""
    try:
        print("[MANUAL] Starting manual team tracker scan...")
        perform_automated_scan()
        return jsonify({'success': True, 'message': 'Manual scan completed'})
    except Exception as e:
        print(f"Error in manual scan: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/gmail-scan', methods=['POST'])
@login_required  
def manual_gmail_scan():
    """Manually trigger Gmail scan for testing."""
    try:
        print("[MANUAL] ===== STARTING MANUAL GMAIL SCAN =====")
        print(f"[MANUAL] Gmail tracker exists: {gmail_tracker is not None}")
        print(f"[MANUAL] Gmail service exists: {gmail_tracker.gmail_service is not None if gmail_tracker else False}")
        
        if not gmail_tracker:
            return jsonify({'success': False, 'error': 'Gmail tracker not initialized'})
            
        if not gmail_tracker.gmail_service:
            # Try to refresh Gmail service from production OAuth
            print("[MANUAL] Gmail service not found, attempting to refresh from OAuth...")
            gmail_tracker.setup_production_gmail_service()
            
            if not gmail_tracker.gmail_service:
                return jsonify({
                    'success': False, 
                    'error': 'Gmail not authenticated. Please visit /auth/gmail to authenticate.',
                    'auth_required': True
                })
            else:
                print("[MANUAL] Gmail service refreshed successfully!")
        
        # Check if watch rules exist in database
        watch_rules_data = production_db.get_watch_rules()
        watch_rules = watch_rules_data.get('watchRules', []) if watch_rules_data else []
        
        print(f"[MANUAL] Watch rules count: {len(watch_rules)}")
        if not watch_rules:
            return jsonify({
                'success': False, 
                'error': 'No Gmail watch rules configured. Please set up email watch rules in the interface first.'
            })
        
        for i, rule in enumerate(watch_rules):
            print(f"[MANUAL] Rule {i+1}: '{rule.get('subject', '')}' -> {rule.get('category', '')} -> {rule.get('assignees', [])}")
        
        print("[MANUAL] Calling gmail_tracker.scan_only_mode()...")
        # Run scan WITHOUT sending notifications (scan-only mode)
        emails_found = gmail_tracker.scan_emails_only(hours_back=24)
        print(f"[MANUAL] ===== MANUAL GMAIL SCAN COMPLETE - FOUND {len(emails_found)} EMAILS =====")
        return jsonify({'success': True, 'message': 'Gmail scan completed - check email processing section below', 'emails_found': len(emails_found), 'emails': emails_found})
    except Exception as e:
        print(f"[MANUAL] ERROR in manual Gmail scan: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/gmail-history', methods=['GET'])
@login_required
def get_gmail_history():
    """Get Gmail processing history from production database."""
    try:
        limit = request.args.get('limit', 50, type=int)
        history = production_db.get_email_history(limit=limit)
        
        return jsonify({
            'success': True,
            'emails': history,
            'total': len(history),
            'database': 'PostgreSQL' if production_db.is_production else 'SQLite'
        })
    except Exception as e:
        print(f"Error getting Gmail history: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/gmail-sync-settings', methods=['POST'])
@login_required
def sync_gmail_settings():
    """Sync Gmail automation settings from web interface to production database."""
    try:
        data = request.get_json()
        
        # Validate required data
        if not data:
            return jsonify({'success': False, 'error': 'No settings data provided'})
        
        # Store in production database (PostgreSQL for production, SQLite for local)
        success = production_db.store_watch_rules(data)
        
        if success:
            # Also save to JSON file for backward compatibility (local development)
            settings_file = 'gmail_automation_settings.json'
            try:
                with open(settings_file, 'w') as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                print(f"[GMAIL] Warning: Could not save to JSON file: {e}")
            
            print(f"[GMAIL] Settings synced to production database")
            print(f"[GMAIL] Auto-scan enabled: {data.get('enableAutoScan', False)}")
            print(f"[GMAIL] Watch rules: {len(data.get('watchRules', []))}")
            
            return jsonify({
                'success': True, 
                'message': 'Gmail settings synced to production database',
                'database': 'PostgreSQL' if production_db.is_production else 'SQLite'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to store settings in database'})
        
    except Exception as e:
        print(f"Error syncing Gmail settings: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/send-tracked-updates', methods=['POST'])
@login_required
def send_tracked_updates():
    """Send WhatsApp updates with proper message tracking."""
    try:
        data = request.get_json()
        selected_cards = data.get('selected_cards', [])
        
        if not selected_cards:
            return jsonify({'success': False, 'error': 'No cards selected'})
        
        # Initialize Trello client
        try:
            trello_client = CustomTrelloClient()
            boards = trello_client.list_boards()
            board = None
            
            for b in boards:
                if 'eeinteractive' in b.name.lower():
                    board = b
                    break
            
            if not board:
                return jsonify({'success': False, 'error': 'EEInteractive board not found'})
                
        except Exception as e:
            return jsonify({'success': False, 'error': f'Trello connection failed: {str(e)}'})
        
        sent_messages = []
        failed_messages = []
        blocked_messages = []
        
        # Process each selected card
        for card_id in selected_cards:
            try:
                # Find the card
                card = None
                cards = board.get_cards()
                for c in cards:
                    if c.id == card_id:
                        card = c
                        break
                
                if not card:
                    failed_messages.append({
                        'card_id': card_id,
                        'error': 'Card not found'
                    })
                    continue
                
                # Get enhanced assignment
                assigned_user, assigned_whatsapp, all_assignments = get_enhanced_card_assignment(card, "")
                
                if not assigned_user or not assigned_whatsapp:
                    failed_messages.append({
                        'card': card.name,
                        'error': 'No assignee or WhatsApp number found'
                    })
                    continue
                
                # Check if message can be sent (cooldown/limits)
                can_send, reason = message_tracker.can_send_message(card.id, assigned_user)
                
                if not can_send:
                    blocked_messages.append({
                        'card': card.name,
                        'user': assigned_user,
                        'reason': reason
                    })
                    continue
                
                # Prepare WhatsApp message
                message_text = f"""🔔 Task Reminder

📋 **Card:** {card.name}

⏰ **Due Date:** Please provide update

📍 **Status:** Needs update from you

Please check your Trello card and provide a status update on your progress.

🔗 **View Card:** https://trello.com/c/{card.id}

Reply with your current status or any blockers you're facing.

---
📱 Auto-reminder from Team Management System"""
                
                # Send WhatsApp message
                api_url = f"https://api.green-api.com/waInstance{os.getenv('GREEN_API_INSTANCE')}/sendMessage/{os.getenv('GREEN_API_TOKEN')}"
                
                payload = {
                    "chatId": assigned_whatsapp,
                    "message": message_text
                }
                
                response = requests.post(api_url, json=payload, timeout=10)
                
                if response.status_code == 200:
                    # Log the message in tracker
                    message_tracker.log_message(
                        card_id=card.id,
                        card_name=card.name,
                        assignee_name=assigned_user,
                        assignee_phone=assigned_whatsapp,
                        message_content=message_text,
                        delivery_status='sent'
                    )
                    
                    sent_messages.append({
                        'card': card.name,
                        'user': assigned_user,
                        'phone': assigned_whatsapp
                    })
                    print(f"Sent tracked update to {assigned_user} for card: {card.name}")
                    
                else:
                    failed_messages.append({
                        'card': card.name,
                        'user': assigned_user,
                        'error': f"WhatsApp API error: {response.status_code}"
                    })
                    print(f"Failed to send to {assigned_user}: {response.status_code}")
                    
            except Exception as e:
                failed_messages.append({
                    'card': getattr(card, 'name', card_id),
                    'error': f"Error: {str(e)}"
                })
                print(f"Error processing card {card_id}: {e}")
        
        return jsonify({
            'success': True,
            'messages_sent': len(sent_messages),
            'messages_failed': len(failed_messages),
            'messages_blocked': len(blocked_messages),
            'sent_details': sent_messages,
            'failed_details': failed_messages,
            'blocked_details': blocked_messages
        })
        
    except Exception as e:
        print(f"Error in send_tracked_updates: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ===== PRODUCTION COMPONENT INITIALIZATION =====

def init_production_components():
    """Initialize components needed for production deployment"""
    print("[PROD] Initializing production components...")
    
    # Start automated scanner
    start_automated_scanner()
    
    # Initialize Gmail tracker and scheduler
    global gmail_tracker, gmail_scheduler
    if gmail_tracker and hasattr(gmail_tracker, 'gmail_service') and gmail_tracker.gmail_service:
        gmail_scheduler = GmailScheduler(gmail_tracker)
        gmail_scheduler.start_scheduler()
        print("[PROD] Gmail scheduler started")
    else:
        print("[PROD] Gmail service not available - scheduler not started")
    
    print(f"[PROD] Database: {'PostgreSQL' if production_db.is_production else 'SQLite'}")
    print("[PROD] Production components initialized")

# ===== ENHANCED TEAM TRACKER API ENDPOINTS =====

@app.route('/api/team-tracker/card-details/<card_id>', methods=['GET'])
@login_required
def get_card_details(card_id):
    """Get detailed information about a specific card including message history"""
    try:
        # Get card status from enhanced team tracker database
        card_status = production_db.get_team_tracker_card(card_id)
        
        # Get assignee's last comment date
        if card_status:
            assignee = card_status['assignee_name']
            last_comment = enhanced_team_tracker.get_assignee_last_comment_date(card_id, assignee)
            
            return jsonify({
                'success': True,
                'card_status': card_status,
                'last_assignee_comment': last_comment.isoformat() if last_comment else None,
                'escalation_info': {
                    'current_level': card_status.get('escalation_level', 0),
                    'message_count': card_status.get('message_count', 0),
                    'next_followup': enhanced_team_tracker.calculate_escalation_schedule(card_status.get('message_count', 0))
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Card not found in tracking database'})
            
    except Exception as e:
        print(f"Error getting card details: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/team-tracker/team-members', methods=['GET'])
@login_required
def get_team_members():
    try:
        # Get team members from database
        db_members = enhanced_team_tracker.db.get_team_members()
        
        members = []
        for name, whatsapp in db_members.items():
            members.append({
                'name': name,
                'whatsapp': whatsapp
            })
        
        # If no database members, seed and return
        if not members:
            enhanced_team_tracker.db.seed_team_members()
            db_members = enhanced_team_tracker.db.get_team_members()
            members = [{'name': name, 'whatsapp': whatsapp} for name, whatsapp in db_members.items()]
        
        return jsonify({
            'success': True,
            'members': members
        })
        
    except Exception as e:
        print(f"Error getting team members: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/team-tracker/team-members', methods=['POST'])
@login_required
def add_team_member():
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        whatsapp = data.get('whatsapp', '').strip()
        
        if not name or not whatsapp:
            return jsonify({'success': False, 'error': 'Name and WhatsApp number are required'})
        
        # Add to database
        success = enhanced_team_tracker.db.update_team_member(name, whatsapp, True)
        if not success:
            return jsonify({'success': False, 'error': 'Failed to add team member to database'})
        
        # Reload team members from database
        enhanced_team_tracker.team_members = enhanced_team_tracker._load_team_members()
        
        return jsonify({'success': True, 'message': 'Team member added successfully'})
        
    except Exception as e:
        print(f"Error adding team member: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/team-tracker/team-members', methods=['PUT'])
@login_required
def update_team_member():
    try:
        data = request.get_json()
        original_name = data.get('originalName', '').strip()
        new_name = data.get('newName', '').strip()
        whatsapp = data.get('whatsapp', '').strip()
        
        if not original_name or not new_name or not whatsapp:
            return jsonify({'success': False, 'error': 'All fields are required'})
        
        # If name changed, deactivate old and create new
        if original_name != new_name:
            enhanced_team_tracker.db.delete_team_member(original_name)
        
        # Update/create new entry
        success = enhanced_team_tracker.db.update_team_member(new_name, whatsapp, True)
        if not success:
            return jsonify({'success': False, 'error': 'Failed to update team member in database'})
        
        # Reload team members from database
        enhanced_team_tracker.team_members = enhanced_team_tracker._load_team_members()
        
        return jsonify({'success': True, 'message': 'Team member updated successfully'})
        
    except Exception as e:
        print(f"Error updating team member: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/team-tracker/team-members', methods=['DELETE'])
@login_required
def remove_team_member():
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'})
        
        # Remove from database
        success = enhanced_team_tracker.db.delete_team_member(name)
        if not success:
            return jsonify({'success': False, 'error': 'Failed to remove team member from database'})
        
        # Reload team members from database
        enhanced_team_tracker.team_members = enhanced_team_tracker._load_team_members()
        
        return jsonify({'success': True, 'message': 'Team member removed successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/team-tracker/populate-history', methods=['POST'])
@login_required
def populate_history():
    """Populate database with complete historical data from all cards."""
    try:
        print("=== POPULATING HISTORICAL DATA ===")
        
        if not trello_client:
            return jsonify({'success': False, 'error': 'Trello client not available'})
        
        # Get the EEInteractive board
        boards = trello_client.list_boards()
        eeinteractive_board = None
        for board in boards:
            if 'eeinteractive' in board.name.lower():
                eeinteractive_board = board
                break
        
        if not eeinteractive_board:
            return jsonify({'success': False, 'error': 'EEInteractive board not found'})
        
        # Get ALL cards from ALL lists
        all_cards = eeinteractive_board.get_cards()
        total_cards = len(all_cards)
        
        activities_collected = 0
        comments_collected = 0
        
        for card in all_cards:
            try:
                # Get recent comments for this card (limit to prevent timeouts)
                actions = trello_client.fetch_json(f'/cards/{card.id}/actions', 
                    query_params={'filter': 'commentCard', 'limit': 50})  # Reduced from 1000
                
                for action in actions:
                    comments_collected += 1
                    # Store in database if needed
                    if enhanced_team_tracker and enhanced_team_tracker.db:
                        # Store comment data for analysis
                        member_name = action.get('memberCreator', {}).get('fullName', '')
                        comment_text = action.get('data', {}).get('text', '')
                        comment_date = action.get('date', '')
                        
                        # You could store this in a new comments table if needed
                        print(f"Comment on {card.name} by {member_name}: {comment_text[:50]}...")
                
                activities_collected += len(actions)
                
            except Exception as e:
                print(f"Error collecting history for card {card.name}: {e}")
                continue
        
        return jsonify({
            'success': True,
            'message': f'Populated history from {total_cards} cards',
            'stats': {
                'total_cards': total_cards,
                'activities': activities_collected,
                'comments': comments_collected
            }
        })
        
    except Exception as e:
        print(f"Error removing team member: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/team-tracker/cards', methods=['GET'])
@login_required
def get_tracker_cards():
    """Get existing cards from database without scanning."""
    try:
        if not enhanced_team_tracker or not enhanced_team_tracker.db:
            return jsonify({'success': False, 'error': 'Team tracker not initialized'})
        
        # Get cards from database
        cards = enhanced_team_tracker.db.get_all_cards()
        
        # Format cards for display
        formatted_cards = []
        for card in cards:
            formatted_cards.append({
                'id': card['card_id'],
                'name': card['card_name'],
                'list_name': card['list_name'],
                'assigned_user': card['assigned_user'],
                'hours_since_assigned_update': card.get('hours_since_assigned_update', 999),
                'message_count': card.get('message_count', 0),
                'next_message_due': card.get('next_message_due'),
                'needs_update': card.get('needs_update', False),
                'last_message_sent': card.get('last_message_sent'),
                'response_detected': card.get('response_detected', False)
            })
        
        return jsonify({'success': True, 'cards': formatted_cards})
        
    except Exception as e:
        print(f"Error getting tracker cards: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/team-tracker/card/<card_id>', methods=['DELETE'])
@login_required
def delete_tracker_card(card_id):
    """Delete a specific card from tracking."""
    try:
        if not enhanced_team_tracker or not enhanced_team_tracker.db:
            return jsonify({'success': False, 'error': 'Team tracker not initialized'})
        
        # Delete card from database
        success = enhanced_team_tracker.db.delete_card(card_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Card deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete card'})
        
    except Exception as e:
        print(f"Error deleting tracker card: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/team-tracker/reset-team', methods=['POST'])
@login_required
def reset_team_members():
    """Reset team members to default list."""
    try:
        if not enhanced_team_tracker or not enhanced_team_tracker.db:
            return jsonify({'success': False, 'error': 'Team tracker not initialized'})
        
        # Clear all team members
        enhanced_team_tracker.db.clear_team_members()
        
        # Reseed with defaults
        enhanced_team_tracker.db.seed_team_members()
        
        # Reload team members
        enhanced_team_tracker.team_members = enhanced_team_tracker._load_team_members()
        
        return jsonify({'success': True, 'message': 'Team members reset to defaults'})
        
    except Exception as e:
        print(f"Error resetting team members: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/team-tracker/stats', methods=['GET'])
@login_required
def get_enhanced_team_stats():
    """Get enhanced team tracker statistics"""
    try:
        # Get message stats from existing system
        today_stats = message_tracker.get_daily_analytics()
        
        # Get enhanced stats from production database
        conn = production_db.get_connection()
        cursor = conn.cursor()
        
        # Count responses today
        if production_db.is_production:
            cursor.execute("""
                SELECT COUNT(*) FROM team_tracker_messages 
                WHERE response_detected_at >= CURRENT_DATE
            """)
        else:
            cursor.execute("""
                SELECT COUNT(*) FROM team_tracker_messages 
                WHERE response_detected_at >= date('now')
            """)
        
        responses_result = cursor.fetchone()
        responses_today = responses_result[0] if responses_result else 0
        
        # Count active cards being tracked
        cursor.execute("SELECT COUNT(*) FROM team_tracker_cards WHERE status = 'active'")
        active_result = cursor.fetchone()
        active_cards = active_result[0] if active_result else 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'today_messages': today_stats.get('messages_sent', 0) if today_stats else 0,
            'responses_today': responses_today,
            'active_cards': active_cards,
            'team_members': len(enhanced_team_tracker.team_members)
        })
        
    except Exception as e:
        print(f"Error getting enhanced team stats: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/team-tracker/mark-responded', methods=['POST'])
@login_required
def mark_card_responded():
    """Mark that an assignee has responded to a card"""
    try:
        data = request.get_json()
        card_id = data.get('card_id')
        
        if not card_id:
            return jsonify({'success': False, 'error': 'Card ID required'})
        
        success = production_db.mark_team_tracker_response(card_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Card marked as responded'})
        else:
            return jsonify({'success': False, 'error': 'Failed to mark card as responded'})
            
    except Exception as e:
        print(f"Error marking card responded: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ==================== TEAM MANAGEMENT SETTINGS API ====================

@app.route('/api/team-tracker/settings', methods=['GET'])
def get_team_tracker_settings():
    """Get current team tracker settings from database."""
    try:
        # Get settings from database or use defaults
        db = production_db or get_production_db()
        
        # Initialize settings table if needed
        if db:
            db.init_settings_table()
        
        settings = {
            'escalation_intervals': db.get_setting('escalation_intervals', [24, 12, 6, 4]) if db else [24, 12, 6, 4],
            'enable_escalation': db.get_setting('enable_escalation', True) if db else True,
            'enable_group_messages': db.get_setting('enable_group_messages', True) if db else True,
            'enable_individual_messages': db.get_setting('enable_individual_messages', True) if db else True,
            'working_hours_start': db.get_setting('working_hours_start', '09:00') if db else '09:00',
            'working_hours_end': db.get_setting('working_hours_end', '17:00') if db else '17:00',
            'working_days': db.get_setting('working_days', ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']) if db else ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        }
        
        return jsonify({'success': True, 'settings': settings})
        
    except Exception as e:
        print(f"Error getting team tracker settings: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/team-tracker/settings', methods=['POST'])
def save_team_tracker_settings():
    """Save team tracker settings."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'})
        
        # Extract settings from request
        settings = data.get('settings', {})
        
        # Validate escalation intervals
        escalation_intervals = settings.get('escalation_intervals', [24, 12, 6, 4])
        if not isinstance(escalation_intervals, list) or len(escalation_intervals) != 4:
            return jsonify({'success': False, 'error': 'Invalid escalation intervals'})
        
        # Save settings to database
        db = production_db or get_production_db()
        if db:
            db.init_settings_table()
            import json
            
            # Save each setting
            db.save_setting('escalation_intervals', json.dumps(escalation_intervals), 'json')
            db.save_setting('enable_escalation', str(settings.get('enable_escalation', True)).lower(), 'bool')
            db.save_setting('enable_group_messages', str(settings.get('enable_group_messages', True)).lower(), 'bool')
            db.save_setting('enable_individual_messages', str(settings.get('enable_individual_messages', True)).lower(), 'bool')
            db.save_setting('working_hours_start', settings.get('working_hours_start', '09:00'), 'string')
            db.save_setting('working_hours_end', settings.get('working_hours_end', '17:00'), 'string')
            db.save_setting('working_days', json.dumps(settings.get('working_days', ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'])), 'json')
            
            print(f"SETTINGS SAVE: Saved team tracker settings to database")
        else:
            print(f"SETTINGS SAVE: No database available, settings not persisted")
        
        return jsonify({'success': True, 'message': 'Settings saved successfully'})
        
    except Exception as e:
        print(f"Error saving team tracker settings: {e}")
        return jsonify({'success': False, 'error': str(e)})

# Initialize components when module is imported (for Gunicorn)
if os.getenv('RENDER') or os.getenv('DATABASE_URL'):
    print("[PROD] Production environment detected - initializing components")
    init_production_components()

# ===== APPLICATION STARTUP =====

if __name__ == '__main__':
    print("Starting Complete Multi-App Web Interface...")
    print(f"AI modules available: SpeakerAnalyzer={SpeakerAnalyzer is not None}")
    print("Features: Google Docs reading, Trello card matching, and automatic commenting")
    print(f"Registered routes: {[rule.rule for rule in app.url_map.iter_rules()]}")
    
    # Start automated scanner
    start_automated_scanner()
    
    # Start Gmail scheduler if available  
    if gmail_tracker and gmail_tracker.gmail_service:
        gmail_scheduler = GmailScheduler(gmail_tracker)
        gmail_scheduler.start_scheduler()
    
    # Use Render's PORT environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV', 'development') == 'development'
    
    print(f"Starting on port {port} with debug={debug_mode}")
    app.run(debug=debug_mode, host='0.0.0.0', port=port)