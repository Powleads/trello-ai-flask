# Meeting Automation Tool

An intelligent automation system that monitors Google Drive for meeting transcripts, generates AI-powered summaries, and distributes action items via WhatsApp and Trello.

## Features

- 🎤 **Automatic Transcript Processing**: Monitors Google Drive folders for new meeting transcripts
- 🤖 **AI-Powered Summaries**: Generates intelligent summaries using OpenAI or Claude
- 📱 **WhatsApp Integration**: Sends formatted summaries to groups via Green API
- 📋 **Trello Card Updates**: Finds existing cards mentioned in meetings and adds discussion notes as comments
- 🚀 **CLI Interface**: Rich command-line interface with progress tracking
- 🔄 **Real-time Monitoring**: Push notifications for instant processing
- 🎯 **Smart Extraction**: NLP-based action item and decision extraction

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd meeting-automation-tool

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Copy the environment template and configure your API credentials:

```bash
cp .env.example .env
```

Edit `.env` with your API credentials:

```env
# Google Drive API
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Green API (WhatsApp)
GREEN_API_INSTANCE_ID=your_instance_id
GREEN_API_TOKEN=your_api_token

# Trello API
TRELLO_API_KEY=your_trello_api_key
TRELLO_TOKEN=your_trello_token

# AI Providers
OPENAI_API_KEY=your_openai_api_key

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/meetingdb
REDIS_URL=redis://localhost:6379
```

### 3. Initial Setup

Run the interactive setup wizard:

```bash
python src/cli.py setup
```

### 4. Test Connections

Verify all integrations are working:

```bash
python src/cli.py test --service all
```

## Usage

### Processing Individual Transcripts

```bash
# Process a single transcript file
python src/cli.py process --file path/to/transcript.txt

# Process with custom output format
python src/cli.py process --file transcript.txt --format detailed
```

### Monitoring Folders

```bash
# Start monitoring a folder for new transcripts
python src/cli.py watch --folder ./transcripts

# Monitor Google Drive folder
python src/cli.py watch --drive-folder "Meeting Transcripts"
```

### Testing Services

```bash
# Test all services
python src/cli.py test --service all

# Test specific services
python src/cli.py test --service google-drive
python src/cli.py test --service whatsapp
python src/cli.py test --service trello
```

## Project Structure

```
meeting-automation-tool/
├── docs/
│   └── PRD.md                          # Product Requirements Document
├── src/
│   ├── api/                            # FastAPI web interface
│   ├── integrations/
│   │   ├── google_drive.py             # Google Drive API client
│   │   ├── green_api.py                # WhatsApp Green API client
│   │   └── trello.py                   # Trello API client
│   ├── processors/
│   │   ├── transcript_parser.py        # Transcript parsing logic
│   │   ├── summarizer.py               # AI summarization
│   │   └── task_extractor.py           # Action item extraction
│   ├── models/                         # Pydantic data models
│   ├── utils/                          # Utility functions
│   ├── cli.py                          # Command-line interface
│   └── agent.py                        # Main automation agent
├── tests/
│   ├── unit/                           # Unit tests
│   └── integration/                    # Integration tests
├── scripts/
│   ├── setup_google_auth.py            # Google OAuth setup
│   └── test_integration.py             # Integration testing
├── .env.example                        # Environment template
├── requirements.txt                    # Python dependencies
├── Makefile                           # Common commands
└── docker-compose.yml                 # Local development environment
```

## Configuration Guide

### Google Drive API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Drive API
4. Create credentials (OAuth 2.0 Client ID)
5. Download the credentials JSON file
6. Run the OAuth setup script:

```bash
python scripts/setup_google_auth.py
```

### Green API (WhatsApp) Setup

1. Sign up at [Green API](https://green-api.com/)
2. Create an instance and get your Instance ID and API Token
3. Configure your WhatsApp number
4. Add the credentials to your `.env` file

### Trello API Setup

1. Go to [Trello Developer Portal](https://trello.com/app-key)
2. Get your API Key
3. Generate a token with read/write permissions
4. Add credentials to your `.env` file

## Advanced Usage

### Custom Templates

Create custom summary templates by modifying the processor configuration:

```python
# In src/processors/summarizer.py
CUSTOM_TEMPLATE = """
## Meeting Summary - {date}

**Participants**: {participants}

**Key Decisions**:
{decisions}

**Action Items**:
{action_items}

**Next Steps**:
{next_steps}
"""
```

### Webhook Configuration

For real-time processing, configure Google Drive webhooks:

```bash
# Set up webhook endpoint
python src/cli.py setup-webhook --url https://your-domain.com/webhook
```

### Batch Processing

Process multiple files at once:

```bash
# Process all files in a directory
python src/cli.py batch-process --input-dir ./transcripts --output-dir ./summaries
```

## Development

### Running Tests

```bash
# Run all tests
make test

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
```

### Local Development with Docker

```bash
# Start local services (Redis, PostgreSQL)
docker-compose up -d

# Run the application
make dev
```

### Code Quality

```bash
# Format code
black src/
isort src/

# Type checking
mypy src/

# Linting
flake8 src/
```

## Troubleshooting

### Common Issues

#### Google Drive Authentication Errors

```bash
# Clear cached credentials
rm -rf ~/.config/meeting-automation/credentials

# Re-run setup
python src/cli.py setup
```

#### WhatsApp API Rate Limiting

The tool automatically handles rate limiting, but you can adjust settings:

```python
# In src/integrations/green_api.py
RATE_LIMIT_DELAY = 3  # seconds between messages
MAX_RETRIES = 5
```

#### Trello Connection Issues

Verify your API credentials and board access:

```bash
python src/cli.py test --service trello --verbose
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
export LOG_LEVEL=DEBUG
python src/cli.py process --file transcript.txt
```

### Performance Optimization

For large transcript files:

```bash
# Use streaming processing
python src/cli.py process --file large_transcript.txt --stream

# Adjust chunk size
export PROCESSING_CHUNK_SIZE=1000
```

## API Reference

### CLI Commands

| Command | Description | Options |
|---------|-------------|---------|
| `setup` | Interactive configuration wizard | `--force` to overwrite existing config |
| `process` | Process single transcript | `--file`, `--format`, `--output` |
| `watch` | Monitor folder for new files | `--folder`, `--interval` |
| `test` | Test service connections | `--service`, `--verbose` |

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Yes |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | Yes |
| `GREEN_API_INSTANCE_ID` | Green API instance ID | Yes |
| `GREEN_API_TOKEN` | Green API token | Yes |
| `TRELLO_API_KEY` | Trello API key | Yes |
| `TRELLO_TOKEN` | Trello OAuth token | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Optional |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `make test`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:

1. Check the [troubleshooting guide](#troubleshooting)
2. Search existing [GitHub issues](https://github.com/your-repo/issues)
3. Create a new issue with detailed information

## Changelog

### v1.0.0
- Initial release
- Basic transcript processing
- Google Drive, WhatsApp, and Trello integrations
- CLI interface with rich output