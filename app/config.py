"""
Configuration management for Portrait Preview Webapp
Loads settings from YAML files with environment variable overrides
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from loguru import logger


class ProductConfig(BaseModel):
    """Product configuration definition"""
    slug: str
    name: str
    code: str
    width_in: float
    height_in: float
    count_images: int
    frame_style_default: str
    parsing_patterns: List[str]
    multi_opening_template: Optional[str] = None

class AppConfig(BaseModel):
    """Main application configuration"""
    
    # Flask settings
    SECRET_KEY: str = Field(default_factory=lambda: os.urandom(24).hex())
    FLASK_ENV: str = "development"
    DEBUG: bool = True
    
    # Paths
    TESSERACT_PATH: Optional[str] = None  # Auto-detect if None
    DROPBOX_ROOT: Optional[str] = None
    UPLOAD_FOLDER: str = "app/static/previews"
    TEMP_FOLDER: str = "tmp"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # OCR settings
    OCR_PSM: int = 6
    OCR_OEM: int = 3
    OCR_MIN_CONFIDENCE: float = 50.0
    
    # Image processing
    MAX_UPLOAD_SIZE: int = 20 * 1024 * 1024  # 20MB
    ALLOWED_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".tif", ".tiff"]
    PX_PER_INCH_DEFAULT: float = 40.0
    MAX_PREVIEW_WIDTH: int = 1920
    
    # UI settings
    BACKGROUND_DEFAULT: str = "Virtual Background 2021.jpg"
    SHOW_LABELS: bool = False
    QUANTITY_BADGE_ENABLED: bool = True
    CROPPING_POLICY: str = "center_crop"  # or "letterbox"
    
    # Layout
    LAYOUT_MARGIN_PX: int = 16
    MIN_ITEM_SIZE_PX: int = 60
    MAX_ITEM_SIZE_RATIO: float = 0.8  # max 80% of background width


def load_yaml_config(file_path: str) -> Dict:
    """Load configuration from YAML file"""
    path = Path(file_path)
    if not path.exists():
        logger.warning(f"Config file not found: {file_path}")
        return {}
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Error loading config file {file_path}: {e}")
        return {}


def load_config(environment: str = "development") -> AppConfig:
    """Load configuration with environment-specific overrides"""
    
    # Load base settings
    base_config = load_yaml_config("config/settings.yaml")
    
    # Load environment-specific settings
    env_config = load_yaml_config(f"config/settings_{environment}.yaml")
    
    # Merge configurations (env overrides base)
    config_dict = {**base_config, **env_config}
    
    # Apply environment variable overrides
    env_overrides = {
        'TESSERACT_PATH': os.getenv('TESSERACT_PATH'),
        'DROPBOX_ROOT': os.getenv('DROPBOX_ROOT'),
        'FLASK_ENV': os.getenv('FLASK_ENV', environment),
        'LOG_LEVEL': os.getenv('LOG_LEVEL'),
        'SECRET_KEY': os.getenv('SECRET_KEY'),
    }
    
    # Only include non-None values
    env_overrides = {k: v for k, v in env_overrides.items() if v is not None}
    config_dict.update(env_overrides)
    
    # Special handling for boolean DEBUG flag
    if 'FLASK_ENV' in config_dict:
        config_dict['DEBUG'] = config_dict['FLASK_ENV'] == 'development'
    
    try:
        return AppConfig(**config_dict)
    except Exception as e:
        logger.error(f"Configuration validation error: {e}")
        # Return default config on validation error
        return AppConfig()


# Global config instance
_config_instance = None

def get_config() -> AppConfig:
    """Get the global configuration instance (legacy function for compatibility)"""
    global _config_instance
    if _config_instance is None:
        _config_instance = load_config()
    return _config_instance


class ProductConfig(BaseModel):
    """Product definition configuration"""
    slug: str
    width_in: float
    height_in: float
    count_images: int = 1
    frame_style_default: str = "none"
    frame_styles_allowed: List[str] = ["none"]
    quantity_behavior: str = "single"  # single, pair, sheet8, qty_from_field
    multi_opening_template: Optional[str] = None
    parsing_patterns: List[str] = []
    orientation_locked: Optional[str] = None  # portrait, landscape


class FrameConfig(BaseModel):
    """Frame asset configuration"""
    product_slug: str
    style: str
    asset_path: str
    opening_boxes: List[List[float]] = []  # List of [x1, y1, x2, y2] relative coords 0-1


def load_product_config() -> Dict:
    """Load product configuration from YAML"""
    config_data = load_yaml_config("config/products.yaml")
    cfg = {"products": config_data.get("products", [])}

    products = {}
    for item in cfg["products"]:
        try:
            product = ProductConfig(**item)
            products[product.slug] = product
        except Exception as e:
            logger.error(f"Error loading product config {item.get('slug', 'unknown')}: {e}")

    cfg["products_by_code"] = {p["code"]: p for p in cfg["products"]}
    cfg["products_by_slug"] = products
    logger.info(f"Loaded {len(products)} product configurations")
    return cfg


def load_frame_config() -> Dict[str, FrameConfig]:
    """Load frame configuration from YAML"""
    config_data = load_yaml_config("config/frames.yaml")
    frames = {}
    
    for item in config_data.get("frames", []):
        try:
            frame = FrameConfig(**item)
            key = f"{frame.product_slug}_{frame.style}"
            frames[key] = frame
        except Exception as e:
            logger.error(f"Error loading frame config {item.get('product_slug', 'unknown')}: {e}")
    
    logger.info(f"Loaded {len(frames)} frame configurations")
    return frames 