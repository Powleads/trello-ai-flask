#!/usr/bin/env python3
"""
Google OAuth Setup Script

Interactive script to set up Google Drive API authentication
and generate the necessary credentials for the meeting automation tool.
"""

import json
import os
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

console = Console()

# Required scopes for Google Drive API
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]

def main():
    """Main setup function."""
    console.print(Panel.fit(
        "[bold blue]Google Drive API Setup[/bold blue]\n"
        "This script will help you set up Google Drive API authentication\n"
        "for the Meeting Automation Tool.",
        border_style="blue"
    ))
    
    # Check for existing credentials
    if Path('credentials.json').exists():
        console.print("[yellow]Found existing credentials.json file[/yellow]")
        if not Confirm.ask("Do you want to use the existing credentials file?"):
            setup_new_credentials()
    else:
        setup_new_credentials()
    
    # Run OAuth flow
    run_oauth_flow()
    
    # Test the connection
    test_connection()
    
    console.print("[green]✅ Google Drive API setup complete![/green]")
    console.print("[yellow]You can now use the meeting automation tool with Google Drive integration.[/yellow]")


def setup_new_credentials():
    """Set up new Google API credentials."""
    console.print("\n[bold]Setting up Google API Credentials[/bold]")
    console.print("To get your Google API credentials:")
    console.print("1. Go to https://console.cloud.google.com/")
    console.print("2. Create a new project or select an existing one")
    console.print("3. Enable the Google Drive API")
    console.print("4. Go to 'Credentials' and create OAuth 2.0 Client ID")
    console.print("5. Download the credentials JSON file")
    console.print()
    
    choice = Prompt.ask(
        "Choose setup method",
        choices=["file", "manual", "env"],
        default="file"
    )
    
    if choice == "file":
        setup_from_file()
    elif choice == "manual":
        setup_manual_entry()
    elif choice == "env":
        setup_from_environment()


def setup_from_file():
    """Set up credentials from downloaded JSON file."""
    file_path = Prompt.ask("Enter path to your credentials JSON file")
    
    if not Path(file_path).exists():
        console.print("[red]File not found. Please check the path.[/red]")
        return
    
    try:
        # Copy the file to the expected location
        import shutil
        shutil.copy(file_path, 'credentials.json')
        console.print("[green]✅ Credentials file copied successfully[/green]")
    except Exception as e:
        console.print(f"[red]Error copying file: {e}[/red]")


def setup_manual_entry():
    """Set up credentials by manual entry."""
    console.print("\n[bold]Manual Credentials Entry[/bold]")
    
    client_id = Prompt.ask("Enter your Google Client ID")
    client_secret = Prompt.ask("Enter your Google Client Secret", password=True)
    
    credentials_data = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
        }
    }
    
    with open('credentials.json', 'w') as f:
        json.dump(credentials_data, f, indent=2)
    
    console.print("[green]✅ Credentials file created[/green]")


def setup_from_environment():
    """Set up credentials from environment variables."""
    console.print("\n[bold]Environment Variables Setup[/bold]")
    
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        console.print("[red]GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables not found[/red]")
        console.print("Please set these variables or choose a different setup method.")
        return
    
    credentials_data = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
        }
    }
    
    with open('credentials.json', 'w') as f:
        json.dump(credentials_data, f, indent=2)
    
    console.print("[green]✅ Credentials file created from environment variables[/green]")


def run_oauth_flow():
    """Run the OAuth authorization flow."""
    console.print("\n[bold]Running OAuth Authorization[/bold]")
    
    if not Path('credentials.json').exists():
        console.print("[red]credentials.json not found. Please run setup first.[/red]")
        return
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        
        console.print("[yellow]Opening browser for authorization...[/yellow]")
        console.print("If the browser doesn't open automatically, copy the URL that appears.")
        
        creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            import pickle
            pickle.dump(creds, token)
        
        console.print("[green]✅ Authorization complete![/green]")
        
    except Exception as e:
        console.print(f"[red]OAuth flow failed: {e}[/red]")
        console.print("Please check your credentials and try again.")


def test_connection():
    """Test the Google Drive API connection."""
    console.print("\n[bold]Testing Connection[/bold]")
    
    try:
        from googleapiclient.discovery import build
        import pickle
        
        # Load credentials
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
        
        # Build service
        service = build('drive', 'v3', credentials=creds)
        
        # Test API call
        about = service.about().get(fields="user").execute()
        user_email = about.get('user', {}).get('emailAddress', 'Unknown')
        
        console.print(f"[green]✅ Connection successful![/green]")
        console.print(f"[blue]Connected as: {user_email}[/blue]")
        
        # List some files to verify permissions
        results = service.files().list(pageSize=5, fields="files(id, name)").execute()
        files = results.get('files', [])
        
        if files:
            console.print(f"[blue]Can access {len(files)} files[/blue]")
        else:
            console.print("[yellow]No files found (this is normal for new accounts)[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Connection test failed: {e}[/red]")
        console.print("Please check your setup and try again.")


def cleanup_credentials():
    """Clean up existing credentials for fresh setup."""
    files_to_remove = ['credentials.json', 'token.pickle']
    
    for file_path in files_to_remove:
        if Path(file_path).exists():
            try:
                os.remove(file_path)
                console.print(f"[yellow]Removed {file_path}[/yellow]")
            except Exception as e:
                console.print(f"[red]Failed to remove {file_path}: {e}[/red]")


def show_setup_instructions():
    """Show detailed setup instructions."""
    instructions = """
[bold]Detailed Google Drive API Setup Instructions[/bold]

1. [blue]Go to Google Cloud Console[/blue]
   - Visit: https://console.cloud.google.com/
   - Sign in with your Google account

2. [blue]Create or Select Project[/blue]
   - Click on the project dropdown at the top
   - Either select an existing project or create a new one
   - Give it a name like "Meeting Automation Tool"

3. [blue]Enable Google Drive API[/blue]
   - Go to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click on it and press "Enable"

4. [blue]Create Credentials[/blue]
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client ID"
   - Choose "Desktop application" as the application type
   - Give it a name like "Meeting Automation"
   - Click "Create"

5. [blue]Download Credentials[/blue]
   - Click the download button for your newly created OAuth 2.0 Client ID
   - Save the file as "credentials.json" in your project directory

6. [blue]Run This Script[/blue]
   - Run this script again and choose "file" option
   - Point to your downloaded credentials.json file

[yellow]Note: You only need to do this setup once![/yellow]
"""
    
    console.print(Panel(instructions, border_style="green"))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        show_setup_instructions()
    elif len(sys.argv) > 1 and sys.argv[1] == "--cleanup":
        cleanup_credentials()
        console.print("[green]Credentials cleaned up. Run script again to set up fresh.[/green]")
    else:
        main()