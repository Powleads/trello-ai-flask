#!/usr/bin/env python3
"""
Test script for the fixed transcript processing API
"""

import requests
import json

# Test data
test_transcript = """John: Good morning everyone. Let's start with our project updates. Sarah, how's the WordPress site coming along?

Sarah: Thanks John. The WordPress development is progressing well. We should have it ready by Friday. I need to finish the client feedback integration though.

Mike: That's great progress! What about the logo approval we discussed last week?

Sarah: Actually, we're still waiting for approval on that. It's been two weeks now and it's blocking our progress.

John: That's concerning. Mike, can you reach out to the client directly today?

Mike: Absolutely. I'll call them this afternoon. Should we proceed with the backend development while waiting?

Sarah: Yes, I think we should. We can always adjust the frontend later.

John: Agreed. Let's make that decision final. Sarah, please coordinate with the backend team."""

def test_direct_text_processing():
    """Test direct text transcript processing."""
    print("Testing direct text transcript processing...")
    
    url = "http://localhost:5000/api/process-transcript"
    data = {
        "direct_text": test_transcript
    }
    
    try:
        response = requests.post(url, json=data, timeout=30)
        result = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Success: {result.get('success', False)}")
        
        if result.get('success'):
            print(f"Message: {result.get('message', 'N/A')}")
            print(f"Source Type: {result.get('source_type', 'N/A')}")
            print(f"Word Count: {result.get('word_count', 'N/A')}")
            print(f"Transcript ID: {result.get('transcript_id', 'N/A')}")
            print(f"Cards Found: {result.get('cards_found', 0)}")
            
            # Check analysis results
            analysis = result.get('analysis_results', {})
            print("\n--- Analysis Results ---")
            
            if 'speaker_analysis' in analysis:
                speaker_data = analysis['speaker_analysis']
                if 'speakers' in speaker_data:
                    print(f"Speakers found: {len(speaker_data['speakers'])}")
                    for speaker in speaker_data['speakers'][:3]:  # Show first 3
                        print(f"  - {speaker.get('speaker', 'Unknown')}: {speaker.get('percentage', 0):.1f}%")
            
            if 'sentiment_analysis' in analysis:
                sentiment = analysis['sentiment_analysis']
                print(f"Sentiment: {sentiment.get('summary', 'N/A')}")
            
            if 'decision_analysis' in analysis:
                decisions = analysis['decision_analysis']
                print(f"Decisions: {decisions.get('summary', 'N/A')}")
            
            if 'communication_analysis' in analysis:
                comm = analysis['communication_analysis']
                print(f"Communication: {comm.get('summary', 'N/A')}")
            
            if 'effectiveness_analysis' in analysis:
                effectiveness = analysis['effectiveness_analysis']
                print(f"Effectiveness: {effectiveness.get('summary', 'N/A')}")
            
            # Check summary data
            summary = result.get('summary', {})
            print("\n--- Summary Data ---")
            print(f"Action Items: {len(summary.get('action_items', []))}")
            print(f"Key Points: {len(summary.get('key_points', []))}")
            print(f"Participants: {summary.get('participants', [])}")
            print(f"Duration Estimate: {summary.get('meeting_duration_estimate', {}).get('formatted', 'N/A')}")
            
            # Show some action items
            action_items = summary.get('action_items', [])
            if action_items:
                print("\nAction Items Found:")
                for item in action_items[:3]:  # Show first 3
                    print(f"  - {item.get('assignee', 'Unknown')}: {item.get('task', 'N/A')}")
            
            # Show matched cards
            matched_cards = result.get('matched_cards', [])
            if matched_cards:
                print(f"\nMatched Trello Cards: {len(matched_cards)}")
                for card in matched_cards[:3]:  # Show first 3
                    print(f"  - {card.get('name', 'Unknown')} (confidence: {card.get('confidence', 0)}%)")
            
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Response text: {response.text if 'response' in locals() else 'No response'}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def test_google_docs_url():
    """Test Google Docs URL processing (will fail without valid doc)."""
    print("\n" + "="*50)
    print("Testing Google Docs URL processing...")
    
    url = "http://localhost:5000/api/process-transcript"
    data = {
        "url": "https://docs.google.com/document/d/1234567890/edit"  # Fake URL for testing
    }
    
    try:
        response = requests.post(url, json=data, timeout=30)
        result = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Success: {result.get('success', False)}")
        print(f"Message/Error: {result.get('error' if not result.get('success') else 'message', 'N/A')}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("="*50)
    print("TRANSCRIPT PROCESSING API TEST")
    print("="*50)
    
    test_direct_text_processing()
    test_google_docs_url()
    
    print("\n" + "="*50)
    print("Test completed!")