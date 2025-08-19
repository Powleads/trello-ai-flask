#!/usr/bin/env python3
"""
Meeting Structure Parser - Identifies James Taylor's card readings and extracts card-specific discussions
"""

import re
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher


class MeetingStructureParser:
    """Parser for structured meeting transcripts where James Taylor reads card names."""
    
    def __init__(self):
        self.james_patterns = [
            r'james\s+taylor',
            r'james',
            r'j\.?\s*taylor'
        ]
        
        # Keywords that indicate Trello section start
        self.trello_indicators = [
            'trello',
            'cards',
            'board',
            'tasks'
        ]
    
    def similarity(self, a: str, b: str) -> float:
        """Calculate similarity between two strings."""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    def extract_card_discussions(self, transcript: str, trello_cards: List[Dict]) -> Dict[str, Dict]:
        """
        Extract card-specific discussions from transcript.
        
        Args:
            transcript: Full meeting transcript
            trello_cards: List of Trello cards with 'name' field
            
        Returns:
            Dict mapping card names to their discussion content
        """
        card_discussions = {}
        
        # Parse transcript into segments
        segments = self._parse_transcript_segments(transcript)
        
        # Find Trello discussion section
        trello_section = self._find_trello_section(segments)
        if not trello_section:
            print("No Trello section found in transcript")
            return card_discussions
        
        # Extract card-specific discussions
        card_segments = self._extract_card_segments(trello_section, trello_cards)
        
        # Process each card segment
        for card_name, segment_data in card_segments.items():
            discussion_text = segment_data['discussion']
            speakers = segment_data['speakers']
            
            # Generate summary for this card
            card_discussions[card_name] = {
                'discussion': discussion_text,
                'speakers': speakers,
                'summary': self._summarize_card_discussion(discussion_text, card_name),
                'confidence': segment_data['confidence']
            }
        
        return card_discussions
    
    def _parse_transcript_segments(self, transcript: str) -> List[Dict]:
        """Parse transcript into speaker segments."""
        segments = []
        lines = transcript.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for speaker patterns: "Speaker Name:" or "Speaker Name -"
            speaker_match = re.match(r'^([A-Za-z][A-Za-z\s\'\.]+?)[\s]*[-:][\s]*(.+)$', line)
            
            if speaker_match:
                speaker_name = speaker_match.group(1).strip()
                spoken_text = speaker_match.group(2).strip()
                
                # Filter out common non-speaker patterns
                if speaker_name.lower() in ['meeting', 'call', 'video', 'audio', 'transcript', 'recording', 'summary']:
                    continue
                
                segments.append({
                    'speaker': speaker_name,
                    'text': spoken_text,
                    'full_line': line
                })
        
        return segments
    
    def _find_trello_section(self, segments: List[Dict]) -> Optional[List[Dict]]:
        """Find the section where James Taylor mentions Trello and starts reading cards."""
        trello_start_idx = None
        
        for i, segment in enumerate(segments):
            speaker = segment['speaker'].lower()
            text = segment['text'].lower()
            
            # Check if this is James Taylor mentioning Trello
            if any(pattern in speaker for pattern in ['james', 'taylor']):
                if any(indicator in text for indicator in self.trello_indicators):
                    trello_start_idx = i
                    print(f"Found Trello section start at segment {i}: {segment['speaker']} - {segment['text'][:100]}...")
                    break
        
        if trello_start_idx is None:
            return None
        
        # Return segments from Trello mention onwards
        return segments[trello_start_idx:]
    
    def _extract_card_segments(self, trello_section: List[Dict], trello_cards: List[Dict]) -> Dict[str, Dict]:
        """Extract segments for each card based on James Taylor's readings."""
        card_segments = {}
        card_names = [card['name'] for card in trello_cards]
        
        current_card = None
        current_discussion = []
        current_speakers = set()
        
        for segment in trello_section:
            speaker = segment['speaker']
            text = segment['text']
            
            # Check if James Taylor is reading a card name
            if any(pattern in speaker.lower() for pattern in ['james', 'taylor']):
                # Try to match this text to a card name
                best_match = self._find_best_card_match(text, card_names)
                
                if best_match:
                    # Save previous card discussion if exists
                    if current_card and current_discussion:
                        card_segments[current_card] = {
                            'discussion': '\n'.join(current_discussion),
                            'speakers': list(current_speakers),
                            'confidence': 85  # High confidence when James reads it
                        }
                    
                    # Start new card
                    current_card = best_match['card_name']
                    current_discussion = []
                    current_speakers = set()
                    
                    print(f"Found card reading: '{text}' -> '{current_card}' (confidence: {best_match['confidence']:.1f}%)")
                    continue
            
            # If we have a current card, add this discussion
            if current_card:
                current_discussion.append(f"{speaker}: {text}")
                current_speakers.add(speaker)
        
        # Save final card discussion
        if current_card and current_discussion:
            card_segments[current_card] = {
                'discussion': '\n'.join(current_discussion),
                'speakers': list(current_speakers),
                'confidence': 85
            }
        
        return card_segments
    
    def _find_best_card_match(self, text: str, card_names: List[str]) -> Optional[Dict]:
        """Find the best matching card name for the given text."""
        best_match = None
        best_score = 0.0
        
        for card_name in card_names:
            # Try exact match first
            if card_name.lower() in text.lower() or text.lower() in card_name.lower():
                score = self.similarity(text, card_name)
                if score > 0.6:  # Reasonable threshold
                    if score > best_score:
                        best_match = {
                            'card_name': card_name,
                            'confidence': score * 100,
                            'match_type': 'similarity'
                        }
                        best_score = score
            
            # Also try keyword matching for longer card names
            card_keywords = [word for word in card_name.lower().split() if len(word) > 3]
            text_words = text.lower().split()
            
            keyword_matches = sum(1 for keyword in card_keywords if any(keyword in word for word in text_words))
            
            if keyword_matches > 0 and len(card_keywords) > 0:
                keyword_score = keyword_matches / len(card_keywords)
                if keyword_score > 0.5 and keyword_score > best_score:
                    best_match = {
                        'card_name': card_name,
                        'confidence': keyword_score * 80,  # Slightly lower confidence for keyword matching
                        'match_type': 'keywords'
                    }
                    best_score = keyword_score
        
        return best_match if best_score > 0.3 else None
    
    def _summarize_card_discussion(self, discussion_text: str, card_name: str) -> str:
        """Create a focused summary of the card-specific discussion."""
        if not discussion_text.strip():
            return "No specific discussion found for this card."
        
        lines = discussion_text.split('\n')
        if len(lines) <= 2:
            return discussion_text
        
        # Extract key points from the discussion
        key_points = []
        action_items = []
        
        for line in lines:
            line_lower = line.lower()
            
            # Look for action items
            if any(phrase in line_lower for phrase in ['will', 'going to', 'need to', 'should', 'must', 'action']):
                action_items.append(line)
            
            # Look for important statements
            elif any(phrase in line_lower for phrase in ['important', 'key', 'main', 'primary', 'critical']):
                key_points.append(line)
            
            # Look for decisions
            elif any(phrase in line_lower for phrase in ['decide', 'agreed', 'conclusion', 'result']):
                key_points.append(line)
        
        summary_parts = []
        
        if key_points:
            summary_parts.append("**Key Discussion Points:**")
            for point in key_points[:3]:  # Top 3 points
                summary_parts.append(f"• {point}")
        
        if action_items:
            summary_parts.append("\n**Action Items Mentioned:**")
            for action in action_items[:3]:  # Top 3 actions
                summary_parts.append(f"• {action}")
        
        if not summary_parts:
            # Fallback: use first few meaningful lines
            meaningful_lines = [line for line in lines if len(line.strip()) > 20][:3]
            return '\n'.join(meaningful_lines) if meaningful_lines else discussion_text
        
        return '\n'.join(summary_parts)


def test_meeting_parser():
    """Test the meeting parser with sample data."""
    parser = MeetingStructureParser()
    
    sample_transcript = """
James Taylor: Alright, let's go through our Trello board now
James Taylor: Organize all court documents and evidence against case
Wendy Ndikum: I've been working on organizing the files, but I need more time to sort through everything
Paige Salinas: I can help with that if needed
James Taylor: Fix the website login issue
Mike Johnson: The login issue is resolved, we pushed the fix yesterday
James Taylor: Update team calendar with new meeting times
Sarah Wilson: I'll handle the calendar updates this week
"""
    
    sample_cards = [
        {'name': 'Organize all court documents and evidence against case'},
        {'name': 'Fix the website login issue'},
        {'name': 'Update team calendar with new meeting times'}
    ]
    
    result = parser.extract_card_discussions(sample_transcript, sample_cards)
    
    print("=== Meeting Parser Test Results ===")
    for card_name, data in result.items():
        print(f"\nCard: {card_name}")
        print(f"Speakers: {', '.join(data['speakers'])}")
        print(f"Discussion:\n{data['discussion']}")
        print(f"Summary:\n{data['summary']}")
        print(f"Confidence: {data['confidence']}%")
        print("-" * 50)


if __name__ == "__main__":
    test_meeting_parser()