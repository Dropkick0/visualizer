"""
Utility functions for Portrait Preview Webapp
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional
from loguru import logger


def validate_folder_path(path_str: str) -> bool:
    """Basic validation of folder path string"""
    if not path_str or not path_str.strip():
        return False
    
    try:
        path = Path(path_str.strip('\'"'))
        return path.exists() and path.is_dir()
    except (OSError, ValueError):
        return False


def get_available_backgrounds() -> List[Dict[str, str]]:
    """Get list of available background images"""
    backgrounds = []
    backgrounds_dir = Path("assets/backgrounds")
    
    if not backgrounds_dir.exists():
        logger.warning(f"Backgrounds directory not found: {backgrounds_dir}")
        return backgrounds
    
    # Look for image files
    for ext in ['.jpg', '.jpeg', '.png', '.tif', '.tiff']:
        for bg_file in backgrounds_dir.glob(f"*{ext}"):
            backgrounds.append({
                'filename': bg_file.name,
                'display_name': bg_file.stem.replace('_', ' ').title(),
                'path': str(bg_file)
            })
    
    # Sort by display name
    backgrounds.sort(key=lambda x: x['display_name'])
    
    logger.info(f"Found {len(backgrounds)} background images")
    return backgrounds


def clean_code_candidate(tok: str) -> str:
    """
    Clean OCR text to extract 4-digit image codes
    Maps common OCR errors: O->0, I->1, l->1, B->8, S->5
    """
    if not tok:
        return ""
    
    # Character mapping for common OCR errors
    char_map = str.maketrans({
        'O': '0', 'o': '0',
        'I': '1', 'l': '1',
        'B': '8', 
        'S': '5',
        'G': '6'
    })
    
    # Apply character mapping and keep only digits
    cleaned = tok.translate(char_map)
    digits = ''.join(ch for ch in cleaned if ch.isdigit())
    
    # Return last 4 digits if longer, or all digits if shorter
    return digits[-4:] if len(digits) >= 4 else digits


def extract_quantity_from_text(text: str) -> int:
    """Extract quantity from order line text"""
    text_lower = text.lower().strip()
    
    # Look for explicit quantity numbers at start
    qty_match = re.match(r'^(\d+)', text_lower)
    if qty_match:
        return int(qty_match.group(1))
    
    # Look for quantity keywords
    if 'pair' in text_lower:
        return 2
    elif 'sheet' in text_lower:
        # Look for "sheet of X" pattern
        sheet_match = re.search(r'sheet\s+of\s+(\d+)', text_lower)
        if sheet_match:
            return int(sheet_match.group(1))
        return 8  # Default wallet sheet count
    elif 'trio' in text_lower or 'triple' in text_lower:
        return 3
    
    return 1  # Default single quantity


def extract_product_size_from_text(text: str) -> Optional[str]:
    """Extract product size from description text"""
    text_lower = text.lower()
    
    # Common size patterns
    size_patterns = [
        r'(\d+)x(\d+)',  # 8x10, 5x7, etc.
        r'(\d+)\s*x\s*(\d+)',  # 8 x 10
        r'(\d+)×(\d+)',  # with multiplication symbol
    ]
    
    for pattern in size_patterns:
        match = re.search(pattern, text_lower)
        if match:
            w, h = match.groups()
            return f"{w}x{h}"
    
    # Wallet pattern
    if 'wallet' in text_lower:
        return 'wallet'
    
    return None


def extract_frame_style_from_text(text: str) -> str:
    """Extract frame style from description text"""
    text_lower = text.lower()
    
    # Frame style keywords in order of preference
    if 'black' in text_lower and ('cherry' in text_lower or 'mat' in text_lower):
        return 'digital_mat_black_cherry'
    elif 'cherry' in text_lower:
        return 'cherry'
    elif 'black' in text_lower:
        return 'black'
    elif 'white' in text_lower:
        return 'white'
    elif 'gold' in text_lower:
        return 'gold'
    elif 'silver' in text_lower:
        return 'silver'
    
    return 'none'  # Default no frame


def extract_image_codes_from_text(text: str) -> List[str]:
    """Extract 4-digit image codes from order line text"""
    # Find all potential 4+ digit sequences
    digit_sequences = re.findall(r'(\d{4,})', text)
    
    codes = []
    for seq in digit_sequences:
        # Clean and normalize the code
        cleaned = clean_code_candidate(seq)
        if len(cleaned) >= 4:
            # Take last 4 digits
            code = cleaned[-4:]
            if code not in codes:  # Avoid duplicates
                codes.append(code)
    
    return codes


def normalize_filename_for_search(filename: str) -> str:
    """Normalize filename for consistent searching"""
    # Convert to lowercase and normalize Unicode
    import unicodedata
    normalized = unicodedata.normalize('NFC', filename.lower())
    return normalized


def find_image_files_in_folder(folder_path: Path, max_depth: int = 5) -> Dict[str, Path]:
    """
    Scan folder recursively for image files and map by 4-digit codes
    Returns dict: {code4: file_path}
    """
    code_map = {}
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.tif', '.tiff']
    
    def scan_directory(dir_path: Path, current_depth: int = 0):
        if current_depth > max_depth:
            return
        
        try:
            for item in dir_path.iterdir():
                if item.is_file():
                    # Check if it's an image file
                    if item.suffix.lower() in allowed_extensions:
                        # Extract 4-digit code from filename
                        codes = extract_image_codes_from_text(item.stem)
                        for code in codes:
                            if code not in code_map:
                                code_map[code] = item
                            else:
                                # Handle duplicates - prefer larger file
                                existing_size = code_map[code].stat().st_size
                                new_size = item.stat().st_size
                                if new_size > existing_size:
                                    logger.info(f"Replacing {code}: {code_map[code].name} -> {item.name} (larger)")
                                    code_map[code] = item
                
                elif item.is_dir() and current_depth < max_depth:
                    # Recurse into subdirectory
                    scan_directory(item, current_depth + 1)
        
        except (OSError, PermissionError) as e:
            logger.warning(f"Error scanning directory {dir_path}: {e}")
    
    logger.info(f"Scanning folder: {folder_path}")
    scan_directory(folder_path)
    logger.info(f"Found {len(code_map)} image files with codes")
    
    return code_map


def crop_to_aspect_ratio(image, target_width: int, target_height: int):
    """
    Crop image to target aspect ratio using center crop
    Returns cropped PIL Image
    """
    from PIL import Image
    
    if not isinstance(image, Image.Image):
        raise ValueError("Input must be a PIL Image")
    
    current_width, current_height = image.size
    target_ratio = target_width / target_height
    current_ratio = current_width / current_height
    
    if abs(current_ratio - target_ratio) < 0.01:
        # Already close enough to target ratio
        return image
    
    if current_ratio > target_ratio:
        # Image is too wide - crop left and right
        new_width = int(current_height * target_ratio)
        left = (current_width - new_width) // 2
        right = left + new_width
        return image.crop((left, 0, right, current_height))
    else:
        # Image is too tall - crop top and bottom
        new_height = int(current_width / target_ratio)
        top = (current_height - new_height) // 2
        bottom = top + new_height
        return image.crop((0, top, current_width, bottom))


def ensure_directory_exists(path: Path) -> None:
    """Ensure directory exists, create if necessary"""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create directory {path}: {e}")
        raise


def safe_filename(filename: str) -> str:
    """Generate safe filename by removing/replacing problematic characters"""
    # Remove path separators and other problematic chars
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove control characters
    safe_name = re.sub(r'[\x00-\x1f\x7f]', '', safe_name)
    # Limit length
    if len(safe_name) > 200:
        name, ext = os.path.splitext(safe_name)
        safe_name = name[:200-len(ext)] + ext
    
    return safe_name or 'unnamed_file' 