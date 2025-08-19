#!/usr/bin/env python3
"""
Simple Runner for Meeting Automation Tool
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

def main():
    """Simple CLI wrapper."""
    if len(sys.argv) < 2:
        print("🤖 Meeting Automation Tool")
        print()
        print("Quick commands:")
        print("  python run.py test         - Test all integrations")
        print("  python run.py sample       - Process sample transcript")
        print("  python run.py process FILE - Process your transcript file")
        print()
        print("Full CLI:")
        print("  python src/cli.py --help")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'test':
        print("🧪 Running quick test...")
        os.system('python quick_test.py')
    
    elif command == 'sample':
        print("📝 Processing sample transcript...")
        os.system('python src/cli.py process --file examples/sample_transcript_with_trello.txt')
    
    elif command == 'process':
        if len(sys.argv) < 3:
            print("❌ Please provide a file path")
            print("   python run.py process your_transcript.txt")
            return
        
        file_path = sys.argv[2]
        if not Path(file_path).exists():
            print(f"❌ File not found: {file_path}")
            return
        
        print(f"📝 Processing: {file_path}")
        os.system(f'python src/cli.py process --file "{file_path}"')
    
    elif command == 'setup':
        print("🔧 Running setup...")
        os.system('python setup.py')
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Available: test, sample, process, setup")

if __name__ == "__main__":
    main()