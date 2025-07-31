"""
Trio Composite Generator
Handles creation of trio portraits using composite frames with multiple openings
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from PIL import Image, ImageDraw
from loguru import logger


def trio_template_filename(size: str, frame: str, matte: str) -> str:
    """Return composite filename based on parameters."""
    size_label = "5x10" if size == "5x10" else "10x20"
    frame_title = frame.capitalize()
    matte_title = matte.capitalize()
    return f"Frame {frame_title} - {matte_title} {size_label} 3 Image.jpg"


def is_trio_product(product: Dict) -> bool:
    """Check if a product is a trio product"""
    slug = product.get('slug', '')
    count_images = product.get('count_images', 0)
    template = product.get('multi_opening_template', '')
    
    return (
        'trio' in slug.lower() or 
        count_images == 3 or
        template == 'trio_horizontal'
    )


def extract_trio_details(product: Dict) -> Tuple[str, str, str]:
    """
    Extract trio details from product configuration
    
    Returns:
        Tuple of (size, frame_color, matte_color)
    """
    slug = product.get('slug', '')
    name = product.get('name', '')
    frame_default = product.get('frame_style_default', 'black')
    width = product.get('width_in', 5.0)
    height = product.get('height_in', 10.0)
    
    # Determine size from dimensions
    if width == 5.0 and height == 10.0:
        size = "5x10"
    elif width == 10.0 and height == 20.0:
        size = "10x20"
    else:
        size = "5x10"  # Default fallback
    
    # Determine frame color from default or name
    frame_color = "Black"  # Default
    if frame_default == 'cherry' or 'cherry' in name.lower():
        frame_color = "Cherry"
    elif frame_default == 'black' or 'black' in name.lower():
        frame_color = "Black"
    
    # Extract matte color from product name
    matte_color = "White"  # Default
    name_lower = name.lower()
    
    if 'creme mat' in name_lower or 'cream mat' in name_lower:
        matte_color = "Tan"  # Creme maps to Tan in composite files
    elif 'white mat' in name_lower:
        matte_color = "White"
    elif 'gray mat' in name_lower or 'grey mat' in name_lower:
        matte_color = "Gray" 
    elif 'black mat' in name_lower:
        matte_color = "Black"
    
    logger.debug(f"Extracted trio details: {size}, {frame_color}, {matte_color} from {name}")
    return size, frame_color, matte_color


class TrioComposite:
    """Represents a trio composite with frame and matte information"""
    
    def __init__(self, frame_color: str, matte_color: str, size: str = "5x10"):
        self.frame_color = frame_color
        self.matte_color = matte_color  
        self.size = size
        self.composite_image: Optional[Image.Image] = None
        self.composite_path: Optional[Path] = None
        
        # Composite dimensions (3078 × 1500 px for 5x10)
        self.full_width = 3078
        self.full_height = 1500
        
        # Image positions for overlaying (from user specs)
        self.image_positions = [
            (240, 312),   # Image 1: top-left at (240px, 312px)
            (1145, 312),  # Image 2: top-left at (1145px, 312px)  
            (2056, 312)   # Image 3: top-left at (2056px, 312px)
        ]
        
    def load_composite(self, composites_dir: Path) -> bool:
        """Load the composite frame image"""
        # Build filename: "Frame [Color] - [Matte] 5x10 3 Image.jpg"
        # Note: some files have extra spaces, so we'll try different variations
        possible_filenames = [
            f"Frame {self.frame_color} - {self.matte_color} {self.size} 3 Image.jpg",
            f"Frame {self.frame_color} - {self.matte_color}  {self.size} 3 Image.jpg"  # Extra space
        ]
        
        logger.debug(f"Looking for composite {self.frame_color}/{self.matte_color} {self.size} in {composites_dir}")
        
        for filename in possible_filenames:
            self.composite_path = composites_dir / filename
            logger.debug(f"Trying filename: {filename}")
            logger.debug(f"Full path: {self.composite_path}")
            logger.debug(f"Exists? {self.composite_path.exists()}")
            if self.composite_path.exists():
                break
        else:
            # List all files in directory for debugging
            available_files = list(composites_dir.glob("*.jpg"))
            logger.warning(f"Composite not found with any filename variation for {self.frame_color}/{self.matte_color}")
            logger.debug(f"Available files in {composites_dir}:")
            for file in available_files:
                logger.debug(f"  - {file.name}")
            return False
            
        try:
            self.composite_image = Image.open(self.composite_path)
            logger.info(f"Loaded composite: {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to load composite {filename}: {e}")
            return False
    
    def get_image_size_for_opening(self, opening_index: int) -> Tuple[int, int]:
        """Calculate the optimal image size for a specific opening"""
        # Exact dimensions to ensure perfect fit in composite openings
        if self.size == "5x10":
            # Precise sizing for 5x10 composites
            return (680, 905)  # Portrait orientation - fits perfectly in openings
        else:  # 10x20
            # Larger openings for 10x20 composites  
            return (1360, 1810)  # Scaled up 2x


class TrioCompositeGenerator:
    """Main class for generating trio composites with customer images"""

    def __init__(self, base_dir: Path | str = "Composites"):
        """Initialize generator with the directory containing composite files."""
        self.base_dir = Path(base_dir)
        
        # Available frame and matte combinations (from composite files)
        self.available_combinations = [
            ("Black", "Black"), ("Black", "Gray"), ("Black", "White"), ("Black", "Tan"),
            ("Cherry", "Black"), ("Cherry", "Gray"), ("Cherry", "White"), ("Cherry", "Tan")
        ]
    
    def _normalize_matte_color(self, matte_color: str) -> str:
        """Normalize matte color names to match composite file names"""
        color_lower = matte_color.lower()
        
        # Map color variations to actual composite file names
        if color_lower in ['creme', 'cream', 'biege', 'beige', 'tan']:
            return "Tan"
        elif color_lower in ['white']:
            return "White"
        elif color_lower in ['black']:
            return "Black"
        elif color_lower in ['gray', 'grey']:
            return "Gray"
        else:
            # Default to Tan for unknown colors (matches user preference)
            logger.debug(f"Unknown matte color '{matte_color}', defaulting to Tan")
            return "Tan"
    
    def _normalize_frame_color(self, frame_color: str) -> str:
        """Normalize frame color names to match composite file names"""
        color_lower = frame_color.lower()
        
        if color_lower in ['cherry']:
            return "Cherry"
        elif color_lower in ['black']:
            return "Black"
        else:
            # Default to Black for unknown colors
            logger.debug(f"Unknown frame color '{frame_color}', defaulting to Black")
            return "Black"
        
    def create_composite_from_product(self, 
                                    product: Dict,
                                    customer_images: List[Path]) -> Optional[Image.Image]:
        """
        Create a trio composite from product configuration and customer images
        
        Args:
            product: Product configuration dictionary
            customer_images: List of customer image paths
            
        Returns:
            Composite image with customer images overlaid, or None if failed
        """
        if not is_trio_product(product):
            logger.warning(f"Product {product.get('slug')} is not a trio product")
            return None
            
        size, frame_color, matte_color = extract_trio_details(product)
        
        return self.create_composite(
            customer_images=customer_images,
            frame_color=frame_color,
            matte_color=matte_color,
            size=size
        )
        
    def create_composite(self,
                        customer_images: List[Path],
                        frame_color: str = "Black",
                        matte_color: str = "White",
                        size: str = "5x10",
                        fallback_to_5x10: bool = False) -> Optional[Image.Image]:
        """
        Create a trio composite by overlaying customer images on composite frame
        
        Args:
            customer_images: List of customer image paths (expects 3 images)
            frame_color: Frame color (Black, Cherry)
            matte_color: Matte color (Black, Gray, White, Tan)
            size: Composite size (5x10 or 10x20)
            
        Returns:
            Composite image with customer images overlaid, or None if failed
        """
        
        # Normalize color names to match composite file names
        matte_color = self._normalize_matte_color(matte_color)
        frame_color = self._normalize_frame_color(frame_color)
        
        # Validate frame/matte combination
        if (frame_color, matte_color) not in self.available_combinations:
            logger.warning(f"Frame/matte combination not available: {frame_color}/{matte_color}")
            # Fall back to default
            frame_color, matte_color = "Black", "White"
            
        # Create and load composite
        composite = TrioComposite(frame_color, matte_color, size)
        scale = 1.0
        if not composite.load_composite(self.base_dir):
            if fallback_to_5x10 and size == "10x20":
                logger.warning("10x20 composite not found, falling back to 5x10")
                composite = TrioComposite(frame_color, matte_color, "5x10")
                if not composite.load_composite(self.base_dir):
                    return None
                size = "5x10"
                scale = 2.0
            else:
                return None
            
        # Use the composite frame as the base and paste customer images into openings
        composite_frame = composite.composite_image.convert('RGB')
        result_image = composite_frame.copy()
        
        # Paste customer images directly into the frame openings
        for i, (image_path, position) in enumerate(zip(customer_images, composite.image_positions)):
            if i >= 3:  # Only handle 3 images
                break
                
            if not image_path or not Path(image_path).exists():
                continue
                
            try:
                # Load and prepare customer image (again)
                customer_img = Image.open(image_path)
                
                # Get optimal size for this opening
                target_width, target_height = composite.get_image_size_for_opening(i)
                
                # Resize and crop to fit opening
                processed_img = self._resize_and_crop_for_opening(
                    customer_img, target_width, target_height
                )
                
                # Apply individual banner overlay if applicable
                processed_img = self._apply_individual_banner(processed_img, image_path)
                
                # Calculate position
                x, y = position
                if size == "10x20":
                    # Scale positions for 10x20 (double size)
                    x *= 2
                    y *= 2
                    
                # Paste customer image directly onto the frame
                result_image.paste(processed_img, (x, y))
                logger.debug(f"Pasted image {i+1} onto frame at position ({x}, {y})")
                
            except Exception as e:
                logger.error(f"Failed to paste image {i+1} onto frame: {e}")
                continue
        
        if scale != 1.0:
            result_image = result_image.resize(
                (result_image.width * int(scale), result_image.height * int(scale)),
                Image.Resampling.LANCZOS
            )

        return result_image
    
    def _apply_individual_banner(self, image: Image.Image, image_path: Path) -> Image.Image:
        """Apply banner overlay to individual image if it qualifies for Artist Series or Retouch"""
        try:
            # Extract image code from path (e.g., "_MG_0033.JPG" -> "0033")
            image_code = None
            image_name = Path(image_path).stem
            
            # Try to extract 4-digit code from filename
            import re
            code_match = re.search(r'(\d{4})', image_name)
            if code_match:
                image_code = code_match.group(1)
            
            if not image_code:
                return image  # No code found, return unchanged
            
            # Check for retouch (using same logic as enhanced_preview)
            retouch_list = ['0033', '0039']  # Images that need retouching
            is_retouch = image_code in retouch_list
            
            # For trio composites, we don't typically have artist series info
            # But we could check based on the image code if needed
            is_artist_series = False  # Could be enhanced later
            
            # Determine banner text
            banner_text = None
            if is_artist_series and is_retouch:
                banner_text = "ARTIST SERIES + RETOUCH"
            elif is_artist_series:
                banner_text = "ARTIST SERIES"
            elif is_retouch:
                banner_text = "RETOUCH"
            
            # Only draw banner if one of the conditions is met
            if not banner_text:
                return image  # No banner needed
            
            # Create a copy to avoid modifying the original
            result_image = image.copy()
            width, height = result_image.size
            
            # Try to load bold font
            try:
                from PIL import ImageFont, ImageDraw
                banner_font = ImageFont.truetype("arialbd.ttf", 14)  # Bold font for banner
            except:
                banner_font = ImageFont.load_default()
            
            # Calculate banner dimensions
            draw = ImageDraw.Draw(result_image)
            bbox = draw.textbbox((0, 0), banner_text, font=banner_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Banner height and positioning
            banner_height = text_height + 8  # Add padding
            
            # Create gradient overlay with transparency: 25% on edges, 75% in center
            overlay = Image.new('RGBA', (width, banner_height), (0, 0, 0, 0))
            
            # Create horizontal gradient alpha mask
            for pixel_x in range(width):
                # Calculate distance from center as percentage
                center = width / 2
                distance_from_center = abs(pixel_x - center) / center  # 0 at center, 1 at edges
                
                # Interpolate alpha
                center_alpha = 150  
                edge_alpha = 150    
                
                alpha = int(center_alpha + (edge_alpha - center_alpha) * distance_from_center)
                
                # Draw vertical line with calculated alpha
                for pixel_y in range(banner_height):
                    overlay.putpixel((pixel_x, pixel_y), (0, 0, 0, alpha))
            
            overlay_draw = ImageDraw.Draw(overlay)
            
            # Draw white bold text centered on overlay (both horizontally and vertically)
            text_x = (width - text_width) // 2
            # Add padding from bottom and top for better centering
            text_padding = 4  # Pixels of padding from edges
            text_y = (banner_height - text_height) // 2 - text_padding  # Center with padding adjustment
            overlay_draw.text((text_x, text_y), banner_text, fill=(255, 255, 255, 255), font=banner_font)
            
            # Paste overlay onto image with alpha blending at the very top
            result_image.paste(overlay, (0, 0), overlay)
            
            logger.debug(f"Applied banner '{banner_text}' to trio composite image {image_code}")
            return result_image
            
        except Exception as e:
            logger.error(f"Failed to apply individual banner to image {image_path}: {e}")
            return image  # Return original on error
    
    def _resize_and_crop_for_opening(self, image: Image.Image, 
                                   target_width: int, target_height: int) -> Image.Image:
        """Resize and crop image to fit the composite opening"""
        
        # DON'T rotate images - keep them in natural orientation for composites too
        # The composite openings are designed for portrait images in their natural orientation
        
        # Calculate scaling to fill the opening
        img_ratio = image.width / image.height
        target_ratio = target_width / target_height
        
        if img_ratio > target_ratio:
            # Image is wider - fit to height and crop width
            new_height = target_height
            new_width = int(target_height * img_ratio)
            resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Crop to target width (center crop)
            crop_x = (new_width - target_width) // 2
            cropped = resized.crop((crop_x, 0, crop_x + target_width, target_height))
        else:
            # Image is taller - fit to width and crop height  
            new_width = target_width
            new_height = int(target_width / img_ratio)
            resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Crop to target height (center crop)
            crop_y = (new_height - target_height) // 2
            cropped = resized.crop((0, crop_y, target_width, crop_y + target_height))
            
        return cropped
    
    def scale_composite_for_preview(self, composite_image: Image.Image, 
                                  preview_width: int, preview_height: int,
                                  size: str = "5x10") -> Image.Image:
        """Scale composite to fit in preview while maintaining aspect ratio"""
        
        # Calculate scale factor based on available space
        # Increased percentages to make composites much larger
        max_width = int(preview_width * 0.45)  # Use 45% of preview width (was 25%)
        max_height = int(preview_height * 0.65)  # Use 65% of preview height (was 40%)
        
        # For 10x20, make it even larger since it's a premium product
        if size == "10x20":
            max_width = int(preview_width * 0.55)  # Use 55% of preview width (was 35%)
            max_height = int(preview_height * 0.80)  # Use 80% of preview height (was 60%)
        
        # Calculate scaling while maintaining aspect ratio
        width_scale = max_width / composite_image.width
        height_scale = max_height / composite_image.height
        scale = min(width_scale, height_scale)
        
        new_width = int(composite_image.width * scale)
        new_height = int(composite_image.height * scale)
        
        scaled = composite_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        logger.debug(f"Scaled {size} composite from {composite_image.size} to {scaled.size}")
        return scaled
        
    def get_available_frame_styles(self) -> List[Tuple[str, str]]:
        """Return list of available (frame_color, matte_color) combinations"""
        return self.available_combinations.copy() 