"""
Test suite for Portrait Preview Webapp.

This package contains unit tests, integration tests, and test utilities
for validating the functionality of the portrait preview generation system.
"""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path for imports
app_dir = Path(__file__).parent.parent
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir)) 