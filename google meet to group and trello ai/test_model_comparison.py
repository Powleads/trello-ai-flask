#!/usr/bin/env python3
"""
AI Model Comparison for Trello Card Matching
Tests different models to find the best balance of accuracy, speed, and cost
"""

import sys
import os
import re
import requests
import asyncio
import openai
import json
import time
from difflib import SequenceMatcher
from typing import List, Dict, Tuple

sys.path.insert(0, 'src')
from dotenv import load_dotenv
from integrations.trello import TrelloClient

load_dotenv()

# Model configurations with pricing (per 1M tokens)
MODELS_TO_TEST = [
    {"name": "gpt-4o", "input_cost": 2.50, "output_cost": 10.00, "context": 128000},
    {"name": "gpt-4o-mini", "input_cost": 0.15, "output_cost": 0.60, "context": 128000},
    {"name": "gpt-4-turbo", "input_cost": 10.00, "output_cost": 30.00, "context": 128000},
    {"name": "gpt-3.5-turbo", "input_cost": 0.50, "output_cost": 1.50, "context": 16385},
    {"name": "gpt-3.5-turbo-0125", "input_cost": 0.50, "output_cost": 1.50, "context": 16385},
]

async def extract_work_items_with_model(transcript_text: str, model_name: str, openai_client) -> Tuple[List[Dict], float, float]:
    """Extract work items using a specific model."""
    
    # Prepare prompt
    prompt = f"""
    Analyze this meeting transcript and extract ALL work items, tasks, or projects mentioned.
    Be very thorough - include even vague references to work.
    
    Look for:
    - Direct task mentions ("we need to...", "let's work on...", "the task is...")
    - Project names and initiatives
    - Action items and follow-ups
    - Updates on existing work
    - Problems or issues being discussed
    - Features or improvements mentioned
    
    Format as JSON:
    {{
        "mentioned_items": [
            {{"title": "item name", "context": "where/how it was discussed", "confidence": 0.9}},
            ...
        ],
        "new_tasks": [
            {{"title": "new task", "context": "why it was suggested"}},
            ...
        ]
    }}
    
    Transcript excerpt:
    {transcript_text[:3000]}
    """
    
    start_time = time.time()
    
    try:
        response = openai_client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are an expert at extracting work items from meeting transcripts. Be thorough and inclusive."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.1
        )
        
        extraction_time = time.time() - start_time
        
        # Parse response
        result_text = response.choices[0].message.content
        # Clean up the response if needed
        result_text = result_text.replace("```json", "").replace("```", "").strip()
        
        result = json.loads(result_text)
        mentioned_items = result.get('mentioned_items', [])
        new_tasks = result.get('new_tasks', [])
        
        # Calculate token usage for cost estimation
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        
        model_config = next((m for m in MODELS_TO_TEST if m["name"] == model_name), MODELS_TO_TEST[0])
        input_cost = (prompt_tokens / 1_000_000) * model_config["input_cost"]
        output_cost = (completion_tokens / 1_000_000) * model_config["output_cost"]
        total_cost = input_cost + output_cost
        
        return {
            "mentioned_items": mentioned_items,
            "new_tasks": new_tasks,
            "extraction_time": extraction_time,
            "cost": total_cost,
            "tokens": {"prompt": prompt_tokens, "completion": completion_tokens}
        }
        
    except Exception as e:
        print(f"Error with model {model_name}: {e}")
        return {
            "mentioned_items": [],
            "new_tasks": [],
            "extraction_time": time.time() - start_time,
            "cost": 0,
            "error": str(e)
        }

async def match_items_to_cards(mentioned_items: List[Dict], board_cards: List[Dict]) -> List[Dict]:
    """Match extracted items to Trello cards."""
    
    matches = []
    
    for item in mentioned_items:
        item_title = item['title'].lower()
        best_matches = []
        
        for card in board_cards:
            card_name = card.get('name', '').lower()
            card_desc = card.get('desc', '').lower()
            
            # Multiple matching strategies
            title_exact = 1.0 if item_title in card_name or card_name in item_title else 0
            title_fuzzy = SequenceMatcher(None, item_title, card_name).ratio()
            
            # Word overlap
            item_words = set(item_title.split())
            card_words = set(card_name.split())
            word_overlap = len(item_words.intersection(card_words)) / max(len(item_words), 1) if item_words else 0
            
            # Description match
            desc_match = 0
            if card_desc:
                desc_fuzzy = SequenceMatcher(None, item_title, card_desc).ratio()
                desc_words = set(card_desc.split())
                desc_word_overlap = len(item_words.intersection(desc_words)) / max(len(item_words), 1) if item_words else 0
                desc_match = max(desc_fuzzy, desc_word_overlap * 0.8)
            
            # Composite score
            composite_score = max(
                title_exact,
                title_fuzzy * 0.9,
                word_overlap * 0.8,
                desc_match * 0.7
            )
            
            if composite_score >= 0.5:  # 50% threshold
                best_matches.append({
                    'card': card,
                    'score': composite_score,
                    'match_type': 'exact' if title_exact > 0 else 'fuzzy' if title_fuzzy > 0.7 else 'partial'
                })
        
        # Sort and take best match
        best_matches.sort(key=lambda x: x['score'], reverse=True)
        if best_matches:
            match = best_matches[0]
            matches.append({
                'item': item,
                'card_name': match['card']['name'],
                'score': match['score'],
                'match_type': match['match_type']
            })
    
    return matches

async def test_all_models():
    """Test all models and compare results."""
    
    print("=" * 80)
    print("AI MODEL COMPARISON FOR TRELLO CARD MATCHING")
    print("=" * 80)
    
    # Get document
    doc_id = '1AQAmQ9LtAKvnVlz5UE65NJ_dREBHvVj-udDo1jfh5EQ'
    export_url = f'https://docs.google.com/document/d/{doc_id}/export?format=txt'
    response = requests.get(export_url, timeout=30)
    transcript_text = response.text
    
    print(f"\nTranscript loaded: {len(transcript_text)} characters")
    
    # Get Trello cards
    trello_client = TrelloClient()
    board_cards = await trello_client.get_board_cards(os.getenv('TRELLO_BOARD_ID'))
    print(f"Trello board has {len(board_cards)} cards")
    
    # Initialize OpenAI
    openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    # Test each model
    results = {}
    
    for model_config in MODELS_TO_TEST:
        model_name = model_config["name"]
        print(f"\n{'='*60}")
        print(f"Testing: {model_name}")
        print(f"Cost: ${model_config['input_cost']}/1M input, ${model_config['output_cost']}/1M output")
        print("-" * 60)
        
        # Extract work items
        extraction_result = await extract_work_items_with_model(transcript_text, model_name, openai_client)
        
        if "error" in extraction_result:
            print(f"ERROR: {extraction_result['error']}")
            continue
        
        # Match to cards
        mentioned_items = extraction_result["mentioned_items"]
        matches = await match_items_to_cards(mentioned_items, board_cards)
        
        # Store results
        results[model_name] = {
            "extraction_time": extraction_result["extraction_time"],
            "cost": extraction_result["cost"],
            "items_found": len(mentioned_items),
            "new_tasks": len(extraction_result["new_tasks"]),
            "matches_found": len(matches),
            "high_confidence_matches": len([m for m in matches if m['score'] >= 0.8]),
            "medium_confidence_matches": len([m for m in matches if 0.6 <= m['score'] < 0.8]),
            "low_confidence_matches": len([m for m in matches if 0.5 <= m['score'] < 0.6]),
            "tokens": extraction_result.get("tokens", {}),
            "sample_items": mentioned_items[:3] if mentioned_items else [],
            "sample_matches": matches[:3] if matches else []
        }
        
        # Print results
        print(f"Time: {extraction_result['extraction_time']:.2f} seconds")
        print(f"Cost: ${extraction_result['cost']:.6f}")
        print(f"Items extracted: {len(mentioned_items)}")
        print(f"New tasks suggested: {len(extraction_result['new_tasks'])}")
        print(f"Cards matched: {len(matches)}")
        print(f"   - High confidence (80%+): {results[model_name]['high_confidence_matches']}")
        print(f"   - Medium confidence (60-79%): {results[model_name]['medium_confidence_matches']}")
        print(f"   - Low confidence (50-59%): {results[model_name]['low_confidence_matches']}")
        
        if matches:
            print(f"\nTop 3 matches:")
            for match in matches[:3]:
                clean_card = match['card_name'].encode('ascii', 'ignore').decode('ascii')
                print(f"   {int(match['score']*100)}% - {clean_card[:50]}")
    
    await trello_client.session.close()
    
    # Summary comparison
    print("\n" + "=" * 80)
    print("SUMMARY COMPARISON")
    print("=" * 80)
    
    # Create comparison table
    print(f"\n{'Model':<20} {'Time(s)':<10} {'Cost($)':<12} {'Items':<8} {'Matches':<10} {'Quality'}")
    print("-" * 80)
    
    for model_name, data in results.items():
        quality = f"{data['high_confidence_matches']}H/{data['medium_confidence_matches']}M/{data['low_confidence_matches']}L"
        print(f"{model_name:<20} {data['extraction_time']:<10.2f} {data['cost']:<12.6f} {data['items_found']:<8} {data['matches_found']:<10} {quality}")
    
    # Find best value
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    # Sort by matches found (effectiveness)
    by_effectiveness = sorted(results.items(), key=lambda x: x[1]['matches_found'], reverse=True)
    print(f"\nMost Effective: {by_effectiveness[0][0]} ({by_effectiveness[0][1]['matches_found']} matches)")
    
    # Sort by cost
    by_cost = sorted(results.items(), key=lambda x: x[1]['cost'])
    print(f"Most Cost-Effective: {by_cost[0][0]} (${by_cost[0][1]['cost']:.6f})")
    
    # Sort by speed
    by_speed = sorted(results.items(), key=lambda x: x[1]['extraction_time'])
    print(f"Fastest: {by_speed[0][0]} ({by_speed[0][1]['extraction_time']:.2f}s)")
    
    # Best overall (balance of matches, cost, and speed)
    for model_name, data in results.items():
        # Calculate a balanced score
        max_matches = max(r['matches_found'] for r in results.values()) or 1
        max_cost = max(r['cost'] for r in results.values()) or 1
        max_time = max(r['extraction_time'] for r in results.values()) or 1
        
        # Higher is better: more matches, lower cost, faster time
        data['balanced_score'] = (
            (data['matches_found'] / max_matches) * 0.5 +  # 50% weight on effectiveness
            (1 - data['cost'] / max_cost) * 0.3 +           # 30% weight on cost
            (1 - data['extraction_time'] / max_time) * 0.2   # 20% weight on speed
        )
    
    by_balance = sorted(results.items(), key=lambda x: x[1]['balanced_score'], reverse=True)
    print(f"\nBEST OVERALL: {by_balance[0][0]}")
    print(f"   - Matches: {by_balance[0][1]['matches_found']}")
    print(f"   - Cost: ${by_balance[0][1]['cost']:.6f}")
    print(f"   - Time: {by_balance[0][1]['extraction_time']:.2f}s")
    print(f"   - Balanced Score: {by_balance[0][1]['balanced_score']:.3f}")

if __name__ == "__main__":
    asyncio.run(test_all_models())