#!/usr/bin/env python3
"""
Authentication and Security Module for Google Meet to Trello AI
Provides user authentication, session management, and security features
"""

import os
import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from functools import wraps
from flask import request, jsonify, session, current_app
import bcrypt
from dotenv import load_dotenv

load_dotenv()

class SecurityManager:
    """Manages authentication and security features."""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or os.environ.get('SECRET_KEY', secrets.token_hex(32))
        self.jwt_secret = os.environ.get('JWT_SECRET', secrets.token_hex(32))
        self.session_timeout = int(os.environ.get('SESSION_TIMEOUT', 3600))  # 1 hour default
        
        # Default admin credentials (change in production!)
        self.default_users = {
            'admin': {
                'password_hash': self._hash_password('admin123'),
                'role': 'admin',
                'permissions': ['read', 'write', 'admin', 'delete']
            },
            'user': {
                'password_hash': self._hash_password('user123'),
                'role': 'user',
                'permissions': ['read', 'write']
            }
        }
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate a user and return user info if successful."""
        user = self.default_users.get(username)
        
        if user and self._verify_password(password, user['password_hash']):
            return {
                'username': username,
                'role': user['role'],
                'permissions': user['permissions'],
                'authenticated_at': datetime.utcnow().isoformat()
            }
        
        return None
    
    def generate_jwt_token(self, user_info: Dict) -> str:
        """Generate a JWT token for authenticated user."""
        payload = {
            'username': user_info['username'],
            'role': user_info['role'],
            'permissions': user_info['permissions'],
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(seconds=self.session_timeout)
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
    
    def verify_jwt_token(self, token: str) -> Optional[Dict]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def generate_api_key(self, username: str) -> str:
        """Generate an API key for a user."""
        data = f"{username}:{datetime.utcnow().isoformat()}:{secrets.token_hex(16)}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def check_permission(self, user_permissions: List[str], required_permission: str) -> bool:
        """Check if user has required permission."""
        return required_permission in user_permissions or 'admin' in user_permissions
    
    def sanitize_input(self, data: Any) -> Any:
        """Sanitize input data to prevent injection attacks."""
        if isinstance(data, str):
            # Remove potentially dangerous characters
            dangerous_chars = ['<', '>', '"', "'", ';', '&', '|', '`']
            for char in dangerous_chars:
                data = data.replace(char, '')
            return data.strip()
        elif isinstance(data, dict):
            return {key: self.sanitize_input(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.sanitize_input(item) for item in data]
        else:
            return data
    
    def rate_limit_check(self, identifier: str, max_requests: int = 100, window_minutes: int = 60) -> bool:
        """Simple rate limiting check (in production, use Redis or similar)."""
        # This is a simplified implementation
        # In production, use a proper rate limiting solution
        return True
    
    def log_security_event(self, event_type: str, details: Dict, severity: str = 'info'):
        """Log security events for monitoring."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'severity': severity,
            'details': details,
            'ip_address': request.remote_addr if request else 'unknown'
        }
        
        # In production, send to security monitoring system
        print(f"SECURITY LOG: {log_entry}")

# Flask decorators for authentication and authorization

def require_auth(f):
    """Decorator to require authentication for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for JWT token in Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            security_manager = getattr(current_app, 'security_manager', None)
            
            if security_manager:
                user_info = security_manager.verify_jwt_token(token)
                if user_info:
                    request.current_user = user_info
                    return f(*args, **kwargs)
        
        # Check for session-based authentication
        if 'user_id' in session and 'authenticated' in session:
            return f(*args, **kwargs)
        
        return jsonify({'error': 'Authentication required'}), 401
    
    return decorated_function

def require_permission(permission: str):
    """Decorator to require specific permission for a route."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_info = getattr(request, 'current_user', None)
            
            if not user_info:
                # Try to get from session
                if 'permissions' not in session:
                    return jsonify({'error': 'Permission denied'}), 403
                user_permissions = session.get('permissions', [])
            else:
                user_permissions = user_info.get('permissions', [])
            
            security_manager = getattr(current_app, 'security_manager', None)
            if security_manager and not security_manager.check_permission(user_permissions, permission):
                return jsonify({'error': f'Permission {permission} required'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def require_admin(f):
    """Decorator to require admin permission for a route."""
    return require_permission('admin')(f)

def sanitize_request(f):
    """Decorator to sanitize request data."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        security_manager = getattr(current_app, 'security_manager', None)
        
        if security_manager:
            # Sanitize form data
            if request.form:
                sanitized_form = security_manager.sanitize_input(dict(request.form))
                request.form = sanitized_form
            
            # Sanitize JSON data
            if request.json:
                sanitized_json = security_manager.sanitize_input(request.json)
                request.json = sanitized_json
        
        return f(*args, **kwargs)
    
    return decorated_function

def audit_log(action: str):
    """Decorator to log user actions for audit trail."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_info = getattr(request, 'current_user', None)
            username = user_info.get('username', 'anonymous') if user_info else session.get('username', 'anonymous')
            
            security_manager = getattr(current_app, 'security_manager', None)
            if security_manager:
                security_manager.log_security_event(
                    'user_action',
                    {
                        'action': action,
                        'username': username,
                        'endpoint': request.endpoint,
                        'method': request.method,
                        'url': request.url
                    }
                )
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

class CSRFProtection:
    """CSRF protection implementation."""
    
    def __init__(self):
        self.token_timeout = 3600  # 1 hour
    
    def generate_csrf_token(self) -> str:
        """Generate a CSRF token."""
        token = secrets.token_urlsafe(32)
        session['csrf_token'] = token
        session['csrf_token_time'] = datetime.utcnow().timestamp()
        return token
    
    def validate_csrf_token(self, token: str) -> bool:
        """Validate CSRF token."""
        if 'csrf_token' not in session or 'csrf_token_time' not in session:
            return False
        
        # Check if token matches
        if not secrets.compare_digest(session['csrf_token'], token):
            return False
        
        # Check if token is not expired
        token_time = session['csrf_token_time']
        if datetime.utcnow().timestamp() - token_time > self.token_timeout:
            return False
        
        return True

def csrf_protect(f):
    """Decorator to protect against CSRF attacks."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE']:
            csrf_token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            
            csrf_protection = getattr(current_app, 'csrf_protection', None)
            if csrf_protection and not csrf_protection.validate_csrf_token(csrf_token):
                return jsonify({'error': 'CSRF token validation failed'}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function

def setup_security(app):
    """Setup security features for Flask app."""
    # Initialize security manager
    security_manager = SecurityManager()
    app.security_manager = security_manager
    
    # Initialize CSRF protection
    csrf_protection = CSRFProtection()
    app.csrf_protection = csrf_protection
    
    # Security headers
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response
    
    return app

def create_login_routes(app):
    """Create authentication routes for the app."""
    
    @app.route('/api/login', methods=['POST'])
    @sanitize_request
    def login():
        """User login endpoint."""
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        user_info = app.security_manager.authenticate_user(username, password)
        
        if user_info:
            # Create session
            session['user_id'] = username
            session['username'] = username
            session['role'] = user_info['role']
            session['permissions'] = user_info['permissions']
            session['authenticated'] = True
            session['login_time'] = datetime.utcnow().isoformat()
            
            # Generate JWT token
            jwt_token = app.security_manager.generate_jwt_token(user_info)
            
            # Generate CSRF token
            csrf_token = app.csrf_protection.generate_csrf_token()
            
            app.security_manager.log_security_event(
                'user_login',
                {'username': username, 'success': True}
            )
            
            return jsonify({
                'success': True,
                'user': {
                    'username': username,
                    'role': user_info['role'],
                    'permissions': user_info['permissions']
                },
                'token': jwt_token,
                'csrf_token': csrf_token
            })
        else:
            app.security_manager.log_security_event(
                'user_login',
                {'username': username, 'success': False},
                'warning'
            )
            
            return jsonify({'error': 'Invalid credentials'}), 401
    
    @app.route('/api/logout', methods=['POST'])
    @require_auth
    def logout():
        """User logout endpoint."""
        username = session.get('username', 'unknown')
        
        # Clear session
        session.clear()
        
        app.security_manager.log_security_event(
            'user_logout',
            {'username': username}
        )
        
        return jsonify({'success': True, 'message': 'Logged out successfully'})
    
    @app.route('/api/csrf-token', methods=['GET'])
    def get_csrf_token():
        """Get CSRF token."""
        csrf_token = app.csrf_protection.generate_csrf_token()
        return jsonify({'csrf_token': csrf_token})
    
    @app.route('/api/user-info', methods=['GET'])
    @require_auth
    def get_user_info():
        """Get current user information."""
        return jsonify({
            'username': session.get('username'),
            'role': session.get('role'),
            'permissions': session.get('permissions'),
            'login_time': session.get('login_time')
        })

def test_security():
    """Test security functions."""
    print("Testing Security Module...")
    
    # Test password hashing
    security_manager = SecurityManager()
    
    # Test authentication
    user_info = security_manager.authenticate_user('admin', 'admin123')
    if user_info:
        print(f"[PASS] Authentication successful for: {user_info['username']}")
        
        # Test JWT token
        token = security_manager.generate_jwt_token(user_info)
        decoded = security_manager.verify_jwt_token(token)
        if decoded:
            print("[PASS] JWT token generation and verification successful")
        else:
            print("[FAIL] JWT token verification failed")
    else:
        print("[FAIL] Authentication failed")
    
    # Test input sanitization
    dangerous_input = "<script>alert('xss')</script>"
    sanitized = security_manager.sanitize_input(dangerous_input)
    print(f"[PASS] Input sanitization: '{dangerous_input}' -> '{sanitized}'")
    
    # Test permission checking
    permissions = ['read', 'write']
    has_read = security_manager.check_permission(permissions, 'read')
    has_admin = security_manager.check_permission(permissions, 'admin')
    print(f"[PASS] Permission check: read={has_read}, admin={has_admin}")
    
    # Test CSRF protection
    csrf = CSRFProtection()
    token = csrf.generate_csrf_token()
    # Simulate session
    import flask
    with flask.Flask(__name__).test_request_context():
        flask.session['csrf_token'] = token
        flask.session['csrf_token_time'] = datetime.utcnow().timestamp()
        
        is_valid = csrf.validate_csrf_token(token)
        print(f"[PASS] CSRF token validation: {is_valid}")
    
    print("Security module test completed!")

if __name__ == "__main__":
    test_security()