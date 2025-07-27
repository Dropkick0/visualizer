#!/usr/bin/env python3
"""
Row-Based OCR Test - Process each table row individually for precise extraction
"""
import sys
import cv2
import numpy as np
from pathlib import Path
import re
import asyncio
try:
    import winocr
    WINDOWS_OCR_AVAILABLE = True
except ImportError:
    WINDOWS_OCR_AVAILABLE = False

from app.bbox_map import BOUNDING_BOXES

def discover_images(base_path: Path, image_codes: list) -> dict:
    """Discover image files for the given codes"""
    if not base_path.exists():
        print(f"⚠️ Image search path not found: {base_path}")
        return {}
    
    found_images = {}
    extensions = ['*.jpg', '*.jpeg', '*.JPG', '*.JPEG', '*.png', '*.PNG']
    
    for code in image_codes:
        matching_files = []
        
        for ext in extensions:
            # Pattern 1: _MG_XXXX.jpg
            pattern1_files = list(base_path.glob(f"_MG_{code}*"))
            matching_files.extend(pattern1_files)
            
            # Pattern 2: XXXX.jpg
            pattern2_files = list(base_path.glob(f"{code}*"))
            matching_files.extend(pattern2_files)
        
        # Remove duplicates
        unique_files = list(set(matching_files))
        
        if unique_files:
            found_images[code] = unique_files[0]  # Take first match
    
    return found_images

def run_windows_ocr_on_region(image_path, bbox):
    """Run Windows OCR on a specific region"""
    if not WINDOWS_OCR_AVAILABLE:
        return "Mock OCR Text"
    
    try:
        # Load image and crop to region
        img = cv2.imread(image_path)
        x1, y1, x2, y2 = bbox
        cropped = img[y1:y2, x1:x2]
        
        # Upscale 3x for better OCR
        height, width = cropped.shape[:2]
        upscaled = cv2.resize(cropped, (width*3, height*3), interpolation=cv2.INTER_CUBIC)
        
        # Convert to PIL for winocr
        from PIL import Image
        pil_image = Image.fromarray(cv2.cvtColor(upscaled, cv2.COLOR_BGR2RGB))
        
        # Run Windows OCR
        result = winocr.recognize_pil_sync(pil_image, 'en-US')
        text = result.get('text', '') if isinstance(result, dict) else ''
        
        return text.strip()
    
    except Exception as e:
        print(f"   ⚠️  OCR error: {e}")
        return ""

def extract_quantity(text):
    """Extract quantity from text"""
    if not text:
        return None
    # Look for numbers at the start or standalone numbers
    match = re.search(r'\b(\d+)\b', text)
    if match:
        qty = int(match.group(1))
        if qty <= 30:  # Reasonable quantity limit
            return qty
    return None

def extract_product_code(text):
    """Extract product code from text"""
    if not text:
        return None
    
    # Common product codes from the screenshot
    valid_codes = [
        "200", "570", "350", "810", "1020.5", "510.3", "1013", "1620", "2024"
    ]
    
    # Look for exact matches
    for code in valid_codes:
        if code in text:
            return code
    
    # Look for numeric patterns
    matches = re.findall(r'\b(\d+(?:\.\d+)?)\b', text)
    for match in matches:
        if match in valid_codes:
            return match
    
    return None

def extract_image_codes(text):
    """Extract 4-digit image codes"""
    if not text:
        return []
    
    # Look for 4-digit codes
    codes = re.findall(r'\b(0\d{3})\b', text)
    return list(set(codes))  # Remove duplicates

def process_table_rows(image_path):
    """Process each table row individually"""
    print(f"🔍 Processing table rows from: {image_path}")
    
    rows = []
    for row_num in range(1, 9):  # Process 8 rows
        print(f"\n📋 Processing Row {row_num}:")
        
        # Get bounding boxes for this row
        qty_box = BOUNDING_BOXES.get(f"ROW{row_num}_QTY")
        code_box = BOUNDING_BOXES.get(f"ROW{row_num}_CODE") 
        desc_box = BOUNDING_BOXES.get(f"ROW{row_num}_DESC")
        img_box = BOUNDING_BOXES.get(f"ROW{row_num}_IMG")
        
        if not all([qty_box, code_box, desc_box, img_box]):
            print(f"   ❌ Missing bounding boxes for row {row_num}")
            continue
        
        # Extract text from each cell
        qty_text = run_windows_ocr_on_region(image_path, qty_box)
        code_text = run_windows_ocr_on_region(image_path, code_box)
        desc_text = run_windows_ocr_on_region(image_path, desc_box)
        img_text = run_windows_ocr_on_region(image_path, img_box)
        
        print(f"   Qty: '{qty_text}'")
        print(f"   Code: '{code_text}'") 
        print(f"   Desc: '{desc_text}'")
        print(f"   Imgs: '{img_text}'")
        
        # Parse extracted data
        qty = extract_quantity(qty_text)
        code = extract_product_code(code_text)
        img_codes = extract_image_codes(img_text)
        
        # Check if row has content
        has_content = any([qty_text.strip(), code_text.strip(), desc_text.strip(), img_text.strip()])
        
        if has_content:
            row_data = {
                'row': row_num,
                'qty': qty,
                'code': code,
                'description': desc_text.strip(),
                'image_codes': img_codes,
                'raw_qty': qty_text,
                'raw_code': code_text,
                'raw_desc': desc_text,
                'raw_img': img_text
            }
            rows.append(row_data)
            print(f"   ✅ Parsed: Qty={qty}, Code={code}, Images={img_codes}")
        else:
            print(f"   ➖ Row appears empty")
    
    return rows

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_row_based_ocr.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    print("🎯 Row-Based OCR Test")
    print("=" * 60)
    
    # Process table rows
    rows = process_table_rows(image_path)
    
    print(f"\n📊 Results Summary:")
    print(f"   • Total rows with content: {len(rows)}")
    
    # Display results
    if rows:
        print(f"\n📋 Extracted Order Items:")
        for i, row in enumerate(rows, 1):
            qty = row['qty'] if row['qty'] else 'N/A'
            code = row['code'] if row['code'] else 'N/A'
            imgs = ', '.join(row['image_codes']) if row['image_codes'] else 'N/A'
            desc = row['description'][:50] + '...' if len(row['description']) > 50 else row['description']
            print(f"   {i}. Qty:{qty} | Code:{code} | Desc:{desc} | Images:{imgs}")
        
        # Image discovery
        all_image_codes = []
        for row in rows:
            all_image_codes.extend(row['image_codes'])
        
        if all_image_codes:
            unique_codes = list(set(all_image_codes))
            print(f"\n📸 Image Discovery:")
            print(f"   • Found {len(unique_codes)} unique image codes: {unique_codes}")
            
            # Find actual image files
            # Check for Dropbox folder first, then fallback to assets
            dropbox_base = Path(r"C:\Users\remem\Dropbox\Duncan - Portrait Preview Automation\2024\PhotosForAutomation\Photos")
            assets_base = Path("assets/backgrounds")
            
            if dropbox_base.exists():
                image_files = discover_images(dropbox_base, unique_codes)
            else:
                image_files = discover_images(assets_base, unique_codes)
            
            for code in unique_codes:
                filepath = image_files.get(code)
                print(f"   • {code}: {filepath.name if filepath else 'NOT FOUND'}")
        
        print(f"\n✅ Row-based OCR extraction completed successfully!")
        
    else:
        print(f"\n❌ No rows extracted - check bounding boxes")
    
    print(f"\nPress Enter to exit...")
    input()

if __name__ == "__main__":
    main() 