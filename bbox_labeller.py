#!/usr/bin/env python3
"""
Bounding Box Labeller Tool for FileMaker PORTRAITS Table
Interactive tool to click-drag rectangle coordinates and auto-fill bbox_map.py
Helps fine-tune column boundaries for optimal OCR performance
"""

import cv2
import numpy as np
from pathlib import Path
import sys

# Add app directory to path  
sys.path.insert(0, str(Path(__file__).parent))

class BBoxLabeller:
    """Interactive bounding box labelling tool"""
    
    def __init__(self, image_path: Path):
        self.image_path = image_path
        self.image = cv2.imread(str(image_path))
        if self.image is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        self.original_image = self.image.copy()
        self.drawing = False
        self.start_point = None
        self.current_box = None
        self.boxes = {}
        self.current_label = "COL_QTY"
        
        # Predefined labels for PORTRAITS table columns
        self.labels = ["COL_QTY", "COL_CODE", "COL_DESC", "COL_IMG", "PORTRAIT_TABLE"]
        self.label_index = 0
        
        # Colors for different boxes
        self.colors = {
            "COL_QTY": (0, 255, 0),      # Green
            "COL_CODE": (255, 0, 0),     # Blue  
            "COL_DESC": (0, 255, 255),   # Yellow
            "COL_IMG": (255, 0, 255),    # Magenta
            "PORTRAIT_TABLE": (255, 255, 0)  # Cyan
        }
        
        print("🎯 Bounding Box Labeller Tool")
        print("=" * 50)
        print("Instructions:")
        print("• Click and drag to draw bounding boxes")
        print("• Press SPACE to switch between labels")
        print("• Press 'r' to reset current box")
        print("• Press 'c' to clear all boxes")
        print("• Press 's' to save coordinates")
        print("• Press 'q' to quit")
        print(f"• Current label: {self.current_label}")
        print("=" * 50)
    
    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse events for box drawing"""
        
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.start_point = (x, y)
            
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                # Update current box
                self.current_box = (self.start_point[0], self.start_point[1], x, y)
                self.redraw_image()
                
        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            if self.start_point and abs(x - self.start_point[0]) > 10 and abs(y - self.start_point[1]) > 10:
                # Store the box
                x1, y1 = self.start_point
                x2, y2 = x, y
                
                # Ensure x1,y1 is top-left and x2,y2 is bottom-right
                self.boxes[self.current_label] = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
                print(f"✅ Saved box for {self.current_label}: {self.boxes[self.current_label]}")
                
                # Auto-advance to next label
                self.advance_label()
                
            self.current_box = None
            self.redraw_image()
    
    def redraw_image(self):
        """Redraw image with all boxes"""
        display_image = self.original_image.copy()
        
        # Draw existing boxes
        for label, box in self.boxes.items():
            color = self.colors.get(label, (128, 128, 128))
            cv2.rectangle(display_image, (box[0], box[1]), (box[2], box[3]), color, 2)
            
            # Add label text
            cv2.putText(display_image, label, (box[0], box[1] - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Draw current box being drawn
        if self.current_box:
            color = self.colors.get(self.current_label, (128, 128, 128))
            cv2.rectangle(display_image, (self.current_box[0], self.current_box[1]), 
                         (self.current_box[2], self.current_box[3]), color, 2)
        
        # Add current label indicator
        cv2.putText(display_image, f"Current: {self.current_label}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        cv2.imshow('Bounding Box Labeller', display_image)
    
    def advance_label(self):
        """Advance to next label"""
        self.label_index = (self.label_index + 1) % len(self.labels)
        self.current_label = self.labels[self.label_index]
        print(f"📍 Current label: {self.current_label}")
    
    def reset_current_box(self):
        """Reset the current label's box"""
        if self.current_label in self.boxes:
            del self.boxes[self.current_label]
            print(f"🗑️  Reset box for {self.current_label}")
            self.redraw_image()
    
    def clear_all_boxes(self):
        """Clear all boxes"""
        self.boxes.clear()
        print("🗑️  Cleared all boxes")
        self.redraw_image()
    
    def save_coordinates(self):
        """Save coordinates to bbox_map.py"""
        if len(self.boxes) < 4:
            print(f"⚠️  Need at least 4 boxes, only have {len(self.boxes)}")
            return
        
        # Generate updated bbox_map.py content
        bbox_map_content = f'''"""
Centralized Bounding Box Map for FileMaker PORTRAITS Table OCR
Auto-generated by bbox_labeller.py
Single Source of Truth for all pixel rectangles - version controlled
Format: (x1, y1, x2, y2) where (x1,y1) is top-left, (x2,y2) is bottom-right
"""

# FileMaker UI Version - update when layout changes
UI_VERSION = "FileOrder_v1.10.25_custom"

# Screenshot capture standards
CAPTURE_STANDARDS = {{
    "resolution": "{self.image.shape[1]}x{self.image.shape[0]}",  # Detected from labelled image
    "scaling": "100%",          # Windows display scaling
    "format": "PNG",            # Lossless format
    "dpi": 96                   # Standard Windows DPI at 100% scaling
}}

# Main bounding boxes for column-isolated OCR (CUSTOM LABELLED)
BOUNDING_BOXES = {{
    # Full PORTRAITS table area
    "PORTRAIT_TABLE": {self.boxes.get("PORTRAIT_TABLE", (0, 0, self.image.shape[1], self.image.shape[0]))},
    
    # Individual column boxes for isolated OCR
    "COL_QTY": {self.boxes.get("COL_QTY", (25, 405, 75, 700))},        # Quantity column
    "COL_CODE": {self.boxes.get("COL_CODE", (80, 405, 155, 700))},     # Product code column  
    "COL_DESC": {self.boxes.get("COL_DESC", (160, 405, 530, 700))},    # Description column
    "COL_IMG": {self.boxes.get("COL_IMG", (535, 405, 850, 700))},      # Image codes column
    
    # Sentinel coordinates for layout drift detection (auto-generated)
    "SENTINELS": [
        ({self.boxes.get("COL_QTY", (25, 405, 75, 700))[0] + 25}, {self.boxes.get("COL_QTY", (25, 405, 75, 700))[1] - 20}),  # Above qty
        ({self.boxes.get("COL_DESC", (160, 405, 530, 700))[0] + 100}, {self.boxes.get("COL_DESC", (160, 405, 530, 700))[1] - 20}),  # Above desc
        ({self.boxes.get("COL_IMG", (535, 405, 850, 700))[0] + 50}, {self.boxes.get("COL_IMG", (535, 405, 850, 700))[1] - 20}),  # Above img
        ({self.boxes.get("COL_QTY", (25, 405, 75, 700))[0] + 15}, {self.boxes.get("COL_QTY", (25, 405, 75, 700))[1] + 30}),  # Inside qty
        ({self.boxes.get("COL_IMG", (535, 405, 850, 700))[0] + 30}, {self.boxes.get("COL_IMG", (535, 405, 850, 700))[1] + 30})   # Inside img
    ]
}}

# Column mapping for row reconstruction
COLUMN_FIELDS = {{
    "COL_QTY": "qty",
    "COL_CODE": "code", 
    "COL_DESC": "desc",
    "COL_IMG": "imgs"
}}

# Expected RGB ranges for layout validation (FileMaker's typical colors)
LAYOUT_COLORS = {{
    "background": (240, 240, 220),     # FileMaker beige background
    "header_bg": (200, 200, 180),      # Header background
    "text_color": (0, 0, 0),           # Black text
    "tolerance": 30                     # RGB delta tolerance for drift detection
}}

def get_column_boxes():
    """Return dictionary of column bounding boxes for OCR processing"""
    return {{
        name: bbox for name, bbox in BOUNDING_BOXES.items() 
        if name.startswith("COL_")
    }}

def get_sentinel_coords():
    """Return list of sentinel coordinates for layout drift detection"""
    return BOUNDING_BOXES["SENTINELS"]

def validate_ui_version():
    """Check if UI version matches expected FileMaker layout"""
    return True

def get_layout_info():
    """Return current layout configuration info"""
    return {{
        "ui_version": UI_VERSION,
        "capture_standards": CAPTURE_STANDARDS,
        "total_columns": len(get_column_boxes()),
        "table_area": BOUNDING_BOXES["PORTRAIT_TABLE"]
    }}

def get_debug_boxes():
    """Return all bounding boxes for visualization/debugging"""
    return BOUNDING_BOXES.copy()
'''
        
        # Write to file
        output_path = Path("app/bbox_map.py")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(bbox_map_content)
        
        print(f"💾 Saved coordinates to {output_path}")
        print("📋 Coordinate Summary:")
        for label, box in self.boxes.items():
            print(f"   • {label}: {box}")
    
    def run(self):
        """Run the interactive labelling tool"""
        cv2.namedWindow('Bounding Box Labeller')
        cv2.setMouseCallback('Bounding Box Labeller', self.mouse_callback)
        
        self.redraw_image()
        
        while True:
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord(' '):  # Space to switch labels
                self.advance_label()
            elif key == ord('r'):  # Reset current box
                self.reset_current_box()
            elif key == ord('c'):  # Clear all boxes
                self.clear_all_boxes()
            elif key == ord('s'):  # Save coordinates
                self.save_coordinates()
        
        cv2.destroyAllWindows()

def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python bbox_labeller.py <screenshot_path>")
        print("Example: python bbox_labeller.py Test_Full_Screenshot.png")
        return
    
    screenshot_path = Path(sys.argv[1])
    if not screenshot_path.exists():
        print(f"❌ Screenshot not found: {screenshot_path}")
        return
    
    try:
        labeller = BBoxLabeller(screenshot_path)
        labeller.run()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 