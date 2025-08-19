#!/usr/bin/env python3
"""
Quick API Test
"""

import os
from dotenv import load_dotenv
import openai
from custom_trello import CustomTrelloClient

load_dotenv()

def test_openai():
    """Test OpenAI connection"""
    print("Testing OpenAI...")
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("No OpenAI API key found")
        return
        
    try:
        client = openai.OpenAI(api_key=api_key)
        
        # Try GPT-4 instead of GPT-5 first
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=10,
            timeout=10
        )
        print("OpenAI GPT-4 works!")
        
        # Now try GPT-5
        try:
            response = client.chat.completions.create(
                model="gpt-5",
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=10,
                timeout=10
            )
            print("OpenAI GPT-5 works!")
        except Exception as e:
            print(f"GPT-5 not available: {e}")
            print("Using GPT-4 as fallback")
            
    except Exception as e:
        print(f"OpenAI error: {e}")

def test_trello():
    """Test Trello connection"""
    print("Testing Trello...")
    try:
        client = CustomTrelloClient()
        boards = client.list_boards()
        print(f"Trello works! Found {len(boards)} boards")
        if boards:
            print(f"First board: {boards[0].name}")
    except Exception as e:
        print(f"Trello error: {e}")

def test_google_doc():
    """Test Google Doc reading"""
    print("Testing Google Docs...")
    
    # Add sys path for imports
    import sys
    sys.path.insert(0, 'src')
    
    try:
        from web_app import get_google_doc_text
        
        # Try with a test document ID (this will likely fail but shows if the function works)
        test_doc_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"  # Google example doc
        result = get_google_doc_text(test_doc_id)
        if result:
            print(f"Google Docs works! Got {len(result)} characters")
        else:
            print("Google Docs function exists but couldn't fetch document (expected for private docs)")
    except Exception as e:
        print(f"Google Docs error: {e}")

if __name__ == "__main__":
    test_openai()
    print()
    test_trello()
    print()
    test_google_doc()