"""
Meeting Summarizer

Handles AI-powered summarization of meeting transcripts using various
LLM providers like OpenAI, Claude, etc.
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import logging

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from agent import MeetingSummary, LLMProvider

logger = logging.getLogger(__name__)

# Summary templates
SUMMARY_TEMPLATES = {
    'standard': """
Analyze this meeting transcript and provide a comprehensive summary with the following sections:

1. MEETING OVERVIEW
   - Main purpose and objectives
   - Key participants and their roles
   
2. KEY DISCUSSIONS
   - Primary topics covered
   - Important points raised
   - Different viewpoints expressed
   
3. DECISIONS MADE
   - Concrete decisions reached
   - Agreements and approvals
   - Policy or strategy changes
   
4. ACTION ITEMS
   - Tasks assigned with owners
   - Deadlines and timelines
   - Follow-up requirements
   
5. NEXT STEPS
   - Planned follow-up meetings
   - Immediate priorities
   - Long-term goals discussed

Transcript:
{transcript}

Summary:
""",
    
    'brief': """
Provide a brief summary of this meeting in 3-4 bullet points covering:
- Main topics discussed
- Key decisions made
- Important action items
- Next steps

Transcript:
{transcript}

Brief Summary:
""",
    
    'detailed': """
Provide a detailed analysis of this meeting transcript including:

1. EXECUTIVE SUMMARY (2-3 sentences)

2. DETAILED DISCUSSION POINTS
   - Break down each topic discussed
   - Include specific details and context
   - Note any concerns or issues raised
   
3. STAKEHOLDER CONTRIBUTIONS
   - Key points made by each participant
   - Areas of expertise demonstrated
   - Collaborative moments
   
4. DECISION ANALYSIS
   - How decisions were reached
   - Factors considered
   - Potential implications
   
5. RISK ASSESSMENT
   - Potential challenges identified
   - Risk mitigation strategies discussed
   - Dependencies noted
   
6. ACTION PLAN
   - Detailed breakdown of next steps
   - Resource requirements
   - Success metrics mentioned

Transcript:
{transcript}

Detailed Analysis:
"""
}


class MeetingSummarizer:
    """
    Generates AI-powered summaries of meeting transcripts.
    
    Supports multiple LLM providers and summary formats.
    """
    
    def __init__(self, 
                 llm_provider: Optional[LLMProvider] = None,
                 default_format: str = 'standard'):
        """
        Initialize the meeting summarizer.
        
        Args:
            llm_provider: LLM provider instance
            default_format: Default summary format
        """
        self.llm_provider = llm_provider or self._get_default_provider()
        self.default_format = default_format
        self.templates = SUMMARY_TEMPLATES
    
    def _get_default_provider(self) -> LLMProvider:
        """Get default LLM provider based on available API keys."""
        if os.getenv('OPENAI_API_KEY'):
            from ..agent import OpenAIProvider
            return OpenAIProvider()
        elif os.getenv('CLAUDE_API_KEY'):
            from ..agent import ClaudeProvider
            return ClaudeProvider()
        else:
            raise ValueError("No LLM provider API key found")
    
    async def summarize_transcript(self, 
                                 transcript_text: str,
                                 format_type: str = None,
                                 participants: Optional[List[str]] = None,
                                 meeting_date: Optional[datetime] = None) -> MeetingSummary:
        """
        Generate a summary of the meeting transcript.
        
        Args:
            transcript_text: Raw transcript text
            format_type: Summary format ('standard', 'brief', 'detailed')
            participants: List of meeting participants
            meeting_date: Date of the meeting
            
        Returns:
            MeetingSummary object
        """
        format_type = format_type or self.default_format
        
        if format_type not in self.templates:
            raise ValueError(f"Unknown format: {format_type}. Available: {list(self.templates.keys())}")
        
        try:
            # Generate summary using LLM
            prompt = self.templates[format_type].format(transcript=transcript_text)
            summary_text = await self.llm_provider.generate_summary(transcript_text)
            
            # Extract action items
            action_items_data = await self.llm_provider.extract_action_items(transcript_text)
            
            # Process action items
            from ..agent import ActionItem
            action_items = []
            for item_data in action_items_data:
                try:
                    action_item = ActionItem(**item_data)
                    action_items.append(action_item)
                except Exception as e:
                    logger.warning(f"Invalid action item data: {e}")
            
            # Extract other components
            key_decisions = await self._extract_decisions(transcript_text)
            topics_discussed = await self._extract_topics(transcript_text)
            
            # Create MeetingSummary
            meeting_summary = MeetingSummary(
                title=self._generate_title(transcript_text, participants),
                date=meeting_date or datetime.now(),
                participants=participants or [],
                summary=summary_text,
                key_decisions=key_decisions,
                action_items=action_items,
                topics_discussed=topics_discussed,
                duration=self._estimate_duration(transcript_text)
            )
            
            logger.info(f"Generated {format_type} summary with {len(action_items)} action items")
            return meeting_summary
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            raise
    
    async def _extract_decisions(self, transcript_text: str) -> List[str]:
        """
        Extract key decisions from transcript.
        
        Args:
            transcript_text: Transcript content
            
        Returns:
            List of key decisions
        """
        try:
            decision_prompt = f"""
            Extract the key decisions made in this meeting. Return only concrete decisions that were agreed upon, not discussions or considerations.
            
            Format as a bullet-pointed list. If no clear decisions were made, return "No specific decisions recorded".
            
            Transcript:
            {transcript_text}
            
            Key Decisions:
            """
            
            # Use a simplified approach - look for decision keywords
            decisions = []
            lines = transcript_text.lower().split('\n')
            
            decision_keywords = [
                'decided', 'agreed', 'approved', 'resolved', 'concluded',
                'we will', 'we should', 'let\'s', 'going forward', 'action:'
            ]
            
            for line in lines:
                for keyword in decision_keywords:
                    if keyword in line and len(line.strip()) > 20:
                        # Clean up and add decision
                        clean_line = line.strip().capitalize()
                        if clean_line not in decisions and len(clean_line) < 200:
                            decisions.append(clean_line)
                        break
            
            return decisions[:5]  # Limit to top 5 decisions
            
        except Exception as e:
            logger.error(f"Failed to extract decisions: {e}")
            return []
    
    async def _extract_topics(self, transcript_text: str) -> List[str]:
        """
        Extract main topics discussed.
        
        Args:
            transcript_text: Transcript content
            
        Returns:
            List of topics
        """
        try:
            # Simple keyword-based topic extraction
            topics = set()
            
            # Common meeting topics
            topic_keywords = {
                'Budget': ['budget', 'cost', 'expense', 'financial', 'money'],
                'Timeline': ['timeline', 'schedule', 'deadline', 'milestone'],
                'Project': ['project', 'initiative', 'program'],
                'Client': ['client', 'customer', 'user'],
                'Team': ['team', 'staff', 'personnel', 'resources'],
                'Strategy': ['strategy', 'plan', 'approach', 'direction'],
                'Issues': ['issue', 'problem', 'challenge', 'concern'],
                'Goals': ['goal', 'objective', 'target', 'aim'],
                'Performance': ['performance', 'metrics', 'results', 'kpi'],
                'Technology': ['technology', 'system', 'platform', 'tool']
            }
            
            text_lower = transcript_text.lower()
            
            for topic, keywords in topic_keywords.items():
                for keyword in keywords:
                    if keyword in text_lower:
                        topics.add(topic)
                        break
            
            return list(topics)
            
        except Exception as e:
            logger.error(f"Failed to extract topics: {e}")
            return []
    
    def _generate_title(self, 
                       transcript_text: str, 
                       participants: Optional[List[str]] = None) -> str:
        """
        Generate a meeting title based on content.
        
        Args:
            transcript_text: Transcript content
            participants: Meeting participants
            
        Returns:
            Generated meeting title
        """
        try:
            # Look for explicit meeting titles in transcript
            lines = transcript_text.split('\n')[:10]
            
            for line in lines:
                # Look for common title patterns
                if any(keyword in line.lower() for keyword in 
                      ['meeting:', 'call:', 'discussion:', 'review:', 'standup']):
                    return line.strip()
            
            # Generate based on content
            text_lower = transcript_text.lower()
            
            if 'standup' in text_lower or 'daily' in text_lower:
                return 'Daily Standup Meeting'
            elif 'review' in text_lower:
                return 'Review Meeting'
            elif 'planning' in text_lower:
                return 'Planning Meeting'
            elif 'retrospective' in text_lower or 'retro' in text_lower:
                return 'Retrospective Meeting'
            elif participants and len(participants) <= 3:
                return '1:1 Meeting'
            else:
                return f"Team Meeting - {datetime.now().strftime('%Y-%m-%d')}"
                
        except Exception as e:
            logger.error(f"Failed to generate title: {e}")
            return f"Meeting - {datetime.now().strftime('%Y-%m-%d')}"
    
    def _estimate_duration(self, transcript_text: str) -> Optional[str]:
        """
        Estimate meeting duration from transcript.
        
        Args:
            transcript_text: Transcript content
            
        Returns:
            Estimated duration string
        """
        try:
            word_count = len(transcript_text.split())
            # Rough estimate: 150 words per minute
            minutes = max(1, word_count // 150)
            
            if minutes >= 60:
                hours = minutes // 60
                remaining_minutes = minutes % 60
                return f"{hours}h {remaining_minutes}m"
            else:
                return f"{minutes}m"
                
        except Exception as e:
            logger.error(f"Failed to estimate duration: {e}")
            return None
    
    async def test_connection(self) -> bool:
        """
        Test the LLM provider connection.
        
        Returns:
            True if connection successful
        """
        try:
            return await self.llm_provider.test_connection()
        except Exception as e:
            logger.error(f"Summarizer connection test failed: {e}")
            return False
    
    def add_custom_template(self, name: str, template: str):
        """
        Add a custom summary template.
        
        Args:
            name: Template name
            template: Template string with {transcript} placeholder
        """
        if '{transcript}' not in template:
            raise ValueError("Template must contain {transcript} placeholder")
        
        self.templates[name] = template
        logger.info(f"Added custom template: {name}")
    
    def get_available_formats(self) -> List[str]:
        """
        Get list of available summary formats.
        
        Returns:
            List of format names
        """
        return list(self.templates.keys())
    
    async def batch_summarize(self, 
                            transcripts: List[Dict[str, Any]],
                            format_type: str = None) -> List[MeetingSummary]:
        """
        Summarize multiple transcripts in batch.
        
        Args:
            transcripts: List of transcript data dictionaries
            format_type: Summary format to use
            
        Returns:
            List of MeetingSummary objects
        """
        summaries = []
        
        for i, transcript_data in enumerate(transcripts):
            try:
                logger.info(f"Processing transcript {i+1}/{len(transcripts)}")
                
                summary = await self.summarize_transcript(
                    transcript_text=transcript_data.get('content', ''),
                    format_type=format_type,
                    participants=transcript_data.get('participants'),
                    meeting_date=transcript_data.get('date')
                )
                
                summaries.append(summary)
                
                # Small delay to respect rate limits
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to summarize transcript {i+1}: {e}")
                # Continue with other transcripts
                continue
        
        logger.info(f"Completed batch summarization: {len(summaries)}/{len(transcripts)} successful")
        return summaries


# Utility functions
def format_summary_for_export(meeting_summary: MeetingSummary, 
                            format_type: str = 'markdown') -> str:
    """
    Format meeting summary for export.
    
    Args:
        meeting_summary: MeetingSummary object
        format_type: Export format ('markdown', 'plain', 'html')
        
    Returns:
        Formatted summary string
    """
    if format_type == 'markdown':
        return _format_markdown(meeting_summary)
    elif format_type == 'html':
        return _format_html(meeting_summary)
    else:
        return _format_plain(meeting_summary)


def _format_markdown(summary: MeetingSummary) -> str:
    """Format summary as Markdown."""
    md = f"# {summary.title}\n\n"
    md += f"**Date:** {summary.date.strftime('%Y-%m-%d %H:%M')}\n"
    md += f"**Duration:** {summary.duration or 'N/A'}\n"
    md += f"**Participants:** {', '.join(summary.participants)}\n\n"
    
    md += "## Summary\n\n"
    md += f"{summary.summary}\n\n"
    
    if summary.key_decisions:
        md += "## Key Decisions\n\n"
        for decision in summary.key_decisions:
            md += f"- {decision}\n"
        md += "\n"
    
    if summary.action_items:
        md += "## Action Items\n\n"
        for i, item in enumerate(summary.action_items, 1):
            md += f"{i}. **{item.description}**\n"
            if item.assignee:
                md += f"   - Assigned to: {item.assignee}\n"
            if item.due_date:
                md += f"   - Due: {item.due_date.strftime('%Y-%m-%d')}\n"
            md += f"   - Priority: {item.priority}\n\n"
    
    if summary.topics_discussed:
        md += "## Topics Discussed\n\n"
        for topic in summary.topics_discussed:
            md += f"- {topic}\n"
        md += "\n"
    
    return md


def _format_plain(summary: MeetingSummary) -> str:
    """Format summary as plain text."""
    text = f"{summary.title}\n"
    text += "=" * len(summary.title) + "\n\n"
    text += f"Date: {summary.date.strftime('%Y-%m-%d %H:%M')}\n"
    text += f"Duration: {summary.duration or 'N/A'}\n"
    text += f"Participants: {', '.join(summary.participants)}\n\n"
    
    text += "SUMMARY\n-------\n"
    text += f"{summary.summary}\n\n"
    
    if summary.key_decisions:
        text += "KEY DECISIONS\n-------------\n"
        for decision in summary.key_decisions:
            text += f"• {decision}\n"
        text += "\n"
    
    if summary.action_items:
        text += "ACTION ITEMS\n------------\n"
        for i, item in enumerate(summary.action_items, 1):
            text += f"{i}. {item.description}\n"
            if item.assignee:
                text += f"   Assigned to: {item.assignee}\n"
            if item.due_date:
                text += f"   Due: {item.due_date.strftime('%Y-%m-%d')}\n"
            text += f"   Priority: {item.priority}\n\n"
    
    return text


def _format_html(summary: MeetingSummary) -> str:
    """Format summary as HTML."""
    html = f"""<html><head><title>{summary.title}</title></head><body>
    <h1>{summary.title}</h1>
    <p><strong>Date:</strong> {summary.date.strftime('%Y-%m-%d %H:%M')}</p>
    <p><strong>Duration:</strong> {summary.duration or 'N/A'}</p>
    <p><strong>Participants:</strong> {', '.join(summary.participants)}</p>
    
    <h2>Summary</h2>
    <p>{summary.summary}</p>
    """
    
    if summary.key_decisions:
        html += "<h2>Key Decisions</h2><ul>"
        for decision in summary.key_decisions:
            html += f"<li>{decision}</li>"
        html += "</ul>"
    
    if summary.action_items:
        html += "<h2>Action Items</h2><ol>"
        for item in summary.action_items:
            html += f"<li><strong>{item.description}</strong>"
            if item.assignee:
                html += f"<br>Assigned to: {item.assignee}"
            if item.due_date:
                html += f"<br>Due: {item.due_date.strftime('%Y-%m-%d')}"
            html += f"<br>Priority: {item.priority}</li>"
        html += "</ol>"
    
    html += "</body></html>"
    return html


if __name__ == "__main__":
    # Test the summarizer
    async def test_summarizer():
        summarizer = MeetingSummarizer()
        
        test_transcript = """
        John: Good morning everyone, let's start our project review meeting.
        Sarah: Thanks John. I wanted to update everyone on the budget status.
        John: Great, go ahead Sarah.
        Sarah: We're currently 15% over budget due to the additional requirements.
        Mike: I think we need to prioritize the core features and push some items to phase 2.
        John: Agreed. Let's decide on the must-have features today.
        Sarah: I'll prepare a revised budget by Friday.
        """
        
        try:
            summary = await summarizer.summarize_transcript(
                test_transcript,
                participants=["John", "Sarah", "Mike"]
            )
            print(f"Title: {summary.title}")
            print(f"Summary: {summary.summary[:100]}...")
            print(f"Action Items: {len(summary.action_items)}")
        except Exception as e:
            print(f"Test failed: {e}")
    
    # Uncomment to run test
    # asyncio.run(test_summarizer())