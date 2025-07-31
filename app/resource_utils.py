import os
import sys
import shutil
from pathlib import Path


def resource_path(rel_path: str) -> Path:
    """Resolve path to bundled resource for PyInstaller compatibility."""
    base_path = Path(getattr(sys, "_MEIPASS", Path(".").resolve()))
    return base_path / rel_path


def ensure_resource_dirs() -> None:
    """Ensure bundled asset folders and config exist in the working directory."""

    for name in ("Composites", "Frames"):
        dst = Path(name)
        if not dst.exists() or not any(dst.iterdir()):
            src = resource_path(name)
            if src.exists():
                shutil.copytree(src, dst, dirs_exist_ok=True)

    cfg_dst = Path("config.json")
    if not cfg_dst.exists():
        cfg_src = resource_path("config.json")
        if cfg_src.exists():
            shutil.copy(cfg_src, cfg_dst)
