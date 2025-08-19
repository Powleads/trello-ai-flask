# 🚀 Trello AI - Intelligent Meeting Transcription & Task Management

A powerful Flask web application that combines AI-powered meeting transcription with intelligent Trello board management and Google Meet integration.

## ✨ Features

- **🎙️ AI Meeting Transcription**: Process Google Meet recordings with speaker analysis
- **🤖 Intelligent Task Extraction**: Automatically identify action items and assignments
- **📋 Smart Trello Integration**: Auto-create and update Trello cards from meeting content
- **👥 Speaker Analysis**: Identify and track different speakers in meetings
- **📊 Team Tracker**: Monitor recurring tasks and team updates
- **🔔 WhatsApp Integration**: Send automated updates via Green API
- **💾 Data Persistence**: SQLite database for meeting history and analytics
- **🔒 Secure API Management**: Environment-based configuration for all credentials

## 🏗️ Architecture

```
Trello AI/
├── google meet to group and trello ai/  # Main Flask application
│   ├── web_app.py                       # Main Flask app entry point
│   ├── templates/                       # HTML templates
│   ├── static/                          # CSS, JS, images
│   ├── requirements.txt                 # Python dependencies
│   └── ...                              # Supporting modules
├── .env.example                         # Environment template
├── .gitignore                          # Security & cleanup rules
└── README.md                           # This file
```

## 🚀 Quick Start

### 1. Prerequisites

- **Python 3.8+** - [Download Python](https://python.org/downloads/)
- **Git** - [Download Git](https://git-scm.com/)

### 2. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd "trello-ai"

# Navigate to the main application directory
cd "google meet to group and trello ai"

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copy environment template
cp ../.env.example .env

# Edit .env file with your API keys and credentials
# See API Setup section below for details
```

### 4. Run the Application

```bash
# Start the Flask development server
python web_app.py

# Or use Flask CLI
export FLASK_APP=web_app.py  # On Windows: set FLASK_APP=web_app.py
flask run --port 5000
```

Visit `http://localhost:5000` in your browser!

## 🔑 API Setup Guide

### Required APIs

#### 1. OpenAI API
```bash
# Get your API key from https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-openai-api-key-here
```

#### 2. Trello API
```bash
# Get your API key and token from https://trello.com/app-key
TRELLO_API_KEY=your-trello-api-key
TRELLO_TOKEN=your-trello-token
TRELLO_BOARD_ID=your-default-board-id
```

#### 3. Google APIs (Optional but recommended)
```bash
# Create project at https://console.cloud.google.com
# Enable Google Drive, Calendar, and Meet APIs
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

#### 4. Green API / WhatsApp (Optional)
```bash
# Sign up at https://green-api.com
GREEN_API_TOKEN=your-green-api-token
GREEN_API_INSTANCE=your-instance-id
```

## 🖥️ Usage

### Main Features

1. **📝 Process Meeting Transcripts**
   - Navigate to "Google Meet Integration"
   - Upload transcript files or paste transcript text
   - AI automatically extracts tasks, assignments, and key points

2. **👥 Team Tracker** 
   - Monitor recurring team tasks
   - Track progress and send reminders
   - Generate team update reports

3. **📊 Analytics Dashboard**
   - View meeting history and insights
   - Track task completion rates
   - Analyze team performance

### API Endpoints

- `POST /api/process-transcript` - Process meeting transcripts
- `GET /api/recent-activity` - Get recent Trello activity
- `POST /api/scan-cards` - Scan and analyze Trello cards
- `POST /api/send-whatsapp-updates` - Send WhatsApp notifications

## 🔧 Configuration Options

### Environment Variables

See `.env.example` for complete configuration options including:

- **Flask Settings**: Debug mode, secret keys, port configuration
- **AI Configuration**: Model selection, confidence thresholds
- **Database**: SQLite (default) or PostgreSQL for production
- **Security**: CORS settings, session management
- **Integrations**: All third-party API credentials

### Database Setup

The application uses SQLite by default. For production, configure PostgreSQL:

```bash
DATABASE_URL=postgresql://user:password@host:port/dbname
```

## 🛡️ Security Features

- **🔒 Environment-based secrets**: All API keys stored in `.env` files
- **🚫 Comprehensive .gitignore**: Prevents accidental credential commits  
- **🔐 Session management**: Secure Flask sessions
- **🛡️ CORS protection**: Configurable cross-origin policies
- **📝 Audit logging**: Track API usage and access

## 🚀 Production Deployment

### Environment Setup
```bash
# Set production environment
FLASK_ENV=production
FLASK_DEBUG=False

# Use strong secret key
SECRET_KEY=your-very-strong-secret-key

# Configure production database
DATABASE_URL=postgresql://user:pass@host/db
```

### Deployment Options

- **Heroku**: Use `Procfile` with `gunicorn`
- **Docker**: See `deployment/` directory for Docker configs
- **VPS**: Use `gunicorn` + `nginx` for production serving

## 🧪 Development

### Project Structure
```
google meet to group and trello ai/
├── web_app.py              # Main Flask application
├── custom_trello.py        # Trello API integration
├── speaker_analysis.py     # AI speaker identification
├── recurring_task_tracker.py  # Task management
├── database.py            # Database operations
├── templates/             # Jinja2 HTML templates
│   ├── index.html
│   ├── google_meet_app.html
│   └── team_tracker.html
└── requirements.txt       # Python dependencies
```

### Key Dependencies
- **Flask 3.0.0** - Web framework
- **OpenAI** - AI processing and analysis
- **py-trello** - Trello API integration
- **requests** - HTTP client for APIs
- **python-dotenv** - Environment variable management

### Development Commands
```bash
# Run in debug mode
python web_app.py

# Run tests (if available)
python -m pytest tests/

# Install new dependencies
pip install package-name
pip freeze > requirements.txt
```

## 📋 Roadmap

- [ ] **Real-time processing** - WebSocket integration for live transcription
- [ ] **Mobile app** - React Native companion app  
- [ ] **Advanced analytics** - Enhanced reporting and insights
- [ ] **Multi-language support** - Internationalization
- [ ] **Plugin system** - Extensible integrations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test thoroughly
4. Commit: `git commit -m "Add feature description"`
5. Push: `git push origin feature-name` 
6. Create a Pull Request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support & Troubleshooting

### Common Issues

**Flask won't start:**
- Check Python version (3.8+ required)
- Verify all dependencies installed: `pip install -r requirements.txt`
- Ensure `.env` file exists with required variables

**API errors:**
- Verify all API keys in `.env` file
- Check API quotas and rate limits
- Review application logs for detailed error messages

**Database issues:**
- Default SQLite should work out of the box
- For production, ensure PostgreSQL is properly configured

### Getting Help

- 📧 Create an issue for bugs or feature requests
- 💬 Check existing issues for solutions
- 📖 Review the configuration examples in `.env.example`

---

**Made with ❤️ for productive teams everywhere**

*Powered by OpenAI, Trello API, and Flask*