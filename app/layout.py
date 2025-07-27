"""
Layout engine module for Portrait Preview Webapp.

This module handles:
- Positioning backgrounds, frames, and customer images on canvas
- Managing different layout strategies (centered, scaled, etc.)
- Calculating optimal placement based on product dimensions
- Handling alignment and spacing for multi-opening frames
"""

import os
from typing import Dict, List, Tuple, Optional, Any
from PIL import Image, ImageDraw, ImageFont
import math
from loguru import logger

from app.config import get_config
from app.errors import RenderError


class LayoutPosition:
    """Represents a position and size on the canvas."""
    
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        
    @property
    def center_x(self) -> int:
        return self.x + self.width // 2
        
    @property
    def center_y(self) -> int:
        return self.y + self.height // 2
        
    @property
    def right(self) -> int:
        return self.x + self.width
        
    @property
    def bottom(self) -> int:
        return self.y + self.height
        
    def __repr__(self) -> str:
        return f"LayoutPosition({self.x}, {self.y}, {self.width}, {self.height})"


class LayoutElement:
    """Represents an element to be placed on the canvas."""
    
    def __init__(self, 
                 image: Image.Image,
                 element_type: str,
                 position: LayoutPosition = None,
                 z_index: int = 0,
                 blend_mode: str = 'normal'):
        self.image = image
        self.element_type = element_type  # 'background', 'frame', 'customer_image'
        self.position = position
        self.z_index = z_index
        self.blend_mode = blend_mode
        
    def __lt__(self, other):
        """Enable sorting by z_index."""
        return self.z_index < other.z_index


class LayoutEngine:
    """Main layout engine class."""
    
    def __init__(self):
        self.config = get_config()
        self.settings = self.config.settings
        
    def calculate_background_position(self, 
                                    background: Image.Image,
                                    canvas_size: Tuple[int, int],
                                    strategy: str = 'center_crop') -> LayoutPosition:
        """
        Calculate position for background image on canvas.
        
        Strategies:
        - center_crop: Scale to fill canvas, crop excess
        - center_fit: Scale to fit within canvas, may have borders
        - stretch: Stretch to exact canvas size
        - tile: Tile the background (for patterns)
        """
        canvas_width, canvas_height = canvas_size
        bg_width, bg_height = background.size
        
        if strategy == 'center_crop':
            # Scale to fill, maintaining aspect ratio
            scale_x = canvas_width / bg_width
            scale_y = canvas_height / bg_height
            scale = max(scale_x, scale_y)
            
            new_width = int(bg_width * scale)
            new_height = int(bg_height * scale)
            
            x = (canvas_width - new_width) // 2
            y = (canvas_height - new_height) // 2
            
        elif strategy == 'center_fit':
            # Scale to fit within canvas
            scale_x = canvas_width / bg_width
            scale_y = canvas_height / bg_height
            scale = min(scale_x, scale_y)
            
            new_width = int(bg_width * scale)
            new_height = int(bg_height * scale)
            
            x = (canvas_width - new_width) // 2
            y = (canvas_height - new_height) // 2
            
        elif strategy == 'stretch':
            # Stretch to exact canvas size
            x, y = 0, 0
            new_width, new_height = canvas_width, canvas_height
            
        else:  # 'tile' or other
            # For tiling, position at origin
            x, y = 0, 0
            new_width, new_height = bg_width, bg_height
            
        return LayoutPosition(x, y, new_width, new_height)
    
    def calculate_frame_position(self,
                               frame: Image.Image,
                               canvas_size: Tuple[int, int],
                               product_config: Dict[str, Any]) -> LayoutPosition:
        """Calculate position for frame on canvas."""
        canvas_width, canvas_height = canvas_size
        frame_width, frame_height = frame.size
        
        # Get frame scaling method from config
        frame_strategy = self.settings.layout.get('frame_strategy', 'center_fit')
        
        if frame_strategy == 'center_fit':
            # Scale frame to fit canvas while maintaining aspect ratio
            scale_x = canvas_width / frame_width
            scale_y = canvas_height / frame_height
            scale = min(scale_x, scale_y)
            
            new_width = int(frame_width * scale)
            new_height = int(frame_height * scale)
            
            x = (canvas_width - new_width) // 2
            y = (canvas_height - new_height) // 2
            
        elif frame_strategy == 'exact_size':
            # Use frame at exact canvas size
            x, y = 0, 0
            new_width, new_height = canvas_width, canvas_height
            
        else:  # 'center_crop' or other
            # Scale to fill canvas
            scale_x = canvas_width / frame_width
            scale_y = canvas_height / frame_height
            scale = max(scale_x, scale_y)
            
            new_width = int(frame_width * scale)
            new_height = int(frame_height * scale)
            
            x = (canvas_width - new_width) // 2
            y = (canvas_height - new_height) // 2
        
        return LayoutPosition(x, y, new_width, new_height)
    
    def calculate_image_positions(self,
                                customer_images: List[Image.Image],
                                frame_openings: List[Dict[str, Any]],
                                frame_position: LayoutPosition) -> List[LayoutPosition]:
        """
        Calculate positions for customer images within frame openings.
        """
        positions = []
        
        # Calculate scale factor from frame position
        frame_scale_x = frame_position.width / frame_openings[0].get('frame_width', frame_position.width)
        frame_scale_y = frame_position.height / frame_openings[0].get('frame_height', frame_position.height)
        
        for i, (image, opening) in enumerate(zip(customer_images, frame_openings)):
            if image is None:
                positions.append(None)
                continue
                
            # Scale opening coordinates based on frame scaling
            opening_x = int(opening['x'] * frame_scale_x) + frame_position.x
            opening_y = int(opening['y'] * frame_scale_y) + frame_position.y
            opening_width = int(opening['width'] * frame_scale_x)
            opening_height = int(opening['height'] * frame_scale_y)
            
            # Image should already be sized correctly for the opening
            # But we may need to center it if sizes don't match exactly
            img_width, img_height = image.size
            
            x = opening_x + (opening_width - img_width) // 2
            y = opening_y + (opening_height - img_height) // 2
            
            position = LayoutPosition(x, y, img_width, img_height)
            positions.append(position)
            
            logger.debug(f"Image {i} position: {position}")
        
        return positions
    
    def create_layout_plan(self, render_context: Dict[str, Any]) -> List[LayoutElement]:
        """
        Create a complete layout plan with all positioned elements.
        
        Returns list of LayoutElements sorted by z-index.
        """
        elements = []
        canvas_size = render_context['canvas_size']
        
        # 1. Background (z-index: 0)
        background = render_context['background']
        bg_position = self.calculate_background_position(
            background, 
            canvas_size,
            self.settings.layout.get('background_strategy', 'center_crop')
        )
        
        # Scale background if needed
        if (bg_position.width != background.width or 
            bg_position.height != background.height):
            scaled_bg = background.resize(
                (bg_position.width, bg_position.height),
                Image.Resampling.LANCZOS
            )
        else:
            scaled_bg = background
            
        elements.append(LayoutElement(
            image=scaled_bg,
            element_type='background',
            position=bg_position,
            z_index=0
        ))
        
        # 2. Customer images (z-index: 1)
        frame_asset = render_context['frame_asset']
        processed_images = render_context['processed_images']
        
        # Calculate frame position first
        frame_position = self.calculate_frame_position(
            frame_asset.frame_image,
            canvas_size,
            render_context['product_config']
        )
        
        # Calculate image positions within frame
        image_positions = self.calculate_image_positions(
            processed_images,
            frame_asset.openings,
            frame_position
        )
        
        for i, (image, position) in enumerate(zip(processed_images, image_positions)):
            if image is not None and position is not None:
                elements.append(LayoutElement(
                    image=image,
                    element_type='customer_image',
                    position=position,
                    z_index=1
                ))
        
        # 3. Frame (z-index: 2) - on top
        if (frame_position.width != frame_asset.frame_image.width or 
            frame_position.height != frame_asset.frame_image.height):
            scaled_frame = frame_asset.frame_image.resize(
                (frame_position.width, frame_position.height),
                Image.Resampling.LANCZOS
            )
        else:
            scaled_frame = frame_asset.frame_image
            
        elements.append(LayoutElement(
            image=scaled_frame,
            element_type='frame',
            position=frame_position,
            z_index=2
        ))
        
        # Sort by z-index
        elements.sort(key=lambda e: e.z_index)
        
        logger.info(f"Created layout plan with {len(elements)} elements")
        return elements
    
    def add_branding_elements(self, 
                            elements: List[LayoutElement],
                            canvas_size: Tuple[int, int],
                            product_config: Dict[str, Any]) -> List[LayoutElement]:
        """Add branding elements like watermarks, logos, etc."""
        
        # Add watermark if enabled
        if self.settings.branding.get('watermark_enabled', False):
            watermark_element = self._create_watermark_element(canvas_size)
            if watermark_element:
                elements.append(watermark_element)
        
        # Add corner logo if enabled
        if self.settings.branding.get('logo_enabled', False):
            logo_element = self._create_logo_element(canvas_size)
            if logo_element:
                elements.append(logo_element)
        
        return elements
    
    def _create_watermark_element(self, canvas_size: Tuple[int, int]) -> Optional[LayoutElement]:
        """Create a watermark element."""
        try:
            watermark_text = self.settings.branding.get('watermark_text', 'PREVIEW')
            
            # Create a transparent overlay
            overlay = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Try to load a font
            try:
                font_size = canvas_size[0] // 20  # Scale with canvas size
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            # Get text dimensions
            bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Position in center
            x = (canvas_size[0] - text_width) // 2
            y = (canvas_size[1] - text_height) // 2
            
            # Draw watermark with transparency
            draw.text((x, y), watermark_text, 
                     fill=(255, 255, 255, 80), font=font)
            
            return LayoutElement(
                image=overlay,
                element_type='watermark',
                position=LayoutPosition(0, 0, canvas_size[0], canvas_size[1]),
                z_index=10,
                blend_mode='overlay'
            )
            
        except Exception as e:
            logger.warning(f"Failed to create watermark: {e}")
            return None
    
    def _create_logo_element(self, canvas_size: Tuple[int, int]) -> Optional[LayoutElement]:
        """Create a logo element."""
        try:
            logo_path = os.path.join(
                self.settings.assets_directory,
                'branding',
                self.settings.branding.get('logo_filename', 'logo.png')
            )
            
            if not os.path.exists(logo_path):
                return None
                
            logo = Image.open(logo_path).convert('RGBA')
            
            # Scale logo to appropriate size
            max_logo_size = min(canvas_size) // 8
            logo.thumbnail((max_logo_size, max_logo_size), Image.Resampling.LANCZOS)
            
            # Position in corner
            position = self.settings.branding.get('logo_position', 'bottom_right')
            margin = 20
            
            if position == 'bottom_right':
                x = canvas_size[0] - logo.width - margin
                y = canvas_size[1] - logo.height - margin
            elif position == 'bottom_left':
                x = margin
                y = canvas_size[1] - logo.height - margin
            elif position == 'top_right':
                x = canvas_size[0] - logo.width - margin
                y = margin
            else:  # top_left
                x = margin
                y = margin
            
            return LayoutElement(
                image=logo,
                element_type='logo',
                position=LayoutPosition(x, y, logo.width, logo.height),
                z_index=5
            )
            
        except Exception as e:
            logger.warning(f"Failed to create logo element: {e}")
            return None
    
    def optimize_layout(self, elements: List[LayoutElement]) -> List[LayoutElement]:
        """Apply layout optimizations and adjustments."""
        
        # Re-sort by z-index to ensure proper ordering
        elements.sort(key=lambda e: e.z_index)
        
        # Apply any layout-specific adjustments
        for element in elements:
            if element.element_type == 'customer_image':
                # Ensure customer images are within canvas bounds
                element.position = self._clamp_to_canvas(element.position, elements[0].position)
        
        return elements
    
    def _clamp_to_canvas(self, position: LayoutPosition, canvas_position: LayoutPosition) -> LayoutPosition:
        """Ensure position is within canvas bounds."""
        max_x = canvas_position.width - position.width
        max_y = canvas_position.height - position.height
        
        clamped_x = max(0, min(position.x, max_x))
        clamped_y = max(0, min(position.y, max_y))
        
        return LayoutPosition(clamped_x, clamped_y, position.width, position.height)


def create_layout_engine() -> LayoutEngine:
    """Factory function to create a LayoutEngine instance."""
    return LayoutEngine() 