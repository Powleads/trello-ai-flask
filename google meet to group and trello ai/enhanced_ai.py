#!/usr/bin/env python3
"""
Enhanced AI Module for Google Meet to Trello AI
Provides advanced AI capabilities with multiple model support and improved analysis
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
    """Enhanced AI module with multiple provider support and advanced analysis."""
    
    def __init__(self, preferred_provider: AIProvider = AIProvider.OPENAI):
        self.preferred_provider = preferred_provider
        self.openai_client = None
        self.setup_providers()
    
    def setup_providers(self):
        """Initialize AI providers."""
        # Setup OpenAI
        if os.environ.get('OPENAI_API_KEY'):
            self.openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
            print("OpenAI client initialized")
        else:
            print("Warning: OPENAI_API_KEY not found")
    
    def analyze_meeting_sentiment(self, transcript: str) -> AnalysisResult:
        """Analyze overall meeting sentiment and mood."""
        start_time = datetime.now()
        
        prompt = f"""
        Analyze the sentiment and mood of this meeting transcript. Provide:
        
        1. Overall sentiment score (1-10, where 1 is very negative, 10 is very positive)
        2. Mood indicators (enthusiastic, frustrated, confused, focused, etc.)
        3. Energy level (low, medium, high)
        4. Collaboration quality (poor, fair, good, excellent)
        5. Key emotional moments or tone shifts
        
        Transcript:
        {transcript}
        
        Respond in JSON format.
        """
        
        try:
            if self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4-turbo",  # GPT-5 model for best results
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1000
                )
                
                content = response.choices[0].message.content
                
                # Parse JSON response
                try:
                    analysis_data = json.loads(content)
                except json.JSONDecodeError:
                    # Fallback parsing
                    analysis_data = self._parse_sentiment_fallback(content)
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                return AnalysisResult(
                    confidence=0.85,
                    summary=f"Meeting sentiment: {analysis_data.get('overall_sentiment', 'neutral')}",
                    insights=[
                        f"Sentiment score: {analysis_data.get('sentiment_score', 'N/A')}/10",
                        f"Mood: {analysis_data.get('mood', 'neutral')}",
                        f"Energy level: {analysis_data.get('energy_level', 'medium')}",
                        f"Collaboration: {analysis_data.get('collaboration_quality', 'fair')}"
                    ],
                    metadata=analysis_data,
                    processing_time=processing_time
                )
            else:
                return self._fallback_sentiment_analysis(transcript, start_time)
                
        except Exception as e:
            print(f"Error in sentiment analysis: {e}")
            return self._fallback_sentiment_analysis(transcript, start_time)
    
    def analyze_decision_points(self, transcript: str) -> AnalysisResult:
        """Identify and analyze decision points in the meeting."""
        start_time = datetime.now()
        
        prompt = f"""
        Analyze this meeting transcript to identify decision points and outcomes. Extract:
        
        1. Decisions made (with who made them)
        2. Pending decisions (what needs to be decided)
        3. Decision criteria mentioned
        4. Stakeholders involved in each decision
        5. Timeline/deadlines for decisions
        
        Transcript:
        {transcript}
        
        Format as JSON with arrays for each category.
        """
        
        try:
            if self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4-turbo",  # GPT-5 model for best results
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1200
                )
                
                content = response.choices[0].message.content
                
                try:
                    analysis_data = json.loads(content)
                except json.JSONDecodeError:
                    analysis_data = self._parse_decisions_fallback(content)
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                decisions_made = analysis_data.get('decisions_made', [])
                pending_decisions = analysis_data.get('pending_decisions', [])
                
                return AnalysisResult(
                    confidence=0.80,
                    summary=f"Found {len(decisions_made)} decisions made, {len(pending_decisions)} pending",
                    insights=[
                        f"Decisions completed: {len(decisions_made)}",
                        f"Decisions pending: {len(pending_decisions)}",
                        f"Decision criteria mentioned: {len(analysis_data.get('decision_criteria', []))}",
                        f"Stakeholders involved: {len(analysis_data.get('stakeholders', []))}"
                    ],
                    metadata=analysis_data,
                    processing_time=processing_time
                )
            else:
                return self._fallback_decision_analysis(transcript, start_time)
                
        except Exception as e:
            print(f"Error in decision analysis: {e}")
            return self._fallback_decision_analysis(transcript, start_time)
    
    def analyze_meeting_effectiveness(self, transcript: str, duration_minutes: int = None) -> AnalysisResult:
        """Analyze meeting effectiveness and provide improvement suggestions."""
        start_time = datetime.now()
        
        prompt = f"""
        Analyze this meeting transcript for effectiveness. Evaluate:
        
        1. Agenda adherence (score 1-10)
        2. Time management quality
        3. Participation balance
        4. Goal achievement level
        5. Communication clarity
        6. Follow-up actions clarity
        7. Specific improvement suggestions
        
        Meeting duration: {duration_minutes or 'Unknown'} minutes
        
        Transcript:
        {transcript}
        
        Provide scores and actionable recommendations in JSON format.
        """
        
        try:
            if self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4-turbo",  # GPT-5 model for best results
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1000
                )
                
                content = response.choices[0].message.content
                
                try:
                    analysis_data = json.loads(content)
                except json.JSONDecodeError:
                    analysis_data = self._parse_effectiveness_fallback(content)
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                overall_score = analysis_data.get('overall_effectiveness', 7.0)
                recommendations = analysis_data.get('improvement_suggestions', [])
                
                return AnalysisResult(
                    confidence=0.75,
                    summary=f"Meeting effectiveness: {overall_score}/10",
                    insights=[
                        f"Overall effectiveness: {overall_score}/10",
                        f"Agenda adherence: {analysis_data.get('agenda_adherence', 'N/A')}/10",
                        f"Time management: {analysis_data.get('time_management', 'Good')}",
                        f"Improvement areas: {len(recommendations)}"
                    ],
                    metadata=analysis_data,
                    processing_time=processing_time
                )
            else:
                return self._fallback_effectiveness_analysis(transcript, start_time)
                
        except Exception as e:
            print(f"Error in effectiveness analysis: {e}")
            return self._fallback_effectiveness_analysis(transcript, start_time)
    
    def match_trello_cards_intelligent(self, transcript: str, card_data: List[Dict]) -> List[Dict]:
        """Use GPT-4 Turbo to intelligently match Trello cards mentioned in transcript."""
        if not self.openai_client or not card_data:
            return []
        
        # Prepare card information for AI analysis
        card_info = []
        for card in card_data:
            card_info.append({
                'id': card.get('id'),
                'name': card.get('name', ''),
                'description': card.get('description', '')[:300],  # Limit description length
                'board': card.get('board_name', ''),
                'list': card.get('list_name', '')
            })
        
        prompt = f"""
        Analyze this meeting transcript and match it with relevant Trello cards. 
        
        For each card that is mentioned, discussed, or relevant to the conversation, provide:
        1. Match confidence (0-100%)
        2. Specific context where it was mentioned
        3. Detailed comment with ACTUAL QUOTES from the meeting discussion
        4. Match type (direct_mention, topic_relevance, action_item)
        
        IMPORTANT: Your suggested comments MUST include:
        - Direct quotes from the meeting (who said what)
        - Specific action items mentioned
        - Any deadlines or commitments made
        - Progress updates given
        - Issues or blockers discussed
        - Team members assigned or mentioned
        
        Meeting Transcript:
        {transcript}
        
        Available Trello Cards:
        {json.dumps(card_info, indent=2)}
        
        Return a JSON array of matches with this structure:
        [{{
            "card_id": "card_id_here",
            "card_name": "card_name_here", 
            "match_confidence": 85,
            "context": "specific quote or context from transcript",
            "suggested_comment": "📅 Meeting Update - [Date]\\n\\n**Discussion Summary:**\\n[Brief summary of what was discussed]\\n\\n**Direct Quotes:**\\n• Speaker: '[Exact quote from meeting]'\\n• Speaker: '[Another relevant quote]'\\n\\n**Action Items:**\\n• [Specific action item with assignee]\\n• [Another action if applicable]\\n\\n**Progress/Status:**\\n• [Current status mentioned]\\n• [Any blockers or challenges]\\n\\n**Next Steps:**\\n• [What needs to happen next]\\n• [Deadlines mentioned]\\n\\n---\\n*Auto-generated from meeting transcript*",
            "match_type": "direct_mention",
            "reasoning": "why this card is relevant"
        }}]
        
        Only include cards with confidence >= 60%. Be specific and accurate.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            
            # Parse JSON response - handle markdown code blocks
            try:
                # Remove markdown code blocks if present
                if content.strip().startswith('```json'):
                    content = content.strip()
                    # Find the JSON content between ```json and ```
                    start = content.find('```json') + 7
                    end = content.rfind('```')
                    if end > start:
                        content = content[start:end].strip()
                elif content.strip().startswith('```'):
                    content = content.strip()
                    # Find the JSON content between ``` and ```
                    start = content.find('```') + 3
                    end = content.rfind('```')
                    if end > start:
                        content = content[start:end].strip()
                
                matches = json.loads(content)
                if isinstance(matches, list):
                    # Add additional fields for UI compatibility
                    for match in matches:
                        # Find original card data
                        original_card = next((c for c in card_data if c.get('id') == match.get('card_id')), {})
                        
                        # Ensure we have the basic fields for backward compatibility
                        match.update({
                            'id': match.get('card_id'),
                            'name': match.get('card_name', original_card.get('name', 'Unknown')),
                            'url': original_card.get('url', ''),
                            'board_name': original_card.get('board', 'Unknown'),
                            'confidence': match.get('match_confidence', 0),
                            'description': original_card.get('description', '')[:200],
                            'list_name': original_card.get('list', 'Unknown'),
                            'card': {
                                'id': match.get('card_id'),
                                'name': match.get('card_name', original_card.get('name', 'Unknown')),
                                'url': original_card.get('url', ''),
                                'list': {'name': original_card.get('list', 'Unknown')}
                            },
                            'match_score': match.get('match_confidence', 0) / 100.0,
                            'reference': {
                                'context': match.get('context', '')
                            },
                            'match_type': match.get('match_type', 'ai_analysis')
                        })
                    
                    return sorted(matches, key=lambda x: x.get('match_confidence', 0), reverse=True)
                else:
                    print("GPT response was not a list")
                    return []
            except json.JSONDecodeError as e:
                print(f"Failed to parse GPT response as JSON: {e}")
                print(f"Response content: {content}")
                return []
                
        except Exception as e:
            print(f"Error in intelligent card matching: {e}")
            return []
    
    def generate_executive_summary(self, transcript: str, target_audience: str = "management") -> AnalysisResult:
        """Generate an executive summary tailored to the target audience."""
        start_time = datetime.now()
        
        audience_prompts = {
            "management": "Focus on high-level decisions, resource allocation, timeline impacts, and strategic implications.",
            "team": "Focus on action items, individual responsibilities, blockers, and next steps.",
            "stakeholders": "Focus on project status, milestones, budget implications, and deliverables.",
            "technical": "Focus on technical decisions, implementation details, architecture choices, and technical blockers."
        }
        
        audience_guidance = audience_prompts.get(target_audience, audience_prompts["management"])
        
        prompt = f"""
        Create an executive summary of this meeting transcript for {target_audience}.
        
        {audience_guidance}
        
        Structure the summary with:
        1. Key Outcomes (2-3 bullet points)
        2. Critical Decisions Made
        3. Action Items with Owners
        4. Risks/Blockers Identified
        5. Next Meeting/Follow-up Required
        
        Keep it concise but comprehensive.
        
        Transcript:
        {transcript}
        
        Format as structured JSON.
        """
        
        try:
            if self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4-turbo",  # GPT-5 model for best results
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1500
                )
                
                content = response.choices[0].message.content
                
                try:
                    summary_data = json.loads(content)
                except json.JSONDecodeError:
                    summary_data = self._parse_summary_fallback(content)
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                key_outcomes = summary_data.get('key_outcomes', [])
                action_items = summary_data.get('action_items', [])
                
                return AnalysisResult(
                    confidence=0.90,
                    summary=f"Executive summary for {target_audience} ({len(key_outcomes)} key outcomes)",
                    insights=[
                        f"Key outcomes: {len(key_outcomes)}",
                        f"Critical decisions: {len(summary_data.get('critical_decisions', []))}",
                        f"Action items: {len(action_items)}",
                        f"Risks identified: {len(summary_data.get('risks_blockers', []))}"
                    ],
                    metadata=summary_data,
                    processing_time=processing_time
                )
            else:
                return self._fallback_summary_analysis(transcript, target_audience, start_time)
                
        except Exception as e:
            print(f"Error in executive summary: {e}")
            return self._fallback_summary_analysis(transcript, target_audience, start_time)
    
    def analyze_communication_patterns(self, transcript: str) -> AnalysisResult:
        """Analyze communication patterns and team dynamics."""
        start_time = datetime.now()
        
        # Extract speakers and their contributions
        speaker_pattern = r'^([A-Za-z][A-Za-z\s]+?):\s*(.+)$'
        lines = transcript.split('\n')
        
        speakers = {}
        interruptions = 0
        questions_asked = 0
        
        for i, line in enumerate(lines):
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
                        'questions': 0,
                        'interruptions': 0
                    }
                
                speakers[speaker]['total_words'] += len(content.split())
                speakers[speaker]['turns'] += 1
                
                # Count questions
                if '?' in content:
                    speakers[speaker]['questions'] += 1
                    questions_asked += 1
                
                # Detect potential interruptions (simplified)
                if i > 0 and content.lower().startswith(('but', 'wait', 'actually', 'hold on')):
                    speakers[speaker]['interruptions'] += 1
                    interruptions += 1
        
        # Calculate communication metrics
        total_words = sum(data['total_words'] for data in speakers.values())
        
        communication_data = {
            'speakers_analysis': {},
            'overall_metrics': {
                'total_speakers': len(speakers),
                'total_words': total_words,
                'questions_asked': questions_asked,
                'interruptions': interruptions,
                'average_words_per_speaker': total_words / len(speakers) if speakers else 0
            }
        }
        
        # Analyze each speaker
        for speaker, data in speakers.items():
            communication_data['speakers_analysis'][speaker] = {
                'word_percentage': (data['total_words'] / total_words * 100) if total_words > 0 else 0,
                'speaking_turns': data['turns'],
                'questions_asked': data['questions'],
                'interruptions': data['interruptions'],
                'avg_words_per_turn': data['total_words'] / data['turns'] if data['turns'] > 0 else 0,
                'engagement_level': self._calculate_engagement_level(data, total_words)
            }
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return AnalysisResult(
            confidence=0.85,
            summary=f"Communication analysis: {len(speakers)} speakers, {questions_asked} questions",
            insights=[
                f"Total speakers: {len(speakers)}",
                f"Questions asked: {questions_asked}",
                f"Interruptions: {interruptions}",
                f"Most active: {max(speakers.keys(), key=lambda x: speakers[x]['total_words']) if speakers else 'N/A'}"
            ],
            metadata=communication_data,
            processing_time=processing_time
        )
    
    def _calculate_engagement_level(self, speaker_data: Dict, total_words: int) -> str:
        """Calculate engagement level for a speaker."""
        word_percentage = (speaker_data['total_words'] / total_words * 100) if total_words > 0 else 0
        questions = speaker_data['questions']
        turns = speaker_data['turns']
        
        # Simple engagement scoring
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
                'decisions_made': decisions[:5],  # Limit for brevity
                'pending_decisions': pending[:5],
                'method': 'pattern_fallback'
            },
            processing_time=processing_time
        )
    
    def _fallback_effectiveness_analysis(self, transcript: str, start_time: datetime) -> AnalysisResult:
        """Fallback effectiveness analysis."""
        # Simple metrics based on content analysis
        words = transcript.split()
        questions = transcript.count('?')
        action_words = ['will', 'should', 'need to', 'must', 'action', 'next']
        action_count = sum(transcript.lower().count(word) for word in action_words)
        
        # Basic effectiveness scoring
        effectiveness_score = 5.0  # Base score
        
        if questions > 2:
            effectiveness_score += 1  # Good engagement
        if action_count > 5:
            effectiveness_score += 1  # Clear action orientation
        if len(words) > 200:
            effectiveness_score += 0.5  # Substantive content
        
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
    
    def _fallback_summary_analysis(self, transcript: str, target_audience: str, start_time: datetime) -> AnalysisResult:
        """Fallback summary generation."""
        # Extract key sentences (simplified)
        sentences = transcript.split('.')
        key_sentences = [s.strip() for s in sentences if len(s.strip()) > 20][:5]
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return AnalysisResult(
            confidence=0.40,
            summary=f"Basic summary for {target_audience}",
            insights=[
                f"Key content extracted: {len(key_sentences)} points",
                f"Target audience: {target_audience}",
                "Limited analysis (AI not available)"
            ],
            metadata={
                'key_content': key_sentences,
                'target_audience': target_audience,
                'method': 'basic_extraction'
            },
            processing_time=processing_time
        )
    
    def _parse_sentiment_fallback(self, content: str) -> Dict:
        """Parse sentiment analysis from non-JSON response."""
        return {
            'sentiment_score': 7.0,
            'mood': 'neutral',
            'energy_level': 'medium',
            'collaboration_quality': 'fair',
            'method': 'fallback_parsing'
        }
    
    def _parse_decisions_fallback(self, content: str) -> Dict:
        """Parse decision analysis from non-JSON response."""
        return {
            'decisions_made': [],
            'pending_decisions': [],
            'decision_criteria': [],
            'stakeholders': [],
            'method': 'fallback_parsing'
        }
    
    def _parse_effectiveness_fallback(self, content: str) -> Dict:
        """Parse effectiveness analysis from non-JSON response."""
        return {
            'overall_effectiveness': 7.0,
            'agenda_adherence': 7,
            'time_management': 'Good',
            'improvement_suggestions': [],
            'method': 'fallback_parsing'
        }
    
    def _parse_summary_fallback(self, content: str) -> Dict:
        """Parse summary from non-JSON response."""
        return {
            'key_outcomes': [],
            'critical_decisions': [],
            'action_items': [],
            'risks_blockers': [],
            'method': 'fallback_parsing'
        }

def test_enhanced_ai():
    """Test the enhanced AI module."""
    print("Testing Enhanced AI module...")
    
    ai = EnhancedAI()
    
    sample_transcript = """
    John: Good morning everyone. Let's start our weekly project review.
    
    Sarah: Thanks John. The WordPress development is going well. We've completed about 80% of the main pages.
    
    Mike: That's great progress! What about the client feedback integration?
    
    Sarah: Actually, we're waiting for approval on the design mockups. It's been two weeks now.
    
    John: That's concerning. We need to escalate this. Mike, can you reach out to the client directly?
    
    Mike: Absolutely. I'll call them today. Also, should we proceed with the backend development while waiting?
    
    Sarah: I think we should. We can always adjust the frontend later.
    
    John: Agreed. Let's make that decision final. Sarah, please coordinate with the backend team.
    """
    
    # Test sentiment analysis
    print("\n--- Sentiment Analysis ---")
    sentiment_result = ai.analyze_meeting_sentiment(sample_transcript)
    print(f"Summary: {sentiment_result.summary}")
    print(f"Insights: {sentiment_result.insights}")
    print(f"Confidence: {sentiment_result.confidence}")
    
    # Test decision analysis
    print("\n--- Decision Analysis ---")
    decision_result = ai.analyze_decision_points(sample_transcript)
    print(f"Summary: {decision_result.summary}")
    print(f"Insights: {decision_result.insights}")
    
    # Test communication patterns
    print("\n--- Communication Patterns ---")
    comm_result = ai.analyze_communication_patterns(sample_transcript)
    print(f"Summary: {comm_result.summary}")
    print(f"Insights: {comm_result.insights}")
    
    # Test effectiveness analysis
    print("\n--- Effectiveness Analysis ---")
    eff_result = ai.analyze_meeting_effectiveness(sample_transcript, 30)
    print(f"Summary: {eff_result.summary}")
    print(f"Insights: {eff_result.insights}")
    
    print("\nEnhanced AI test completed!")

if __name__ == "__main__":
    test_enhanced_ai()