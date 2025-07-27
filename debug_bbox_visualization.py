#!/usr/bin/env python3
"""
Debug script to visualize bounding boxes on the screenshot
"""
import cv2
import numpy as np
from app.bbox_map import BOUNDING_BOXES

def visualize_bboxes(image_path):
    """Visualize bounding boxes on the screenshot"""
    # Load the image
    img = cv2.imread(image_path)
    if img is None:
        print(f"❌ Could not load image: {image_path}")
        return
    
    print(f"📸 Image dimensions: {img.shape[1]}x{img.shape[0]}")
    
    # Define colors for each column
    colors = {
        'COL_QTY': (0, 255, 0),    # Green
        'COL_CODE': (255, 0, 0),   # Blue  
        'COL_DESC': (0, 0, 255),   # Red
        'COL_IMG': (255, 255, 0),  # Cyan
        'PORTRAIT_TABLE': (255, 0, 255)  # Magenta
    }
    
    # Draw bounding boxes
    for box_name, coords in BOUNDING_BOXES.items():
        if box_name.startswith('COL_') or box_name == 'PORTRAIT_TABLE' or box_name.startswith('ROW'):
            x1, y1, x2, y2 = coords
            
            # Different colors for different types
            if box_name.startswith('ROW'):
                # Row-specific colors (lighter)
                row_num = int(box_name.split('_')[0][3:])  # Extract row number
                if 'QTY' in box_name:
                    color = (100, 255, 100)  # Light green
                elif 'CODE' in box_name:
                    color = (255, 100, 100)  # Light blue
                elif 'DESC' in box_name:
                    color = (100, 100, 255)  # Light red
                elif 'IMG' in box_name:
                    color = (255, 255, 100)  # Light cyan
            else:
                color = colors.get(box_name, (128, 128, 128))
            
            # Draw rectangle
            thickness = 1 if box_name.startswith('ROW') else 2
            cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)
            
            # Add label for non-row boxes
            if not box_name.startswith('ROW'):
                cv2.putText(img, box_name, (x1, y1-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            print(f"📦 {box_name}: ({x1}, {y1}, {x2}, {y2}) - {color}")
    
    # Draw sentinel points
    if 'SENTINELS' in BOUNDING_BOXES:
        for i, (x, y) in enumerate(BOUNDING_BOXES['SENTINELS']):
            cv2.circle(img, (x, y), 5, (0, 255, 255), -1)  # Yellow circles
            cv2.putText(img, f"S{i+1}", (x+10, y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    
    # Save visualization
    output_path = "tmp/bbox_visualization.png"
    cv2.imwrite(output_path, img)
    print(f"✅ Visualization saved to: {output_path}")
    
    # Also display key areas for debugging
    print("\n🔍 Bounding Box Analysis:")
    for box_name, coords in BOUNDING_BOXES.items():
        if box_name.startswith('COL_'):
            x1, y1, x2, y2 = coords
            width = x2 - x1
            height = y2 - y1
            print(f"   {box_name}: {width}x{height} pixels")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python debug_bbox_visualization.py <image_path>")
        sys.exit(1)
    
    visualize_bboxes(sys.argv[1]) 