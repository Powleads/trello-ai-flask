#!/usr/bin/env python3
"""
Simple Setup Script for Meeting Automation Tool
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and show the result."""
    print(f"Installing {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   SUCCESS: {description} completed")
            return True
        else:
            print(f"   ERROR: {description} failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ERROR: {description} failed: {e}")
        return False

def main():
    print("Setting up Meeting Automation Tool...\n")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("ERROR: Python 3.8+ required")
        return
    
    print(f"SUCCESS: Python {sys.version.split()[0]} detected")
    
    # Install dependencies
    if not run_command("pip install -r requirements.txt", "dependencies"):
        print("HINT: Try: python -m pip install -r requirements.txt")
        return
    
    # Setup environment
    if not Path('.env').exists():
        if Path('.env.example').exists():
            import shutil
            shutil.copy('.env.example', '.env')
            print("SUCCESS: Created .env file")
        else:
            print("ERROR: .env.example not found")
            return
    else:
        print("SUCCESS: .env file already exists")
    
    # Create directories
    for directory in ['downloads', 'logs', 'temp']:
        Path(directory).mkdir(exist_ok=True)
        print(f"SUCCESS: Created {directory}/ directory")
    
    print("\nSetup complete!")
    print("\nRun quick test:")
    print("   python quick_test.py")
    print("\nProcess a transcript:")
    print("   python src/cli.py process --file examples/sample_transcript_with_trello.txt")
    print("\nFull documentation:")
    print("   See README.md")

if __name__ == "__main__":
    main()