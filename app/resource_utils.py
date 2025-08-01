import os
import sys
import shutil
from pathlib import Path
from PIL import Image


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

    # Auto-generate 10x20 composites if missing
    generate_10x20_composites(Path("Composites"))

    cfg_dst = Path("config.json")
    if not cfg_dst.exists():
        cfg_src = resource_path("config.json")
        if cfg_src.exists():
            shutil.copy(cfg_src, cfg_dst)


def generate_10x20_composites(composites_dir: Path) -> None:
    """Create 10x20 composite images by doubling existing 5x10 files."""
    if not composites_dir.exists():
        return

    for file in composites_dir.glob("*5x10 3 Image.jpg"):
        target_name = file.name.replace("5x10", "10x20")
        target = composites_dir / target_name
        if target.exists():
            continue

        try:
            img = Image.open(file)
            doubled = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
            doubled.save(target, format="JPEG")
        except Exception:
            continue

