#!/usr/bin/env python3
"""
Fetch all Trello cards from the board
"""

import os
import sys
sys.path.append('..')

from custom_trello import CustomTrelloClient
from dotenv import load_dotenv
import json

load_dotenv()

def fetch_all_cards():
    """Fetch all cards from Trello board"""
    api_key = os.getenv('TRELLO_API_KEY')
    token = os.getenv('TRELLO_TOKEN')
    board_id = os.getenv('TRELLO_BOARD_ID')
    
    client = CustomTrelloClient(api_key=api_key, token=token)
    
    # Get board
    board = client.get_board(board_id)
    print(f"Board: {board.name}")
    print("-" * 50)
    
    # Get all cards directly from the board
    cards = board.list_cards()
    
    # Get lists to map card list IDs to list names
    lists = board.get_lists()
    list_map = {lst.id: lst.name for lst in lists}
    
    all_cards = []
    
    for card in cards:
        list_name = list_map.get(card.list_id, 'Unknown List')
        card_info = {
            'name': card.name,
            'description': card.description,
            'list': list_name,
            'id': card.id
        }
        all_cards.append(card_info)
        print(f"[{list_name}] {card.name}")
    
    # Save to JSON
    with open('trello_cards.json', 'w') as f:
        json.dump(all_cards, f, indent=2)
    
    print(f"\n\nTotal cards found: {len(all_cards)}")
    return all_cards

if __name__ == "__main__":
    cards = fetch_all_cards()