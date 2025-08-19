#!/usr/bin/env python3
"""
Test Team Tracker Trello Integration
"""

import os
import requests
import json
from dotenv import load_dotenv
from custom_trello import CustomTrelloClient

load_dotenv()

def test_team_tracker_api():
    """Test the Team Tracker API endpoint directly"""
    print("[TEST] Testing Team Tracker API endpoint...")
    
    try:
        # Make a request to the scan-cards endpoint
        response = requests.post('http://localhost:5000/api/scan-cards', timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"[SUCCESS] Team Tracker API working!")
                print(f"Found {len(data.get('cards', []))} cards")
                return True
            else:
                print(f"[ERROR] API returned error: {data.get('error')}")
                return False
        else:
            print(f"[ERROR] HTTP {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("[WARNING] Flask app not running. Testing Trello client directly...")
        return test_trello_client_directly()
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def test_trello_client_directly():
    """Test Trello client directly like the web app does"""
    print("[TEST] Testing Trello client directly...")
    
    try:
        # Initialize client same way as web_app.py
        trello_client = CustomTrelloClient(
            api_key=os.environ.get('TRELLO_API_KEY'),
            token=os.environ.get('TRELLO_TOKEN')
        )
        
        if not trello_client:
            print("[ERROR] Trello client not available")
            return False
        
        # Get only the EEInteractive board (same logic as web_app.py)
        boards = trello_client.list_boards()
        eeinteractive_board = None
        
        print(f"[INFO] Found {len(boards)} total boards")
        
        for board in boards:
            print(f"[INFO] Checking board: '{board.name}' (closed: {board.closed})")
            if board.closed:
                continue
            if 'eeinteractive' in board.name.lower():
                eeinteractive_board = board
                print(f"[MATCH] Found EEInteractive board: {board.name}")
                break
        
        if not eeinteractive_board:
            print("[ERROR] EEInteractive board not found")
            print("[INFO] Available boards:")
            for board in boards:
                if not board.closed:
                    print(f"  - {board.name}")
            return False
        
        # Get lists for this board
        board_lists = eeinteractive_board.get_lists()
        list_names = {lst.id: lst.name for lst in board_lists}
        
        print(f"[INFO] Available lists on EEInteractive board:")
        for lst in board_lists:
            print(f"  - {lst.name} (ID: {lst.id})")
        
        # Find DOING/IN PROGRESS lists only (same logic as web_app.py)
        target_lists = []
        for lst in board_lists:
            list_name_lower = lst.name.lower()
            if 'doing' in list_name_lower or 'in progress' in list_name_lower:
                target_lists.append(lst.id)
                print(f"[TARGET] Found target list: {lst.name}")
        
        if not target_lists:
            print("[ERROR] No DOING/IN PROGRESS lists found")
            return False
        
        # Get cards from target lists
        board_cards = eeinteractive_board.list_cards()
        target_cards = []
        
        for card in board_cards:
            if card.closed:
                continue
            if card.list_id in target_lists:
                target_cards.append(card)
        
        print(f"[SUCCESS] Found {len(target_cards)} cards in target lists:")
        for card in target_cards[:5]:  # Show first 5
            list_name = list_names.get(card.list_id, 'Unknown List')
            print(f"  - {card.name} (List: {list_name})")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Team Tracker Integration Test")
    print("=" * 50)
    
    # Test 1: API endpoint
    api_success = test_team_tracker_api()
    
    print("\n" + "-" * 30)
    
    # Test 2: Direct client test
    client_success = test_trello_client_directly()
    
    print("\n" + "=" * 50)
    if api_success or client_success:
        print("[OVERALL] SUCCESS - Team Tracker can access Trello!")
    else:
        print("[OVERALL] FAILED - Team Tracker cannot access Trello")