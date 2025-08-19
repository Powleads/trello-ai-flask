#!/usr/bin/env python3
"""
Simple debug test - no unicode
"""

import requests
import time

def test_simple_api():
    """Test with a very simple transcript."""
    
    simple_transcript = "Sarah: Let's discuss the Mobile App. Mike: The Mobile App is going well. Emily: What about SEO? David: SEO is blocked."
    
    print("Testing simple API call...")
    print(f"Transcript: {simple_transcript}")
    
    url = "http://localhost:5000/api/process-transcript"
    data = {"direct_text": simple_transcript}
    
    try:
        start_time = time.time()
        response = requests.post(url, json=data, timeout=30)
        end_time = time.time()
        
        print(f"Request took {end_time - start_time:.2f} seconds")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result.get('success')}")
            print(f"Cards found: {result.get('cards_found', 0)}")
            
            matched_cards = result.get('matched_cards', [])
            if matched_cards:
                print("Matched cards:")
                for card in matched_cards:
                    print(f"  - {card.get('name', 'Unknown')}: {card.get('confidence', 0)}%")
            else:
                print("No cards matched")
            
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Request failed: {e}")
        return False

if __name__ == "__main__":
    test_simple_api()