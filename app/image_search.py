"""
Optimized image search functionality for finding photos in Dropbox folder
Based on 4-digit codes from FileMaker wishlist
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from glob import glob
from loguru import logger
from PIL import Image
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import time


def find_all_images(root: Path) -> Dict[str, Path]:
    """Recursively map image codes to file paths using depth-first search."""
    patterns = ("*.jpg", "*.jpeg", "*.png")
    files: Dict[str, Path] = {}
    for ext in patterns:
        for path in root.rglob(ext):
            files[path.stem] = path
    return files


class OptimizedDropboxImageSearcher:
    """Optimized search for images in Dropbox folder based on 4-digit codes"""
    
    def __init__(self, dropbox_root: str):
        self.dropbox_root = Path(dropbox_root)
        self.supported_extensions = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp'}
        self._image_cache: Optional[Dict[str, List[Path]]] = None
        self._cache_timestamp: Optional[float] = None
        self._cache_valid_duration = 300  # 5 minutes
        
        logger.info(f"Optimized Dropbox image searcher initialized: {self.dropbox_root}")
    
    def find_images_by_codes(self, codes: List[str]) -> Dict[str, List[Path]]:
        """
        Find images in Dropbox folder that end with the specified 4-digit codes
        Uses optimized single-pass directory traversal with in-memory pattern matching
        
        Args:
            codes: List of 4-digit codes to search for
            
        Returns:
            Dictionary mapping codes to lists of image file paths
        """
        start_time = time.time()
        
        if not self.dropbox_root.exists():
            logger.warning(f"Dropbox folder not found: {self.dropbox_root}")
            return {}
        
        # Validate and filter codes
        valid_codes = []
        for code in codes:
            if len(code) == 4 and code.isdigit():
                valid_codes.append(code)
            else:
                logger.warning(f"Invalid code format: {code} (must be 4 digits)")
        
        if not valid_codes:
            return {}
        
        logger.info(f"Searching for {len(valid_codes)} codes using optimized searcher")
        
        # Get or build image index
        image_index = self._get_image_index()
        
        # Use parallel processing to match codes
        results = self._parallel_code_matching(valid_codes, image_index)
        
        # Sort results for each code by modification time (newest first)
        for code in results:
            if results[code]:
                try:
                    results[code].sort(key=lambda p: p.stat().st_mtime, reverse=True)
                except OSError:
                    # Handle cases where files might have been deleted
                    results[code] = [p for p in results[code] if p.exists()]
        
        elapsed = time.time() - start_time
        total_found = sum(len(images) for images in results.values())
        logger.info(f"✅ Found {total_found} total images for {len(valid_codes)} codes in {elapsed:.2f}s")
        
        return results
    
    def _get_image_index(self) -> Dict[str, List[Path]]:
        """Get or build the image index, with caching"""
        current_time = time.time()
        
        # Check if cache is valid
        if (self._image_cache is not None and 
            self._cache_timestamp is not None and 
            current_time - self._cache_timestamp < self._cache_valid_duration):
            logger.debug("Using cached image index")
            return self._image_cache
        
        # Build new index
        logger.info("Building image index from directory scan...")
        start_time = time.time()
        
        self._image_cache = self._build_image_index()
        self._cache_timestamp = current_time
        
        elapsed = time.time() - start_time
        total_images = sum(len(paths) for paths in self._image_cache.values())
        logger.info(f"Built index of {total_images} images in {elapsed:.2f}s")
        
        return self._image_cache
    
    def _build_image_index(self) -> Dict[str, List[Path]]:
        """Build index of all images organized by potential codes they could match"""
        index = {}
        
        try:
            # Single recursive traversal of entire directory tree
            for file_path in self.dropbox_root.rglob("*"):
                if not file_path.is_file():
                    continue
                
                # Check if it's an image file
                if file_path.suffix.lower() not in self.supported_extensions:
                    continue
                
                # Extract potential codes from filename
                potential_codes = self._extract_codes_from_filename(file_path)
                
                # Add file to index for each potential code
                for code in potential_codes:
                    if code not in index:
                        index[code] = []
                    index[code].append(file_path)
        
        except Exception as e:
            logger.error(f"Error building image index: {e}")
            return {}
        
        return index
    
    def _extract_codes_from_filename(self, file_path: Path) -> Set[str]:
        """Extract all potential 4-digit codes from a filename"""
        codes = set()
        filename = file_path.stem  # filename without extension
        
        # Find all 4-digit sequences in the filename
        for match in re.finditer(r'\d{4}', filename):
            code = match.group()
            codes.add(code)
        
        return codes
    
    def _parallel_code_matching(self, codes: List[str], image_index: Dict[str, List[Path]]) -> Dict[str, List[Path]]:
        """Use parallel processing to match codes against the image index"""
        results = {}
        
        # For small numbers of codes, don't use threading overhead
        if len(codes) <= 4:
            for code in codes:
                results[code] = self._match_single_code(code, image_index)
            return results
        
        # Use thread pool for larger searches
        with ThreadPoolExecutor(max_workers=min(8, len(codes))) as executor:
            future_to_code = {
                executor.submit(self._match_single_code, code, image_index): code 
                for code in codes
            }
            
            for future in concurrent.futures.as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    results[code] = future.result()
                except Exception as e:
                    logger.error(f"Error matching code {code}: {e}")
                    results[code] = []
        
        return results
    
    def _match_single_code(self, code: str, image_index: Dict[str, List[Path]]) -> List[Path]:
        """Match a single code against the image index with advanced pattern matching"""
        matching_files = []
        
        # Direct index lookup (fastest)
        if code in image_index:
            matching_files.extend(image_index[code])
        
        # Additional pattern matching for camera naming conventions
        # This scans the index for patterns like _MG_0033, DSC_0033, etc.
        for indexed_code, paths in image_index.items():
            if indexed_code == code:
                continue  # Already handled above
            
            # Check if any files match advanced patterns
            for path in paths:
                filename = path.stem.upper()
                
                # Camera naming patterns
                if (f"_MG_{code}" in filename or 
                    f"DSC_{code}" in filename or 
                    f"IMG_{code}" in filename or
                    f"_{code}_" in filename or
                    f"-{code}" in filename or
                    filename.endswith(f"_{code}")):
                    
                    if path not in matching_files:
                        matching_files.append(path)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for path in matching_files:
            if path not in seen:
                seen.add(path)
                unique_files.append(path)
        
        # Log results
        if unique_files:
            logger.debug(f"Code {code}: found {len(unique_files)} images")
            for img in unique_files[:3]:  # Log first 3 matches
                logger.debug(f"  - {img.name}")
        else:
            logger.debug(f"Code {code}: no images found")
        
        return unique_files
    
    def invalidate_cache(self):
        """Force cache invalidation for next search"""
        self._image_cache = None
        self._cache_timestamp = None
        logger.info("Image cache invalidated")


# Maintain backward compatibility
class DropboxImageSearcher(OptimizedDropboxImageSearcher):
    """Backward compatible alias for the optimized searcher"""
    
    def _search_code_recursive(self, code: str) -> List[Path]:
        """Legacy method - now uses optimized search internally"""
        image_index = self._get_image_index()
        return self._match_single_code(code, image_index)
    
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