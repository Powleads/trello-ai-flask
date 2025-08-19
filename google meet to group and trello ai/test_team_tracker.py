#!/usr/bin/env python3
"""
Test team tracker API
"""

import requests
import json
import time

def test_team_tracker_api():
    """Test the team tracker scan-cards endpoint."""
    
    print("Testing team tracker API...")
    
    url = "http://localhost:5002/api/scan-cards"
    
    try:
        start_time = time.time()
        response = requests.post(url, json={}, timeout=60)
        end_time = time.time()
        
        print(f"Request took {end_time - start_time:.2f} seconds")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result.get('success')}")
            print(f"Total cards: {result.get('total_cards', 0)}")
            print(f"Processing time: {result.get('processing_time', 0):.2f}s")
            
            cards = result.get('cards', [])
            if cards:
                print(f"\nFirst 3 cards:")
                for i, card in enumerate(cards[:3]):
                    name = card.get('name', 'Unknown')
                    days = card.get('days_since_comment', 'N/A')
                    board = card.get('board_name', 'Unknown')
                    print(f"  {i+1}. {name} - {days} days since comment - {board}")
            
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Request failed: {e}")
        return False

if __name__ == "__main__":
    test_team_tracker_api()