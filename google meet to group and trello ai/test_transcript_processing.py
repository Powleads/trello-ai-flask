#!/usr/bin/env python3
"""
Test transcript processing with actual sample data
"""

import os
import sys
import json
import requests
from datetime import datetime

sys.path.insert(0, 'src')

# Load sample transcript
def get_sample_transcript():
    """Get the sample transcript that mentions actual Trello cards."""
    return """Google Meet Transcript - EEInteractive Team Meeting
Date: January 18, 2025
Time: 10:00 AM - 10:45 AM EST
Participants: Sarah Chen, Mike Johnson, Emily Rodriguez, David Kim, Lisa Thompson

[00:00:15] Sarah Chen: Good morning everyone! Thanks for joining our weekly sync. Let's dive right in. Mike, can you give us an update on the mobile app development?

[00:00:28] Mike Johnson: Sure, Sarah. So the Mobile App is progressing well. We've completed the UI mockups and the backend API is about 70% done. We're still targeting end of month for beta testing.

[00:00:45] Sarah Chen: Excellent! Any blockers we should be aware of?

[00:00:52] Mike Johnson: Not really blockers, but we might need some help with the push notification integration. I'll reach out to the DevOps team later today.

[00:01:05] Sarah Chen: Sounds good. Emily, how's the SEO project coming along? I know it's been marked as blocked.

[00:01:15] Emily Rodriguez: Yeah, about that... The SEO work is definitely blocked right now. We need access to Google Search Console and the analytics dashboard. I've been waiting on credentials from IT for about a week now.

[00:01:32] David Kim: Oh, I can help with that! I have admin access. Let's sync after this meeting and I'll get you sorted.

[00:01:40] Emily Rodriguez: That would be amazing, David! Thanks so much. Once I have access, I can start the technical audit and keyword research.

[00:01:52] Sarah Chen: Perfect! Problem solved. Lisa, can you update us on the Support Ticket System Revival? I saw it was marked complete in Trello.

[00:02:05] Lisa Thompson: Yes! Happy to report the Support Ticket System Revival is fully complete as of yesterday. We've migrated all the old tickets, set up the new categories, and trained the support team on the new workflow.

[00:02:22] Mike Johnson: That's fantastic! What's the response time looking like now?

[00:02:28] Lisa Thompson: We've cut it down from 48 hours to under 12 hours for initial response. The automation is handling about 30% of common queries automatically.

[00:02:40] Sarah Chen: Incredible work, Lisa! David, I wanted to check in on the EE System Universal Scheduler. Where are we with that?

[00:02:52] David Kim: The EE System Universal Scheduler is also complete! We launched it on Wednesday. Already have 15 centers using it actively. The feedback has been really positive.

[00:03:08] Emily Rodriguez: Oh that's great! Are the centers finding it easy to integrate with their existing calendars?

[00:03:16] David Kim: Yes, most of them. We have Google Calendar and Outlook integration working smoothly. A few centers using Apple Calendar had minor issues, but we pushed a fix this morning.

[00:03:30] Sarah Chen: Excellent progress everyone! Now, let's talk about next priorities. We need to tackle the onboarding improvements. I know there's a task about reaching out to onboarded centers to show leads.

[00:03:45] Mike Johnson: Right, the "reach out to onboarded, show leads" task. Who's taking that one?

[00:03:53] Emily Rodriguez: I can take that after the SEO project gets unblocked. It aligns well with the marketing initiatives I'm working on.

[00:04:02] Lisa Thompson: Makes sense. I can provide the list of recently onboarded centers from the support ticket data.

[00:04:10] Sarah Chen: Perfect teamwork! Let's also make sure we're following up on the forever tasks. I know we have ongoing work with adding Facebook pixels to landing pages.

[00:04:24] David Kim: Yeah, I've been slowly working through those. Added pixels to 12 more landing pages this week. Still have about 30 to go.

[00:04:35] Mike Johnson: Do we have analytics on the conversion improvements from the pixels we've already added?

[00:04:42] David Kim: Early data shows about 15% better retargeting effectiveness, but we need more time for statistically significant results.

[00:04:52] Sarah Chen: Good to hear there's positive movement. Any other updates before we wrap up?

[00:05:02] Lisa Thompson: Quick one - I noticed we have a task to organize court documents and evidence. That seems out of scope for our team. Should we reassign that?

[00:05:15] Sarah Chen: Good catch! That's actually for the legal team. I'll move it to their board after this meeting.

[00:05:23] Emily Rodriguez: Also, just a reminder to everyone to check the Trello board daily. I've noticed some tasks sitting in review for a while.

[00:05:33] Mike Johnson: Guilty as charged! I'll review the pending items today.

[00:05:39] David Kim: Same here. I have two items waiting for my approval.

[00:05:45] Sarah Chen: Great! Let's make sure we're keeping the board current. It really helps with our velocity tracking. Alright, unless there's anything else, let's get back to building awesome things!

[00:05:58] Everyone: Thanks! / See you! / Bye!

[00:06:02] Meeting ended"""

def test_basic_matching():
    """Test basic card matching logic."""
    print("Testing basic card matching...")
    
    # Get actual cards from Trello
    from custom_trello import CustomTrelloClient
    
    try:
        client = CustomTrelloClient()
        boards = client.list_boards()
        
        eeinteractive = None
        for board in boards:
            if 'eeinteractive' in board.name.lower():
                eeinteractive = board
                break
        
        if not eeinteractive:
            print("[ERROR] EEInteractive board not found")
            return False
        
        cards = eeinteractive.list_cards()
        print(f"[INFO] Found {len(cards)} total cards")
        
        # Get sample transcript
        transcript = get_sample_transcript()
        
        # Expected matches based on transcript content
        expected_matches = [
            "Mobile App",
            "SEO", 
            "Support Ticket System Revival",
            "EE System Universal Scheduler", 
            "reach out to onboarded, show leads"
        ]
        
        print("\nExpected matches from transcript:")
        for expected in expected_matches:
            print(f"  - {expected}")
        
        print("\nActual card names in Trello:")
        actual_cards = []
        for card in cards[:10]:  # Show first 10
            actual_cards.append(card.name)
            print(f"  - {card.name}")
        
        print("\nTesting matching logic...")
        matches = []
        
        for card in cards:
            confidence = 0
            
            # Direct name matching
            for expected in expected_matches:
                if expected.lower() in card.name.lower() or card.name.lower() in expected.lower():
                    confidence += 80
                    break
            
            # Keyword matching
            transcript_lower = transcript.lower()
            card_words = card.name.lower().split()
            
            for word in card_words:
                if len(word) > 3 and word in transcript_lower:
                    confidence += 20
            
            if confidence >= 50:
                matches.append({
                    'name': card.name,
                    'confidence': confidence,
                    'url': card.url
                })
        
        print(f"\n[RESULT] Found {len(matches)} matches:")
        for match in matches:
            print(f"  - {match['name']} ({match['confidence']}% confidence)")
        
        return len(matches) > 0
        
    except Exception as e:
        print(f"[ERROR] Basic matching test failed: {e}")
        return False

def test_web_api():
    """Test the web API processing endpoint."""
    print("\nTesting web API processing...")
    
    try:
        transcript = get_sample_transcript()
        
        # Test API endpoint
        url = "http://localhost:5000/api/process-transcript"
        data = {"direct_text": transcript}
        
        print(f"[INFO] Sending transcript to {url}")
        print(f"[INFO] Transcript length: {len(transcript)} characters")
        
        response = requests.post(url, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                print(f"[OK] Processing successful")
                print(f"[INFO] Cards found: {result.get('cards_found', 0)}")
                print(f"[INFO] Word count: {result.get('word_count', 0)}")
                
                matched_cards = result.get('matched_cards', [])
                if matched_cards:
                    print(f"\n[MATCHES] Found {len(matched_cards)} card matches:")
                    for card in matched_cards:
                        print(f"  - {card.get('name', 'Unknown')}: {card.get('confidence', 0)}% confidence")
                else:
                    print("[WARNING] No card matches found")
                
                return len(matched_cards) > 0
            else:
                print(f"[ERROR] Processing failed: {result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"[ERROR] API request failed with status {response.status_code}")
            print(f"[ERROR] Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Web API test failed: {e}")
        return False

def main():
    """Run transcript processing tests."""
    print("Transcript Processing Test")
    print("=" * 50)
    
    tests = [
        test_basic_matching,
        test_web_api
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
                print("[PASS]\n")
            else:
                print("[FAIL]\n")
        except Exception as e:
            print(f"[CRASH] {e}\n")
    
    print(f"Results: {passed}/{len(tests)} tests passed")
    
    if passed == 0:
        print("\n[DIAGNOSIS] No card matches found. Possible issues:")
        print("1. OpenAI quota exceeded (confirmed) - AI matching disabled")
        print("2. Card names don't match transcript keywords exactly")
        print("3. Matching logic needs improvement")
        print("4. Sample transcript needs better keyword alignment")

if __name__ == "__main__":
    main()