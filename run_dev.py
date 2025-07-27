#!/usr/bin/env python3
"""
Portrait Preview Webapp - Development Runner
Run this script to start the development server
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment defaults
os.environ.setdefault('FLASK_APP', 'app')
os.environ.setdefault('FLASK_ENV', 'development')

try:
    from app import create_app
    from loguru import logger
    
    def main():
        """Main entry point"""
        print("=" * 60)
        print("Portrait Preview Webapp - Development Server")
        print("=" * 60)
        
        # Create and configure the app
        app = create_app()
        
        # Print startup info
        print(f"Environment: {app.config.get('FLASK_ENV', 'unknown')}")
        print(f"Debug mode: {app.config.get('DEBUG', False)}")
        print(f"Log level: {app.config.get('LOG_LEVEL', 'INFO')}")
        
        # Check for required directories
        required_dirs = [
            'assets/backgrounds',
            'assets/frames/single', 
            'assets/frames/multi',
            'config',
            'tmp',
            'logs'
        ]
        
        missing_dirs = []
        for dir_path in required_dirs:
            if not Path(dir_path).exists():
                missing_dirs.append(dir_path)
                Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        if missing_dirs:
            print(f"Created missing directories: {', '.join(missing_dirs)}")
        
        # Validate configuration files
        config_files = [
            'config/settings.yaml',
            'config/products.yaml', 
            'config/frames.yaml'
        ]
        
        missing_configs = []
        for config_file in config_files:
            if not Path(config_file).exists():
                missing_configs.append(config_file)
        
        if missing_configs:
            print(f"⚠️  Missing config files: {', '.join(missing_configs)}")
            print("   The app may not function correctly.")
        
        # Check for sample assets
        bg_dir = Path('assets/backgrounds')
        if bg_dir.exists() and not any(bg_dir.glob('*.jpg')):
            print("⚠️  No background images found in assets/backgrounds/")
            print("   Add Virtual Background 2021.jpg or other background images.")
        
        print("-" * 60)
        print("Starting development server...")
        print("Open your browser to: http://localhost:5000")
        print("Press Ctrl+C to stop")
        print("-" * 60)
        
        # Run the development server
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=app.config.get('DEBUG', True),
            use_reloader=True,
            threaded=True
        )

    if __name__ == '__main__':
        main()

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nPlease install the required dependencies:")
    print("  pip install -r requirements.txt")
    sys.exit(1)

except Exception as e:
    print(f"❌ Error starting application: {e}")
    sys.exit(1) 