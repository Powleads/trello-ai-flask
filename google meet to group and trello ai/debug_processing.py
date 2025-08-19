#!/usr/bin/env python3
"""
Debug the transcript processing step by step
"""

import os
import sys
import time
from datetime import datetime

sys.path.insert(0, 'src')

# Test imports
print("Testing imports...")

try:
    from custom_trello import CustomTrelloClient
    print("✓ Custom Trello client imported")
except Exception as e:
    print(f"✗ Custom Trello import failed: {e}")

try:
    from enhanced_ai import EnhancedAI
    print("✓ Enhanced AI imported")
except Exception as e:
    print(f"✗ Enhanced AI import failed: {e}")

try:
    from speaker_analysis import SpeakerAnalyzer
    print("✓ Speaker Analysis imported")
except Exception as e:
    print(f"✗ Speaker Analysis import failed: {e}")

# Test simple transcript processing
print("\n" + "="*50)
print("Testing basic transcript processing...")

sample_transcript = """Sarah Chen: Good morning everyone! Let's discuss the Mobile App progress.

Mike Johnson: The Mobile App is going well. We've completed the UI mockups.

Emily Rodriguez: Great! What about the SEO project?

David Kim: I can help with the SEO work."""

print(f"Sample transcript length: {len(sample_transcript)}")

# Test speaker extraction
print("\nTesting speaker extraction...")
import re
speaker_pattern = r'^([A-Za-z][A-Za-z\s]+?):\s*(.+)$'
lines = sample_transcript.split('\n')
speakers = []

for line in lines:
    line = line.strip()
    if not line:
        continue
    match = re.match(speaker_pattern, line)
    if match:
        speaker = match.group(1).strip()
        if speaker not in speakers:
            speakers.append(speaker)

print(f"✓ Found {len(speakers)} speakers: {', '.join(speakers)}")

# Test Trello connection
print("\nTesting Trello connection...")
try:
    client = CustomTrelloClient()
    boards = client.list_boards()
    
    eeinteractive = None
    for board in boards:
        if 'eeinteractive' in board.name.lower():
            eeinteractive = board
            break
    
    if eeinteractive:
        print(f"✓ Found EEInteractive board: {eeinteractive.name}")
        
        # Get a few cards for testing
        cards = eeinteractive.list_cards()
        print(f"✓ Found {len(cards)} cards")
        
        # Test card matching
        print("\nTesting card matching...")
        matches = []
        transcript_lower = sample_transcript.lower()
        
        for card in cards[:10]:  # Test first 10 cards
            confidence = 0
            card_name_lower = card.name.lower()
            
            # Check for direct mentions
            if 'mobile' in card_name_lower and 'mobile' in transcript_lower:
                confidence += 80
                print(f"  Found potential match: {card.name} (mobile)")
            
            if 'seo' in card_name_lower and 'seo' in transcript_lower:
                confidence += 80  
                print(f"  Found potential match: {card.name} (seo)")
            
            if confidence >= 50:
                matches.append({
                    'name': card.name,
                    'confidence': confidence
                })
        
        print(f"✓ Basic matching found {len(matches)} matches")
        for match in matches:
            print(f"  - {match['name']}: {match['confidence']}%")
        
    else:
        print("✗ EEInteractive board not found")
        
except Exception as e:
    print(f"✗ Trello test failed: {e}")

# Test Enhanced AI with timeout
print("\nTesting Enhanced AI with timeout...")
try:
    start_time = time.time()
    ai_engine = EnhancedAI()
    
    # Test sentiment analysis with timeout
    print("Testing sentiment analysis...")
    sentiment_start = time.time()
    sentiment_result = ai_engine.analyze_meeting_sentiment(sample_transcript)
    sentiment_time = time.time() - sentiment_start
    print(f"✓ Sentiment analysis completed in {sentiment_time:.2f}s: {sentiment_result.summary}")
    
    # Test card matching with timeout  
    print("Testing AI card matching...")
    test_cards = [
        {'id': '1', 'name': 'Mobile App', 'description': 'Mobile development', 'url': 'test1'},
        {'id': '2', 'name': 'SEO', 'description': 'Search optimization', 'url': 'test2'}
    ]
    
    matching_start = time.time()
    card_matches = ai_engine.match_trello_cards_intelligent(sample_transcript, test_cards)
    matching_time = time.time() - matching_start
    print(f"✓ Card matching completed in {matching_time:.2f}s: found {len(card_matches)} matches")
    
    for match in card_matches:
        print(f"  - {match.get('name', 'Unknown')}: {match.get('confidence', 0)}%")
    
    total_time = time.time() - start_time
    print(f"✓ Total Enhanced AI test time: {total_time:.2f}s")
    
except Exception as e:
    print(f"✗ Enhanced AI test failed: {e}")

# Test Speaker Analysis
print("\nTesting Speaker Analysis...")
try:
    start_time = time.time()
    analyzer = SpeakerAnalyzer()
    result = analyzer.analyze_transcript(sample_transcript)
    analysis_time = time.time() - start_time
    
    if result.get('success'):
        speakers = result.get('speakers', {})
        print(f"✓ Speaker analysis completed in {analysis_time:.2f}s: {len(speakers)} speakers")
        for speaker, data in speakers.items():
            print(f"  - {speaker}: {data.get('word_count', 0)} words")
    else:
        print(f"✗ Speaker analysis failed: {result.get('error', 'Unknown error')}")
        
except Exception as e:
    print(f"✗ Speaker analysis test failed: {e}")

print("\n" + "="*50)
print("Debug test completed!")
print("If all tests pass quickly, the issue might be in the web app processing logic.")