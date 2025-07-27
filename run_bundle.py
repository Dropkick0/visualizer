#!/usr/bin/env python3
"""
Main entry point for bundled Portrait Preview Webapp
"""

import sys
import os
from pathlib import Path
import argparse

# Add current directory to Python path for bundled execution
if getattr(sys, 'frozen', False):
    # Running as bundled executable
    bundle_dir = Path(sys.executable).parent
    sys.path.insert(0, str(bundle_dir))
    os.chdir(bundle_dir)
else:
    # Running as script
    sys.path.insert(0, str(Path(__file__).parent))

# Set environment variables for bundled execution
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_DEBUG'] = '0'

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Portrait Preview Webapp')
    parser.add_argument('--port', type=int, default=5000, help='Port to run on')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--help-setup', action='store_true', help='Show setup instructions')
    
    args = parser.parse_args()
    
    if args.help_setup:
        show_setup_help()
        return
    
    try:
        # Import Flask app
        from app import create_app
        
        # Create app instance
        app = create_app()
        
        print("🎨 Portrait Preview Webapp")
        print("=" * 50)
        print(f"📡 Starting server on http://{args.host}:{args.port}")
        print("🌐 Open this URL in your web browser")
        print("🛑 Press Ctrl+C to stop the server")
        print("=" * 50)
        
        # Start the Flask development server
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            threaded=True
        )
        
    except ImportError as e:
        print(f"❌ Failed to import Flask app: {e}")
        print("Make sure all dependencies are installed.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)


def show_setup_help():
    """Show setup and usage instructions"""
    help_text = """
🎨 Portrait Preview Webapp - Setup Guide
========================================

PREREQUISITES:
1. Windows 10 or Windows 11
2. English OCR language pack installed

FIRST TIME SETUP:
Run as Administrator in PowerShell:
> Add-WindowsCapability -Online -Name "Language.OCR~~~en-US~0.0.1.0"

STARTING THE APP:
- Double-click "Launch_Portrait_Preview.bat", OR
- Run this executable directly: PortraitPreview.exe

USING THE WEBAPP:
1. Open browser to http://localhost:5000
2. Upload FileMaker screenshot (PNG/JPG format)
3. Enter Dropbox folder path with customer images
4. Select background and frame options  
5. Click "Generate Preview"
6. Download the generated portrait preview

FOLDER STRUCTURE:
PortraitPreview/
├── PortraitPreview.exe          # Main application
├── Launch_Portrait_Preview.bat  # Easy launcher
├── assets/                      # Backgrounds and frames
├── config/                      # Product and frame configs
└── README.md                    # Detailed documentation

TROUBLESHOOTING:
- OCR errors: Install Windows OCR language pack (see setup above)
- Port in use: Close other apps using port 5000
- Missing images: Check Dropbox folder path is correct
- App won't start: Try running as Administrator

For detailed help, see README.md
"""
    print(help_text)


if __name__ == "__main__":
    main() 