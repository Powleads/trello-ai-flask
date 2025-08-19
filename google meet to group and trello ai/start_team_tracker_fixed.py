#!/usr/bin/env python3
"""
Team Update Tracker Startup Script
Launches the multi-app web interface with proper configuration
"""

import os
import sys
import subprocess
import time
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
        print("[ERROR] Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these in your .env file or environment.")
        return False
    
    return True

def install_dependencies():
    """Install required Python packages."""
    print("[INFO] Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("[OK] Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to install dependencies: {e}")
        return False

def test_integrations():
    """Test Trello and Green API integrations."""
    print("[INFO] Testing integrations...")
    
    try:
        # Test Trello integration
        from trello_integration import test_trello_integration
        if test_trello_integration():
            print("[OK] Trello integration working")
        else:
            print("[WARN] Trello integration issues detected")
        
        # Test Green API integration  
        from green_api_integration import test_green_api
        if test_green_api():
            print("[OK] Green API integration working")
        else:
            print("[WARN] Green API integration issues detected")
            
        return True
        
    except Exception as e:
        print(f"[ERROR] Integration test failed: {e}")
        return False

def start_web_app():
    """Start the Flask web application."""
    print("[INFO] Starting Team Update Tracker web application...")
    print("[INFO] Access the dashboard at: http://localhost:5000")
    print("[INFO] Team Tracker at: http://localhost:5000/team-tracker")
    print("[INFO] Google Meet app at: http://localhost:5000/google-meet")
    print("\nPress Ctrl+C to stop the server\n")
    
    try:
        # Import and run the web app
        from web_app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped by user")
    except Exception as e:
        print(f"[ERROR] Error starting web app: {e}")

def main():
    """Main startup function."""
    print("*** JGV EEsystems Team Update Tracker ***")
    print("=" * 50)
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Check environment
    if not check_environment():
        print("\n[INFO] Create a .env file with the required variables:")
        print("""
TRELLO_API_KEY=your_trello_api_key
TRELLO_API_SECRET=your_trello_api_secret
TRELLO_TOKEN=your_trello_token
GREEN_API_TOKEN=your_green_api_token
GREEN_API_INSTANCE_ID=7105263120
SECRET_KEY=your_secret_key_here
""")
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Test integrations
    if not test_integrations():
        print("[WARN] Some integrations have issues, but continuing...")
    
    # Start web app
    start_web_app()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)