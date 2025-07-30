"""
Portrait Preview Webapp - Flask Application Factory
Internal tool for generating portrait previews from FileMaker Field Order screenshots
"""

import os
import uuid
from pathlib import Path
from flask import Flask
from loguru import logger
from dotenv import load_dotenv

from .config import load_config


def create_app(config_name=None):
    """Flask application factory"""
    
    # Load environment variables
    load_dotenv()
    
    app = Flask(__name__)
    
    # Load configuration
    config = load_config(config_name or os.getenv('FLASK_ENV', 'development'))
    app.config.update(config.model_dump())
    
    # Configure logging
    setup_logging(app)
    
    # Ensure upload directories exist
    setup_directories(app)
    
    # Register blueprints
    from . import routes
    app.register_blueprint(routes.bp)
    
    logger.info(f"Portrait Preview Webapp initialized in {config_name or 'development'} mode")
    
    return app


def setup_logging(app):
    """Configure loguru logging"""
    log_level = app.config.get('LOG_LEVEL', 'INFO')
    log_file = app.config.get('LOG_FILE', 'logs/app.log')
    
    # Ensure logs directory exists
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        log_file,
        rotation="1 day",
        retention="30 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    )


def setup_directories(app):
    """Ensure required directories exist"""
    dirs = [
        app.config.get('UPLOAD_FOLDER', 'app/static/previews'),
        app.config.get('TEMP_FOLDER', 'tmp'),
        'logs',
        'assets/backgrounds',
        'assets/frames/single',
        'assets/frames/multi'
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True) 