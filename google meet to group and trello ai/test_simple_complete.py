#!/usr/bin/env python3
"""
Simple test of the complete API
"""

import requests
import time

def test_simple():
    """Simple test of the complete API."""
    
    sample_transcript = """Sarah Chen: Let's discuss the Mobile App progress.
Mike Johnson: The Mobile App is going well, almost ready for testing.
Emily Rodriguez: What about the SEO project?
David Kim: I can help with the SEO work.
Lisa Thompson: The Support Ticket System Revival is complete."""
    
    print("Testing Complete API")
    print("=" * 40)
    
    url = "http://localhost:5002/api/process-transcript"
    data = {"direct_text": sample_transcript}
    
    try:
        response = requests.post(url, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                print("[SUCCESS] Processing completed!")
                print(f"Cards found: {result.get('cards_found', 0)}")
                print(f"Comments posted: {result.get('comments_posted', 0)}")
                print(f"Processing time: {result.get('processing_time', 0):.1f}s")
                
                matched_cards = result.get('matched_cards', [])
                print(f"\nMatched cards:")
                for i, card in enumerate(matched_cards, 1):
                    name = card.get('name', 'Unknown')
                    confidence = card.get('confidence', 0)
                    commented = card.get('comment_posted', False)
                    status = "COMMENTED" if commented else "NO COMMENT"
                    print(f"  {i}. {name} ({confidence}%) - {status}")
                
                return True
            else:
                print(f"[ERROR] {result.get('error', 'Unknown')}")
                return False
        else:
            print(f"[ERROR] Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

if __name__ == "__main__":
    success = test_simple()
    if success:
        print("\n[RESULT] Complete API working - cards matched and commented!")
    else:
        print("\n[RESULT] API has issues")