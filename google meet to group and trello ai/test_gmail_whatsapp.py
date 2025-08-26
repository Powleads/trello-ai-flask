#!/usr/bin/env python3
"""
Test script for Gmail Tracker WhatsApp notifications
"""

import os
import sys
import io

# Set UTF-8 encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dotenv import load_dotenv
from gmail_tracker import GmailTracker

# Load environment variables
load_dotenv()

def test_whatsapp_connection():
    """Test WhatsApp API connection."""
    print("=" * 50)
    print("Testing Gmail Tracker WhatsApp Integration")
    print("=" * 50)
    
    # Check environment variables
    print("\n1. Checking environment variables...")
    green_api_token = os.getenv('GREEN_API_TOKEN')
    green_api_instance = os.getenv('GREEN_API_INSTANCE_ID', '7105263120')
    
    if not green_api_token:
        print("❌ GREEN_API_TOKEN not found in .env file")
        print("Please add: GREEN_API_TOKEN=your_token_here")
        return False
    else:
        print(f"✅ GREEN_API_TOKEN found (ends with ...{green_api_token[-4:]})")
        print(f"✅ GREEN_API_INSTANCE_ID: {green_api_instance}")
    
    # Initialize Gmail Tracker
    print("\n2. Initializing Gmail Tracker...")
    tracker = GmailTracker()
    print("✅ Gmail Tracker initialized")
    
    # Test WhatsApp message sending
    print("\n3. Testing WhatsApp message sending...")
    
    # Test message to James Taylor (you can change this for testing)
    test_number = "19056064550@c.us"  # James Taylor's number
    test_message = """🧪 TEST MESSAGE - Gmail Tracker WhatsApp Integration

This is a test message from the Gmail Tracker.
If you receive this, WhatsApp notifications are working correctly!

- JGV EEsystems"""
    
    print(f"Sending test message to {test_number}...")
    result = tracker.send_whatsapp_message(test_number, test_message)
    
    if result:
        print("✅ Test message sent successfully!")
    else:
        print("❌ Failed to send test message")
        print("Check your GREEN_API_TOKEN and internet connection")
        return False
    
    return True

def test_email_categorization():
    """Test email categorization without sending notifications."""
    print("\n4. Testing email categorization...")
    
    tracker = GmailTracker()
    
    # Test email samples
    test_emails = [
        {
            "subject": "New client onboarding - ABC Company",
            "content": "We have a new client starting onboarding process today.",
            "sender": "client@example.com"
        },
        {
            "subject": "GoHighLevel Support Ticket #12345",
            "content": "Technical issue with automation workflow not triggering.",
            "sender": "support@gohighlevel.com"
        },
        {
            "subject": "URGENT: Website is down",
            "content": "The main website is showing 500 errors. Need immediate help!",
            "sender": "team@justgoingviral.com"
        }
    ]
    
    for i, email in enumerate(test_emails, 1):
        print(f"\nTest Email {i}:")
        print(f"  Subject: {email['subject']}")
        
        # Categorize email
        result = tracker.categorize_email_with_ai(
            email['subject'],
            email['content'],
            email['sender']
        )
        
        print(f"  Category: {result.get('category', 'unknown')}")
        print(f"  Priority: {result.get('priority', 0)}/5")
        print(f"  Assigned to: {result.get('suggested_assignee', 'unassigned')}")
        print(f"  Summary: {result.get('summary', 'No summary')}")
        print(f"  Action Required: {result.get('action_required', False)}")
    
    print("\n✅ Email categorization test complete")

def main():
    """Run all tests."""
    print("\n🚀 Starting Gmail Tracker WhatsApp Integration Tests\n")
    
    # Test WhatsApp connection
    whatsapp_ok = test_whatsapp_connection()
    
    if whatsapp_ok:
        # Test email categorization
        test_email_categorization()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed successfully!")
        print("=" * 50)
        
        print("\n📝 Next Steps:")
        print("1. Verify you received the test WhatsApp message")
        print("2. Check that email categorization is working correctly")
        print("3. Run the full Gmail scan with: python gmail_tracker.py")
        print("4. Set up scheduled scanning for 6 AM and 6 PM PST")
    else:
        print("\n" + "=" * 50)
        print("❌ Tests failed - please fix the issues above")
        print("=" * 50)

if __name__ == "__main__":
    main()