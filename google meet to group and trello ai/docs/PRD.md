# Meeting Automation Tool - Product Requirements Document

## Overview

The Meeting Automation Tool is a comprehensive solution that monitors Google Drive for meeting transcripts, processes them using AI to generate summaries, extracts action items, and automatically distributes results via WhatsApp and Trello.

## Core Features

### 1. Transcript Monitoring
- Monitor Google Drive folders for new meeting transcript files
- Support for Google Meet transcript format
- Real-time processing using webhook notifications
- Automatic file download and parsing

### 2. AI-Powered Analysis
- Generate intelligent meeting summaries using LLM providers (OpenAI, Claude)
- Extract key decisions and action items
- Identify speakers and their contributions
- Classify discussion topics and importance levels

### 3. WhatsApp Distribution
- Send formatted summaries to WhatsApp groups using Green API
- Support for rich text formatting and attachments
- Rate limiting and message queuing
- Group management and member notifications

### 4. Trello Integration
- Find existing Trello cards mentioned in meeting discussions
- Add meeting notes and context as comments to relevant cards
- Intelligent card matching using fuzzy text matching
- Link related decisions and action items to existing work

## Technical Architecture

### Core Components

#### 1. CLI Interface (`src/cli.py`)
- Click-based command-line interface
- Commands: `process`, `watch`, `test`, `setup`
- Rich terminal output for better user experience
- Interactive configuration wizard

#### 2. Meeting Automation Agent (`src/agent.py`)
- Central orchestration component
- Dependency injection pattern for integrations
- Async processing pipeline
- Tool pattern for extensible integrations

#### 3. Data Models (`src/models/`)
- Pydantic models for type safety
- MeetingSummary, ActionItem, TranscriptData
- Validation and serialization

#### 4. Integration Layer (`src/integrations/`)
- Google Drive API client with OAuth2
- Green API WhatsApp client
- Trello API client
- Standardized client interface

#### 5. Processing Pipeline (`src/processors/`)
- Transcript parsing and speaker identification
- LLM-based summarization
- NLP action item extraction
- Priority and assignee classification

### API Integrations

#### Google Drive API
- **Purpose**: Monitor and download meeting transcripts
- **Authentication**: OAuth2 with service account support
- **Features**: Push notifications, file watching, metadata extraction
- **Rate Limits**: 1000 requests per 100 seconds per user

#### Green API (WhatsApp)
- **Purpose**: Send meeting summaries to WhatsApp groups
- **Authentication**: Instance ID and API token
- **Features**: Rich text formatting, file attachments, group management
- **Rate Limits**: 200 messages per minute

#### Trello API
- **Purpose**: Find existing cards and add meeting discussion comments
- **Authentication**: API key and OAuth token
- **Features**: Card search, comment addition, context linking, board management
- **Rate Limits**: 300 requests per 10 seconds

#### OpenAI/Claude API
- **Purpose**: Generate summaries and extract insights
- **Authentication**: API keys
- **Features**: Text completion, function calling, structured outputs
- **Rate Limits**: Varies by model and tier

### Data Flow

1. **File Detection**: Google Drive webhook triggers on new transcript upload
2. **Download & Parse**: Transcript downloaded and parsed for structure
3. **AI Processing**: LLM generates summary and extracts action items
4. **Distribution**: Summary sent via WhatsApp, tasks created in Trello
5. **Logging**: All activities logged for audit and debugging

### Security Considerations

- OAuth2 flow for Google Drive authentication
- Secure storage of API credentials using environment variables
- Rate limiting to prevent API abuse
- Input validation and sanitization
- Encrypted webhook endpoints

### Scalability & Performance

- Async processing for I/O operations
- Redis for caching and message queuing
- PostgreSQL for persistent data storage
- Docker containerization for easy deployment
- Horizontal scaling with Celery workers

## Implementation Details

### Phase 1: Core Infrastructure
- Basic CLI interface
- Google Drive monitoring
- Simple transcript parsing
- Database schema setup

### Phase 2: AI Integration
- LLM provider integration
- Summary generation
- Action item extraction
- Quality metrics and validation

### Phase 3: Distribution
- WhatsApp integration via Green API
- Trello card creation
- Duplicate detection
- User preference management

### Phase 4: Advanced Features
- Multi-language support
- Custom templates
- Analytics dashboard
- Webhook management UI

## Success Metrics

- **Processing Speed**: < 2 minutes from transcript upload to distribution
- **Accuracy**: > 95% action item extraction accuracy
- **Reliability**: 99.9% uptime for monitoring service
- **User Satisfaction**: Positive feedback from team productivity improvements

## Risk Mitigation

- **API Rate Limits**: Implement exponential backoff and queuing
- **Service Downtime**: Circuit breaker pattern and fallback mechanisms
- **Data Privacy**: End-to-end encryption and access controls
- **Cost Management**: Usage monitoring and budget alerts

## Future Enhancements

- Integration with Slack, Microsoft Teams
- Video/audio transcript processing
- Real-time meeting participation
- Custom workflow builders
- Mobile application
- Advanced analytics and reporting