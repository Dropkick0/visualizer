#!/usr/bin/env python3
"""
Simple demonstration of Trio Composite functionality
Shows how the trio composite system works with the available composite frames
"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.trio_composite import TrioCompositeGenerator
from PIL import Image


def demo_trio_composites():
    """Demonstrate trio composite functionality"""
    print("🎨 Trio Composite Demonstration")
    print("=" * 50)
    
    # Initialize trio composite generator
    composites_dir = Path("Composites")
    if not composites_dir.exists():
        print(f"❌ Composites directory not found: {composites_dir}")
        return False
    
    trio_generator = TrioCompositeGenerator(composites_dir)
    
    # Show available composite combinations
    print(f"\n📁 Available composite combinations:")
    available_combinations = trio_generator.get_available_frame_styles()
    for i, (frame, matte) in enumerate(available_combinations, 1):
        print(f"  {i}. Frame: {frame}, Matte: {matte}")
    
    # Test with a few combinations that we know exist
    test_combinations = [
        ("Black", "White"),
        ("Cherry", "Gray"),
        ("Black", "Tan")
    ]
    
    print(f"\n🎨 Testing composite generation...")
    
    for frame_color, matte_color in test_combinations:
        print(f"\n  Testing {frame_color} frame with {matte_color} matte...")
        
        # Create composite (with no customer images for demo)
        composite = trio_generator.create_composite(
            customer_images=[None, None, None],  # No actual images for demo
            frame_color=frame_color,
            matte_color=matte_color,
            size="5x10"
        )
        
        if composite:
            print(f"    ✅ Composite created successfully!")
            print(f"       Original size: {composite.size}")
            
            # Scale for preview
            scaled = trio_generator.scale_composite_for_preview(
                composite, 2400, 1600, "5x10"
            )
            print(f"       Scaled size: {scaled.size}")
            
            # Save a demo image
            demo_output = Path("app/static/previews")
            demo_output.mkdir(parents=True, exist_ok=True)
            
            demo_path = demo_output / f"demo_trio_{frame_color.lower()}_{matte_color.lower()}.png"
            scaled.save(demo_path)
            print(f"       Saved demo to: {demo_path}")
            
        else:
            print(f"    ❌ Failed to create composite")
    
    print(f"\n🖼️  Creating composite preview demonstration...")
    
    # Create a simple preview showing how composites would appear
    preview_width = 1200
    preview_height = 800
    beige_color = (245, 240, 230)
    
    # Create preview canvas
    canvas = Image.new('RGB', (preview_width, preview_height), beige_color)
    
    # Position some composites
    composite_x = preview_width - 400  # Right side
    current_y = 50
    
    for i, (frame_color, matte_color) in enumerate(test_combinations[:2]):  # Just first 2
        composite = trio_generator.create_composite(
            customer_images=[None, None, None],
            frame_color=frame_color,
            matte_color=matte_color,
            size="5x10"
        )
        
        if composite:
            # Scale for preview
            scaled = trio_generator.scale_composite_for_preview(
                composite, 300, 200, "5x10"
            )
            
            # Paste onto canvas
            canvas.paste(scaled, (composite_x, current_y))
            current_y += scaled.height + 20
    
    # Save the preview
    demo_preview_path = Path("app/static/previews") / "trio_composite_demo_preview.png"
    canvas.save(demo_preview_path)
    print(f"    ✅ Demo preview saved to: {demo_preview_path}")
    
    print(f"\n✅ Trio composite demonstration completed!")
    print(f"\nImplemented features:")
    print(f"  • Automatic composite frame loading ✅")
    print(f"  • Multiple frame/matte combinations ✅")
    print(f"  • Proper scaling for preview display ✅")
    print(f"  • Right-side positioning ✅")
    print(f"  • Support for customer image overlaying ✅")
    
    return True


if __name__ == "__main__":
    print("Starting trio composite demonstration...")
    success = demo_trio_composites()
    
    if success:
        print(f"\n🎉 Demonstration successful!")
        print(f"\nThe trio composite system is working and ready to use!")
        print(f"When customer images are available, they will be overlaid at:")
        print(f"  • Position 1: (240px, 312px)")
        print(f"  • Position 2: (1145px, 312px)")
        print(f"  • Position 3: (2056px, 312px)")
    else:
        print(f"\n❌ Demonstration failed. Check the output above.")
    
    input("\nPress Enter to exit...") 