#!/usr/bin/env python3
"""
Team Update Tracker Startup Script
Simple launcher without Unicode characters for Windows compatibility
"""

import os
import sys
import subprocess
from pathlib import Path

def check_environment():
    """Check if all required environment variables are set."""
    required_vars = [
        'TRELLO_API_KEY',
        'TRELLO_API_SECRET', 
        'TRELLO_TOKEN',
        'GREEN_API_TOKEN'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("ERROR: Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these in your .env file")
        return False
    
    return True

def install_dependencies():
    """Install required Python packages."""
    print("Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install dependencies: {e}")
        return False

def start_web_app():
    """Start the Flask web application."""
    print("Starting Team Update Tracker...")
    print("Dashboard: http://localhost:5000")
    print("Team Tracker: http://localhost:5000/team-tracker")
    print("Analytics: http://localhost:5000/analytics")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        from web_app import app
        app.run(debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\nServer stopped")
    except Exception as e:
        print(f"Error: {e}")

def main():
    """Main function."""
    print("JGV EEsystems Team Update Tracker")
    print("=" * 40)
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Check environment
    if not check_environment():
        print("\nCreate a .env file with:")
        print("TRELLO_API_KEY=your_key")
        print("TRELLO_API_SECRET=your_secret") 
        print("TRELLO_TOKEN=your_token")
        print("GREEN_API_TOKEN=your_token")
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Start app
    start_web_app()
    return True

if __name__ == "__main__":
    main()