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

# Production imports
from production_db import get_production_db
from gmail_oauth import gmail_oauth

class GmailTracker:
    """Gmail Tracker for automatic email analysis and team notifications."""
    
    def __init__(self, db_path='gmail_tracker.db'):
        self.db_path = db_path
        self.gmail_service = None
        self.openai_client = None
        self.db = get_production_db()
        self.setup_openai()
        self.setup_production_gmail_service()
        
        # Team members from environment variables (production-ready)
        self.team_members = self._load_team_members()
        
        # NO hardcoded patterns - ONLY use watch rules from database
        print("[GMAIL] Production-ready Gmail tracker initialized")
    
    def _load_team_members(self) -> Dict[str, str]:
        """Load team members from environment variables for production"""
        # Try environment variables first (production)
        team_members = {}
        
        # Expected format: TEAM_MEMBER_NAME=phone_number
        for key, value in os.environ.items():
            if key.startswith('TEAM_MEMBER_'):
                name = key.replace('TEAM_MEMBER_', '').replace('_', ' ').title()
                team_members[name] = value
        
        # Fallback to hardcoded for local development
        if not team_members:
            print("[GMAIL] Using fallback team members for local development")
            team_members = {
                'James Taylor': '19056064550@c.us',
                'Breyden': '12894434373@c.us', 
                'Ezechiel': '12894434373@c.us',
                'Dustin Salinas': '19054251997@c.us'
            }
        
        print(f"[GMAIL] Loaded {len(team_members)} team members")
        return team_members
    
    def scan_emails_only(self, hours_back=24, unread_only=True) -> List[Dict]:
        """Scan emails without sending notifications - for manual review"""
        if not self.gmail_service:
            print("[GMAIL] Gmail service not available")
            return []
        
        # Get watch rules from production database  
        watch_rules_data = self.db.get_watch_rules()
        watch_rules = watch_rules_data.get('watchRules', []) if watch_rules_data else []
        
        if not watch_rules:
            print("[GMAIL] No watch rules configured")
            return []
        
        processed_emails = []
        since = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        
        print(f"[GMAIL] Scanning emails from last {hours_back} hours (unread only: {unread_only})")
        
        try:
            # Process each watch rule
            for rule_index, rule in enumerate(watch_rules):
                subject_filter = rule.get('subject', '')
                sender_filter = rule.get('sender', '')
                body_filter = rule.get('body', '')
                
                # Skip empty rules
                if not subject_filter and not sender_filter and not body_filter:
                    continue
                
                # Build Gmail search query for this rule
                query_parts = [f'after:{since.strftime("%Y/%m/%d")}']
                
                # Add unread filter if requested
                if unread_only:
                    query_parts.append('is:unread')
                
                if subject_filter:
                    query_parts.append(f'subject:"{subject_filter}"')
                    
                if sender_filter:
                    query_parts.append(f'from:"{sender_filter}"')
                    
                # Note: Gmail API doesn't support body search in basic queries
                # Body filtering will be done post-fetch
                
                query = ' '.join(query_parts)
                print(f"[GMAIL] Query: {query}")
                
                print(f"[GMAIL] SCAN-ONLY Rule {rule_index + 1}: '{subject_filter or 'Any subject'}' from '{sender_filter or 'Any sender'}' -> {rule.get('category', 'unknown')}")
                
                try:
                    results = self.gmail_service.users().messages().list(
                        userId='me',
                        q=query,
                        maxResults=50
                    ).execute()
                    
                    messages = results.get('messages', [])
                    print(f"[GMAIL] SCAN-ONLY Found {len(messages)} emails matching rule: '{subject_filter or 'Any subject'}'")
                    
                    for message in messages:
                        try:
                            # Extract email data
                            email_data = self.extract_email_data(message)
                            if not email_data:
                                continue
                            
                            # Add rule context
                            email_data['matched_rule'] = rule
                            email_data['rule_category'] = rule.get('category', 'other')
                            email_data['rule_assignees'] = rule.get('assignees', [])
                            
                            # Check if WhatsApp notification was already sent today
                            email_data['sent_today'] = self.db.is_email_sent_today(email_data['id'])
                            if email_data['sent_today']:
                                print(f"[GMAIL] Email {email_data['id']} already sent WhatsApp today")
                            
                            # Check for duplicate
                            if not any(e['id'] == email_data['id'] for e in processed_emails):
                                processed_emails.append(email_data)
                                sent_status = "✅ SENT" if email_data['sent_today'] else "PENDING"
                                print(f"[GMAIL] SCAN-ONLY Email queued [{sent_status}]: '{email_data['subject'][:50]}...' -> Category: {rule.get('category', 'other')}")
                                
                        except Exception as e:
                            print(f"Error processing message {message['id']}: {e}")
                            
                except Exception as e:
                    print(f"Error processing rule {rule_index + 1}: {e}")
                    
        except Exception as e:
            print(f"[GMAIL] Error in scan_emails_only: {e}")
            
        print(f"[GMAIL] SCAN-ONLY Complete: Found {len(processed_emails)} total emails for review")
        return processed_emails
    
    def setup_production_gmail_service(self):
        """Set up Gmail service using production OAuth handler"""
        try:
            self.gmail_service = gmail_oauth.get_gmail_service()
            if self.gmail_service:
                print("[GMAIL] Production Gmail service initialized")
                return True
            else:
                print("[GMAIL] Gmail service not available - authentication required")
                return False
        except Exception as e:
            print(f"[GMAIL] Error setting up production Gmail service: {e}")
            return False
    
    # Database setup moved to production_db.py - no longer needed here
    
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
                print("[GMAIL] OpenAI GPT-4o client initialized for email analysis")
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
        """Legacy method - redirects to production Gmail service setup"""
        print("[GMAIL] Using production OAuth handler for Gmail authentication")
        return self.setup_production_gmail_service()
    
    def categorize_email_with_ai(self, subject: str, content: str, sender: str, email_data: Dict = None) -> Dict[str, Any]:
        """Use GPT-4o to categorize and analyze email importance based on matched rule."""
        if not self.openai_client:
            return self.categorize_email_basic(subject, content, sender, email_data)
        
        # Use rule-based assignment if available
        if email_data and email_data.get('matched_rule'):
            rule = email_data['matched_rule']
            category = rule.get('category', 'other')
            assignees = rule.get('assignees', [])
            
            prompt = f"""
            Analyze this email that matched a specific watch rule and provide categorization:

            FROM: {sender}
            SUBJECT: {subject}
            CONTENT: {content[:1000]}...
            
            MATCHED RULE:
            - Category: {category}
            - Subject Filter: {rule.get('subject', 'N/A')}
            - Sender Filter: {rule.get('sender', 'N/A')}
            - Body Filter: {rule.get('body', 'N/A')}
            - Assigned to: {', '.join(assignees) if assignees else 'Unassigned'}

            Please analyze and return a JSON response with:
            1. category: "{category}" (from matched rule)
            2. priority: 1-5 (5 = urgent, 1 = low priority)
            3. keywords: list of important keywords found
            4. suggested_assignee: {assignees[0] if assignees else '"Unassigned"'} (from rule)
            5. all_assignees: {assignees} (all people assigned to this category)
            6. summary: brief 1-sentence summary focused on the content
            7. action_required: boolean (whether immediate action is needed)

            Focus on determining priority and summarizing the content.
            Response must be valid JSON only.
            """
        else:
            # Fallback for emails without rules (shouldn't happen in new system)
            prompt = f"""
            Analyze this email and provide basic categorization:

            FROM: {sender}
            SUBJECT: {subject}
            CONTENT: {content[:1000]}...

            Please analyze and return a JSON response with:
            1. category: "other"
            2. priority: 1-5
            3. keywords: list of important keywords found
            4. suggested_assignee: "Unassigned"
            5. all_assignees: []
            6. summary: brief summary
            7. action_required: boolean

            Response must be valid JSON only.
            """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"[GMAIL] AI categorization failed: {e}")
            return self.categorize_email_basic(subject, content, sender, email_data)
    
    def categorize_email_basic(self, subject: str, content: str, sender: str, email_data: Dict = None) -> Dict[str, Any]:
        """Simplified email categorization based on matched rule."""
        text = f"{subject} {content}".lower()
        
        # Use rule-based assignment if available
        if email_data and email_data.get('matched_rule'):
            rule = email_data['matched_rule']
            category = rule.get('category', 'other')
            assignees = rule.get('assignees', [])
            
            priority = 3  # Default medium priority
            keywords = []
            
            # Extract keywords from rule filters
            rule_keywords = []
            if rule.get('subject'):
                rule_keywords.extend(rule['subject'].lower().split())
            if rule.get('body'):
                rule_keywords.extend(rule['body'].lower().split())
            
            # Find which keywords are present in the email
            for keyword in rule_keywords:
                if keyword in text and len(keyword) > 2:  # Skip short words
                    keywords.append(keyword)
            
            # Check for urgency indicators
            urgency_keywords = ['urgent', 'asap', 'immediate', 'critical', 'emergency']
            for urgent_word in urgency_keywords:
                if urgent_word in text:
                    priority = 5
                    keywords.append(urgent_word)
                    break
            
            return {
                'category': category,
                'priority': priority,
                'keywords': keywords,
                'suggested_assignee': assignees[0] if assignees else 'Unassigned',
                'all_assignees': assignees,
                'summary': f"Email from {sender} matching {category} rule",
                'action_required': priority >= 3
            }
        else:
            # Fallback for emails without rules
            return {
                'category': 'other',
                'priority': 2,
                'keywords': [],
                'suggested_assignee': 'Unassigned',
                'all_assignees': [],
                'summary': f"Email from {sender}",
                'action_required': False
            }
    
    def get_watch_rules_from_web_interface(self) -> List[Dict]:
        """Load watch rules from database (production) or JSON file (local)."""
        try:
            # Try database first (production)
            settings = self.db.get_watch_rules()
            if settings and settings.get('watchRules'):
                return settings.get('watchRules', [])
            
            # Fallback to settings file (local development)
            settings_file = 'gmail_automation_settings.json'
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    return settings.get('watchRules', [])
            
            return []
            
        except Exception as e:
            print(f"[GMAIL] Error loading watch rules: {e}")
            return []
    
    def scan_recent_emails(self, hours_back: int = 24, manual_rules: List[Dict] = None) -> List[Dict]:
        """Scan recent emails based on active watch rules only."""
        if not self.gmail_service:
            print("[GMAIL] Gmail service not initialized")
            return []
        
        # Get watch rules from web interface or use manual rules
        watch_rules = manual_rules or self.get_watch_rules_from_web_interface()
        
        if not watch_rules:
            print("[GMAIL] No active watch rules found. No emails will be scanned.")
            print("[GMAIL] Please configure email watch rules in the web interface first.")
            return []
        
        try:
            # Calculate time range
            since = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            processed_emails = []
            
            print(f"[GMAIL] Scanning emails based on {len(watch_rules)} active watch rules...")
            
            # Process each watch rule
            for rule_index, rule in enumerate(watch_rules):
                subject_filter = rule.get('subject', '')
                sender_filter = rule.get('sender', '')
                body_filter = rule.get('body', '')
                
                # Skip empty rules
                if not subject_filter and not sender_filter and not body_filter:
                    continue
                
                # Build Gmail search query for this rule
                query_parts = [f'after:{since.strftime("%Y/%m/%d")}']
                
                if subject_filter:
                    query_parts.append(f'subject:"{subject_filter}"')
                    
                if sender_filter:
                    query_parts.append(f'from:"{sender_filter}"')
                
                if body_filter:
                    query_parts.append(f'"{body_filter}"')
                
                query = ' '.join(query_parts)
                
                print(f"[GMAIL] RULE {rule_index + 1}: '{subject_filter or 'Any subject'}' from '{sender_filter or 'Any sender'}' -> {rule.get('category', 'unknown')}")
                print(f"[GMAIL] Query: {query}")
                print(f"[GMAIL] Assignees: {', '.join(rule.get('assignees', []))}")
                
                try:
                    # Search for emails matching this rule
                    results = self.gmail_service.users().messages().list(
                        userId='me', 
                        q=query,
                        maxResults=50
                    ).execute()
                    
                    messages = results.get('messages', [])
                    print(f"[GMAIL] Found {len(messages)} emails matching rule: '{subject_filter or 'Any subject'}'")
                    
                    for message in messages:
                        try:
                            # Get full message
                            msg = self.gmail_service.users().messages().get(
                                userId='me', 
                                id=message['id']
                            ).execute()
                            
                            # Extract email data
                            email_data = self.extract_email_data(msg)
                            if email_data and not any(e['id'] == email_data['id'] for e in processed_emails):
                                # Add rule info to email data
                                email_data['matched_rule'] = rule
                                email_data['rule_category'] = rule.get('category', 'other')
                                email_data['rule_assignees'] = rule.get('assignees', [])
                                processed_emails.append(email_data)
                                print(f"[GMAIL] Email matched: '{email_data['subject'][:50]}...' -> Category: {rule.get('category', 'other')}")
                                
                        except Exception as e:
                            print(f"Error processing message {message['id']}: {e}")
                            continue
                            
                except Exception as e:
                    print(f"Error processing rule {rule_index + 1}: {e}")
                    continue
            
            print(f"[GMAIL] TOTAL EMAILS FOUND: {len(processed_emails)} matching {len(watch_rules)} active rules")
            
            # Debug: Show summary by category
            category_counts = {}
            for email in processed_emails:
                cat = email.get('rule_category', 'unknown')
                category_counts[cat] = category_counts.get(cat, 0) + 1
            
            if category_counts:
                print(f"[GMAIL] BREAKDOWN BY CATEGORY:")
                for cat, count in category_counts.items():
                    print(f"[GMAIL]    {cat}: {count} emails")
            
            return processed_emails
            
        except HttpError as error:
            print(f"Gmail API error: {error}")
            return []
    
    def extract_email_data(self, message: Dict) -> Optional[Dict]:
        """Extract relevant data from Gmail message."""
        try:
            headers = message['payload'].get('headers', [])
            
            # Extract headers with better fallbacks
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            if not subject.strip():
                # Try different subject header variations
                subject = next((h['value'] for h in headers if h['name'].lower() in ['subject', 'subj']), '')
                if not subject.strip():
                    # Generate a better title from sender or content
                    sender_part = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                    sender_name = sender_part.split('<')[0].strip() if '<' in sender_part else sender_part.split('@')[0]
                    subject = f"Message from {sender_name}"
            
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            recipient = next((h['value'] for h in headers if h['name'] == 'To'), '')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Extract email content
            content = self.extract_email_content(message['payload'])
            
            # Check if already processed
            if self.is_email_processed(message['id']):
                print(f"[GMAIL] Skipping already processed email: {subject[:30]}...")
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
    
    def process_email(self, email_data: Dict, batch_notifications: bool = False) -> Dict:
        """Process a single email with AI categorization and team assignment."""
        try:
            # Analyze email with AI (now includes rule context)
            analysis = self.categorize_email_with_ai(
                email_data['subject'],
                email_data['content'],
                email_data['sender'],
                email_data  # Pass full email_data for rule context
            )
            
            # Store in database
            self.store_email_history(email_data, analysis)
            
            # Send notifications to ALL assignees if required (unless batching)
            if not batch_notifications and (analysis.get('action_required', False) or analysis.get('priority', 1) >= 3):
                self.send_team_notifications_to_all_assignees(email_data, analysis)
            
            return {
                'success': True,
                'email_id': email_data['id'],
                'category': analysis['category'],
                'assigned_to': analysis.get('all_assignees', [analysis.get('suggested_assignee', 'Unassigned')]),
                'priority': analysis['priority'],
                'analysis': analysis  # Include analysis for batching
            }
            
        except Exception as e:
            print(f"Error processing email {email_data['id']}: {e}")
            return {'success': False, 'error': str(e)}
    
    def store_email_history(self, email_data: Dict, analysis: Dict):
        """Store processed email in database."""
        import pytz
        from datetime import datetime
        
        # Get all assignees and join them with commas
        all_assignees = analysis.get('all_assignees', [])
        if not all_assignees:
            all_assignees = [analysis.get('suggested_assignee', 'Unassigned')]
        assignees_text = ', '.join(all_assignees)
        
        # Get Vegas time for timestamp
        vegas_tz = pytz.timezone('America/Los_Angeles')
        vegas_time = datetime.now(vegas_tz).strftime('%Y-%m-%d %H:%M:%S %Z')
        
        # Use production database manager
        self.db.store_email_history(
            email_data['id'],
            email_data['subject'],
            email_data['sender'],
            email_data['recipient'],
            analysis['category'],
            assignees_text,
            email_data['content'],
            analysis['priority'],
            vegas_time
        )
    
    def send_batched_notifications(self, emails_by_assignee: Dict) -> int:
        """Send batched notifications to team members with multiple emails and URLs."""
        notifications_sent = 0
        
        for assignee, email_list in emails_by_assignee.items():
            whatsapp_number = self.team_members.get(assignee)
            
            if not whatsapp_number:
                print(f"No WhatsApp number found for {assignee}")
                continue
            
            # Create batched message
            email_count = len(email_list)
            if email_count == 1:
                # Single email - use original format
                email_item = email_list[0]
                email_data = email_item['email_data']
                analysis = email_item['analysis']['analysis']
                
                message = f"""📧 NEW EMAIL ALERT

👤 From: {email_data['sender']}
📋 Subject: {email_data['subject']}
🏷️ Category: {analysis['category']}
⚡ Priority: {analysis['priority']}/5

📝 Summary: {analysis.get('summary', 'Email requires attention')}

🔗 Keywords: {', '.join(analysis.get('keywords', []))}

Please check your email and respond as needed.

⏰ Time: {self.get_las_vegas_time()}

- JGV Email Tracker"""
            else:
                # Multiple emails - create batched message
                message = f"""📧 MULTIPLE EMAIL ALERTS ({email_count} emails)

Hi {assignee}, you have {email_count} new emails requiring attention:

"""
                
                for i, email_item in enumerate(email_list, 1):
                    email_data = email_item['email_data']
                    analysis = email_item['analysis']['analysis']
                    
                    # Add Gmail URL for each email
                    gmail_url = f"https://mail.google.com/mail/u/0/#inbox/{email_data['thread_id']}"
                    
                    message += f"""{i}. 📋 {email_data['subject'][:60]}{'...' if len(email_data['subject']) > 60 else ''}
   👤 From: {email_data['sender']}
   🏷️ {analysis['category']} | ⚡ Priority: {analysis['priority']}/5
   🔗 {gmail_url}

"""
                
                message += f"""Please check your emails and respond as needed.

⏰ Time: {self.get_las_vegas_time()}

- JGV Email Tracker"""
            
            # Send the message
            if self.send_whatsapp_message(whatsapp_number, message):
                notifications_sent += 1
                print(f"Batched notification sent to {assignee} ({email_count} emails)")
            else:
                print(f"❌ Failed to send batched notification to {assignee}")
        
        print(f"[GMAIL] Sent {notifications_sent} batched notifications")
        return notifications_sent
    
    def get_las_vegas_time(self) -> str:
        """Get current Las Vegas time as formatted string."""
        import pytz
        from datetime import datetime
        
        las_vegas_tz = pytz.timezone('America/Los_Angeles')
        las_vegas_time = datetime.now(las_vegas_tz)
        return las_vegas_time.strftime('%Y-%m-%d %I:%M %p PST')
    
    def send_team_notifications_to_all_assignees(self, email_data: Dict, analysis: Dict) -> bool:
        """Send WhatsApp notifications to ALL assigned team members."""
        success_count = 0
        total_assignees = 0
        
        try:
            # Get all assignees from analysis
            all_assignees = analysis.get('all_assignees', [])
            if not all_assignees:
                # Fallback to single assignee
                assignee = analysis.get('suggested_assignee')
                if assignee and assignee != 'Unassigned':
                    all_assignees = [assignee]
            
            if not all_assignees:
                print(f"No assignees found for email {email_data['id']}")
                return False
            
            # Create notification message
            assignee_list = ', '.join(all_assignees) if len(all_assignees) > 1 else all_assignees[0]
            message = f"""NEW EMAIL ALERT
            
From: {email_data['sender']}
Subject: {email_data['subject']}
Category: {analysis['category']}
Priority: {analysis['priority']}/5
Assigned to: {assignee_list}

Summary: {analysis.get('summary', 'Email requires attention')}

Keywords: {', '.join(analysis.get('keywords', []))}

Please check your email and respond as needed.

- JGV Email Tracker"""
            
            # Send to each assignee
            for assignee in all_assignees:
                total_assignees += 1
                whatsapp_number = self.team_members.get(assignee)
                
                if not whatsapp_number:
                    print(f"No WhatsApp number found for {assignee}")
                    continue
                
                # Send via Green API
                if self.send_whatsapp_message(whatsapp_number, message):
                    success_count += 1
                    print(f"Notification sent to {assignee}")
                else:
                    print(f"❌ Failed to send notification to {assignee}")
            
            print(f"[GMAIL] Sent {success_count}/{total_assignees} notifications successfully")
            return success_count > 0
            
        except Exception as e:
            print(f"Error sending team notifications: {e}")
            return False
    
    def send_team_notification(self, email_data: Dict, analysis: Dict) -> bool:
        """Legacy method - redirects to new multi-assignee method."""
        return self.send_team_notifications_to_all_assignees(email_data, analysis)
    
    def send_whatsapp_message(self, phone_number: str, message: str) -> bool:
        """Send WhatsApp message via Green API."""
        try:
            # Use consistent environment variable names with the rest of the app
            green_api_instance = os.getenv('GREEN_API_INSTANCE_ID', '7105263120')
            green_api_token = os.getenv('GREEN_API_TOKEN')
            
            if not green_api_token:
                print("[GMAIL] Green API token not configured")
                print("[GMAIL] Please set GREEN_API_TOKEN in your .env file")
                return False
            
            url = f"https://api.green-api.com/waInstance{green_api_instance}/sendMessage/{green_api_token}"
            
            payload = {
                "chatId": phone_number,
                "message": message
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                print(f"[GMAIL] WhatsApp notification sent to {phone_number}")
                # Update database to mark as sent
                self.mark_whatsapp_sent(phone_number, True)
                return True
            else:
                print(f"[GMAIL] WhatsApp send failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"[GMAIL] Error sending WhatsApp: {e}")
            return False
    
    def mark_whatsapp_sent(self, phone_number: str, sent: bool):
        """Mark WhatsApp notification as sent in database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE email_history 
                SET whatsapp_sent = ? 
                WHERE assigned_to IN (
                    SELECT team_member FROM team_member_rules 
                    WHERE team_member IN (
                        SELECT key FROM (
                            SELECT 'James Taylor' as key, '19056064550@c.us' as value
                            UNION SELECT 'Breyden', '12894434373@c.us'
                            UNION SELECT 'Ezechiel', '12894434373@c.us'
                            UNION SELECT 'Dustin Salinas', '19054251997@c.us'
                        ) WHERE value = ?
                    )
                )
                AND processed_at >= datetime('now', '-1 hour')
            ''', (sent, phone_number))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[GMAIL] Error updating WhatsApp status: {e}")
    
    def run_automated_scan(self, hours_back: int = 24):
        """Run automated scan based on active watch rules only."""
        print("[GMAIL] Starting automated scan based on active watch rules...")
        
        try:
            # Get watch rules from web interface
            watch_rules = self.get_watch_rules_from_web_interface()
            
            if not watch_rules:
                print("[GMAIL] No active watch rules found. Automated scan cancelled.")
                print("[GMAIL] Please configure email watch rules in the web interface.")
                return
            
            # Scan emails based on active rules
            emails = self.scan_recent_emails(hours_back=hours_back)
            
            if not emails:
                print(f"[GMAIL] No emails found matching active watch rules in last {hours_back} hours")
                return
            
            processed_count = 0
            notifications_sent = 0
            category_counts = {}
            
            # Collect all emails for batched notifications
            emails_by_assignee = {}
            
            print(f"[GMAIL] Processing {len(emails)} emails matching active rules...")
            
            for email_data in emails:
                result = self.process_email(email_data, batch_notifications=True)
                if result['success']:
                    processed_count += 1
                    category = result.get('category', 'other')
                    
                    # Group emails by assignee for batching
                    assignees = result.get('assigned_to', [])
                    for assignee in assignees:
                        if assignee not in emails_by_assignee:
                            emails_by_assignee[assignee] = []
                        emails_by_assignee[assignee].append({
                            'email_data': email_data,
                            'analysis': result
                        })
            
            # Send batched notifications
            if emails_by_assignee:
                notifications_sent = self.send_batched_notifications(emails_by_assignee)
            
            # Count categories for summary
            for assignee_emails in emails_by_assignee.values():
                for email_item in assignee_emails:
                    category = email_item['analysis']['category']
                    category_counts[category] = category_counts.get(category, 0) + 1
            
            # Send rule-based summary
            self.send_rule_based_summary(processed_count, notifications_sent, category_counts, len(watch_rules))
            
            print(f"[GMAIL] Processed {processed_count} emails, sent {notifications_sent} notifications")
            
        except Exception as e:
            print(f"Error in automated scan: {e}")
    
    def send_rule_based_summary(self, processed_count: int, notifications_sent: int, category_counts: Dict, rule_count: int):
        """Send summary based on active watch rules to group chat."""
        group_chat_id = os.getenv('WHATSAPP_GROUP_CHAT_ID', '120363401025025313@g.us')
        
        if processed_count > 0:
            # Build category breakdown
            category_lines = []
            for category, count in category_counts.items():
                    category_lines.append(f"{category.replace('_', ' ').title()}: {count}")
            
            category_breakdown = '\n'.join(category_lines)
            
            message = f"""EMAIL TRACKER SUMMARY

Emails processed: {processed_count}
Active watch rules: {rule_count}
Notifications sent: {notifications_sent}
Scan time: {datetime.now().strftime('%H:%M %p')}

Category breakdown:
{category_breakdown}

All matching emails have been assigned to team members.

- JGV Email Tracker (Automated)"""
        else:
            message = f"""EMAIL TRACKER SUMMARY

No new emails matching active rules
Active watch rules: {rule_count}
Scan time: {datetime.now().strftime('%H:%M %p')}

- JGV Email Tracker (Automated)"""
        
        self.send_whatsapp_message(group_chat_id, message)
    
    def send_onboarding_summary(self, processed_count: int, notifications_sent: int):
        """Legacy method - redirects to rule-based summary."""
        category_counts = {'onboarding': processed_count} if processed_count > 0 else {}
        self.send_rule_based_summary(processed_count, notifications_sent, category_counts, 1)
        
    def send_group_summary(self, processed_count: int, notifications_sent: int):
        """Legacy method - redirects to rule-based summary."""
        category_counts = {'other': processed_count} if processed_count > 0 else {}
        self.send_rule_based_summary(processed_count, notifications_sent, category_counts, 0)
    
    def get_email_history(self, limit: int = 50) -> List[Dict]:
        """Get recent email processing history from production database."""
        return self.db.get_email_history(limit)


# Automated scanning scheduler
class GmailScheduler:
    """Scheduler for automated Gmail scanning - only runs when enabled in web interface."""
    
    def __init__(self, gmail_tracker: GmailTracker):
        self.gmail_tracker = gmail_tracker
        self.running = False
        self.thread = None
    
    def is_auto_scan_enabled(self) -> bool:
        """Check if automatic scanning is enabled in web interface settings."""
        try:
            settings_file = 'gmail_automation_settings.json'
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    return settings.get('enableAutoScan', False)  # Default to FALSE
            return False
        except Exception as e:
            print(f"[GMAIL] Error checking auto-scan setting: {e}")
            return False
    
    def start_scheduler(self):
        """Start the automated scanning scheduler - only if enabled."""
        if self.running:
            return
            
        if not self.is_auto_scan_enabled():
            print("[GMAIL] Automated scanning is disabled in web interface")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        print("[GMAIL] Scheduler started - will check for enabled scans twice daily")
    
    def stop_scheduler(self):
        """Stop the automated scanning scheduler."""
        self.running = False
        if self.thread:
            self.thread.join()
        print("[GMAIL] Scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop - checks settings before each scan."""
        while self.running:
            try:
                # Check if auto-scan is still enabled
                if not self.is_auto_scan_enabled():
                    print("[GMAIL] Auto-scan disabled, stopping scheduler")
                    self.running = False
                    break
                
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
        
        # Set up Gmail API - production or local
        try:
            # Try production OAuth first (environment variables)
            if os.getenv('GOOGLE_CLIENT_ID') and os.getenv('GOOGLE_CLIENT_SECRET'):
                print("[GMAIL] Using production OAuth (environment variables)")
                gmail_tracker_instance.setup_production_gmail_service()
            elif os.path.exists('credentials.json'):
                print("[GMAIL] Using local credentials.json")
                gmail_tracker_instance.setup_gmail_api()
            else:
                print("[GMAIL] No OAuth credentials found - authentication required via web interface")
        except Exception as e:
            print(f"[GMAIL] Setup error: {e}")
        
        # Print status about automation
        print("[GMAIL] Gmail tracker initialized")
        print("[GMAIL] Automated scanning is DISABLED by default")
        print("[GMAIL] Enable in web interface to activate scheduled scans")
    
    return gmail_tracker_instance


def create_settings_from_web_interface():
    """Helper to create settings file from web interface (for testing)."""
    # Example settings structure - this would normally come from the web interface
    example_settings = {
        "enableAutoScan": False,  # Default to OFF
        "watchRules": [
            {
                "subject": "New Tech Onboarding",
                "sender": "",
                "body": "",
                "category": "onboarding",
                "assignees": ["James Taylor"],
                "notes": "Default onboarding rule",
                "created_at": datetime.now().isoformat()
            }
        ],
        "teamMembers": [
            {"name": "James Taylor", "phone": "19056064550@c.us"},
            {"name": "Breyden", "phone": "12894434373@c.us"},
            {"name": "Ezechiel", "phone": "12894434373@c.us"},
            {"name": "Dustin Salinas", "phone": "19054251997@c.us"}
        ]
    }
    
    with open('gmail_automation_settings.json', 'w') as f:
        json.dump(example_settings, f, indent=2)
    print("Example settings file created: gmail_automation_settings.json")

if __name__ == "__main__":
    # Test the Gmail tracker
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "create-settings":
        create_settings_from_web_interface()
        sys.exit(0)
    
    tracker = GmailTracker()
    
    if tracker.setup_gmail_api():
        print("Testing Gmail tracker...")
        emails = tracker.scan_recent_emails(hours_back=24)
        print(f"Found {len(emails)} emails matching active watch rules")
        
        if emails:
            for email in emails[:3]:  # Process first 3 emails
                result = tracker.process_email(email)
                print(f"Processed: {result}")
        else:
            print("No emails found. Make sure you have active watch rules configured.")
            print("Run 'python gmail_tracker.py create-settings' to create example settings.")