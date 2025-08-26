# 🚀 Production Deployment Guide - Render.com

This guide covers deploying the Gmail tracker to Render.com with full production readiness.

## ✅ **Production-Ready Features Implemented**

### **🔧 Fixed Issues:**
1. **PostgreSQL Support** - Auto-detects DATABASE_URL for production
2. **Web-based OAuth** - No more console input requirements  
3. **Environment Variables** - All secrets moved to env vars
4. **Database Token Storage** - Persistent across deployments
5. **Settings Persistence** - Stored in database, not JSON files

### **📦 New Components Added:**
- `production_db.py` - PostgreSQL/SQLite compatibility layer
- `gmail_oauth.py` - Web-based OAuth handler 
- Updated `gmail_tracker.py` - Production-ready
- Updated `web_app.py` - Integrated with production components
- Enhanced `requirements.txt` - Added PostgreSQL & timezone support

## 🔑 **Required Environment Variables**

Set these in your Render.com service settings:

### **Core Application**
```bash
SECRET_KEY=your_super_secret_key_here
LOGIN_USERNAME=admin@justgoingviral.com
LOGIN_PASSWORD=your_secure_password

# Database (automatically provided by Render PostgreSQL)
DATABASE_URL=postgresql://user:pass@host:port/db

# Production Detection (automatically set by Render)
RENDER=true
RENDER_EXTERNAL_URL=https://your-app.onrender.com
```

### **APIs & Integrations**
```bash
# OpenAI for email analysis
OPENAI_API_KEY=sk-your-openai-key

# Google OAuth (from Google Cloud Console)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# WhatsApp via Green API
GREEN_API_TOKEN=your-green-api-token
GREEN_API_INSTANCE_ID=7105263120
WHATSAPP_GROUP_CHAT_ID=120363401025025313@g.us

# Trello Integration
TRELLO_API_KEY=your-trello-key
TRELLO_API_SECRET=your-trello-secret  
TRELLO_TOKEN=your-trello-token
```

### **Team Members WhatsApp Numbers**
```bash
TEAM_MEMBER_JAMES_TAYLOR=19056064550@c.us
TEAM_MEMBER_LEVY=237659250977@c.us
TEAM_MEMBER_WENDY=237677079267@c.us
TEAM_MEMBER_FORKA=237652275097@c.us
TEAM_MEMBER_BRAYAN=237676267420@c.us
TEAM_MEMBER_EZECHIEL=23754071907@c.us
TEAM_MEMBER_DUSTIN_SALINAS=19054251997@c.us
TEAM_MEMBER_BREYDEN=13179979692@c.us
```

## 🛠 **Deployment Steps**

### **1. Prepare Google OAuth**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select your project
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `https://your-app.onrender.com/auth/gmail/callback`
6. Get Client ID and Client Secret

### **2. Deploy to Render**
1. **Connect Repository**: Link your GitHub repo to Render
2. **Create Web Service**: Choose "Web Service" deployment
3. **Set Build Command**: `pip install -r requirements.txt`
4. **Set Start Command**: `gunicorn web_app:app`
5. **Add PostgreSQL Database**: Create PostgreSQL add-on service

### **3. Configure Environment Variables**
Add all the environment variables listed above in your Render service settings.

### **4. First-Time Setup**
After deployment:

1. **Visit your app**: `https://your-app.onrender.com`
2. **Login**: Use your configured credentials
3. **Authenticate Gmail**: Visit `/auth/gmail` to start OAuth flow
4. **Configure Watch Rules**: Set up email filtering rules
5. **Test Manual Scan**: Verify everything works

## 🔄 **How It Works in Production**

### **Database Handling**
- **Local Development**: Uses SQLite (`gmail_tracker.db`)
- **Production**: Auto-detects `DATABASE_URL` and uses PostgreSQL
- **Migrations**: Tables created automatically on first run

### **Gmail Authentication**
- **Local**: Falls back to `credentials.json` file
- **Production**: Uses environment variables (`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`)
- **Tokens**: Stored in database (persistent across restarts)
- **Refresh**: Automatic token refresh handled

### **Settings Storage**
- **Local**: JSON file + database backup
- **Production**: PostgreSQL database (persistent)
- **Sync**: Web interface automatically syncs to database

### **Team Members**
- **Local**: Hardcoded fallback values
- **Production**: Loaded from environment variables
- **Format**: `TEAM_MEMBER_NAME=phone@c.us`

## 🧪 **Testing Checklist**

After deployment, verify:

- [ ] **App loads**: Homepage accessible
- [ ] **Login works**: Authentication successful  
- [ ] **Gmail auth**: OAuth flow completes at `/auth/gmail`
- [ ] **Watch rules**: Can create/edit email rules
- [ ] **Manual scan**: Finds emails matching rules
- [ ] **Email history**: Shows processed emails with all assignees
- [ ] **Vegas timezone**: Timestamps show correct time
- [ ] **WhatsApp**: Notifications sent to team members
- [ ] **Database persistence**: Data survives restart

## 🚨 **Troubleshooting**

### **Database Connection Issues**
```bash
# Check DATABASE_URL format
postgresql://username:password@hostname:port/database_name

# Verify PostgreSQL service is linked
# Check Render dashboard for database connection string
```

### **Gmail OAuth Issues** 
```bash
# Verify redirect URI in Google Console matches:
https://your-app.onrender.com/auth/gmail/callback

# Check environment variables are set:
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

### **WhatsApp Integration**
```bash
# Verify Green API credentials:
GREEN_API_TOKEN=...
GREEN_API_INSTANCE_ID=...

# Check team member phone format:
TEAM_MEMBER_NAME=1234567890@c.us
```

### **Environment Detection**
The system automatically detects production environment via:
- `DATABASE_URL` presence (PostgreSQL connection string)
- `RENDER` environment variable
- `RENDER_EXTERNAL_URL` for OAuth redirects

## 📊 **Production vs Local Development**

| Feature | Local Development | Production (Render) |
|---------|------------------|-------------------|
| Database | SQLite file | PostgreSQL |
| Gmail OAuth | credentials.json | Environment vars |
| Token Storage | JSON files | Database |
| Settings Storage | JSON + DB | Database only |
| Team Members | Hardcoded | Environment vars |
| URL Detection | localhost:5000 | RENDER_EXTERNAL_URL |

## 🔐 **Security Notes**

- All secrets stored as environment variables
- OAuth tokens encrypted in database
- HTTPS enforced in production
- Session security configured
- Rate limiting implemented
- Input validation throughout

---

## ✅ **Ready for Production!**

Your Gmail tracker is now production-ready with:
- ✅ **Database persistence** (PostgreSQL)
- ✅ **Web-based authentication** 
- ✅ **Environment variable configuration**
- ✅ **Automatic deployment support**
- ✅ **Zero-downtime token refresh**
- ✅ **Multi-assignee email processing**
- ✅ **Vegas timezone display**

Deploy with confidence! 🚀