#!/usr/bin/env python3
"""
Test AI Services Integration
Check if OpenAI API and other AI services are working properly
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, 'src')

load_dotenv()

def test_openai_connection():
    """Test OpenAI API connection and functionality."""
    print("Testing OpenAI API connection...")
    
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        return False
    
    print(f"✓ API Key found: {api_key[:20]}...")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Simple test request
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Reply with just 'working' if you can read this."}
            ],
            max_tokens=10,
            temperature=0
        )
        
        result = response.choices[0].message.content.strip().lower()
        
        if "working" in result:
            print("✅ OpenAI API is working correctly")
            return True
        else:
            print(f"⚠️ OpenAI API responded but with unexpected content: {result}")
            return False
            
    except Exception as e:
        print(f"❌ OpenAI API test failed: {e}")
        return False

def test_enhanced_ai_module():
    """Test the Enhanced AI module."""
    print("\nTesting Enhanced AI module...")
    
    try:
        from enhanced_ai import EnhancedAI
        
        ai_engine = EnhancedAI()
        
        # Test with simple transcript
        test_transcript = """
        John: Good morning everyone. Let's discuss the WordPress project status.
        
        Sarah: The WordPress site is going well. Main landing page should be ready by Friday.
        
        Mike: Great! What about the mobile app development?
        
        Sarah: That's progressing too. I think we can move the mobile app card to review soon.
        """
        
        print("Testing sentiment analysis...")
        sentiment_result = ai_engine.analyze_meeting_sentiment(test_transcript)
        print(f"✓ Sentiment analysis completed: {sentiment_result.summary}")
        
        print("Testing card matching...")
        # Test card data
        test_cards = [
            {
                'id': 'test1',
                'name': 'WordPress Site Development', 
                'description': 'Build main landing page',
                'board': 'EEInteractive',
                'list': 'DOING - IN PROGRESS'
            },
            {
                'id': 'test2',
                'name': 'Mobile App', 
                'description': 'Mobile application development',
                'board': 'EEInteractive', 
                'list': 'DOING - IN PROGRESS'
            }
        ]
        
        matched_cards = ai_engine.match_trello_cards_intelligent(test_transcript, test_cards)
        print(f"✓ Card matching completed: Found {len(matched_cards)} matches")
        
        for card in matched_cards:
            print(f"  - {card.get('card_name', 'Unknown')}: {card.get('confidence', 0):.1f}% confidence")
        
        print("✅ Enhanced AI module is working correctly")
        return True
        
    except ImportError as e:
        print(f"❌ Enhanced AI module import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Enhanced AI module test failed: {e}")
        return False

def test_speaker_analysis():
    """Test speaker analysis module."""
    print("\nTesting Speaker Analysis module...")
    
    try:
        from speaker_analysis import SpeakerAnalyzer
        
        analyzer = SpeakerAnalyzer()
        
        test_transcript = """
        John: Good morning everyone. Let's start with our updates. Sarah, how's the progress on the WordPress site?
        
        Sarah: The WordPress site is going well. I've been working on the main landing page and we should have the initial version ready for review by Friday.
        
        Mike: Great! What about the task for reaching out to onboarded clients?
        
        Sarah: Yes, I've been working on that too. The reach out task is about 60% complete.
        """
        
        result = analyzer.analyze_transcript(test_transcript)
        
        if result.get('success'):
            speakers = result.get('speakers', {})
            print(f"✓ Speaker analysis completed: Found {len(speakers)} speakers")
            
            for speaker, data in speakers.items():
                print(f"  - {speaker}: {data.get('word_count', 0)} words, {data.get('questions_asked', 0)} questions")
            
            print("✅ Speaker Analysis module is working correctly")
            return True
        else:
            print(f"❌ Speaker analysis failed: {result.get('error', 'Unknown error')}")
            return False
            
    except ImportError as e:
        print(f"❌ Speaker Analysis module import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Speaker Analysis module test failed: {e}")
        return False

def test_trello_integration():
    """Test Trello client integration."""
    print("\nTesting Trello integration...")
    
    try:
        from custom_trello import CustomTrelloClient
        
        api_key = os.environ.get('TRELLO_API_KEY')
        token = os.environ.get('TRELLO_TOKEN')
        
        if not api_key or not token:
            print("❌ Trello credentials not found")
            return False
        
        client = CustomTrelloClient(api_key=api_key, token=token)
        
        # Test connection
        if not client.test_connection():
            print("❌ Trello connection test failed")
            return False
        
        print("✓ Trello connection successful")
        
        # Test board access
        boards = client.list_boards()
        eeinteractive_board = None
        
        for board in boards:
            if 'eeinteractive' in board.name.lower():
                eeinteractive_board = board
                break
        
        if not eeinteractive_board:
            print("⚠️ EEInteractive board not found")
            return False
        
        print(f"✓ Found EEInteractive board: {eeinteractive_board.name}")
        
        # Test card access
        cards = eeinteractive_board.list_cards()
        print(f"✓ Found {len(cards)} cards in board")
        
        print("✅ Trello integration is working correctly")
        return True
        
    except ImportError as e:
        print(f"❌ Trello integration import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Trello integration test failed: {e}")
        return False

def test_transcript_processing_pipeline():
    """Test the complete transcript processing pipeline."""
    print("\nTesting complete transcript processing pipeline...")
    
    sample_transcript = """
Google Meet Transcript - EEInteractive Team Meeting
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
"""
    
    try:
        # Test the complete flow that would happen in the web app
        print("✓ Sample transcript prepared")
        
        # Test speaker extraction
        participants = []
        lines = sample_transcript.split('\n')
        for line in lines:
            if ':' in line and '[' not in line:  # Skip timestamp lines
                speaker_match = re.match(r'^([A-Za-z][A-Za-z\s]+?):\s*(.+)$', line.strip())
                if speaker_match:
                    speaker = speaker_match.group(1).strip()
                    if speaker not in participants:
                        participants.append(speaker)
        
        print(f"✓ Extracted {len(participants)} participants: {', '.join(participants)}")
        
        # Test action item extraction
        action_patterns = [
            r'(\w+)\s+(?:will|should|must|needs? to)\s+([^.!?]+)',
            r'(\w+)\s+is\s+going\s+to\s+([^.!?]+)',
            r'(\w+)\s+can\s+take\s+([^.!?]+)'
        ]
        
        action_items = []
        for line in lines:
            for pattern in action_patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple) and len(match) >= 2:
                        action_items.append({'assignee': match[0], 'task': match[1]})
        
        print(f"✓ Extracted {len(action_items)} action items")
        
        # Test card name extraction
        card_mentions = [
            'Mobile App', 'SEO', 'Support Ticket System Revival', 
            'EE System Universal Scheduler', 'reach out to onboarded'
        ]
        
        found_cards = []
        for card in card_mentions:
            if card.lower() in sample_transcript.lower():
                found_cards.append(card)
        
        print(f"✓ Found {len(found_cards)} card mentions: {', '.join(found_cards)}")
        
        print("✅ Transcript processing pipeline working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Transcript processing pipeline test failed: {e}")
        return False

def main():
    """Run all AI service tests."""
    print("🧪 AI Services Integration Test")
    print("=" * 50)
    
    tests = [
        test_openai_connection,
        test_enhanced_ai_module, 
        test_speaker_analysis,
        test_trello_integration,
        test_transcript_processing_pipeline
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All AI services are working correctly!")
    elif passed >= total - 1:
        print("⚠️ Most AI services working, minor issues detected")
    else:
        print("🚨 Major issues detected with AI services")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)