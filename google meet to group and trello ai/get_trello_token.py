#!/usr/bin/env python3
"""
Simple Trello Token Generator

Use this to get a proper Trello OAuth token.
"""

import webbrowser
from urllib.parse import urlencode

def main():
    print("Trello Token Generator")
    print("====================")
    
    api_key = "5d7cc4c72ddcc47fe2de385510402b84"
    
    # Create authorization URL
    params = {
        'expiration': 'never',
        'scope': 'read,write',
        'response_type': 'token',
        'key': api_key,
        'name': 'Meeting Automation Tool'
    }
    
    auth_url = f"https://trello.com/1/authorize?{urlencode(params)}"
    
    print(f"1. Opening authorization URL in browser...")
    print(f"   {auth_url}")
    print()
    print("2. Click 'Allow' to authorize the application")
    print("3. Copy the token from the page")
    print("4. Paste it below:")
    print()
    
    try:
        webbrowser.open(auth_url)
    except:
        print("Could not open browser automatically.")
        print("Please copy this URL and open it manually:")
        print(auth_url)
    
    token = input("Enter your Trello token: ").strip()
    
    if token:
        print(f"\nYour Trello token: {token}")
        print("\nAdd this to your .env file:")
        print(f"TRELLO_TOKEN={token}")
        
        # Test the token
        print("\nTesting token...")
        import requests
        
        test_url = f"https://api.trello.com/1/members/me?key={api_key}&token={token}"
        try:
            response = requests.get(test_url)
            if response.status_code == 200:
                user_data = response.json()
                print(f"SUCCESS: Connected as {user_data.get('fullName', 'Unknown')}")
            else:
                print(f"ERROR: Token test failed with status {response.status_code}")
        except Exception as e:
            print(f"ERROR: Token test failed: {e}")
    else:
        print("No token provided.")

if __name__ == "__main__":
    main()