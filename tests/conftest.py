"""
Pytest configuration and fixtures for Portrait Preview Webapp tests.

Provides shared fixtures, test configuration, and utilities
for running tests across the entire application.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Generator
from PIL import Image, ImageDraw, ImageFont
import json

from app import create_app
from app.config import load_config


@pytest.fixture(scope='session')
def app():
    """Create and configure a test Flask application."""
    app = create_app({
        'TESTING': True,
        'SECRET_KEY': 'test-key',
        'TEMP_FOLDER': tempfile.mkdtemp(),
        'UPLOAD_FOLDER': tempfile.mkdtemp(),
        'DEBUG': True,
        'WTF_CSRF_ENABLED': False  # Disable CSRF for testing
    })
    
    yield app
    
    # Cleanup temp directories
    try:
        shutil.rmtree(app.config['TEMP_FOLDER'])
        shutil.rmtree(app.config['UPLOAD_FOLDER'])
    except:
        pass


@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test runner for CLI commands."""
    return app.test_cli_runner()


@pytest.fixture(scope='session')
def test_data_dir():
    """Get the test data directory path."""
    return Path(__file__).parent / 'data'


class TestConfig:
    """Simple test configuration wrapper."""
    def __init__(self, app_config, products):
        self.app_config = app_config
        self.products = products
        
        # Expose app_config attributes directly for compatibility
        for key, value in app_config.model_dump().items():
            setattr(self, key, value)


@pytest.fixture(scope='session')
def sample_config():
    """Load sample configuration for testing."""
    from app.config import AppConfig, ProductConfig
    
    # Create test product configurations
    test_products = {
        "8x10_basic": ProductConfig(
            slug="8x10_basic",
            width_in=8.0,
            height_in=10.0,
            count_images=2,  # Allow multiple images for testing
            frame_style_default="basic",
            frame_styles_allowed=["basic", "cherry"],
            parsing_patterns=["8x10.*basic", "8x10.*print", "8x10.*digital"],
            orientation_locked=None
        ),
        "5x7_wallet": ProductConfig(
            slug="5x7_wallet",
            width_in=5.0,
            height_in=7.0,
            count_images=1,
            frame_style_default="basic",
            frame_styles_allowed=["basic", "cherry"],
            parsing_patterns=["5x7.*wallet", "wallet", "5x7.*cherry"],
            orientation_locked="portrait"
        ),
        "8x10_trio": ProductConfig(
            slug="8x10_trio",
            width_in=8.0,
            height_in=10.0,
            count_images=3,
            frame_style_default="cherry",
            frame_styles_allowed=["cherry"],
            parsing_patterns=["trio.*cherry", "8x10.*trio", "8x10.*cherry.*frame"],
            multi_opening_template="trio_template.png"
        )
    }
    
    # Create AppConfig with test settings
    app_config = AppConfig(
        SECRET_KEY='dev-key-change-in-production',
        FLASK_ENV='development',
        DEBUG=True,
        TESSERACT_PATH=None,
        DROPBOX_ROOT=None,
        UPLOAD_FOLDER="app/static/previews",
        TEMP_FOLDER="tmp",
        LOG_LEVEL="INFO",
        LOG_FILE="logs/app.log",
        OCR_PSM=6,
        OCR_OEM=3,
        OCR_MIN_CONFIDENCE=50.0,
        MAX_UPLOAD_SIZE=20971520,
        ALLOWED_EXTENSIONS=[".jpg", ".jpeg", ".png", ".tif", ".tiff"],
        PX_PER_INCH_DEFAULT=40.0,
        MAX_PREVIEW_WIDTH=1920,
        BACKGROUND_DEFAULT="Virtual Background 2021.jpg",
        SHOW_LABELS=False,
        QUANTITY_BADGE_ENABLED=True,
        CROPPING_POLICY="center_crop",
        LAYOUT_MARGIN_PX=16,
        MIN_ITEM_SIZE_PX=60,
        MAX_ITEM_SIZE_RATIO=0.8
    )
    
    # Create wrapper with both app config and products
    return TestConfig(app_config, test_products)


@pytest.fixture
def temp_work_dir():
    """Create a temporary work directory for test processing."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_screenshot(temp_work_dir):
    """Create a sample FileMaker screenshot for testing."""
    screenshot_path = temp_work_dir / "test_screenshot.png"
    
    # Create a realistic-looking FileMaker screenshot
    img = Image.new('RGB', (1200, 800), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a system font, fallback to default
    try:
        font = ImageFont.truetype("arial.ttf", 14)
        header_font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()
        header_font = font
    
    # Draw table header
    draw.rectangle([50, 100, 1150, 130], fill='lightgray', outline='black')
    draw.text((60, 105), "PORTRAITS", fill='black', font=header_font)
    
    # Draw sample order rows
    sample_orders = [
        "2 8x10 Basic Print Digital                    1234, 5678",
        "1 5x7 Cherry Wallet                          9876",
        "1 8x10 Trio Cherry Frame                     1111, 2222, 3333", 
        "2 Wallets Basic                              4444, 5555"
    ]
    
    y_pos = 140
    for order in sample_orders:
        draw.rectangle([50, y_pos, 1150, y_pos + 25], fill='white', outline='gray')
        draw.text((60, y_pos + 5), order, fill='black', font=font)
        y_pos += 30
    
    img.save(screenshot_path)
    return screenshot_path


@pytest.fixture
def sample_customer_images(temp_work_dir):
    """Create sample customer images with 4-digit codes."""
    images_dir = temp_work_dir / "customer_images"
    images_dir.mkdir()
    
    # Create sample images with different codes
    codes = ['1234', '5678', '9876', '1111', '2222', '3333', '4444', '5555']
    image_paths = {}
    
    for code in codes:
        # Create a simple colored image
        img = Image.new('RGB', (400, 600), color=(100 + int(code) % 155, 150, 200))
        draw = ImageDraw.Draw(img)
        
        # Add code text to image
        try:
            font = ImageFont.truetype("arial.ttf", 48)
        except:
            font = ImageFont.load_default()
        
        draw.text((150, 250), code, fill='white', font=font)
        
        # Save with realistic filename
        image_path = images_dir / f"IMG_{code}.jpg"
        img.save(image_path, 'JPEG', quality=85)
        image_paths[code] = image_path
    
    return images_dir, image_paths


@pytest.fixture
def sample_frame_assets(temp_work_dir):
    """Create sample frame assets for testing."""
    frames_dir = temp_work_dir / "assets" / "frames"
    frames_dir.mkdir(parents=True)
    
    # Create sample frame images
    frame_configs = [
        {'name': 'cherry_single.png', 'size': (800, 1000), 'opening': (100, 100, 600, 800)},
        {'name': 'cherry_trio.png', 'size': (1200, 800), 'opening1': (50, 100, 350, 600), 
         'opening2': (400, 100, 700, 600), 'opening3': (750, 100, 1050, 600)}
    ]
    
    frame_paths = {}
    
    for frame_config in frame_configs:
        img = Image.new('RGBA', frame_config['size'], color=(139, 69, 19, 255))  # Brown frame
        draw = ImageDraw.Draw(img)
        
        # Cut out openings (make transparent)
        if 'opening' in frame_config:
            x1, y1, x2, y2 = frame_config['opening']
            for y in range(y1, y2):
                for x in range(x1, x2):
                    img.putpixel((x, y), (0, 0, 0, 0))
        
        # Handle multiple openings for trio frames
        for i in range(1, 4):
            opening_key = f'opening{i}'
            if opening_key in frame_config:
                x1, y1, x2, y2 = frame_config[opening_key]
                for y in range(y1, y2):
                    for x in range(x1, x2):
                        img.putpixel((x, y), (0, 0, 0, 0))
        
        frame_path = frames_dir / frame_config['name']
        img.save(frame_path, 'PNG')
        frame_paths[frame_config['name']] = frame_path
    
    return frames_dir, frame_paths


@pytest.fixture
def sample_background_assets(temp_work_dir):
    """Create sample background assets for testing."""
    backgrounds_dir = temp_work_dir / "assets" / "backgrounds"
    backgrounds_dir.mkdir(parents=True)
    
    # Create sample background
    img = Image.new('RGB', (1200, 1600), color=(245, 245, 245))  # Light gray
    draw = ImageDraw.Draw(img)
    
    # Add subtle pattern
    for x in range(0, 1200, 50):
        for y in range(0, 1600, 50):
            draw.rectangle([x, y, x+25, y+25], fill=(250, 250, 250))
    
    bg_path = backgrounds_dir / "test_background.jpg"
    img.save(bg_path, 'JPEG', quality=95)
    
    return backgrounds_dir, bg_path


@pytest.fixture
def mock_tesseract_result():
    """Create a mock Tesseract OCR result for testing."""
    class MockOCRResult:
        def __init__(self):
            self.lines = [
                "2 8x10 Basic Print Digital                    1234, 5678",
                "1 5x7 Cherry Wallet                          9876",
                "1 8x10 Trio Cherry Frame                     1111, 2222, 3333",
                "2 Wallets Basic                              4444, 5555"
            ]
            self.words = [word for line in self.lines for word in line.split()]
            self.confidence_avg = 85.5
            self.roi_bbox = (50, 100, 1150, 250)
    
    return MockOCRResult()


@pytest.fixture
def sample_parsed_items():
    """Create sample parsed order items for testing."""
    from app.parse import OrderItem
    
    items = [
        OrderItem(
            quantity=2,
            product_slug="8x10_basic_print",
            width_in=8.0,
            height_in=10.0,
            orientation="portrait",
            frame_style="digital",
            codes=["1234", "5678"],
            source_line_text="2 8x10 Basic Print Digital                    1234, 5678"
        ),
        OrderItem(
            quantity=1,
            product_slug="5x7_wallet",
            width_in=5.0,
            height_in=7.0,
            orientation="portrait", 
            frame_style="cherry",
            codes=["9876"],
            source_line_text="1 5x7 Cherry Wallet                          9876"
        ),
        OrderItem(
            quantity=1,
            product_slug="8x10_trio",
            width_in=8.0,
            height_in=10.0,
            orientation="landscape",
            frame_style="cherry",
            codes=["1111", "2222", "3333"],
            source_line_text="1 8x10 Trio Cherry Frame                     1111, 2222, 3333"
        )
    ]
    
    return items


class TestDataHelper:
    """Helper class for creating test data and scenarios."""
    
    @staticmethod
    def create_test_session_data(temp_dir: Path) -> Dict[str, Any]:
        """Create a complete test session with all required files."""
        session_id = "test-session-12345"
        work_dir = temp_dir / session_id
        work_dir.mkdir()
        
        return {
            'session_id': session_id,
            'work_dir': work_dir,
            'screenshot_path': work_dir / "screenshot.png",
            'sit_folder_path': temp_dir / "customer_images",
            'background_name': "test_background.jpg"
        }
    
    @staticmethod
    def create_error_scenario(error_type: str) -> Dict[str, Any]:
        """Create test scenarios for specific error conditions."""
        scenarios = {
            'no_tesseract': {
                'mock_error': 'tesseract: command not found',
                'expected_error': 'TesseractNotInstalledError'
            },
            'no_items_detected': {
                'ocr_lines': [],
                'expected_error': 'NoItemsDetectedError'
            },
            'missing_images': {
                'codes_requested': ['1234', '5678', '9999'],
                'codes_found': ['1234', '5678'],
                'expected_error': 'ImageFilesNotFoundError'
            },
            'invalid_image': {
                'file_content': b'not an image',
                'expected_error': 'InvalidImageFormatError'
            }
        }
        
        return scenarios.get(error_type, {})


@pytest.fixture
def test_helper():
    """Provide the TestDataHelper class as a fixture."""
    return TestDataHelper 