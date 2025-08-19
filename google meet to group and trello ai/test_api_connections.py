#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Connection Test Suite
Tests all integrations: OpenAI GPT-5, Google Docs, Trello APIs
"""

import os
import sys
from dotenv import load_dotenv
import openai
from custom_trello import CustomTrelloClient

# Load environment
load_dotenv()

def test_openai_connection():
    """Test OpenAI GPT-5 connection."""
    print("[AI] Testing OpenAI GPT-5 Connection...")
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        return False
    
    try:
        client = openai.OpenAI(api_key=api_key)
        
        # Test with a simple prompt
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[{"role": "user", "content": "Say 'OpenAI GPT-5 connection successful!'"}],
            max_tokens=50
        )
        
        result = response.choices[0].message.content
        print(f"[SUCCESS] OpenAI GPT-5 Response: {result}")
        return True
        
    except Exception as e:
        print(f"[ERROR] OpenAI GPT-5 Connection Failed: {e}")
        # Try fallback to GPT-4 Turbo
        try:
            print("[RETRY] Trying fallback to GPT-4 Turbo...")
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": "Say 'GPT-4 Turbo fallback successful!'"}],
                max_tokens=50
            )
            result = response.choices[0].message.content
            print(f"[WARNING] Fallback Success: {result}")
            return "fallback"
        except Exception as e2:
            print(f"[ERROR] Fallback also failed: {e2}")
            return False

def test_trello_connection():
    """Test Trello API connection."""
    print("\n[TRELLO] Testing Trello API Connection...")
    
    api_key = os.getenv('TRELLO_API_KEY')
    token = os.getenv('TRELLO_TOKEN')
    
    if not api_key or not token:
        print("[ERROR] TRELLO_API_KEY or TRELLO_TOKEN not found in environment")
        print(f"  API Key present: {bool(api_key)}")
        print(f"  Token present: {bool(token)}")
        return False
    
    try:
        client = CustomTrelloClient(api_key, token)
        
        # Test by listing boards
        boards = client.list_boards()
        if boards:
            print(f"[SUCCESS] Trello Connection Successful! Found {len(boards)} boards:")
            for board in boards[:3]:  # Show first 3 boards
                print(f"  - {board.name} (ID: {board.id})")
            return True
        else:
            print("[WARNING] Trello connected but no boards found")
            return True
            
    except Exception as e:
        print(f"[ERROR] Trello Connection Failed: {e}")
        return False

def test_google_docs_connection():
    """Test Google Docs API connection."""
    print("\n[GOOGLE] Testing Google Docs API Connection...")
    
    try:
        from src.integrations.google_drive import GoogleDriveClient
        
        # Check for credentials
        creds_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
        token_file = os.getenv('GOOGLE_TOKEN_FILE', 'token.pickle')
        
        if not os.path.exists(creds_file) and not os.getenv('GOOGLE_CLIENT_ID'):
            print("[ERROR] Google credentials not found")
            print(f"  Looking for: {creds_file}")
            print("  Or environment variables: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET")
            return False
        
        # Try to initialize client
        drive_client = GoogleDriveClient(
            credentials_file=creds_file,
            token_file=token_file
        )
        
        print("[SUCCESS] Google Drive Client initialized successfully")
        print("[INFO] Note: Full OAuth flow may be required on first use")
        return True
        
    except Exception as e:
        print(f"[ERROR] Google Docs Integration Failed: {e}")
        return False

def test_environment_variables():
    """Test all required environment variables."""
    print("\n[ENV] Checking Environment Variables...")
    
    required_vars = {
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'TRELLO_API_KEY': os.getenv('TRELLO_API_KEY'),
        'TRELLO_TOKEN': os.getenv('TRELLO_TOKEN')
    }
    
    optional_vars = {
        'GOOGLE_CLIENT_ID': os.getenv('GOOGLE_CLIENT_ID'),
        'GOOGLE_CLIENT_SECRET': os.getenv('GOOGLE_CLIENT_SECRET'),
        'GOOGLE_CREDENTIALS_FILE': os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json'),
    }
    
    print("Required Variables:")
    all_required = True
    for var, value in required_vars.items():
        status = "[OK]" if value else "[MISSING]"
        masked_value = f"{value[:10]}..." if value and len(value) > 10 else "NOT SET"
        print(f"  {status} {var}: {masked_value}")
        if not value:
            all_required = False
    
    print("\nOptional Variables (for Google integration):")
    for var, value in optional_vars.items():
        status = "[OK]" if value else "[OPTIONAL]"
        if var.endswith('_FILE'):
            display_value = f"File exists: {os.path.exists(value)}" if value else "NOT SET"
        else:
            display_value = f"{value[:10]}..." if value and len(value) > 10 else "NOT SET"
        print(f"  {status} {var}: {display_value}")
    
    return all_required

def main():
    """Run all API connection tests."""
    print("[TEST] API Connection Test Suite")
    print("=" * 50)
    
    # Test environment variables first
    env_ok = test_environment_variables()
    
    if not env_ok:
        print("\n[ERROR] Some required environment variables are missing!")
        print("[TIP] Please check your .env file and ensure all API keys are configured.")
        return False
    
    # Test individual connections
    results = {}
    results['openai'] = test_openai_connection()
    results['trello'] = test_trello_connection()
    results['google'] = test_google_docs_connection()
    
    # Summary
    print("\n" + "=" * 50)
    print("[RESULTS] Test Results Summary:")
    
    for service, result in results.items():
        if result is True:
            print(f"[SUCCESS] {service.upper()}: CONNECTED")
        elif result == 'fallback':
            print(f"[WARNING] {service.upper()}: FALLBACK MODE")
        else:
            print(f"[ERROR] {service.upper()}: FAILED")
    
    # Overall status
    success_count = sum(1 for r in results.values() if r in [True, 'fallback'])
    total_count = len(results)
    
    if success_count == total_count:
        print(f"\n[SUCCESS] ALL SYSTEMS OPERATIONAL! ({success_count}/{total_count})")
        return True
    else:
        print(f"\n[WARNING] PARTIAL SUCCESS: ({success_count}/{total_count}) services working")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)