#!/usr/bin/env python3
"""
Test Script for Simplified Gmail Onboarding Tracker
Tests the "New Tech Onboarding" email filtering functionality
"""

import sys
from datetime import datetime
from gmail_tracker import GmailTracker

def test_onboarding_tracker():
    """Test the simplified onboarding tracker."""
    print("TESTING GMAIL ONBOARDING TRACKER")
    print("=" * 50)
    
    # Initialize tracker
    tracker = GmailTracker()
    print("Gmail tracker initialized")
    
    # Test Gmail API setup
    if tracker.setup_gmail_api():
        print("Gmail API connection established")
    else:
        print("Gmail API setup failed - check credentials")
        return False
    
    # Test simplified email scanning
    print("\nTesting simplified email scanning...")
    print("Looking for 'New Tech Onboarding' emails in last 24 hours...")
    
    try:
        # Test the simplified scan
        emails = tracker.scan_recent_emails(
            hours_back=24, 
            subject_filter="New Tech Onboarding"
        )
        
        print(f"Scan completed: {len(emails)} emails found")
        
        if emails:
            print(f"\nFOUND ONBOARDING EMAILS:")
            for i, email in enumerate(emails, 1):
                print(f"  {i}. From: {email.get('sender', 'Unknown')}")
                print(f"     Subject: {email.get('subject', 'No subject')}")
                print(f"     Date: {email.get('date', 'Unknown date')}")
                print()
                
                # Test categorization
                analysis = tracker.categorize_email_basic(
                    email.get('subject', ''),
                    email.get('content', ''),
                    email.get('sender', '')
                )
                
                print(f"     Category: {analysis['category']}")
                print(f"     Priority: {analysis['priority']}/5")
                print(f"     Assigned to: {analysis['suggested_assignee']}")
                print(f"     Keywords: {', '.join(analysis['keywords'])}")
                print(f"     Action required: {analysis['action_required']}")
                print("-" * 40)
        else:
            print("No 'New Tech Onboarding' emails found in last 24 hours")
            
        # Test automated scan
        print("\nTesting automated scan function...")
        tracker.run_automated_scan()
        
        print("\nAll tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error during testing: {e}")
        return False

def test_offline_categorization():
    """Test categorization without Gmail API."""
    print("\nTESTING OFFLINE CATEGORIZATION")
    print("=" * 50)
    
    tracker = GmailTracker()
    
    # Test samples
    test_cases = [
        {
            'subject': 'New Tech Onboarding - Client ABC Setup Required',
            'content': 'Hello, we have a new client that needs tech onboarding for their EESystem setup.',
            'sender': 'support@example.com'
        },
        {
            'subject': 'URGENT: New Tech Onboarding - Immediate Setup Needed',
            'content': 'This is urgent - client needs immediate onboarding assistance for their new system.',
            'sender': 'admin@client.com'
        },
        {
            'subject': 'New Tech Onboarding - Standard Setup Process',
            'content': 'Standard onboarding request for new client getting started with EESystem.',
            'sender': 'info@partner.com'
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Subject: {case['subject']}")
        print(f"From: {case['sender']}")
        
        analysis = tracker.categorize_email_basic(
            case['subject'],
            case['content'],
            case['sender']
        )
        
        print(f"Result:")
        print(f"  Category: {analysis['category']}")
        print(f"  Priority: {analysis['priority']}/5")
        print(f"  Assigned: {analysis['suggested_assignee']}")
        print(f"  Keywords: {', '.join(analysis['keywords'])}")
        print(f"  Action: {analysis['action_required']}")
        print(f"  Summary: {analysis['summary']}")
    
    print("\nOffline categorization tests completed!")

if __name__ == "__main__":
    print("Starting Gmail Onboarding Tracker Tests")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Always run offline tests
    test_offline_categorization()
    
    # Ask user if they want to run online tests
    if len(sys.argv) > 1 and sys.argv[1].lower() == '--online':
        print("\n" + "=" * 60)
        test_onboarding_tracker()
    else:
        print("\n" + "=" * 60)
        print("To test Gmail API connection, run:")
        print("   python test_gmail_onboarding.py --online")
    
    print(f"\nAll tests completed at: {datetime.now().strftime('%H:%M:%S')}")