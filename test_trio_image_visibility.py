#!/usr/bin/env python3
"""
Test script to verify that customer images are visible through trio composite frame openings
Creates colored test images and overlays them to verify proper layering
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.trio_composite import TrioCompositeGenerator


def create_test_customer_images():
    """Create colored test images to verify visibility"""
    test_images_dir = Path("tmp/test_images")
    test_images_dir.mkdir(parents=True, exist_ok=True)
    
    # Create 3 distinctive colored test images
    colors = [
        (255, 100, 100),  # Red
        (100, 255, 100),  # Green  
        (100, 100, 255)   # Blue
    ]
    
    labels = ["IMAGE 1", "IMAGE 2", "IMAGE 3"]
    image_paths = []
    
    for i, (color, label) in enumerate(zip(colors, labels)):
        # Create test image
        img = Image.new('RGB', (800, 1000), color)  # Portrait orientation
        
        # Add text label
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 60)
        except:
            font = ImageFont.load_default()
        
        # Get text size and center it
        bbox = draw.textbbox((0, 0), label, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (800 - text_width) // 2
        y = (1000 - text_height) // 2
        
        # Draw text with outline for visibility
        outline_color = (255, 255, 255) if sum(color) < 600 else (0, 0, 0)
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), label, font=font, fill=outline_color)
        draw.text((x, y), label, font=font, fill=(0, 0, 0))
        
        # Save test image
        image_path = test_images_dir / f"test_customer_{i+1}.jpg"
        img.save(image_path, 'JPEG', quality=95)
        image_paths.append(image_path)
        
        print(f"Created test image {i+1}: {color} - {image_path}")
    
    return image_paths


def test_trio_image_visibility():
    """Test that customer images are visible through frame openings"""
    print("🧪 Testing Trio Image Visibility")
    print("=" * 50)
    
    # Create test customer images
    print("\n1. Creating test customer images...")
    test_image_paths = create_test_customer_images()
    
    # Initialize trio composite generator
    composites_dir = Path("Composites")
    if not composites_dir.exists():
        print(f"❌ Composites directory not found: {composites_dir}")
        return False
    
    trio_generator = TrioCompositeGenerator(composites_dir)
    
    # Test with different frame/matte combinations
    test_combinations = [
        ("Black", "White"),
        ("Cherry", "Gray"),
        ("Black", "Tan")
    ]
    
    print(f"\n2. Testing image visibility with different frames...")
    
    output_dir = Path("app/static/previews")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for frame_color, matte_color in test_combinations:
        print(f"\n  Testing {frame_color} frame with {matte_color} matte...")
        
        # Create composite with test images
        composite = trio_generator.create_composite(
            customer_images=test_image_paths,
            frame_color=frame_color,
            matte_color=matte_color,
            size="5x10"
        )
        
        if composite:
            print(f"    ✅ Composite created: {composite.size}")
            
            # Save full-size composite for inspection
            full_size_path = output_dir / f"visibility_test_{frame_color.lower()}_{matte_color.lower()}_full.jpg"
            composite.save(full_size_path, 'JPEG', quality=95)
            print(f"    📁 Full size saved: {full_size_path}")
            
            # Create scaled version for easier viewing
            scaled = trio_generator.scale_composite_for_preview(
                composite, 1200, 800, "5x10"
            )
            scaled_path = output_dir / f"visibility_test_{frame_color.lower()}_{matte_color.lower()}_scaled.jpg"
            scaled.save(scaled_path, 'JPEG', quality=95)
            print(f"    📁 Scaled version saved: {scaled_path}")
            
            # Analyze the result
            print(f"    🔍 Analysis:")
            print(f"       - Frame areas should show {frame_color} frame with {matte_color} matte")
            print(f"       - Opening 1 should show RED 'IMAGE 1' text")
            print(f"       - Opening 2 should show GREEN 'IMAGE 2' text")  
            print(f"       - Opening 3 should show BLUE 'IMAGE 3' text")
            
        else:
            print(f"    ❌ Failed to create composite")
            return False
    
    print(f"\n3. Creating comparison view...")
    
    # Create a comparison showing just the test images
    comparison = Image.new('RGB', (2400, 800), (240, 240, 240))
    
    # Show the test images side by side
    for i, img_path in enumerate(test_image_paths):
        test_img = Image.open(img_path)
        resized = test_img.resize((400, 500), Image.Resampling.LANCZOS)
        x = 200 + i * 600
        y = 150
        comparison.paste(resized, (x, y))
    
    comparison_path = output_dir / "test_images_comparison.jpg"
    comparison.save(comparison_path, 'JPEG', quality=95)
    print(f"    📁 Test images comparison: {comparison_path}")
    
    print(f"\n✅ Image visibility test completed!")
    print(f"\nTo verify the results:")
    print(f"  1. Check the generated composite images in: {output_dir}")
    print(f"  2. Look for the colored test images (RED, GREEN, BLUE) in the frame openings")
    print(f"  3. Compare with test_images_comparison.jpg to see the original test images")
    print(f"\nIf you see the colored images with text in the frame openings, the layering is working correctly!")
    
    return True


if __name__ == "__main__":
    print("Starting trio image visibility test...")
    success = test_trio_image_visibility()
    
    if success:
        print(f"\n🎉 Test completed! Check the output images to verify visibility.")
    else:
        print(f"\n❌ Test failed. Check the output above.")
    
    input("\nPress Enter to exit...") 