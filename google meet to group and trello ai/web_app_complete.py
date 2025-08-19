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

def generate_meeting_comment(transcript_text, card_name, match_context=""):
    """Generate a structured comment for Trello card based on meeting transcript."""
    try:
        # Extract participants and key info
        participants = extract_participants_fast(transcript_text)
        action_items = extract_action_items_fast(transcript_text)
        
        # Find relevant quotes about this card
        card_quotes = []
        lines = transcript_text.split('\n')
        card_name_lower = card_name.lower()
        
        for line in lines:
            line = line.strip()
            if not line or '[' in line:  # Skip timestamps
                continue
            
            # Check if line mentions this card
            if any(word in line.lower() for word in card_name_lower.split() if len(word) > 3):
                # Extract speaker and content
                speaker_match = re.match(r'^([A-Za-z][A-Za-z\s]+?):\s*(.+)$', line)
                if speaker_match:
                    speaker = speaker_match.group(1).strip()
                    content = speaker_match.group(2).strip()
                    card_quotes.append(f"• **{speaker}**: {content}")
        
        # Build comment
        comment_parts = [
            f"📅 **Meeting Update - {datetime.now().strftime('%B %d, %Y')}**",
            "",
            f"**Discussion Summary:** This card was discussed in today's team meeting.",
            ""
        ]
        
        if card_quotes:
            comment_parts.extend([
                "**Direct Quotes:**",
                *card_quotes[:3],  # Limit to 3 quotes
                ""
            ])
        
        if participants:
            comment_parts.extend([
                f"**Meeting Participants:** {', '.join(participants)}",
                ""
            ])
        
        # Add relevant action items
        relevant_actions = []
        for action in action_items:
            task_text = action.get('task', '').lower()
            if any(word in task_text for word in card_name_lower.split() if len(word) > 3):
                relevant_actions.append(f"• **{action.get('assignee', 'TBD')}**: {action.get('task', '')}")
        
        if relevant_actions:
            comment_parts.extend([
                "**Action Items:**",
                *relevant_actions[:2],  # Limit to 2 action items
                ""
            ])
        
        if match_context:
            comment_parts.extend([
                f"**Context:** {match_context}",
                ""
            ])
        
        comment_parts.extend([
            "**Next Steps:** Please update this card with current progress and any blockers.",
            "",
            "---",
            "*Auto-generated from meeting transcript analysis*"
        ])
        
        return '\n'.join(comment_parts)
        
    except Exception as e:
        print(f"Error generating comment: {e}")
        return f"📅 Meeting Update - {datetime.now().strftime('%B %d, %Y')}\n\nThis card was discussed in today's team meeting. Please update with current status.\n\n---\n*Auto-generated from meeting transcript*"

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
                    
                    # Generate comment
                    comment_text = generate_meeting_comment(
                        transcript_text, 
                        card_name, 
                        card_match.get('context', '')
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

# ===== APPLICATION STARTUP =====

if __name__ == '__main__':
    print("Starting Complete Multi-App Web Interface...")
    print(f"AI modules available: SpeakerAnalyzer={SpeakerAnalyzer is not None}")
    print("Features: Google Docs reading, Trello card matching, and automatic commenting")
    app.run(debug=True, host='0.0.0.0', port=5002)  # Use port 5002 for complete version