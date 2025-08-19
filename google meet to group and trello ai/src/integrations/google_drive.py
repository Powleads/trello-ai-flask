"""
Google Drive Integration

Handles authentication, file monitoring, and download of meeting transcripts
from Google Drive using the Google Drive API.
"""

import asyncio
import json
import os
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import io

logger = logging.getLogger(__name__)

# Scopes required for Google Drive API
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]

# File types to monitor for transcripts
TRANSCRIPT_MIMETYPES = [
    'text/plain',
    'application/vnd.google-apps.document',
    'application/pdf'
]


class GoogleDriveClient:
    """
    Google Drive client for monitoring and downloading meeting transcripts.
    
    Supports OAuth2 authentication, push notifications, and file monitoring.
    """
    
    def __init__(self, 
                 credentials_file: Optional[str] = None,
                 token_file: Optional[str] = None):
        """
        Initialize Google Drive client.
        
        Args:
            credentials_file: Path to credentials.json file
            token_file: Path to store OAuth tokens
        """
        self.credentials_file = credentials_file or 'credentials.json'
        self.token_file = token_file or 'token.pickle'
        self.service = None
        self.credentials = None
        
        # Initialize credentials
        self._load_credentials()
    
    def _load_credentials(self):
        """Load and refresh OAuth2 credentials."""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, run OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Failed to refresh credentials: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_file):
                    # Try to get credentials from environment
                    client_id = os.getenv('GOOGLE_CLIENT_ID')
                    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
                    
                    if client_id and client_secret:
                        # Create credentials dict
                        creds_dict = {
                            "installed": {
                                "client_id": client_id,
                                "client_secret": client_secret,
                                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                                "token_uri": "https://oauth2.googleapis.com/token",
                                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
                            }
                        }
                        
                        # Save temporary credentials file
                        with open(self.credentials_file, 'w') as f:
                            json.dump(creds_dict, f)
                    else:
                        raise FileNotFoundError(
                            f"Credentials file not found: {self.credentials_file}. "
                            "Please run the setup script or provide GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET"
                        )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        self.credentials = creds
        self.service = build('drive', 'v3', credentials=creds)
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection to Google Drive API.
        
        Returns:
            Dict containing connection status and user info
        """
        try:
            about = self.service.about().get(fields="user").execute()
            return {
                'status': 'success',
                'user': about.get('user', {}),
                'email': about.get('user', {}).get('emailAddress', 'unknown')
            }
        except HttpError as e:
            logger.error(f"Google Drive connection test failed: {e}")
            raise Exception(f"Connection test failed: {e}")
    
    async def list_files(self, 
                        folder_id: Optional[str] = None,
                        query: Optional[str] = None,
                        max_results: int = 100) -> List[Dict[str, Any]]:
        """
        List files in Google Drive.
        
        Args:
            folder_id: ID of folder to search in
            query: Custom search query
            max_results: Maximum number of results
            
        Returns:
            List of file metadata dictionaries
        """
        try:
            # Build query
            search_query = []
            
            if folder_id:
                search_query.append(f"'{folder_id}' in parents")
            
            # Look for transcript files
            mime_queries = [f"mimeType='{mime}'" for mime in TRANSCRIPT_MIMETYPES]
            search_query.append(f"({' or '.join(mime_queries)})")
            
            # Add custom query
            if query:
                search_query.append(query)
            
            final_query = ' and '.join(search_query)
            
            results = self.service.files().list(
                q=final_query,
                pageSize=max_results,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime, size, parents)"
            ).execute()
            
            return results.get('files', [])
            
        except HttpError as e:
            logger.error(f"Error listing files: {e}")
            raise
    
    async def download_file(self, 
                           file_id: str, 
                           output_path: Optional[str] = None) -> str:
        """
        Download a file from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            output_path: Local path to save file
            
        Returns:
            Path to downloaded file
        """
        try:
            # Get file metadata
            file_metadata = self.service.files().get(fileId=file_id).execute()
            file_name = file_metadata['name']
            mime_type = file_metadata['mimeType']
            
            # Determine output path
            if not output_path:
                downloads_dir = Path('downloads')
                downloads_dir.mkdir(exist_ok=True)
                output_path = downloads_dir / file_name
            
            output_path = Path(output_path)
            
            # Handle Google Docs export
            if mime_type == 'application/vnd.google-apps.document':
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='text/plain'
                )
            else:
                request = self.service.files().get_media(fileId=file_id)
            
            # Download file
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            
            while done is False:
                status, done = downloader.next_chunk()
                logger.debug(f"Download progress: {int(status.progress() * 100)}%")
            
            # Save to file
            with open(output_path, 'wb') as f:
                f.write(fh.getvalue())
            
            logger.info(f"Downloaded file: {output_path}")
            return str(output_path)
            
        except HttpError as e:
            logger.error(f"Error downloading file {file_id}: {e}")
            raise
    
    async def watch_folder(self, 
                          folder_id: str,
                          webhook_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Set up push notifications for folder changes.
        
        Args:
            folder_id: Google Drive folder ID to watch
            webhook_url: URL to receive push notifications
            
        Returns:
            Watch resource information
        """
        try:
            import uuid
            
            if not webhook_url:
                webhook_url = os.getenv('GOOGLE_DRIVE_WEBHOOK_URL')
                if not webhook_url:
                    raise ValueError("Webhook URL not provided")
            
            # Create watch request
            watch_request = {
                'id': str(uuid.uuid4()),
                'type': 'web_hook',
                'address': webhook_url,
                'payload': True
            }
            
            # Start watching
            response = self.service.files().watch(
                fileId=folder_id,
                body=watch_request
            ).execute()
            
            logger.info(f"Started watching folder {folder_id}")
            return response
            
        except HttpError as e:
            logger.error(f"Error setting up folder watch: {e}")
            raise
    
    async def stop_watch(self, channel_id: str, resource_id: str):
        """
        Stop a push notification channel.
        
        Args:
            channel_id: Channel ID from watch response
            resource_id: Resource ID from watch response
        """
        try:
            self.service.channels().stop(body={
                'id': channel_id,
                'resourceId': resource_id
            }).execute()
            
            logger.info(f"Stopped watching channel {channel_id}")
            
        except HttpError as e:
            logger.error(f"Error stopping watch: {e}")
            raise
    
    async def find_folder_by_name(self, folder_name: str) -> Optional[str]:
        """
        Find a folder by name and return its ID.
        
        Args:
            folder_name: Name of the folder to find
            
        Returns:
            Folder ID if found, None otherwise
        """
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            results = self.service.files().list(
                q=query,
                fields="files(id, name)"
            ).execute()
            
            folders = results.get('files', [])
            if folders:
                return folders[0]['id']
            
            return None
            
        except HttpError as e:
            logger.error(f"Error finding folder: {e}")
            raise
    
    async def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """
        Create a new folder in Google Drive.
        
        Args:
            folder_name: Name of the folder to create
            parent_id: Parent folder ID (optional)
            
        Returns:
            Created folder ID
        """
        try:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                folder_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"Created folder '{folder_name}' with ID: {folder_id}")
            return folder_id
            
        except HttpError as e:
            logger.error(f"Error creating folder: {e}")
            raise
    
    async def get_recent_files(self, 
                              hours: int = 24,
                              folder_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get files modified in the last N hours.
        
        Args:
            hours: Number of hours to look back
            folder_id: Folder to search in (optional)
            
        Returns:
            List of recently modified files
        """
        try:
            # Calculate time threshold
            threshold = datetime.utcnow() - timedelta(hours=hours)
            threshold_str = threshold.isoformat() + 'Z'
            
            # Build query
            query_parts = [f"modifiedTime > '{threshold_str}'"]
            
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")
            
            # Look for transcript files
            mime_queries = [f"mimeType='{mime}'" for mime in TRANSCRIPT_MIMETYPES]
            query_parts.append(f"({' or '.join(mime_queries)})")
            
            query = ' and '.join(query_parts)
            
            results = self.service.files().list(
                q=query,
                orderBy='modifiedTime desc',
                fields="files(id, name, mimeType, modifiedTime, size)"
            ).execute()
            
            return results.get('files', [])
            
        except HttpError as e:
            logger.error(f"Error getting recent files: {e}")
            raise
    
    async def monitor_folder_polling(self, 
                                   folder_id: str,
                                   callback: callable,
                                   interval: int = 60):
        """
        Monitor folder for changes using polling (fallback for webhooks).
        
        Args:
            folder_id: Folder ID to monitor
            callback: Function to call when new files are found
            interval: Polling interval in seconds
        """
        logger.info(f"Starting polling monitor for folder {folder_id}")
        processed_files = set()
        
        while True:
            try:
                # Get recent files
                recent_files = await self.get_recent_files(
                    hours=1, 
                    folder_id=folder_id
                )
                
                # Process new files
                for file_info in recent_files:
                    file_id = file_info['id']
                    
                    if file_id not in processed_files:
                        logger.info(f"New file detected: {file_info['name']}")
                        
                        try:
                            # Download and process
                            local_path = await self.download_file(file_id)
                            await callback(local_path, file_info)
                            processed_files.add(file_id)
                            
                        except Exception as e:
                            logger.error(f"Error processing file {file_id}: {e}")
                
                await asyncio.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("Polling monitor stopped")
                break
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(interval)


# Utility functions
async def setup_drive_monitoring(folder_name: str = "Meeting Transcripts") -> GoogleDriveClient:
    """
    Set up Google Drive monitoring for a specific folder.
    
    Args:
        folder_name: Name of folder to monitor
        
    Returns:
        Configured GoogleDriveClient instance
    """
    client = GoogleDriveClient()
    
    # Test connection
    await client.test_connection()
    
    # Find or create folder
    folder_id = await client.find_folder_by_name(folder_name)
    if not folder_id:
        folder_id = await client.create_folder(folder_name)
        logger.info(f"Created monitoring folder: {folder_name}")
    else:
        logger.info(f"Found existing folder: {folder_name}")
    
    return client


if __name__ == "__main__":
    # Test the Google Drive client
    async def test_client():
        client = GoogleDriveClient()
        result = await client.test_connection()
        print(f"Connection test: {result}")
        
        files = await client.list_files(max_results=5)
        print(f"Recent files: {len(files)}")
        for file in files[:3]:
            print(f"  - {file['name']} ({file['mimeType']})")
    
    asyncio.run(test_client())