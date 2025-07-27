#!/usr/bin/env python3
"""
Production deployment configuration for Portrait Preview Webapp.

This module provides production-ready WSGI server configuration,
environment setup, and deployment utilities.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any

# Production WSGI application
def create_production_app():
    """Create production Flask application with proper configuration."""
    # Set production environment
    os.environ['FLASK_ENV'] = 'production'
    os.environ['FLASK_DEBUG'] = 'False'
    
    # Import after setting environment
    from app import create_app
    
    # Production configuration
    config = {
        'SECRET_KEY': os.environ.get('SECRET_KEY', 'production-secret-key-change-me'),
        'DEBUG': False,
        'TESTING': False,
        'TEMP_FOLDER': os.environ.get('TEMP_FOLDER', '/tmp/portrait_preview'),
        'UPLOAD_FOLDER': os.environ.get('UPLOAD_FOLDER', '/var/uploads/portrait_preview'),
        'LOG_FILE': os.environ.get('LOG_FILE', '/var/log/portrait_preview/app.log'),
        'LOG_LEVEL': os.environ.get('LOG_LEVEL', 'INFO'),
        'ASSETS_DIRECTORY': os.environ.get('ASSETS_DIRECTORY', '/opt/portrait_preview/assets'),
        'MAX_UPLOAD_SIZE': int(os.environ.get('MAX_UPLOAD_SIZE', '20971520')),  # 20MB
        'SESSION_COOKIE_SECURE': True,
        'SESSION_COOKIE_HTTPONLY': True,
        'SESSION_COOKIE_SAMESITE': 'Lax',
        'PERMANENT_SESSION_LIFETIME': 3600,  # 1 hour
    }
    
    # Create application
    app = create_app(config)
    
    # Setup production logging
    setup_production_logging(app)
    
    # Create required directories
    create_production_directories(config)
    
    return app


def setup_production_logging(app):
    """Configure production logging."""
    log_file = app.config.get('LOG_FILE', '/var/log/portrait_preview/app.log')
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
    
    # Ensure log directory exists
    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Suppress noisy loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    

def create_production_directories(config: Dict[str, Any]):
    """Create required production directories."""
    directories = [
        config['TEMP_FOLDER'],
        config['UPLOAD_FOLDER'],
        Path(config['LOG_FILE']).parent,
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        

def check_production_requirements():
    """Check that production requirements are met."""
    errors = []
    
    # Check Python version
    if sys.version_info < (3, 8):
        errors.append("Python 3.8 or higher required")
    
    # Check environment variables
    required_env_vars = ['SECRET_KEY']
    for var in required_env_vars:
        if not os.environ.get(var):
            errors.append(f"Environment variable {var} is required")
    
    # Check Tesseract installation
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
    except Exception:
        errors.append("Tesseract OCR not installed or not accessible")
    
    # Check write permissions
    temp_folder = os.environ.get('TEMP_FOLDER', '/tmp/portrait_preview')
    try:
        test_file = Path(temp_folder) / 'test_write'
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text('test')
        test_file.unlink()
    except Exception:
        errors.append(f"No write permission to temp folder: {temp_folder}")
    
    return errors


# WSGI application instance
app = create_production_app()

if __name__ == '__main__':
    # Check requirements
    errors = check_production_requirements()
    if errors:
        print("❌ Production requirements not met:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    
    print("✅ Production requirements check passed")
    
    # Run with Waitress WSGI server
    try:
        from waitress import serve
        
        host = os.environ.get('HOST', '0.0.0.0')
        port = int(os.environ.get('PORT', '8000'))
        threads = int(os.environ.get('THREADS', '4'))
        
        print(f"🚀 Starting Portrait Preview Webapp on {host}:{port}")
        print(f"   Threads: {threads}")
        print(f"   Environment: production")
        
        serve(
            app,
            host=host,
            port=port,
            threads=threads,
            channel_timeout=120,
            cleanup_interval=30,
            connection_limit=1000,
            url_scheme='https' if os.environ.get('HTTPS', '').lower() == 'true' else 'http'
        )
        
    except ImportError:
        print("❌ Waitress not installed. Install with: pip install waitress")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1) 