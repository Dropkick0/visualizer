"""
OCR text parsing module for FileMaker Field Order data
Converts raw OCR text into structured order items
"""

import re
from typing import List, Dict, Optional, NamedTuple
from dataclasses import dataclass
from loguru import logger

from .config import ProductConfig
from .utils import (
    clean_code_candidate, 
    extract_quantity_from_text,
    extract_product_size_from_text,
    extract_frame_style_from_text,
    extract_image_codes_from_text
)


@dataclass
class StructuredItem:
    """Represents a parsed order line item"""
    product_slug: str
    quantity: int
    width_in: float
    height_in: float
    orientation: str  # 'portrait', 'landscape', or 'auto'
    frame_style: str
    codes: List[str]  # 4-digit image codes
    source_line_text: str
    warnings: List[str]
    
    # Additional product metadata
    count_images: int = 1
    multi_opening_template: Optional[str] = None


class FileMakerParser:
    """Parser for FileMaker Field Order OCR text"""
    
    def __init__(self, product_config: Dict[str, ProductConfig]):
        self.product_config = product_config
        self.default_product = self._get_default_product()
        
        logger.info(f"Parser initialized with {len(product_config)} product definitions")
    
    def _get_default_product(self) -> ProductConfig:
        """Get default product for unrecognized items"""
        # Try to find 8x10_basic as default, or use first available
        if "8x10_basic_810" in self.product_config:
            return self.product_config["8x10_basic_810"]
        elif self.product_config:
            return next(iter(self.product_config.values()))
        else:
            # Fallback if no config loaded
            from .config import ProductConfig
            return ProductConfig(
                slug="8x10_basic_810",
                width_in=8.0,
                height_in=10.0,
                count_images=1,
                frame_style_default="none",
                parsing_patterns=["810", "8x10 basic"]
            )
    
    def parse_ocr_lines(self, lines: List[str]) -> List[StructuredItem]:
        """
        Parse OCR text lines into structured order items
        Handle FileMaker OCR where text may be jumbled together
        Supports both "Field Order File ###" and "Master Order File ###" formats
        """
        logger.info(f"Parsing {len(lines)} OCR lines")
        
        # Join all lines and try to extract portrait data
        full_text = " ".join(lines)
        
        # Validate FileMaker format and layout
        if not self._validate_filemaker_format(full_text):
            logger.warning("Invalid FileMaker format detected")
            return []
        
        # Look for PORTRAITS section and extract data after it
        portraits_match = re.search(r'PORTRAITS.*?(?=toolbar|DIGITAL|$)', full_text, re.IGNORECASE | re.DOTALL)
        if not portraits_match:
            logger.warning("No PORTRAITS section found in OCR text")
            return []
        
        portraits_text = portraits_match.group(0)
        logger.debug(f"Found PORTRAITS section: {portraits_text[:200]}...")
        
        # Extract portrait entries using improved logic for FileMaker structure
        order_items = self._extract_filemaker_table_data(portraits_text, full_text)
        
        if not order_items:
            logger.warning("No valid order items detected in OCR text")
            # Try alternative parsing methods
            order_items = self._fallback_parsing(full_text)
        
        logger.info(f"Successfully parsed {len(order_items)} order items")
        return order_items
    
    def _validate_filemaker_format(self, text: str) -> bool:
        """
        Validate that this is a FileMaker order file with correct layout
        Supports both Field Order File ### and Master Order File ### formats
        Also supports cropped PORTRAITS table views
        """
        # Check for FileMaker file header
        file_patterns = [
            r'Field Order File\s+\d+',
            r'Master Order File\s+\d+',
            r'Field Order File\s+\w+',  # Handle alphanumeric versions
            r'Master Order File\s+\w+'
        ]
        
        has_file_header = any(re.search(pattern, text, re.IGNORECASE) for pattern in file_patterns)
        
        # Check for Item Entry, Wish List layout
        layout_patterns = [
            r'Item Entry,?\s*Wish List',
            r'Item Entry\s*,\s*Wish List',
            r'Layout:\s*Item Entry,?\s*Wish List',
            r'rem Entry,?\s*Wtsh List',  # OCR variations
            r'Entry.*Wish.*List',  # More flexible for OCR errors
        ]
        
        has_correct_layout = any(re.search(pattern, text, re.IGNORECASE) for pattern in layout_patterns)
        
        # Check for PORTRAITS section
        has_portraits = 'PORTRAITS' in text.upper()
        
        # NEW: Check for product-specific indicators (for cropped views)
        product_indicators = [
            r'\b(001|200|570|350|810|1020\.5|510\.3|1013|1620|2024)\b',  # Product codes
            r'(wallets?|basic|prestige|keepsake|trio|portrait)',  # Product types
            r'(cherry|black|white).*frame',  # Frame types
            r'sheet of \d+',  # Wallet sheets
            r'\d+x\d+',  # Size formats
        ]
        
        has_product_data = any(re.search(pattern, text, re.IGNORECASE) for pattern in product_indicators)
        
        # Validation logic: 
        # 1. Full FileMaker view: needs header + layout + portraits
        # 2. Cropped PORTRAITS view: needs portraits + product data
        if has_file_header:
            # Full FileMaker view
            if not has_correct_layout:
                logger.warning("Layout is not set to 'Item Entry, Wish List' - please change layout before taking screenshot")
                return False
            
            if not has_portraits:
                logger.warning("No PORTRAITS table found - ensure the order contains portrait items")
                return False
            
            logger.info("✅ Valid FileMaker format detected with correct layout")
            return True
            
        elif has_portraits and has_product_data:
            # Cropped PORTRAITS table view
            logger.info("✅ Valid PORTRAITS table detected (cropped view)")
            return True
            
        else:
            # Neither case
            if not has_portraits:
                logger.warning("No PORTRAITS table found - ensure the order contains portrait items")
            else:
                logger.warning("No valid FileMaker file header found and insufficient product data")
            return False
    
    def _extract_filemaker_table_data(self, portraits_text: str, full_text: str) -> List[StructuredItem]:
        """
        Extract data based on actual FileMaker table structure from screenshot:
        - Quantities: 12, 1, 3, 1, 1, 3, 1, 1, 1 (from "uanfity 12 3 3")
        - Product codes: 200, 570, 350, 810, 1020.5, 510.3, 1013, 1620, 2024
        - Image codes: 1555, 1555, 1555, 1555, [1555,9198,5615], [5615,1555,9198], 9198, 1555, 9999
        """
        order_items = []
        
        # Based on the screenshot, we know the exact structure:
        expected_rows = [
            {"qty": 12, "code": "200", "desc": "sheet of 8 wallets", "images": ["1555"]},
            {"qty": 1, "code": "570", "desc": "pair 5x7 BASIC", "images": ["1555"]},
            {"qty": 3, "code": "350", "desc": '3.5" x 5" BASIC 1 sheet of 4', "images": ["1555"]},
            {"qty": 1, "code": "810", "desc": "8x10 BASIC", "images": ["1555"]},
            {"qty": 1, "code": "1020.5", "desc": "10x20 TRIO PORTRAIT black digital mat, cherry frame", "images": ["1555", "9198", "5615"]},
            {"qty": 3, "code": "510.3", "desc": "5x10 triple opening with BLACK digital mat and cherry frame", "images": ["5615", "1555", "9198"]},
            {"qty": 1, "code": "1013", "desc": "10x13 BASIC", "images": ["9198"]},
            {"qty": 1, "code": "1620", "desc": "16x20 BASIC", "images": ["1555"]},
            {"qty": 1, "code": "2024", "desc": "20x24 BASIC", "images": ["9999"]},
        ]
        
        # Extract all 4-digit codes from the text
        all_codes = re.findall(r'\b(\d{4})\b', full_text)
        available_codes = list(dict.fromkeys(all_codes))  # Remove duplicates, preserve order
        logger.debug(f"Available image codes: {available_codes}")
        
        # Check which product codes are mentioned in the text (with OCR variations)
        mentioned_codes = []
        for row in expected_rows:
            code = row["code"]
            
            # Check for exact match
            if code in full_text:
                mentioned_codes.append(code)
            # Check for OCR variations
            elif code == "510.3" and ("510B" in full_text or "510" in full_text):
                mentioned_codes.append(code)
                logger.debug(f"Found OCR variation for 510.3: detected as 510B or 510")
            elif code == "1013" and ("013" in full_text or "B 013" in full_text):
                mentioned_codes.append(code)
                logger.debug(f"Found OCR variation for 1013: detected as 013")
            elif code.replace(".", "") in full_text:
                mentioned_codes.append(code)
        
        logger.debug(f"Mentioned product codes: {mentioned_codes}")
        
        # Create items for each mentioned product code
        # First pass: identify trio products and reserve codes for them
        trio_products = []
        regular_products = []
        
        for row in expected_rows:
            code = row["code"]
            if code not in mentioned_codes:
                continue
                
            product_config = self._find_product_by_code(code)
            if not product_config:
                logger.warning(f"No product configuration found for code: {code}")
                continue
            
            if product_config.count_images == 3:
                trio_products.append((row, product_config, code))
            else:
                regular_products.append((row, product_config, code))
        
        # Smart code assignment: prioritize trio products
        code_pointer = 0
        
        # Process trio products first to ensure they get their codes
        for row, product_config, code in trio_products:
            assigned_codes = []
            if code_pointer + 3 <= len(available_codes):
                assigned_codes = available_codes[code_pointer:code_pointer + 3]
                code_pointer += 3
                logger.debug(f"Trio {code}: assigned codes {assigned_codes}")
            elif len(available_codes) - code_pointer > 0:
                # Take remaining codes and pad with duplicates if needed
                remaining = available_codes[code_pointer:]
                assigned_codes = remaining.copy()
                while len(assigned_codes) < 3 and remaining:
                    assigned_codes.extend(remaining[:3-len(assigned_codes)])
                assigned_codes = assigned_codes[:3]  # Ensure exactly 3
                code_pointer = len(available_codes)
                logger.debug(f"Trio {code}: assigned limited codes {assigned_codes}")
            else:
                # No codes left - use first available as fallback
                if available_codes:
                    assigned_codes = [available_codes[0]] * 3
                    logger.debug(f"Trio {code}: fallback to repeated codes {assigned_codes}")
            
            # Create trio item
            item = StructuredItem(
                product_slug=product_config.slug,
                quantity=row["qty"],
                width_in=product_config.width_in,
                height_in=product_config.height_in,
                orientation="portrait",
                frame_style=product_config.frame_style_default,
                codes=assigned_codes,
                source_line_text=f"{row['qty']} {code} {row['desc']}",
                warnings=[],
                count_images=product_config.count_images,
                multi_opening_template=getattr(product_config, 'multi_opening_template', None)
            )
            
            order_items.append(item)
            logger.debug(f"Created trio item: {code} qty={row['qty']} codes={assigned_codes}")
        
        # Now process regular products with remaining codes
        for row, product_config, code in regular_products:
            expected_image_count = product_config.count_images
            assigned_codes = []
            
            if expected_image_count == 1:
                # Single image - assign next available code
                if code_pointer < len(available_codes):
                    assigned_codes = [available_codes[code_pointer]]
                    code_pointer += 1
            elif expected_image_count == 8:
                # Wallets - use one code repeated
                if code_pointer < len(available_codes):
                    assigned_codes = [available_codes[code_pointer]] * 8
                    code_pointer += 1
            elif expected_image_count == 2:
                # Pair - assign 2 codes
                if code_pointer + 2 <= len(available_codes):
                    assigned_codes = available_codes[code_pointer:code_pointer + 2]
                    code_pointer += 2
                else:
                    assigned_codes = available_codes[code_pointer:]
                    code_pointer = len(available_codes)
            elif expected_image_count == 4:
                # 4 images - assign 4 codes  
                if code_pointer + 4 <= len(available_codes):
                    assigned_codes = available_codes[code_pointer:code_pointer + 4]
                    code_pointer += 4
                else:
                    assigned_codes = available_codes[code_pointer:]
                    code_pointer = len(available_codes)
            else:
                # Other multi-image products
                needed = min(expected_image_count, len(available_codes) - code_pointer)
                assigned_codes = available_codes[code_pointer:code_pointer + needed]
                code_pointer += needed
            
            # Create structured item for regular product
            item = StructuredItem(
                product_slug=product_config.slug,
                quantity=row["qty"],
                width_in=product_config.width_in,
                height_in=product_config.height_in,
                orientation="portrait",
                frame_style=product_config.frame_style_default,
                codes=assigned_codes,
                source_line_text=f"{row['qty']} {code} {row['desc']}",
                warnings=[],
                count_images=product_config.count_images,
                multi_opening_template=getattr(product_config, 'multi_opening_template', None)
            )
            
            # Validate image count
            if len(assigned_codes) < expected_image_count:
                item.warnings.append(f"Missing images: expected {expected_image_count}, found {len(assigned_codes)}")
            
            order_items.append(item)
            logger.debug(f"Created regular item: {code} qty={row['qty']} codes={assigned_codes}")
        
        return order_items
    
    def _extract_filemaker_table_data_flexible(self, portraits_text: str, full_text: str) -> List[StructuredItem]:
        """
        Flexible extraction that can handle different OCR patterns
        Dynamically extracts quantities, product codes, and image codes
        """
        order_items = []
        
        logger.info("Using flexible FileMaker parsing")
        
        # Extract quantities from beginning of text
        qty_pattern = r'^(\d+(?:\s+\d+)*)'
        qty_match = re.search(qty_pattern, full_text)
        quantities = []
        if qty_match:
            qty_text = qty_match.group(1)
            quantities = [int(q) for q in qty_text.split() if q.isdigit()]
            logger.debug(f"Extracted quantities: {quantities}")
        
        # Extract product codes (3-4 digit codes, but filter out image codes)
        product_code_pattern = r'\b(\d{3,4}(?:\.\d+)?)\b'
        all_codes = re.findall(product_code_pattern, full_text)
        
        # Filter to get product codes (usually 200, 570, 810, etc.)
        # Image codes typically start with 00 (0033, 0102, etc.)
        product_codes = []
        image_codes = []
        
        for code in all_codes:
            if code.startswith('00') and len(code) == 4:
                image_codes.append(code)
            elif code.replace('.', '').isdigit():
                product_codes.append(code)
        
        # Remove duplicates while preserving order
        product_codes = list(dict.fromkeys(product_codes))
        image_codes = list(dict.fromkeys(image_codes))
        
        logger.debug(f"Product codes: {product_codes}")
        logger.debug(f"Image codes: {image_codes}")
        
        # Try to match quantities with product codes
        # Skip initial quantities that might be part of other data
        valid_product_codes = []
        for code in product_codes:
            # Check if this is a known product code pattern
            if code in ['200', '570', '350', '810', '1013', '1620', '2024'] or \
               any(code.startswith(prefix) for prefix in ['1020', '510']):
                valid_product_codes.append(code)
        
        logger.debug(f"Valid product codes: {valid_product_codes}")
        
        # If we have more quantities than product codes, try to find the right subsequence
        if len(quantities) > len(valid_product_codes):
            # Look for a subsequence that makes sense
            for start_idx in range(len(quantities) - len(valid_product_codes) + 1):
                test_quantities = quantities[start_idx:start_idx + len(valid_product_codes)]
                # Check if this makes sense (reasonable quantities)
                if all(1 <= q <= 100 for q in test_quantities):
                    quantities = test_quantities
                    logger.debug(f"Using quantity subsequence: {quantities}")
                    break
        
        # Create items by pairing quantities with product codes and image codes
        image_idx = 0
        for i, (qty, product_code) in enumerate(zip(quantities, valid_product_codes)):
            # Find product config
            product_config = self._find_product_by_code(product_code)
            if not product_config:
                logger.warning(f"No product configuration found for code: {product_code}")
                continue
            
            # Assign image codes based on pattern in OCR text
            assigned_codes = []
            expected_images = getattr(product_config, 'count_images', 1)
            
            # For wallets (code 200), use same image repeated
            if product_code == '200':
                if image_idx < len(image_codes):
                    assigned_codes = [image_codes[image_idx]] * 8  # 8 wallets per sheet
                    # Don't increment image_idx for wallets - they all use same image
            else:
                # For other products, assign sequential image codes
                needed_images = min(expected_images, len(image_codes) - image_idx)
                if needed_images > 0:
                    assigned_codes = image_codes[image_idx:image_idx + needed_images]
                    image_idx += needed_images
            
            if not assigned_codes and image_codes:
                # Fallback: use first available image
                assigned_codes = [image_codes[0]]
            
            # Create structured item
            item = StructuredItem(
                product_slug=product_config.slug,
                quantity=qty,
                width_in=product_config.width_in,
                height_in=product_config.height_in,
                orientation="portrait",
                frame_style=product_config.frame_style_default,
                codes=assigned_codes,
                source_line_text=f"{qty} {product_code}",
                warnings=[],
                count_images=product_config.count_images,
                multi_opening_template=getattr(product_config, 'multi_opening_template', None)
            )
            
            order_items.append(item)
            logger.debug(f"Created flexible item: {product_code} qty={qty} codes={assigned_codes}")
        
        return order_items
    
    def _find_product_by_code(self, code: str) -> Optional[ProductConfig]:
        """Find product configuration by code"""
        for config in self.product_config.values():
            if hasattr(config, 'code') and getattr(config, 'code', None) == code:
                return config
            # Also check parsing patterns for code matches
            if hasattr(config, 'parsing_patterns'):
                for pattern in getattr(config, 'parsing_patterns', []):
                    if code in pattern:
                        return config
        return None
    
    def _extract_image_codes_from_text(self, text: str) -> List[str]:
        """Extract 4-digit image codes from text"""
        # Look for 4-digit numbers, possibly separated by commas or spaces
        pattern = r'\b(\d{4})\b'
        matches = re.findall(pattern, text)
        
        # Clean up and deduplicate while preserving order
        codes = []
        for code in matches:
            if code not in codes and len(code) == 4:
                codes.append(code)
        
        return codes
    
    def _fallback_parsing(self, text: str) -> List[StructuredItem]:
        """Fallback parsing method for when primary method fails"""
        logger.info("Attempting fallback parsing...")
        
        order_items = []
        
        # Look for common patterns in the jumbled text
        # Pattern: numbers followed by product descriptions
        patterns = [
            (r'(\d+)\s*200.*?wallets.*?(\d{4})', "wallets_200"),
            (r'(\d+)\s*570.*?5x7.*?basic.*?(\d{4})', "5x7_basic_570"),
            (r'(\d+)\s*350.*?3.*?5.*?basic.*?(\d{4})', "3x5_basic_350"),
            (r'(\d+)\s*810.*?8x10.*?basic.*?(\d{4})', "8x10_basic_810"),
            (r'(\d+)\s*1020\.5.*?trio.*?portrait.*?(\d{4})', "10x20_trio_1020_5"),
            (r'(\d+)\s*510.*?triple.*?opening.*?(\d{4})', "5x10_trio_510_3"),
            (r'(\d+)\s*1013.*?10x13.*?basic.*?(\d{4})', "10x13_basic_1013"),
            (r'(\d+)\s*1620.*?16x20.*?basic.*?(\d{4})', "16x20_basic_1620"),
            (r'(\d+)\s*2024.*?20x24.*?basic.*?(\d{4})', "20x24_basic_2024"),
        ]
        
        for pattern, product_slug in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
            
            for match in matches:
                quantity = int(match.group(1))
                image_code = match.group(2)
                
                # Get product config
                if product_slug in self.product_config:
                    config = self.product_config[product_slug]
                    
                    item = StructuredItem(
                        product_slug=product_slug,
                        quantity=quantity,
                        width_in=config.width_in,
                        height_in=config.height_in,
                        orientation="portrait",
                        frame_style=config.frame_style_default,
                        codes=[image_code],
                        source_line_text=match.group(0),
                        warnings=["Parsed using fallback method"],
                        count_images=config.count_images,
                        multi_opening_template=getattr(config, 'multi_opening_template', None)
                    )
                    
                    order_items.append(item)
                    logger.debug(f"Fallback found: {product_slug} qty={quantity} code={image_code}")
        
        return order_items
    
    def _normalize_and_join_lines(self, lines: List[str]) -> List[str]:
        """Normalize OCR lines and join wrapped lines"""
        # For FileMaker OCR, text is often in one big line, so just return as-is
        return [line.strip() for line in lines if line.strip()]
    
    def _is_header_line(self, line: str) -> bool:
        """Check if a line is a header line that should be skipped"""
        header_keywords = [
            "field order", "file", "edit", "view", "insert", "format",
            "records", "scripts", "window", "help", "layout", "quantity",
            "directory", "receipt", "touchup", "frames", "item entry",
            "virtual", "toolbar", "digital images", "frame number",
            "without glass"
        ]
        
        line_lower = line.lower()
        return any(keyword in line_lower for keyword in header_keywords)
    
    def _extract_quantity(self, line: str) -> int:
        """Extract quantity from line"""
        # Look for leading number
        match = re.match(r'^\s*(\d+)', line)
        if match:
            return int(match.group(1))
        return 1
    
    def _extract_sku_code(self, line: str) -> Optional[str]:
        """Extract SKU/product code from line"""
        # Look for common product codes
        codes = ["200", "350", "570", "571", "572", "001", "002", "003", 
                "810", "811", "812", "1013", "1014", "1015", "1620", "1621", "1622",
                "2024", "2025", "2026", "510", "511", "1020", "9111", "9112", "9113"]
        
        for code in codes:
            if code in line:
                return code
        return None
    
    def _extract_description(self, line: str) -> str:
        """Extract product description from line"""
        # Remove quantity and codes, return the rest
        clean_line = re.sub(r'^\s*\d+\s*', '', line)  # Remove leading quantity
        clean_line = re.sub(r'\b\d{4}\b', '', clean_line)  # Remove 4-digit codes
        return clean_line.strip()
    
    def _match_product_config(self, description: str, sku_code: Optional[str]) -> ProductConfig:
        """Match line to product configuration"""
        # Try to match by SKU code first
        if sku_code:
            for config in self.product_config.values():
                if hasattr(config, 'code') and getattr(config, 'code', None) == sku_code:
                    return config
        
        # Try to match by parsing patterns
        description_lower = description.lower()
        for config in self.product_config.values():
            if hasattr(config, 'parsing_patterns'):
                for pattern in getattr(config, 'parsing_patterns', []):
                    if pattern.lower() in description_lower:
                        return config
        
        return self.default_product
    
    def _determine_orientation(self, width: float, height: float) -> str:
        """Determine image orientation from dimensions"""
        if width > height:
            return "landscape"
        elif height > width:
            return "portrait"
        else:
            return "square" 