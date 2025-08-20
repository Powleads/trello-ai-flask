"""
Intelligent Trello Card Matcher
- Understands what each card is about by reading descriptions and comments
- Detects when Trello discussion starts
- Filters out meta cards
- Caches card understanding for speed
"""

import os
import re
import json
import asyncio
import openai
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from difflib import SequenceMatcher
from collections import defaultdict

# Cache for card understanding
CARD_UNDERSTANDING_CACHE = {}

async def get_card_understanding(card: Dict, trello_client) -> Dict:
    """Get a deep understanding of what a card is about."""
    
    card_id = card['id']
    
    # Check cache first
    if card_id in CARD_UNDERSTANDING_CACHE:
        return CARD_UNDERSTANDING_CACHE[card_id]
    
    understanding = {
        'id': card_id,
        'name': card['name'],
        'description': card.get('desc', ''),
        'is_meta': False,  # Is this a meta/instruction card?
        'topics': [],      # Main topics this card is about
        'keywords': [],    # Important keywords
        'context': '',     # What this card is actually about
        'last_activity': None
    }
    
    # Check if this is a meta card (rules, instructions, etc.)
    meta_indicators = ['READ', 'RULES', 'DO NOT DELETE', 'INSTRUCTIONS', 'TEMPLATE']
    name_upper = card['name'].upper()
    if any(indicator in name_upper for indicator in meta_indicators):
        understanding['is_meta'] = True
        CARD_UNDERSTANDING_CACHE[card_id] = understanding
        return understanding
    
    # Get last comments for context
    try:
        comments = await trello_client._make_request(f'cards/{card_id}/actions', params={'filter': 'commentCard', 'limit': 3})
        if comments:
            last_comment = comments[0].get('data', {}).get('text', '')
            understanding['last_activity'] = last_comment[:200]
    except:
        pass
    
    # Extract topics and keywords
    text_to_analyze = f"{card['name']} {card.get('desc', '')} {understanding.get('last_activity', '')}"
    
    # Key topics to look for
    topic_patterns = {
        'wordpress': ['wordpress', 'wp', 'website', 'site'],
        'facebook': ['facebook', 'fb', 'meta', 'ads', 'pixel'],
        'landing_page': ['landing', 'page', 'funnel'],
        'onboarding': ['onboard', 'setup', 'new client'],
        'automation': ['automat', 'workflow', 'trigger'],
        'shopify': ['shopify', 'ecommerce', 'store', 'product'],
        'testimonial': ['testimonial', 'review', 'feedback'],
        'support': ['support', 'ticket', 'help', 'issue'],
        'calendar': ['calendar', 'schedule', 'booking', 'appointment'],
        'excel': ['excel', 'spreadsheet', 'sheet'],
        'center': ['center', 'location', 'facility']
    }
    
    for topic, keywords in topic_patterns.items():
        if any(kw in text_to_analyze.lower() for kw in keywords):
            understanding['topics'].append(topic)
            understanding['keywords'].extend(keywords)
    
    # Generate context summary
    if understanding['topics']:
        understanding['context'] = f"Card about: {', '.join(understanding['topics'])}"
    else:
        understanding['context'] = f"General task: {card['name'][:50]}"
    
    CARD_UNDERSTANDING_CACHE[card_id] = understanding
    return understanding


def find_trello_discussion_start(transcript_text: str) -> Tuple[int, str]:
    """Find where Trello discussion actually starts in the transcript."""
    
    lines = transcript_text.split('\n')
    
    # Patterns that indicate Trello discussion is starting
    start_patterns = [
        r'trello',
        r'board',
        r'let\'?s (check|look at|review) (the )?(board|trello)',
        r'(checking|reviewing|looking at) (the )?(board|trello)',
        r'move (on )?to (the )?(board|trello)',
        r'open(ing)? (up )?(the )?(board|trello)',
        r'pull(ing)? up (the )?(board|trello)'
    ]
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        for pattern in start_patterns:
            if re.search(pattern, line_lower):
                # Return the position and the relevant transcript from that point
                return i, '\n'.join(lines[i:])
    
    # If no explicit start found, return full transcript
    return 0, transcript_text


async def intelligent_card_matching(transcript_text: str, trello_client, openai_client) -> Tuple[List, List]:
    """Match transcript to cards with deep understanding."""
    
    # Find where Trello discussion starts
    start_line, relevant_transcript = find_trello_discussion_start(transcript_text)
    
    if start_line > 0:
        print(f"Trello discussion starts at line {start_line}")
    
    # Get board structure
    board_id = os.getenv('TRELLO_BOARD_ID')
    board_lists = await trello_client.get_board_lists(board_id)
    board_cards = await trello_client.get_board_cards(board_id)
    
    # Get understanding of each card (excluding meta cards)
    card_understandings = {}
    relevant_cards = []
    
    for card in board_cards:
        understanding = await get_card_understanding(card, trello_client)
        card_understandings[card['id']] = understanding
        
        # Skip meta cards
        if not understanding['is_meta']:
            relevant_cards.append(card)
    
    print(f"Analyzing {len(relevant_cards)} relevant cards (excluded {len(board_cards) - len(relevant_cards)} meta cards)")
    
    # Create enhanced prompt with card understanding
    cards_context = "TRELLO CARDS WITH CONTEXT:\n\n"
    list_names = {lst['id']: lst['name'] for lst in board_lists}
    
    cards_by_list = defaultdict(list)
    for card in relevant_cards:
        cards_by_list[card.get('idList')].append(card)
    
    for list_id, cards in cards_by_list.items():
        list_name = list_names.get(list_id, 'Unknown')
        cards_context += f"{list_name}:\n"
        
        for card in cards[:15]:  # Limit for context size
            understanding = card_understandings[card['id']]
            cards_context += f"  - {card['name']}"
            if understanding['topics']:
                cards_context += f" (Topics: {', '.join(understanding['topics'][:3])})"
            if understanding.get('last_activity'):
                cards_context += f" [Recent: {understanding['last_activity'][:50]}...]"
            cards_context += "\n"
        cards_context += "\n"
    
    # Use GPT-4 Turbo with enhanced understanding
    extraction_prompt = f"""
    This is a meeting transcript where the team reviews their Trello board.
    The Trello discussion starts around: "{relevant_transcript[:500]}..."
    
    {cards_context}
    
    IMPORTANT INSTRUCTIONS:
    1. Only extract items that are actually discussed in the meeting
    2. Match discussions to the specific cards above based on topics and context
    3. Ignore general conversation - focus on work items
    4. If someone says "WordPress site", match it to cards about WordPress/website topics
    5. Look for context clues - what are they actually talking about?
    
    Extract work items mentioned and match them to specific cards above.
    
    Format as JSON:
    {{
        "mentioned_items": [
            {{
                "quote": "exact quote from transcript",
                "matched_card": "card name if matched",
                "confidence": 0.9,
                "reason": "why this matches"
            }}
        ]
    }}
    
    Transcript excerpt (from Trello discussion):
    {relevant_transcript[:3000]}
    """
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": "You are an expert at matching meeting discussions to specific Trello cards based on context and meaning, not just keywords."},
                {"role": "user", "content": extraction_prompt}
            ],
            max_tokens=1500,
            temperature=0.1
        )
        
        result = json.loads(response.choices[0].message.content.replace("```json", "").replace("```", "").strip())
        mentioned_items = result.get('mentioned_items', [])
        
        # Match items to actual cards with understanding
        matched_cards = []
        
        for item in mentioned_items:
            if item.get('matched_card'):
                # Find the actual card
                for card in relevant_cards:
                    if item['matched_card'].lower() in card['name'].lower() or card['name'].lower() in item['matched_card'].lower():
                        understanding = card_understandings[card['id']]
                        
                        matched_cards.append({
                            'card': card,
                            'quote': item.get('quote', ''),
                            'confidence': item.get('confidence', 0.5),
                            'reason': item.get('reason', 'Matched by AI'),
                            'topics': understanding['topics'],
                            'suggested_comment': f"""Meeting Discussion:
"{item.get('quote', 'Discussion about this card')[:200]}..."

Reason for match: {item.get('reason', 'Discussed in meeting')}
Topics: {', '.join(understanding['topics'])} 

*Added from meeting transcript*"""
                        })
                        break
        
        return matched_cards, []
        
    except Exception as e:
        print(f"AI matching failed: {e}")
        return [], []


async def test_with_doc(doc_id: str):
    """Test the intelligent matcher with a specific document."""
    
    import requests
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent / 'src'))
    from integrations.trello import TrelloClient
    
    # Get document
    export_url = f'https://docs.google.com/document/d/{doc_id}/export?format=txt'
    response = requests.get(export_url, timeout=30)
    transcript_text = response.text
    
    print(f"Document loaded: {len(transcript_text)} characters")
    
    # Initialize clients
    trello_client = TrelloClient()
    openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    # Run intelligent matching
    matched_cards, new_tasks = await intelligent_card_matching(transcript_text, trello_client, openai_client)
    
    print(f"\nMatched {len(matched_cards)} cards:")
    for match in matched_cards:
        print(f"\n- {match['card']['name']}")
        print(f"  Confidence: {match['confidence']*100:.0f}%")
        print(f"  Quote: '{match['quote'][:100]}...'")
        print(f"  Reason: {match['reason']}")
        print(f"  Topics: {', '.join(match['topics'])}")
    
    await trello_client.session.close()
    

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Test with the provided document
    doc_id = '1ZZZPKZSijZgWK5bt62KCmfEIF0Fksu0kG67EpE0pCfE'
    asyncio.run(test_with_doc(doc_id))