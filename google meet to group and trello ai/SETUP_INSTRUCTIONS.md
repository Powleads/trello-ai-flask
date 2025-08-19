# JGV EEsystems Team Update Tracker - Setup Instructions

## 🚀 Quick Start

### Prerequisites
- Python 3.8+ installed
- Trello account with API access
- Green API WhatsApp account
- Git (optional)

### 1. Environment Setup

1. **Clone or download the project**
   ```bash
   cd "C:\Users\james\Desktop\TRELLO AI\google meet to group and trello ai"
   ```

2. **Create environment file**
   Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   copy .env.example .env
   ```

3. **Edit the .env file with your credentials:**
   ```env
   # Trello API Configuration
   TRELLO_API_KEY=your_trello_api_key_here
   TRELLO_API_SECRET=your_trello_api_secret_here
   TRELLO_TOKEN=your_trello_token_here

   # Green API WhatsApp Configuration
   GREEN_API_TOKEN=your_green_api_token_here
   GREEN_API_INSTANCE_ID=7105263120

   # Flask Application
   SECRET_KEY=your_secret_key_here
   ```

### 2. Get Trello Credentials

1. **Get API Key and Secret:**
   - Go to https://trello.com/app-key
   - Copy your API Key and Secret

2. **Get Token:**
   - Run the token generator:
   ```bash
   python get_trello_token.py
   ```
   - Or visit: https://trello.com/1/authorize?expiration=never&scope=read,write&response_type=token&key=YOUR_API_KEY

### 3. Get Green API Credentials

1. **Sign up at Green API:**
   - Visit https://green-api.com
   - Create an account and get your instance

2. **Get your token:**
   - Instance ID: `7105263120` (already configured)
   - Copy your API token from the dashboard

### 4. Launch the Application

Run the startup script:
```bash
python start_team_tracker.py
```

The script will:
- ✅ Check environment variables
- 📦 Install required dependencies
- 🔍 Test integrations
- 🚀 Launch the web application

### 5. Access the Applications

Open your browser and navigate to:

- **Main Dashboard:** http://localhost:5000
- **Team Update Tracker:** http://localhost:5000/team-tracker
- **Google Meet App:** http://localhost:5000/google-meet
- **Analytics Dashboard:** http://localhost:5000/analytics

## 📋 Features Overview

### Team Update Tracker
- **Card Scanning:** Automatically scans Trello boards for cards needing updates
- **24-Hour Monitoring:** Identifies cards with no comments in the last 24 hours
- **WhatsApp Integration:** Sends automated update requests to team members
- **Escalation System:** After 3 unanswered requests, escalates to group chat
- **Scheduling:** Automated daily scans Monday-Friday
- **Analytics:** Comprehensive team performance metrics

### Google Meet to Trello
- **Transcript Processing:** Converts Google Docs meeting transcripts to Trello cards
- **AI-Powered:** Intelligent task extraction and assignment
- **Seamless Integration:** Direct connection to your Trello boards

### Analytics Dashboard
- **Performance Metrics:** Track team response rates and productivity
- **Visual Charts:** Interactive charts and graphs
- **Board Analytics:** Monitor board-specific performance
- **Escalation Alerts:** Real-time alerts for team members needing attention
- **Export Reports:** Download performance reports

## 🛠️ Configuration

### Team Members
The system is pre-configured with your team members from the blueprint:

```python
TEAM_MEMBERS = {
    'Criselle': '639494048499@c.us',
    'Lancey': '639264438378@c.us',
    'Ezechiel': '23754071907@c.us',
    'Levy': '237659250977@c.us',
    'Wendy': '237677079267@c.us',
    'Forka': '237652275097@c.us',
    'Breyden': '13179979692@c.us',
    'Brayan': '237676267420@c.us'
}
```

To modify team members, edit the `TEAM_MEMBERS` dictionary in `web_app.py`.

### Scheduling Settings
In the Team Tracker app, click "Settings" to configure:
- **Auto Schedule:** Enable/disable automated scanning
- **Schedule Time:** Time of day to run scans (default: 09:00)
- **Schedule Days:** Which days to run (default: Monday-Friday)

### Message Templates
Customize WhatsApp message templates in `green_api_integration.py`:
- `create_update_request_message()` - Individual update requests
- `create_unassigned_cards_message()` - Unassigned card notifications
- `create_escalation_message()` - Escalation alerts

## 🔧 Advanced Configuration

### Database Storage (Optional)
For production use, configure a database in `.env`:
```env
DATABASE_URL=postgresql://user:password@localhost/team_tracker
```

### Custom Board Selection
To scan specific boards only, modify the `scan_cards()` function in `web_app.py` to specify board IDs.

### Notification Thresholds
Adjust time thresholds in `trello_integration.py`:
- Default: 24 hours for update requirements
- Escalation: 3 update requests

## 📊 Usage Guide

### Daily Workflow
1. **Morning:** System automatically scans cards (if scheduled)
2. **Review:** Check Team Tracker dashboard for cards needing updates
3. **Action:** Select cards and send update requests
4. **Monitor:** View analytics for team performance insights
5. **Escalate:** Handle persistent non-responders through group chat

### Manual Operations
- **Scan Cards:** Click "Scan Cards" to check for updates
- **Send Updates:** Select cards and click "Send Updates"
- **View Analytics:** Monitor team performance in real-time
- **Export Reports:** Download performance data for analysis

## 🔍 Troubleshooting

### Common Issues

1. **Trello Connection Failed**
   - Verify API credentials in `.env`
   - Check token permissions (read/write required)
   - Ensure token hasn't expired

2. **WhatsApp Messages Not Sending**
   - Verify Green API token and instance ID
   - Check WhatsApp number format (@c.us suffix)
   - Ensure Green API instance is active

3. **Cards Not Found**
   - Check board accessibility with Trello token
   - Verify board IDs if using custom configuration
   - Ensure boards are not archived

4. **Scheduling Not Working**
   - Check system time and timezone
   - Verify schedule settings in app
   - Review console logs for errors

### Getting Help
- Check console logs for detailed error messages
- Test integrations using the built-in test functions
- Review the PRD document for feature specifications

## 🔐 Security Notes

- Keep your `.env` file secure and never commit it to version control
- Regularly rotate API tokens and credentials
- Use HTTPS in production environments
- Limit Trello token permissions to required boards only

## 📈 Performance Tips

- Schedule scans during off-peak hours
- Limit board scanning to active boards only
- Use database storage for large teams
- Monitor API rate limits for Trello and Green API

## 🚀 Production Deployment

For production use:
1. Use a proper database (PostgreSQL/MySQL)
2. Set up proper logging
3. Use a production WSGI server (Gunicorn)
4. Configure reverse proxy (Nginx)
5. Set up SSL certificates
6. Use environment-specific configurations

---

**Support:** For technical support, contact the development team or refer to the project documentation.