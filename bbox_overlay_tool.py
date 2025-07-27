#!/usr/bin/env python3
"""
Bounding Box Overlay Tool - Visual validation of crop rectangles
Usage: python bbox_overlay_tool.py <screenshot_path> [--save-crops]
"""
import sys
import cv2
import numpy as np
from pathlib import Path
from app.bbox_map import BB, UI_VERSION, PAD_X, PAD_Y

def create_bbox_overlay(image_path: str, save_crops: bool = False):
    """Create visual overlay of bounding boxes on screenshot"""
    # Load the image
    img = cv2.imread(image_path)
    if img is None:
        print(f"❌ Could not load image: {image_path}")
        return
    
    height, width = img.shape[:2]
    print(f"📸 Image dimensions: {width}x{height}")
    print(f"🎯 UI Version: {UI_VERSION}")
    print(f"🔧 Padding: X={PAD_X}px, Y={PAD_Y}px")
    
    # Create overlay copy
    overlay = img.copy()
    
    # Define colors for different columns
    colors = {
        'PORTRAIT_TABLE': (255, 0, 255),  # Magenta - table boundary
        'COL_QTY': (0, 255, 0),           # Green - quantity
        'COL_CODE': (255, 0, 0),          # Blue - product code  
        'COL_DESC': (0, 0, 255),          # Red - description
        'COL_IMG': (0, 255, 255),         # Yellow - image codes
    }
    
    # Draw bounding boxes
    crops_saved = []
    for box_name, (x1, y1, x2, y2) in BB.items():
        if box_name not in colors:
            continue
            
        color = colors[box_name]
        
        # Apply padding if it's a column box
        if box_name.startswith('COL_'):
            x1_padded = max(0, x1 - PAD_X)
            y1_padded = max(0, y1 - PAD_Y)
            x2_padded = min(width, x2 + PAD_X)
            y2_padded = min(height, y2 + PAD_Y)
            
            # Draw padded box (thinner line)
            cv2.rectangle(overlay, (x1_padded, y1_padded), (x2_padded, y2_padded), 
                         (128, 128, 128), 1)
            
            # Save individual crops if requested
            if save_crops:
                crop = img[y1_padded:y2_padded, x1_padded:x2_padded]
                crop_path = f"tmp/debug_{box_name}.png"
                cv2.imwrite(crop_path, crop)
                crops_saved.append(crop_path)
                print(f"💾 Saved crop: {crop_path} ({crop.shape[1]}x{crop.shape[0]}px)")
        
        # Draw main bounding box
        thickness = 3 if box_name == 'PORTRAIT_TABLE' else 2
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, thickness)
        
        # Add label
        label_y = y1 - 10 if y1 > 20 else y1 + 25
        cv2.putText(overlay, box_name, (x1, label_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Print dimensions
        width_px = x2 - x1
        height_px = y2 - y1
        print(f"📦 {box_name}: ({x1}, {y1}, {x2}, {y2}) - {width_px}x{height_px}px")
    
    # Save overlay
    output_path = "tmp/bbox_overlay.png"
    Path("tmp").mkdir(exist_ok=True)
    cv2.imwrite(output_path, overlay)
    print(f"✅ Overlay saved: {output_path}")
    
    if crops_saved:
        print(f"📁 Individual crops saved: {len(crops_saved)} files")
    
    return output_path

def validate_bbox_alignment(image_path: str):
    """Quick validation checks for bounding box alignment"""
    img = cv2.imread(image_path)
    if img is None:
        return
    
    print(f"\n🔍 Bounding Box Validation:")
    
    issues = []
    
    # Check if boxes are within image bounds
    height, width = img.shape[:2]
    for box_name, (x1, y1, x2, y2) in BB.items():
        if not box_name.startswith('COL_'):
            continue
            
        if x2 > width or y2 > height:
            issues.append(f"❌ {box_name} extends beyond image bounds")
        elif x1 < 0 or y1 < 0:
            issues.append(f"❌ {box_name} has negative coordinates")
        else:
            print(f"✅ {box_name} within bounds")
    
    # Check for reasonable column widths
    for box_name, (x1, y1, x2, y2) in BB.items():
        if box_name.startswith('COL_'):
            width_px = x2 - x1
            if width_px < 20:
                issues.append(f"⚠️  {box_name} very narrow ({width_px}px)")
            elif width_px > 500:
                issues.append(f"⚠️  {box_name} very wide ({width_px}px)")
    
    if issues:
        print(f"\n⚠️  Issues found:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print(f"\n✅ All bounding boxes look good!")

def main():
    if len(sys.argv) < 2:
        print("Usage: python bbox_overlay_tool.py <screenshot_path> [--save-crops]")
        sys.exit(1)
    
    image_path = sys.argv[1]
    save_crops = "--save-crops" in sys.argv
    
    print("🎯 Bounding Box Overlay Tool")
    print("=" * 50)
    
    # Create overlay visualization
    overlay_path = create_bbox_overlay(image_path, save_crops)
    
    # Run validation checks
    validate_bbox_alignment(image_path)
    
    print(f"\n📋 Next steps:")
    print(f"   1. Open {overlay_path} to visually verify alignment")
    if save_crops:
        print(f"   2. Check tmp/debug_COL_*.png files for text quality")
    print(f"   3. Adjust BB coordinates in bbox_map.py if needed")
    print(f"   4. Re-run OCR test to validate improvements")

if __name__ == "__main__":
    main() 