#!/usr/bin/env python3
"""
Test the fixed web API
"""

import requests
import time

def test_fixed_api():
    """Test the fixed API with optimized processing."""
    
    sample_transcript = """Sarah Chen: Good morning everyone! Let's discuss the Mobile App progress.

Mike Johnson: The Mobile App is going well. We've completed the UI mockups and the backend API is about 70% done.

Emily Rodriguez: Great! What about the SEO project? I know it's been blocked.

David Kim: I can help unblock the SEO work. Let me get you the credentials you need.

Lisa Thompson: Perfect! I also wanted to update everyone on the Support Ticket System Revival. It's complete as of yesterday.

Sarah Chen: Excellent work! David, how's the EE System Universal Scheduler coming along?

David Kim: The EE System Universal Scheduler is also complete! We launched it and have 15 centers using it.

Mike Johnson: That's fantastic! What about the task to reach out to onboarded centers to show leads?

Emily Rodriguez: I can take that task. It aligns well with the marketing work I'm doing."""
    
    print("Testing Fixed Web API")
    print("=" * 40)
    
    url = "http://localhost:5001/api/process-transcript"
    data = {"direct_text": sample_transcript}
    
    print(f"Sending request to: {url}")
    print(f"Transcript length: {len(sample_transcript)} characters")
    print("Expected matches: Mobile App, SEO, Support Ticket System Revival, EE System Universal Scheduler")
    print()
    
    try:
        start_time = time.time()
        response = requests.post(url, json=data, timeout=30)
        end_time = time.time()
        
        print(f"Request completed in {end_time - start_time:.2f} seconds")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                print("\n[SUCCESS] Transcript processed successfully!")
                
                print(f"Processing time: {result.get('processing_time', 'N/A'):.2f}s")
                print(f"Word count: {result.get('word_count', 'N/A')}")
                print(f"Cards found: {result.get('cards_found', 0)}")
                
                # Print matched cards
                matched_cards = result.get('matched_cards', [])
                if matched_cards:
                    print(f"\n[MATCHES] Found {len(matched_cards)} card matches:")
                    for i, card in enumerate(matched_cards, 1):
                        name = card.get('name', 'Unknown')
                        confidence = card.get('confidence', 0)
                        match_type = card.get('match_type', 'unknown')
                        print(f"  {i}. {name} ({confidence}% confidence)")
                    
                    # Validate expected matches
                    expected = ['mobile app', 'seo', 'support ticket system', 'scheduler', 'reach out']
                    found_expected = []
                    
                    for card in matched_cards:
                        card_name_lower = card.get('name', '').lower()
                        for expected_name in expected:
                            if expected_name in card_name_lower:
                                found_expected.append(expected_name)
                                break
                    
                    print(f"\n[VALIDATION] Found {len(found_expected)} expected matches:")
                    for exp in found_expected:
                        print(f"  - {exp}")
                
                else:
                    print("\n[WARNING] No card matches found!")
                
                # Print analysis results
                analysis = result.get('analysis_results', {})
                if analysis:
                    print(f"\n[ANALYSIS] AI Analysis completed:")
                    
                    speaker_analysis = analysis.get('speaker_analysis', {})
                    if speaker_analysis and speaker_analysis.get('success'):
                        speakers = speaker_analysis.get('speakers', {})
                        print(f"  - Speakers: {len(speakers)} detected")
                    
                    sentiment = analysis.get('sentiment_analysis', {})
                    if sentiment:
                        print(f"  - Sentiment: {sentiment.get('summary', 'N/A')}")
                
                # Print summary
                summary = result.get('summary', {})
                if summary:
                    participants = summary.get('participants', [])
                    action_items = summary.get('action_items', [])
                    print(f"\n[SUMMARY]")
                    print(f"  - Participants: {len(participants)} ({', '.join(participants)})")
                    print(f"  - Action items: {len(action_items)}")
                    if action_items:
                        for item in action_items[:3]:
                            print(f"    * {item.get('assignee', 'Unknown')}: {item.get('task', 'N/A')}")
                
                return True
                
            else:
                print(f"\n[ERROR] Processing failed: {result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"\n[ERROR] HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n[ERROR] Request timed out")
        return False
    except Exception as e:
        print(f"\n[ERROR] Request failed: {e}")
        return False

def main():
    """Run the fixed API test."""
    success = test_fixed_api()
    
    if success:
        print("\n" + "=" * 40)
        print("[RESULT] Fixed web API is working!")
        print("The optimized transcript processing is functional.")
    else:
        print("\n" + "=" * 40)
        print("[RESULT] Fixed API still has issues")
    
    return success

if __name__ == "__main__":
    main()