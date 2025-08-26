"""
Gmail OAuth Handler - Web-based authentication for production deployment
Replaces console-based OAuth with proper web redirect flow
"""

import os
import json
from typing import Optional
from flask import request, redirect, session, url_for, jsonify
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from production_db import get_production_db

class GmailOAuthHandler:
    """Handles Gmail OAuth authentication for production deployment"""
    
    def __init__(self, app=None):
        self.app = app
        self.scopes = ['https://www.googleapis.com/auth/gmail.readonly']
        self.client_config = self._get_client_config()
        self.db = get_production_db()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize OAuth routes with Flask app"""
        app.add_url_rule('/auth/gmail', 'gmail_auth', self.start_oauth_flow)
        app.add_url_rule('/auth/gmail/callback', 'gmail_callback', self.oauth_callback)
        app.add_url_rule('/auth/gmail/status', 'gmail_status', self.get_auth_status)
    
    def _get_client_config(self):
        """Get OAuth client configuration from environment variables"""
        # Check for environment variables first (production)
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        
        if client_id and client_secret:
            return {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": []
                }
            }
        
        # Fallback to credentials.json file (local development)
        credentials_file = 'credentials.json'
        if os.path.exists(credentials_file):
            with open(credentials_file, 'r') as f:
                return json.load(f)
        
        raise ValueError("No OAuth credentials found. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables or provide credentials.json file.")
    
    def _get_redirect_uri(self):
        """Get the correct redirect URI for current environment"""
        if os.getenv('RENDER_EXTERNAL_URL'):
            # Production on Render
            return f"{os.getenv('RENDER_EXTERNAL_URL')}/auth/gmail/callback"
        elif request:
            # Dynamic redirect URI based on current request
            return url_for('gmail_callback', _external=True)
        else:
            # Fallback for local development
            return "http://localhost:5000/auth/gmail/callback"
    
    def start_oauth_flow(self):
        """Start the OAuth flow"""
        try:
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.scopes
            )
            flow.redirect_uri = self._get_redirect_uri()
            
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'  # Force consent to get refresh token
            )
            
            # Store state in session for security
            session['oauth_state'] = state
            
            return redirect(authorization_url)
        
        except Exception as e:
            return jsonify({'error': f'Failed to start OAuth flow: {str(e)}'}), 500
    
    def oauth_callback(self):
        """Handle OAuth callback"""
        try:
            # Verify state parameter
            state = session.get('oauth_state')
            if not state or state != request.args.get('state'):
                return jsonify({'error': 'Invalid state parameter'}), 400
            
            # Get authorization code
            code = request.args.get('code')
            if not code:
                error = request.args.get('error', 'Unknown error')
                return jsonify({'error': f'OAuth error: {error}'}), 400
            
            # Exchange code for tokens
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.scopes,
                state=state
            )
            flow.redirect_uri = self._get_redirect_uri()
            
            flow.fetch_token(authorization_response=request.url)
            credentials = flow.credentials
            
            # Store credentials in database
            creds_data = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None
            }
            
            success = self.db.store_gmail_token(creds_data)
            
            if success:
                # Test the credentials
                gmail_service = build('gmail', 'v1', credentials=credentials)
                profile = gmail_service.users().getProfile(userId='me').execute()
                
                # Clear state from session
                session.pop('oauth_state', None)
                
                return redirect(f'/gmail-tracker?auth=success&email={profile.get("emailAddress", "")}')
            else:
                return jsonify({'error': 'Failed to store credentials'}), 500
        
        except Exception as e:
            return jsonify({'error': f'OAuth callback failed: {str(e)}'}), 500
    
    def get_auth_status(self):
        """Check Gmail authentication status"""
        try:
            credentials = self.get_valid_credentials()
            if credentials:
                # Test the credentials
                gmail_service = build('gmail', 'v1', credentials=credentials)
                profile = gmail_service.users().getProfile(userId='me').execute()
                
                return jsonify({
                    'authenticated': True,
                    'email': profile.get('emailAddress', ''),
                    'expires_at': credentials.expiry.isoformat() if credentials.expiry else None
                })
            else:
                return jsonify({'authenticated': False})
        
        except Exception as e:
            return jsonify({'authenticated': False, 'error': str(e)})
    
    def get_valid_credentials(self) -> Optional[Credentials]:
        """Get valid Gmail credentials, refreshing if necessary"""
        try:
            # Get stored credentials from database
            creds_data = self.db.get_gmail_token()
            if not creds_data:
                return None
            
            # Create credentials object
            credentials = Credentials(
                token=creds_data.get('token'),
                refresh_token=creds_data.get('refresh_token'),
                token_uri=creds_data.get('token_uri'),
                client_id=creds_data.get('client_id'),
                client_secret=creds_data.get('client_secret'),
                scopes=creds_data.get('scopes')
            )
            
            # Set expiry if available
            if creds_data.get('expiry'):
                from datetime import datetime
                credentials.expiry = datetime.fromisoformat(creds_data['expiry'])
            
            # Refresh if expired
            if not credentials.valid:
                if credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                    
                    # Update stored credentials
                    updated_creds_data = {
                        'token': credentials.token,
                        'refresh_token': credentials.refresh_token,
                        'token_uri': credentials.token_uri,
                        'client_id': credentials.client_id,
                        'client_secret': credentials.client_secret,
                        'scopes': credentials.scopes,
                        'expiry': credentials.expiry.isoformat() if credentials.expiry else None
                    }
                    self.db.store_gmail_token(updated_creds_data)
                else:
                    return None
            
            return credentials
        
        except Exception as e:
            print(f"[OAUTH] Error getting valid credentials: {e}")
            return None
    
    def get_gmail_service(self):
        """Get authenticated Gmail service"""
        credentials = self.get_valid_credentials()
        if credentials:
            return build('gmail', 'v1', credentials=credentials)
        return None

# Global OAuth handler
gmail_oauth = GmailOAuthHandler()