"""
Advanced Trello Card Matching with List-Aware Context
Understands that meetings follow Trello board structure (left-to-right, top-to-bottom)
"""

import os
import re
import asyncio
import openai
import json
from typing import List, Dict, Tuple, Optional
from difflib import SequenceMatcher
from collections import defaultdict

def find_trello_cards_in_transcript_advanced(transcript_text):
    """Advanced AI-powered Trello card matching with board structure awareness."""
    try:
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent / 'src'))
        
        from integrations.trello import TrelloClient
        
        # Initialize clients
        trello_client = TrelloClient()
        openai_key = os.getenv('OPENAI_API_KEY')
        
        if not openai_key:
            print("OpenAI API key not configured")
            return [], []
        
        openai_client = openai.OpenAI(api_key=openai_key)
        
        async def intelligent_card_matching_with_context():
            # Get board structure
            board_id = os.getenv('TRELLO_BOARD_ID')
            board_lists = await trello_client.get_board_lists(board_id)
            board_cards = await trello_client.get_board_cards(board_id)
            
            # Organize cards by list (preserving order)
            cards_by_list = defaultdict(list)
            list_order = {lst['id']: idx for idx, lst in enumerate(board_lists)}
            list_names = {lst['id']: lst['name'] for lst in board_lists}
            
            for card in board_cards:
                list_id = card.get('idList')
                if list_id:
                    cards_by_list[list_id].append(card)
            
            # Sort lists left-to-right
            sorted_lists = sorted(cards_by_list.keys(), key=lambda x: list_order.get(x, 999))
            
            # Create board context for AI
            board_structure = "Board Structure (left to right):\n"
            for list_id in sorted_lists:
                list_name = list_names.get(list_id, 'Unknown')
                board_structure += f"\n{list_name}:\n"
                for card in cards_by_list[list_id][:10]:  # First 10 cards per list
                    board_structure += f"  - {card['name']}\n"
            
            # Enhanced AI extraction with board context
            ai_extraction_prompt = f"""
            This is a meeting transcript where participants are reviewing a Trello board.
            They go through the board left-to-right (list by list) and top-to-bottom (card by card).
            
            BOARD STRUCTURE:
            {board_structure}
            
            IMPORTANT PATTERNS TO RECOGNIZE:
            1. When someone mentions a card, the next discussion might be about the card below it in the same list
            2. After finishing one list, they move to the next list (left to right)
            3. List names mentioned indicate which section they're reviewing
            4. Sequential discussions often relate to nearby cards
            5. "Next one", "the one below", "moving on" often refer to the next card in order
            
            Analyze this transcript and extract:
            1. All work items, tasks, or Trello cards mentioned
            2. Which list they might be discussing (if mentioned)
            3. The order/sequence of discussion
            4. Context clues about card position ("next", "below", "after that")
            
            Look for:
            - Direct card/task mentions
            - List names (NEW TASKS, DOING - IN PROGRESS, BLOCKED, etc.)
            - Sequential indicators ("next", "then", "after that", "moving on")
            - Updates on existing work
            - Facebook ads, landing pages, onboarding, Excel, centers, websites
            - Company/center names (like "Vitality", "Quantum Healing", etc.)
            
            Format as JSON:
            {{
                "mentioned_items": [
                    {{
                        "title": "item name",
                        "context": "discussion context",
                        "list_hint": "list name if mentioned",
                        "sequence_hint": "before/after which item",
                        "confidence": 0.9
                    }},
                    ...
                ],
                "new_tasks": [
                    {{"title": "new task", "context": "why suggested"}},
                    ...
                ],
                "discussion_flow": ["item1", "item2", "item3"]  // Order of discussion
            }}
            
            Transcript:
            {transcript_text[:4000]}...
            """
            
            try:
                # Use GPT-4 Turbo for better understanding
                ai_response = openai_client.chat.completions.create(
                    model="gpt-4-turbo-preview",  # Better model as requested
                    messages=[
                        {"role": "system", "content": "You are an expert at understanding Trello board reviews in meetings. You understand that discussions follow board structure (left-to-right lists, top-to-bottom cards)."},
                        {"role": "user", "content": ai_extraction_prompt}
                    ],
                    max_tokens=1500,
                    temperature=0.1
                )
                
                result_text = ai_response.choices[0].message.content
                result_text = result_text.replace("```json", "").replace("```", "").strip()
                
                ai_extracted = json.loads(result_text)
                mentioned_items = ai_extracted.get('mentioned_items', [])
                new_tasks = ai_extracted.get('new_tasks', [])
                discussion_flow = ai_extracted.get('discussion_flow', [])
                
            except Exception as e:
                print(f"AI extraction failed: {e}")
                mentioned_items = []
                new_tasks = []
                discussion_flow = []
            
            # Enhanced matching with context awareness
            matched_cards = []
            last_matched_card = None
            last_matched_list = None
            
            for item_idx, item in enumerate(mentioned_items):
                best_matches = []
                
                # If we have a list hint, prioritize cards from that list
                list_hint = item.get('list_hint', '').lower()
                prioritized_cards = board_cards
                
                if list_hint:
                    # Find matching list
                    for list_id, list_name in list_names.items():
                        if list_hint in list_name.lower():
                            prioritized_cards = cards_by_list[list_id] + board_cards
                            break
                
                # If this seems to be sequential discussion, check nearby cards
                if last_matched_card and item.get('sequence_hint'):
                    # Find cards near the last matched card
                    if last_matched_list:
                        list_cards = cards_by_list[last_matched_list]
                        last_idx = next((i for i, c in enumerate(list_cards) if c['id'] == last_matched_card['id']), -1)
                        
                        if last_idx >= 0:
                            # Prioritize next few cards in the same list
                            nearby_cards = list_cards[last_idx:last_idx+5] + list_cards[max(0, last_idx-2):last_idx]
                            prioritized_cards = nearby_cards + prioritized_cards
                
                # Match against cards with context awareness
                for card in prioritized_cards:
                    card_name = card.get('name', '').lower()
                    card_desc = card.get('desc', '').lower()
                    item_title = item.get('title', '').lower()
                    
                    # Multiple matching strategies
                    scores = []
                    
                    # 1. Exact or substring match
                    if item_title in card_name or card_name in item_title:
                        scores.append(1.0)
                    
                    # 2. Fuzzy title match
                    title_fuzzy = SequenceMatcher(None, item_title, card_name).ratio()
                    scores.append(title_fuzzy)
                    
                    # 3. Word overlap
                    item_words = set(item_title.split())
                    card_words = set(card_name.split())
                    if item_words and card_words:
                        word_overlap = len(item_words.intersection(card_words)) / min(len(item_words), len(card_words))
                        scores.append(word_overlap)
                    
                    # 4. Description match
                    if card_desc:
                        desc_fuzzy = SequenceMatcher(None, item_title, card_desc).ratio()
                        scores.append(desc_fuzzy * 0.7)
                    
                    # 5. Context bonus for sequential discussion
                    context_bonus = 0
                    if card in prioritized_cards[:5]:  # If in prioritized set
                        context_bonus = 0.15
                    
                    # Calculate composite score
                    base_score = max(scores) if scores else 0
                    composite_score = min(1.0, base_score + context_bonus)
                    
                    # Lower threshold to 40% for better recall
                    if composite_score >= 0.4:
                        best_matches.append({
                            'card': card,
                            'score': composite_score,
                            'match_type': 'exact' if base_score >= 0.9 else 'fuzzy' if base_score >= 0.6 else 'partial',
                            'list_name': list_names.get(card.get('idList'), 'Unknown')
                        })
                
                # Sort by score and take best matches
                best_matches.sort(key=lambda x: x['score'], reverse=True)
                
                if best_matches:
                    match = best_matches[0]
                    
                    # Track last matched card for sequential context
                    last_matched_card = match['card']
                    last_matched_list = match['card'].get('idList')
                    
                    # Generate context-aware comment
                    comment_text = f"""Meeting Discussion - {item.get('context', 'Item discussed')}

**Match Confidence:** {int(match['score'] * 100)}% ({match['match_type']} match)
**List:** {match['list_name']}"""
                    
                    if item.get('list_hint'):
                        comment_text += f"\n**List Context:** Discussion was in {item['list_hint']} section"
                    
                    if item.get('sequence_hint'):
                        comment_text += f"\n**Sequence:** {item['sequence_hint']}"
                    
                    comment_text += "\n\n*Auto-generated from meeting transcript*"
                    
                    matched_cards.append({
                        'reference': item,
                        'card': match['card'],
                        'match_score': match['score'],
                        'match_type': match['match_type'],
                        'suggested_comment': comment_text,
                        'list_name': match['list_name']
                    })
            
            # Remove duplicates, keeping highest scores
            seen_cards = {}
            unique_matches = []
            for match in matched_cards:
                card_id = match['card']['id']
                if card_id not in seen_cards or match['match_score'] > seen_cards[card_id]['match_score']:
                    seen_cards[card_id] = match
            
            unique_matches = list(seen_cards.values())
            unique_matches.sort(key=lambda x: x['match_score'], reverse=True)
            
            return unique_matches, new_tasks
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(intelligent_card_matching_with_context())
        loop.close()
        
        return results
        
    except Exception as e:
        print(f"Error in advanced card matching: {e}")
        return [], []