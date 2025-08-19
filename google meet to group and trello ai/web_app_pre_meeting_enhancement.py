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

# Team member data
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

# Initialize database
db = DatabaseManager() if DatabaseManager else None

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

# ===== MAIN ROUTES =====

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/google-meet')
def google_meet_app():
    return render_template('google_meet_app.html')

@app.route('/team-tracker')
def team_tracker_app():
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
    """Extract text from Google Docs using export URL with timeout protection."""
    try:
        print(f"Attempting to fetch Google Doc: {doc_id}")
        
        # Try multiple approaches for different document permissions
        export_urls = [
            f"https://docs.google.com/document/d/{doc_id}/export?format=txt",
            f"https://docs.google.com/document/u/0/d/{doc_id}/export?format=txt"
        ]
        
        for i, url in enumerate(export_urls):
            try:
                print(f"Trying URL method {i+1}: {url}")
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
                print(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    text = response.text
                    print(f"Retrieved text length: {len(text)}")
                    
                    # Check if it's actual content
                    if len(text) > 50 and not text.startswith('<!DOCTYPE'):
                        content_indicators = ['transcript', ':', 'said', 'meeting', 'discussion']
                        
                        if any(indicator.lower() in text.lower() for indicator in content_indicators) or len(text) > 200:
                            print("Valid transcript content detected")
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
        print(f"Critical error fetching Google Doc: {e}")
        return None

# ===== ENHANCED ASSIGNMENT DETECTION SYSTEM =====

def get_card_checklists(card_id):
    """Read Trello card checklists to find assignments."""
    try:
        api_key = os.environ.get('TRELLO_API_KEY')
        token = os.environ.get('TRELLO_TOKEN')
        
        if not api_key or not token:
            print(f"  CHECKLISTS: Missing Trello API credentials")
            return []
        
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
            
            # Look for assignment-related checklists
            if any(keyword in checklist_name for keyword in ['assign', 'team', 'member', 'responsible']):
                print(f"  CHECKLISTS: Found assignment checklist: {checklist['name']}")
                
                for item in check_items:
                    item_text = item.get('name', '').lower()
                    
                    # Check if item contains team member names
                    for team_member, whatsapp in TEAM_MEMBERS.items():
                        member_lower = team_member.lower()
                        
                        # Skip admin and criselle
                        if member_lower in ['admin', 'criselle']:
                            continue
                        
                        # Check if member is mentioned in checklist item
                        if (member_lower in item_text or 
                            f"@{member_lower}" in item_text or
                            any(word in item_text for word in [member_lower, team_member.lower()])):
                            
                            assigned_members.append({
                                'name': team_member,
                                'whatsapp': whatsapp,
                                'source': f"Checklist: {checklist['name']} - {item['name']}",
                                'confidence': 90
                            })
                            print(f"  CHECKLISTS: Found {team_member} in checklist item: {item['name']}")
            
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
        
        # Get recent comments
        url = f"https://api.trello.com/1/cards/{card_id}/actions"
        params = {
            'filter': 'commentCard',
            'limit': 20,
            'key': api_key,
            'token': token
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return None
        
        comments = response.json()
        
        for comment in comments:
            commenter_name = comment.get('memberCreator', {}).get('fullName', '').lower()
            
            # Skip admin and criselle
            if 'admin' in commenter_name or 'criselle' in commenter_name:
                continue
            
            # Check if commenter matches our team members
            for team_member, whatsapp in TEAM_MEMBERS.items():
                if (team_member.lower() in commenter_name or 
                    commenter_name in team_member.lower()):
                    return {
                        'name': team_member,
                        'whatsapp': whatsapp,
                        'source': f"Last commenter: {comment.get('memberCreator', {}).get('fullName', '')}",
                        'confidence': 75,
                        'comment_date': comment.get('date', '')
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
        
        # Use enhanced AI for intelligent matching if available
        try:
            from enhanced_ai import EnhancedAI
            ai_engine = EnhancedAI()
            
            # Prepare simplified card data (no member/action calls that can hang)
            simple_cards = []
            for card in cards[:20]:  # Limit to 20 cards for speed
                if not card.closed:
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
            print("Using fallback keyword matching...")
            
            transcript_lower = transcript_text.lower()
            
            for card in cards[:30]:  # Limit for speed
                if card.closed:
                    continue
                
                # Skip if already matched by AI
                if any(match.get('id') == card.id for match in matched_cards):
                    continue
                
                confidence = 0
                card_name_lower = card.name.lower()
                
                # Direct name matching
                if card_name_lower in transcript_lower:
                    confidence += 70
                
                # Word-by-word matching
                card_words = card_name_lower.split()
                for word in card_words:
                    if len(word) > 3 and word in transcript_lower:
                        confidence += 15
                
                if confidence >= 40:  # Lower threshold for fallback
                    matched_cards.append({
                        'id': card.id,
                        'name': card.name,
                        'url': card.url,
                        'confidence': min(100, confidence),
                        'description': card.description[:200] if card.description else '',
                        'board_name': eeinteractive_board.name,
                        'match_type': 'keyword_fallback'
                    })
        
        # Sort by confidence
        matched_cards.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        total_time = time.time() - start_time
        print(f"Card matching completed in {total_time:.2f}s, found {len(matched_cards)} matches")
        
        return matched_cards[:10]  # Return top 10 matches
        
    except Exception as e:
        print(f"Error in fast card matching: {e}")
        return []

def generate_meeting_comment(transcript_text, card_name, match_context="", card_id=None):
    """Generate a structured comment for Trello card based on meeting transcript with enhanced assignment detection."""
    try:
        # Extract participants and key info
        participants = extract_participants_fast(transcript_text)
        action_items = extract_action_items_fast(transcript_text)
        
        # Get assignment information using enhanced detection
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
                    assignment_info.append("**Assignment Analysis:**")
                    for i, assignment in enumerate(all_assignments[:3], 1):  # Top 3 assignments
                        confidence_emoji = "🎯" if assignment['confidence'] >= 85 else "📝" if assignment['confidence'] >= 70 else "💭"
                        assignment_info.append(f"{confidence_emoji} **{assignment['name']}** - {assignment['source']} (confidence: {assignment['confidence']}%)")
                    assignment_info.append("")
                    
                    # Highlight primary assignee
                    if assigned_user:
                        assignment_info.append(f"**📌 Primary Assignee:** {assigned_user}")
                        assignment_info.append("")
                        
            except Exception as e:
                print(f"Error in assignment detection for comment: {e}")
        
        # Find relevant quotes about this card (enhanced)
        card_quotes = []
        assignment_quotes = []
        lines = transcript_text.split('\n')
        card_name_lower = card_name.lower()
        
        for line in lines:
            line = line.strip()
            if not line or '[' in line:  # Skip timestamps
                continue
            
            # Check if line mentions this card
            card_mentioned = any(word in line.lower() for word in card_name_lower.split() if len(word) > 3)
            
            # Check if line contains assignment language
            assignment_mentioned = any(keyword in line.lower() for keyword in [
                'assign', 'responsible', 'handle', 'take care', 'work on', 'can you', 'please'
            ])
            
            if card_mentioned or assignment_mentioned:
                # Extract speaker and content
                speaker_match = re.match(r'^([A-Za-z][A-Za-z\s]+?):\s*(.+)$', line)
                if speaker_match:
                    speaker = speaker_match.group(1).strip()
                    content = speaker_match.group(2).strip()
                    
                    # Skip admin/criselle quotes
                    if 'admin' in speaker.lower() or 'criselle' in speaker.lower():
                        continue
                    
                    if card_mentioned:
                        card_quotes.append(f"• **{speaker}**: {content}")
                    elif assignment_mentioned:
                        assignment_quotes.append(f"• **{speaker}**: {content}")
        
        # Build enhanced comment
        comment_parts = [
            f"📅 **Meeting Update - {datetime.now().strftime('%B %d, %Y')}**",
            "",
            f"**Discussion Summary:** This card was discussed in today's team meeting with assignment analysis completed.",
            ""
        ]
        
        # Add assignment information first (most important)
        if assignment_info:
            comment_parts.extend(assignment_info)
        
        # Add direct quotes about the card
        if card_quotes:
            comment_parts.extend([
                "**Direct Quotes (Card Discussion):**",
                *card_quotes[:3],  # Limit to 3 quotes
                ""
            ])
        
        # Add assignment-related quotes
        if assignment_quotes and not card_quotes:  # Only if no direct card quotes
            comment_parts.extend([
                "**Assignment Discussion:**",
                *assignment_quotes[:2],  # Limit to 2 quotes
                ""
            ])
        
        if participants:
            comment_parts.extend([
                f"**Meeting Participants:** {', '.join(participants)}",
                ""
            ])
        
        # Add relevant action items (enhanced)
        relevant_actions = []
        for action in action_items:
            task_text = action.get('task', '').lower()
            assignee = action.get('assignee', 'TBD')
            
            # Skip actions assigned to admin/criselle
            if 'admin' in assignee.lower() or 'criselle' in assignee.lower():
                continue
            
            if any(word in task_text for word in card_name_lower.split() if len(word) > 3):
                relevant_actions.append(f"• **{assignee}**: {action.get('task', '')}")
        
        if relevant_actions:
            comment_parts.extend([
                "**Action Items:**",
                *relevant_actions[:2],  # Limit to 2 action items
                ""
            ])
        
        if match_context:
            comment_parts.extend([
                f"**Match Context:** {match_context}",
                ""
            ])
        
        comment_parts.extend([
            "**Next Steps:** Please update this card with current progress and any blockers.",
            "**Note:** If you're assigned to this card, please confirm and provide status update.",
            "",
            "---",
            "*Auto-generated from meeting transcript with enhanced assignment detection*"
        ])
        
        return '\n'.join(comment_parts)
        
    except Exception as e:
        print(f"Error generating enhanced comment: {e}")
        return f"📅 Meeting Update - {datetime.now().strftime('%B %d, %Y')}\n\nThis card was discussed in today's team meeting. Enhanced assignment detection encountered an error.\n\nPlease update with current status and confirm assignment.\n\n---\n*Auto-generated from meeting transcript*"

@app.route('/api/process-transcript', methods=['POST'])
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
            
            # Get document text
            transcript_text = get_google_doc_text(doc_id)
            if not transcript_text:
                return jsonify({'success': False, 'error': 'Could not fetch document or document is empty'})
            
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
        
        # Initialize results
        analysis_results = {}
        
        # Fast speaker analysis
        if SpeakerAnalyzer:
            try:
                analyzer = SpeakerAnalyzer()
                speaker_analysis = analyzer.analyze_transcript(transcript_text)
                analysis_results['speaker_analysis'] = speaker_analysis
                print(f"Speaker analysis completed")
            except Exception as e:
                print(f"Speaker analysis failed: {e}")
                analysis_results['speaker_analysis'] = {'error': str(e)}
        
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
        
        # Fast card matching
        matched_cards = []
        try:
            matched_cards = scan_trello_cards_fast(transcript_text)
            print(f"Card matching completed: {len(matched_cards)} matches")
        except Exception as e:
            print(f"Card matching failed: {e}")
        
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
                    
                    # Generate enhanced comment with assignment detection
                    comment_text = generate_meeting_comment(
                        transcript_text, 
                        card_name, 
                        card_match.get('context', ''),
                        card_id  # Pass card_id for enhanced assignment detection
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
        
        # Fast summary generation
        summary_data = {}
        try:
            participants = extract_participants_fast(transcript_text)
            action_items = extract_action_items_fast(transcript_text)
            
            summary_data = {
                'participants': participants,
                'action_items': action_items,
                'word_count': len(transcript_text.split()),
                'meeting_duration_estimate': estimate_duration_fast(transcript_text),
                'comments_posted': comments_posted,
                'comment_errors': comment_errors
            }
            print(f"Summary generation completed")
            
        except Exception as e:
            print(f"Summary generation failed: {e}")
            summary_data = {'error': str(e)}
        
        # Store results
        app_data['speaker_analyses'].append({
            'timestamp': datetime.now().isoformat(),
            'source_type': source_type,
            'source_url': source_url,
            'analysis': analysis_results,
            'summary': summary_data,
            'matched_cards': matched_cards
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
            'processing_time': total_time
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
    """Get recent activity from Trello cards - last 24 hours only."""
    try:
        data = request.json or {}
        days = 1  # Force to 24 hours only
        
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
def scan_cards():
    """Scan Trello cards for team tracker - EEInteractive board only, DOING/IN PROGRESS lists."""
    print("=== SCAN CARDS ROUTE CALLED ===")
    try:
        print("=== SCANNING TRELLO CARDS FOR TEAM TRACKER ===")
        start_time = time.time()
        
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
        
        # Find DOING/IN PROGRESS lists only
        target_lists = []
        print(f"Available lists on board:")
        for lst in board_lists:
            print(f"  - {lst.name} (ID: {lst.id})")
            list_name_lower = lst.name.lower()
            if 'doing' in list_name_lower or 'in progress' in list_name_lower:
                target_lists.append(lst.id)
                print(f"TARGET: Found target list: {lst.name}")
        
        if not target_lists:
            print("ERROR: No DOING/IN PROGRESS lists found")
            return jsonify({'success': False, 'error': 'No DOING/IN PROGRESS lists found'})
        
        all_cards = []
        cards_needing_updates = []
        
        # Get cards from EEInteractive board only
        board_cards = eeinteractive_board.list_cards()
        
        for card in board_cards:
            if card.closed:
                print(f"SKIP: Closed card: {card.name}")
                continue
            
            # Debug: Show which list each card is in
            card_list_name = list_names.get(card.list_id, 'Unknown')
            print(f"CARD: '{card.name}' is in list: {card_list_name}")
            
            # Only process cards in DOING/IN PROGRESS lists
            if card.list_id not in target_lists:
                print(f"SKIP: Card '{card.name}' - not in target lists")
                continue
            
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
            
            # Extract assigned user from checklists and comments
            assigned_user = None
            assigned_whatsapp = None
            
            try:
                print(f"SEARCH: Looking for assigned user for card: {card.name}")
                
                # Method 1: Check card description for team member names and @mentions
                card_description = (card.description or '').lower()
                card_name_lower = card.name.lower()
                print(f"  DESCRIPTION: '{card_description[:100]}...'")
                print(f"  CARD NAME: '{card_name_lower}'")
                
                # Check for @mentions and direct name references
                for member_name, whatsapp_num in TEAM_MEMBERS.items():
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
                            for team_member_name, whatsapp_num in TEAM_MEMBERS.items():
                                if team_member_name.lower() in member_name_lower or member_name_lower in team_member_name.lower():
                                    assigned_user = team_member_name
                                    assigned_whatsapp = whatsapp_num
                                    print(f"FOUND: Assigned user from Trello members: {team_member_name}")
                                    break
                            if assigned_user:
                                break
                                
                    except Exception as e:
                        print(f"  MEMBERS: Could not access Trello members: {e}")
                
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
                                    for team_member_name, whatsapp_num in TEAM_MEMBERS.items():
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
                    
                    # Content-based assignments
                    if any(keyword in card_content for keyword in ['mobile', 'app', 'ios', 'android']):
                        assigned_user = 'Wendy'
                        assigned_whatsapp = TEAM_MEMBERS.get('Wendy')
                        print(f"FOUND: Mobile/App content assigned to Wendy")
                    elif any(keyword in card_content for keyword in ['website', 'web', 'wordpress', 'landing', 'page']):
                        assigned_user = 'Lancey'
                        assigned_whatsapp = TEAM_MEMBERS.get('Lancey')
                        print(f"FOUND: Website content assigned to Lancey")
                    elif any(keyword in card_content for keyword in ['design', 'logo', 'brand', 'graphics']):
                        assigned_user = 'Breyden'
                        assigned_whatsapp = TEAM_MEMBERS.get('Breyden')
                        print(f"FOUND: Design content assigned to Breyden")
                    elif any(keyword in card_content for keyword in ['automation', 'integration', 'api', 'webhook']):
                        assigned_user = 'Ezechiel'
                        assigned_whatsapp = TEAM_MEMBERS.get('Ezechiel')
                        print(f"FOUND: Automation content assigned to Ezechiel")
                    
            except Exception as e:
                print(f"Error extracting assigned user for card {card.name}: {e}")
            
            # If no assigned user found, skip this card for updates
            if not assigned_user:
                print(f"ERROR: No assigned user found for card: {card.name}")
                print(f"   Available team members: {list(TEAM_MEMBERS.keys())}")
                continue
            else:
                print(f"SUCCESS: Assigned user found: {assigned_user} -> {assigned_whatsapp}")
            
            # AI-powered analysis to determine if assigned user has provided updates
            assigned_user_last_update_hours = 999  # Default to very high
            needs_update = True  # Default to needs update
            
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
                            assigned_user_last_update_hours = 999
                    
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
                'hours_since_assigned_update': round(assigned_user_last_update_hours, 1),  # Assigned user activity
                'days_since_comment': round(assigned_user_last_update_hours / 24, 1),  # Based on assigned user
                'needs_update': needs_update,  # AI-determined
                'last_activity': card.date_last_activity,
                'priority': 'high' if assigned_user_last_update_hours > 72 else 'medium' if assigned_user_last_update_hours > 24 else 'normal'
            }
            
            all_cards.append(card_data)
            
            # Add to cards needing updates if over 24 hours
            if needs_update:
                cards_needing_updates.append(card_data)
        
        # Sort by hours since assigned user update (most urgent first)
        all_cards.sort(key=lambda x: x['hours_since_assigned_update'], reverse=True)
        cards_needing_updates.sort(key=lambda x: x['hours_since_assigned_update'], reverse=True)
        
        # Store in app_data for other endpoints
        app_data['all_cards'] = all_cards
        app_data['cards_needing_updates'] = cards_needing_updates
        
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
                'hours_since_update': card_data.get('hours_since_assigned_update', 0),
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
                    'urgency': 'high' if any(c['hours_since_update'] > 72 for c in regular_cards) else 'medium',
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

# ===== APPLICATION STARTUP =====

if __name__ == '__main__':
    print("Starting Complete Multi-App Web Interface...")
    print(f"AI modules available: SpeakerAnalyzer={SpeakerAnalyzer is not None}")
    print("Features: Google Docs reading, Trello card matching, and automatic commenting")
    print(f"Registered routes: {[rule.rule for rule in app.url_map.iter_rules()]}")
    app.run(debug=True, host='0.0.0.0', port=5000)  # Restored to original port 5000