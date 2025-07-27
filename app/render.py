"""
Render preparation module for Portrait Preview Webapp.

This module handles:
- Loading and validating frame assets
- Scaling customer images to fit frame openings
- Cropping images appropriately  
- Preparing background images
- Managing different frame types (single, duo, trio, triple openings)
"""

import os
from typing import Dict, List, Tuple, Optional, Any
from PIL import Image, ImageOps, ImageEnhance
import numpy as np
from loguru import logger

from app.config import get_config
from app.errors import RenderError


class FrameAsset:
    """Represents a loaded frame asset with opening coordinates."""
    
    def __init__(self, frame_path: str, openings: List[Dict[str, Any]]):
        self.frame_path = frame_path
        self.openings = openings
        self.frame_image: Optional[Image.Image] = None
        self.loaded = False
        
    def load(self) -> Image.Image:
        """Load the frame image from disk."""
        if not self.loaded:
            if not os.path.exists(self.frame_path):
                raise RenderError(f"Frame asset not found: {self.frame_path}")
                
            try:
                self.frame_image = Image.open(self.frame_path).convert('RGBA')
                self.loaded = True
                logger.debug(f"Loaded frame asset: {self.frame_path} ({self.frame_image.size})")
            except Exception as e:
                raise RenderError(f"Failed to load frame asset {self.frame_path}: {e}")
                
        return self.frame_image
    
    def get_opening_count(self) -> int:
        """Get the number of openings in this frame."""
        return len(self.openings)


class CustomerImage:
    """Represents a customer image with processing metadata."""
    
    def __init__(self, image_path: str, image_code: str):
        self.image_path = image_path
        self.image_code = image_code
        self.original_image: Optional[Image.Image] = None
        self.processed_image: Optional[Image.Image] = None
        self.loaded = False
        
    def load(self) -> Image.Image:
        """Load the customer image from disk."""
        if not self.loaded:
            if not os.path.exists(self.image_path):
                raise RenderError(f"Customer image not found: {self.image_path}")
                
            try:
                self.original_image = Image.open(self.image_path).convert('RGB')
                self.loaded = True
                logger.debug(f"Loaded customer image: {self.image_path} ({self.original_image.size})")
            except Exception as e:
                raise RenderError(f"Failed to load customer image {self.image_path}: {e}")
                
        return self.original_image
    
    def get_aspect_ratio(self) -> float:
        """Get the aspect ratio (width/height) of the original image."""
        if not self.loaded:
            self.load()
        return self.original_image.width / self.original_image.height


class RenderPrep:
    """Main render preparation class."""
    
    def __init__(self):
        self.config = get_config()
        self.frames_config = self.config.frames
        self.settings = self.config.settings
        
        # Asset cache
        self._frame_cache: Dict[str, FrameAsset] = {}
        self._background_cache: Dict[str, Image.Image] = {}
        
    def load_frame_asset(self, frame_style: str, product_type: str) -> FrameAsset:
        """Load a frame asset for the given style and product type."""
        cache_key = f"{frame_style}_{product_type}"
        
        if cache_key in self._frame_cache:
            return self._frame_cache[cache_key]
            
        # Find frame configuration
        frame_config = None
        for frame in self.frames_config.frames:
            if frame.name == frame_style and frame.product_type == product_type:
                frame_config = frame
                break
                
        if not frame_config:
            raise RenderError(f"Frame configuration not found: {frame_style} for {product_type}")
            
        # Build frame asset path
        frame_path = os.path.join(
            self.settings.assets_directory,
            'frames',
            frame_config.filename
        )
        
        # Create and cache frame asset
        frame_asset = FrameAsset(frame_path, frame_config.openings)
        self._frame_cache[cache_key] = frame_asset
        
        return frame_asset
    
    def load_background(self, background_name: str = None) -> Image.Image:
        """Load a background image."""
        if background_name is None:
            background_name = self.settings.default_background
            
        if background_name in self._background_cache:
            return self._background_cache[background_name]
            
        background_path = os.path.join(
            self.settings.assets_directory,
            'backgrounds',
            background_name
        )
        
        if not os.path.exists(background_path):
            raise RenderError(f"Background not found: {background_path}")
            
        try:
            background = Image.open(background_path).convert('RGB')
            self._background_cache[background_name] = background
            logger.debug(f"Loaded background: {background_path} ({background.size})")
            return background
        except Exception as e:
            raise RenderError(f"Failed to load background {background_path}: {e}")
    
    def calculate_crop_dimensions(self, 
                                image_size: Tuple[int, int],
                                target_size: Tuple[int, int],
                                crop_method: str = 'center') -> Tuple[int, int, int, int]:
        """
        Calculate crop box coordinates to fit image into target size while maintaining aspect ratio.
        
        Returns: (left, top, right, bottom) crop box coordinates
        """
        img_width, img_height = image_size
        target_width, target_height = target_size
        
        img_ratio = img_width / img_height
        target_ratio = target_width / target_height
        
        if img_ratio > target_ratio:
            # Image is wider than target, crop horizontally
            new_width = int(img_height * target_ratio)
            if crop_method == 'center':
                left = (img_width - new_width) // 2
            else:  # crop_method == 'left' or other
                left = 0
            return (left, 0, left + new_width, img_height)
        else:
            # Image is taller than target, crop vertically  
            new_height = int(img_width / target_ratio)
            if crop_method == 'center':
                top = (img_height - new_height) // 2
            else:  # crop_method == 'top' or other
                top = 0
            return (0, top, img_width, top + new_height)
    
    def scale_and_crop_image(self,
                           customer_image: CustomerImage,
                           target_width: int,
                           target_height: int,
                           crop_method: str = 'center') -> Image.Image:
        """
        Scale and crop a customer image to fit the target dimensions.
        """
        original = customer_image.load()
        
        # Calculate crop box
        crop_box = self.calculate_crop_dimensions(
            original.size,
            (target_width, target_height),
            crop_method
        )
        
        # Crop the image
        cropped = original.crop(crop_box)
        
        # Scale to exact target size
        scaled = cropped.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        # Apply any image enhancements
        if self.settings.image_processing.auto_enhance:
            scaled = self._enhance_image(scaled)
            
        logger.debug(f"Scaled and cropped image {customer_image.image_code}: "
                    f"{original.size} -> {crop_box} -> {scaled.size}")
        
        return scaled
    
    def _enhance_image(self, image: Image.Image) -> Image.Image:
        """Apply automatic image enhancements."""
        try:
            # Auto-level (similar to Photoshop's auto-levels)
            image = ImageOps.autocontrast(image, cutoff=0.1)
            
            # Slight sharpening
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.1)
            
            # Slight color enhancement
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(1.05)
            
            return image
        except Exception as e:
            logger.warning(f"Image enhancement failed: {e}")
            return image
    
    def prepare_images_for_product(self,
                                 customer_images: List[CustomerImage],
                                 frame_asset: FrameAsset,
                                 product_config: Dict[str, Any]) -> List[Image.Image]:
        """
        Prepare customer images for a specific product configuration.
        
        Returns list of processed images ready for compositing.
        """
        frame_asset.load()  # Ensure frame is loaded
        
        required_count = frame_asset.get_opening_count()
        available_count = len(customer_images)
        
        if available_count < required_count:
            logger.warning(f"Not enough images: need {required_count}, have {available_count}")
            # Pad with placeholders or repeat images as needed
            while len(customer_images) < required_count:
                customer_images.append(customer_images[-1] if customer_images else None)
        
        processed_images = []
        
        for i, opening in enumerate(frame_asset.openings):
            if i >= len(customer_images) or customer_images[i] is None:
                # Create placeholder image
                placeholder = Image.new('RGB', 
                                      (opening['width'], opening['height']), 
                                      color=(200, 200, 200))
                processed_images.append(placeholder)
                continue
                
            customer_image = customer_images[i]
            
            # Scale and crop for this opening
            processed = self.scale_and_crop_image(
                customer_image,
                opening['width'],
                opening['height'],
                crop_method=self.settings.image_processing.crop_method
            )
            
            processed_images.append(processed)
            
        logger.info(f"Prepared {len(processed_images)} images for {frame_asset.frame_path}")
        return processed_images
    
    def get_canvas_size(self, product_config: Dict[str, Any]) -> Tuple[int, int]:
        """Get the canvas size for a product based on its dimensions and DPI."""
        # Convert inches to pixels
        width_inches = product_config.get('width', 8)
        height_inches = product_config.get('height', 10)
        dpi = self.settings.image_processing.output_dpi
        
        canvas_width = int(width_inches * dpi)
        canvas_height = int(height_inches * dpi)
        
        return (canvas_width, canvas_height)
    
    def create_render_context(self,
                            customer_images: List[CustomerImage],
                            frame_style: str,
                            product_type: str,
                            product_config: Dict[str, Any],
                            background_name: str = None) -> Dict[str, Any]:
        """
        Create a complete render context with all prepared assets.
        
        Returns a dictionary containing all assets ready for compositing.
        """
        # Load frame asset
        frame_asset = self.load_frame_asset(frame_style, product_type)
        
        # Load background
        background = self.load_background(background_name)
        
        # Prepare customer images
        processed_images = self.prepare_images_for_product(
            customer_images, frame_asset, product_config
        )
        
        # Get canvas dimensions
        canvas_size = self.get_canvas_size(product_config)
        
        render_context = {
            'frame_asset': frame_asset,
            'background': background,
            'processed_images': processed_images,
            'canvas_size': canvas_size,
            'product_config': product_config,
            'frame_style': frame_style,
            'product_type': product_type
        }
        
        logger.info(f"Created render context for {product_type} with {frame_style} frame")
        return render_context


def create_render_prep() -> RenderPrep:
    """Factory function to create a RenderPrep instance."""
    return RenderPrep() 