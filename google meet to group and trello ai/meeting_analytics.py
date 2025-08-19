#!/usr/bin/env python3
"""
Meeting Analytics Module - Comprehensive meeting participation and engagement analysis
"""

import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from collections import Counter, defaultdict
import json

class MeetingAnalyzer:
    """Analyzes meeting transcripts for participation, engagement, and effectiveness."""
    
    def __init__(self):
        self.speaker_pattern = re.compile(r'^([A-Za-z][A-Za-z\s\'\.]+?)[\s]*[-:][\s]*(.+)$', re.MULTILINE)
        
    def analyze_full_meeting(self, transcript: str, doc_content: Dict = None) -> Dict[str, Any]:
        """
        Perform comprehensive meeting analysis.
        
        Returns:
            Dict with all meeting analytics including participation, engagement, and insights
        """
        # Extract all speakers and their contributions
        speakers_data = self._extract_speakers(transcript)
        
        # Calculate participation metrics
        participation = self._calculate_participation(speakers_data)
        
        # Identify silent participants (if we have a participant list)
        silent_participants = self._identify_silent_participants(speakers_data, doc_content)
        
        # Calculate engagement metrics
        engagement = self._calculate_engagement(speakers_data)
        
        # Extract key insights
        insights = self._extract_insights(transcript, speakers_data)
        
        # Calculate meeting effectiveness
        effectiveness = self._calculate_effectiveness(participation, engagement, insights)
        
        # Generate WhatsApp summary
        whatsapp_summary = self._generate_whatsapp_summary(
            participation, silent_participants, insights, effectiveness
        )
        
        return {
            'participation': participation,
            'silent_participants': silent_participants,
            'engagement': engagement,
            'insights': insights,
            'effectiveness': effectiveness,
            'whatsapp_summary': whatsapp_summary,
            'raw_speakers': speakers_data
        }
    
    def _extract_speakers(self, transcript: str) -> Dict[str, List[str]]:
        """Extract all speakers and their statements from transcript."""
        speakers_data = defaultdict(list)
        
        for match in self.speaker_pattern.finditer(transcript):
            speaker = match.group(1).strip()
            statement = match.group(2).strip()
            
            # Filter out common non-speaker patterns
            if speaker.lower() not in ['meeting', 'call', 'video', 'audio', 'transcript', 'recording', 'summary']:
                speakers_data[speaker].append(statement)
        
        return dict(speakers_data)
    
    def _calculate_participation(self, speakers_data: Dict) -> Dict[str, Any]:
        """Calculate participation metrics for each speaker."""
        total_statements = sum(len(statements) for statements in speakers_data.values())
        total_words = sum(
            sum(len(statement.split()) for statement in statements)
            for statements in speakers_data.values()
        )
        
        participation_data = {}
        
        for speaker, statements in speakers_data.items():
            word_count = sum(len(statement.split()) for statement in statements)
            statement_count = len(statements)
            
            participation_data[speaker] = {
                'statement_count': statement_count,
                'word_count': word_count,
                'participation_percentage': round((word_count / total_words * 100) if total_words > 0 else 0, 1),
                'average_statement_length': round(word_count / statement_count if statement_count > 0 else 0, 1),
                'speaking_rank': 0  # Will be calculated after sorting
            }
        
        # Add speaking ranks
        sorted_speakers = sorted(
            participation_data.items(),
            key=lambda x: x[1]['word_count'],
            reverse=True
        )
        
        for rank, (speaker, data) in enumerate(sorted_speakers, 1):
            participation_data[speaker]['speaking_rank'] = rank
        
        return {
            'speakers': participation_data,
            'total_speakers': len(speakers_data),
            'total_statements': total_statements,
            'total_words': total_words,
            'most_active': sorted_speakers[0][0] if sorted_speakers else None,
            'least_active': sorted_speakers[-1][0] if sorted_speakers else None
        }
    
    def _identify_silent_participants(self, speakers_data: Dict, doc_content: Dict) -> List[str]:
        """Identify participants who didn't speak in the meeting."""
        silent_participants = []
        
        if doc_content and doc_content.get('participants'):
            # Get list of expected participants from doc
            expected_participants = doc_content['participants']
            
            # Get list of actual speakers
            actual_speakers = set(speakers_data.keys())
            
            # Find who didn't speak
            for participant in expected_participants:
                # Check if participant name appears in any speaker name
                found = False
                for speaker in actual_speakers:
                    if participant.lower() in speaker.lower() or speaker.lower() in participant.lower():
                        found = True
                        break
                
                if not found:
                    silent_participants.append(participant)
        
        return silent_participants
    
    def _calculate_engagement(self, speakers_data: Dict) -> Dict[str, Any]:
        """Calculate engagement metrics."""
        engagement_data = {}
        
        for speaker, statements in speakers_data.items():
            questions_asked = sum(1 for s in statements if '?' in s)
            exclamations = sum(1 for s in statements if '!' in s)
            
            # Simple engagement scoring
            engagement_score = min(100, (
                questions_asked * 15 +  # Questions show engagement
                len(statements) * 2 +    # Frequency of participation
                exclamations * 5         # Enthusiasm
            ))
            
            engagement_data[speaker] = {
                'questions_asked': questions_asked,
                'engagement_score': engagement_score,
                'interaction_style': self._determine_interaction_style(statements)
            }
        
        # Calculate overall meeting engagement
        avg_engagement = sum(e['engagement_score'] for e in engagement_data.values()) / len(engagement_data) if engagement_data else 0
        
        return {
            'individual': engagement_data,
            'average_engagement': round(avg_engagement, 1),
            'total_questions': sum(e['questions_asked'] for e in engagement_data.values()),
            'meeting_energy': self._calculate_meeting_energy(avg_engagement)
        }
    
    def _determine_interaction_style(self, statements: List[str]) -> str:
        """Determine a speaker's interaction style based on their statements."""
        if not statements:
            return "silent"
        
        questions = sum(1 for s in statements if '?' in s)
        total = len(statements)
        question_ratio = questions / total if total > 0 else 0
        
        if question_ratio > 0.4:
            return "inquisitive"
        elif total > 10:
            return "active"
        elif total > 5:
            return "moderate"
        else:
            return "reserved"
    
    def _calculate_meeting_energy(self, avg_engagement: float) -> str:
        """Determine overall meeting energy level."""
        if avg_engagement >= 70:
            return "high"
        elif avg_engagement >= 40:
            return "moderate"
        else:
            return "low"
    
    def _extract_insights(self, transcript: str, speakers_data: Dict) -> Dict[str, Any]:
        """Extract key insights from the meeting."""
        insights = {
            'decisions': [],
            'action_items': [],
            'key_topics': [],
            'concerns_raised': [],
            'positive_moments': []
        }
        
        # Decision patterns
        decision_patterns = [
            r'(?:we|I) (?:decided|agreed|concluded) (?:to|that) (.+?)(?:\.|$)',
            r'(?:the|our) decision is (.+?)(?:\.|$)',
            r'(?:let\'s|we\'ll|we will) (.+?)(?:\.|$)'
        ]
        
        # Action item patterns
        action_patterns = [
            r'(?:will|need to|should|must) (.+?)(?:\.|$)',
            r'action item[:\s]+(.+?)(?:\.|$)',
            r'(?:please|kindly) (.+?)(?:\.|$)'
        ]
        
        # Concern patterns
        concern_patterns = [
            r'(?:concerned about|worried about|issue with) (.+?)(?:\.|$)',
            r'(?:problem|challenge|blocker) (?:is|with) (.+?)(?:\.|$)'
        ]
        
        transcript_lower = transcript.lower()
        
        # Extract decisions
        for pattern in decision_patterns:
            matches = re.findall(pattern, transcript_lower, re.IGNORECASE)
            insights['decisions'].extend(matches[:3])  # Top 3
        
        # Extract action items
        for pattern in action_patterns:
            matches = re.findall(pattern, transcript_lower, re.IGNORECASE)
            insights['action_items'].extend(matches[:5])  # Top 5
        
        # Extract concerns
        for pattern in concern_patterns:
            matches = re.findall(pattern, transcript_lower, re.IGNORECASE)
            insights['concerns_raised'].extend(matches[:3])  # Top 3
        
        # Identify key topics (most frequent meaningful words)
        words = re.findall(r'\b[a-z]{4,}\b', transcript_lower)
        word_freq = Counter(words)
        
        # Filter out common words
        common_words = {'that', 'this', 'with', 'from', 'have', 'will', 'what', 'when', 'where', 'which', 'would', 'could', 'should', 'about', 'there', 'their', 'been', 'some', 'just', 'like', 'more', 'very', 'really'}
        
        for word, count in word_freq.most_common(20):
            if word not in common_words and count > 3:
                insights['key_topics'].append(word)
            if len(insights['key_topics']) >= 5:
                break
        
        # Clean up insights
        insights['decisions'] = list(set(insights['decisions']))[:3]
        insights['action_items'] = list(set(insights['action_items']))[:5]
        insights['concerns_raised'] = list(set(insights['concerns_raised']))[:3]
        
        return insights
    
    def _calculate_effectiveness(self, participation: Dict, engagement: Dict, insights: Dict) -> Dict[str, Any]:
        """Calculate overall meeting effectiveness metrics."""
        scores = {
            'participation_balance': 0,
            'engagement_level': 0,
            'decision_clarity': 0,
            'action_orientation': 0
        }
        
        # Participation balance (how evenly distributed was participation)
        if participation['speakers']:
            percentages = [s['participation_percentage'] for s in participation['speakers'].values()]
            avg_percentage = 100 / len(percentages) if percentages else 0
            variance = sum((p - avg_percentage) ** 2 for p in percentages) / len(percentages) if percentages else 0
            scores['participation_balance'] = max(0, 100 - variance)
        
        # Engagement level
        scores['engagement_level'] = engagement['average_engagement']
        
        # Decision clarity
        scores['decision_clarity'] = min(100, len(insights['decisions']) * 33)
        
        # Action orientation
        scores['action_orientation'] = min(100, len(insights['action_items']) * 20)
        
        # Overall effectiveness
        overall_score = sum(scores.values()) / len(scores)
        
        return {
            'scores': scores,
            'overall_score': round(overall_score, 1),
            'rating': self._get_effectiveness_rating(overall_score),
            'recommendations': self._get_recommendations(scores, participation, engagement)
        }
    
    def _get_effectiveness_rating(self, score: float) -> str:
        """Get effectiveness rating based on score."""
        if score >= 80:
            return "excellent"
        elif score >= 60:
            return "good"
        elif score >= 40:
            return "fair"
        else:
            return "needs improvement"
    
    def _get_recommendations(self, scores: Dict, participation: Dict, engagement: Dict) -> List[str]:
        """Generate recommendations based on meeting analysis."""
        recommendations = []
        
        if scores['participation_balance'] < 50:
            recommendations.append("Encourage more balanced participation from all attendees")
        
        if scores['engagement_level'] < 50:
            recommendations.append("Increase engagement by asking more questions and encouraging discussion")
        
        if scores['decision_clarity'] < 50:
            recommendations.append("Make decisions more explicit and document them clearly")
        
        if scores['action_orientation'] < 50:
            recommendations.append("Define clear action items with owners and deadlines")
        
        if engagement['total_questions'] < 5:
            recommendations.append("Ask more questions to ensure understanding and alignment")
        
        return recommendations[:3]  # Top 3 recommendations
    
    def generate_narrative_summary(self, transcript: str, doc_content: Dict, doc_url: str = "") -> str:
        """Extract and format existing summary and next steps from Google Doc Notes section."""
        try:
            # Extract attendees from transcript
            attendees = self._extract_attendees(transcript)
            
            # Get Notes content and full transcript
            notes_content = doc_content.get('notes_content', '')
            
            print(f"Notes content length: {len(notes_content)}")
            print(f"Notes preview: {notes_content[:200]}...")
            
            # If notes content is too short, search in full transcript
            content_to_search = notes_content
            if len(notes_content) < 500:  # Notes section is too short, use full transcript
                content_to_search = transcript
                print(f"Notes too short ({len(notes_content)} chars), using full transcript ({len(transcript)} chars)")
            
            if not content_to_search:
                return self._fallback_narrative_summary(transcript, doc_content, doc_url)
            
            # Extract existing meeting summary from content
            meeting_summary = self._extract_meeting_summary(content_to_search)
            
            # Extract existing next steps from content
            next_steps = self._extract_next_steps(content_to_search)
            
            # Extract details section from content
            details = self._extract_details(content_to_search)
            
            print(f"Found meeting summary: {len(meeting_summary)} chars")
            print(f"Found next steps: {len(next_steps)} items")
            print(f"Found details: {len(details)} items")
            
            # Format the final summary
            summary_parts = []
            
            # Attendees
            if attendees:
                summary_parts.append(f"Today the following attended the meeting: {', '.join(attendees)}")
            else:
                summary_parts.append("Today the following attended the meeting: Team members")
            
            summary_parts.append("")
            
            # Meeting Summary
            if meeting_summary:
                summary_parts.append("MEETING SUMMARY:")
                summary_parts.append(meeting_summary)
            else:
                summary_parts.append("MEETING SUMMARY:")
                summary_parts.append("Meeting notes and discussions are documented in the attached Google Doc.")
            
            summary_parts.append("")
            
            # Next Steps
            if next_steps:
                summary_parts.append("Suggested next steps:")
                for step in next_steps:
                    summary_parts.append(step)
            else:
                summary_parts.append("Suggested next steps:")
                summary_parts.append("Team members will follow up on action items as discussed.")
            
            summary_parts.append("")
            summary_parts.append("")
            
            # Document Link
            summary_parts.append("LINK TO FULL SUMMARISED DOCUMENT:")
            summary_parts.append("This is a google doc which contains more details of the meeting:")
            summary_parts.append(doc_url if doc_url else "[Document link not available]")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            print(f"Error extracting summary from Notes: {e}")
            return self._fallback_narrative_summary(transcript, doc_content, doc_url)
    
    def _extract_details(self, content: str) -> List[str]:
        """Extract the Details section from content."""
        try:
            # Look for "Details" or similar patterns
            details_patterns = [
                r'Details[:\s]*\n(.+?)(?=\n\n|\n[A-Z][a-z]+\s*steps|\nSuggested|\nLINK TO|$)',
                r'DETAILS[:\s]*\n(.+?)(?=\n\n|\n[A-Z][a-z]+\s*steps|\nSuggested|\nLINK TO|$)',
                r'Meeting Details[:\s]*\n(.+?)(?=\n\n|\n[A-Z][a-z]+\s*steps|\nSuggested|\nLINK TO|$)',
                # Also look for bullet points or structured content
                r'\* (.+?)(?=\n\*|\n\n|\nSuggested|\nLINK TO|$)'
            ]
            
            for pattern in details_patterns:
                match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
                if match:
                    details_text = match.group(1).strip()
                    
                    # Split into individual details
                    details = []
                    for line in details_text.split('\n'):
                        line = line.strip()
                        if line and not line.startswith(('LINK TO', 'Link to', 'Suggested')):
                            # Clean up common bullet points
                            line = re.sub(r'^[-•*]\s*', '', line)
                            if line and len(line) > 10:  # Only include substantial details
                                details.append(line)
                    
                    if details:
                        return details[:10]  # Limit to 10 details
            
            return []
            
        except Exception as e:
            print(f"Error extracting details: {e}")
            return []
    
    def _extract_meeting_summary(self, notes_content: str) -> str:
        """Extract the MEETING SUMMARY section from Notes content."""
        try:
            # Look for "MEETING SUMMARY:" or similar patterns (more flexible)
            summary_patterns = [
                r'MEETING SUMMARY[:\s]*\n(.+?)(?=\n\n|\n[A-Z][a-z]+\s*steps|\nSuggested|$)',
                r'Meeting Summary[:\s]*\n(.+?)(?=\n\n|\n[A-Z][a-z]+\s*steps|\nSuggested|$)',
                r'Summary[:\s]*\n(.+?)(?=\n\n|\n[A-Z][a-z]+\s*steps|\nSuggested|$)',
                r'SUMMARY[:\s]*\n(.+?)(?=\n\n|\n[A-Z][a-z]+\s*steps|\nSuggested|$)',
                # Also look for content after "outlined" or other meeting-related phrases
                r'outlined (.+?)(?=\n\n|\n[A-Z][a-z]+\s*steps|\nSuggested|$)',
                r'discussed (.+?)(?=\n\n|\n[A-Z][a-z]+\s*steps|\nSuggested|$)'
            ]
            
            for pattern in summary_patterns:
                match = re.search(pattern, notes_content, re.IGNORECASE | re.DOTALL)
                if match:
                    summary = match.group(1).strip()
                    # Clean up the summary
                    summary = re.sub(r'\n+', ' ', summary)  # Replace multiple newlines with space
                    summary = re.sub(r'\s+', ' ', summary)  # Replace multiple spaces with single space
                    return summary
            
            return ""
            
        except Exception as e:
            print(f"Error extracting meeting summary: {e}")
            return ""
    
    def _extract_next_steps(self, notes_content: str) -> List[str]:
        """Extract the Suggested next steps section from Notes content."""
        try:
            # Look for "Suggested next steps:" or similar patterns (more flexible)
            steps_patterns = [
                r'Suggested next steps[:\s]*\n(.+?)(?=\n\n|LINK TO|LINK:|Link to|$)',
                r'Next steps[:\s]*\n(.+?)(?=\n\n|LINK TO|LINK:|Link to|$)',
                r'Action items[:\s]*\n(.+?)(?=\n\n|LINK TO|LINK:|Link to|$)',
                r'TODO[:\s]*\n(.+?)(?=\n\n|LINK TO|LINK:|Link to|$)',
                # Look for lines that start with names followed by "will"
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+will\s+.+?)(?=\n\n|LINK TO|LINK:|Link to|$)',
                # Look for action patterns
                r'((?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+will\s+.+?\n?){1,10})(?=\n\n|LINK TO|LINK:|Link to|$)'
            ]
            
            for pattern in steps_patterns:
                match = re.search(pattern, notes_content, re.IGNORECASE | re.DOTALL)
                if match:
                    steps_text = match.group(1).strip()
                    
                    # Split into individual steps
                    steps = []
                    for line in steps_text.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('LINK TO'):
                            # Clean up common bullet points
                            line = re.sub(r'^[-•*]\s*', '', line)
                            if line:
                                steps.append(line)
                    
                    return steps[:10]  # Limit to 10 steps
            
            return []
            
        except Exception as e:
            print(f"Error extracting next steps: {e}")
            return []
    
    def _extract_attendees(self, transcript: str) -> List[str]:
        """Extract attendee names from transcript."""
        # Find speaker patterns
        speaker_matches = re.findall(r'^([A-Za-z][A-Za-z\s\'\.]+?)[\s]*[-:]', transcript, re.MULTILINE)
        
        # Clean and deduplicate names
        attendees = set()
        for name in speaker_matches:
            name = name.strip()
            # Filter out common non-names
            if name.lower() not in ['meeting', 'call', 'video', 'audio', 'transcript', 'recording', 'summary']:
                if len(name) > 2 and len(name) < 50:  # Reasonable name length
                    attendees.add(name)
        
        return sorted(list(attendees))
    
    def _fallback_narrative_summary(self, transcript: str, doc_content: Dict, doc_url: str) -> str:
        """Fallback summary if GPT-5 fails."""
        today = datetime.now().strftime('%B %d, %Y')
        attendees = self._extract_attendees(transcript)
        
        return f"""Today the following attended the meeting: {', '.join(attendees) if attendees else 'Team members'}

MEETING SUMMARY:
A team meeting was conducted where various topics were discussed and decisions were made. The team reviewed current projects, discussed upcoming initiatives, and aligned on next steps for moving forward.

Suggested next steps:
Team members will follow up on their respective action items as discussed in the meeting.

LINK TO FULL SUMMARISED DOCUMENT:
This is a google doc which contains more details of the meeting:
{doc_url if doc_url else "[Document link not available]"}"""
    
    def _generate_whatsapp_summary(self, participation: Dict, silent_participants: List[str], 
                                   insights: Dict, effectiveness: Dict) -> str:
        """This method is now deprecated in favor of generate_narrative_summary."""
        return "Use generate_narrative_summary instead for proper WhatsApp summaries."