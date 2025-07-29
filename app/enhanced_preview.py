"""
Enhanced Portrait Preview Generator - V2 CORRECTED
Fixed orientation, scaling, and sheet container issues per remediation plan
"""

import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageOps
from loguru import logger
import math

# Global safe zone padding in pixels
SAFE_PAD_PX = 40

# Import trio composite functionality
from .trio_composite import TrioCompositeGenerator, is_trio_product, trio_template_filename
from .order_utils import _extract_size_from_item

# Import frame overlay functionality
from .frame_overlay import (
    FrameOverlayEngine,
    FrameSpec,
    create_frame_overlay_engine,
    apply_frames_simple,
)

# Recognized large print sizes for grouping
LARGE_PRINT_SIZES = {"8x10", "10x13", "16x20", "20x24"}


class EnhancedPortraitPreviewGenerator:
    """Generate enhanced portrait previews with corrected orientation, scaling, and sheet logic"""
    
    def __init__(self, products_config: Dict, images_found: Dict, output_dir: Path):
        self.products_config = products_config
        self.images_found = images_found
        self.output_dir = output_dir
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # STEP 1: FREEZE CANVAS CONSTANTS (never change these)
        self.CANVAS_W = 2400
        self.CANVAS_H = 1600

        # STEP 2: DEFINE SAFE DRAWABLE REGION
        self.safe_pad_px = SAFE_PAD_PX
        self.MARGIN_TOP = self.safe_pad_px
        self.MARGIN_LEFT = self.safe_pad_px
        self.MARGIN_RIGHT = self.safe_pad_px
        self.MARGIN_BOTTOM = self.safe_pad_px

        self.DRAW_W = self.CANVAS_W - 2 * self.safe_pad_px
        self.DRAW_H = self.CANVAS_H - 2 * self.safe_pad_px
        
        # STEP 3: PARTITION CANVAS (Left: Regular prints, Right: Composites)
        self.RIGHT_REGION_W = 500  # Fixed pixel width for composites
        self.INTER_REGION_GAP = 20
        self.LEFT_REGION_W = self.DRAW_W - self.RIGHT_REGION_W - self.INTER_REGION_GAP

        # Left region bounds
        self.LEFT_X0 = self.safe_pad_px
        self.LEFT_Y0 = self.safe_pad_px
        self.LEFT_X1 = self.LEFT_X0 + self.LEFT_REGION_W
        self.LEFT_Y1 = self.LEFT_Y0 + self.DRAW_H

        # Right region bounds
        self.RIGHT_X1 = self.CANVAS_W - self.safe_pad_px
        self.RIGHT_X0 = self.RIGHT_X1 - self.RIGHT_REGION_W
        self.RIGHT_Y0 = self.safe_pad_px
        self.RIGHT_Y1 = self.RIGHT_Y0 + self.DRAW_H
        
        self.beige_color = (245, 240, 230)  # Warm beige background
        
        # STEP 4: BUILD PRODUCT SPEC TABLE (single source of truth)
        self.product_specs = self._build_product_spec_table()
        
        # Image processing maps (Step 6)
        self.images = {}  # Will store processed image metadata
        self.master_images = {}  # Will store master cropped portraits
        
        # Initialize trio composite generator
        self.trio_generator = TrioCompositeGenerator(Path("Composites"))
        
        # Initialize frame overlay engine
        self.frame_engine = create_frame_overlay_engine()
        
        logger.info(f"Enhanced preview generator V2 initialized with corrected scaling system")
    
    def parse_frame_data_from_screenshot(self, frame_section_text: str) -> Dict[str, int]:
        """
        Parse frame data from the FRAMES section of screenshot OCR
        
        Args:
            frame_section_text: Text from the FRAMES section of the screenshot
            
        Returns:
            Dictionary mapping frame size to quantity
        """
        frame_requirements = {}
        
        # Example frame data format from screenshot:
        # "2 5 x 7 cherry frame P360CHRsn-GVEBHB"
        # "2 8 x 10 black frame P360BLK8x10-GVE8Ha"
        # "1 10 x 13 black frame 360BLK1dÅ13-MBTS"
        
        lines = frame_section_text.split('\n')
        for line in lines:
            line = line.strip().lower()
            if not line:
                continue
                
            # Try to extract quantity and frame size
            # Look for patterns like "2 5 x 7", "1 8 x 10", etc.
            import re
            
            # Pattern: number followed by dimensions
            patterns = [
                (r'(\d+)\s+5\s*x\s*7', "5x7"),
                (r'(\d+)\s+8\s*x\s*10', "8x10"),
                (r'(\d+)\s+10\s*x\s*13', "10x13"),
                (r'(\d+)\s+16\s*x\s*20', "16x20"),
                (r'(\d+)\s+20\s*x\s*24', "20x24"),
            ]
            
            for pattern, size in patterns:
                match = re.search(pattern, line)
                if match:
                    quantity = int(match.group(1))
                    frame_requirements[size] = frame_requirements.get(size, 0) + quantity
                    logger.debug(f"Parsed frame requirement: {quantity}x {size}")
                    break
        
        logger.info(f"Parsed frame requirements from screenshot: {frame_requirements}")
        return frame_requirements

    def _safe_disp(self, spec: Dict, item: Dict) -> str:
        """Return a safe display name for logging."""
        return spec.get('display_name') or item.get('display_name') or item.get('product_code', 'Unknown')

    def _build_product_spec_table(self) -> Dict[str, Dict]:
        """STEP 4: Build unified Product Spec Table with all product definitions"""
        specs = {
            # BASIC LARGE PRINTS (container = physical size)
            '810': {
                'internal_code': '810',
                'display_name': '8x10 Basic',
                'phys_w_in': 8.0,
                'phys_h_in': 10.0,
                'container_w_in': 8.0,
                'container_h_in': 10.0,
                'category': 'large_print',
                'orientation': 'portrait',
                'cells': 1,
                'cell_aspect': 8.0/10.0
            },
            '1013': {
                'internal_code': '1013', 
                'display_name': '10x13 Basic',
                'phys_w_in': 10.0,
                'phys_h_in': 13.0,
                'container_w_in': 10.0,
                'container_h_in': 13.0,
                'category': 'large_print',
                'orientation': 'portrait',
                'cells': 1,
                'cell_aspect': 10.0/13.0
            },
            '1620': {
                'internal_code': '1620',
                'display_name': '16x20 Basic', 
                'phys_w_in': 16.0,
                'phys_h_in': 20.0,
                'container_w_in': 16.0,
                'container_h_in': 20.0,
                'category': 'large_print',
                'orientation': 'portrait',
                'cells': 1,
                'cell_aspect': 16.0/20.0
            },
            '2024': {
                'internal_code': '2024',
                'display_name': '20x24 Basic',
                'phys_w_in': 20.0,
                'phys_h_in': 24.0,
                'container_w_in': 20.0,
                'container_h_in': 24.0,
                'category': 'large_print',
                'orientation': 'portrait',
                'cells': 1,
                'cell_aspect': 20.0/24.0
            },
            
            # INDIVIDUAL 5x7s (split from pairs)
            '570_individual': {
                'internal_code': '570_individual',
                'display_name': '5x7 Individual',
                'phys_w_in': 5.0,
                'phys_h_in': 7.0,
                'container_w_in': 5.0,
                'container_h_in': 7.0,
                'category': 'medium_print',  # Keep separate from large prints
                'sheet_type': 'INDIVIDUAL5x7',  # Special category for layout
                'orientation': 'portrait',
                'cells': 1,
                'cell_aspect': 5.0/7.0
            },
            
            # INDIVIDUAL 5x7s WITH FRAMES
            '570_individual_framed': {
                'internal_code': '570_individual_framed',
                'display_name': '5x7 Individual (Framed)',
                'phys_w_in': 5.0,
                'phys_h_in': 7.0,
                'container_w_in': 5.0,
                'container_h_in': 7.0,
                'category': 'medium_print',  # Keep separate from large prints
                'sheet_type': 'INDIVIDUAL5x7_FRAMED',  # Special category for layout
                'orientation': 'portrait',
                'cells': 1,
                'cell_aspect': 5.0/7.0
            },
            
            # SHEET PRODUCTS - CORRECTED SIZES: 5x7=10x7 landscape, 3.5x5=7x10 portrait
            '570_sheet': {
                'internal_code': '570_sheet',
                'display_name': '5x7 Pair',
                'phys_w_in': 10.0,  # Container is 10x7 LANDSCAPE
                'phys_h_in': 7.0,
                'container_w_in': 10.0,
                'container_h_in': 7.0,
                'category': 'sheet_print',
                'sheet_type': 'PAIR5x7',  # NEW: Sub-category for row separation
                'orientation': 'landscape',  # Container is landscape, images portrait
                'cells': 2,
                'cell_aspect': 5.0/7.0,  # Images still portrait 5x7
                'grid_rows': 1,
                'grid_cols': 2
            },
            '350_sheet': {
                'internal_code': '350_sheet',
                'display_name': '3.5x5 Sheet of 4',
                'phys_w_in': 7.0,  # Container is 7x10 PORTRAIT (remove extra inch)
                'phys_h_in': 10.0,
                'container_w_in': 7.0,
                'container_h_in': 10.0,
                'category': 'sheet_print',
                'sheet_type': 'SHEET3x5',  # NEW: Sub-category for row separation
                'orientation': 'portrait',
                'cells': 4,
                'cell_aspect': 3.5/5.0,
                'grid_rows': 2,
                'grid_cols': 2
            },
            '200_sheet': {
                'internal_code': '200_sheet',
                'display_name': 'Wallet Sheet of 8',
                'phys_w_in': 10.0,  # Container is 10x7 LANDSCAPE (4 wallets × 2.5" = 10" wide)
                'phys_h_in': 7.0,   # 2 wallets × 3.5" = 7" tall
                'container_w_in': 10.0,
                'container_h_in': 7.0,
                'category': 'sheet_print',
                'sheet_type': 'WALLET8',  # NEW: Sub-category for row separation
                'orientation': 'landscape',  # Container is landscape for optimal wallet fit
                'cells': 8,
                'cell_aspect': 2.5/3.5,
                'grid_rows': 2,
                'grid_cols': 4
            },
            
            # TRIO COMPOSITES 
            '510.3': {
                'internal_code': '510.3',
                'display_name': '5x10 Trio Frame',
                'phys_w_in': 10.0,  # Landscape container
                'phys_h_in': 5.0,
                'container_w_in': 10.0,
                'container_h_in': 5.0,
                'category': 'trio_composite',
                'orientation': 'landscape',  # Container is landscape
                'cells': 3,
                'cell_aspect': None,  # Portrait openings expect portrait images
                'openings': [  # 3 portrait windows as % of container
                    {'x': 0.05, 'y': 0.05, 'w': 0.27, 'h': 0.90},
                    {'x': 0.36, 'y': 0.05, 'w': 0.27, 'h': 0.90},
                    {'x': 0.67, 'y': 0.05, 'w': 0.27, 'h': 0.90}
                ]
            },
            '1020.5': {
                'internal_code': '1020.5', 
                'display_name': '10x20 Trio Frame',
                'phys_w_in': 20.0,  # Landscape container
                'phys_h_in': 10.0,
                'container_w_in': 20.0,
                'container_h_in': 10.0,
                'category': 'trio_composite',
                'orientation': 'landscape',  # Container is landscape  
                'cells': 3,
                'cell_aspect': None,  # Portrait openings expect portrait images
                'openings': [  # 3 portrait windows as % of container
                    {'x': 0.05, 'y': 0.05, 'w': 0.27, 'h': 0.90},
                    {'x': 0.36, 'y': 0.05, 'w': 0.27, 'h': 0.90},
                    {'x': 0.67, 'y': 0.05, 'w': 0.27, 'h': 0.90}
                ]
            }
        }
        
        logger.info(f"Built product spec table with {len(specs)} product definitions")
        return specs

    def _process_images(self, order_items: List[Dict]) -> None:
        """STEP 6-12: Process all images to canonical portrait orientation with master crops"""
        
        # Collect all unique image codes from order
        all_codes = set()
        for item in order_items:
            codes = item.get('image_codes', [])
            all_codes.update(codes)
        
        logger.info(f"Processing {len(all_codes)} unique image codes")
        
        for code in all_codes:
            if code not in self.images_found:
                logger.warning(f"Image code {code} not found in available images")
                continue
                
            image_path = self.images_found[code][0]
            
            try:
                # STEP 7: Load and apply EXIF autorotate
                with Image.open(image_path) as img:
                    # Apply EXIF orientation correction
                    img = ImageOps.exif_transpose(img)
                    
                    # STEP 8: Force canonical portrait orientation
                    if img.width > img.height:
                        # Rotate 90° counterclockwise to make portrait
                        img = img.rotate(90, expand=True)
                        logger.debug(f"Rotated {code} from landscape to portrait")
                    
                    # Store image metadata
                    self.images[code] = {
                        'filepath': image_path,
                        'width_px': img.width,
                        'height_px': img.height,
                        'canonical_portrait_img': img.copy()
                    }
                    
                    # STEP 10: Determine controlling crop (largest product using this image)
                    controlling_spec = self._find_controlling_product_for_image(code, order_items)
                    target_aspect = controlling_spec['cell_aspect'] if controlling_spec else (8.0/10.0)
                    
                    # STEP 11: Apply controlling crop to create master image
                    master_img = self._crop_to_aspect(img, target_aspect)
                    self.master_images[code] = master_img
                    
                    logger.debug(f"Processed image {code}: {img.width}x{img.height} -> master crop aspect {target_aspect:.3f}")
                    
            except Exception as e:
                logger.error(f"Failed to process image {code}: {e}")
                continue

    def _find_controlling_product_for_image(self, image_code: str, order_items: List[Dict]) -> Optional[Dict]:
        """STEP 10: Find the largest product (by area) that uses this image"""
        largest_area = 0
        controlling_spec = None
        
        for item in order_items:
            if image_code in item.get('image_codes', []):
                product_code = item.get('product_code', '')
                if product_code in self.product_specs:
                    spec = self.product_specs[product_code]
                    # Only consider large prints and sheets for controlling crop (exclude composites)
                    if spec['category'] in ['large_print', 'sheet_print']:
                        area = spec['container_w_in'] * spec['container_h_in']
                        if area > largest_area:
                            largest_area = area
                            controlling_spec = spec
        
        return controlling_spec

    def _crop_to_aspect(self, img: Image.Image, target_aspect: float) -> Image.Image:
        """STEP 11: Crop image to target aspect ratio (center-weighted)"""
        current_aspect = img.width / img.height
        
        if abs(current_aspect - target_aspect) < 0.01:
            return img  # Already correct aspect
            
        if current_aspect > target_aspect:
            # Image too wide, crop width
            new_width = int(img.height * target_aspect)
            x_offset = (img.width - new_width) // 2
            crop_box = (x_offset, 0, x_offset + new_width, img.height)
        else:
            # Image too tall, crop height  
            new_height = int(img.width / target_aspect)
            y_offset = (img.height - new_height) // 2
            crop_box = (0, y_offset, img.width, y_offset + new_height)
            
        return img.crop(crop_box)

    def _sort_items_by_size_corrected(self, items: List[Dict]) -> List[Dict]:
        """Sort items by physical height (largest first) for proper scaling display"""
        def get_height_priority(item):
            product_code = item.get('product_code', '')
            if product_code in self.product_specs:
                spec = self.product_specs[product_code]
                return spec['container_h_in']
            return 5.0  # Default
        
        return sorted(items, key=get_height_priority, reverse=True)

    def _calculate_corrected_layout(self, sorted_items: List[Dict]) -> List[Dict]:
        """STEP 17-20: Calculate layout with proper PPI scaling where 8x10 is smallest large print"""
        
        # Group items by category using product specs
        groups = self._group_items_by_category(sorted_items)
        
        # STEP 17: Calculate global PPI for left region
        ppi_left = self._calculate_optimal_ppi(groups)
        
        # Calculate reference dimensions for 8x10 (for wallets which still use 8x10)
        eight_w_px = round(8.0 * ppi_left)
        eight_h_px = round(10.0 * ppi_left)
        
        logger.info(f"Proportional scaling: PPI={ppi_left:.1f}, 8x10 ref={eight_w_px}x{eight_h_px}px, 5x7=10x7 landscape, 3.5x5=7x10 portrait, wallets=10x7 landscape")
        
        # STEP 33-37: Layout rows with proper spacing
        layout = self._layout_groups_with_ppi(groups, ppi_left, eight_w_px, eight_h_px)
        
        return layout

    def _group_items_by_category(self, items: List[Dict]) -> Dict[str, List[Dict]]:
        """Group items by category using product specs - SEPARATED BY SHEET TYPE"""
        groups = {
            'large_print': [],
            'PAIR5x7': [],      # NEW: Separate row for 5x7 pairs
            'SHEET3x5': [],     # NEW: Separate row for 3.5x5 sheets  
            'WALLET8': [],      # NEW: Separate row for wallet sheets
            'trio_composite': []
        }
        
        for i, item in enumerate(items):
            product_code = item.get('product_code', '')
            if product_code in self.product_specs:
                spec = self.product_specs[product_code]
                
                # Determine grouping key
                if spec['category'] == 'large_print':
                    group_key = 'large_print'
                elif spec['category'] == 'sheet_print':
                    group_key = spec.get('sheet_type', 'sheet_print')  # Use sheet_type for separation
                elif spec['category'] == 'trio_composite':
                    group_key = 'trio_composite'
                else:
                    continue  # Skip unknown categories
                
                if group_key in groups:
                    # STEP 2: Collapse quantities - store sheet_qty instead of expanding
                    processed_item = {
                        'item': item,
                        'spec': spec,
                        'original_index': i,
                        'sheet_qty': item.get('quantity', 1) if spec['category'] == 'sheet_print' else 1
                    }
                    groups[group_key].append(processed_item)
        
        return {k: v for k, v in groups.items() if v}  # Remove empty groups

    def _calculate_optimal_ppi(self, groups: Dict[str, List[Dict]]) -> float:
        """STEP 17: Calculate dynamic PPI that fills available space optimally - considers both width AND height"""
        
        # Calculate width constraints (existing logic)
        max_width_needed = 0
        
        for group_name, group_items in groups.items():
            if group_name == 'trio_composite':
                continue  # Skip composites - they go in right region
                
            # Calculate total width for this row in inches
            total_width_in = 0
            gap_in = 0.5  # Half-inch gaps between items
            
            for item_data in group_items:
                spec = item_data['spec']
                total_width_in += spec['container_w_in']
            
            if len(group_items) > 1:
                total_width_in += gap_in * (len(group_items) - 1)
            
            max_width_needed = max(max_width_needed, total_width_in)
            
            logger.debug(f"Group {group_name}: {len(group_items)} items, {total_width_in:.1f}\" total width")
        
        # NEW: Calculate height constraints
        total_height_needed = self._calculate_total_height_needed(groups)
        
        # Calculate PPI based on both width and height constraints
        width_ppi = self.LEFT_REGION_W / max_width_needed if max_width_needed > 0 else 80
        height_ppi = self.DRAW_H / total_height_needed if total_height_needed > 0 else 80
        
        # Use the more restrictive constraint, but apply dynamic scaling based on order size
        base_ppi = min(width_ppi, height_ppi)
        
        # NEW: Dynamic scaling based on total item count for better space utilization
        total_items = sum(len(items) for group, items in groups.items() if group != 'trio_composite')
        
        # Scale factor based on order size - fewer items = bigger scale, more items = smaller scale
        if total_items <= 3:
            # Very small orders - make items much larger to fill space
            scale_factor = 1.4
        elif total_items <= 8:
            # Small orders - make items larger
            scale_factor = 1.2
        elif total_items <= 15:
            # Medium orders - normal scaling
            scale_factor = 1.0
        elif total_items <= 25:
            # Large orders - slightly smaller to fit more
            scale_factor = 0.9
        else:
            # Very large orders - much smaller to ensure everything fits at a glance
            scale_factor = 0.75
        
        # Apply scaling factor while maintaining ratio constraints
        ppi = base_ppi * scale_factor
        
        # Apply reasonable bounds - wider range for better fill
        ppi = min(ppi, 120)  # Higher maximum for small orders
        ppi = max(ppi, 25)   # Lower minimum for large orders
        
        logger.info(f"Dynamic PPI calculation:")
        logger.info(f"  - Max width needed: {max_width_needed:.1f}\", Height needed: {total_height_needed:.1f}\"")
        logger.info(f"  - Width PPI: {width_ppi:.1f}, Height PPI: {height_ppi:.1f}")
        logger.info(f"  - Total items: {total_items}, Scale factor: {scale_factor:.2f}")
        logger.info(f"  - Final PPI: {ppi:.1f} (optimized for space fill)")
        
        return ppi
    
    def _calculate_total_height_needed(self, groups: Dict[str, List[Dict]]) -> float:
        """Calculate total height needed for all groups in inches"""
        
        # Define row order (same as layout)
        row_order = ['large_print', 'ALL_5x7', 'SHEET3x5', 'WALLET8']
        
        total_height = 0
        row_gap_in = 30 / 50  # Convert pixel gap to inches (approx 0.6")
        subtitle_space_in = 30 / 50  # Space for subtitles
        
        for group_name in row_order:
            if group_name not in groups:
                continue
                
            group_items = groups[group_name]
            if not group_items:
                continue
            
            # Find the tallest item in this group (max container height)
            max_height_in = 0
            for item_data in group_items:
                spec = item_data['spec']
                item_height = spec['container_h_in']
                
                # Add frame thickness if item has a frame
                item = item_data['item']
                if item.get('has_frame') and item.get('frame_spec'):
                    frame_spec = item.get('frame_spec')
                    # Estimate frame thickness in inches (typical frame is ~0.5" thick)
                    frame_thickness_in = 0.5
                    item_height += frame_thickness_in
                
                max_height_in = max(max_height_in, item_height)
            
            # Add subtitle space for this row
            row_height = max_height_in + subtitle_space_in
            total_height += row_height
            
            # Add gap before next row (except for last row)
            if group_name != row_order[-1]:
                total_height += row_gap_in
            
            logger.debug(f"Group {group_name}: max height {max_height_in:.1f}\", total with subtitle: {row_height:.1f}\"")
        
        # Add top/bottom margins
        margin_in = 40 / 50  # Convert pixel margins to inches
        total_height += margin_in
        
        logger.debug(f"Total height needed: {total_height:.1f}\" (available: {self.DRAW_H / 50:.1f}\")")
        return total_height

    def _layout_groups_with_ppi(self, groups: Dict[str, List[Dict]], ppi: float, 
                               eight_w_px: int, eight_h_px: int) -> List[Dict]:
        """STEP 33-37: Layout groups in rows with proper spacing - SEPARATED SHEET ROWS"""
        layout = []
        
        # STEP 9: Strict vertical order - separate row for each sheet type
        row_order = ['large_print', 'ALL_5x7', 'SHEET3x5', 'WALLET8']
        
        current_y = self.LEFT_Y0 + 20  # Start with small top margin
        row_gap = 30  # Gap between rows
        
        for group_name in row_order:
            logger.debug(f"🔍 Checking group '{group_name}' - exists: {group_name in groups}")
            if group_name not in groups:
                logger.debug(f"🔍 Skipping group '{group_name}' - not found in groups")
                continue
                
            group_items = groups[group_name]
            logger.debug(f"🔍 Processing group '{group_name}' with {len(group_items)} items")
            
            # Calculate row layout - different logic for sheet types vs individual items
            logger.debug(f"🎯 Processing group '{group_name}' with {len(group_items)} items")
            if group_name == 'ALL_5x7':
                # Mixed 5x7 group - contains both individual items and pairs
                logger.info(f"🎯 Using mixed 5x7 layout for group: {group_name}")
                row_layout = self._layout_mixed_5x7_group(group_items, ppi, current_y, eight_w_px, eight_h_px)
            elif group_name in ['SHEET3x5', 'WALLET8']:
                row_layout = self._layout_sheet_row(group_items, ppi, current_y, eight_w_px, eight_h_px, group_name)
            else:
                row_layout = self._layout_single_row(group_items, ppi, current_y, eight_w_px, eight_h_px)
            
            layout.extend(row_layout)
            logger.debug(f"🔍 Added {len(row_layout)} items from group '{group_name}' to layout")
            
            # Move to next row position
            if row_layout:
                max_bottom = max(item['y'] + item['height'] for item in row_layout)
                current_y = max_bottom + row_gap
                logger.debug(f"🔍 Updated current_y to {current_y} after group '{group_name}'")
        
        return layout
    
    def _layout_mixed_5x7_group(self, group_items: List[Dict], ppi: float, start_y: int,
                               eight_w_px: int, eight_h_px: int) -> List[Dict]:
        """Layout mixed 5x7 group containing both individual items and pairs"""
        layout = []
        
        # Separate individual 5x7s from pairs for easier processing
        individual_items = []
        pair_items = []
        
        for item_data in group_items:
            item = item_data['item']
            sheet_type = item_data['spec'].get('sheet_type', '')
            
            if sheet_type in ['INDIVIDUAL5x7_FRAMED', 'INDIVIDUAL5x7']:
                individual_items.append(item_data)
            elif sheet_type == 'PAIR5x7':
                pair_items.append(item_data)
        
        logger.info(f"Mixed 5x7 group: {len(individual_items)} individuals, {len(pair_items)} pairs, total items: {len(group_items)}")
        
        # Layout all items with proper row wrapping, left to right
        current_x = self.LEFT_X0
        current_y = start_y
        item_gap = round(0.5 * ppi)  # 0.5 inch gaps
        row_height = 0  # Track the height of the current row
        
        # Subtitle space constant (pixels)
        subtitle_space = 30  # Space for subtitle below each image
        
        # Combine all items for unified layout with wrapping
        all_items = individual_items + pair_items
        
        for item_data in all_items:
            spec = item_data['spec']
            item = item_data['item']
            
            # Calculate pixel dimensions
            width_px = round(spec['container_w_in'] * ppi)
            height_px = round(spec['container_h_in'] * ppi)
            
            # Add extra space for frames if this item has a frame
            if item.get('has_frame') and item.get('frame_spec'):
                frame_spec = item.get('frame_spec')
                width_px += frame_spec.left_thickness + frame_spec.right_thickness
                height_px += frame_spec.top_thickness + frame_spec.bottom_thickness
                logger.debug(
                    f"Added frame space to {self._safe_disp(spec, item)}: "
                    f"+{frame_spec.left_thickness + frame_spec.right_thickness}px width, "
                    f"+{frame_spec.top_thickness + frame_spec.bottom_thickness}px height"
                )
            
            # Calculate total height including subtitle space
            total_height_px = height_px + subtitle_space
            
            # Check if this item would overflow the right boundary
            if current_x + width_px > self.LEFT_X1 and current_x > self.LEFT_X0:
                # Wrap to next row
                current_x = self.LEFT_X0
                current_y += row_height + 20  # Move down by row height + gap
                row_height = 0  # Reset row height for new row
                logger.debug(
                    f"5x7 section wrapped to new row at y={current_y} for {self._safe_disp(spec, item)}"
                )
            
            layout.append({
                'x': current_x,
                'y': current_y,
                'width': width_px,
                'height': height_px,
                'spec': spec,
                'item': item,
                'original_index': item_data['original_index']
            })
            
            # Update row height to tallest item in this row (including subtitle space)
            row_height = max(row_height, total_height_px)
            
            current_x += width_px + item_gap
        
        return layout
    
    def _layout_single_row(self, group_items: List[Dict], ppi: float, start_y: int,
                          eight_w_px: int, eight_h_px: int) -> List[Dict]:
        """Layout items with proper row wrapping to prevent overflow"""
        row_layout = []
        
        current_x = self.LEFT_X0  # Start at left margin
        current_y = start_y
        item_gap = round(0.5 * ppi)  # 0.5 inch gaps
        row_height = 0  # Track the height of the current row
        
        # Subtitle space constant (pixels)
        subtitle_space = 30  # Space for subtitle below each image
        
        for item_data in group_items:
            spec = item_data['spec']
            item = item_data['item']
            
            # Calculate pixel dimensions from physical inches (proportional scaling)
            width_px = round(spec['container_w_in'] * ppi)
            height_px = round(spec['container_h_in'] * ppi)
            
            # Add extra space for frames if this item has a frame
            if item.get('has_frame') and item.get('frame_spec'):
                frame_spec = item.get('frame_spec')
                width_px += frame_spec.left_thickness + frame_spec.right_thickness
                height_px += frame_spec.top_thickness + frame_spec.bottom_thickness
                logger.debug(
                    f"Added frame space to {self._safe_disp(spec, item)}: "
                    f"+{frame_spec.left_thickness + frame_spec.right_thickness}px width, "
                    f"+{frame_spec.top_thickness + frame_spec.bottom_thickness}px height"
                )
            
            # Add space for subtitle below the image
            total_height_px = height_px + subtitle_space
            
            # Check if this item would overflow the right boundary
            if current_x + width_px > self.LEFT_X1 and current_x > self.LEFT_X0:
                # Wrap to next row
                current_x = self.LEFT_X0
                current_y += row_height + 20  # Move down by row height + gap
                row_height = 0  # Reset row height for new row
                logger.debug(
                    f"Wrapped to new row at y={current_y} for {self._safe_disp(spec, item)}"
                )
            
            # Position item (height is still the image height, subtitle space is handled in row calculations)
            row_layout.append({
                'x': current_x,
                'y': current_y,
                'width': width_px,
                'height': height_px,
                'spec': spec,
                'item': item,
                'original_index': item_data['original_index']
            })
            
            # Update row height to tallest item in this row (including subtitle space)
            row_height = max(row_height, total_height_px)
            
            # Move to next position
            current_x += width_px + item_gap
        
        return row_layout

    def _layout_sheet_row(self, group_items: List[Dict], ppi: float, start_y: int,
                         eight_w_px: int, eight_h_px: int, sheet_type: str) -> List[Dict]:
        """Layout sheet row using correct proportional container sizes"""
        row_layout = []
        
        # Subtitle space constant (pixels)
        subtitle_space = 30  # Space for subtitle below each image
        
        # Use actual container dimensions for each sheet type (proportional scaling)
        if group_items:
            spec = group_items[0]['spec']  # All items in group have same spec
            container_w = round(spec['container_w_in'] * ppi)
            container_h = round(spec['container_h_in'] * ppi)
        else:
            container_w = eight_w_px  # Fallback
            container_h = eight_h_px
        
        # STEP 6: Calculate how many containers fit across left region
        item_gap = round(0.5 * ppi)  # 0.5 inch gaps
        cols = max(1, (self.LEFT_REGION_W + item_gap) // (container_w + item_gap))
        
        logger.info(f"Sheet row {sheet_type}: {len(group_items)} items, {cols} columns, container={container_w}x{container_h}px")
        
        current_x = self.LEFT_X0  # Start at left margin
        current_y = start_y
        col = 0
        
        for item_data in group_items:
            spec = item_data['spec']
            item = item_data['item']
            sheet_qty = item_data.get('sheet_qty', 1)
            
            # STEP 6: Wrap to next line if needed
            if col >= cols:
                col = 0
                current_x = self.LEFT_X0
                current_y += container_h + subtitle_space + 20  # Move to next line with gap + subtitle space
            
            # Position item using consistent container size
            row_layout.append({
                'x': current_x,
                'y': current_y,
                'width': container_w,
                'height': container_h,
                'spec': spec,
                'item': item,
                'sheet_qty': sheet_qty,  # Store quantity for badge rendering
                'sheet_type': sheet_type,  # Store type for specific rendering
                'original_index': item_data['original_index']
            })
            
            # Move to next position
            current_x += container_w + item_gap
            col += 1
        
        return row_layout

    def _calculate_corrected_layout_with_composites(self, sorted_regular_items: List[Dict], 
                                                   trio_items: List[Tuple[Dict, Dict]]) -> List[Dict]:
        """Calculate layout including composites in the same proportional scaling system"""
        
        # Convert trio items to regular format for grouping
        trio_regular_items = []
        for item, product_config in trio_items:
            # Get or create spec for trio item
            product_code = item.get('product_code', '')
            if product_code in self.product_specs:
                spec = self.product_specs[product_code]
            else:
                # Create temporary spec for unknown trios
                if "1020" in product_code:
                    spec = {'container_w_in': 20.0, 'container_h_in': 10.0, 'category': 'trio_composite'}
                else:
                    spec = {'container_w_in': 10.0, 'container_h_in': 5.0, 'category': 'trio_composite'}
            
            trio_regular_items.append({
                'item': item,
                'spec': spec,
                'original_index': len(sorted_regular_items) + len(trio_regular_items),
                'is_composite': True
            })
        
        # Convert regular items to consistent format
        formatted_regular_items = []
        for i, item in enumerate(sorted_regular_items):
            formatted_regular_items.append({
                'item': item,
                'spec': None,  # Will be looked up in grouping
                'original_index': i,
                'is_composite': False
            })
        
        # Combine all items for unified PPI calculation
        all_items = formatted_regular_items + trio_regular_items
        
        # Group items by category (now including composites)
        groups = self._group_items_by_category_with_composites(all_items)
        
        # Dynamically solve for PPI that perfectly fits all rows
        layout, ppi_unified = self._fit_ppi(groups)

        logger.info(
            f"Unified proportional scaling: PPI={ppi_unified:.1f}, includes composites at correct ratios"
        )

        return layout

    def _group_items_by_category_with_composites(self, items: List[Dict]) -> Dict[str, List[Dict]]:
        """Group items including composites in proper categories"""
        groups = {
            'large_print': [],
            'ALL_5x7': [],  # Combined group for all 5x7 types
            'SHEET3x5': [],
            'WALLET8': [],
            'trio_composite': []
        }
        
        for item_data in items:
            if item_data.get('is_composite'):
                # This is a composite item
                groups['trio_composite'].append(item_data)
            else:
                # This is a regular item, need to look up spec
                item = item_data['item']
                product_code = item.get('product_code', '')
                
                # Look up spec or fallback based on item info
                if product_code in self.product_specs:
                    spec = self.product_specs[product_code]
                else:
                    size_cat = item.get('size_category')
                    name = item.get('display_name', 'Unknown')
                    if size_cat == 'large_print' or any(sz in name for sz in LARGE_PRINT_SIZES):
                        guessed_size = _extract_size_from_item(item) or '8x10'
                        width, height = {
                            '10x13': (10.0, 13.0),
                            '16x20': (16.0, 20.0),
                            '20x24': (20.0, 24.0)
                        }.get(guessed_size, (8.0, 10.0))
                        spec = {
                            'container_w_in': width,
                            'container_h_in': height,
                            'category': 'large_print'
                        }
                    else:
                        continue  # Skip items without recognizable size
                
                if spec['category'] == 'large_print':
                    group_key = 'large_print'
                elif spec['category'] == 'medium_print':
                    # Individual 5x7s - all go to unified 5x7 group
                    group_key = 'ALL_5x7'
                elif spec['category'] == 'sheet_print':
                    sheet_type = spec.get('sheet_type', 'sheet_print')
                    if sheet_type == 'PAIR5x7':
                        # 5x7 pairs also go to unified 5x7 group
                        group_key = 'ALL_5x7'
                    else:
                        group_key = sheet_type
                else:
                    continue
                
                if group_key in groups:
                    # Add sheet_qty for sheet products
                    processed_item = {
                        'item': item,
                        'spec': spec,
                        'original_index': item_data['original_index'],
                        'sheet_qty': item.get('quantity', 1) if spec['category'] == 'sheet_print' else 1
                    }
                    logger.debug(f"🔍 Grouping item '{spec.get('display_name', 'Unknown')}' into group '{group_key}'")
                    groups[group_key].append(processed_item)
        
        final_groups = {k: v for k, v in groups.items() if v}
        logger.info(f"�� Final groups: {[(k, len(v)) for k, v in final_groups.items()]}")
        return final_groups

    def _calculate_optimal_ppi_with_composites(self, groups: Dict[str, List[Dict]]) -> float:
        """Calculate dynamic PPI including composites - fills available space optimally"""
        
        # Calculate width requirements for left region (regular products)
        max_left_width = 0
        for group_name, group_items in groups.items():
            if group_name == 'trio_composite':
                continue  # Skip composites for left region calculation
                
            total_width_in = 0
            gap_in = 0.5
            
            for item_data in group_items:
                spec = item_data['spec']
                total_width_in += spec['container_w_in']
            
            if len(group_items) > 1:
                total_width_in += gap_in * (len(group_items) - 1)
            
            max_left_width = max(max_left_width, total_width_in)
        
        # Calculate height requirements for left region
        left_height_needed = self._calculate_total_height_needed(groups)
        
        # Calculate requirements for right region (composites)
        max_right_width = 0
        total_right_height = 0
        if 'trio_composite' in groups:
            composite_items = groups['trio_composite']
            if composite_items:
                # Sort composites by size (largest first)
                sorted_composites = sorted(composite_items, 
                                         key=lambda x: x['spec']['container_w_in'] * x['spec']['container_h_in'], 
                                         reverse=True)
                # Use width of largest composite
                max_right_width = sorted_composites[0]['spec']['container_w_in']
                
                # Calculate total height needed for composites
                gap_in = 0.6  # Gap between composites
                for i, item_data in enumerate(sorted_composites):
                    spec = item_data['spec']
                    total_right_height += spec['container_h_in']
                    if i < len(sorted_composites) - 1:  # Add gap except for last item
                        total_right_height += gap_in
                
                # Add margins for composites
                total_right_height += 0.8  # Top/bottom margins
        
        # Calculate PPI constraints for both regions
        left_width_ppi = self.LEFT_REGION_W / max_left_width if max_left_width > 0 else 120
        left_height_ppi = self.DRAW_H / left_height_needed if left_height_needed > 0 else 120
        right_width_ppi = self.RIGHT_REGION_W / max_right_width if max_right_width > 0 else 120
        right_height_ppi = self.DRAW_H / total_right_height if total_right_height > 0 else 120
        
        # Find the most restrictive constraint, respecting both columns
        left_ppi = min(left_width_ppi, left_height_ppi)
        right_ppi = min(right_width_ppi, right_height_ppi)
        base_ppi = min(left_ppi, right_ppi)
        
        # Apply dynamic scaling based on total item count (including composites)
        total_items = sum(len(items) for group, items in groups.items())
        
        # Scale factor based on order size
        if total_items <= 3:
            scale_factor = 1.4
        elif total_items <= 8:
            scale_factor = 1.2
        elif total_items <= 15:
            scale_factor = 1.0
        elif total_items <= 25:
            scale_factor = 0.9
        else:
            scale_factor = 0.75
        
        # Apply scaling while maintaining ratio constraints
        ppi = base_ppi * scale_factor

        # Clamp against hard limits after scaling
        ppi = min(
            ppi,
            left_width_ppi,
            left_height_ppi,
            right_width_ppi,
            right_height_ppi,
            120,  # Upper bound for very small orders
        )
        ppi = max(ppi, 20)  # Lower bound for very large orders
        
        logger.info(f"Dynamic unified PPI calculation:")
        logger.info(f"  - Left: width={max_left_width:.1f}\", height={left_height_needed:.1f}\"")
        logger.info(f"  - Right: width={max_right_width:.1f}\", height={total_right_height:.1f}\"")
        logger.info(f"  - PPIs: L_w={left_width_ppi:.1f}, L_h={left_height_ppi:.1f}, R_w={right_width_ppi:.1f}, R_h={right_height_ppi:.1f}")
        logger.info(f"  - Total items: {total_items}, Scale factor: {scale_factor:.2f}, Final PPI: {ppi:.1f}")
        
        return ppi

    def _layout_composites_with_ppi(self, composite_items: List[Dict], ppi: float) -> List[Dict]:
        """Layout composites in right region using unified PPI scaling"""
        layout = []
        
        if not composite_items:
            return layout
        
        # Sort composites by size (10×20 first, then 5×10 - largest first)
        sorted_composites = sorted(composite_items, 
                                 key=lambda x: x['spec']['container_w_in'] * x['spec']['container_h_in'], 
                                 reverse=True)
        
        current_y = self.RIGHT_Y0 + 20
        gap = 30
        
        for item_data in sorted_composites:
            spec = item_data['spec']
            item = item_data['item']
            
            # Calculate dimensions using unified PPI
            width_px = round(spec['container_w_in'] * ppi)
            height_px = round(spec['container_h_in'] * ppi)
            
            # Center horizontally in right region and clamp
            x = self.RIGHT_X0 + (self.RIGHT_REGION_W - width_px) // 2
            x = max(self.RIGHT_X0, min(x, self.RIGHT_X1 - width_px))
            
            layout.append({
                'x': x,
                'y': current_y,
                'width': width_px,
                'height': height_px,
                'spec': spec,
                'item': item,
                'is_composite': True,
                'original_index': item_data['original_index']
            })
            
            current_y += height_px + gap
            
            logger.debug(f"Composite {spec['container_w_in']}×{spec['container_h_in']} -> {width_px}×{height_px}px at ({x}, {current_y-height_px-gap})")
        
        return layout

    def _layout_with_ppi(self, groups: Dict[str, List[Dict]], ppi: float) -> List[Dict]:
        """Helper that lays out all products using a given PPI."""
        eight_w_px = round(8.0 * ppi)
        eight_h_px = round(10.0 * ppi)

        left_layout = self._layout_groups_with_ppi(groups, ppi, eight_w_px, eight_h_px)
        right_layout = self._layout_composites_with_ppi(groups.get('trio_composite', []), ppi)

        return left_layout + right_layout

    def _fit_ppi(self, groups: Dict[str, List[Dict]]) -> Tuple[List[Dict], float]:
        """Binary search the tightest PPI that fits within the canvas."""
        LOW, HIGH = 5.0, 140.0

        def try_ppi(ppi: float) -> Tuple[List[Dict], float]:
            layout = self._layout_with_ppi(groups, ppi)
            used_bottom = max((i['y'] + i['height'] for i in layout), default=0)
            overflow = used_bottom - (self.CANVAS_H - self.safe_pad_px)
            return layout, overflow

        lo, hi = LOW, HIGH
        best_layout = None
        for _ in range(12):
            mid = (lo + hi) / 2
            layout, overflow = try_ppi(mid)
            if overflow <= 0:
                best_layout = layout
                lo = mid
            else:
                hi = mid

        return best_layout if best_layout is not None else [], lo

    def _enforce_safe_zone(self, layout: List[Dict]):
        """Ensure all layout rectangles stay within the safe padding."""
        pad = self.safe_pad_px
        for item in layout:
            assert item['x'] >= pad and item['y'] >= pad, "Item fell above/left of safe zone"
            assert item['x'] + item['width'] <= self.CANVAS_W - pad, "Item overflowed right edge"
            assert item['y'] + item['height'] <= self.CANVAS_H - pad, "Item overflowed bottom edge"

    def _draw_product_corrected(self, canvas: Image.Image, position: Dict):
        """Draw product using corrected orientation and master images - includes composites"""
        x, y = position['x'], position['y']
        width, height = position['width'], position['height']
        spec = position.get('spec') or self._find_product_config(position.get('item', {}).get('product_slug', '')) or {}
        item = position['item']
        
        # Check if this is a composite
        if position.get('is_composite'):
            self._draw_composite_with_unified_scaling(canvas, position)
            return
        
        draw = ImageDraw.Draw(canvas)

        # Draw container border (thin gray)
        draw.rectangle([x-2, y-2, x+width+2, y+height+2], outline=(120, 120, 120), width=2)
        
        # Draw white background
        draw.rectangle([x, y, x+width, y+height], fill=(255, 255, 255), outline=(180, 180, 180))
        
        # Get image codes for this product
        image_codes = item.get('image_codes', [])
        
        # Check the sheet type and category to determine rendering method
        sheet_type = position.get('sheet_type', spec.get('sheet_type'))
        
        category = spec.get('category', 'large_print')
        if category == 'large_print':
            # STEP 22: Render single large print
            self._render_large_print(canvas, x, y, width, height, image_codes, spec, item)
        elif category == 'medium_print' or sheet_type in ['INDIVIDUAL5x7', 'INDIVIDUAL5x7_FRAMED']:
            # STEP 22: Render individual 5x7 (framed or unframed)
            self._render_large_print(canvas, x, y, width, height, image_codes, spec, item)
        elif category == 'sheet_print':
            # STEP 7: Use specific renderer based on sheet type
            if sheet_type == 'PAIR5x7':
                self._render_5x7_pair_sheet(canvas, x, y, width, height, image_codes, spec)
            elif sheet_type == 'SHEET3x5':
                self._render_3x5_sheet(canvas, x, y, width, height, image_codes, spec)
            elif sheet_type == 'WALLET8':
                self._render_wallet_sheet(canvas, x, y, width, height, image_codes, spec)
            else:
                # Fallback to generic sheet rendering
                self._render_sheet_print(canvas, x, y, width, height, image_codes, spec)
        
        # Draw subtitle below image instead of overlay on image
        image_codes = item.get('image_codes', [])
        subtitle_y = y + height + 5  # Position subtitle below the image
        self._draw_image_subtitle(canvas, x, subtitle_y, width, spec, item, image_codes)
        
        # Draw overlay banner if applicable (Artist Series, Retouch, or Both)
        self._draw_overlay_banner(canvas, x, y, width, height, spec, item, image_codes)
        
        # STEP 8: Draw quantity badge for sheet products (keep in corner)
        sheet_qty = position.get('sheet_qty', item.get('quantity', 1))
        if spec['category'] == 'sheet_print' and sheet_qty > 1:
            self._draw_sheet_quantity_badge(canvas, x + width - 30, y + height - 25, sheet_qty)
        elif spec['category'] == 'large_print' and sheet_qty > 1:
            self._draw_quantity_badge_clean(canvas, x + width - 25, y + 5, sheet_qty)

    def _draw_composite_with_unified_scaling(self, canvas: Image.Image, position: Dict):
        """Draw composite using unified PPI scaling and proper proportions"""
        x, y = position['x'], position['y']
        width, height = position['width'], position['height']
        spec = position['spec']
        item = position['item']
        
        draw = ImageDraw.Draw(canvas)
        product_name = item.get('display_name', f"Trio {spec['container_w_in']:.0f}x{spec['container_h_in']:.0f}")
        
        logger.info(f"Drawing composite {product_name} at ({x}, {y}) size {width}×{height}px")
        
        try:
            # Get customer images for this trio
            customer_images = self._get_customer_images_for_item(item)
            
            if len(customer_images) < 3:
                logger.warning(f"Trio item has less than 3 images: {len(customer_images)}")
                # Pad with duplicates or placeholders as needed
                while len(customer_images) < 3:
                    if customer_images:
                        customer_images.append(customer_images[-1])
                    else:
                        customer_images.append(None)
            
            # Extract trio details
            frame_color = item.get('frame_color', 'Black').capitalize()
            matte_color = item.get('matte_color', 'White').capitalize()

            # Determine composite size from product code
            size_label = "10x20" if "1020" in item.get('product_code', '') else "5x10"

            template_name = trio_template_filename(size_label, frame_color, matte_color)
            logger.debug(
                f"Generating composite: {template_name}"
            )

            # Generate the composite using the correct size for file lookup
            composite_image = self.trio_generator.create_composite(
                customer_images=customer_images,
                frame_color=frame_color,
                matte_color=matte_color,
                size=size_label,
                fallback_to_5x10=True
            )
            
            if composite_image:
                # Scale composite to fit the calculated dimensions
                scaled_composite = composite_image.resize((width, height), Image.Resampling.LANCZOS)
                
                # Paste composite onto canvas
                canvas.paste(scaled_composite, (x, y))
                
                # Draw composite label
                self._draw_composite_label_unified(canvas, x, y + height + 5, width, product_name, item.get('quantity', 1))
                
                logger.info(f"✅ Successfully drew composite {product_name} at ({x}, {y})")
            else:
                logger.error(f"❌ Composite generation failed for {product_name}")
                # Draw VERY OBVIOUS placeholder with thick border for visibility
                draw.rectangle([x-5, y-5, x + width + 5, y + height + 5], outline=(255, 0, 0), width=5)
                draw.rectangle([x, y, x + width, y + height], fill=(255, 100, 100), outline=(200, 0, 0), width=3)
                
                # Add error text
                try:
                    font = ImageFont.load_default()
                    error_text = f"MISSING: {product_name}"
                    bbox = draw.textbbox((0, 0), error_text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_x = x + (width - text_width) // 2
                    text_y = y + height // 2 - 10
                    draw.text((text_x, text_y), error_text, fill=(255, 255, 255), font=font)
                    
                    # Add position info
                    pos_text = f"@({x},{y}) {width}x{height}"
                    draw.text((text_x, text_y + 15), pos_text, fill=(255, 255, 255), font=font)
                except:
                    pass
            
        except Exception as e:
            logger.error(f"❌ Exception drawing composite {product_name}: {e}")
            import traceback
            traceback.print_exc()
            
            # Draw obvious error placeholder
            draw.rectangle([x-2, y-2, x + width + 2, y + height + 2], outline=(255, 0, 0), width=3)
            draw.rectangle([x, y, x + width, y + height], fill=(255, 200, 200), outline=(200, 0, 0), width=2)
            
            # Add error text
            try:
                font = ImageFont.load_default()
                error_text = f"EXCEPTION: {product_name}"
                bbox = draw.textbbox((0, 0), error_text, font=font)
                text_width = bbox[2] - bbox[0]
                text_x = x + (width - text_width) // 2
                text_y = y + height // 2
                draw.text((text_x, text_y), error_text, fill=(255, 0, 0), font=font)
            except:
                pass

    def _draw_composite_label_unified(self, canvas: Image.Image, x: int, y: int, width: int,
                                     product_name: str, quantity: int):
        """Draw label for a composite using unified scaling"""
        try:
            draw = ImageDraw.Draw(canvas)
            
            # Try to load a font
            try:
                font = ImageFont.truetype("arial.ttf", 14)
            except:
                font = ImageFont.load_default()
            
            # Format label text
            label_text = f"{product_name}"
            if quantity > 1:
                label_text += f" (Qty: {quantity})"
            
            # Draw label centered below composite
            bbox = draw.textbbox((0, 0), label_text, font=font)
            text_width = bbox[2] - bbox[0]
            
            label_x = x + (width - text_width) // 2
            label_y = y
            
            # Draw text with subtle shadow
            draw.text((label_x + 1, label_y + 1), label_text, fill=(180, 180, 180), font=font)
            draw.text((label_x, label_y), label_text, fill=(60, 60, 60), font=font)
            
        except Exception as e:
            logger.error(f"Failed to draw composite label: {e}")

    def _draw_image_subtitle(self, canvas: Image.Image, x: int, y: int, width: int,
                            spec: Dict, item: Dict = None, image_codes: List[str] = None):
        """Draw simplified subtitle below image with finish, size, per-sheet quantity, and framing status"""
        try:
            draw = ImageDraw.Draw(canvas)
            
            # Try to load a font (slightly smaller than composite labels)
            try:
                font = ImageFont.truetype("arial.ttf", 12)
                bold_font = ImageFont.truetype("arialbd.ttf", 12)  # Bold font for finish types
            except:
                font = ImageFont.load_default()
                bold_font = font  # Fallback to same font
            
            # Build simplified subtitle text
            subtitle_parts = []
            
            # Extract size from display name and clean it up
            display_name = item.get('display_name', spec.get('display_name', 'Unknown'))
            sheet_type = spec.get('sheet_type', '')
            category = spec.get('category', '')
            
            # Determine if this product has finish options (excludes composites, 3.5x5 sheets, and wallets)
            has_finish = True
            if (category == 'trio_composite' or 
                'wallet' in display_name.lower() or 
                '3.5x5' in display_name or 
                'SHEET3x5' in sheet_type):
                has_finish = False
            
            # Get finish type and prepare color coding
            finish_type = None
            if has_finish and item:
                finish_type = item.get('finish', item.get('finish_type', 'Basic'))
            
            # Extract and format size
            if 'x' in display_name.lower():
                # Extract size with better regex to preserve zeros
                import re
                size_match = re.search(r'(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)', display_name, re.IGNORECASE)
                if size_match:
                    width_str = size_match.group(1)
                    height_str = size_match.group(2)
                    # Only remove .0 if it's actually .0, preserve other decimals
                    if width_str.endswith('.0'):
                        width_str = width_str[:-2]
                    if height_str.endswith('.0'):
                        height_str = height_str[:-2]
                    clean_size = f"{width_str}x{height_str}"
                else:
                    # Fallback to first part of display name
                    clean_size = display_name.split()[0] if display_name else "Unknown"
            else:
                # For wallet sheets, just say "Wallets"
                if 'wallet' in display_name.lower():
                    clean_size = "Wallets"
                else:
                    # For other products, use first meaningful part
                    clean_size = display_name.split()[0] if display_name else "Unknown"
            
            # Add per-sheet quantity for sheet products
            if category == 'sheet_print' or 'sheet' in sheet_type.lower():
                cells = spec.get('cells', 1)
                if 'wallet' in display_name.lower():
                    clean_size += f" - {cells}"  # "Wallets - 8"
                elif '3.5x5' in display_name or 'SHEET3x5' in sheet_type:
                    clean_size += f" - {cells}"  # "3.5x5 - 4"
                elif '5x7' in display_name and 'pair' in display_name.lower():
                    clean_size += f" - {cells}"  # "5x7 - 2"
            
            # Prepare text parts for uniform professional rendering
            text_parts = []
            standard_color = (50, 50, 50)  # Professional dark gray for all text
            
            # Add finish as first part with bold styling if applicable
            if has_finish and finish_type:
                text_parts.append({
                    'text': finish_type.upper(),
                    'font': bold_font,
                    'color': standard_color  # Same color as other text
                })
            
            # Add size as second part
            text_parts.append({
                'text': clean_size,
                'font': font,
                'color': standard_color
            })
            
            # Add framing status if item has a frame
            if item and item.get('has_frame'):
                text_parts.append({
                    'text': "Framed",
                    'font': font,
                    'color': standard_color
                })
            
            # Add sheet quantity for sheets (number of sheets ordered)
            if item and item.get('quantity', 1) > 1:
                quantity = item.get('quantity', 1)
                if category == 'sheet_print' or 'sheet' in sheet_type.lower():
                    text_parts.append({
                        'text': f"({quantity} sheets)",
                        'font': font,
                        'color': (100, 100, 100)  # Slightly lighter gray for quantity info
                    })
            
            # Calculate total text width for centering
            total_width = 0
            for i, part in enumerate(text_parts):
                bbox = draw.textbbox((0, 0), part['text'], font=part['font'])
                part['width'] = bbox[2] - bbox[0]
                total_width += part['width']
                if i < len(text_parts) - 1:  # Add space width except for last part
                    space_bbox = draw.textbbox((0, 0), " ", font=font)
                    total_width += space_bbox[2] - space_bbox[0]
            
            # Calculate starting position (centered below image)
            start_x = x + (width - total_width) // 2
            subtitle_y = y + 8  # Small gap below image
            
            # Draw each part with its own color
            current_x = start_x
            for i, part in enumerate(text_parts):
                # Draw shadow for readability
                draw.text((current_x + 1, subtitle_y + 1), part['text'], fill=(200, 200, 200), font=part['font'])
                # Draw main text with specified color
                draw.text((current_x, subtitle_y), part['text'], fill=part['color'], font=part['font'])
                
                # Move to next position
                current_x += part['width']
                if i < len(text_parts) - 1:  # Add space except after last part
                    space_bbox = draw.textbbox((0, 0), " ", font=font)
                    space_width = space_bbox[2] - space_bbox[0]
                    current_x += space_width
            
        except Exception as e:
            logger.error(f"Failed to draw image subtitle: {e}")

    def _render_large_print(self, canvas: Image.Image, x: int, y: int, width: int, height: int,
                           image_codes: List[str], spec: Dict, item: Dict = None):
        """STEP 22: Render single large print using master image - FULL CONTAINER FILL"""
        if not image_codes or not image_codes[0]:
            self._draw_subtle_placeholder(canvas, x, y, width, height, 1)
            return
            
        image_code = image_codes[0]
        if image_code not in self.master_images:
            self._draw_subtle_placeholder(canvas, x, y, width, height, 1)
            return
            
        master_img = self.master_images[image_code]
        
        # Check if this item has a frame
        if item and (item.get('has_frame') or item.get('framed')):
            frame_spec = item.get('frame_spec') or FrameSpec("5x7", item.get('frame_color', 'Black').capitalize())
            
            # Calculate the inner image size (original container minus frame thickness)
            inner_width = width - frame_spec.left_thickness - frame_spec.right_thickness
            inner_height = height - frame_spec.top_thickness - frame_spec.bottom_thickness
            
            # Scale image to fill the inner area (this keeps the customer image the same size as unframed)
            img_filled = self._scale_image_to_fill_container(master_img, inner_width, inner_height)
            
            # Apply frame around the image
            framed_image = self.frame_engine.apply_frame_to_image(img_filled, frame_spec)
            
            if framed_image:
                # The framed image should now fit exactly in the expanded container
                canvas.paste(framed_image, (x, y))
                logger.debug(f"Applied {frame_spec.frame_style} {frame_spec.size} frame to large print. "
                           f"Inner: {inner_width}x{inner_height}, Framed: {framed_image.size}")
            else:
                # Fallback to unframed if frame application failed
                img_filled = self._scale_image_to_fill_container(master_img, inner_width, inner_height)
                # Center the unframed image in the expanded container
                offset_x = frame_spec.left_thickness
                offset_y = frame_spec.top_thickness
                canvas.paste(img_filled, (x + offset_x, y + offset_y))
                logger.warning(f"Frame application failed, using unframed image")
        else:
            # FULL CONTAINER FILL: Scale image to fill entire container with center crop
            img_filled = self._scale_image_to_fill_container(master_img, width, height)
            
            # Paste at exact position - no margins or borders
            canvas.paste(img_filled, (x, y))

    def _scale_image_to_fill_container(self, image: Image.Image, container_width: int, container_height: int) -> Image.Image:
        """Scale image to completely fill container using center crop (eliminates white space)"""
        img_width, img_height = image.size
        container_aspect = container_width / container_height
        img_aspect = img_width / img_height
        
        if img_aspect > container_aspect:
            # Image is wider - scale by height and crop width
            scale = container_height / img_height
            new_width = int(img_width * scale)
            new_height = container_height
            
            # Resize image
            resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Center crop to container width
            crop_x = (new_width - container_width) // 2
            cropped = resized.crop((crop_x, 0, crop_x + container_width, new_height))
        else:
            # Image is taller - scale by width and crop height
            scale = container_width / img_width
            new_width = container_width
            new_height = int(img_height * scale)
            
            # Resize image
            resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Center crop to container height
            crop_y = (new_height - container_height) // 2
            cropped = resized.crop((0, crop_y, new_width, crop_y + container_height))
        
        return cropped

    def _render_sheet_print(self, canvas: Image.Image, x: int, y: int, width: int, height: int,
                           image_codes: List[str], spec: Dict):
        """STEP 23-25: Render sheet with internal grid using master images - FULL CONTAINER FILL"""
        rows = spec.get('grid_rows', 1)
        cols = spec.get('grid_cols', 1)
        cells = spec.get('cells', 1)
        
        # Calculate cell dimensions with minimal gaps (no margins, tight fit)
        gap = 1  # Minimal gap for visual separation
        
        cell_width = (width - (cols - 1) * gap) // cols
        cell_height = (height - (rows - 1) * gap) // rows
        
        # Get the master image for this sheet (usually same image repeated)
        image_code = image_codes[0] if image_codes else None
        master_img = self.master_images.get(image_code) if image_code else None
        
        # Draw grid of cells
        for cell_idx in range(cells):
            row = cell_idx // cols
            col = cell_idx % cols
            
            cell_x = x + col * (cell_width + gap)
            cell_y = y + row * (cell_height + gap)
            
            # Draw image in cell - FULL FILL (no borders or margins)
            if master_img:
                # Scale image to completely fill cell using center crop
                cell_img_filled = self._scale_image_to_fill_container(master_img, cell_width, cell_height)
                canvas.paste(cell_img_filled, (cell_x, cell_y))
            else:
                # Draw placeholder that fills entire cell
                self._draw_subtle_placeholder(canvas, cell_x, cell_y, cell_width, cell_height, 1)

    def _render_5x7_pair_sheet(self, canvas: Image.Image, x: int, y: int, width: int, height: int,
                              image_codes: List[str], spec: Dict):
        """Render 5x7 pair sheet - 10x7 LANDSCAPE container with 2 PORTRAIT 5x7 images side by side - FULL FILL"""
        gap = 2  # Minimal gap for visual separation
        cols = 2
        rows = 1
        
        # Calculate cell dimensions for 2 portrait images side by side in landscape container (no margins)
        available_width = width - (cols - 1) * gap
        available_height = height
        
        # Target aspect for individual 5x7 portrait image
        target_aspect = 5.0 / 7.0  # Portrait: narrower than tall
        
        # Calculate cell size to fit 2 portrait 5x7s in landscape container
        # Try fitting by width first (divide available width by 2)
        cell_width_by_width = available_width // cols
        cell_height_by_width = int(cell_width_by_width / target_aspect)
        
        # Try fitting by height
        cell_height_by_height = available_height
        cell_width_by_height = int(cell_height_by_height * target_aspect)
        
        # Use the constraint that gives smaller cells (ensures both fit)
        if cell_height_by_width <= available_height:
            cell_width = cell_width_by_width
            cell_height = cell_height_by_width
        else:
            cell_width = cell_width_by_height
            cell_height = cell_height_by_height
        
        logger.debug(f"5x7 landscape container {width}x{height} -> cells {cell_width}x{cell_height}")
        
        # Get master images (2 codes if available, else duplicate first)
        master_images = []
        for i in range(2):
            if i < len(image_codes) and image_codes[i] in self.master_images:
                master_images.append(self.master_images[image_codes[i]])
            elif image_codes and image_codes[0] in self.master_images:
                master_images.append(self.master_images[image_codes[0]])  # Duplicate first
            else:
                master_images.append(None)
        
        # Draw 2 portrait cells side by side in landscape container (full fill)
        start_x = x + (available_width - 2 * cell_width - gap) // 2  # Center horizontally
        start_y = y + (available_height - cell_height) // 2  # Center vertically
        
        for col in range(2):
            cell_x = start_x + col * (cell_width + gap)
            cell_y = start_y
            
            self._draw_sheet_cell(canvas, cell_x, cell_y, cell_width, cell_height, 
                                master_images[col], target_aspect)

    def _render_3x5_sheet(self, canvas: Image.Image, x: int, y: int, width: int, height: int,
                         image_codes: List[str], spec: Dict):
        """Render 3.5x5 sheet - 7x10 PORTRAIT container with 2×2 grid of portrait 3.5x5 images - FULL FILL"""
        gap = 2  # Minimal gap for visual separation
        cols = 2
        rows = 2
        
        # Calculate cell dimensions for 2x2 grid in 7x10 portrait container (no margins)
        available_width = width - (cols - 1) * gap
        available_height = height - (rows - 1) * gap
        
        # Target aspect for individual 3.5x5 portrait image
        target_aspect = 3.5 / 5.0  # Portrait: narrower than tall
        
        # Calculate cell size to fit 2x2 grid optimally
        cell_width_by_width = available_width // cols
        cell_height_by_width = int(cell_width_by_width / target_aspect)
        
        cell_height_by_height = available_height // rows
        cell_width_by_height = int(cell_height_by_height * target_aspect)
        
        # Use the constraint that fits best
        if cell_height_by_width * rows <= available_height:
            cell_width = cell_width_by_width
            cell_height = cell_height_by_width
        else:
            cell_width = cell_width_by_height
            cell_height = cell_height_by_height
        
        logger.debug(f"3.5x5 portrait container {width}x{height} -> cells {cell_width}x{cell_height}")
        
        # Get master image (same image duplicated across all 4 cells)
        master_img = None
        if image_codes and image_codes[0] in self.master_images:
            master_img = self.master_images[image_codes[0]]
        
        # Center the 2×2 grid in the container (full fill)
        grid_width = 2 * cell_width + gap
        grid_height = 2 * cell_height + gap
        start_x = x + (available_width - grid_width) // 2
        start_y = y + (available_height - grid_height) // 2
        
        # Draw 2×2 grid
        for row in range(2):
            for col in range(2):
                cell_x = start_x + col * (cell_width + gap)
                cell_y = start_y + row * (cell_height + gap)
                
                self._draw_sheet_cell(canvas, cell_x, cell_y, cell_width, cell_height,
                                    master_img, target_aspect)

    def _render_wallet_sheet(self, canvas: Image.Image, x: int, y: int, width: int, height: int,
                            image_codes: List[str], spec: Dict):
        """Render wallet sheet - 10x7 LANDSCAPE container with 2×4 grid of portrait 2.5x3.5 wallets - FULL FILL"""
        gap = 1  # Minimal gap between wallets
        cols = 4
        rows = 2
        
        # Calculate cell dimensions for 2×4 grid in 10×7 landscape container (no margins)
        available_width = width - (cols - 1) * gap
        available_height = height - (rows - 1) * gap
        
        # Target aspect for individual wallet (2.5×3.5 portrait)
        target_aspect = 2.5 / 3.5  # Portrait: narrower than tall
        
        # Calculate cell size to fit 2×4 grid of wallets optimally
        cell_width_by_width = available_width // cols
        cell_height_by_width = int(cell_width_by_width / target_aspect)
        
        cell_height_by_height = available_height // rows
        cell_width_by_height = int(cell_height_by_height * target_aspect)
        
        # Use the constraint that fits best (ensures all 8 wallets fit)
        if cell_height_by_width * rows <= available_height:
            cell_width = cell_width_by_width
            cell_height = cell_height_by_width
        else:
            cell_width = cell_width_by_height
            cell_height = cell_height_by_height
        
        logger.debug(f"Wallet landscape container {width}x{height} -> cells {cell_width}x{cell_height}")
        
        # Get master image (same image duplicated across all 8 cells)
        master_img = None
        if image_codes and image_codes[0] in self.master_images:
            master_img = self.master_images[image_codes[0]]
        
        # Center the 2×4 grid in the landscape container (full fill)
        grid_width = 4 * cell_width + 3 * gap
        grid_height = 2 * cell_height + gap
        start_x = x + (available_width - grid_width) // 2
        start_y = y + (available_height - grid_height) // 2
        
        # Draw 2×4 grid (8 wallets)
        for row in range(2):
            for col in range(4):
                cell_x = start_x + col * (cell_width + gap)
                cell_y = start_y + row * (cell_height + gap)
                
                self._draw_sheet_cell(canvas, cell_x, cell_y, cell_width, cell_height,
                                    master_img, target_aspect)

    def _draw_sheet_cell(self, canvas: Image.Image, x: int, y: int, width: int, height: int,
                        master_img: Optional[Image.Image], target_aspect: float):
        """Draw a single cell within a sheet - FULL CONTAINER FILL (no borders/margins)"""
        if master_img:
            # Scale image to completely fill cell using center crop (no white space)
            cell_img_filled = self._scale_image_to_fill_container(master_img, width, height)
            canvas.paste(cell_img_filled, (x, y))
        else:
            # Draw placeholder that fills entire cell
            self._draw_subtle_placeholder(canvas, x, y, width, height, 1)

    def _draw_sheet_quantity_badge(self, canvas: Image.Image, x: int, y: int, sheet_qty: int):
        """STEP 8: Draw quantity badge for sheet products"""
        if sheet_qty <= 1:
            return
            
        draw = ImageDraw.Draw(canvas)
        
        # Semi-transparent background
        badge_size = 24
        draw.ellipse([x, y, x + badge_size, y + badge_size], 
                    fill=(50, 50, 200, 200), outline=(30, 30, 150))
        
        try:
            font = ImageFont.load_default()
            text = f"×{sheet_qty}"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = x + (badge_size - text_width) // 2
            text_y = y + (badge_size - text_height) // 2
            draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)
        except:
            pass

    # NOTE: _draw_size_label_corrected method removed - replaced with subtitle functionality
    # Labels are now drawn below images using _draw_image_subtitle method
    
    def generate_size_based_preview_with_composites(self, items: List[Dict], output_filename: str,
                                                   frame_requirements: Dict[str, int] = None,
                                                   frame_style_preferences: Dict[str, str] = None,
                                                   debug: bool = False) -> bool:
        """
        Generate preview with products arranged by size and trio composites on the right
        
        Args:
            items: List of order items with product info and quantities
            output_filename: Where to save the preview
            frame_requirements: Optional dictionary mapping frame size to quantity needed
            frame_style_preferences: Optional dictionary mapping frame size to frame style preference
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Generating size-based preview with composites for {len(items)} product types")
            
            # Process frame requirements if provided
            processed_items = items
            if frame_requirements:
                logger.info(f"Applying frame requirements: {frame_requirements}")
                processed_items = apply_frames_simple(items, frame_requirements)
                logger.info(
                    f"Processed items: {len(items)} -> {len(processed_items)} (after frame application)"
                )
            
            # STEP 5: Process all images to canonical portrait orientation and master crops
            self._process_images(processed_items)
            
            # Create canvas with beige background
            canvas = Image.new('RGB', (self.CANVAS_W, self.CANVAS_H), self.beige_color)
            
            # Separate trio and non-trio products
            trio_items = []
            regular_items = []
            
            for item in processed_items:
                product_config = self._find_product_config(item.get('product_slug', ''))
                
                # Check if it's a trio product (either from config or item properties)
                is_trio = False
                if product_config and is_trio_product(product_config):
                    is_trio = True
                elif not product_config and is_trio_product(item):  # Check item directly if no config found
                    is_trio = True
                
                if is_trio:
                    trio_items.append((item, product_config))
                else:
                    regular_items.append(item)
            
            # Sort regular items by physical size (area) - largest first
            sorted_regular_items = self._sort_items_by_size_corrected(regular_items)
            
            # STEP 17-20: Calculate PPI and layout with corrected scaling system (including composites)
            all_items = sorted_regular_items + [item for item, _ in trio_items]
            layout = self._calculate_corrected_layout_with_composites(sorted_regular_items, trio_items)
            self._enforce_safe_zone(layout)
            
            # Draw title
            self._draw_title(canvas, "Portrait Order Preview")
            
            # Draw all products (regular and composites) using unified rendering
            for position in layout:
                self._draw_product_corrected(canvas, position)
            
            # Add minimal order info
            self._draw_minimal_summary(canvas, sorted_regular_items + [item for item, _ in trio_items])

            if debug:
                self._draw_debug_regions(canvas)

            # Save preview
            canvas.save(output_filename, 'PNG', quality=95)
            logger.info(f"✅ Enhanced preview with composites saved: {output_filename}")
            
            return True
            
        except Exception:
            logger.exception("Error generating enhanced preview with composites")
            return False

    def _draw_debug_regions(self, canvas: Image.Image):
        """Draw debug visualization of layout regions"""
        draw = ImageDraw.Draw(canvas)

        pad = self.safe_pad_px
        draw.rectangle([pad, pad, self.CANVAS_W - pad, self.CANVAS_H - pad], outline="red", width=2)
        
        # Draw left region bounds (green)
        draw.rectangle([self.LEFT_X0, self.LEFT_Y0, self.LEFT_X1, self.LEFT_Y1], 
                      outline=(0, 255, 0), width=2)
        
        # Draw right region bounds (blue)
        draw.rectangle([self.RIGHT_X0, self.RIGHT_Y0, self.RIGHT_X1, self.RIGHT_Y1], 
                      outline=(0, 0, 255), width=2)
        
        # Add region labels
        try:
            font = ImageFont.load_default()
            draw.text((self.LEFT_X0 + 10, self.LEFT_Y0 + 10), "LEFT REGION", fill=(0, 255, 0), font=font)
            draw.text((self.RIGHT_X0 + 10, self.RIGHT_Y0 + 10), "RIGHT REGION (COMPOSITES)", fill=(0, 0, 255), font=font)
            
            # Show region dimensions
            left_info = f"Left: {self.LEFT_REGION_W}×{self.DRAW_H}px"
            right_info = f"Right: {self.RIGHT_REGION_W}×{self.DRAW_H}px"
            draw.text((self.LEFT_X0 + 10, self.LEFT_Y0 + 30), left_info, fill=(0, 255, 0), font=font)
            draw.text((self.RIGHT_X0 + 10, self.RIGHT_Y0 + 30), right_info, fill=(0, 0, 255), font=font)
        except:
            pass

    def _find_product_config(self, product_slug: str) -> Optional[Dict]:
        """Find product configuration by slug"""
        products = self.products_config.get('products', [])
        for product in products:
            if product.get('slug') == product_slug:
                return product
        return None

    def _draw_trio_composites_section(self, canvas: Image.Image, 
                                    trio_items: List[Tuple[Dict, Dict]], 
                                    section_width: int):
        """Draw trio composites in the right section of the preview"""
        if not trio_items:
            return
            
        # Calculate composite section position
        section_x = self.RIGHT_X0 + self.INTER_REGION_GAP
        section_y = self.MARGIN_TOP + 10  # Closer to top for more space
        section_height = self.DRAW_H - 20  # Use more of the available height
        
        # Sort trio items by size (10x20 first, then 5x10)
        def get_trio_size(trio_item):
            item, product_config = trio_item
            if product_config:
                return product_config.get('height_in', 10) * product_config.get('width_in', 5)
            else:
                # Extract size from product code if no config
                product_code = item.get('product_code', '')
                return 200 if "1020" in product_code else 50  # 10x20 = 200, 5x10 = 50
        
        sorted_trios = sorted(trio_items, key=get_trio_size, reverse=True)
        
        current_y = section_y + 10  # Reduced top margin for composites
        
        for i, (item, product_config) in enumerate(sorted_trios):
            try:
                # Get customer images for this trio
                customer_images = self._get_customer_images_for_item(item)
                
                if len(customer_images) < 3:
                    logger.warning(f"Trio item has less than 3 images: {len(customer_images)}")
                    # Pad with duplicates or placeholders as needed
                    while len(customer_images) < 3:
                        if customer_images:
                            customer_images.append(customer_images[-1])
                        else:
                            customer_images.append(None)
                
                # Extract trio details (handle case where product_config is None)
                if product_config:
                    # Use product config if available
                    frame_color = item.get('frame_color', product_config.get('frame_style_default', 'Black'))
                    matte_color = item.get('matte_color', 'White')
                    size = f"{product_config.get('width_in', 5):.0f}x{product_config.get('height_in', 10):.0f}"
                    product_name = product_config.get('name', 'Trio Portrait')
                else:
                    # Extract from item properties if no product config
                    frame_color = item.get('frame_color', 'Black')
                    matte_color = item.get('matte_color', 'White')  
                    size = "10x20" if "1020" in item.get('product_code', '') else "5x10"
                    product_name = item.get('display_name', 'Trio Portrait')
                
                # Generate the composite using direct parameters
                composite_image = self.trio_generator.create_composite(
                    customer_images=customer_images,
                    frame_color=frame_color,
                    matte_color=matte_color,
                    size=size
                )
                
                if composite_image:
                    # Scale composite for preview
                    scaled_composite = self.trio_generator.scale_composite_for_preview(
                        composite_image, 
                        section_width - 40,  # Leave margins
                        section_height // len(sorted_trios),  # Divide space evenly
                        size
                    )
                    
                    # Right-justify the composite
                    composite_x = section_x + section_width - scaled_composite.width - 20
                    composite_y = current_y
                    
                    # Paste composite onto canvas
                    canvas.paste(scaled_composite, (composite_x, composite_y))
                    
                    # Add product label
                    self._draw_composite_label(
                        canvas, 
                        composite_x, 
                        composite_y + scaled_composite.height + 5,
                        scaled_composite.width,
                        product_name,
                        item.get('quantity', 1)
                    )
                    
                    # Update position for next composite
                    current_y += scaled_composite.height + 40
                    
                    logger.info(f"Drew trio composite: {product_name}")
                
            except Exception as e:
                product_name = product_config.get('name', 'Unknown') if product_config else item.get('display_name', 'Unknown')
                logger.error(f"Failed to draw trio composite {product_name}: {e}")
                continue

    def _get_customer_images_for_item(self, item: Dict) -> List[Path]:
        """Get customer images for trio composites - properly oriented and saved as temp files"""
        import tempfile
        import os
        
        customer_image_paths = []
        codes = item.get('codes', item.get('image_codes', []))
        
        for code in codes:
            if code in self.master_images:
                # Use master image (already portrait oriented and cropped)
                master_img = self.master_images[code]
                # NO rotation needed - master images are already upright portrait
                
                # Save master image to temporary file for composite
                temp_dir = Path("tmp")
                temp_dir.mkdir(exist_ok=True)
                temp_path = temp_dir / f"composite_{code}.jpg"
                master_img.save(temp_path, 'JPEG', quality=95)
                customer_image_paths.append(temp_path)
                
                logger.debug(f"Using master image {code} for composite (upright portrait): {master_img.size}")
            elif code in self.images_found:
                # Fallback: load and process image directly
                try:
                    image_path = self.images_found[code][0]
                    with Image.open(image_path) as img:
                        # Apply same orientation fixes as master images
                        img = ImageOps.exif_transpose(img)
                        if img.width > img.height:
                            img = img.rotate(90, expand=True)
                        # NO additional rotation for composite - keep upright portrait
                        
                        # Save processed image to temporary file
                        temp_dir = Path("tmp")
                        temp_dir.mkdir(exist_ok=True)
                        temp_path = temp_dir / f"composite_fallback_{code}.jpg"
                        img.save(temp_path, 'JPEG', quality=95)
                        customer_image_paths.append(temp_path)
                        
                        logger.debug(f"Processed and saved image {code} for composite (upright portrait)")
                except Exception as e:
                    logger.error(f"Failed to load image {code}: {e}")
                    customer_image_paths.append(None)
            else:
                customer_image_paths.append(None)
                
        return customer_image_paths

    def _draw_composite_label(self, canvas: Image.Image, x: int, y: int, width: int, 
                            product_name: str, quantity: int):
        """Draw label for a composite"""
        try:
            draw = ImageDraw.Draw(canvas)
            
            # Try to load a font
            try:
                font = ImageFont.truetype("arial.ttf", 14)
            except:
                font = ImageFont.load_default()
            
            # Format label text
            label_text = f"{product_name}"
            if quantity > 1:
                label_text += f" (Qty: {quantity})"
            
            # Draw label centered below composite
            bbox = draw.textbbox((0, 0), label_text, font=font)
            text_width = bbox[2] - bbox[0]
            
            label_x = x + (width - text_width) // 2
            label_y = y
            
            # Draw text with subtle shadow
            draw.text((label_x + 1, label_y + 1), label_text, fill=(180, 180, 180), font=font)
            draw.text((label_x, label_y), label_text, fill=(60, 60, 60), font=font)
            
        except Exception as e:
            logger.error(f"Failed to draw composite label: {e}")

    def _calculate_layout_with_reduced_width(self, items: List[Dict], available_width: int) -> List[Dict]:
        """Calculate layout for regular products with reduced width (space reserved for composites)"""
        layout = []
        
        if not items:
            return layout
        
        # Use reduced width instead of full canvas width
        available_height = self.DRAW_H - 80  # Reduced space for title for more product area
        
        # Group items by size category (same as before)
        size_groups = {
            'large': [],
            'medium': [], 
            'medium_sheet': [],  # 5x7 landscape sheets
            'small': [],
            'small_sheet': [],   # 3.5x5 portrait sheets
            'wallet': [],
            'wallet_sheet': []   # Wallet 2x2 sheets
        }
        
        for i, item in enumerate(items):
            category = item.get('size_category', 'large')
            width_in, height_in = self._get_product_dimensions(item)
            size_groups[category].append({
                'item': item,
                'index': i,
                'width_in': width_in,
                'height_in': height_in
            })
        
        # Filter out empty groups
        active_groups = {k: v for k, v in size_groups.items() if v}
        
        logger.info(f"Size groups: {[(k, len(v)) for k, v in active_groups.items()]}")
        
        # Calculate space allocation for each group (same logic but with reduced width)
        group_space = {}
        
        for group_name, group_items in active_groups.items():
            # Allocate height based on group importance and item count
            if group_name == 'large':
                height_ratio = 0.4  # Large items get 40% of height
            elif group_name == 'medium':  
                height_ratio = 0.25  # Medium items get 25% of height
            elif group_name == 'medium_sheet':  
                height_ratio = 0.20  # 5x7 sheets get 20% of height
            elif group_name == 'small':
                height_ratio = 0.15   # Small items get 15% of height
            elif group_name == 'small_sheet':
                height_ratio = 0.15  # 3.5x5 sheets get 15% of height
            elif group_name == 'wallet_sheet':
                height_ratio = 0.15  # Wallet sheets get 15% of height
            else:  # wallet
                height_ratio = 0.15  # Individual wallets get 15% of height
            
            group_space[group_name] = {
                'height': available_height * height_ratio,
                'items': group_items
            }
        
        # Position each group independently - start higher and tighter spacing
        current_y = 50  # Start higher up for more space
        gap_between_groups = 15  # Reduced gap for tighter layout
        
        for group_name in ['large', 'medium_sheet', 'small_sheet', 'wallet_sheet']:
            if group_name not in active_groups:
                continue
                
            group_items = active_groups[group_name]
            group_height = group_space[group_name]['height']
            
            # Calculate optimal layout for this group with reduced width
            group_layout = self._layout_size_group_with_width(
                group_items, available_width, group_height, current_y
            )
            layout.extend(group_layout)
            
            # Move to next group position
            if group_layout:
                max_bottom = max(item['y'] + item['height'] for item in group_layout)
                current_y = max_bottom + gap_between_groups
        
        return layout

    def _layout_size_group_with_width(self, group_items: List[Dict], available_width: float, 
                          available_height: float, start_y: float) -> List[Dict]:
        """Layout a size group with specified width instead of full canvas width"""
        group_layout = []
        
        if not group_items:
            return group_layout
        
        # Calculate optimal scale and columns for this group
        max_width_in = max(item['width_in'] for item in group_items)
        max_height_in = max(item['height_in'] for item in group_items)
        
        # Try different column counts to find optimal layout
        best_layout = None
        best_scale = 0
        
        for cols in range(1, min(len(group_items) + 1, 5)):  # Try 1-4 columns
            rows = (len(group_items) + cols - 1) // cols
            
            # Calculate scale that fits all items
            h_gap = 20
            v_gap = 20
            
            max_item_width = (available_width - (cols + 1) * h_gap) / cols
            max_item_height = (available_height - (rows + 1) * v_gap) / rows
            
            scale_x = max_item_width / max_width_in
            scale_y = max_item_height / max_height_in
            scale = min(scale_x, scale_y, self.scale_factor)  # Don't exceed our target scale
            
            if scale > best_scale:
                best_scale = scale
                best_layout = (cols, rows, scale)
        
        if best_layout is None:
            logger.warning("Could not find suitable layout for group")
            return group_layout
        
        cols, rows, scale = best_layout
        
        # Position items using the best layout with strong left justification
        h_gap = 30  # Use consistent gap size for better layout
        max_item_height = max_height_in * scale
        
        start_x = self.MARGIN_LEFT  # Start directly at margin for true left justification
        v_gap = max(15, (available_height - max_item_height) / 3)  # Reduced vertical gap for tighter layout
        
        # Position items with proper spacing for different sizes
        current_x = start_x
        
        for i, item_data in enumerate(group_items):
            row = i // cols
            col = i % cols
            
            item = item_data['item']
            width_in = item_data['width_in']
            height_in = item_data['height_in']
            
            # Calculate size
            item_width = width_in * scale
            item_height = height_in * scale
            
            # Reset x position for new row
            if col == 0 and i > 0:
                current_x = start_x
            
            # Calculate position
            x = current_x
            y = start_y + v_gap + row * (max_item_height + v_gap)
            
            # Update x for next item
            current_x += item_width + h_gap
            
            group_layout.append({
                'x': int(x),
                'y': int(y),
                'width': int(item_width),
                'height': int(item_height),
                'actual_width_in': width_in,
                'actual_height_in': height_in,
                'quantity': 1,
                'original_index': item_data['index']
            })
        
        return group_layout
    
    def _sort_items_by_size(self, items: List[Dict]) -> List[Dict]:
        """Sort items by physical area (largest first)"""
        def get_area(item):
            width, height = self._get_product_dimensions(item)
            return width * height
        
        return sorted(items, key=get_area, reverse=True)
    
    def _get_product_dimensions(self, item: Dict) -> Tuple[float, float]:
        """Get product dimensions in inches with better matching"""
        product_code = item.get('product_code', '')
        product_slug = item.get('product_slug', '')
        
        logger.debug(f"Looking for product: code='{product_code}', slug='{product_slug}'")
        
        # First try exact code match
        for product in self.products_config.get('products', []):
            if product.get('code') == product_code:
                width = product.get('width_in', 5)
                height = product.get('height_in', 7)
                logger.debug(f"Found by code '{product_code}': {width}x{height} - {product.get('name')}")
                return width, height
        
        # Then try slug match
        for product in self.products_config.get('products', []):
            if product.get('slug') == product_slug:
                width = product.get('width_in', 5)
                height = product.get('height_in', 7)
                logger.debug(f"Found by slug '{product_slug}': {width}x{height} - {product.get('name')}")
                return width, height
        
        # Fallback based on common codes
        size_map = {
            '200': (2.5, 3.5),    # Wallets
            '350': (3.5, 5.0),    # 3.5x5
            '570': (5.0, 7.0),    # 5x7
            '810': (8.0, 10.0),   # 8x10 - SMALLEST large image
            '1013': (10.0, 13.0), # 10x13
            '1620': (16.0, 20.0), # 16x20
            '2024': (20.0, 24.0), # 20x24 - LARGEST
            '510.3': (5.0, 10.0), # 5x10 trio
            '1020.5': (10.0, 20.0), # 10x20 trio
            # Sheet-based products - ALL SAME SIZE AS 8x10 since printed on 8x10 paper
            '200_sheet': (8.0, 10.0),  # Wallet sheet on 8x10 PORTRAIT paper
            '350_sheet': (8.0, 10.0),  # 3.5x5 sheet on 8x10 PORTRAIT paper  
            '570_sheet': (8.0, 10.0),  # 5x7 sheet on 8x10 PORTRAIT paper
        }
        
        if product_code in size_map:
            width, height = size_map[product_code]
            logger.debug(f"Found by size map '{product_code}': {width}x{height}")
            return width, height
        
        logger.warning(f"No size found for code='{product_code}', slug='{product_slug}', using default")
        return 5.0, 7.0  # Default
    
    def _calculate_dynamic_layout(self, items: List[Dict]) -> List[Dict]:
        """Calculate layout with independent rows for each size category"""
        layout = []
        
        if not items:
            return layout
        
        # Available space with margins - use more of the canvas
        available_width = self.CANVAS_W - 2 * self.MARGIN_LEFT
        available_height = self.CANVAS_H - 80  # Reduced title space for more product area
        
        # Group items by size category
        size_groups = {
            'large': [],
            'medium': [], 
            'medium_sheet': [],  # 5x7 landscape sheets
            'small': [],
            'small_sheet': [],   # 3.5x5 portrait sheets
            'wallet': [],
            'wallet_sheet': []   # Wallet 2x2 sheets
        }
        
        for i, item in enumerate(items):
            category = item.get('size_category', 'large')
            width_in, height_in = self._get_product_dimensions(item)
            size_groups[category].append({
                'item': item,
                'index': i,
                'width_in': width_in,
                'height_in': height_in
            })
        
        # Filter out empty groups
        active_groups = {k: v for k, v in size_groups.items() if v}
        
        logger.info(f"Size groups: {[(k, len(v)) for k, v in active_groups.items()]}")
        
        # Calculate space allocation for each group
        total_items = len(items)
        group_space = {}
        
        for group_name, group_items in active_groups.items():
            # Allocate height based on group importance and item count
            if group_name == 'large':
                height_ratio = 0.4  # Large items get 40% of height
            elif group_name == 'medium':  
                height_ratio = 0.25  # Medium items get 25% of height
            elif group_name == 'medium_sheet':  
                height_ratio = 0.20  # 5x7 sheets get 20% of height
            elif group_name == 'small':
                height_ratio = 0.15   # Small items get 15% of height
            elif group_name == 'small_sheet':
                height_ratio = 0.15  # 3.5x5 sheets get 15% of height
            elif group_name == 'wallet_sheet':
                height_ratio = 0.15  # Wallet sheets get 15% of height
            else:  # wallet
                height_ratio = 0.15  # Individual wallets get 15% of height
            
            group_space[group_name] = {
                'height': available_height * height_ratio,
                'items': group_items
            }
        
        # Position each group independently - start higher and tighter spacing
        current_y = 50  # Start higher up for more space
        gap_between_groups = 15  # Reduced gap for tighter layout
        
        for group_name in ['large', 'medium_sheet', 'small_sheet', 'wallet_sheet']:
            if group_name not in active_groups:
                continue
                
            group_items = active_groups[group_name]
            group_height = group_space[group_name]['height']
            
            # Calculate optimal layout for this group
            group_layout = self._layout_size_group(group_items, available_width, group_height, current_y)
            layout.extend(group_layout)
            
            # Move to next group position
            if group_layout:
                max_bottom = max(item['y'] + item['height'] for item in group_layout)
                current_y = max_bottom + gap_between_groups
        
        return layout
    
    def _layout_size_group(self, group_items: List[Dict], available_width: float, 
                          available_height: float, start_y: float) -> List[Dict]:
        """Layout a single size group with equal spacing"""
        if not group_items:
            return []
        
        group_layout = []
        num_items = len(group_items)
        
        # Try different column configurations for this group
        best_layout = None
        best_scale = 0
        
        max_cols = min(8, num_items)
        for cols in range(1, max_cols + 1):
            rows = (num_items + cols - 1) // cols
            
            # Calculate space available per item
            item_width_space = available_width / cols
            item_height_space = available_height / rows
            
            # Find the largest item in this group to determine scale
            max_width = max(item['width_in'] for item in group_items)
            max_height = max(item['height_in'] for item in group_items)
            
            # Calculate scale that fits the largest item - use more space
            width_scale = (item_width_space * 0.95) / max_width  # Use 95% instead of 90%
            height_scale = (item_height_space * 0.95) / max_height  # Use 95% instead of 90%
            scale = min(width_scale, height_scale)
            
            if scale > best_scale:
                best_scale = scale
                best_layout = (cols, rows, scale)
        
        if not best_layout:
            return []
        
        cols, rows, scale = best_layout
        
        logger.info(f"Group layout: {cols} cols × {rows} rows, scale: {scale:.1f}")
        
        # Calculate actual total width of all items
        actual_items_width = sum(item['width_in'] * scale for item in group_items)
        min_gap = 30  # Reduced minimum gap for tighter layout
        
        # Left justify ALL groups - start at left margin (ensure strong left justification)
        h_gap = min_gap
        start_x = self.MARGIN_LEFT  # Always start at margin for true left justification
        
        # For height, use the maximum height in each row
        max_item_height = max(item['height_in'] for item in group_items) * scale
        v_gap = max(20, (available_height - max_item_height) / 3)  # Minimum 20px vertical gap
        
        # Position items with proper spacing for different sizes
        current_x = start_x
        
        for i, item_data in enumerate(group_items):
            row = i // cols
            col = i % cols
            
            item = item_data['item']
            width_in = item_data['width_in']
            height_in = item_data['height_in']
            
            # Calculate size
            item_width = width_in * scale
            item_height = height_in * scale
            
            # Reset x position for new row
            if col == 0 and i > 0:
                current_x = start_x
            
            # Calculate position
            x = current_x
            y = start_y + v_gap + row * (max_item_height + v_gap)
            
            # Update x for next item
            current_x += item_width + h_gap
            
            group_layout.append({
                'x': int(x),
                'y': int(y),
                'width': int(item_width),
                'height': int(item_height),
                'actual_width_in': width_in,
                'actual_height_in': height_in,
                'quantity': 1,
                'original_index': item_data['index']
            })
        
        return group_layout
    
    def _draw_product_clean(self, canvas: Image.Image, item: Dict, position: Dict):
        """Draw a product cleanly without debug info"""
        x, y = position['x'], position['y']
        width, height = position['width'], position['height']
        quantity = position.get('quantity', item.get('quantity', 1))
        
        # Get product info
        product_code = item.get('product_code', '')
        image_codes = item.get('image_codes', [])
        product_slug = item.get('product_slug', '')
        sheet_type = item.get('sheet_type', '')
        
        # Get product details
        product_info = self._get_product_info(product_slug, product_code)
        count_images = product_info.get('count_images', 1)
        frame_style = product_info.get('frame_style_default', 'none')
        
        # Draw frame
        frame_color = self._get_frame_color(frame_style)
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([x-2, y-2, x+width+2, y+height+2], outline=frame_color, width=3)
        
        # Draw white background
        draw.rectangle([x, y, x+width, y+height], fill=(255, 255, 255), outline=(150, 150, 150))
        
        # Handle sheet-based products differently
        if sheet_type == '2x2':
            # Wallet sheet with 2x2 grid
            self._draw_wallet_sheet_2x2(canvas, x, y, width, height, image_codes)
        elif sheet_type == 'landscape_2x1':
            # 5x7 landscape sheet with 2 portrait images side by side
            self._draw_5x7_landscape_sheet(canvas, x, y, width, height, image_codes)
        elif sheet_type == 'portrait_2x2':
            # 3.5x5 portrait sheet with 2x2 grid
            self._draw_3x5_portrait_sheet(canvas, x, y, width, height, image_codes)
        else:
            # Regular single image products
            self._draw_images_clean(canvas, x, y, width, height, image_codes, count_images)
        
        # Draw quantity badge if > 1
        if quantity > 1:
            self._draw_quantity_badge_clean(canvas, x + width - 25, y + 5, quantity)
        
        # Draw size label (small, unobtrusive)
        self._draw_size_label(canvas, x + 2, y + 2, position['actual_width_in'], position['actual_height_in'])
    
    def _draw_wallet_sheet_2x2(self, canvas: Image.Image, x: int, y: int, width: int, height: int, image_codes: List[str]):
        """Draw a wallet sheet with 2x4 grid of 8 identical images on 8x10 landscape"""
        # Calculate individual wallet size within the sheet (2 rows, 4 columns)
        wallet_width = (width - 10) // 4  # 10px total for borders/gaps (2 + 4*2)
        wallet_height = (height - 6) // 2  # 6px total for borders/gaps (2 + 2*2)
        
        # Get the image code (should be same for all 8)
        image_code = image_codes[0] if image_codes else None
        
        # Draw 2x4 grid (2 rows, 4 columns)
        for row in range(2):
            for col in range(4):
                wallet_x = x + 2 + col * (wallet_width + 2)
                wallet_y = y + 2 + row * (wallet_height + 2)
                
                # Draw individual wallet with image
                self._draw_single_wallet(canvas, wallet_x, wallet_y, wallet_width, wallet_height, image_code)
    
    def _draw_5x7_landscape_sheet(self, canvas: Image.Image, x: int, y: int, width: int, height: int, image_codes: List[str]):
        """Draw a landscape 5x7 sheet with 2 portrait images side by side"""
        # Calculate individual 5x7 size within the sheet
        image_width = (width - 6) // 2  # 6px total for borders/gaps
        image_height = height - 4  # 4px for top/bottom borders
        
        # Draw 2 side-by-side portraits
        for i in range(2):
            image_x = x + 2 + i * (image_width + 2)
            image_y = y + 2
            
            # Get the image code for this position
            image_code = image_codes[i] if i < len(image_codes) else (image_codes[0] if image_codes else None)
            
            # Draw individual 5x7 portrait
            self._draw_single_image_from_code(canvas, image_x, image_y, image_width, image_height, image_code)
    
    def _draw_3x5_portrait_sheet(self, canvas: Image.Image, x: int, y: int, width: int, height: int, image_codes: List[str]):
        """Draw a portrait 3.5x5 sheet with 2x2 grid of 4 identical images on 7x10 portrait"""
        # Calculate individual 3.5x5 size within the sheet (2 rows, 2 columns)
        image_width = (width - 6) // 2  # 6px total for borders/gaps (2 + 2*2)
        image_height = (height - 6) // 2  # 6px total for borders/gaps (2 + 2*2)
        
        # Get the image code (should be same for all 4)
        image_code = image_codes[0] if image_codes else None
        
        # Draw 2x2 grid (2 rows, 2 columns)
        for row in range(2):
            for col in range(2):
                image_x = x + 2 + col * (image_width + 2)
                image_y = y + 2 + row * (image_height + 2)
                
                # Draw individual 3.5x5 image
                self._draw_single_image_from_code(canvas, image_x, image_y, image_width, image_height, image_code)
    
    def _draw_single_wallet(self, canvas: Image.Image, x: int, y: int, width: int, height: int, image_code: str):
        """Draw a single wallet image"""
        draw = ImageDraw.Draw(canvas)
        
        # Draw wallet border
        draw.rectangle([x, y, x+width, y+height], fill=(250, 250, 250), outline=(180, 180, 180))
        
        # Draw the actual image if available
        if image_code and image_code in self.images:
            self._draw_actual_image_in_rect(canvas, x+1, y+1, width-2, height-2, image_code)
        else:
            # Subtle placeholder for missing image
            self._draw_subtle_placeholder(canvas, x+1, y+1, width-2, height-2, 1)
    
    def _draw_single_image_from_code(self, canvas: Image.Image, x: int, y: int, width: int, height: int, image_code: str):
        """Draw a single portrait image from image code"""
        draw = ImageDraw.Draw(canvas)
        
        # Draw image border
        draw.rectangle([x, y, x+width, y+height], fill=(250, 250, 250), outline=(180, 180, 180))
        
        # Draw the actual image if available
        if image_code and image_code in self.images:
            self._draw_actual_image_in_rect(canvas, x+1, y+1, width-2, height-2, image_code)
        else:
            # Subtle placeholder for missing image
            self._draw_subtle_placeholder(canvas, x+1, y+1, width-2, height-2, 1)
    
    def _draw_actual_image_in_rect(self, canvas: Image.Image, x: int, y: int, width: int, height: int, image_code: str):
        """Draw an actual image file within the specified rectangle"""
        try:
            image_path = self.images[image_code]['canonical_portrait_img']
            with Image.open(image_path) as img:
                # DON'T rotate images - keep them in their natural orientation
                # The previous rotation was causing images to appear sideways
                
                # Resize to fit while maintaining aspect ratio
                img_ratio = img.width / img.height
                rect_ratio = width / height
                
                if img_ratio > rect_ratio:
                    # Image is wider relative to rect
                    new_width = width
                    new_height = int(width / img_ratio)
                    y_offset = (height - new_height) // 2
                    x_offset = 0
                else:
                    # Image is taller relative to rect
                    new_height = height
                    new_width = int(height * img_ratio)
                    x_offset = (width - new_width) // 2
                    y_offset = 0
                
                img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                canvas.paste(img_resized, (x + x_offset, y + y_offset))
                
        except Exception as e:
            # If image loading fails, draw placeholder
            self._draw_subtle_placeholder(canvas, x, y, width, height, 1)
    
    def _draw_images_clean(self, canvas: Image.Image, x: int, y: int, width: int, height: int, 
                          image_codes: List[str], count_images: int):
        """Draw images cleanly in portrait orientation"""
        # Find actual image files
        actual_images = []
        for code in image_codes:
            if code in self.images:
                actual_images.extend(self.images[code]['canonical_portrait_img'])
        
        if not actual_images and count_images > 0:
            # Create a subtle placeholder instead of "No Image Found"
            self._draw_subtle_placeholder(canvas, x, y, width, height, count_images)
            return
        
        # Layout based on count_images
        if count_images == 1:
            self._draw_single_image_portrait(canvas, x, y, width, height, actual_images)
        elif count_images == 2:
            self._draw_pair_images_portrait(canvas, x, y, width, height, actual_images)
        elif count_images == 3:
            self._draw_trio_images_portrait(canvas, x, y, width, height, actual_images)
        elif count_images >= 4:
            self._draw_grid_images_portrait(canvas, x, y, width, height, actual_images, count_images)
    
    def _draw_single_image_portrait(self, canvas: Image.Image, x: int, y: int, width: int, height: int, images: List[Path]):
        """Draw single image in portrait orientation"""
        if not images:
            return
        
        try:
            img = Image.open(images[0])
            
            # DON'T force portrait orientation - keep images upright as they are
            # The previous rotation logic was causing images to be turned sideways
            # Just use the image in its natural orientation
            
            # Fit to rectangle maintaining aspect ratio
            img_ratio = img.width / img.height
            rect_ratio = width / height
            
            if img_ratio > rect_ratio:
                # Image wider relative to rect - fit to width
                new_width = width - 8
                new_height = int(new_width / img_ratio)
            else:
                # Image taller relative to rect - fit to height
                new_height = height - 8
                new_width = int(new_height * img_ratio)
            
            # Resize and center
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            paste_x = x + (width - new_width) // 2
            paste_y = y + (height - new_height) // 2
            canvas.paste(resized, (paste_x, paste_y))
            
        except Exception as e:
            logger.error(f"Error drawing image {images[0]}: {e}")
            self._draw_subtle_placeholder(canvas, x, y, width, height, 1)
    
    def _draw_pair_images_portrait(self, canvas: Image.Image, x: int, y: int, width: int, height: int, images: List[Path]):
        """Draw pair of images side by side in portrait"""
        img_width = (width - 12) // 2
        
        for i in range(2):
            img_x = x + 4 + i * (img_width + 4)
            
            if i < len(images):
                try:
                    img = Image.open(images[i])
                    # DON'T rotate - keep natural orientation
                    
                    # Fit to available space maintaining aspect ratio
                    img_ratio = img.width / img.height
                    target_ratio = img_width / (height - 8)
                    
                    if img_ratio > target_ratio:
                        # Fit to width
                        new_width = img_width
                        new_height = int(img_width / img_ratio)
                        y_offset = ((height - 8) - new_height) // 2
                        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        canvas.paste(resized, (img_x, y + 4 + y_offset))
                    else:
                        # Fit to height
                        new_height = height - 8
                        new_width = int((height - 8) * img_ratio)
                        x_offset = (img_width - new_width) // 2
                        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        canvas.paste(resized, (img_x + x_offset, y + 4))
                except:
                    self._draw_subtle_placeholder(canvas, img_x, y + 4, img_width, height - 8, 1)
    
    def _draw_trio_images_portrait(self, canvas: Image.Image, x: int, y: int, width: int, height: int, images: List[Path]):
        """Draw trio of images horizontally in portrait"""
        img_width = (width - 16) // 3
        
        for i in range(3):
            img_x = x + 4 + i * (img_width + 4)
            
            if i < len(images):
                try:
                    img = Image.open(images[i])
                    # DON'T rotate - keep natural orientation
                    
                    # Fit to available space maintaining aspect ratio
                    img_ratio = img.width / img.height
                    target_ratio = img_width / (height - 8)
                    
                    if img_ratio > target_ratio:
                        # Fit to width
                        new_width = img_width
                        new_height = int(img_width / img_ratio)
                        y_offset = ((height - 8) - new_height) // 2
                        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        canvas.paste(resized, (img_x, y + 4 + y_offset))
                    else:
                        # Fit to height
                        new_height = height - 8
                        new_width = int((height - 8) * img_ratio)
                        x_offset = (img_width - new_width) // 2
                        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        canvas.paste(resized, (img_x + x_offset, y + 4))
                except:
                    self._draw_subtle_placeholder(canvas, img_x, y + 4, img_width, height - 8, 1)
    
    def _draw_grid_images_portrait(self, canvas: Image.Image, x: int, y: int, width: int, height: int, 
                                  images: List[Path], count: int):
        """Draw multiple images in grid layout in portrait"""
        cols = min(4, count)
        rows = (count + cols - 1) // cols
        
        img_width = (width - (cols + 1) * 2) // cols
        img_height = (height - (rows + 1) * 2) // rows
        
        for i in range(min(count, 8)):  # Limit to 8 for wallets
            row = i // cols
            col = i % cols
            
            img_x = x + 2 + col * (img_width + 2)
            img_y = y + 2 + row * (img_height + 2)
            
            if i < len(images):
                try:
                    img = Image.open(images[i % len(images)])
                    if img.width > img.height:
                        img = img.rotate(90, expand=True)
                    
                    resized = img.resize((img_width, img_height), Image.Resampling.LANCZOS)
                    canvas.paste(resized, (img_x, img_y))
                except:
                    self._draw_subtle_placeholder(canvas, img_x, img_y, img_width, img_height, 1)
    
    def _draw_subtle_placeholder(self, canvas: Image.Image, x: int, y: int, width: int, height: int, count: int):
        """Draw subtle placeholder without error text"""
        draw = ImageDraw.Draw(canvas)
        
        # Very light gray background
        draw.rectangle([x, y, x + width, y + height], fill=(250, 250, 250), outline=(220, 220, 220))
        
        # Small icon or pattern instead of text
        center_x = x + width // 2
        center_y = y + height // 2
        
        # Draw a simple camera icon
        icon_size = min(width, height) // 6
        draw.rectangle([center_x - icon_size, center_y - icon_size//2, 
                       center_x + icon_size, center_y + icon_size//2], 
                      fill=(200, 200, 200))
        draw.ellipse([center_x - icon_size//3, center_y - icon_size//3,
                     center_x + icon_size//3, center_y + icon_size//3],
                    fill=(180, 180, 180))
    
    def _get_product_info(self, product_slug: str, product_code: str) -> Dict:
        """Get product info from config"""
        for product in self.products_config.get('products', []):
            if product.get('slug') == product_slug or product.get('code') == product_code:
                return product
        return {'name': product_slug or product_code, 'count_images': 1, 'frame_style_default': 'none'}
    
    def _get_frame_color(self, frame_style: str) -> Tuple[int, int, int]:
        """Get frame color based on style"""
        frame_colors = {
            'cherry': (139, 69, 19),
            'black': (0, 0, 0),
            'white': (220, 220, 220),
            'none': (100, 100, 100)
        }
        return frame_colors.get(frame_style, (100, 100, 100))
    
    def _draw_quantity_badge_clean(self, canvas: Image.Image, x: int, y: int, quantity: int):
        """Draw clean quantity badge"""
        draw = ImageDraw.Draw(canvas)
        
        badge_size = 20
        draw.ellipse([x, y, x + badge_size, y + badge_size], 
                    fill=(200, 50, 50), outline=(150, 30, 30), width=1)
        
        try:
            font = ImageFont.load_default()
            text = f"×{quantity}"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = x + (badge_size - text_width) // 2
            text_y = y + (badge_size - text_height) // 2
            draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)
        except:
            pass
    
    def _draw_size_label(self, canvas: Image.Image, x: int, y: int, width_in: float, height_in: float):
        """Draw small size label"""
        draw = ImageDraw.Draw(canvas)
        
        try:
            font = ImageFont.load_default()
            text = f"{width_in}×{height_in}\""
            draw.text((x, y), text, fill=(100, 100, 100), font=font)
        except:
            pass
    
    def _draw_title(self, canvas: Image.Image, title: str):
        """Draw clean title"""
        draw = ImageDraw.Draw(canvas)
        
        try:
            font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), title, font=font)
            text_width = bbox[2] - bbox[0]
            x = (self.CANVAS_W - text_width) // 2
            draw.text((x, 20), title, fill=(80, 80, 80), font=font)
        except:
            pass
    
    def _draw_minimal_summary(self, canvas: Image.Image, items: List[Dict]):
        """Draw minimal order summary"""
        draw = ImageDraw.Draw(canvas)
        
        try:
            font = ImageFont.load_default()
            
            # Count totals
            total_pieces = sum(item.get('quantity', 1) for item in items)
            total_types = len(items)
            
            summary_text = f"Order: {total_types} product types, {total_pieces} total pieces"
            
            # Bottom right corner
            bbox = draw.textbbox((0, 0), summary_text, font=font)
            text_width = bbox[2] - bbox[0]
            x = self.CANVAS_W - text_width - 20
            y = self.CANVAS_H - 30
            
            draw.text((x, y), summary_text, fill=(120, 120, 120), font=font)
            
        except Exception as e:
            logger.error(f"Error drawing summary: {e}")

    def generate_frame_showcase_preview(self, items: List[Dict], output_filename: str,
                                       frame_requirements: Dict[str, int] = None) -> bool:
        """
        Generate a frame showcase preview with alternating Black and Cherry frames
        
        Args:
            items: List of order items with product info and quantities
            output_filename: Where to save the preview
            frame_requirements: Dictionary mapping frame size to quantity needed
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Generating frame showcase preview for {len(items)} product types")
            
            # Process frame requirements with alternating styles
            processed_items = items
            if frame_requirements:
                logger.info(f"Applying frame requirements with alternating styles: {frame_requirements}")
                processed_items = self.frame_engine.apply_frames_with_alternating_styles(items, frame_requirements)
                logger.info(f"Processed items: {len(items)} -> {len(processed_items)} (after frame application)")
            
            # STEP 5: Process all images to canonical portrait orientation and master crops
            self._process_images(processed_items)
            
            # Create canvas with beige background
            canvas = Image.new('RGB', (self.CANVAS_W, self.CANVAS_H), self.beige_color)
            
            # Separate trio and non-trio products
            regular_items = []
            trio_items = []
            
            for item in processed_items:
                if is_trio_product(item):
                    # Get product config for trio item
                    product_code = item.get('product_code', '')
                    if product_code in self.products_config:
                        trio_items.append((item, self.products_config[product_code]))
                else:
                    regular_items.append(item)
            
            # Sort regular items by size (largest first)
            sorted_regular_items = self._sort_items_by_size_corrected(regular_items)
            
            # Calculate layout with composites
            layout = self._calculate_corrected_layout_with_composites(sorted_regular_items, trio_items)
            
            # Draw all items
            for position in layout:
                self._draw_product_corrected(canvas, position)
            
            # Save preview
            canvas.save(output_filename, 'PNG', quality=95)
            logger.info(f"✅ Frame showcase preview saved: {output_filename}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate frame showcase preview: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _draw_overlay_banner(self, canvas: Image.Image, x: int, y: int, width: int, height: int,
                           spec: Dict, item: Dict = None, image_codes: List[str] = None):
        """Draw overlay banner for Artist Series, Retouch, or Both at the top of portraits"""
        try:
            if not item:
                return
                
            # Check for Artist Series
            is_artist_series = self._is_artist_series(item, spec)
            
            # Check for Retouch (if any image codes or item flag indicate it)
            is_retouch = self._is_retouch(image_codes or [], item)
            
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
                return
                
            draw = ImageDraw.Draw(canvas)
            
            # Try to load bold font
            try:
                banner_font = ImageFont.truetype("arialbd.ttf", 14)  # Bold font for banner
            except:
                banner_font = ImageFont.load_default()
            
            # Calculate banner dimensions
            bbox = draw.textbbox((0, 0), banner_text, font=banner_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Banner height and positioning
            banner_height = text_height + 8  # Add padding
            banner_y = y  # Position at very top of image
            
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
            
            # Paste overlay onto canvas with alpha blending
            canvas.paste(overlay, (x, banner_y), overlay)
            
            logger.debug(f"Drew gradient overlay banner '{banner_text}' for item at ({x}, {y})")
            
        except Exception as e:
            logger.error(f"Failed to draw overlay banner: {e}")

    def _is_artist_series(self, item: Dict, spec: Dict) -> bool:
        """Check if item qualifies for Artist Series banner"""
        # Artist Series applies to top three portrait options with specific descriptions
        display_name = item.get('display_name', 'Unknown')
        product_slug = item.get('product_slug', '')
        
        # Check for artist series keywords in display name or description
        artist_keywords = [
            'artist series', 'artist brush strokes', 'artist', 'brush strokes',
            'artistic', 'enhanced artistic', 'premium artistic'
        ]
        
        # Check if any artist keywords are present
        for keyword in artist_keywords:
            if keyword.lower() in display_name.lower():
                return True
                
        # Check if item has artist_series flag
        if item.get('artist_series', False):
            return True
            
        return False

    def _is_retouch(self, image_codes: List[str], item: Dict | None = None) -> bool:
        """Check if an item or its images are flagged for retouch."""
        if item and item.get('retouch'):
            return True

        # Fallback to legacy list based on image codes
        retouch_list = ['0033', '0039']
        for code in image_codes:
            if code in retouch_list:
                return True

        return False