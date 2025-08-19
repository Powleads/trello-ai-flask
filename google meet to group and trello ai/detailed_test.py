#!/usr/bin/env python3
"""
Detailed test to check if comments are being posted
"""

import requests
import json
import time

def test_detailed_api():
    """Test with detailed response analysis."""
    
    simple_transcript = "Sarah: Let's discuss the Mobile App. Mike: The Mobile App is going well. Emily: What about SEO? David: SEO is blocked."
    
    print("Testing detailed API call...")
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
            print(f"Comments posted: {result.get('comments_posted', 0)}")
            
            # Show comment errors if any
            comment_errors = result.get('comment_errors', [])
            if comment_errors:
                print("Comment errors:")
                for error in comment_errors:
                    print(f"  - {error}")
            
            matched_cards = result.get('matched_cards', [])
            if matched_cards:
                print("Matched cards details:")
                for card in matched_cards:
                    name = card.get('name', 'Unknown')
                    confidence = card.get('confidence', 0)
                    comment_posted = card.get('comment_posted', False)
                    print(f"  - {name}: {confidence}% confidence, Comment posted: {comment_posted}")
                    
                    if comment_posted and 'comment_text' in card:
                        comment_preview = card['comment_text'][:100] + "..." if len(card['comment_text']) > 100 else card['comment_text']
                        print(f"    Comment preview: {comment_preview}")
            else:
                print("No cards matched")
            
            # Show full response for debugging
            print("\nFull response keys:", list(result.keys()))
            
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Request failed: {e}")
        return False

if __name__ == "__main__":
    test_detailed_api()