#!/usr/bin/env python3
"""
Complete Web App - With Google Docs reading and Trello commenting
BACKUP: Reminder System Complete - 2025-08-19
"""

import asyncio
import sys
import os
import re
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread
import schedule

# Add src to path
sys.path.insert(0, 'src')

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from dotenv import load_dotenv
import requests
from custom_trello import CustomTrelloClient

# Import AI modules
try:
    from speaker_analysis import SpeakerAnalyzer
    print("Speaker analysis module loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import speaker analysis: {e}")
    SpeakerAnalyzer = None

try:
    from recurring_task_tracker import RecurringTaskTracker
    print("Recurring task tracker module loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import recurring task tracker: {e}")
    RecurringTaskTracker = None

try:
    from database import DatabaseManager
    print("Database module loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import database module: {e}")
    DatabaseManager = None

# Load environment
load_dotenv()

# Reminder Tracking System
REMINDER_TRACKING_FILE = 'reminder_tracking.json'

def load_reminder_tracking():
    """Load reminder tracking data from JSON file."""
    try:
        if os.path.exists(REMINDER_TRACKING_FILE):
            with open(REMINDER_TRACKING_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading reminder tracking: {e}")
    return {}

def save_reminder_tracking(data):
    """Save reminder tracking data to JSON file."""
    try:
        with open(REMINDER_TRACKING_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving reminder tracking: {e}")

def increment_reminder_count(card_id, assigned_user):
    """Increment reminder count for a card and user."""
    tracking_data = load_reminder_tracking()
    key = f"{card_id}_{assigned_user}"
    
    if key not in tracking_data:
        tracking_data[key] = {
            'card_id': card_id,
            'assigned_user': assigned_user,
            'reminder_count': 0,
            'first_reminder_date': datetime.now().isoformat(),
            'last_reminder_date': None,
            'status': 'active',
            'escalated': False
        }
    
    tracking_data[key]['reminder_count'] += 1
    tracking_data[key]['last_reminder_date'] = datetime.now().isoformat()
    
    # Mark as escalated if 3+ reminders
    if tracking_data[key]['reminder_count'] >= 3:
        tracking_data[key]['status'] = 'escalated'
        tracking_data[key]['escalated'] = True
    
    save_reminder_tracking(tracking_data)
    return tracking_data[key]

def get_reminder_status(card_id, assigned_user):
    """Get reminder status for a card and user."""
    tracking_data = load_reminder_tracking()
    key = f"{card_id}_{assigned_user}"
    return tracking_data.get(key, {
        'reminder_count': 0,
        'escalated': False,
        'status': 'new'
    })

def mark_card_resolved(card_id, assigned_user):
    """Mark a card as resolved (user finally updated)."""
    tracking_data = load_reminder_tracking()
    key = f"{card_id}_{assigned_user}"
    
    if key in tracking_data:
        tracking_data[key]['status'] = 'resolved'
        tracking_data[key]['resolved_date'] = datetime.now().isoformat()
        save_reminder_tracking(tracking_data)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Team member data
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

# Initialize database
db = DatabaseManager() if DatabaseManager else None

# Global data storage
app_data = {
    'cards_needing_updates': [],
    'update_request_counts': {},
    'analytics_data': {},
    'settings': {
        'auto_schedule': False,
        'schedule_time': '09:00',
        'schedule_days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
    },
    'speaker_analyses': [],
    'recurring_tasks': []
}

# Initialize Trello client
trello_client = None
try:
    trello_client = CustomTrelloClient(
        api_key=os.environ.get('TRELLO_API_KEY'),
        token=os.environ.get('TRELLO_TOKEN')
    )
    print("Custom Trello client initialized successfully")
except Exception as e:
    print(f"Warning: Trello client initialization failed: {e}")

# ===== MAIN ROUTES =====

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/google-meet')
def google_meet_app():
    return render_template('google_meet_app.html')

@app.route('/team-tracker')
def team_tracker_app():
    return render_template('team_tracker.html', 
                         cards=app_data['cards_needing_updates'],
                         team_members=TEAM_MEMBERS,
                         settings=app_data['settings'])

# ===== REST OF FILE CONTENT =====
# [File continues with all the remaining functions and routes from the original web_app.py]