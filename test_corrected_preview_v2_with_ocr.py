#!/usr/bin/env python3
"""
Test Enhanced Preview Generator - OCR-based V3 WITH FRAMES
Uses OCR to automatically detect order items from FileMaker screenshot
Then maps to images in Dropbox folder and generates preview
"""

import sys
from pathlib import Path
import re
from typing import Dict, List

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_ocr_based_preview():
    """Test with OCR-detected data from actual FileMaker screenshot"""
    print("🎨 Enhanced Portrait Preview - OCR-based Detection V3 WITH FRAMES")
    print("=" * 80)
    
    try:
        from app.enhanced_preview import EnhancedPortraitPreviewGenerator
        from app.config import load_product_config, load_config
        from app.ocr_windows import WindowsOCR
        from app.parse import FileMakerParser
        
        # Load configuration
        app_config = load_config()
        products_config = load_product_config()
        
        print(f"✅ Loaded {len(products_config.get('products', []))} product configurations")
        
        # Step 1: OCR Processing
        print(f"\n🔍 Step 1: OCR Processing on FileMaker Screenshot")
        print("=" * 60)
        
        screenshot_path = Path("Test_Full_Screenshot.png")
        if not screenshot_path.exists():
            print(f"❌ Screenshot not found: {screenshot_path}")
            return False
        
        # Initialize OCR
        ocr_processor = WindowsOCR(app_config)
        
        # Create work directory
        work_dir = Path("tmp")
        work_dir.mkdir(exist_ok=True)
        
        # Process screenshot with OCR
        print(f"📸 Processing screenshot: {screenshot_path}")
        ocr_result = ocr_processor.process_screenshot(screenshot_path, work_dir)
        
        print(f"✅ OCR completed:")
        print(f"   • Confidence: {ocr_result.confidence_avg:.1f}%")
        print(f"   • Lines detected: {len(ocr_result.lines)}")
        print(f"   • Words detected: {len(ocr_result.words)}")
        
        # Show sample of OCR text
        sample_text = ocr_result.raw_text[:200] + "..." if len(ocr_result.raw_text) > 200 else ocr_result.raw_text
        print(f"   • Sample text: {sample_text}")
        
        # Step 2: Parse Order Items
        print(f"\n📋 Step 2: Parsing Order Items from OCR Text")
        print("=" * 60)
        
        parser = FileMakerParser(products_config)
        parsed_items = parser.parse_ocr_lines(ocr_result.lines)

        if not parsed_items:
            raise RuntimeError("No order items parsed from OCR. Fix OCR instead of faking.")
        
        print(f"✅ Successfully parsed {len(parsed_items)} order items:")
        for item in parsed_items:
            codes_str = ', '.join(item.codes) if hasattr(item, 'codes') and item.codes else 'No codes'
            print(f"   • {item.quantity}x {item.product_slug}: [{codes_str}]")
        
        # Step 3: Convert to enhanced preview format
        print(f"\n🔄 Step 3: Converting to Enhanced Preview Format")
        print("=" * 60)
        
        order_items = convert_parsed_to_preview_format(parsed_items)
        
        # Step 4: Image Discovery
        print(f"\n📸 Step 4: Discovering Images in Dropbox Folder")
        print("=" * 60)
        
        # Extract image codes from OCR
        image_codes = extract_image_codes_from_ocr(ocr_result.raw_text)
        print(f"🔍 Detected image codes from OCR: {image_codes}")
        
        # Found images from the specified Dropbox path
        dropbox_base = Path("C:/Users/remem/Re MEMBER Dropbox/PHOTOGRAPHY PROOFING/PHOTOGRAPHER UPLOADS (1)/Ethan/From/8017 Lab Order")
        
        # Search for images
        existing_images = discover_images_in_dropbox(dropbox_base, image_codes)
        
        if not existing_images:
            print("⚠️ No images found in Dropbox folder, using test images...")
            # Fallback to test images in local directory
            test_base = Path("C:/Users/remem/Re MEMBER Dropbox/PHOTOGRAPHY PROOFING/PHOTOGRAPHER UPLOADS (1)/Ethan/From/8017 Lab Order/Lab Order TU Only")
            existing_images = {
                '0033': [test_base / "_MG_0033.JPG"],
                '0039': [test_base / "_MG_0039.JPG"], 
                '0044': [test_base / "_MG_0044.JPG"],
                '0102': [test_base / "_MG_0102.JPG"],
            }
            
            # Filter to only existing files
            existing_images = {code: paths for code, paths in existing_images.items() 
                             if any(p.exists() for p in paths)}
        
        print(f"📸 Using {len(existing_images)} images:")
        for code, paths in existing_images.items():
            print(f"   • {code}: {paths[0].name}")
        
        # Step 5: Generate Preview
        print(f"\n🚀 Step 5: Generating OCR-based Preview with Frames")
        print("=" * 60)
        
        # Create frame requirements based on detected order
        frame_requirements = determine_frame_requirements(order_items)
        
        # Create enhanced generator
        output_dir = Path("app/static/previews")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generator = EnhancedPortraitPreviewGenerator(products_config, existing_images, output_dir)
        
        # Generate preview
        output_path = output_dir / "ocr_based_preview_v3_with_frames.png"
        
        print(f"🎨 Generating preview...")
        print(f"   • Input: OCR-detected order items")
        print(f"   • Images: {len(existing_images)} customer images")
        print(f"   • Frames: {sum(frame_requirements.values())} total frames")
        print(f"   • Output: {output_path}")
        
        success = generator.generate_size_based_preview_with_composites(
            order_items, output_path, frame_requirements
        )
        
        if success:
            print(f"✅ OCR-based preview created successfully!")
            print(f"📁 Saved to: {output_path}")
            print(f"🎯 Successfully used OCR to detect and render FileMaker order")
            return True
        else:
            print(f"❌ Failed to create preview")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def extract_image_codes_from_ocr(ocr_text: str) -> List[str]:
    """Extract 4-digit image codes from OCR text"""
    # Look for 4-digit codes that appear to be image references
    codes = re.findall(r'\b(\d{4})\b', ocr_text)
    
    # Filter out product codes (known from CSV)
    product_codes = ['0001', '0002', '0003', '0200', '0350', '0510', '0570', '0810', '1013', '1020', '1620', '2024']
    image_codes = [code for code in codes if code not in product_codes and code != '2025']  # Exclude year
    
    # Remove duplicates while preserving order
    unique_codes = list(dict.fromkeys(image_codes))
    return unique_codes

def discover_images_in_dropbox(base_path: Path, image_codes: List[str]) -> Dict[str, List[Path]]:
    """Search for images in Dropbox folder structure"""
    if not base_path.exists():
        print(f"⚠️ Dropbox path not found: {base_path}")
        return {}
    
    found_images = {}
    
    # Search patterns for image files
    extensions = ['*.jpg', '*.jpeg', '*.JPG', '*.JPEG', '*.png', '*.PNG']
    
    for code in image_codes:
        matching_files = []
        
        # Search in base directory and subdirectories
        for ext in extensions:
            # Pattern 1: _MG_XXXX.jpg
            pattern1 = f"_MG_{code}.*"
            matches1 = list(base_path.rglob(pattern1))
            matching_files.extend(matches1)
            
            # Pattern 2: XXXX.jpg
            pattern2 = f"{code}.*"
            matches2 = list(base_path.rglob(pattern2))
            matching_files.extend(matches2)
            
            # Pattern 3: Files containing the code
            for file_path in base_path.rglob(ext):
                if code in file_path.name:
                    matching_files.append(file_path)
        
        # Remove duplicates
        unique_files = list(set(matching_files))
        
        if unique_files:
            found_images[code] = unique_files[:1]  # Take first match
            print(f"   • Found {code}: {unique_files[0].name}")
    
    return found_images

def convert_parsed_to_preview_format(parsed_items: List) -> List[Dict]:
    """Convert parsed items to enhanced preview format"""
    order_items = []
    
    print(f"🔄 Converting {len(parsed_items)} parsed items to preview format...")
    
    for item in parsed_items:
        # Basic conversion - handle missing attributes
        product_code = getattr(item, 'product_code', None) or getattr(item, 'code', 'unknown')
        
        order_item = {
            'product_slug': item.product_slug,
            'product_code': product_code,
            'quantity': item.quantity,
            'image_codes': item.codes if hasattr(item, 'codes') and item.codes else ['0033'],
            'display_name': item.product_slug.replace('_', ' ').title()
        }
        
        # Add size category based on product slug and product code
        product_slug_lower = item.product_slug.lower()
        
        # Handle specific product types based on product code
        if product_code == '200':  # Wallets
            order_item['size_category'] = 'wallet_sheet'
            order_item['sheet_type'] = '2x2'
            order_item['display_name'] = f"{item.quantity} Wallet Sheets (8 wallets each)"
            print(f"   • Wallets: {order_item['display_name']}")
            
        elif product_code == '570':  # 5x7 pairs
            order_item['size_category'] = 'medium_sheet'
            order_item['sheet_type'] = 'landscape_2x1'
            order_item['display_name'] = f"{item.quantity} 5x7 Pair"
            print(f"   • 5x7 Pair: {order_item['display_name']}")
            
        elif product_code == '350':  # 3.5x5 sheets
            order_item['size_category'] = 'small_sheet' 
            order_item['sheet_type'] = 'portrait_2x2'
            order_item['display_name'] = f"{item.quantity} 3.5x5 Sheets (4 images each)"
            print(f"   • 3.5x5 Sheets: {order_item['display_name']}")
            
        elif product_code in ['810', '1013', '1620', '2024']:  # Individual prints
            order_item['size_category'] = 'large'
            size_map = {'810': '8x10', '1013': '10x13', '1620': '16x20', '2024': '20x24'}
            size = size_map.get(product_code, 'Unknown')
            order_item['display_name'] = f"{item.quantity} {size} BASIC"
            print(f"   • Individual print: {order_item['display_name']}")
            
        elif product_code in ['1020.5', '510.3']:  # Trio composites
            order_item['size_category'] = 'trio_composite'
            order_item['template'] = 'trio_horizontal'
            order_item['count_images'] = getattr(item, 'count_images', 3)
            order_item['frame_color'] = 'Black'
            order_item['matte_color'] = 'White'
            
            if product_code == '1020.5':
                order_item['display_name'] = f"{item.quantity} 10x20 Trio Portrait"
            else:
                order_item['display_name'] = f"{item.quantity} 5x10 Trio Portrait"
            print(f"   • Trio composite: {order_item['display_name']}")
            
        else:
            # Fallback categorization
            if 'wallet' in product_slug_lower:
                order_item['size_category'] = 'wallet_sheet'
                order_item['sheet_type'] = '2x2'
            elif '5x7' in product_slug_lower or 'pair' in product_slug_lower:
                order_item['size_category'] = 'medium_sheet'
                order_item['sheet_type'] = 'landscape_2x1'
            elif '3x5' in product_slug_lower:
                order_item['size_category'] = 'small_sheet'
                order_item['sheet_type'] = 'portrait_2x2'
            elif 'trio' in product_slug_lower:
                order_item['size_category'] = 'trio_composite'
                order_item['template'] = 'trio_horizontal'
                order_item['count_images'] = getattr(item, 'count_images', 3)
                order_item['frame_color'] = 'Black'
                order_item['matte_color'] = 'White'
            else:
                order_item['size_category'] = 'large'
        
        order_items.append(order_item)
    
    print(f"   ✅ Converted to {len(order_items)} preview items")
    return order_items

def determine_frame_requirements(order_items: List[Dict]) -> Dict[str, int]:
    """Determine frame requirements based on order items"""
    frame_requirements = {
        "5x7": 0,
        "8x10": 0,
        "10x13": 0,
        "16x20": 0,
        "20x24": 0
    }
    
    for item in order_items:
        if '5x7' in item.get('product_slug', '').lower():
            frame_requirements["5x7"] += item.get('quantity', 0)
        elif '8x10' in item.get('product_slug', '').lower():
            frame_requirements["8x10"] += item.get('quantity', 0)
        elif '10x13' in item.get('product_slug', '').lower():
            frame_requirements["10x13"] += item.get('quantity', 0)
        elif '16x20' in item.get('product_slug', '').lower():
            frame_requirements["16x20"] += item.get('quantity', 0)
        elif '20x24' in item.get('product_slug', '').lower():
            frame_requirements["20x24"] += item.get('quantity', 0)
    
    return frame_requirements

if __name__ == "__main__":
    test_ocr_based_preview() 