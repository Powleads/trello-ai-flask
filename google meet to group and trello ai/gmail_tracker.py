#!/usr/bin/env python3
"""
Gmail Tracker & Informer - AI-powered email analysis with team notifications
Integrates with existing JGV EEsystems platform
"""

import os
import json
import time
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import sqlite3
from email.mime.text import MIMEText
import base64
import re

# Google API imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# AI and messaging imports
import openai
import requests

class GmailTracker:
    """Gmail Tracker for automatic email analysis and team notifications."""
    
    def __init__(self, db_path='gmail_tracker.db'):
        self.db_path = db_path
        self.gmail_service = None
        self.openai_client = None
        self.setup_database()
        self.setup_openai()
        
        # Team members mapping (reuse from main app)
        self.team_members = {
            'James Taylor': '19056064550@c.us',
            'Breyden': '12894434373@c.us', 
            'Ezechiel': '12894434373@c.us',
            'Dustin Salinas': '19054251997@c.us'
        }
        
        # Email categorization patterns
        self.category_patterns = {
            'onboarding': ['onboarding', 'new client', 'welcome', 'getting started', 'setup'],
            'ghl_support': ['gohighlevel', 'ghl', 'support ticket', 'technical issue'],
            'tech_issues': ['error', 'bug', 'problem', 'not working', 'broken', 'issue'],
            'client_communication': ['client', 'customer', 'urgent', 'request'],
            'system_alerts': ['alert', 'notification', 'system', 'automated', 'monitoring']
        }
    
    def setup_database(self):
        """Initialize SQLite database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Email watches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_watches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_pattern TEXT,
                sender_pattern TEXT,
                team_member TEXT,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
        ''')
        
        # Email history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id TEXT UNIQUE,
                subject TEXT,
                sender TEXT,
                recipient TEXT,
                category TEXT,
                assigned_to TEXT,
                whatsapp_sent BOOLEAN DEFAULT FALSE,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                email_content TEXT,
                priority INTEGER DEFAULT 1
            )
        ''')
        
        # Team member rules table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_member_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_patterns TEXT,
                keywords TEXT,
                team_member TEXT,
                priority INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Default team member rules
        default_rules = [
            ('onboarding,new client,setup', 'James Taylor', 1),
            ('gohighlevel,ghl,technical', 'Ezechiel', 2),
            ('design,creative,branding', 'Breyden', 2),
            ('urgent,critical,emergency', 'James Taylor', 3)
        ]
        
        for keywords, member, priority in default_rules:
            cursor.execute('''
                INSERT OR IGNORE INTO team_member_rules (keywords, team_member, priority)
                VALUES (?, ?, ?)
            ''', (keywords, member, priority))
        
        conn.commit()
        conn.close()
        print("[GMAIL] Database initialized successfully")
    
    def setup_openai(self):
        """Initialize OpenAI client for email categorization."""
        # Try loading from .env file if not in environment
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            try:
                # Try new client initialization
                self.openai_client = openai.OpenAI(api_key=api_key)
                print("[GMAIL] OpenAI GPT-5 client initialized for email analysis")
            except (TypeError, AttributeError) as e:
                # Fallback for compatibility issues
                print(f"[GMAIL] OpenAI client initialization adjusted for compatibility")
                # Set API key directly for older versions
                openai.api_key = api_key
                self.openai_client = None
                print("[GMAIL] Using fallback OpenAI configuration")
        else:
            print("[GMAIL] OpenAI API key not found - email categorization will be limited")
    
    def setup_gmail_api(self, credentials_file='credentials.json', token_file='gmail_token.json'):
        """Set up Gmail API authentication."""
        SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
        
        creds = None
        
        # Load existing token
        if os.path.exists(token_file):
            try:
                with open(token_file, 'r') as token:
                    creds_data = json.load(token)
                    creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
            except Exception as e:
                print(f"Error loading token: {e}")
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(credentials_file):
                    print(f"[GMAIL] Gmail credentials file not found: {credentials_file}")
                    print("Please download credentials.json from Google Cloud Console")
                    return False
                
                flow = Flow.from_client_secrets_file(credentials_file, SCOPES)
                flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                
                auth_url, _ = flow.authorization_url(prompt='consent')
                print(f"[GMAIL] Please visit this URL to authorize Gmail access: {auth_url}")
                
                code = input('Enter the authorization code: ')
                flow.fetch_token(code=code)
                creds = flow.credentials
            
            # Save credentials for next time
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
        
        try:
            self.gmail_service = build('gmail', 'v1', credentials=creds)
            print("[GMAIL] API connection established")
            return True
        except Exception as e:
            print(f"[GMAIL] Error setting up Gmail API: {e}")
            return False
    
    def categorize_email_with_ai(self, subject: str, content: str, sender: str) -> Dict[str, Any]:
        """Use GPT-5 to categorize and analyze email importance."""
        if not self.openai_client:
            return self.categorize_email_basic(subject, content, sender)
        
        prompt = f"""
        Analyze this email and provide categorization:

        FROM: {sender}
        SUBJECT: {subject}
        CONTENT: {content[:1000]}...

        Please analyze and return a JSON response with:
        1. category: one of (onboarding, ghl_support, tech_issues, client_communication, system_alerts, other)
        2. priority: 1-5 (5 = urgent, 1 = low)
        3. keywords: list of important keywords found
        4. suggested_assignee: which team member should handle this
        5. summary: brief 1-sentence summary
        6. action_required: boolean if immediate action needed

        Team members: James Taylor (general/urgent), Ezechiel (technical/GHL), Breyden (design), Dustin Salinas (operations)

        Response must be valid JSON only.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-5",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"AI categorization failed: {e}")
            return self.categorize_email_basic(subject, content, sender)
    
    def categorize_email_basic(self, subject: str, content: str, sender: str) -> Dict[str, Any]:
        """Basic email categorization without AI."""
        text = f"{subject} {content}".lower()
        
        category = "other"
        priority = 2
        keywords = []
        
        for cat, patterns in self.category_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    category = cat
                    keywords.append(pattern)
                    if cat in ['tech_issues', 'ghl_support']:
                        priority = 4
                    elif cat == 'onboarding':
                        priority = 3
                    break
        
        # Determine assignee based on category
        assignee_map = {
            'onboarding': 'James Taylor',
            'ghl_support': 'Ezechiel', 
            'tech_issues': 'Ezechiel',
            'client_communication': 'James Taylor',
            'system_alerts': 'Ezechiel'
        }
        
        return {
            'category': category,
            'priority': priority,
            'keywords': keywords,
            'suggested_assignee': assignee_map.get(category, 'James Taylor'),
            'summary': f"Email from {sender} about {category}",
            'action_required': priority >= 4
        }
    
    def scan_recent_emails(self, hours_back: int = 12) -> List[Dict]:
        """Scan recent emails for processing."""
        if not self.gmail_service:
            print("[GMAIL] Gmail service not initialized")
            return []
        
        try:
            # Calculate time range
            since = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            query = f'to:admin@justgoingviral.com after:{since.strftime("%Y/%m/%d")}'
            
            # Search for emails
            results = self.gmail_service.users().messages().list(
                userId='me', 
                q=query,
                maxResults=50
            ).execute()
            
            messages = results.get('messages', [])
            processed_emails = []
            
            print(f"[GMAIL] Found {len(messages)} emails to process")
            
            for message in messages:
                try:
                    # Get full message
                    msg = self.gmail_service.users().messages().get(
                        userId='me', 
                        id=message['id']
                    ).execute()
                    
                    # Extract email data
                    email_data = self.extract_email_data(msg)
                    if email_data:
                        processed_emails.append(email_data)
                        
                except Exception as e:
                    print(f"Error processing message {message['id']}: {e}")
                    continue
            
            return processed_emails
            
        except HttpError as error:
            print(f"Gmail API error: {error}")
            return []
    
    def extract_email_data(self, message: Dict) -> Optional[Dict]:
        """Extract relevant data from Gmail message."""
        try:
            headers = message['payload'].get('headers', [])
            
            # Extract headers
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            recipient = next((h['value'] for h in headers if h['name'] == 'To'), '')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Extract email content
            content = self.extract_email_content(message['payload'])
            
            # Check if already processed
            if self.is_email_processed(message['id']):
                return None
            
            return {
                'id': message['id'],
                'subject': subject,
                'sender': sender,
                'recipient': recipient,
                'date': date,
                'content': content,
                'thread_id': message.get('threadId', '')
            }
            
        except Exception as e:
            print(f"Error extracting email data: {e}")
            return None
    
    def extract_email_content(self, payload: Dict) -> str:
        """Extract text content from email payload."""
        content = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        content += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        else:
            if payload['mimeType'] == 'text/plain':
                data = payload['body'].get('data', '')
                if data:
                    content = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        return content[:2000]  # Limit content length
    
    def is_email_processed(self, email_id: str) -> bool:
        """Check if email has already been processed."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM email_history WHERE email_id = ?', (email_id,))
        result = cursor.fetchone()
        
        conn.close()
        return result is not None
    
    def process_email(self, email_data: Dict) -> Dict:
        """Process a single email with AI categorization and team assignment."""
        try:
            # Analyze email with AI
            analysis = self.categorize_email_with_ai(
                email_data['subject'],
                email_data['content'],
                email_data['sender']
            )
            
            # Store in database
            self.store_email_history(email_data, analysis)
            
            # Send notifications if required
            if analysis.get('action_required', False) or analysis.get('priority', 1) >= 3:
                self.send_team_notification(email_data, analysis)
            
            return {
                'success': True,
                'email_id': email_data['id'],
                'category': analysis['category'],
                'assigned_to': analysis['suggested_assignee'],
                'priority': analysis['priority']
            }
            
        except Exception as e:
            print(f"Error processing email {email_data['id']}: {e}")
            return {'success': False, 'error': str(e)}
    
    def store_email_history(self, email_data: Dict, analysis: Dict):
        """Store processed email in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO email_history 
            (email_id, subject, sender, recipient, category, assigned_to, email_content, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            email_data['id'],
            email_data['subject'],
            email_data['sender'],
            email_data['recipient'],
            analysis['category'],
            analysis['suggested_assignee'],
            email_data['content'],
            analysis['priority']
        ))
        
        conn.commit()
        conn.close()
    
    def send_team_notification(self, email_data: Dict, analysis: Dict) -> bool:
        """Send WhatsApp notification to assigned team member."""
        try:
            assignee = analysis['suggested_assignee']
            whatsapp_number = self.team_members.get(assignee)
            
            if not whatsapp_number:
                print(f"No WhatsApp number found for {assignee}")
                return False
            
            # Create notification message
            message = f"""📧 NEW IMPORTANT EMAIL
            
👤 From: {email_data['sender']}
📋 Subject: {email_data['subject']}
🏷️ Category: {analysis['category']}
⚡ Priority: {analysis['priority']}/5

📝 Summary: {analysis.get('summary', 'Email requires attention')}

🔗 Keywords: {', '.join(analysis.get('keywords', []))}

Please check your email and respond as needed.

- JGV Email Tracker"""
            
            # Send via Green API
            return self.send_whatsapp_message(whatsapp_number, message)
            
        except Exception as e:
            print(f"Error sending team notification: {e}")
            return False
    
    def send_whatsapp_message(self, phone_number: str, message: str) -> bool:
        """Send WhatsApp message via Green API."""
        try:
            green_api_instance = os.getenv('GREEN_API_INSTANCE')
            green_api_token = os.getenv('GREEN_API_TOKEN')
            
            if not green_api_instance or not green_api_token:
                print("Green API credentials not configured")
                return False
            
            url = f"https://api.green-api.com/waInstance{green_api_instance}/sendMessage/{green_api_token}"
            
            payload = {
                "chatId": phone_number,
                "message": message
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                print(f"WhatsApp sent to {phone_number}")
                return True
            else:
                print(f"WhatsApp send failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error sending WhatsApp: {e}")
            return False
    
    def run_automated_scan(self):
        """Run automated email scanning."""
        print("[GMAIL] Starting automated Gmail scan...")
        
        try:
            # Scan recent emails
            emails = self.scan_recent_emails(hours_back=12)
            
            if not emails:
                print("[GMAIL] No new emails found")
                return
            
            processed_count = 0
            notifications_sent = 0
            
            for email_data in emails:
                result = self.process_email(email_data)
                if result['success']:
                    processed_count += 1
                    if result.get('assigned_to'):
                        notifications_sent += 1
            
            # Send group summary
            self.send_group_summary(processed_count, notifications_sent)
            
            print(f"[GMAIL] Processed {processed_count} emails, sent {notifications_sent} notifications")
            
        except Exception as e:
            print(f"Error in automated scan: {e}")
    
    def send_group_summary(self, processed_count: int, notifications_sent: int):
        """Send summary to group chat."""
        group_chat_id = os.getenv('WHATSAPP_GROUP_CHAT_ID', '120363401025025313@g.us')
        
        message = f"""📊 EMAIL TRACKER SUMMARY
        
📧 Processed: {processed_count} emails
🔔 Notifications sent: {notifications_sent}
⏰ Scan completed: {datetime.now().strftime('%H:%M %p')}

Team members have been notified of important emails.

- JGV Email Tracker (Automated)"""
        
        self.send_whatsapp_message(group_chat_id, message)
    
    def get_email_history(self, limit: int = 50) -> List[Dict]:
        """Get recent email processing history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT email_id, subject, sender, category, assigned_to, 
                   whatsapp_sent, processed_at, priority
            FROM email_history 
            ORDER BY processed_at DESC 
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                'email_id': row[0],
                'subject': row[1],
                'sender': row[2],
                'category': row[3],
                'assigned_to': row[4],
                'whatsapp_sent': bool(row[5]),
                'processed_at': row[6],
                'priority': row[7]
            }
            for row in results
        ]


# Automated scanning scheduler
class GmailScheduler:
    """Scheduler for automated Gmail scanning twice daily."""
    
    def __init__(self, gmail_tracker: GmailTracker):
        self.gmail_tracker = gmail_tracker
        self.running = False
        self.thread = None
    
    def start_scheduler(self):
        """Start the automated scanning scheduler."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        print("[GMAIL] Scheduler started - scanning twice daily (6 AM & 6 PM PST)")
    
    def stop_scheduler(self):
        """Stop the automated scanning scheduler."""
        self.running = False
        if self.thread:
            self.thread.join()
        print("[GMAIL] Scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop."""
        while self.running:
            try:
                now = datetime.now()
                
                # Check if it's time for scheduled scan (6 AM or 6 PM)
                if (now.hour == 6 or now.hour == 18) and now.minute == 0:
                    print(f"[GMAIL] Scheduled scan at {now.strftime('%H:%M')}")
                    self.gmail_tracker.run_automated_scan()
                    
                    # Wait to avoid duplicate scans
                    time.sleep(60)
                
                # Check every minute
                time.sleep(60)
                
            except Exception as e:
                print(f"Error in Gmail scheduler: {e}")
                time.sleep(300)  # Wait 5 minutes on error


# Global instance for integration with main app
gmail_tracker_instance = None

def initialize_gmail_tracker():
    """Initialize Gmail tracker for use in main application."""
    global gmail_tracker_instance
    
    if gmail_tracker_instance is None:
        gmail_tracker_instance = GmailTracker()
        
        # Set up Gmail API if credentials exist
        if os.path.exists('credentials.json'):
            try:
                gmail_tracker_instance.setup_gmail_api()
            except Exception as e:
                print(f"[GMAIL] Setup skipped: {e}")
        else:
            print("[GMAIL] Gmail credentials not found - manual setup required")
    
    return gmail_tracker_instance


if __name__ == "__main__":
    # Test the Gmail tracker
    tracker = GmailTracker()
    
    if tracker.setup_gmail_api():
        print("Testing Gmail tracker...")
        emails = tracker.scan_recent_emails(hours_back=24)
        print(f"Found {len(emails)} emails")
        
        for email in emails[:3]:  # Process first 3 emails
            result = tracker.process_email(email)
            print(f"Processed: {result}")