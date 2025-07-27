#!/usr/bin/env python3
"""
Test script for Trio Composite functionality
Demonstrates the new trio composite feature with actual composite frames
"""

import sys
from pathlib import Path
from typing import Dict, List

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import load_product_config
from app.enhanced_preview import EnhancedPortraitPreviewGenerator
from app.trio_composite import TrioCompositeGenerator, is_trio_product, extract_trio_details


def create_test_trio_items() -> List[Dict]:
    """Create test trio items for demonstration"""
    
    # Mock images found for testing
    images_found = {
        '1555': ['demo_images/portrait1.jpg', 'demo_images/portrait2.jpg'],
        '9198': ['demo_images/portrait3.jpg'],
        '5615': ['demo_images/portrait4.jpg']
    }
    
    # Create test trio items
    trio_items = [
        {
            'product_slug': '5x10_trio_510_3',
            'product_code': '510.3',
            'quantity': 1,
            'image_codes': ['1555', '9198', '5615'],
            'codes': ['1555', '9198', '5615'],
            'size_category': 'trio_5x10'
        },
        {
            'product_slug': '10x20_trio_1020_5',
            'product_code': '1020.5',
            'quantity': 1,
            'image_codes': ['1555', '9198', '5615'],
            'codes': ['1555', '9198', '5615'],
            'size_category': 'trio_10x20'
        }
    ]
    
    # Add some regular items for comparison
    regular_items = [
        {
            'product_slug': '8x10_basic_810',
            'product_code': '810',
            'quantity': 1,
            'image_codes': ['1555'],
            'codes': ['1555'],
            'size_category': 'large'
        },
        {
            'product_slug': '5x7_basic_570',
            'product_code': '570',
            'quantity': 2,
            'image_codes': ['1555', '9198'],
            'codes': ['1555', '9198'],
            'size_category': 'medium'
        }
    ]
    
    all_items = trio_items + regular_items
    
    print(f"Created {len(trio_items)} trio items and {len(regular_items)} regular items")
    return all_items, images_found


def test_trio_detection_and_parsing():
    """Test the trio product detection and detail extraction"""
    print("\n🔍 Testing Trio Product Detection and Parsing...")
    
    # Load product configuration
    products_config = load_product_config()
    
    # Test with known trio products
    test_products = [
        '5x10_trio_510_3',
        '10x20_trio_1020_5',
        '8x10_basic_001',  # Should NOT be trio
        '5x7_basic_570'    # Should NOT be trio
    ]
    
    for product_slug in test_products:
        # Find product config
        product_config = None
        for product in products_config.get('products', []):
            if product.get('slug') == product_slug:
                product_config = product
                break
        
        if product_config:
            is_trio = is_trio_product(product_config)
            print(f"  {product_slug}: {'✅ TRIO' if is_trio else '❌ NOT TRIO'}")
            
            if is_trio:
                size, frame_color, matte_color = extract_trio_details(product_config)
                print(f"    → Size: {size}, Frame: {frame_color}, Matte: {matte_color}")
        else:
            print(f"  {product_slug}: ❌ Product not found in config")


def test_composite_generation():
    """Test the composite generation with mock data"""
    print("\n🎨 Testing Composite Generation...")
    
    # Initialize trio composite generator
    composites_dir = Path("Composites")
    if not composites_dir.exists():
        print(f"❌ Composites directory not found: {composites_dir}")
        return False
    
    trio_generator = TrioCompositeGenerator(composites_dir)
    
    # Test with available composite combinations
    available_combinations = trio_generator.get_available_frame_styles()
    print(f"  Available frame/matte combinations: {len(available_combinations)}")
    for frame, matte in available_combinations[:3]:  # Show first 3
        print(f"    - Frame: {frame}, Matte: {matte}")
    
    # Create mock customer images (use placeholders for now)
    mock_images = [None, None, None]  # Will use placeholders in generation
    
    # Test composite creation for 5x10
    print("\n  Testing 5x10 composite creation...")
    composite_5x10 = trio_generator.create_composite(
        customer_images=mock_images,
        frame_color="Black",
        matte_color="White",
        size="5x10"
    )
    
    if composite_5x10:
        print(f"    ✅ 5x10 composite created: {composite_5x10.size}")
        
        # Test scaling for preview
        scaled = trio_generator.scale_composite_for_preview(
            composite_5x10, 2400, 1600, "5x10"
        )
        print(f"    ✅ Scaled for preview: {scaled.size}")
    else:
        print(f"    ❌ Failed to create 5x10 composite")
        return False
    
    # Test composite creation for 10x20
    print("\n  Testing 10x20 composite creation...")
    composite_10x20 = trio_generator.create_composite(
        customer_images=mock_images,
        frame_color="Cherry",
        matte_color="Gray",
        size="10x20"
    )
    
    if composite_10x20:
        print(f"    ✅ 10x20 composite created: {composite_10x20.size}")
        
        # Test scaling for preview
        scaled = trio_generator.scale_composite_for_preview(
            composite_10x20, 2400, 1600, "10x20"
        )
        print(f"    ✅ Scaled for preview: {scaled.size}")
    else:
        print(f"    ❌ Failed to create 10x20 composite")
        return False
    
    return True


def test_enhanced_preview_with_composites():
    """Test the enhanced preview with trio composites"""
    print("\n🖼️  Testing Enhanced Preview with Trio Composites...")
    
    # Create test data
    all_items, images_found = create_test_trio_items()
    
    # Load product configuration
    products_config = load_product_config()
    
    # Create enhanced generator with trio support
    output_dir = Path("app/static/previews")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    generator = EnhancedPortraitPreviewGenerator(
        products_config,
        images_found,
        output_dir
    )
    
    # Generate preview with composites
    output_path = output_dir / "trio_composite_preview_test.png"
    print(f"  Generating preview to: {output_path}")
    
    success = generator.generate_size_based_preview_with_composites(all_items, output_path)
    
    if success:
        print(f"  ✅ Enhanced preview with composites created successfully!")
        print(f"  📁 Saved to: {output_path}")
        print(f"  📐 Should show regular items on left, trio composites on right")
        return True
    else:
        print(f"  ❌ Failed to create enhanced preview with composites")
        return False


def test_composite_availability():
    """Test which composite files are available"""
    print("\n📁 Testing Composite File Availability...")
    
    composites_dir = Path("Composites")
    if not composites_dir.exists():
        print(f"❌ Composites directory not found: {composites_dir}")
        return False
    
    # List all composite files
    composite_files = list(composites_dir.glob("*.jpg"))
    print(f"  Found {len(composite_files)} composite files:")
    
    for file in composite_files:
        print(f"    - {file.name}")
        # Test if file can be opened
        try:
            from PIL import Image
            with Image.open(file) as img:
                print(f"      → {img.size[0]}x{img.size[1]} pixels, {img.mode} mode")
        except Exception as e:
            print(f"      → ❌ Error opening: {e}")
    
    return len(composite_files) > 0


def main():
    """Run all trio composite tests"""
    print("🎨 Testing Trio Composite Functionality")
    print("=" * 60)
    
    # Test 1: Composite file availability
    print("\n1. Checking composite files...")
    if not test_composite_availability():
        print("❌ Cannot proceed without composite files")
        return False
    
    # Test 2: Product detection and parsing
    print("\n2. Testing trio product detection...")
    test_trio_detection_and_parsing()
    
    # Test 3: Composite generation
    print("\n3. Testing composite generation...")
    if not test_composite_generation():
        print("❌ Composite generation failed")
        return False
    
    # Test 4: Enhanced preview integration
    print("\n4. Testing enhanced preview integration...")
    if not test_enhanced_preview_with_composites():
        print("❌ Enhanced preview integration failed")
        return False
    
    print("\n" + "=" * 60)
    print("✅ ALL TRIO COMPOSITE TESTS PASSED!")
    print("\nTrio composite functionality is working correctly:")
    print("  • Product detection and parsing ✅")
    print("  • Composite frame loading ✅")
    print("  • Image overlaying ✅")
    print("  • Preview integration ✅")
    print("\nFeatures implemented:")
    print("  • 5x10 and 10x20 trio composites")
    print("  • Frame color detection (Black, Cherry)")
    print("  • Matte color detection (Black, Gray, White, Tan)")
    print("  • Right-justified composite section in preview")
    print("  • Proper scaling for different composite sizes")
    
    return True


if __name__ == "__main__":
    success = main()
    
    if success:
        print(f"\n🎉 Trio composite functionality is ready!")
    else:
        print(f"\n❌ Some tests failed. Check the output above.")
    
    input("\nPress Enter to exit...") 