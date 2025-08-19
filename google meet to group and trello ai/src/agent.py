"""
Meeting Automation Agent

Core automation engine that orchestrates transcript processing, AI analysis,
and distribution across multiple platforms.
"""

import asyncio
import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import logging

from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ActionItem(BaseModel):
    """Represents an action item extracted from a meeting transcript."""
    
    description: str = Field(..., description="Description of the action item")
    assignee: Optional[str] = Field(None, description="Person assigned to the task")
    due_date: Optional[datetime] = Field(None, description="Due date for the task")
    priority: str = Field("medium", description="Priority level: low, medium, high, urgent")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    
    @validator('priority')
    def validate_priority(cls, v):
        if v.lower() not in ['low', 'medium', 'high', 'urgent']:
            raise ValueError('Priority must be one of: low, medium, high, urgent')
        return v.lower()


class MeetingSummary(BaseModel):
    """Represents a processed meeting summary with metadata."""
    
    title: str = Field(..., description="Meeting title or subject")
    date: datetime = Field(..., description="Meeting date and time")
    participants: List[str] = Field(default_factory=list, description="List of participants")
    duration: Optional[str] = Field(None, description="Meeting duration")
    summary: str = Field(..., description="AI-generated meeting summary")
    key_decisions: List[str] = Field(default_factory=list, description="Key decisions made")
    action_items: List[ActionItem] = Field(default_factory=list, description="Extracted action items")
    topics_discussed: List[str] = Field(default_factory=list, description="Main topics covered")
    next_meeting: Optional[datetime] = Field(None, description="Next scheduled meeting")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TranscriptData(BaseModel):
    """Raw transcript data with metadata."""
    
    file_path: str = Field(..., description="Path to the transcript file")
    content: str = Field(..., description="Raw transcript content")
    file_size: int = Field(..., description="File size in bytes")
    created_at: datetime = Field(..., description="File creation timestamp")
    source: str = Field("google_meet", description="Source of the transcript")
    language: str = Field("en", description="Language of the transcript")
    
    @validator('source')
    def validate_source(cls, v):
        allowed_sources = ['google_meet', 'zoom', 'teams', 'manual']
        if v not in allowed_sources:
            raise ValueError(f'Source must be one of: {allowed_sources}')
        return v


class ProcessingResult(BaseModel):
    """Result of transcript processing pipeline."""
    
    transcript_data: TranscriptData
    meeting_summary: MeetingSummary
    processing_time: float = Field(..., description="Processing time in seconds")
    whatsapp_sent: bool = Field(False, description="Whether WhatsApp message was sent")
    trello_cards_created: List[str] = Field(default_factory=list, description="IDs of created Trello cards")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")
    
    @property
    def summary(self) -> str:
        """Get the formatted summary text."""
        return self.meeting_summary.summary
    
    @property
    def action_items(self) -> List[ActionItem]:
        """Get the extracted action items."""
        return self.meeting_summary.action_items


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate_summary(self, transcript: str) -> str:
        """Generate a meeting summary from transcript text."""
        pass
    
    @abstractmethod
    async def extract_action_items(self, transcript: str) -> List[Dict[str, Any]]:
        """Extract action items from transcript text."""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test the connection to the LLM provider."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
    
    async def generate_summary(self, transcript: str) -> str:
        """Generate summary using OpenAI GPT."""
        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=self.api_key)
            
            prompt = f"""
            Please analyze this meeting transcript and provide a comprehensive summary including:
            1. Main topics discussed
            2. Key decisions made
            3. Important points raised
            4. Overall outcomes
            
            Transcript:
            {transcript}
            
            Summary:
            """
            
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert meeting analyst. Provide clear, concise summaries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI summary generation failed: {e}")
            raise
    
    async def extract_action_items(self, transcript: str) -> List[Dict[str, Any]]:
        """Extract action items using OpenAI GPT."""
        try:
            from openai import AsyncOpenAI
            import json
            
            client = AsyncOpenAI(api_key=self.api_key)
            
            prompt = f"""
            Analyze this meeting transcript and extract all action items. For each action item, provide:
            - description: Clear description of the task
            - assignee: Person assigned (if mentioned)
            - priority: low, medium, high, or urgent
            - due_date: Any mentioned deadline (in ISO format if possible)
            
            Return as JSON array.
            
            Transcript:
            {transcript}
            """
            
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert at extracting action items. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.1
            )
            
            return json.loads(response.choices[0].message.content.strip())
            
        except Exception as e:
            logger.error(f"OpenAI action item extraction failed: {e}")
            return []
    
    async def test_connection(self) -> bool:
        """Test OpenAI API connection."""
        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=self.api_key)
            
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            logger.error(f"OpenAI connection test failed: {e}")
            return False


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('CLAUDE_API_KEY')
        if not self.api_key:
            raise ValueError("Claude API key not provided")
    
    async def generate_summary(self, transcript: str) -> str:
        """Generate summary using Claude."""
        # Implementation would use Anthropic's Claude API
        # This is a placeholder for the actual implementation
        return "Claude summary implementation needed"
    
    async def extract_action_items(self, transcript: str) -> List[Dict[str, Any]]:
        """Extract action items using Claude."""
        # Implementation would use Anthropic's Claude API
        return []
    
    async def test_connection(self) -> bool:
        """Test Claude API connection."""
        return False


class IntegrationTool(ABC):
    """Abstract base class for integration tools."""
    
    @abstractmethod
    async def process(self, data: Any) -> Any:
        """Process data using this integration."""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test the connection to the service."""
        pass


class MeetingAutomationAgent:
    """
    Main automation agent that orchestrates the entire workflow.
    
    Uses dependency injection pattern for extensibility and testability.
    """
    
    def __init__(self, 
                 llm_provider: Optional[LLMProvider] = None,
                 integrations: Optional[Dict[str, IntegrationTool]] = None):
        """
        Initialize the automation agent.
        
        Args:
            llm_provider: LLM provider for AI processing
            integrations: Dictionary of integration tools
        """
        self.llm_provider = llm_provider or self._get_default_llm_provider()
        self.integrations = integrations or {}
        
        # Initialize default integrations if not provided
        if not self.integrations:
            self._initialize_integrations()
    
    def _get_default_llm_provider(self) -> LLMProvider:
        """Get the default LLM provider based on available API keys."""
        if os.getenv('OPENAI_API_KEY'):
            return OpenAIProvider()
        elif os.getenv('CLAUDE_API_KEY'):
            return ClaudeProvider()
        else:
            raise ValueError("No LLM provider API key found in environment")
    
    def _initialize_integrations(self):
        """Initialize integration tools."""
        try:
            from integrations.google_drive import GoogleDriveClient
            from integrations.green_api import WhatsAppClient
            from integrations.trello import TrelloClient
            
            self.integrations = {
                'google_drive': GoogleDriveClient(),
                'whatsapp': WhatsAppClient(),
                'trello': TrelloClient()
            }
        except ImportError as e:
            logger.warning(f"Could not import integrations: {e}")
    
    async def process_transcript(self, 
                               file_path: str,
                               output_format: str = 'standard',
                               send_whatsapp: bool = True,
                               create_trello: bool = True) -> ProcessingResult:
        """
        Process a single transcript file through the complete pipeline.
        
        Args:
            file_path: Path to the transcript file
            output_format: Format for the output summary
            send_whatsapp: Whether to send summary via WhatsApp
            create_trello: Whether to create Trello cards for action items
            
        Returns:
            ProcessingResult with all outputs and metadata
        """
        start_time = asyncio.get_event_loop().time()
        errors = []
        
        try:
            # Load and parse transcript
            transcript_data = await self._load_transcript(file_path)
            logger.info(f"Loaded transcript: {transcript_data.file_path}")
            
            # Process with AI
            summary_text = await self.llm_provider.generate_summary(transcript_data.content)
            action_items_data = await self.llm_provider.extract_action_items(transcript_data.content)
            
            # Convert action items to Pydantic models
            action_items = []
            for item_data in action_items_data:
                try:
                    action_item = ActionItem(**item_data)
                    action_items.append(action_item)
                except Exception as e:
                    logger.warning(f"Invalid action item data: {e}")
                    errors.append(f"Invalid action item: {e}")
            
            # Create meeting summary
            meeting_summary = MeetingSummary(
                title=f"Meeting - {datetime.now().strftime('%Y-%m-%d')}",
                date=transcript_data.created_at,
                summary=summary_text,
                action_items=action_items,
                participants=self._extract_participants(transcript_data.content),
                topics_discussed=self._extract_topics(transcript_data.content)
            )
            
            # Distribution
            whatsapp_sent = False
            trello_cards = []
            
            if send_whatsapp and 'whatsapp' in self.integrations:
                try:
                    await self.integrations['whatsapp'].send_summary(meeting_summary)
                    whatsapp_sent = True
                    logger.info("Summary sent via WhatsApp")
                except Exception as e:
                    errors.append(f"WhatsApp sending failed: {e}")
                    logger.error(f"WhatsApp error: {e}")
            
            if create_trello and 'trello' in self.integrations:
                try:
                    # Find existing Trello cards mentioned in meeting and add comments
                    trello_result = await self.integrations['trello'].find_and_update_cards_from_meeting(meeting_summary)
                    trello_cards = [card['card_id'] for card in trello_result.get('updated_cards', [])]
                    logger.info(f"Updated {trello_result.get('cards_updated', 0)} Trello cards with meeting notes")
                except Exception as e:
                    errors.append(f"Trello card update failed: {e}")
                    logger.error(f"Trello error: {e}")
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return ProcessingResult(
                transcript_data=transcript_data,
                meeting_summary=meeting_summary,
                processing_time=processing_time,
                whatsapp_sent=whatsapp_sent,
                trello_cards_created=trello_cards,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            raise
    
    async def watch_folder(self, 
                          folder_path: str, 
                          interval: int = 30,
                          recursive: bool = True):
        """
        Monitor a folder for new transcript files and process them automatically.
        
        Args:
            folder_path: Path to monitor
            interval: Polling interval in seconds
            recursive: Whether to monitor subdirectories
        """
        folder = Path(folder_path)
        processed_files = set()
        
        logger.info(f"Starting folder monitoring: {folder_path}")
        
        while True:
            try:
                # Find new transcript files
                pattern = "**/*.txt" if recursive else "*.txt"
                current_files = set(folder.glob(pattern))
                new_files = current_files - processed_files
                
                for file_path in new_files:
                    try:
                        logger.info(f"Processing new file: {file_path}")
                        result = await self.process_transcript(str(file_path))
                        processed_files.add(file_path)
                        logger.info(f"Successfully processed: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to process {file_path}: {e}")
                
                await asyncio.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("Folder monitoring stopped")
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(interval)
    
    async def _load_transcript(self, file_path: str) -> TranscriptData:
        """Load transcript file and create TranscriptData object."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Transcript file not found: {file_path}")
        
        content = path.read_text(encoding='utf-8')
        file_stats = path.stat()
        
        return TranscriptData(
            file_path=str(path.absolute()),
            content=content,
            file_size=file_stats.st_size,
            created_at=datetime.fromtimestamp(file_stats.st_ctime),
            source="google_meet"  # Default, could be detected from content
        )
    
    def _extract_participants(self, transcript_content: str) -> List[str]:
        """Extract participant names from transcript content."""
        # Simple implementation - look for speaker patterns
        participants = set()
        lines = transcript_content.split('\n')
        
        for line in lines:
            # Look for patterns like "John Doe:" or "Speaker 1:"
            if ':' in line:
                speaker = line.split(':')[0].strip()
                if len(speaker) < 50 and speaker.replace(' ', '').isalnum():
                    participants.add(speaker)
        
        return list(participants)
    
    def _extract_topics(self, transcript_content: str) -> List[str]:
        """Extract main topics from transcript content."""
        # Simple keyword-based topic extraction
        # In production, this could use more sophisticated NLP
        topics = []
        
        common_keywords = [
            'project', 'budget', 'timeline', 'deadline', 'milestone',
            'client', 'customer', 'requirements', 'features', 'issues',
            'goals', 'objectives', 'strategy', 'planning', 'review'
        ]
        
        content_lower = transcript_content.lower()
        for keyword in common_keywords:
            if keyword in content_lower:
                topics.append(keyword.title())
        
        return topics[:10]  # Limit to top 10 topics