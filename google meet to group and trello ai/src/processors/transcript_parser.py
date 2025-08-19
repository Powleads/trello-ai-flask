"""
Transcript Parser

Handles parsing and processing of meeting transcript files from various sources
like Google Meet, Zoom, Microsoft Teams, etc.
"""

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)

# Regex patterns for different transcript formats
GOOGLE_MEET_PATTERNS = {
    'speaker': r'^([^:]+):\s*(.+)$',
    'timestamp': r'(\d{1,2}:\d{2}:\d{2})',
    'participant_joined': r'(.+)\s+joined\s+the\s+meeting',
    'participant_left': r'(.+)\s+left\s+the\s+meeting'
}

ZOOM_PATTERNS = {
    'speaker': r'^(\d{2}:\d{2}:\d{2})\s+([^:]+):\s*(.+)$',
    'timestamp': r'^(\d{2}:\d{2}:\d{2})',
    'participant_action': r'^(\d{2}:\d{2}:\d{2})\s+(.+)\s+(joined|left)'
}

TEAMS_PATTERNS = {
    'speaker': r'^(\d{1,2}:\d{2}:\d{2}\s+[AP]M)\s+([^:]+):\s*(.+)$',
    'timestamp': r'^(\d{1,2}:\d{2}:\d{2}\s+[AP]M)',
    'participant_action': r'^(\d{1,2}:\d{2}:\d{2}\s+[AP]M)\s+(.+)\s+(joined|left)\s+the\s+meeting'
}


class TranscriptSegment:
    """Represents a segment of transcript with speaker and content."""
    
    def __init__(self, 
                 speaker: str, 
                 content: str, 
                 timestamp: Optional[str] = None,
                 start_time: Optional[datetime] = None):
        self.speaker = speaker.strip()
        self.content = content.strip()
        self.timestamp = timestamp
        self.start_time = start_time
        self.word_count = len(content.split())
    
    def __repr__(self):
        return f"TranscriptSegment(speaker='{self.speaker}', content='{self.content[:50]}...', timestamp='{self.timestamp}')"


class TranscriptParser:
    """
    Parses meeting transcripts from various platforms and formats.
    
    Supports Google Meet, Zoom, Microsoft Teams, and generic formats.
    """
    
    def __init__(self):
        self.patterns = {
            'google_meet': GOOGLE_MEET_PATTERNS,
            'zoom': ZOOM_PATTERNS,
            'teams': TEAMS_PATTERNS
        }
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a transcript file and extract structured data.
        
        Args:
            file_path: Path to transcript file
            
        Returns:
            Dictionary containing parsed transcript data
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Transcript file not found: {file_path}")
        
        # Read file content
        try:
            content = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # Try with different encoding
            content = path.read_text(encoding='latin-1')
        
        # Detect transcript format
        format_type = self._detect_format(content)
        logger.info(f"Detected transcript format: {format_type}")
        
        # Parse based on detected format
        if format_type == 'google_meet':
            return self._parse_google_meet(content, path)
        elif format_type == 'zoom':
            return self._parse_zoom(content, path)
        elif format_type == 'teams':
            return self._parse_teams(content, path)
        else:
            return self._parse_generic(content, path)
    
    def _detect_format(self, content: str) -> str:
        """
        Detect the transcript format based on content patterns.
        
        Args:
            content: Transcript content
            
        Returns:
            Detected format type
        """
        lines = content.split('\n')[:20]  # Check first 20 lines
        
        # Google Meet detection
        google_indicators = [
            'joined the meeting',
            'left the meeting',
            # Pattern: "Name: message"
            len([line for line in lines if re.match(r'^[^:]+:\s*.+$', line)]) > 3
        ]
        
        # Zoom detection
        zoom_indicators = [
            # Pattern: "HH:MM:SS Name: message"
            len([line for line in lines if re.match(r'^\d{2}:\d{2}:\d{2}\s+[^:]+:', line)]) > 3,
            'GMT' in content,
            'UTC' in content
        ]
        
        # Teams detection
        teams_indicators = [
            # Pattern: "HH:MM:SS AM/PM Name: message"
            len([line for line in lines if re.match(r'^\d{1,2}:\d{2}:\d{2}\s+[AP]M\s+[^:]+:', line)]) > 2,
            'Microsoft Teams' in content,
            'joined the meeting' in content and ('AM' in content or 'PM' in content)
        ]\n        \n        if sum(zoom_indicators) >= 2:\n            return 'zoom'\n        elif sum(teams_indicators) >= 2:\n            return 'teams'\n        elif sum(google_indicators) >= 2:\n            return 'google_meet'\n        else:\n            return 'generic'\n    \n    def _parse_google_meet(self, content: str, file_path: Path) -> Dict[str, Any]:\n        \"\"\"\n        Parse Google Meet transcript format.\n        \n        Args:\n            content: Transcript content\n            file_path: Path to transcript file\n            \n        Returns:\n            Parsed transcript data\n        \"\"\"\n        lines = content.split('\\n')\n        segments = []\n        participants = set()\n        meeting_events = []\n        \n        current_speaker = None\n        current_content = []\n        \n        for line in lines:\n            line = line.strip()\n            if not line:\n                continue\n            \n            # Check for speaker pattern\n            speaker_match = re.match(GOOGLE_MEET_PATTERNS['speaker'], line)\n            if speaker_match:\n                # Save previous segment\n                if current_speaker and current_content:\n                    segments.append(TranscriptSegment(\n                        speaker=current_speaker,\n                        content=' '.join(current_content)\n                    ))\n                \n                # Start new segment\n                current_speaker = speaker_match.group(1)\n                current_content = [speaker_match.group(2)]\n                participants.add(current_speaker)\n            \n            # Check for meeting events\n            elif 'joined the meeting' in line:\n                name = line.replace('joined the meeting', '').strip()\n                participants.add(name)\n                meeting_events.append({\n                    'type': 'join',\n                    'participant': name,\n                    'text': line\n                })\n            \n            elif 'left the meeting' in line:\n                name = line.replace('left the meeting', '').strip()\n                meeting_events.append({\n                    'type': 'leave',\n                    'participant': name,\n                    'text': line\n                })\n            \n            else:\n                # Continue current speaker's content\n                if current_speaker and line:\n                    current_content.append(line)\n        \n        # Add final segment\n        if current_speaker and current_content:\n            segments.append(TranscriptSegment(\n                speaker=current_speaker,\n                content=' '.join(current_content)\n            ))\n        \n        return {\n            'format': 'google_meet',\n            'file_path': str(file_path),\n            'segments': segments,\n            'participants': list(participants),\n            'meeting_events': meeting_events,\n            'total_segments': len(segments),\n            'estimated_duration': self._estimate_duration(segments),\n            'word_count': sum(segment.word_count for segment in segments)\n        }\n    \n    def _parse_zoom(self, content: str, file_path: Path) -> Dict[str, Any]:\n        \"\"\"\n        Parse Zoom transcript format.\n        \n        Args:\n            content: Transcript content\n            file_path: Path to transcript file\n            \n        Returns:\n            Parsed transcript data\n        \"\"\"\n        lines = content.split('\\n')\n        segments = []\n        participants = set()\n        meeting_events = []\n        \n        for line in lines:\n            line = line.strip()\n            if not line:\n                continue\n            \n            # Check for speaker with timestamp\n            speaker_match = re.match(ZOOM_PATTERNS['speaker'], line)\n            if speaker_match:\n                timestamp = speaker_match.group(1)\n                speaker = speaker_match.group(2)\n                content_text = speaker_match.group(3)\n                \n                segments.append(TranscriptSegment(\n                    speaker=speaker,\n                    content=content_text,\n                    timestamp=timestamp\n                ))\n                participants.add(speaker)\n            \n            # Check for participant actions\n            elif re.search(r'(joined|left)', line):\n                action_match = re.match(ZOOM_PATTERNS['participant_action'], line)\n                if action_match:\n                    timestamp = action_match.group(1)\n                    participant = action_match.group(2)\n                    action = action_match.group(3)\n                    \n                    participants.add(participant)\n                    meeting_events.append({\n                        'type': action,\n                        'participant': participant,\n                        'timestamp': timestamp,\n                        'text': line\n                    })\n        \n        return {\n            'format': 'zoom',\n            'file_path': str(file_path),\n            'segments': segments,\n            'participants': list(participants),\n            'meeting_events': meeting_events,\n            'total_segments': len(segments),\n            'estimated_duration': self._estimate_duration(segments),\n            'word_count': sum(segment.word_count for segment in segments)\n        }\n    \n    def _parse_teams(self, content: str, file_path: Path) -> Dict[str, Any]:\n        \"\"\"\n        Parse Microsoft Teams transcript format.\n        \n        Args:\n            content: Transcript content\n            file_path: Path to transcript file\n            \n        Returns:\n            Parsed transcript data\n        \"\"\"\n        lines = content.split('\\n')\n        segments = []\n        participants = set()\n        meeting_events = []\n        \n        for line in lines:\n            line = line.strip()\n            if not line:\n                continue\n            \n            # Check for speaker with timestamp\n            speaker_match = re.match(TEAMS_PATTERNS['speaker'], line)\n            if speaker_match:\n                timestamp = speaker_match.group(1)\n                speaker = speaker_match.group(2)\n                content_text = speaker_match.group(3)\n                \n                segments.append(TranscriptSegment(\n                    speaker=speaker,\n                    content=content_text,\n                    timestamp=timestamp\n                ))\n                participants.add(speaker)\n            \n            # Check for participant actions\n            elif 'joined the meeting' in line or 'left the meeting' in line:\n                action_match = re.match(TEAMS_PATTERNS['participant_action'], line)\n                if action_match:\n                    timestamp = action_match.group(1)\n                    participant = action_match.group(2)\n                    action = action_match.group(3)\n                    \n                    participants.add(participant)\n                    meeting_events.append({\n                        'type': action,\n                        'participant': participant,\n                        'timestamp': timestamp,\n                        'text': line\n                    })\n        \n        return {\n            'format': 'teams',\n            'file_path': str(file_path),\n            'segments': segments,\n            'participants': list(participants),\n            'meeting_events': meeting_events,\n            'total_segments': len(segments),\n            'estimated_duration': self._estimate_duration(segments),\n            'word_count': sum(segment.word_count for segment in segments)\n        }\n    \n    def _parse_generic(self, content: str, file_path: Path) -> Dict[str, Any]:\n        \"\"\"\n        Parse generic transcript format (fallback).\n        \n        Args:\n            content: Transcript content\n            file_path: Path to transcript file\n            \n        Returns:\n            Parsed transcript data\n        \"\"\"\n        lines = content.split('\\n')\n        segments = []\n        participants = set()\n        \n        current_speaker = 'Unknown Speaker'\n        current_content = []\n        \n        for line in lines:\n            line = line.strip()\n            if not line:\n                continue\n            \n            # Try to detect speaker changes with simple patterns\n            # Pattern: \"Name:\" or \"Name said:\" or \"[Name]\"\n            speaker_patterns = [\n                r'^([A-Za-z\\s]+):(.+)$',\n                r'^([A-Za-z\\s]+)\\ssaid:(.+)$',\n                r'^\\[([A-Za-z\\s]+)\\](.+)$'\n            ]\n            \n            speaker_found = False\n            for pattern in speaker_patterns:\n                match = re.match(pattern, line)\n                if match:\n                    # Save previous segment\n                    if current_content:\n                        segments.append(TranscriptSegment(\n                            speaker=current_speaker,\n                            content=' '.join(current_content)\n                        ))\n                    \n                    # Start new segment\n                    current_speaker = match.group(1).strip()\n                    current_content = [match.group(2).strip()]\n                    participants.add(current_speaker)\n                    speaker_found = True\n                    break\n            \n            if not speaker_found:\n                # Add to current content\n                current_content.append(line)\n        \n        # Add final segment\n        if current_content:\n            segments.append(TranscriptSegment(\n                speaker=current_speaker,\n                content=' '.join(current_content)\n            ))\n        \n        return {\n            'format': 'generic',\n            'file_path': str(file_path),\n            'segments': segments,\n            'participants': list(participants),\n            'meeting_events': [],\n            'total_segments': len(segments),\n            'estimated_duration': self._estimate_duration(segments),\n            'word_count': sum(segment.word_count for segment in segments)\n        }\n    \n    def _estimate_duration(self, segments: List[TranscriptSegment]) -> str:\n        \"\"\"\n        Estimate meeting duration based on content.\n        \n        Args:\n            segments: List of transcript segments\n            \n        Returns:\n            Estimated duration string\n        \"\"\"\n        if not segments:\n            return \"Unknown\"\n        \n        # Rough estimation: 150 words per minute average speaking rate\n        total_words = sum(segment.word_count for segment in segments)\n        estimated_minutes = max(1, total_words // 150)\n        \n        hours = estimated_minutes // 60\n        minutes = estimated_minutes % 60\n        \n        if hours > 0:\n            return f\"{hours}h {minutes}m\"\n        else:\n            return f\"{minutes}m\"\n    \n    def get_speaker_stats(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:\n        \"\"\"\n        Get statistics about speaker participation.\n        \n        Args:\n            parsed_data: Parsed transcript data\n            \n        Returns:\n            Speaker statistics\n        \"\"\"\n        segments = parsed_data.get('segments', [])\n        if not segments:\n            return {}\n        \n        speaker_stats = {}\n        total_words = 0\n        \n        for segment in segments:\n            speaker = segment.speaker\n            if speaker not in speaker_stats:\n                speaker_stats[speaker] = {\n                    'segments': 0,\n                    'word_count': 0,\n                    'percentage': 0\n                }\n            \n            speaker_stats[speaker]['segments'] += 1\n            speaker_stats[speaker]['word_count'] += segment.word_count\n            total_words += segment.word_count\n        \n        # Calculate percentages\n        for speaker in speaker_stats:\n            if total_words > 0:\n                speaker_stats[speaker]['percentage'] = round(\n                    (speaker_stats[speaker]['word_count'] / total_words) * 100, 1\n                )\n        \n        return speaker_stats\n    \n    def extract_text(self, parsed_data: Dict[str, Any]) -> str:\n        \"\"\"\n        Extract plain text from parsed transcript data.\n        \n        Args:\n            parsed_data: Parsed transcript data\n            \n        Returns:\n            Plain text transcript\n        \"\"\"\n        segments = parsed_data.get('segments', [])\n        \n        text_parts = []\n        for segment in segments:\n            text_parts.append(f\"{segment.speaker}: {segment.content}\")\n        \n        return '\\n'.join(text_parts)\n    \n    def search_content(self, \n                      parsed_data: Dict[str, Any], \n                      query: str,\n                      case_sensitive: bool = False) -> List[Dict[str, Any]]:\n        \"\"\"\n        Search for specific content in the transcript.\n        \n        Args:\n            parsed_data: Parsed transcript data\n            query: Search query\n            case_sensitive: Whether search is case sensitive\n            \n        Returns:\n            List of matching segments with context\n        \"\"\"\n        segments = parsed_data.get('segments', [])\n        results = []\n        \n        search_query = query if case_sensitive else query.lower()\n        \n        for i, segment in enumerate(segments):\n            content = segment.content if case_sensitive else segment.content.lower()\n            \n            if search_query in content:\n                results.append({\n                    'segment_index': i,\n                    'speaker': segment.speaker,\n                    'content': segment.content,\n                    'timestamp': segment.timestamp,\n                    'context_before': segments[i-1].content if i > 0 else None,\n                    'context_after': segments[i+1].content if i < len(segments)-1 else None\n                })\n        \n        return results\n\n\nif __name__ == \"__main__\":\n    # Test the transcript parser\n    parser = TranscriptParser()\n    \n    # Example usage\n    print(\"Transcript Parser Test\")\n    print(\"Create a test transcript file to see parsing in action\")