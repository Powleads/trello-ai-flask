#!/usr/bin/env python3
"""
Web Interface Launcher

Simple script to start the web interface.
"""

import subprocess
import sys
import webbrowser
import time
from pathlib import Path

def main():
    print("🚀 Starting Meeting Automation Web Interface...")
    print("=" * 50)
    
    # Check if templates directory exists
    if not Path('templates').exists():
        print("❌ Templates directory not found!")
        return
    
    # Check if app.py exists
    if not Path('app.py').exists():
        print("❌ app.py not found!")
        return
    
    print("✅ Starting Flask web server...")
    print("🌐 Opening browser in 3 seconds...")
    print("📍 URL: http://localhost:5000")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Open browser after a short delay
    def open_browser():
        time.sleep(3)
        try:
            webbrowser.open('http://localhost:5000')
        except:
            pass
    
    import threading
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Start Flask app
    try:
        subprocess.run([sys.executable, 'app.py'], check=True)
    except KeyboardInterrupt:
        print("\n👋 Shutting down web server...")
    except Exception as e:
        print(f"❌ Error starting web server: {e}")

if __name__ == "__main__":
    main()