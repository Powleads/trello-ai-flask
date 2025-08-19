#!/usr/bin/env python3
"""
Enhanced AI Module - Fixed version with better error handling
Handles OpenAI quota issues gracefully and fails fast to fallback methods
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from openai import OpenAI
from dotenv import load_dotenv
import time

load_dotenv()

class AIProvider(Enum):
    """Supported AI providers."""
    OPENAI = "openai"
    CLAUDE = "claude"
    LOCAL = "local"

@dataclass
class AnalysisResult:
    """Structured result from AI analysis."""
    confidence: float
    summary: str
    insights: List[str]
    metadata: Dict[str, Any]
    processing_time: float

class EnhancedAI:
    """Enhanced AI module with better error handling for quota issues."""
    
    def __init__(self, preferred_provider: AIProvider = AIProvider.OPENAI):
        self.preferred_provider = preferred_provider
        self.openai_client = None
        self.openai_available = False
        self.setup_providers()
    
    def setup_providers(self):
        """Initialize AI providers with quota check."""
        # Setup OpenAI with quick availability test
        if os.environ.get('OPENAI_API_KEY'):
            try:
                self.openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
                
                # Quick test to check quota
                test_response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1,
                    timeout=5.0
                )
                self.openai_available = True
                print("OpenAI client initialized and available")
            except Exception as e:
                self.openai_available = False
                print(f"OpenAI not available: {e}")
        else:
            print("Warning: OPENAI_API_KEY not found")
    
    def _safe_openai_call(self, messages, max_tokens=1000, timeout=10.0):
        """Make a safe OpenAI API call with timeout and error handling."""
        if not self.openai_available or not self.openai_client:
            return None
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use cheaper model to conserve quota
                messages=messages,
                temperature=0.3,
                max_tokens=max_tokens,
                timeout=timeout
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API call failed: {e}")
            # Mark as unavailable if quota exceeded
            if "quota" in str(e).lower() or "429" in str(e):
                self.openai_available = False
            return None
    
    def analyze_meeting_sentiment(self, transcript: str) -> AnalysisResult:
        """Analyze overall meeting sentiment and mood."""
        start_time = datetime.now()
        
        if self.openai_available:
            prompt = f"""Analyze sentiment of this meeting (1-10 scale, JSON format):
            
{transcript[:1000]}  # Truncate for quota conservation

Respond: {{"sentiment_score": 7, "mood": "positive", "energy": "medium"}}"""
            
            response = self._safe_openai_call([{"role": "user", "content": prompt}], max_tokens=200, timeout=8.0)
            
            if response:
                try:
                    analysis_data = json.loads(response)
                    processing_time = (datetime.now() - start_time).total_seconds()
                    
                    return AnalysisResult(
                        confidence=0.85,
                        summary=f"Meeting sentiment: {analysis_data.get('sentiment_score', 'N/A')}/10",
                        insights=[
                            f"Sentiment score: {analysis_data.get('sentiment_score', 'N/A')}/10",
                            f"Mood: {analysis_data.get('mood', 'neutral')}",
                            f"Energy level: {analysis_data.get('energy', 'medium')}"
                        ],
                        metadata=analysis_data,
                        processing_time=processing_time
                    )
                except json.JSONDecodeError:
                    pass
        
        # Fallback to simple analysis
        return self._fallback_sentiment_analysis(transcript, start_time)
    
    def analyze_decision_points(self, transcript: str) -> AnalysisResult:
        """Identify and analyze decision points in the meeting."""
        start_time = datetime.now()
        
        if self.openai_available:
            prompt = f"""Extract decisions from meeting (JSON format):

{transcript[:800]}

Respond: {{"decisions_made": ["decision 1"], "pending": ["pending 1"]}}"""
            
            response = self._safe_openai_call([{"role": "user", "content": prompt}], max_tokens=300, timeout=8.0)
            
            if response:
                try:
                    analysis_data = json.loads(response)
                    processing_time = (datetime.now() - start_time).total_seconds()
                    
                    decisions_made = analysis_data.get('decisions_made', [])
                    pending_decisions = analysis_data.get('pending', [])
                    
                    return AnalysisResult(
                        confidence=0.80,
                        summary=f"Found {len(decisions_made)} decisions made, {len(pending_decisions)} pending",
                        insights=[
                            f"Decisions completed: {len(decisions_made)}",
                            f"Decisions pending: {len(pending_decisions)}"
                        ],
                        metadata=analysis_data,
                        processing_time=processing_time
                    )
                except json.JSONDecodeError:
                    pass
        
        return self._fallback_decision_analysis(transcript, start_time)
    
    def analyze_communication_patterns(self, transcript: str) -> AnalysisResult:
        """Analyze communication patterns and team dynamics."""
        start_time = datetime.now()
        
        # Extract speakers and their contributions
        speaker_pattern = r'^([A-Za-z][A-Za-z\s]+?):\s*(.+)$'
        lines = transcript.split('\n')
        
        speakers = {}
        questions_asked = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            match = re.match(speaker_pattern, line)
            if match:
                speaker = match.group(1).strip()
                content = match.group(2).strip()
                
                if speaker not in speakers:
                    speakers[speaker] = {
                        'total_words': 0,
                        'turns': 0,
                        'questions': 0
                    }
                
                speakers[speaker]['total_words'] += len(content.split())
                speakers[speaker]['turns'] += 1
                
                # Count questions
                if '?' in content:
                    speakers[speaker]['questions'] += 1
                    questions_asked += 1
        
        # Calculate communication metrics
        total_words = sum(data['total_words'] for data in speakers.values())
        
        communication_data = {
            'speakers_analysis': {},
            'overall_metrics': {
                'total_speakers': len(speakers),
                'total_words': total_words,
                'questions_asked': questions_asked,
                'average_words_per_speaker': total_words / len(speakers) if speakers else 0
            }
        }
        
        # Analyze each speaker
        for speaker, data in speakers.items():
            communication_data['speakers_analysis'][speaker] = {
                'word_percentage': (data['total_words'] / total_words * 100) if total_words > 0 else 0,
                'speaking_turns': data['turns'],
                'questions_asked': data['questions'],
                'engagement_level': self._calculate_engagement_level(data, total_words)
            }
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return AnalysisResult(
            confidence=0.85,
            summary=f"Communication analysis: {len(speakers)} speakers, {questions_asked} questions",
            insights=[
                f"Total speakers: {len(speakers)}",
                f"Questions asked: {questions_asked}",
                f"Most active: {max(speakers.keys(), key=lambda x: speakers[x]['total_words']) if speakers else 'N/A'}"
            ],
            metadata=communication_data,
            processing_time=processing_time
        )
    
    def analyze_meeting_effectiveness(self, transcript: str, duration_minutes: int = None) -> AnalysisResult:
        """Analyze meeting effectiveness and provide improvement suggestions."""
        start_time = datetime.now()
        
        if self.openai_available:
            prompt = f"""Rate meeting effectiveness (1-10, JSON format):

{transcript[:600]}

Respond: {{"effectiveness": 7, "time_management": "good", "suggestions": ["suggestion 1"]}}"""
            
            response = self._safe_openai_call([{"role": "user", "content": prompt}], max_tokens=200, timeout=8.0)
            
            if response:
                try:
                    analysis_data = json.loads(response)
                    processing_time = (datetime.now() - start_time).total_seconds()
                    
                    overall_score = analysis_data.get('effectiveness', 7.0)
                    
                    return AnalysisResult(
                        confidence=0.75,
                        summary=f"Meeting effectiveness: {overall_score}/10",
                        insights=[
                            f"Overall effectiveness: {overall_score}/10",
                            f"Time management: {analysis_data.get('time_management', 'Good')}"
                        ],
                        metadata=analysis_data,
                        processing_time=processing_time
                    )
                except json.JSONDecodeError:
                    pass
        
        return self._fallback_effectiveness_analysis(transcript, start_time)
    
    def match_trello_cards_intelligent(self, transcript: str, card_data: List[Dict]) -> List[Dict]:
        """Use AI to intelligently match Trello cards mentioned in transcript."""
        if not self.openai_available or not self.openai_client or not card_data:
            print("AI matching not available, using fallback")
            return self._fallback_card_matching(transcript, card_data)
        
        # Prepare simplified card information
        card_info = []
        for card in card_data[:10]:  # Limit to 10 cards to save tokens
            card_info.append({
                'id': card.get('id'),
                'name': card.get('name', '')[:100],  # Truncate long names
                'description': card.get('description', '')[:150]  # Truncate descriptions
            })
        
        prompt = f"""Match meeting content with Trello cards (JSON format):

Meeting: {transcript[:800]}  # Truncate for quota

Cards: {json.dumps(card_info)}

Find relevant matches, respond: [{{"card_id": "id", "card_name": "name", "match_confidence": 85, "context": "quote"}}]"""
        
        response = self._safe_openai_call([{"role": "user", "content": prompt}], max_tokens=800, timeout=15.0)
        
        if response:
            try:
                # Clean response
                if response.strip().startswith('```json'):
                    content = response.strip()
                    start = content.find('```json') + 7
                    end = content.rfind('```')
                    if end > start:
                        response = content[start:end].strip()
                
                matches = json.loads(response)
                if isinstance(matches, list):
                    # Add compatibility fields
                    for match in matches:
                        original_card = next((c for c in card_data if c.get('id') == match.get('card_id')), {})
                        
                        match.update({
                            'id': match.get('card_id'),
                            'name': match.get('card_name', original_card.get('name', 'Unknown')),
                            'url': original_card.get('url', ''),
                            'confidence': match.get('match_confidence', 0),
                            'description': original_card.get('description', '')[:200]
                        })
                    
                    return sorted(matches, key=lambda x: x.get('match_confidence', 0), reverse=True)
            except json.JSONDecodeError as e:
                print(f"Failed to parse AI response: {e}")
        
        # Fallback to basic matching
        return self._fallback_card_matching(transcript, card_data)
    
    def _fallback_card_matching(self, transcript: str, card_data: List[Dict]) -> List[Dict]:
        """Fallback card matching using keyword analysis."""
        matches = []
        transcript_lower = transcript.lower()
        
        for card in card_data:
            confidence = 0
            card_name_lower = card.get('name', '').lower()
            
            # Direct name matching
            if card_name_lower in transcript_lower:
                confidence += 80
            
            # Word-by-word matching
            card_words = card_name_lower.split()
            for word in card_words:
                if len(word) > 3 and word in transcript_lower:
                    confidence += 15
            
            # Description matching (if available)
            description = card.get('description', '').lower()
            if description:
                desc_words = description.split()[:10]  # First 10 words
                for word in desc_words:
                    if len(word) > 4 and word in transcript_lower:
                        confidence += 5
            
            if confidence >= 30:  # Threshold for relevance
                matches.append({
                    'id': card.get('id'),
                    'name': card.get('name', 'Unknown'),
                    'url': card.get('url', ''),
                    'confidence': min(100, confidence),
                    'description': card.get('description', '')[:200],
                    'match_type': 'keyword_fallback'
                })
        
        return sorted(matches, key=lambda x: x['confidence'], reverse=True)[:10]
    
    def _calculate_engagement_level(self, speaker_data: Dict, total_words: int) -> str:
        """Calculate engagement level for a speaker."""
        word_percentage = (speaker_data['total_words'] / total_words * 100) if total_words > 0 else 0
        questions = speaker_data['questions']
        turns = speaker_data['turns']
        
        score = 0
        if word_percentage > 30:
            score += 3
        elif word_percentage > 15:
            score += 2
        elif word_percentage > 5:
            score += 1
        
        if questions > 2:
            score += 2
        elif questions > 0:
            score += 1
        
        if turns > 5:
            score += 2
        elif turns > 2:
            score += 1
        
        if score >= 6:
            return "high"
        elif score >= 3:
            return "medium"
        else:
            return "low"
    
    # Fallback methods for when AI APIs are not available
    
    def _fallback_sentiment_analysis(self, transcript: str, start_time: datetime) -> AnalysisResult:
        """Fallback sentiment analysis using keyword matching."""
        positive_words = ['great', 'excellent', 'good', 'perfect', 'amazing', 'wonderful', 'fantastic']
        negative_words = ['problem', 'issue', 'blocked', 'stuck', 'difficult', 'frustrated', 'concerned']
        
        text_lower = transcript.lower()
        positive_count = sum(text_lower.count(word) for word in positive_words)
        negative_count = sum(text_lower.count(word) for word in negative_words)
        
        total_sentiment_words = positive_count + negative_count
        if total_sentiment_words > 0:
            sentiment_score = ((positive_count - negative_count) / total_sentiment_words + 1) * 5
        else:
            sentiment_score = 5.0  # Neutral
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return AnalysisResult(
            confidence=0.60,
            summary=f"Sentiment analysis (fallback): {sentiment_score:.1f}/10",
            insights=[
                f"Positive indicators: {positive_count}",
                f"Negative indicators: {negative_count}",
                f"Overall tone: {'positive' if sentiment_score > 6 else 'negative' if sentiment_score < 4 else 'neutral'}"
            ],
            metadata={
                'sentiment_score': sentiment_score,
                'positive_count': positive_count,
                'negative_count': negative_count,
                'method': 'keyword_fallback'
            },
            processing_time=processing_time
        )
    
    def _fallback_decision_analysis(self, transcript: str, start_time: datetime) -> AnalysisResult:
        """Fallback decision analysis using pattern matching."""
        decision_patterns = [
            r'we decided to (.+)',
            r'decision is (.+)',
            r'agreed to (.+)',
            r'will go with (.+)'
        ]
        
        pending_patterns = [
            r'need to decide (.+)',
            r'should we (.+)\?',
            r'what about (.+)\?',
            r'pending decision on (.+)'
        ]
        
        decisions = []
        pending = []
        
        for pattern in decision_patterns:
            matches = re.findall(pattern, transcript, re.IGNORECASE)
            decisions.extend(matches)
        
        for pattern in pending_patterns:
            matches = re.findall(pattern, transcript, re.IGNORECASE)
            pending.extend(matches)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return AnalysisResult(
            confidence=0.50,
            summary=f"Decision analysis (fallback): {len(decisions)} made, {len(pending)} pending",
            insights=[
                f"Decisions made: {len(decisions)}",
                f"Pending decisions: {len(pending)}",
                f"Decision clarity: {'good' if len(decisions) > 0 else 'needs improvement'}"
            ],
            metadata={
                'decisions_made': decisions[:5],
                'pending_decisions': pending[:5],
                'method': 'pattern_fallback'
            },
            processing_time=processing_time
        )
    
    def _fallback_effectiveness_analysis(self, transcript: str, start_time: datetime) -> AnalysisResult:
        """Fallback effectiveness analysis."""
        words = transcript.split()
        questions = transcript.count('?')
        action_words = ['will', 'should', 'need to', 'must', 'action', 'next']
        action_count = sum(transcript.lower().count(word) for word in action_words)
        
        effectiveness_score = 5.0  # Base score
        
        if questions > 2:
            effectiveness_score += 1
        if action_count > 5:
            effectiveness_score += 1
        if len(words) > 200:
            effectiveness_score += 0.5
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return AnalysisResult(
            confidence=0.45,
            summary=f"Effectiveness analysis (fallback): {effectiveness_score}/10",
            insights=[
                f"Questions asked: {questions}",
                f"Action-oriented content: {action_count} instances",
                f"Content length: {len(words)} words"
            ],
            metadata={
                'overall_effectiveness': effectiveness_score,
                'questions_count': questions,
                'action_words_count': action_count,
                'word_count': len(words),
                'method': 'basic_fallback'
            },
            processing_time=processing_time
        )

def test_enhanced_ai_fixed():
    """Test the fixed enhanced AI module."""
    print("Testing Enhanced AI (Fixed Version)...")
    
    ai = EnhancedAI()
    
    sample_transcript = """
    Sarah Chen: Good morning everyone! Let's discuss the Mobile App progress.
    
    Mike Johnson: The Mobile App is going well. We've completed the UI mockups and the backend API is about 70% done.
    
    Emily Rodriguez: Great! What about the SEO project? I know it's been blocked.
    
    David Kim: I can help unblock the SEO work. Let me get you the credentials you need.
    """
    
    # Test all functions with timeout protection
    print("\n--- Testing Sentiment Analysis ---")
    start_time = time.time()
    sentiment_result = ai.analyze_meeting_sentiment(sample_transcript)
    print(f"Time: {time.time() - start_time:.2f}s")
    print(f"Summary: {sentiment_result.summary}")
    print(f"Confidence: {sentiment_result.confidence}")
    
    print("\n--- Testing Communication Patterns ---")
    start_time = time.time()
    comm_result = ai.analyze_communication_patterns(sample_transcript)
    print(f"Time: {time.time() - start_time:.2f}s")
    print(f"Summary: {comm_result.summary}")
    
    # Test card matching
    print("\n--- Testing Card Matching ---")
    start_time = time.time()
    test_cards = [
        {'id': '1', 'name': 'Mobile App', 'description': 'Mobile application development', 'url': 'test1'},
        {'id': '2', 'name': 'SEO', 'description': 'Search engine optimization', 'url': 'test2'},
        {'id': '3', 'name': 'WordPress Site', 'description': 'Website development', 'url': 'test3'}
    ]
    
    matches = ai.match_trello_cards_intelligent(sample_transcript, test_cards)
    print(f"Time: {time.time() - start_time:.2f}s")
    print(f"Found {len(matches)} matches:")
    for match in matches:
        print(f"  - {match.get('name', 'Unknown')}: {match.get('confidence', 0)}% confidence")
    
    print("\nFixed Enhanced AI test completed!")

if __name__ == "__main__":
    test_enhanced_ai_fixed()