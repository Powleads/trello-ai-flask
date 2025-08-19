#!/usr/bin/env python3
"""
Google Meet Analytics API - Simplified meeting analysis without Trello
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import traceback
from meeting_analytics import MeetingAnalyzer

# Create blueprint
google_meet_analytics = Blueprint('google_meet_analytics', __name__)

@google_meet_analytics.route('/api/analyze-meeting', methods=['POST'])
def analyze_meeting():
    """
    Analyze a Google Meet transcript for participation and insights.
    No Trello integration - just pure meeting analytics.
    """
    try:
        data = request.json
        doc_url = data.get('doc_url', '').strip()
        
        if not doc_url:
            return jsonify({
                'success': False,
                'error': 'Please provide a Google Doc URL'
            }), 400
        
        # Extract document ID
        import re
        doc_id_match = re.search(r'/document/d/([a-zA-Z0-9-_]+)', doc_url)
        if not doc_id_match:
            return jsonify({
                'success': False,
                'error': 'Invalid Google Doc URL format'
            }), 400
        
        doc_id = doc_id_match.group(1)
        
        # Fetch document content
        print(f"Fetching Google Doc: {doc_id}")
        doc_content, transcript_text = fetch_google_doc_content(doc_id)
        
        if not transcript_text:
            return jsonify({
                'success': False,
                'error': 'Could not fetch document content'
            }), 400
        
        # Analyze meeting
        print("Analyzing meeting transcript...")
        analyzer = MeetingAnalyzer()
        analysis = analyzer.analyze_full_meeting(transcript_text, doc_content)
        
        # Generate narrative summary and extract details
        print("Generating narrative summary...")
        narrative_summary = analyzer.generate_narrative_summary(transcript_text, doc_content, doc_url)
        
        # Extract details for the UI
        details = analyzer._extract_details(transcript_text)
        
        # Format response
        response_data = {
            'success': True,
            'analysis': {
                'overview': {
                    'total_speakers': analysis['participation']['total_speakers'],
                    'total_words': analysis['participation']['total_words'],
                    'total_statements': analysis['participation']['total_statements'],
                    'meeting_date': datetime.now().strftime('%B %d, %Y'),
                    'effectiveness_rating': analysis['effectiveness']['rating'],
                    'overall_score': analysis['effectiveness']['overall_score']
                },
                'participation': {
                    'speakers': analysis['participation']['speakers'],
                    'most_active': analysis['participation']['most_active'],
                    'least_active': analysis['participation']['least_active'],
                    'silent_participants': analysis['silent_participants']
                },
                'engagement': {
                    'average': analysis['engagement']['average_engagement'],
                    'energy': analysis['engagement']['meeting_energy'],
                    'total_questions': analysis['engagement']['total_questions'],
                    'individual': analysis['engagement']['individual']
                },
                'insights': {
                    'decisions': analysis['insights']['decisions'],
                    'action_items': analysis['insights']['action_items'],
                    'key_topics': analysis['insights']['key_topics'],
                    'concerns': analysis['insights']['concerns_raised']
                },
                'effectiveness': {
                    'scores': analysis['effectiveness']['scores'],
                    'overall': analysis['effectiveness']['overall_score'],
                    'rating': analysis['effectiveness']['rating'],
                    'recommendations': analysis['effectiveness']['recommendations']
                },
                'whatsapp_summary': narrative_summary,
                'details': details
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error in meeting analysis: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}'
        }), 500

def fetch_google_doc_content(doc_id):
    """
    Fetch Google Doc content using the fallback public URL method.
    Returns both structured content and raw transcript text.
    """
    import requests
    
    try:
        # Try public export URL
        export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(export_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            text_content = response.text
            
            # Fix encoding issues with special characters
            try:
                # Replace problematic characters for Windows console
                text_content = text_content.encode('utf-8', 'ignore').decode('utf-8')
                # Clean up common problematic characters
                text_content = text_content.replace('\u00a0', ' ')  # non-breaking space
                text_content = text_content.replace('\u2019', "'")  # right single quotation mark
                text_content = text_content.replace('\u201c', '"')  # left double quotation mark
                text_content = text_content.replace('\u201d', '"')  # right double quotation mark
                
                print(f"Full document length: {len(text_content)}")
                print(f"Document preview: {text_content[:500].encode('ascii', 'ignore').decode('ascii')}...")
            except Exception as encoding_error:
                print(f"Encoding error: {encoding_error}")
                # Use safe encoding
                text_content = text_content.encode('ascii', 'ignore').decode('ascii')
            
            # Parse for participants (look for "Invited" or "Attendees" section)
            participants = []
            if 'Invited' in text_content:
                invited_section = text_content.split('Invited')[1].split('\n')[0]
                # Extract names (simple pattern matching)
                import re
                names = re.findall(r'[A-Z][a-z]+ [A-Z][a-z]+', invited_section)
                participants = list(set(names))[:20]  # Limit to 20 participants
            
            # Try to extract Notes and Transcript sections
            notes_content = ""
            transcript_content = text_content  # Default to full content
            
            print(f"Looking for Notes section...")
            if 'Notes' in text_content:
                print("Found 'Notes' in document")
                if 'Transcript' in text_content:
                    print("Found 'Transcript' in document")
                    # Try to extract Notes section
                    try:
                        notes_start = text_content.index('Notes')
                        transcript_start = text_content.index('Transcript')
                        if notes_start < transcript_start:
                            notes_content = text_content[notes_start:transcript_start]
                            transcript_content = text_content[transcript_start:]
                            print(f"Extracted Notes section: {len(notes_content)} characters")
                        else:
                            print("Notes section comes after Transcript - using different approach")
                            notes_content = text_content[:notes_start] if notes_start > 0 else ""
                    except Exception as e:
                        print(f"Error extracting sections: {e}")
                else:
                    print("No 'Transcript' found, extracting Notes from beginning")
                    # If no transcript section, try to extract notes from the beginning
                    notes_end = min(5000, len(text_content))
                    notes_content = text_content[:notes_end]
            else:
                print("No 'Notes' section found in document")
            
            doc_content = {
                'participants': participants,
                'notes_content': notes_content[:5000] if notes_content else "",  # Further increased limit for notes
                'full_text_length': len(text_content)
            }
            
            print(f"Final notes content length: {len(doc_content['notes_content'])}")
            print(f"Notes preview: {doc_content['notes_content'][:300]}...")
            
            return doc_content, transcript_content
            
    except Exception as e:
        print(f"Error fetching Google Doc: {e}")
    
    return {}, ""

@google_meet_analytics.route('/api/send-whatsapp-summary', methods=['POST'])
def send_whatsapp_summary():
    """Send the WhatsApp summary to the group chat."""
    try:
        data = request.json
        summary = data.get('summary', '')
        
        if not summary:
            return jsonify({
                'success': False,
                'error': 'No summary provided'
            }), 400
        
        # Import WhatsApp sending functionality
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        # Send via Green API
        import requests
        
        instance = os.getenv('GREEN_API_INSTANCE')
        token = os.getenv('GREEN_API_TOKEN')
        chat_id = os.getenv('WHATSAPP_DEFAULT_CHAT', '120363401025025313@g.us')
        
        if not instance or not token:
            return jsonify({
                'success': False,
                'error': 'WhatsApp API not configured'
            }), 500
        
        url = f"https://api.green-api.com/waInstance{instance}/sendMessage/{token}"
        
        payload = {
            "chatId": chat_id,
            "message": summary
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': 'Summary sent to WhatsApp group'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'WhatsApp API error: {response.status_code}'
            }), 500
            
    except Exception as e:
        print(f"Error sending WhatsApp summary: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500