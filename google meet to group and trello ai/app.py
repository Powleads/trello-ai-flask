#!/usr/bin/env python3
"""
Meeting Automation Web Frontend

Simple web interface for processing Google Docs transcripts.
"""

import asyncio
import sys
import os
import re
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv
import requests

# Load environment
load_dotenv()

app = Flask(__name__)

def extract_google_doc_id(url):
    """Extract document ID from Google Docs URL."""
    # Pattern to match Google Docs URLs
    pattern = r'/document/d/([a-zA-Z0-9-_]+)'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_google_doc_text(doc_id):
    """Extract text from Google Docs using export URL and verify it contains transcript."""
    try:
        # Use Google Docs export API to get plain text
        export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
        
        response = requests.get(export_url, timeout=30)
        
        if response.status_code == 200:
            text = response.text
            
            # Verify this looks like a transcript
            transcript_indicators = [
                'transcript',
                ':',  # Speaker indicators like "John:"
                'said',
                'meeting',
                'discussion',
                'talked about',
                'mentioned'
            ]
            
            # Check for conversation-like patterns
            lines = text.split('\n')
            conversation_lines = 0
            for line in lines:
                if ':' in line and len(line.strip()) > 10:
                    conversation_lines += 1
            
            # Basic heuristics to detect if this is likely a transcript
            is_likely_transcript = (
                len(text) > 100 and  # Minimum length
                (
                    conversation_lines >= 3 or  # Has speaker lines
                    any(indicator.lower() in text.lower() for indicator in transcript_indicators[:3]) or  # Contains transcript keywords
                    text.count(':') >= 5  # Multiple colons (speaker indicators)
                )
            )
            
            if not is_likely_transcript:
                print(f"Warning: Document may not contain a transcript. Length: {len(text)}, Conversation lines: {conversation_lines}")
                # Still return the text but with a warning flag
                return {
                    'text': text,
                    'warning': 'This document may not contain a meeting transcript. Please verify the content is from a meeting discussion.'
                }
            
            return {'text': text, 'warning': None}
        else:
            return None
    except Exception as e:
        print(f"Error fetching Google Doc: {e}")
        return None

def find_trello_cards_in_transcript(transcript_text):
    """Intelligent Trello card matching with deep understanding."""
    try:
        # Import required modules
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent / 'src'))
        
        from integrations.trello import TrelloClient
        import openai
        import re
        import asyncio
        from collections import defaultdict
        
        # Initialize clients
        trello_client = TrelloClient()
        openai_key = os.getenv('OPENAI_API_KEY')
        
        if not openai_key:
            print("OpenAI API key not configured")
            return [], []
        
        openai_client = openai.OpenAI(api_key=openai_key)
        
        # Cache for card understanding
        card_cache = {}
        
        async def get_card_understanding(card):
            """Get understanding of what a card is about."""
            card_id = card['id']
            if card_id in card_cache:
                return card_cache[card_id]
            
            understanding = {
                'is_meta': False,
                'topics': [],
                'context': ''
            }
            
            # Check if meta card
            meta_indicators = ['READ', 'RULES', 'DO NOT DELETE', 'INSTRUCTIONS', 'TEMPLATE']
            name_upper = card['name'].upper()
            if any(indicator in name_upper for indicator in meta_indicators):
                understanding['is_meta'] = True
                card_cache[card_id] = understanding
                return understanding
            
            # Extract topics
            text = f"{card['name']} {card.get('desc', '')}"
            topic_patterns = {
                'wordpress': ['wordpress', 'wp', 'website', 'site'],
                'facebook': ['facebook', 'fb', 'meta', 'ads', 'pixel'],
                'landing_page': ['landing', 'page', 'funnel'],
                'onboarding': ['onboard', 'setup', 'new client'],
                'shopify': ['shopify', 'ecommerce', 'store', 'product'],
                'support': ['support', 'ticket', 'help', 'issue'],
                'automation': ['automat', 'workflow', 'trigger'],
                'excel': ['excel', 'spreadsheet', 'sheet'],
                'center': ['center', 'location', 'facility']
            }
            
            for topic, keywords in topic_patterns.items():
                if any(kw in text.lower() for kw in keywords):
                    understanding['topics'].append(topic)
            
            understanding['context'] = f"Card about: {', '.join(understanding['topics'])}" if understanding['topics'] else card['name'][:50]
            card_cache[card_id] = understanding
            return understanding
        
        async def find_trello_start(transcript):
            """Find where Trello discussion starts."""
            lines = transcript.split('\n')
            patterns = [r'trello', r'board', r'let\'?s (check|look at|review)', r'wordpress', r'onboard']
            
            for i, line in enumerate(lines):
                line_lower = line.lower()
                if any(re.search(pattern, line_lower) for pattern in patterns):
                    return i, '\n'.join(lines[i:])
            return 0, transcript

        async def intelligent_card_matching():
            # Get board data
            board_id = os.getenv('TRELLO_BOARD_ID')
            board_lists = await trello_client.get_board_lists(board_id)
            board_cards = await trello_client.get_board_cards(board_id)
            
            # Filter out meta cards and understand others
            relevant_cards = []
            for card in board_cards:
                understanding = await get_card_understanding(card)
                if not understanding['is_meta']:
                    relevant_cards.append((card, understanding))
            
            print(f"Analyzing {len(relevant_cards)} relevant cards (excluded {len(board_cards) - len(relevant_cards)} meta cards)")
            
            # Find Trello discussion start
            start_line, relevant_transcript = await find_trello_start(transcript_text)
            
            # Create context for AI
            list_names = {lst['id']: lst['name'] for lst in board_lists}
            cards_by_list = defaultdict(list)
            for card, understanding in relevant_cards:
                cards_by_list[card['idList']].append((card, understanding))
            
            cards_context = "RELEVANT TRELLO CARDS:\n\n"
            for list_id, card_list in cards_by_list.items():
                list_name = list_names.get(list_id, 'Unknown')
                cards_context += f"{list_name}:\n"
                for card, understanding in card_list[:10]:
                    cards_context += f"  - {card['name']}"
                    if understanding['topics']:
                        cards_context += f" (Topics: {', '.join(understanding['topics'])})"
                    cards_context += "\n"
                cards_context += "\n"
            
            # Use AI to extract meeting notes for specific cards
            ai_extraction_prompt = f"""
            This is a meeting transcript where the team reviews their Trello board.
            
            {cards_context}
            
            INSTRUCTIONS:
            1. Find discussions about specific cards above
            2. Extract the actual meeting notes, updates, and tasks discussed
            3. Focus on what was said about the work, not matching reasons
            4. Include any action items, updates, blockers, or next steps mentioned
            
            For each card discussed, extract the meeting notes:
            
            Format as JSON:
            {{
                "card_discussions": [
                    {{
                        "card_name": "exact card name",
                        "meeting_notes": "actual discussion points about this card",
                        "action_items": ["task 1", "task 2"],
                        "updates": "status updates mentioned",
                        "blockers": "any issues mentioned",
                        "next_steps": "what needs to happen next",
                        "confidence": 0.9
                    }}
                ]
            }}
            
            Extract useful meeting notes for the cards:
            
            Transcript excerpt:
            {relevant_transcript[:4000]}
            """
            
            try:
                ai_response = openai_client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": "You are an expert at matching meeting discussions to specific Trello cards based on context and meaning, not just keywords."},
                        {"role": "user", "content": ai_extraction_prompt}
                    ],
                    max_tokens=1500,
                    temperature=0.1
                )
                
                import json
                result_text = ai_response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
                ai_extracted = json.loads(result_text)
                card_discussions = ai_extracted.get('card_discussions', [])
                
            except Exception as e:
                print(f"AI note extraction failed: {e}")
                card_discussions = []
            
            # Match discussions to actual cards and generate proper comments
            matched_cards = []
            for discussion in card_discussions:
                card_name = discussion.get('card_name', '')
                
                # Find the actual card
                for card, understanding in relevant_cards:
                    if (card_name.lower() in card['name'].lower() or 
                        card['name'].lower() in card_name.lower()):
                        
                        # Generate proper meeting comment
                        comment_parts = []
                        
                        # Meeting header
                        from datetime import datetime
                        date_str = datetime.now().strftime('%Y-%m-%d')
                        comment_parts.append(f"**Meeting Update - {date_str}**")
                        
                        # Meeting notes
                        if discussion.get('meeting_notes'):
                            comment_parts.append(f"**Discussion:**")
                            comment_parts.append(discussion['meeting_notes'])
                        
                        # Updates
                        if discussion.get('updates'):
                            comment_parts.append(f"**Status Update:**")
                            comment_parts.append(discussion['updates'])
                        
                        # Action items
                        if discussion.get('action_items'):
                            comment_parts.append(f"**Action Items:**")
                            for item in discussion['action_items']:
                                comment_parts.append(f"• {item}")
                        
                        # Blockers
                        if discussion.get('blockers'):
                            comment_parts.append(f"**Blockers:**")
                            comment_parts.append(discussion['blockers'])
                        
                        # Next steps
                        if discussion.get('next_steps'):
                            comment_parts.append(f"**Next Steps:**")
                            comment_parts.append(discussion['next_steps'])
                        
                        # Footer
                        comment_parts.append("*Added from team meeting*")
                        
                        suggested_comment = "\n\n".join(comment_parts)
                        
                        matched_cards.append({
                            'reference': {
                                'title': card_name,
                                'context': discussion.get('meeting_notes', ''),
                                'confidence': discussion.get('confidence', 0.8)
                            },
                            'card': card,
                            'match_score': discussion.get('confidence', 0.8),
                            'match_type': 'meeting_notes',
                            'suggested_comment': suggested_comment
                        })
                        break
            
            # Remove duplicates and sort by confidence
            seen_cards = {}
            for match in matched_cards:
                card_id = match['card']['id']
                if card_id not in seen_cards or match['match_score'] > seen_cards[card_id]['match_score']:
                    seen_cards[card_id] = match
            
            unique_matches = list(seen_cards.values())
            unique_matches.sort(key=lambda x: x['match_score'], reverse=True)
            
            return unique_matches, []  # No new tasks for now
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(intelligent_card_matching())
        loop.close()
        
        return results
        
    except Exception as e:
        print(f"Error in advanced card matching: {e}")
        return [], []

def process_transcript_simple(transcript_text, send_whatsapp_enabled=False, source_url=None):
    """Process transcript using the simple core functionality."""
    try:
        # Import OpenAI
        import openai
        
        openai_key = os.getenv('OPENAI_API_KEY')
        if not openai_key:
            return {"error": "OpenAI API key not configured"}
        
        client = openai.OpenAI(api_key=openai_key)
        
        # Generate summary
        summary_prompt = f"""
        Analyze this meeting transcript and provide a comprehensive summary with the following format:

        1. First, identify all participants/attendees mentioned in the transcript
        2. List the main topics discussed 
        3. Key decisions made
        4. Action items with assignees (if mentioned)
        5. Next steps

        Start the summary with: "Today's meeting was attended by [list attendees] and discussed the following points:"

        Format the response clearly and professionally.
        
        Transcript:
        {transcript_text[:2000]}...
        
        Summary:
        """
        
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are an expert meeting analyst. Provide clear, structured summaries."},
                {"role": "user", "content": summary_prompt}
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        summary = response.choices[0].message.content
        
        # Format the final WhatsApp message with additional sections
        formatted_message = summary
        
        # Add Trello cards section (placeholder for now)
        formatted_message += "\\n\\n📋 **Trello Cards Updated:**\\n"
        formatted_message += "• [Coming Soon] - Card matching and commenting feature in development"
        
        # Add Google Doc link at the end
        if source_url:
            formatted_message += f"\\n\\n📄 **Full Meeting Details:**\\nFor a more detailed summary, visit the original document:\\n{source_url}"
        
        # Send to WhatsApp
        whatsapp_sent = False
        whatsapp_error = None
        
        whatsapp_instance = os.getenv('GREEN_API_INSTANCE_ID')
        whatsapp_token = os.getenv('GREEN_API_TOKEN')
        chat_id = os.getenv('WHATSAPP_DEFAULT_CHAT')
        
        if send_whatsapp_enabled:
            if whatsapp_instance and whatsapp_token and chat_id:
                try:
                    message = f"🤖 **Meeting Summary**\\n\\n{formatted_message}\\n\\n*Generated by Meeting Automation Tool*"
                    
                    send_url = f"https://api.green-api.com/waInstance{whatsapp_instance}/sendMessage/{whatsapp_token}"
                    send_data = {
                        "chatId": chat_id,
                        "message": message
                    }
                    
                    send_response = requests.post(send_url, json=send_data, timeout=10)
                    
                    if send_response.status_code == 200:
                        whatsapp_sent = True
                    else:
                        whatsapp_error = f"Failed to send (Status: {send_response.status_code})"
                        
                except Exception as e:
                    whatsapp_error = str(e)
            else:
                whatsapp_error = "WhatsApp credentials not configured"
        else:
            whatsapp_error = "WhatsApp sending disabled"
        
        return {
            "success": True,
            "summary": summary,
            "formatted_message": formatted_message,
            "whatsapp_sent": whatsapp_sent,
            "whatsapp_error": whatsapp_error,
            "transcript_length": len(transcript_text)
        }
        
    except Exception as e:
        return {"error": str(e)}

@app.route('/')
def index():
    """Main page with input form."""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    """Step 1: Analyze transcript and find Trello cards."""
    try:
        # Get input from form
        google_doc_url = request.form.get('google_doc_url', '').strip()
        direct_text = request.form.get('direct_text', '').strip()
        send_whatsapp_enabled = request.form.get('send_whatsapp') == '1'
        
        transcript_text = None
        source = None
        
        if google_doc_url:
            # Process Google Docs URL
            doc_id = extract_google_doc_id(google_doc_url)
            if not doc_id:
                return jsonify({"error": "Invalid Google Docs URL"})
            
            doc_result = get_google_doc_text(doc_id)
            if not doc_result:
                return jsonify({"error": "Could not access Google Doc. Make sure it's publicly viewable."})
            
            transcript_text = doc_result['text']
            doc_warning = doc_result['warning']
            
            source = f"Google Doc: {google_doc_url}"
            if doc_warning:
                source += f" ⚠️ Warning: {doc_warning}"
            
        elif direct_text:
            # Process direct text input
            transcript_text = direct_text
            source = "Direct text input"
        
        else:
            return jsonify({"error": "Please provide either a Google Docs URL or direct text"})
        
        if len(transcript_text.strip()) < 50:
            return jsonify({"error": "Transcript too short. Please provide a longer text."})
        
        # Find Trello cards mentioned in transcript using advanced AI matching
        print("Looking for Trello cards in transcript using AI...")
        matched_cards, suggested_new_tasks = find_trello_cards_in_transcript(transcript_text)
        
        return jsonify({
            'success': True,
            'source': source,
            'matched_cards': matched_cards,
            'suggested_new_tasks': suggested_new_tasks,
            'transcript_length': len(transcript_text),
            'workflow_step': 'trello_matching',
            'transcript_text': transcript_text,  # Store for later use
            'source_url': google_doc_url if google_doc_url else None
        })
        
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/demo-analyze', methods=['POST'])
def demo_analyze():
    """Demo mode with sample Trello card matches."""
    try:
        # Get input for demo purposes
        google_doc_url = request.form.get('google_doc_url', '').strip()
        direct_text = request.form.get('direct_text', '').strip()
        
        source = "Demo Mode"
        if google_doc_url:
            source = f"Demo Mode - Google Doc: {google_doc_url}"
        elif direct_text:
            source = f"Demo Mode - Direct text input"
        
        # Sample demo transcript with references to your actual board cards
        demo_transcript = """
        Meeting Transcript - Team Status Update
        
        John: Good morning everyone. Let's start with our updates. Sarah, how's the progress on the EESYSTEM WORDPRESS SITE?
        
        Sarah: The WordPress site is going well. I've been working on the main landing page and we should have the initial version ready for review by Friday. I think we can move that card to the review column soon.
        
        Mike: Great! What about the task for reaching out to onboarded clients? I know we discussed showing leads to new prospects.
        
        Sarah: Yes, I've been working on that too. The reach out to onboarded, show leads task is about 60% complete. I have a list of 15 clients ready to contact and I'm preparing the presentation materials.
        
        John: Perfect. Any blockers on the Center Name projects? I know we have a few of those.
        
        Mike: Actually yes. For the Center Name: Vitality Energy Healing project, I'm waiting for approval on the logo design. And for Center Name: Quantum Healing Room, we need to finalize the color scheme before proceeding.
        
        Sarah: I can help with the Quantum Healing Room colors. I have some ideas that might work well with their branding.
        
        John: Excellent. Let's make sure we update these cards with our discussion points so the team knows the current status.
        
        Mike: Agreed. I'll add comments about the logo approval wait for Vitality Energy Healing, and Sarah, if you can add your color scheme ideas for Quantum Healing Room, that would be great.
        
        Meeting ended at 10:30 AM
        """
        
        # Create demo matched cards based on actual cards from your board
        demo_matched_cards = [
            {
                'reference': {
                    'title': 'EESYSTEM WORDPRESS SITE',
                    'context': 'Sarah: The WordPress site is going well. I\'ve been working on the main landing page and we should have the initial version ready for review by Friday.',
                    'confidence': 0.95
                },
                'card': {
                    'id': 'demo_card_1',
                    'name': 'EESYSTEM WORDPRESS SITE',
                    'url': 'https://trello.com/c/demo1/eesystem-wordpress-site',
                    'list': {'name': 'DOING - IN PROGRESS'}
                },
                'match_score': 1.0,
                'match_type': 'exact',
                'suggested_comment': '''Meeting Update - WordPress Site Progress

**Status Update from Sarah:**
- Main landing page development is progressing well
- Initial version will be ready for review by Friday
- Ready to move to review column soon

**Match Confidence:** 100% (exact match)
**Discussion Context:** This item was mentioned in today's meeting.

*Auto-generated from meeting transcript*'''
            },
            {
                'reference': {
                    'title': 'reach out to onboarded, show leads',
                    'context': 'Mike: What about the task for reaching out to onboarded clients? I know we discussed showing leads to new prospects. Sarah: Yes, I\'ve been working on that too. The reach out to onboarded, show leads task is about 60% complete.',
                    'confidence': 0.90
                },
                'card': {
                    'id': 'demo_card_2',
                    'name': 'reach out to onboarded , show leads',
                    'url': 'https://trello.com/c/demo2/reach-out-to-onboarded-show-leads',
                    'list': {'name': 'DOING - IN PROGRESS'}
                },
                'match_score': 0.95,
                'match_type': 'fuzzy',
                'suggested_comment': '''Meeting Update - Client Outreach Progress

**Progress Report from Sarah:**
- Task is 60% complete
- Prepared list of 15 clients ready to contact
- Working on presentation materials for new prospects

**Match Confidence:** 95% (fuzzy match)
**Discussion Context:** This item was mentioned in today's meeting.

*Auto-generated from meeting transcript*'''
            },
            {
                'reference': {
                    'title': 'Center Name: Vitality Energy Healing',
                    'context': 'Mike: For the Center Name: Vitality Energy Healing project, I\'m waiting for approval on the logo design.',
                    'confidence': 0.85
                },
                'card': {
                    'id': 'demo_card_3',
                    'name': 'Center Name: Vitality Energy Healing',
                    'url': 'https://trello.com/c/demo3/vitality-energy-healing',
                    'list': {'name': 'BLOCKED - HELP NEEDED'}
                },
                'match_score': 0.85,
                'match_type': 'partial',
                'suggested_comment': '''Meeting Update - Project Status

**Current Blocker (from Mike):**
- Waiting for approval on logo design
- Project paused pending design approval

**Match Confidence:** 85% (partial match)
**Discussion Context:** This item was mentioned in today's meeting.

*Auto-generated from meeting transcript*'''
            },
            {
                'reference': {
                    'title': 'Center Name: Quantum Healing Room',
                    'context': 'Mike: And for Center Name: Quantum Healing Room, we need to finalize the color scheme before proceeding. Sarah: I can help with the Quantum Healing Room colors. I have some ideas that might work well with their branding.',
                    'confidence': 0.88
                },
                'card': {
                    'id': 'demo_card_4',
                    'name': 'Center Name: Quantum Healing Room',
                    'url': 'https://trello.com/c/demo4/quantum-healing-room',
                    'list': {'name': 'NEW TASKS'}
                },
                'match_score': 0.72,
                'match_type': 'fuzzy',
                'suggested_comment': '''Meeting Update - Color Scheme Discussion

**Current Issue:**
- Need to finalize color scheme before proceeding
- Project on hold pending color decisions

**Team Collaboration:**
- Sarah offered to help with color scheme ideas
- She has concepts that align with client branding

**Match Confidence:** 72% (fuzzy match)
**Discussion Context:** This item was mentioned in today's meeting.

*Auto-generated from meeting transcript*'''
            }
        ]
        
        # Demo suggested new tasks
        demo_suggested_new_tasks = [
            {
                'title': 'Follow up on logo design approval',
                'context': 'Mike mentioned waiting for logo approval for Vitality Energy Healing',
                'is_new_task': True
            },
            {
                'title': 'Create color scheme presentation for Quantum Healing Room',
                'context': 'Sarah offered to help with color scheme ideas and create proposals',
                'is_new_task': True
            }
        ]
        
        return jsonify({
            'success': True,
            'demo_mode': True,
            'source': source,
            'matched_cards': demo_matched_cards,
            'suggested_new_tasks': demo_suggested_new_tasks,
            'transcript_length': len(demo_transcript),
            'workflow_step': 'trello_matching',
            'transcript_text': demo_transcript,
            'source_url': google_doc_url if google_doc_url else None
        })
        
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/post-trello-comments', methods=['POST'])
def post_trello_comments():
    """Post comments to Trello cards."""
    try:
        data = request.get_json()
        comments = data.get('comments', [])
        
        if not comments:
            return jsonify({"error": "No comments to post"})
        
        # Import Trello client
        from integrations.trello import TrelloClient
        
        trello_client = TrelloClient()
        posted_cards = []
        
        for comment_data in comments:
            try:
                # Post comment to Trello card
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                comment_result = loop.run_until_complete(
                    trello_client.add_comment(
                        comment_data['card_id'], 
                        comment_data['comment']
                    )
                )
                success = bool(comment_result)
                
                loop.close()
                
                if success:
                    posted_cards.append({
                        'card_id': comment_data['card_id'],
                        'card_name': comment_data['card_name'],
                        'card_url': comment_data['card_url'],
                        'comment_posted': True
                    })
                    print(f"Posted comment to card: {comment_data['card_name']}")
                else:
                    print(f"Failed to post comment to card: {comment_data['card_name']}")
                    
            except Exception as e:
                print(f"Error posting to card {comment_data['card_name']}: {e}")
        
        return jsonify({
            "success": True,
            "posted_cards": posted_cards,
            "total_attempted": len(comments),
            "total_successful": len(posted_cards)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/generate-summary', methods=['POST'])
def generate_summary():
    """Generate AI summary from transcript."""
    try:
        data = request.get_json()
        transcript_text = data.get('transcript_text', '')
        source_url = data.get('source_url', '')
        
        if not transcript_text:
            return jsonify({"error": "No transcript text provided"})
        
        # Import OpenAI
        import openai
        
        openai_key = os.getenv('OPENAI_API_KEY')
        if not openai_key:
            return jsonify({"error": "OpenAI API key not configured"})
        
        client = openai.OpenAI(api_key=openai_key)
        
        # Generate summary
        summary_prompt = f"""
        Analyze this meeting transcript and provide a comprehensive summary with the following format:

        1. First, identify all participants/attendees mentioned in the transcript
        2. List the main topics discussed 
        3. Key decisions made
        4. Action items with assignees (if mentioned)
        5. Next steps

        Start the summary with: "Today's meeting was attended by [list attendees] and discussed the following points:"

        Format the response clearly and professionally.
        
        Transcript:
        {transcript_text[:3000]}...
        
        Summary:
        """
        
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are an expert meeting analyst. Provide clear, structured summaries."},
                {"role": "user", "content": summary_prompt}
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        summary = response.choices[0].message.content
        
        return jsonify({
            "success": True,
            "summary": summary
        })
        
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/send-whatsapp', methods=['POST'])
def send_whatsapp():
    """Send WhatsApp message."""
    try:
        data = request.get_json()
        message = data.get('message', '')
        chat_id = data.get('chat_id') or os.getenv('WHATSAPP_DEFAULT_CHAT')
        
        if not message:
            return jsonify({"error": "No message provided"})
        
        whatsapp_instance = os.getenv('GREEN_API_INSTANCE_ID')
        whatsapp_token = os.getenv('GREEN_API_TOKEN')
        
        if not whatsapp_instance or not whatsapp_token or not chat_id:
            return jsonify({"error": "WhatsApp credentials not configured"})
        
        # Send message
        send_url = f"https://api.green-api.com/waInstance{whatsapp_instance}/sendMessage/{whatsapp_token}"
        send_data = {
            "chatId": chat_id,
            "message": message
        }
        
        response = requests.post(send_url, json=send_data, timeout=10)
        
        if response.status_code == 200:
            return jsonify({
                "success": True,
                "message": "WhatsApp message sent successfully"
            })
        else:
            return jsonify({
                "error": f"Failed to send WhatsApp message (Status: {response.status_code})"
            })
        
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/status')
def status():
    """Check system status."""
    status_info = {
        "openai_configured": bool(os.getenv('OPENAI_API_KEY')),
        "whatsapp_configured": bool(os.getenv('GREEN_API_INSTANCE_ID') and os.getenv('GREEN_API_TOKEN')),
        "trello_configured": bool(os.getenv('TRELLO_API_KEY') and os.getenv('TRELLO_TOKEN'))
    }
    return jsonify(status_info)

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    Path('templates').mkdir(exist_ok=True)
    
    print("Meeting Automation Web Interface")
    print("===============================")
    print("Starting web server on http://localhost:5000")
    print("Press Ctrl+C to stop")
    
    app.run(debug=True, host='0.0.0.0', port=5000)