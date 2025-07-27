"""
Image mapping module for Portrait Preview Webapp
Maps 4-digit image codes to actual image files in the Sit Folder
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from .utils import find_image_files_in_folder, normalize_filename_for_search
from .parse import StructuredItem


@dataclass
class ImageMatch:
    """Represents a matched image file"""
    code: str
    file_path: Path
    file_size: int
    file_modified: float
    is_preferred: bool = False


class ImageMapper:
    """Maps 4-digit codes from order items to actual image files"""
    
    def __init__(self, sit_folder_path: Path):
        self.sit_folder_path = sit_folder_path
        self.code_map = {}  # Will be populated by scan
        self.scan_stats = {
            'total_files': 0,
            'image_files': 0,
            'files_with_codes': 0,
            'unique_codes': 0
        }
        
    def scan_folder(self, max_depth: int = 5) -> Dict[str, Path]:
        """
        Scan sit folder for image files and build code mapping
        Steps 96-100 of implementation plan
        """
        logger.info(f"Scanning folder: {self.sit_folder_path}")
        
        if not self.sit_folder_path.exists():
            raise ValueError(f"Sit folder not found: {self.sit_folder_path}")
        
        if not self.sit_folder_path.is_dir():
            raise ValueError(f"Path is not a directory: {self.sit_folder_path}")
        
        # Use utility function to find image files
        self.code_map = find_image_files_in_folder(self.sit_folder_path, max_depth)
        
        # Update scan statistics
        self.scan_stats['unique_codes'] = len(self.code_map)
        
        # Count total files for statistics
        total_files = 0
        image_files = 0
        for root, dirs, files in os.walk(self.sit_folder_path):
            # Limit depth
            level = root.replace(str(self.sit_folder_path), '').count(os.sep)
            if level >= max_depth:
                dirs[:] = []  # Don't recurse deeper
                continue
                
            total_files += len(files)
            for file in files:
                if Path(file).suffix.lower() in ['.jpg', '.jpeg', '.png', '.tif', '.tiff']:
                    image_files += 1
        
        self.scan_stats['total_files'] = total_files
        self.scan_stats['image_files'] = image_files
        self.scan_stats['files_with_codes'] = len(self.code_map)
        
        logger.info(f"Scan complete: {len(self.code_map)} unique codes from {image_files} image files")
        return self.code_map
    
    def map_order_items(self, order_items: List[StructuredItem]) -> List[StructuredItem]:
        """
        Map image codes in order items to actual file paths
        Steps 101-108 of implementation plan
        """
        logger.info(f"Mapping images for {len(order_items)} order items")
        
        # Ensure we have scanned the folder
        if not self.code_map:
            self.scan_folder()
        
        updated_items = []
        total_codes = 0
        found_codes = 0
        
        for item in order_items:
            # Step 101: Cross-check against order list
            image_paths = []
            item_warnings = list(item.warnings)  # Copy existing warnings
            
            for code in item.codes:
                total_codes += 1
                
                # Step 102: Look up in code map
                if code in self.code_map:
                    file_path = self.code_map[code]
                    
                    # Step 104: Verify image integrity (optional)
                    if self._verify_image_integrity(file_path):
                        image_paths.append(str(file_path))
                        found_codes += 1
                        logger.debug(f"Mapped code {code} -> {file_path.name}")
                    else:
                        # Image file is corrupted
                        item_warnings.append(f"Image file corrupted: {code}")
                        image_paths.append(None)
                        logger.warning(f"Corrupted image file for code {code}: {file_path}")
                else:
                    # Step 102: Not found
                    item_warnings.append(f"Image not found: {code}")
                    image_paths.append(None)
                    logger.warning(f"Image not found for code: {code}")
            
            # Step 106: Augment StructuredItem with image paths
            # Create new item with updated data
            updated_item = StructuredItem(
                product_slug=item.product_slug,
                quantity=item.quantity,
                width_in=item.width_in,
                height_in=item.height_in,
                orientation=item.orientation,
                frame_style=item.frame_style,
                codes=item.codes,
                source_line_text=item.source_line_text,
                warnings=item_warnings,
                count_images=item.count_images,
                multi_opening_template=item.multi_opening_template
            )
            
            # Add image_paths as a new attribute (extending the dataclass dynamically)
            setattr(updated_item, 'image_paths', image_paths)
            
            updated_items.append(updated_item)
        
        # Log mapping statistics
        success_rate = (found_codes / total_codes * 100) if total_codes > 0 else 0
        logger.info(f"Image mapping complete: {found_codes}/{total_codes} codes matched ({success_rate:.1f}%)")
        
        return updated_items
    
    def _verify_image_integrity(self, file_path: Path) -> bool:
        """
        Verify that image file can be opened (Step 104)
        """
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                # Try to load the image data
                img.verify()
            return True
        except Exception as e:
            logger.debug(f"Image integrity check failed for {file_path}: {e}")
            return False
    
    def get_scan_statistics(self) -> Dict:
        """Return folder scan statistics"""
        return {
            **self.scan_stats,
            'scan_folder': str(self.sit_folder_path),
            'success_rate': (self.scan_stats['files_with_codes'] / 
                           max(self.scan_stats['image_files'], 1)) * 100
        }
    
    def find_missing_codes(self, order_items: List[StructuredItem]) -> List[str]:
        """Find codes that are requested but not available in folder"""
        all_requested_codes = []
        for item in order_items:
            all_requested_codes.extend(item.codes)
        
        missing_codes = []
        for code in set(all_requested_codes):  # Remove duplicates
            if code not in self.code_map:
                missing_codes.append(code)
        
        return sorted(missing_codes)
    
    def find_extra_codes(self, order_items: List[StructuredItem]) -> List[str]:
        """Find codes that exist in folder but aren't requested"""
        requested_codes = set()
        for item in order_items:
            requested_codes.update(item.codes)
        
        available_codes = set(self.code_map.keys())
        extra_codes = available_codes - requested_codes
        
        return sorted(list(extra_codes))
    
    def get_code_details(self, code: str) -> Optional[Dict]:
        """Get detailed information about a specific code"""
        if code not in self.code_map:
            return None
        
        file_path = self.code_map[code]
        try:
            stat = file_path.stat()
            
            # Try to get image dimensions
            dimensions = None
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    dimensions = img.size
            except Exception:
                pass
            
            return {
                'code': code,
                'file_path': str(file_path),
                'file_name': file_path.name,
                'file_size': stat.st_size,
                'file_modified': stat.st_mtime,
                'dimensions': dimensions,
                'file_extension': file_path.suffix.lower()
            }
        except Exception as e:
            logger.warning(f"Error getting details for code {code}: {e}")
            return None 