"""
Frame Overlay module for Portrait Preview Webapp.

This module handles:
- Loading frame assets from the Frames directory
- Applying frame overlays to portrait images
- Handling different frame sizes (5x7, 8x10, 10x13, 16x20, 20x24)
- Breaking up 5x7 pairs when frames are applied
- Scaling frames and positioning them outside of images
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from PIL import Image, ImageOps
from loguru import logger


class FrameSpec:
    """Specification for a frame size and style"""
    
    # FRAME THICKNESS CONSTANTS - Adjust these to dial in perfect fit for each frame/size combo
    # Format: FRAME_THICKNESS[frame_style][size] = {'top': px, 'bottom': px, 'left': px, 'right': px}
    FRAME_THICKNESS = {
        "Black": {
            "5x7": {'top': 13, 'bottom': 11, 'left': 11, 'right': 14},
            "8x10": {'top': 20, 'bottom': 17, 'left': 20, 'right': 22},
            "10x13": {'top': 25, 'bottom': 22, 'left': 23, 'right': 27},
            "16x20": {'top': 26, 'bottom': 27, 'left': 27, 'right': 27},
            "20x24": {'top': 27, 'bottom': 27, 'left': 27, 'right': 27}
        },
        "Cherry": {
            "5x7": {'top': 13, 'bottom': 13, 'left': 13, 'right': 11},
            "8x10": {'top': 17, 'bottom': 17, 'left': 17, 'right': 17},
            "10x13": {'top': 24, 'bottom': 22, 'left': 25, 'right': 24},
            "16x20": {'top': 27, 'bottom': 27, 'left': 27, 'right': 27},
            "20x24": {'top': 27, 'bottom': 27, 'left': 27, 'right': 27}
        }
    }
    
    def __init__(self, size: str, frame_style: str = "Black"):
        self.size = size  # e.g., "5x7", "8x10", "10x13", "16x20", "20x24"
        self.frame_style = frame_style  # "Black" or "Cherry"
        
        # Get frame border thickness from constants (per frame style and size)
        thickness = self.FRAME_THICKNESS.get(frame_style, {}).get(size, {})
        self.top_thickness = thickness.get('top', 27)
        self.bottom_thickness = thickness.get('bottom', 27)
        self.left_thickness = thickness.get('left', 27)
        self.right_thickness = thickness.get('right', 27)
        
        # Parse size dimensions
        self.width_in, self.height_in = self._parse_size(size)
        
    def _parse_size(self, size: str) -> Tuple[float, float]:
        """Parse size string like '8x10' into width and height in inches"""
        size_map = {
            "5x7": (5.0, 7.0),
            "8x10": (8.0, 10.0), 
            "10x13": (10.0, 13.0),
            "16x20": (16.0, 20.0),
            "20x24": (20.0, 24.0)
        }
        return size_map.get(size, (8.0, 10.0))  # Default to 8x10
        
    def get_frame_filename(self) -> str:
        """Get the expected frame filename"""
        return f"{self.frame_style} Frame.jpg"


class FrameOverlayEngine:
    """Main engine for applying frame overlays to images"""
    
    def __init__(self, frames_dir: Path):
        self.frames_dir = frames_dir
        self.available_frames = {}  # Cache loaded frames
        
        # Available frame sizes (in order of preference for assignment)
        self.supported_sizes = ["20x24", "16x20", "10x13", "8x10", "5x7"]
        
        logger.info(f"Frame overlay engine initialized with frames from: {frames_dir}")
        
    def load_frame_asset(self, frame_spec: FrameSpec) -> Optional[Image.Image]:
        """Load a frame asset from disk"""
        frame_key = f"{frame_spec.frame_style}_{frame_spec.size}"
        
        if frame_key in self.available_frames:
            return self.available_frames[frame_key]
            
        frame_filename = frame_spec.get_frame_filename()
        frame_path = self.frames_dir / frame_filename
        
        if not frame_path.exists():
            logger.warning(f"Frame asset not found: {frame_path}")
            return None
            
        try:
            frame_image = Image.open(frame_path).convert('RGBA')
            self.available_frames[frame_key] = frame_image
            logger.debug(f"Loaded frame asset: {frame_path} ({frame_image.size})")
            return frame_image
        except Exception as e:
            logger.error(f"Failed to load frame asset {frame_path}: {e}")
            return None
    
    def apply_frame_to_image(self, image: Image.Image, frame_spec: FrameSpec) -> Optional[Image.Image]:
        """
        Apply a frame around an image, keeping the image size exactly the same
        
        Args:
            image: The customer image (will keep this exact size)
            frame_spec: Frame specification (size and style)
            
        Returns:
            Larger image with frame around the original image, or None if frame can't be applied
        """
        frame_asset = self.load_frame_asset(frame_spec)
        if not frame_asset:
            return None
            
        try:
            # Get original image size - this stays exactly the same
            image_width, image_height = image.size
            
            # Calculate final output size (image + frame borders)
            final_width = image_width + frame_spec.left_thickness + frame_spec.right_thickness
            final_height = image_height + frame_spec.top_thickness + frame_spec.bottom_thickness
            
            # Scale the frame asset to match the final output size
            frame_scaled = frame_asset.resize((final_width, final_height), Image.Resampling.LANCZOS)
            
            # Create final composition starting with the frame as the base
            result = frame_scaled.convert('RGB')
            
            # Calculate where to paste the customer image (centered in the frame opening)
            image_x = frame_spec.left_thickness
            image_y = frame_spec.top_thickness
            
            # Paste the customer image ON TOP of the frame at the correct position
            # This preserves the exact customer image size and puts it in the frame opening
            result.paste(image, (image_x, image_y))
            
            logger.debug(f"Applied {frame_spec.frame_style} {frame_spec.size} frame around image. "
                        f"Original: {image_width}x{image_height}, Final: {final_width}x{final_height}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to apply frame {frame_spec.frame_style} {frame_spec.size}: {e}")
            return None
    
    def parse_frame_requirements(self, frame_data: List[Dict]) -> Dict[str, int]:
        """
        Parse frame requirements from the FRAMES section data
        
        Args:
            frame_data: List of frame entries with quantity, size, and description
            
        Returns:
            Dictionary mapping frame size to quantity needed
        """
        frame_requirements = {}
        
        for frame_entry in frame_data:
            quantity = frame_entry.get('quantity', 0)
            description = frame_entry.get('description', '').lower()
            
            # Parse frame size from description
            size = None
            if '5 x 7' in description or '5x7' in description:
                size = "5x7"
            elif '8 x 10' in description or '8x10' in description:
                size = "8x10"
            elif '10 x 13' in description or '10x13' in description:
                size = "10x13"
            elif '16 x 20' in description or '16x20' in description:
                size = "16x20"
            elif '20 x 24' in description or '20x24' in description:
                size = "20x24"
                
            if size and quantity > 0:
                frame_requirements[size] = frame_requirements.get(size, 0) + quantity
                
        logger.info(f"Parsed frame requirements: {frame_requirements}")
        return frame_requirements
    
    def apply_frames_to_order_items(self, order_items: List[Dict], 
                                  frame_requirements: Dict[str, int],
                                  frame_style_preferences: Dict[str, str] = None) -> List[Dict]:
        """
        Apply frame requirements to order items, modifying them as needed
        
        This will:
        1. Split 5x7 pairs into singles when frames are applied
        2. Add frame specifications to applicable items with preferred frame styles
        3. Respect frame quantity limits
        
        Args:
            order_items: List of order items 
            frame_requirements: Dictionary of frame size -> quantity
            frame_style_preferences: Dictionary of frame size -> preferred style ("Black" or "Cherry")
            
        Returns:
            Modified order items with frame specifications added
        """
        modified_items = []
        frames_used = {size: 0 for size in frame_requirements.keys()}
        
        # Default frame style preferences if not provided
        if frame_style_preferences is None:
            frame_style_preferences = {}
        
        # Process items and apply frames where applicable
        for item in order_items:
            product_code = item.get('product_code', '')
            size_category = item.get('size_category', '')
            quantity = item.get('quantity', 1)
            
            # Skip items that can't have frames (wallets, 3.5x5s)
            if product_code in ['200_sheet', '350_sheet'] or size_category in ['wallet_sheet', 'small_sheet']:
                modified_items.append(item)
                continue
                
            # Skip composites - they already have their own frames
            if size_category == 'trio_composite':
                modified_items.append(item)
                continue
                
            # Determine frame size for this item
            frame_size = self._get_frame_size_for_item(item)
            if not frame_size or frame_size not in frame_requirements:
                modified_items.append(item)
                continue
                
            # Get preferred frame style for this size (default to Black)
            preferred_style = frame_style_preferences.get(frame_size, "Black")
                
            # Special handling for 5x7 pairs
            if frame_size == "5x7" and item.get('sheet_type') == 'landscape_2x1':
                # This is a 5x7 pair - split into singles if we have frames
                available_frames = frame_requirements["5x7"] - frames_used["5x7"]
                
                if available_frames > 0:
                    # Split the pair into individual 5x7s
                    images_in_pair = item.get('image_codes', [])
                    
                    # Create individual 5x7 items with frames
                    frames_to_apply = min(available_frames, len(images_in_pair))
                    
                    for i in range(frames_to_apply):
                        single_item = item.copy()
                        single_item.update({
                            'product_slug': '5x7_individual_framed',
                            'product_code': '570_individual_framed',
                            'quantity': 1,
                            'image_codes': [images_in_pair[i]],
                            'size_category': 'medium_sheet',  # Keep in 5x7 section
                            'sheet_type': 'INDIVIDUAL5x7_FRAMED',
                            'display_name': f'5x7 Individual ({preferred_style} Framed)',
                            'has_frame': True,
                            'frame_spec': FrameSpec("5x7", preferred_style)
                        })
                        modified_items.append(single_item)
                        frames_used["5x7"] += 1
                    
                    # If there are remaining images without frames, create individual items or keep as pair
                    remaining_images = images_in_pair[frames_to_apply:]
                    if remaining_images:
                        if len(remaining_images) == 1:
                            # Single unframed 5x7
                            remaining_item = item.copy()
                            remaining_item.update({
                                'product_slug': '5x7_individual',
                                'product_code': '570_individual',
                                'quantity': 1,
                                'image_codes': remaining_images,
                                'size_category': 'medium_sheet',  # Keep in 5x7 section
                                'sheet_type': 'INDIVIDUAL5x7',
                                'display_name': '5x7 Individual'
                            })
                            modified_items.append(remaining_item)
                        else:
                            # Keep as pair if more than 1 remaining
                            remaining_item = item.copy()
                            remaining_item['image_codes'] = remaining_images
                            modified_items.append(remaining_item)
                else:
                    # No frames available - keep as pair
                    modified_items.append(item)
            else:
                # Regular item (8x10, 10x13, 16x20, 20x24)
                available_frames = frame_requirements[frame_size] - frames_used[frame_size]
                
                if available_frames >= quantity:
                    # Apply frames to all quantities
                    framed_item = item.copy()
                    framed_item.update({
                        'has_frame': True,
                        'frame_spec': FrameSpec(frame_size, preferred_style)
                    })
                    modified_items.append(framed_item)
                    frames_used[frame_size] += quantity
                elif available_frames > 0:
                    # Partial frames available
                    # Create framed version
                    framed_item = item.copy()
                    framed_item.update({
                        'quantity': available_frames,
                        'has_frame': True,
                        'frame_spec': FrameSpec(frame_size, preferred_style)
                    })
                    modified_items.append(framed_item)
                    
                    # Create unframed version for remainder
                    unframed_item = item.copy()
                    unframed_item['quantity'] = quantity - available_frames
                    modified_items.append(unframed_item)
                    
                    frames_used[frame_size] += available_frames
                else:
                    # No frames available
                    modified_items.append(item)
        
        logger.info(f"Applied frames to order items. Frames used: {frames_used}")
        return modified_items
    
    def apply_frames_with_alternating_styles(self, order_items: List[Dict], 
                                            frame_requirements: Dict[str, int]) -> List[Dict]:
        """
        Apply frames with alternating styles (Black then Cherry) for showcase purposes
        
        This will:
        1. Split 5x7 pairs into singles when frames are applied
        2. Alternate between Black and Cherry frames for each size
        3. Respect frame quantity limits
        
        Args:
            order_items: List of order items 
            frame_requirements: Dictionary of frame size -> quantity
            
        Returns:
            Modified order items with alternating frame styles
        """
        modified_items = []
        frames_used = {size: 0 for size in frame_requirements.keys()}
        style_counters = {size: 0 for size in frame_requirements.keys()}  # Track frame style alternation
        
        # Process items and apply frames where applicable
        for item in order_items:
            product_code = item.get('product_code', '')
            size_category = item.get('size_category', '')
            quantity = item.get('quantity', 1)
            
            # Skip items that can't have frames (wallets, 3.5x5s)
            if product_code in ['200_sheet', '350_sheet'] or size_category in ['wallet_sheet', 'small_sheet']:
                modified_items.append(item)
                continue
                
            # Skip composites - they already have their own frames
            if size_category == 'trio_composite':
                modified_items.append(item)
                continue
                
            # Determine frame size for this item
            frame_size = self._get_frame_size_for_item(item)
            if not frame_size or frame_size not in frame_requirements:
                modified_items.append(item)
                continue
                
            # Get alternating frame style (Black first, then Cherry)
            frame_style = "Black" if style_counters[frame_size] % 2 == 0 else "Cherry"
                
            # Special handling for 5x7 pairs
            if frame_size == "5x7" and item.get('sheet_type') == 'landscape_2x1':
                # This is a 5x7 pair - split into singles if we have frames
                available_frames = frame_requirements["5x7"] - frames_used["5x7"]
                
                if available_frames > 0:
                    # Split the pair into individual 5x7s
                    images_in_pair = item.get('image_codes', [])
                    
                    # Create individual 5x7 items with frames (only 1 frame per pair for demo)
                    if available_frames >= 1:
                        single_item = item.copy()
                        single_item.update({
                            'product_slug': '5x7_individual_framed',
                            'product_code': '570_individual_framed',
                            'quantity': 1,
                            'image_codes': [images_in_pair[0]],  # Just use first image
                            'size_category': 'medium_sheet',  # Keep in 5x7 section
                            'sheet_type': 'INDIVIDUAL5x7_FRAMED',
                            'display_name': f'5x7 Individual ({frame_style} Framed)',
                            'has_frame': True,
                            'frame_spec': FrameSpec("5x7", frame_style)
                        })
                        modified_items.append(single_item)
                        frames_used["5x7"] += 1
                        style_counters["5x7"] += 1
                    
                    # Add remaining images as unframed individuals if any
                    remaining_images = images_in_pair[1:]
                    for img_code in remaining_images:
                        remaining_item = item.copy()
                        remaining_item.update({
                            'product_slug': '5x7_individual',
                            'product_code': '570_individual',
                            'quantity': 1,
                            'image_codes': [img_code],
                            'size_category': 'medium_sheet',  # Keep in 5x7 section
                            'sheet_type': 'INDIVIDUAL5x7',
                            'display_name': f'5x7 Individual (Unframed)'
                        })
                        modified_items.append(remaining_item)
                else:
                    # No frames available - keep as pair
                    modified_items.append(item)
            else:
                # Regular item (8x10, 10x13, 16x20, 20x24)
                available_frames = frame_requirements[frame_size] - frames_used[frame_size]
                
                if available_frames >= quantity:
                    # Apply frames to all quantities
                    framed_item = item.copy()
                    framed_item.update({
                        'has_frame': True,
                        'frame_spec': FrameSpec(frame_size, frame_style),
                        'display_name': f"{framed_item.get('display_name', '')} ({frame_style} Frame)"
                    })
                    modified_items.append(framed_item)
                    frames_used[frame_size] += quantity
                    style_counters[frame_size] += 1
                elif available_frames > 0:
                    # Partial frames available
                    # Create framed version
                    framed_item = item.copy()
                    framed_item.update({
                        'quantity': available_frames,
                        'has_frame': True,
                        'frame_spec': FrameSpec(frame_size, frame_style),
                        'display_name': f"{framed_item.get('display_name', '')} ({frame_style} Frame)"
                    })
                    modified_items.append(framed_item)
                    
                    # Create unframed version for remainder
                    unframed_item = item.copy()
                    unframed_item['quantity'] = quantity - available_frames
                    modified_items.append(unframed_item)
                    
                    frames_used[frame_size] += available_frames
                    style_counters[frame_size] += 1
                else:
                    # No frames available
                    modified_items.append(item)
        
        logger.info(f"Applied alternating frame styles. Frames used: {frames_used}")
        return modified_items
    
    def _get_frame_size_for_item(self, item: Dict) -> Optional[str]:
        """Determine what frame size applies to an order item"""
        product_code = item.get('product_code', '')
        
        # Map product codes to frame sizes
        frame_size_map = {
            '810': "8x10",
            '1013': "10x13", 
            '1620': "16x20",
            '2024': "20x24",
            '570_sheet': "5x7"  # 5x7 pairs
        }
        
        return frame_size_map.get(product_code)


def create_frame_overlay_engine() -> FrameOverlayEngine:
    """Factory function to create a frame overlay engine"""
    frames_dir = Path("Frames")
    return FrameOverlayEngine(frames_dir)


def apply_frames_simple(order_items: List[Dict], frame_counts: Dict[str, Dict[str, int]]) -> List[Dict]:
    """Assign frame colors to order items based on parsed counts."""

    for item in order_items:
        # Skip trio composites - they already include specific frame info
        if item.get("category") == "trio_composite":
            continue

        size = item.get("size", "").replace(" ", "")
        colors = frame_counts.get(size)
        if not colors:
            continue

        if isinstance(colors, int):
            colors = {"black": colors}
            frame_counts[size] = colors

        preferred = None
        name = item.get("product_name", "").lower()
        if "cherry" in name:
            preferred = "cherry"
        elif "black" in name:
            preferred = "black"

        chosen = None
        if preferred and colors.get(preferred, 0) > 0:
            chosen = preferred
        else:
            for c in ("cherry", "black"):
                if colors.get(c, 0) > 0:
                    chosen = c
                    break

        if chosen:
            item["frame_color"] = chosen.capitalize()
            colors[chosen] -= 1

    return order_items
