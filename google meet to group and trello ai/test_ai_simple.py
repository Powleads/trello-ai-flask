#!/usr/bin/env python3
"""
Simple AI Services Test
Check if OpenAI API and core services are working
"""

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, 'src')
load_dotenv()

def test_openai():
    """Test OpenAI API connection."""
    print("Testing OpenAI API...")
    
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("[ERROR] OPENAI_API_KEY not found")
        return False
    
    print(f"[OK] API Key found: {api_key[:20]}...")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'working' if you can read this."}],
            max_tokens=10
        )
        
        result = response.choices[0].message.content.strip()
        print(f"[OK] OpenAI response: {result}")
        return "working" in result.lower()
        
    except Exception as e:
        print(f"[ERROR] OpenAI test failed: {e}")
        return False

def test_enhanced_ai():
    """Test Enhanced AI module."""
    print("\nTesting Enhanced AI module...")
    
    try:
        from enhanced_ai import EnhancedAI
        ai_engine = EnhancedAI()
        
        test_transcript = "John: How's the mobile app? Sarah: It's going well, almost ready for review."
        
        result = ai_engine.analyze_meeting_sentiment(test_transcript)
        print(f"[OK] Sentiment analysis: {result.summary}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Enhanced AI failed: {e}")
        return False

def test_card_matching():
    """Test card matching logic."""
    print("\nTesting card matching...")
    
    try:
        from custom_trello import CustomTrelloClient
        
        client = CustomTrelloClient()
        boards = client.list_boards()
        
        eeinteractive = None
        for board in boards:
            if 'eeinteractive' in board.name.lower():
                eeinteractive = board
                break
        
        if not eeinteractive:
            print("[ERROR] EEInteractive board not found")
            return False
        
        cards = eeinteractive.list_cards()[:5]  # Test with first 5 cards
        print(f"[OK] Found {len(cards)} test cards")
        
        # Test basic matching
        test_transcript = "Let's discuss the mobile app and SEO project updates"
        matches = 0
        
        for card in cards:
            if any(word in card.name.lower() for word in ['mobile', 'app', 'seo']):
                matches += 1
                print(f"[MATCH] {card.name}")
        
        print(f"[OK] Found {matches} potential matches")
        return True
        
    except Exception as e:
        print(f"[ERROR] Card matching failed: {e}")
        return False

def main():
    """Run tests."""
    print("AI Services Test")
    print("=" * 40)
    
    tests = [test_openai, test_enhanced_ai, test_card_matching]
    passed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
                print("[PASS]")
            else:
                print("[FAIL]")
        except Exception as e:
            print(f"[CRASH] {e}")
        print()
    
    print(f"Results: {passed}/{len(tests)} tests passed")
    return passed == len(tests)

if __name__ == "__main__":
    main()