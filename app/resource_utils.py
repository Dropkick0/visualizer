import os
import sys
import shutil
from pathlib import Path


def resource_path(rel_path: str) -> Path:
    """Resolve path to bundled resource for PyInstaller compatibility."""
    base_path = Path(getattr(sys, "_MEIPASS", Path(".").resolve()))
    return base_path / rel_path


def ensure_resource_dirs():
    """Ensure bundled asset folders exist in the working directory."""
    for name in ("Composites", "Frames"):
        dst = Path(name)
        if not dst.exists() or not any(dst.iterdir()):
            src = resource_path(name)
            if src.exists():
                shutil.copytree(src, dst, dirs_exist_ok=True)
