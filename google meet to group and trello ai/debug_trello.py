#!/usr/bin/env python3
"""
Debug Trello Integration - Find actual board names
"""

import os
from dotenv import load_dotenv
from custom_trello import CustomTrelloClient

load_dotenv()

def debug_trello_boards():
    """Debug Trello boards to find actual names"""
    print("[DEBUG] Debugging Trello Integration...")
    
    try:
        client = CustomTrelloClient()
        boards = client.list_boards()
        
        print(f"[SUCCESS] Found {len(boards)} boards:")
        print("=" * 50)
        
        for i, board in enumerate(boards, 1):
            print(f"{i}. Board Name: '{board.name}'")
            print(f"   Board ID: {board.id}")
            print(f"   Closed: {board.closed}")
            
            # Check for EE-related names
            name_lower = board.name.lower()
            if 'ee' in name_lower or 'interactive' in name_lower:
                print(f"   [MATCH] POTENTIAL MATCH!")
                
                # Get lists for this board
                try:
                    board_lists = board.get_lists()
                    print(f"   [LISTS] Lists ({len(board_lists)}):")
                    for lst in board_lists:
                        list_name_lower = lst.name.lower()
                        if 'doing' in list_name_lower or 'in progress' in list_name_lower:
                            print(f"      - {lst.name} (ID: {lst.id}) [TARGET]")
                        else:
                            print(f"      - {lst.name} (ID: {lst.id})")
                except Exception as e:
                    print(f"   [ERROR] Error getting lists: {e}")
            
            print("-" * 30)
        
        # Look for exact matches
        print("\n[RESULTS] Search Results:")
        ee_boards = [b for b in boards if 'ee' in b.name.lower()]
        interactive_boards = [b for b in boards if 'interactive' in b.name.lower()]
        
        if ee_boards:
            print(f"Boards with 'EE': {[b.name for b in ee_boards]}")
        if interactive_boards:
            print(f"Boards with 'Interactive': {[b.name for b in interactive_boards]}")
            
        # Current search logic from web_app.py
        eeinteractive_board = None
        for board in boards:
            if board.closed:
                continue
            if 'eeinteractive' in board.name.lower():
                eeinteractive_board = board
                break
        
        if eeinteractive_board:
            print(f"\n[SUCCESS] Current logic found: {eeinteractive_board.name}")
        else:
            print("\n[ERROR] Current logic (looking for 'eeinteractive') found no matches")
            print("[SUGGESTIONS] Try these boards:")
            for board in boards[:5]:  # Show first 5 boards
                if not board.closed:
                    print(f"   - Try board: '{board.name}'")
        
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    debug_trello_boards()