"""
Image search functionality for finding photos in Dropbox folder
Based on 4-digit codes from FileMaker wishlist
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from loguru import logger
from PIL import Image


class DropboxImageSearcher:
    """Search for images in Dropbox folder based on 4-digit codes"""
    
    def __init__(self, dropbox_root: str):
        self.dropbox_root = Path(dropbox_root)
        self.supported_extensions = ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp']
        
        logger.info(f"Dropbox image searcher initialized: {self.dropbox_root}")
    
    def find_images_by_codes(self, codes: List[str]) -> Dict[str, List[Path]]:
        """
        Find images in Dropbox folder that end with the specified 4-digit codes
        
        Args:
            codes: List of 4-digit codes to search for
            
        Returns:
            Dictionary mapping codes to lists of image file paths
        """
        results = {}
        
        if not self.dropbox_root.exists():
            logger.warning(f"Dropbox folder not found: {self.dropbox_root}")
            return results
        
        logger.info(f"Searching for images with codes: {codes}")
        
        for code in codes:
            if len(code) != 4 or not code.isdigit():
                logger.warning(f"Invalid code format: {code} (must be 4 digits)")
                continue
            
            matching_images = self._search_code_recursive(code)
            results[code] = matching_images
            
            logger.debug(f"Code {code}: found {len(matching_images)} images")
            for img in matching_images[:3]:  # Log first 3 matches
                logger.debug(f"  - {img.name}")
        
        total_found = sum(len(images) for images in results.values())
        logger.info(f"✅ Found {total_found} total images for {len(codes)} codes")
        
        return results
    
    def _search_code_recursive(self, code: str) -> List[Path]:
        """Recursively search for images ending with the specified code"""
        matching_files = []
        
        try:
            # Search all subdirectories recursively with no depth limit
            for ext in self.supported_extensions:
                # Pattern: any filename ending with the 4-digit code before extension
                # Examples: IMG_1555.jpg, Portrait_1555.tif, 1555.jpeg, etc.
                pattern = f"*{code}{ext}"
                matches = list(self.dropbox_root.rglob(pattern))
                matching_files.extend(matches)
                
                # Also search for files with code anywhere in the name (more flexible)
                pattern_flexible = f"*{code}*{ext}"
                flexible_matches = list(self.dropbox_root.rglob(pattern_flexible))
                
                # Only add flexible matches that actually end with the code before extension
                for match in flexible_matches:
                    stem = match.stem  # filename without extension
                    if stem.endswith(code) and match not in matching_files:
                        matching_files.append(match)
                
                # Additional patterns for common camera naming conventions
                # _MG_0033.jpg, DSC_0033.jpg, IMG_0033.jpg, etc.
                camera_patterns = [
                    f"*_MG_{code}{ext}",
                    f"*DSC_{code}{ext}", 
                    f"*IMG_{code}{ext}",
                    f"*{code}_*{ext}",
                    f"*-{code}{ext}",
                    f"*_{code}{ext}"
                ]
                
                for camera_pattern in camera_patterns:
                    camera_matches = list(self.dropbox_root.rglob(camera_pattern))
                    for match in camera_matches:
                        if match not in matching_files:
                            matching_files.append(match)
        
        except Exception as e:
            logger.error(f"Error searching for code {code}: {e}")
        
        # Sort by modification time (newest first)
        matching_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        # Log search results for debugging
        if matching_files:
            logger.info(f"Code {code}: Found {len(matching_files)} images")
            for img in matching_files[:3]:
                logger.debug(f"  - {img.relative_to(self.dropbox_root)}")
        else:
            logger.warning(f"Code {code}: No images found")
        
        return matching_files
    
    def validate_images(self, image_paths: List[Path]) -> List[Path]:
        """Validate that image files can be opened and are valid"""
        valid_images = []
        
        for img_path in image_paths:
            try:
                # Try to open and verify the image
                with Image.open(img_path) as img:
                    # Basic validation - ensure it has dimensions
                    width, height = img.size
                    if width > 0 and height > 0:
                        valid_images.append(img_path)
                    else:
                        logger.warning(f"Invalid image dimensions: {img_path}")
            
            except Exception as e:
                logger.warning(f"Cannot open image {img_path}: {e}")
        
        return valid_images
    
    def get_image_info(self, image_path: Path) -> Dict:
        """Get detailed information about an image file"""
        try:
            with Image.open(image_path) as img:
                return {
                    'path': image_path,
                    'filename': image_path.name,
                    'size': img.size,
                    'mode': img.mode,
                    'format': img.format,
                    'file_size': image_path.stat().st_size,
                    'modified': image_path.stat().st_mtime
                }
        except Exception as e:
            logger.error(f"Error getting image info for {image_path}: {e}")
            return {'path': image_path, 'error': str(e)}
    
    def find_images_for_order_items(self, order_items: List) -> Dict[str, Dict[str, List[Path]]]:
        """
        Find images for each order item based on their assigned codes
        
        Args:
            order_items: List of StructuredItem objects with codes
            
        Returns:
            Dictionary mapping product_slug to code-to-images mapping
        """
        all_codes = []
        item_codes = {}
        
        # Collect all unique codes and track which items need which codes
        for item in order_items:
            product_slug = item.product_slug
            codes = item.codes
            
            item_codes[product_slug] = codes
            all_codes.extend(codes)
        
        # Remove duplicates while preserving order
        unique_codes = list(dict.fromkeys(all_codes))
        
        # Search for all codes at once
        code_to_images = self.find_images_by_codes(unique_codes)
        
        # Map results back to order items
        results = {}
        for product_slug, codes in item_codes.items():
            results[product_slug] = {}
            for code in codes:
                results[product_slug][code] = code_to_images.get(code, [])
        
        return results


def create_image_searcher(config) -> Optional[DropboxImageSearcher]:
    """Create image searcher from app configuration"""
    dropbox_root = getattr(config, 'DROPBOX_ROOT', None)
    
    if not dropbox_root:
        logger.warning("No Dropbox root path configured - AHK should have set DROPBOX_ROOT")
        return None
    
    logger.info(f"Using Dropbox path from config: {dropbox_root}")
    return DropboxImageSearcher(dropbox_root) 
