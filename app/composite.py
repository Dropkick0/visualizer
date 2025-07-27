"""
Composite module for Portrait Preview Webapp.

This module handles:
- Combining all layout elements into final preview image
- Managing blend modes and transparency
- Applying final image adjustments and quality settings
- Handling different output formats and sizes
"""

import os
from typing import Dict, List, Tuple, Optional, Any
from PIL import Image, ImageFilter, ImageEnhance
import io
from loguru import logger

from app.config import get_config
from app.errors import RenderError
from app.layout import LayoutElement, LayoutPosition


class CompositeSettings:
    """Settings for composite operations."""
    
    def __init__(self, 
                 output_format: str = 'JPEG',
                 quality: int = 95,
                 optimize: bool = True,
                 progressive: bool = True,
                 background_color: Tuple[int, int, int] = (255, 255, 255)):
        self.output_format = output_format
        self.quality = quality
        self.optimize = optimize
        self.progressive = progressive
        self.background_color = background_color


class CompositeEngine:
    """Main composite engine class."""
    
    def __init__(self):
        self.config = get_config()
        self.settings = self.config.settings
        
    def create_canvas(self, canvas_size: Tuple[int, int], background_color: Tuple[int, int, int] = None) -> Image.Image:
        """Create a new canvas with the specified size and background color."""
        if background_color is None:
            background_color = (255, 255, 255)  # White default
            
        canvas = Image.new('RGB', canvas_size, background_color)
        logger.debug(f"Created canvas: {canvas_size} with background {background_color}")
        return canvas
    
    def apply_blend_mode(self, 
                        base_image: Image.Image,
                        overlay_image: Image.Image,
                        blend_mode: str = 'normal',
                        opacity: float = 1.0) -> Image.Image:
        """
        Apply blend mode between base and overlay images.
        
        Supported blend modes:
        - normal: Standard alpha blending
        - multiply: Darken effect
        - screen: Lighten effect  
        - overlay: Contrast enhancement
        - soft_light: Subtle contrast
        - hard_light: Strong contrast
        """
        if blend_mode == 'normal':
            return self._blend_normal(base_image, overlay_image, opacity)
        elif blend_mode == 'multiply':
            return self._blend_multiply(base_image, overlay_image, opacity)
        elif blend_mode == 'screen':
            return self._blend_screen(base_image, overlay_image, opacity)
        elif blend_mode == 'overlay':
            return self._blend_overlay(base_image, overlay_image, opacity)
        else:
            # Default to normal blending
            logger.warning(f"Unsupported blend mode: {blend_mode}, using normal")
            return self._blend_normal(base_image, overlay_image, opacity)
    
    def _blend_normal(self, base: Image.Image, overlay: Image.Image, opacity: float) -> Image.Image:
        """Normal alpha blending."""
        if overlay.mode != 'RGBA':
            overlay = overlay.convert('RGBA')
            
        if opacity < 1.0:
            # Adjust overlay opacity
            alpha = overlay.split()[-1]
            alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
            overlay.putalpha(alpha)
            
        # Composite with alpha
        if base.mode != 'RGBA':
            base = base.convert('RGBA')
            
        result = Image.alpha_composite(base, overlay)
        return result.convert('RGB')
    
    def _blend_multiply(self, base: Image.Image, overlay: Image.Image, opacity: float) -> Image.Image:
        """Multiply blend mode - darkens the image."""
        import numpy as np
        
        base_array = np.array(base.convert('RGB'), dtype=np.float32) / 255.0
        overlay_array = np.array(overlay.convert('RGB'), dtype=np.float32) / 255.0
        
        result_array = base_array * overlay_array * opacity + base_array * (1 - opacity)
        result_array = np.clip(result_array * 255, 0, 255).astype(np.uint8)
        
        return Image.fromarray(result_array, 'RGB')
    
    def _blend_screen(self, base: Image.Image, overlay: Image.Image, opacity: float) -> Image.Image:
        """Screen blend mode - lightens the image."""
        import numpy as np
        
        base_array = np.array(base.convert('RGB'), dtype=np.float32) / 255.0
        overlay_array = np.array(overlay.convert('RGB'), dtype=np.float32) / 255.0
        
        result_array = 1 - (1 - base_array) * (1 - overlay_array)
        result_array = result_array * opacity + base_array * (1 - opacity)
        result_array = np.clip(result_array * 255, 0, 255).astype(np.uint8)
        
        return Image.fromarray(result_array, 'RGB')
    
    def _blend_overlay(self, base: Image.Image, overlay: Image.Image, opacity: float) -> Image.Image:
        """Overlay blend mode - increases contrast."""
        import numpy as np
        
        base_array = np.array(base.convert('RGB'), dtype=np.float32) / 255.0
        overlay_array = np.array(overlay.convert('RGB'), dtype=np.float32) / 255.0
        
        # Overlay formula
        mask = base_array < 0.5
        result_array = np.where(mask, 
                               2 * base_array * overlay_array,
                               1 - 2 * (1 - base_array) * (1 - overlay_array))
        
        result_array = result_array * opacity + base_array * (1 - opacity)
        result_array = np.clip(result_array * 255, 0, 255).astype(np.uint8)
        
        return Image.fromarray(result_array, 'RGB')
    
    def composite_elements(self, 
                          elements: List[LayoutElement],
                          canvas_size: Tuple[int, int],
                          background_color: Tuple[int, int, int] = None) -> Image.Image:
        """
        Composite all layout elements into a single image.
        
        Elements should be pre-sorted by z-index.
        """
        # Create base canvas
        canvas = self.create_canvas(canvas_size, background_color)
        
        logger.info(f"Compositing {len(elements)} elements onto {canvas_size} canvas")
        
        for i, element in enumerate(elements):
            try:
                canvas = self._composite_element(canvas, element)
                logger.debug(f"Composited element {i+1}/{len(elements)}: {element.element_type}")
            except Exception as e:
                logger.error(f"Failed to composite element {element.element_type}: {e}")
                continue
        
        return canvas
    
    def _composite_element(self, canvas: Image.Image, element: LayoutElement) -> Image.Image:
        """Composite a single element onto the canvas."""
        if element.position is None:
            logger.warning(f"Element {element.element_type} has no position, skipping")
            return canvas
            
        # Handle different element types
        if element.element_type == 'background':
            return self._composite_background(canvas, element)
        elif element.element_type == 'customer_image':
            return self._composite_customer_image(canvas, element)
        elif element.element_type == 'frame':
            return self._composite_frame(canvas, element)
        elif element.element_type in ['watermark', 'logo']:
            return self._composite_overlay(canvas, element)
        else:
            # Generic compositing
            return self._composite_generic(canvas, element)
    
    def _composite_background(self, canvas: Image.Image, element: LayoutElement) -> Image.Image:
        """Composite background element."""
        pos = element.position
        
        if element.image.size == canvas.size and pos.x == 0 and pos.y == 0:
            # Direct replacement
            return element.image.convert('RGB')
        else:
            # Paste at position
            canvas.paste(element.image, (pos.x, pos.y))
            return canvas
    
    def _composite_customer_image(self, canvas: Image.Image, element: LayoutElement) -> Image.Image:
        """Composite customer image element."""
        pos = element.position
        
        # Convert to RGB if needed
        image = element.image.convert('RGB')
        
        # Paste at calculated position
        canvas.paste(image, (pos.x, pos.y))
        return canvas
    
    def _composite_frame(self, canvas: Image.Image, element: LayoutElement) -> Image.Image:
        """Composite frame element with transparency support."""
        pos = element.position
        
        # Ensure frame has alpha channel
        frame_image = element.image
        if frame_image.mode != 'RGBA':
            frame_image = frame_image.convert('RGBA')
        
        # Create a temporary canvas for blending
        temp_canvas = canvas.convert('RGBA')
        
        # Handle positioning and sizing
        if frame_image.size != (pos.width, pos.height):
            frame_image = frame_image.resize((pos.width, pos.height), Image.Resampling.LANCZOS)
        
        # Composite with alpha blending
        if pos.x == 0 and pos.y == 0 and frame_image.size == temp_canvas.size:
            result = Image.alpha_composite(temp_canvas, frame_image)
        else:
            # Create overlay canvas
            overlay = Image.new('RGBA', temp_canvas.size, (0, 0, 0, 0))
            overlay.paste(frame_image, (pos.x, pos.y))
            result = Image.alpha_composite(temp_canvas, overlay)
        
        return result.convert('RGB')
    
    def _composite_overlay(self, canvas: Image.Image, element: LayoutElement) -> Image.Image:
        """Composite overlay elements like watermarks and logos."""
        pos = element.position
        
        # Apply blend mode
        if element.blend_mode != 'normal':
            # For special blend modes, we need to work with the full canvas
            overlay_canvas = Image.new('RGB', canvas.size, (255, 255, 255))
            overlay_canvas.paste(element.image, (pos.x, pos.y))
            
            return self.apply_blend_mode(canvas, overlay_canvas, element.blend_mode, 0.8)
        else:
            # Normal alpha blending
            if element.image.mode == 'RGBA':
                temp_canvas = canvas.convert('RGBA')
                overlay = Image.new('RGBA', temp_canvas.size, (0, 0, 0, 0))
                overlay.paste(element.image, (pos.x, pos.y))
                result = Image.alpha_composite(temp_canvas, overlay)
                return result.convert('RGB')
            else:
                canvas.paste(element.image, (pos.x, pos.y))
                return canvas
    
    def _composite_generic(self, canvas: Image.Image, element: LayoutElement) -> Image.Image:
        """Generic compositing for unknown element types."""
        pos = element.position
        
        if element.image.mode == 'RGBA':
            # Handle transparency
            temp_canvas = canvas.convert('RGBA')
            overlay = Image.new('RGBA', temp_canvas.size, (0, 0, 0, 0))
            overlay.paste(element.image, (pos.x, pos.y))
            result = Image.alpha_composite(temp_canvas, overlay)
            return result.convert('RGB')
        else:
            # Simple paste
            canvas.paste(element.image, (pos.x, pos.y))
            return canvas
    
    def apply_final_adjustments(self, image: Image.Image, adjustments: Dict[str, Any] = None) -> Image.Image:
        """Apply final image adjustments before output."""
        if adjustments is None:
            adjustments = self.settings.image_processing.get('final_adjustments', {})
        
        result = image
        
        # Apply sharpening
        sharpening = adjustments.get('sharpening', 0)
        if sharpening > 0:
            result = result.filter(ImageFilter.UnsharpMask(
                radius=adjustments.get('sharpen_radius', 1.0),
                percent=int(sharpening * 100),
                threshold=adjustments.get('sharpen_threshold', 3)
            ))
        
        # Apply contrast adjustment
        contrast = adjustments.get('contrast', 1.0)
        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(result)
            result = enhancer.enhance(contrast)
        
        # Apply brightness adjustment
        brightness = adjustments.get('brightness', 1.0)
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(result)
            result = enhancer.enhance(brightness)
        
        # Apply saturation adjustment
        saturation = adjustments.get('saturation', 1.0)
        if saturation != 1.0:
            enhancer = ImageEnhance.Color(result)
            result = enhancer.enhance(saturation)
        
        logger.debug(f"Applied final adjustments: {adjustments}")
        return result
    
    def create_thumbnail(self, 
                        image: Image.Image, 
                        max_size: Tuple[int, int] = (400, 400)) -> Image.Image:
        """Create a thumbnail version of the image."""
        thumbnail = image.copy()
        thumbnail.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Ensure minimum quality
        if thumbnail.width < 100 or thumbnail.height < 100:
            # Scale up if too small
            scale = max(100 / thumbnail.width, 100 / thumbnail.height)
            new_size = (int(thumbnail.width * scale), int(thumbnail.height * scale))
            thumbnail = thumbnail.resize(new_size, Image.Resampling.LANCZOS)
        
        return thumbnail
    
    def save_image(self, 
                  image: Image.Image,
                  output_path: str,
                  settings: CompositeSettings = None) -> bool:
        """Save the final image to disk."""
        if settings is None:
            settings = CompositeSettings()
        
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Prepare save parameters
            save_kwargs = {
                'format': settings.output_format,
                'optimize': settings.optimize
            }
            
            if settings.output_format.upper() == 'JPEG':
                save_kwargs.update({
                    'quality': settings.quality,
                    'progressive': settings.progressive
                })
                # Ensure RGB mode for JPEG
                if image.mode != 'RGB':
                    image = image.convert('RGB')
            elif settings.output_format.upper() == 'PNG':
                save_kwargs['compress_level'] = 6
            
            # Save the image
            image.save(output_path, **save_kwargs)
            
            file_size = os.path.getsize(output_path)
            logger.info(f"Saved composite image: {output_path} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save image {output_path}: {e}")
            return False
    
    def get_image_bytes(self, 
                       image: Image.Image,
                       settings: CompositeSettings = None) -> bytes:
        """Get image as bytes for web response."""
        if settings is None:
            settings = CompositeSettings()
        
        # Prepare save parameters
        save_kwargs = {
            'format': settings.output_format,
            'optimize': settings.optimize
        }
        
        if settings.output_format.upper() == 'JPEG':
            save_kwargs.update({
                'quality': settings.quality,
                'progressive': settings.progressive
            })
            # Ensure RGB mode for JPEG
            if image.mode != 'RGB':
                image = image.convert('RGB')
        elif settings.output_format.upper() == 'PNG':
            save_kwargs['compress_level'] = 6
        
        # Save to bytes
        buffer = io.BytesIO()
        image.save(buffer, **save_kwargs)
        return buffer.getvalue()
    
    def create_preview_sizes(self, 
                           image: Image.Image,
                           sizes: List[Tuple[int, int]] = None) -> Dict[str, Image.Image]:
        """Create multiple preview sizes of the image."""
        if sizes is None:
            sizes = [
                (800, 1000),   # Large preview
                (400, 500),    # Medium preview  
                (200, 250),    # Small preview
                (100, 125)     # Thumbnail
            ]
        
        previews = {}
        
        for width, height in sizes:
            # Calculate scale to fit within bounds
            scale = min(width / image.width, height / image.height)
            
            if scale < 1.0:  # Only downscale
                new_width = int(image.width * scale)
                new_height = int(image.height * scale)
                
                preview = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                size_key = f"{width}x{height}"
                previews[size_key] = preview
        
        logger.debug(f"Created {len(previews)} preview sizes")
        return previews


def create_composite_engine() -> CompositeEngine:
    """Factory function to create a CompositeEngine instance."""
    return CompositeEngine() 