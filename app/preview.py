"""
Portrait Preview Generator
Creates preview images showing how portraits will look with frames and backgrounds
"""

import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
from loguru import logger


class PortraitPreviewGenerator:
    """Generate portrait previews with frames and backgrounds"""
    
    def __init__(self, products_config: Dict, backgrounds_dir: Path, frames_dir: Path, output_dir: Path):
        self.products_config = products_config
        self.backgrounds_dir = backgrounds_dir
        self.frames_dir = frames_dir
        self.output_dir = output_dir
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Default settings
        self.preview_width = 1920
        self.preview_height = 1080
        self.margin = 20
        
        logger.info(f"Preview generator initialized: {self.output_dir}")
    
    def generate_preview(self, items: List[Dict], background_name: str, output_path: Path) -> bool:
        """
        Generate a complete preview showing all portrait items
        
        Args:
            items: List of preview items with image paths and product info
            background_name: Name of background image file
            output_path: Where to save the preview
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Generating preview with {len(items)} items")
            
            # Load background
            background = self._load_background(background_name)
            if not background:
                logger.error("Failed to load background")
                return False
            
            # Create preview canvas
            preview = Image.new('RGB', (self.preview_width, self.preview_height), (255, 255, 255))
            
            # Paste background
            bg_resized = background.resize((self.preview_width, self.preview_height), Image.Resampling.LANCZOS)
            preview.paste(bg_resized, (0, 0))
            
            # Calculate layout for items
            layout = self._calculate_layout(items)
            
            # Draw each item
            for i, item in enumerate(items):
                if i < len(layout):
                    position = layout[i]
                    self._draw_item(preview, item, position)
            
            # Add title/info overlay
            self._add_info_overlay(preview, items)
            
            # Save preview
            preview.save(output_path, 'PNG', quality=95)
            logger.info(f"✅ Preview saved: {output_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error generating preview: {e}")
            return False
    
    def _load_background(self, background_name: str) -> Optional[Image.Image]:
        """Load background image"""
        try:
            bg_path = self.backgrounds_dir / background_name
            
            if not bg_path.exists():
                # Try common background files
                common_backgrounds = [
                    "Virtual Background 2021.jpg",
                    "background.jpg", 
                    "default.jpg"
                ]
                
                for common_bg in common_backgrounds:
                    alt_path = self.backgrounds_dir / common_bg
                    if alt_path.exists():
                        bg_path = alt_path
                        break
                else:
                    logger.warning(f"Background not found: {background_name}")
                    # Create a simple gradient background
                    return self._create_default_background()
            
            background = Image.open(bg_path)
            logger.debug(f"Loaded background: {bg_path}")
            return background
            
        except Exception as e:
            logger.warning(f"Error loading background: {e}")
            return self._create_default_background()
    
    def _create_default_background(self) -> Image.Image:
        """Create a simple default background"""
        bg = Image.new('RGB', (1920, 1080), (240, 240, 240))
        draw = ImageDraw.Draw(bg)
        
        # Add subtle gradient effect
        for y in range(1080):
            color = int(240 - (y / 1080) * 40)  # Fade from light to darker gray
            draw.line([(0, y), (1920, y)], fill=(color, color, color))
        
        return bg
    
    def _calculate_layout(self, items: List[Dict]) -> List[Dict]:
        """Calculate positions for all items in the preview"""
        layout = []
        
        if not items:
            return layout
        
        # Simple grid layout
        cols = min(4, len(items))  # Max 4 columns
        rows = (len(items) + cols - 1) // cols  # Ceiling division
        
        # Calculate item dimensions
        item_width = (self.preview_width - self.margin * (cols + 1)) // cols
        item_height = (self.preview_height - self.margin * (rows + 1)) // rows
        
        # Position each item
        for i, item in enumerate(items):
            row = i // cols
            col = i % cols
            
            x = self.margin + col * (item_width + self.margin)
            y = self.margin + row * (item_height + self.margin)
            
            layout.append({
                'x': x,
                'y': y,
                'width': item_width,
                'height': item_height
            })
        
        return layout
    
    def _draw_item(self, canvas: Image.Image, item: Dict, position: Dict):
        """Draw a single portrait item at the specified position"""
        try:
            x, y, width, height = position['x'], position['y'], position['width'], position['height']
            
            # Create item canvas
            item_canvas = Image.new('RGBA', (width, height), (255, 255, 255, 0))
            
            # Get product info
            product_slug = item.get('product_slug', 'unknown')
            image_paths = item.get('image_paths', [])
            quantity = item.get('quantity', 1)
            
            # Draw images
            if image_paths and any(path for path in image_paths):
                self._draw_images(item_canvas, image_paths, product_slug)
            else:
                self._draw_placeholder(item_canvas, product_slug)
            
            # Draw frame if specified
            frame_style = item.get('frame_style', 'none')
            if frame_style != 'none':
                self._draw_frame(item_canvas, frame_style)
            
            # Add quantity badge
            if quantity > 1:
                self._draw_quantity_badge(item_canvas, quantity)
            
            # Add product label
            self._draw_product_label(item_canvas, product_slug, quantity)
            
            # Paste onto main canvas
            canvas.paste(item_canvas, (x, y), item_canvas)
            
        except Exception as e:
            logger.error(f"Error drawing item {item.get('product_slug', 'unknown')}: {e}")
    
    def _draw_images(self, canvas: Image.Image, image_paths: List[Path], product_slug: str):
        """Draw the actual portrait images"""
        valid_paths = [path for path in image_paths if path and Path(path).exists()]
        
        if not valid_paths:
            self._draw_placeholder(canvas, product_slug)
            return
        
        canvas_width, canvas_height = canvas.size
        
        # Handle different layouts based on number of images
        if len(valid_paths) == 1:
            # Single image - center it
            self._draw_single_image(canvas, valid_paths[0])
        elif len(valid_paths) == 2:
            # Pair - side by side
            self._draw_pair_images(canvas, valid_paths)
        elif len(valid_paths) == 3:
            # Trio - horizontal layout
            self._draw_trio_images(canvas, valid_paths)
        elif len(valid_paths) >= 4:
            # Multiple images - 2x2 grid or similar
            self._draw_multiple_images(canvas, valid_paths)
    
    def _draw_single_image(self, canvas: Image.Image, image_path: Path):
        """Draw a single image that fills the entire canvas with center crop"""
        try:
            image = Image.open(image_path)
            canvas_width, canvas_height = canvas.size
            
            # Calculate scaling to completely fill canvas (no white space)
            img_ratio = image.width / image.height
            canvas_ratio = canvas_width / canvas_height
            
            if img_ratio > canvas_ratio:
                # Image is wider - scale by height and crop width
                scale = canvas_height / image.height
                new_width = int(image.width * scale)
                new_height = canvas_height
                
                # Resize and center crop
                resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                crop_x = (new_width - canvas_width) // 2
                cropped = resized.crop((crop_x, 0, crop_x + canvas_width, new_height))
            else:
                # Image is taller - scale by width and crop height
                scale = canvas_width / image.width
                new_width = canvas_width
                new_height = int(image.height * scale)
                
                # Resize and center crop
                resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                crop_y = (new_height - canvas_height) // 2
                cropped = resized.crop((0, crop_y, new_width, crop_y + canvas_height))
            
            # Paste the cropped image (fills entire canvas)
            canvas.paste(cropped, (0, 0))
            
        except Exception as e:
            logger.error(f"Error drawing single image {image_path}: {e}")
            self._draw_placeholder(canvas, "Image Error")
    
    def _draw_pair_images(self, canvas: Image.Image, image_paths: List[Path]):
        """Draw two images side by side with full container fill"""
        canvas_width, canvas_height = canvas.size
        gap = 2  # Minimal gap between images
        img_width = (canvas_width - gap) // 2  # Each image gets half the width minus gap
        
        for i, path in enumerate(image_paths[:2]):
            try:
                image = Image.open(path)
                
                # Scale each image to completely fill its half-section using center crop
                img_ratio = image.width / image.height
                section_ratio = img_width / canvas_height
                
                if img_ratio > section_ratio:
                    # Image is wider - scale by height and crop width
                    scale = canvas_height / image.height
                    new_width = int(image.width * scale)
                    new_height = canvas_height
                    
                    resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    crop_x = (new_width - img_width) // 2
                    cropped = resized.crop((crop_x, 0, crop_x + img_width, new_height))
                else:
                    # Image is taller - scale by width and crop height
                    scale = img_width / image.width
                    new_width = img_width
                    new_height = int(image.height * scale)
                    
                    resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    crop_y = (new_height - canvas_height) // 2
                    cropped = resized.crop((0, crop_y, new_width, crop_y + canvas_height))
                
                # Position: first image at x=0, second image at x=img_width + gap
                x = i * (img_width + gap)
                canvas.paste(cropped, (x, 0))
            except Exception as e:
                logger.error(f"Error drawing pair image {path}: {e}")
    
    def _draw_trio_images(self, canvas: Image.Image, image_paths: List[Path]):
        """Draw three images horizontally"""
        canvas_width, canvas_height = canvas.size
        img_width = canvas_width // 3 - 4  # Small gaps
        
        for i, path in enumerate(image_paths[:3]):
            try:
                image = Image.open(path)
                resized = image.resize((img_width, canvas_height), Image.Resampling.LANCZOS)
                x = i * (img_width + 6)
                canvas.paste(resized, (x, 0))
            except Exception as e:
                logger.error(f"Error drawing trio image {path}: {e}")
    
    def _draw_multiple_images(self, canvas: Image.Image, image_paths: List[Path]):
        """Draw multiple images in a grid"""
        # For wallet sheets or other multi-image products
        canvas_width, canvas_height = canvas.size
        
        # Simple 2x2 grid for up to 4 images
        rows = 2
        cols = 2
        img_width = canvas_width // cols - 2
        img_height = canvas_height // rows - 2
        
        for i, path in enumerate(image_paths[:4]):
            row = i // cols
            col = i % cols
            
            try:
                image = Image.open(path)
                resized = image.resize((img_width, img_height), Image.Resampling.LANCZOS)
                x = col * (img_width + 4)
                y = row * (img_height + 4)
                canvas.paste(resized, (x, y))
            except Exception as e:
                logger.error(f"Error drawing grid image {path}: {e}")
    
    def _draw_placeholder(self, canvas: Image.Image, product_slug: str):
        """Draw placeholder when no image is available"""
        canvas_width, canvas_height = canvas.size
        
        # Create a simple placeholder
        placeholder = Image.new('RGB', (canvas_width, canvas_height), (220, 220, 220))
        draw = ImageDraw.Draw(placeholder)
        
        # Draw border
        draw.rectangle([2, 2, canvas_width-3, canvas_height-3], outline=(180, 180, 180), width=2)
        
        # Add text
        try:
            # Try to use a simple font
            font = ImageFont.load_default()
        except:
            font = None
        
        text = f"No Image\n{product_slug}"
        if font:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (canvas_width - text_width) // 2
            y = (canvas_height - text_height) // 2
            draw.text((x, y), text, fill=(100, 100, 100), font=font)
        
        canvas.paste(placeholder, (0, 0))
    
    def _draw_frame(self, canvas: Image.Image, frame_style: str):
        """Draw frame around the image"""
        # Simple frame drawing - can be enhanced with actual frame assets
        draw = ImageDraw.Draw(canvas)
        width, height = canvas.size
        
        # Frame colors based on style
        frame_colors = {
            'cherry': (139, 69, 19),
            'black': (0, 0, 0),
            'white': (255, 255, 255),
            'none': None
        }
        
        color = frame_colors.get(frame_style, (100, 100, 100))
        if color:
            # Draw frame border
            frame_width = max(3, min(width, height) // 50)
            for i in range(frame_width):
                draw.rectangle([i, i, width-1-i, height-1-i], outline=color)
    
    def _draw_quantity_badge(self, canvas: Image.Image, quantity: int):
        """Draw quantity badge in corner"""
        draw = ImageDraw.Draw(canvas)
        
        # Badge in top-right corner
        badge_size = 30
        x = canvas.width - badge_size - 5
        y = 5
        
        # Draw badge
        draw.ellipse([x, y, x + badge_size, y + badge_size], fill=(255, 0, 0), outline=(200, 0, 0))
        
        # Draw quantity text
        try:
            font = ImageFont.load_default()
            text = str(quantity)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = x + (badge_size - text_width) // 2
            text_y = y + (badge_size - text_height) // 2
            draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)
        except:
            pass
    
    def _draw_product_label(self, canvas: Image.Image, product_slug: str, quantity: int):
        """Draw product label at bottom"""
        draw = ImageDraw.Draw(canvas)
        
        # Label background
        label_height = 25
        y = canvas.height - label_height
        draw.rectangle([0, y, canvas.width, canvas.height], fill=(0, 0, 0, 180))
        
        # Label text
        try:
            font = ImageFont.load_default()
            text = f"{quantity}x {product_slug.replace('_', ' ').title()}"
            draw.text((5, y + 5), text, fill=(255, 255, 255), font=font)
        except:
            pass
    
    def _add_info_overlay(self, canvas: Image.Image, items: List[Dict]):
        """Add info overlay with order summary"""
        draw = ImageDraw.Draw(canvas)
        
        # Summary box in top-left
        box_width = 300
        box_height = len(items) * 20 + 40
        
        # Semi-transparent background
        overlay = Image.new('RGBA', (box_width, box_height), (0, 0, 0, 128))
        canvas.paste(overlay, (10, 10), overlay)
        
        # Title
        try:
            font = ImageFont.load_default()
            y_pos = 20
            draw.text((20, y_pos), "Order Summary:", fill=(255, 255, 255), font=font)
            y_pos += 25
            
            # Item list
            for item in items:
                product_name = item.get('product_slug', 'unknown').replace('_', ' ').title()
                quantity = item.get('quantity', 1)
                codes = item.get('image_paths', [])
                codes_count = len([c for c in codes if c])
                
                text = f"{quantity}x {product_name} ({codes_count} images)"
                draw.text((20, y_pos), text, fill=(255, 255, 255), font=font)
                y_pos += 18
                
        except Exception as e:
            logger.error(f"Error adding info overlay: {e}")


def create_preview_generator(config) -> PortraitPreviewGenerator:
    """Create preview generator from app configuration"""
    backgrounds_dir = Path("app/static/backgrounds")
    frames_dir = Path("app/static/frames") 
    output_dir = Path("app/static/previews")
    
    # Create directories if they don't exist
    for directory in [backgrounds_dir, frames_dir, output_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Load products config
    from .config import load_product_config
    products = load_product_config()
    
    return PortraitPreviewGenerator(
        products_config=products,
        backgrounds_dir=backgrounds_dir,
        frames_dir=frames_dir,
        output_dir=output_dir
    ) 