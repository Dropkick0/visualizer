import os
import sys
from pathlib import Path


def resource_path(rel_path: str) -> Path:
    """Resolve path to bundled resource for PyInstaller compatibility."""
    base_path = Path(getattr(sys, "_MEIPASS", Path(".").resolve()))
    return base_path / rel_path
