#!/usr/bin/env python3
"""
Speaker Analysis and Meeting Insights Module
Analyzes meeting transcripts for speaking patterns, engagement, and improvement suggestions
"""

import os
import re
import json
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

class SpeakerAnalyzer:
    """Analyzes meeting transcripts for speaker patterns and insights."""
    
    def __init__(self):
        self.openai_api_key = os.environ.get('OPENAI_API_KEY')
        
    def extract_speakers_and_content(self, transcript: str) -> Dict[str, Dict]:
        """Extract speakers and their contributions from transcript."""
        speakers = defaultdict(lambda: {
            'lines': [],
            'word_count': 0,
            'speaking_time_estimate': 0,
            'topics_mentioned': [],
            'questions_asked': 0,
            'action_items_given': 0,
            'interruptions': 0,
            'tone_indicators': []
        })
        
        lines = transcript.split('\n')
        current_speaker = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for speaker patterns: "Name:" or "Name -"
            speaker_match = re.match(r'^([A-Za-z][A-Za-z\s]+?)\s*[-:]\s*(.+)$', line)
            
            if speaker_match:
                speaker_name = speaker_match.group(1).strip().title()
                spoken_text = speaker_match.group(2).strip()
                current_speaker = speaker_name
                
                # Filter out common non-speaker patterns
                if speaker_name.lower() in ['meeting', 'call', 'video', 'audio', 'transcript', 'recording']:
                    continue
                
                speakers[speaker_name]['lines'].append(spoken_text)
                speakers[speaker_name]['word_count'] += len(spoken_text.split())
                
                # Estimate speaking time (rough: 150 words per minute)
                speakers[speaker_name]['speaking_time_estimate'] = speakers[speaker_name]['word_count'] / 150
                
                # Analyze content
                self._analyze_speaking_content(speakers[speaker_name], spoken_text)
                
            elif current_speaker and line:
                # Continuation of previous speaker
                speakers[current_speaker]['lines'].append(line)
                speakers[current_speaker]['word_count'] += len(line.split())
                speakers[current_speaker]['speaking_time_estimate'] = speakers[current_speaker]['word_count'] / 150
                self._analyze_speaking_content(speakers[current_speaker], line)
        
        return dict(speakers)
    
    def _analyze_speaking_content(self, speaker_data: Dict, text: str):
        """Analyze the content of what a speaker said."""
        text_lower = text.lower()
        
        # Count questions
        speaker_data['questions_asked'] += text.count('?')
        
        # Detect action items
        action_patterns = ['will do', "i'll", 'let me', 'i can', "i'll take", "i'll handle", 'next step']
        for pattern in action_patterns:
            if pattern in text_lower:
                speaker_data['action_items_given'] += 1
                break
        
        # Detect tone indicators
        positive_indicators = ['great', 'excellent', 'perfect', 'good', 'thanks', 'appreciate']
        negative_indicators = ['issue', 'problem', 'concern', 'difficult', 'challenge', 'stuck']
        uncertainty_indicators = ['maybe', 'perhaps', 'not sure', 'think', 'might', 'possibly']
        
        for indicator in positive_indicators:
            if indicator in text_lower:
                speaker_data['tone_indicators'].append('positive')
                break
        
        for indicator in negative_indicators:
            if indicator in text_lower:
                speaker_data['tone_indicators'].append('negative')
                break
                
        for indicator in uncertainty_indicators:
            if indicator in text_lower:
                speaker_data['tone_indicators'].append('uncertain')
                break
    
    def calculate_engagement_metrics(self, speakers: Dict[str, Dict]) -> Dict:
        """Calculate engagement and participation metrics."""
        total_words = sum(data['word_count'] for data in speakers.values())
        total_time = sum(data['speaking_time_estimate'] for data in speakers.values())
        
        metrics = {
            'total_speakers': len(speakers),
            'total_words': total_words,
            'estimated_meeting_duration': max(total_time, 5),  # Minimum 5 minutes
            'speaking_distribution': {},
            'engagement_scores': {},
            'participation_balance': 'balanced'
        }
        
        # Calculate speaking distribution
        for name, data in speakers.items():
            if total_words > 0:
                percentage = (data['word_count'] / total_words) * 100
                metrics['speaking_distribution'][name] = {
                    'percentage': round(percentage, 1),
                    'word_count': data['word_count'],
                    'estimated_minutes': round(data['speaking_time_estimate'], 1)
                }
                
                # Calculate engagement score
                engagement_score = self._calculate_engagement_score(data, percentage)
                metrics['engagement_scores'][name] = engagement_score
        
        # Determine participation balance
        percentages = [dist['percentage'] for dist in metrics['speaking_distribution'].values()]
        if percentages:
            max_percentage = max(percentages)
            min_percentage = min(percentages)
            
            if max_percentage > 60:
                metrics['participation_balance'] = 'dominated'
            elif max_percentage - min_percentage > 40:
                metrics['participation_balance'] = 'unbalanced'
            else:
                metrics['participation_balance'] = 'balanced'
        
        return metrics
    
    def _calculate_engagement_score(self, speaker_data: Dict, speaking_percentage: float) -> Dict:
        """Calculate engagement score for a speaker."""
        score = 50  # Base score
        factors = []
        
        # Speaking time factor (optimal around 20-40% for 2-3 people, less for larger groups)
        if 15 <= speaking_percentage <= 45:
            score += 20
            factors.append('Good speaking balance')
        elif speaking_percentage > 60:
            score -= 15
            factors.append('May be dominating conversation')
        elif speaking_percentage < 10:
            score -= 10
            factors.append('Limited participation')
        
        # Questions factor
        if speaker_data['questions_asked'] > 0:
            score += min(speaker_data['questions_asked'] * 5, 15)
            factors.append(f"Asked {speaker_data['questions_asked']} questions")
        
        # Action items factor
        if speaker_data['action_items_given'] > 0:
            score += min(speaker_data['action_items_given'] * 8, 20)
            factors.append(f"Committed to {speaker_data['action_items_given']} action items")
        
        # Tone analysis
        positive_count = speaker_data['tone_indicators'].count('positive')
        negative_count = speaker_data['tone_indicators'].count('negative')
        
        if positive_count > negative_count:
            score += 10
            factors.append('Positive tone')
        elif negative_count > positive_count * 2:
            score -= 5
            factors.append('Frequent concerns raised')
        
        return {
            'score': max(0, min(100, score)),
            'level': 'High' if score >= 80 else 'Medium' if score >= 60 else 'Low',
            'factors': factors
        }
    
    def analyze_transcript(self, transcript: str) -> Dict:
        """Main analysis function that processes a transcript and returns comprehensive insights."""
        try:
            # Extract speakers and their content
            speakers = self.extract_speakers_and_content(transcript)
            
            if not speakers:
                return {
                    'success': False,
                    'error': 'No speakers detected in transcript. Please ensure the transcript includes speaker names followed by colons or dashes.'
                }
            
            # Calculate metrics
            metrics = self.calculate_engagement_metrics(speakers)
            
            # Generate basic insights
            meeting_insights = {
                'meeting_quality': 'Good' if metrics['participation_balance'] == 'balanced' else 'Needs Improvement',
                'key_observations': [],
                'recommended_improvements': []
            }
            
            # Simple individual suggestions
            individual_suggestions = {}
            for name in speakers.keys():
                individual_suggestions[name] = ['Great participation in the meeting!']
            
            return {
                'success': True,
                'speakers': speakers,
                'metrics': metrics,
                'individual_suggestions': individual_suggestions,
                'meeting_insights': meeting_insights,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Analysis failed: {str(e)}'
            }

def test_speaker_analysis():
    """Test the speaker analysis functionality."""
    sample_transcript = """
John: Good morning everyone. Let's start with our updates. Sarah, how's the progress on the WordPress site?

Sarah: The WordPress site is going well. I've been working on the main landing page and we should have the initial version ready for review by Friday.

Mike: Great! What about the task for reaching out to onboarded clients?

Sarah: Yes, I've been working on that too. The reach out task is about 60% complete.

John: Perfect. Any blockers on the Center Name projects?

Mike: Actually yes. For the Vitality Energy Healing project, I'm waiting for approval on the logo design.
"""
    
    analyzer = SpeakerAnalyzer()
    result = analyzer.analyze_transcript(sample_transcript)
    
    if result['success']:
        print("Speaker Analysis Test Results:")
        print(f"Speakers found: {list(result['speakers'].keys())}")
        print(f"Meeting quality: {result['meeting_insights']['meeting_quality']}")
        print(f"Participation balance: {result['metrics']['participation_balance']}")
        return True
    else:
        print(f"Test failed: {result['error']}")
        return False

if __name__ == "__main__":
    if test_speaker_analysis():
        print("Speaker analysis test passed!")
    else:
        print("Speaker analysis test failed!")