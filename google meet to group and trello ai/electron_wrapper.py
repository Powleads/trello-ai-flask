#!/usr/bin/env python3
"""
Electron wrapper for the Flask app
Adds CORS support and configurable port for desktop environment
"""

import os
import sys
from flask_cors import CORS

# Import the main web app
from web_app import app

def configure_for_electron():
    """Configure Flask app for Electron environment"""
    
    # Enable CORS for Electron
    CORS(app, resources={
        r"/*": {
            "origins": ["http://localhost:*", "file://*"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Disable Flask debug mode in production
    app.config['DEBUG'] = os.environ.get('ELECTRON_ENV') != 'production'
    
    # Set secret key if not already set
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'electron-trello-ai-secret-key-change-in-production')
    
    # Configure for desktop environment
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for development
    
    # Add desktop-specific routes
    @app.route('/desktop/status')
    def desktop_status():
        """Health check endpoint for Electron"""
        return {
            'status': 'running',
            'mode': 'desktop',
            'version': '1.0.0'
        }
    
    @app.route('/desktop/shutdown', methods=['POST'])
    def desktop_shutdown():
        """Graceful shutdown endpoint"""
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            return {'error': 'Not running with the Werkzeug Server'}, 500
        func()
        return {'status': 'shutting down'}
    
    print("Flask app configured for Electron desktop mode")

if __name__ == '__main__':
    # Get port from environment or use default
    port = int(os.environ.get('FLASK_PORT', 5000))
    host = '127.0.0.1'  # Only listen on localhost for security
    
    # Configure for Electron
    configure_for_electron()
    
    print(f"Starting Flask server on {host}:{port}")
    
    # Run the Flask app
    try:
        app.run(
            host=host,
            port=port,
            debug=False,  # Disable debug in Electron
            use_reloader=False,  # Disable reloader in Electron
            threaded=True  # Enable threading for better performance
        )
    except Exception as e:
        print(f"Error starting Flask server: {e}")
        sys.exit(1)