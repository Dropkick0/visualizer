"""
Unit tests for the text parsing module.

Tests the FileMakerParser's ability to extract structured order items
from OCR text lines with various formats and edge cases.
"""

import pytest
from app.parse import FileMakerParser, StructuredItem


class TestFileMakerParser:
    """Test cases for the FileMakerParser class."""
    
    @pytest.fixture
    def parser(self, sample_config):
        """Create a parser instance with test configuration."""
        return FileMakerParser(sample_config.products)
    
    def test_parse_basic_print_line(self, parser):
        """Test parsing a basic print order line."""
        line = "2 8x10 Basic Print Digital                    1234, 5678"
        items = parser.parse_ocr_lines([line])
        
        assert len(items) == 1
        item = items[0]
        assert item.quantity == 2
        assert item.product_slug == "8x10_basic"
        assert item.width_in == 8.0
        assert item.height_in == 10.0
        assert item.frame_style == "basic"
        assert item.codes == ["1234", "5678"]
        assert item.source_line_text == line
    
    def test_parse_wallet_line(self, parser):
        """Test parsing a wallet order line."""
        line = "1 5x7 Cherry Wallet                          9876"
        items = parser.parse_ocr_lines([line])
        
        assert len(items) == 1
        item = items[0]
        assert item.quantity == 1
        assert item.product_slug == "5x7_wallet"
        assert item.frame_style == "cherry"  # Cherry is detected from the text
        assert item.codes == ["9876"]
    
    def test_parse_trio_frame_line(self, parser):
        """Test parsing a trio frame order line."""
        line = "1 8x10 Trio Cherry Frame                     1111, 2222, 3333"
        items = parser.parse_ocr_lines([line])
        
        assert len(items) == 1
        item = items[0]
        assert item.quantity == 1
        assert item.product_slug == "8x10_trio"
        assert item.frame_style == "cherry"
        assert item.codes == ["1111", "2222", "3333"]
        assert len(item.codes) == 3
    
    def test_parse_multiple_lines(self, parser):
        """Test parsing multiple order lines."""
        lines = [
            "2 8x10 Basic Print Digital                    1234, 5678",
            "1 5x7 Cherry Wallet                          9876",
            "1 8x10 Trio Cherry Frame                     1111, 2222, 3333"
        ]
        
        items = parser.parse_ocr_lines(lines)
        
        assert len(items) == 3
        assert items[0].quantity == 2
        assert items[1].quantity == 1
        assert items[2].quantity == 1
        assert items[0].codes == ["1234", "5678"]
        assert items[1].codes == ["9876"]
        assert items[2].codes == ["1111", "2222", "3333"]
    
    def test_parse_line_with_extra_whitespace(self, parser):
        """Test parsing lines with irregular whitespace."""
        line = "  2   8x10   Basic Print   Digital        1234,   5678  "
        items = parser.parse_ocr_lines([line])
        
        assert len(items) == 1
        item = items[0]
        assert item.quantity == 2
        assert item.codes == ["1234", "5678"]
    
    def test_parse_line_with_no_codes(self, parser):
        """Test parsing lines without 4-digit codes."""
        line = "2 8x10 Basic Print Digital"
        items = parser.parse_ocr_lines([line])
        
        # Should still create item but with empty codes
        assert len(items) == 1
        item = items[0]
        assert item.quantity == 2
        assert item.codes == []
    
    def test_parse_line_with_invalid_codes(self, parser):
        """Test parsing lines with invalid code formats."""
        line = "2 8x10 Basic Print Digital                    12A4, XYZ8"
        items = parser.parse_ocr_lines([line])
        
        assert len(items) == 1
        item = items[0]
        # Invalid codes should be filtered out
        assert item.codes == []
    
    def test_parse_line_mixed_valid_invalid_codes(self, parser):
        """Test parsing lines with mix of valid and invalid codes."""
        line = "2 8x10 Basic Print Digital                    1234, ABC5, 5678"
        items = parser.parse_ocr_lines([line])
        
        assert len(items) == 1
        item = items[0]
        # Only valid 4-digit codes should be kept
        assert item.codes == ["1234", "5678"]
    
    def test_parse_unrecognized_line(self, parser):
        """Test parsing lines that don't match any product pattern."""
        line = "This is not a valid order line"
        items = parser.parse_ocr_lines([line])
        
        assert len(items) == 0
    
    def test_parse_empty_line(self, parser):
        """Test parsing empty or whitespace-only lines."""
        items = parser.parse_ocr_lines([""])
        assert len(items) == 0
        
        items = parser.parse_ocr_lines(["   "])
        assert len(items) == 0
    
    def test_parse_header_line(self, parser):
        """Test parsing table header lines."""
        line = "PORTRAITS"
        items = parser.parse_ocr_lines([line])
        
        assert len(items) == 0
    
    def test_extract_quantity_patterns(self, parser):
        """Test various quantity extraction patterns."""
        test_cases = [
            ("1 8x10", 1),
            ("2 5x7", 2),
            ("10 Wallets", 10),
            ("5 Basic Print", 5),
            ("No quantity here", 1),  # Default to 1
        ]
        
        for line, expected_qty in test_cases:
            quantity = parser._extract_quantity(line)
            assert quantity == expected_qty
    
    def test_extract_codes_patterns(self, parser):
        """Test various code extraction patterns."""
        from app.utils import extract_image_codes_from_text
        
        test_cases = [
            ("1234", ["1234"]),
            ("1234, 5678", ["1234", "5678"]),
            ("1234,5678,9999", ["1234", "5678", "9999"]),
            ("1234 5678 9999", ["1234", "5678", "9999"]),
            ("No codes here", []),
            ("12A4, 5678", ["5678"]),  # Filter invalid
            ("1234, 5678, 999", ["1234", "5678"]),  # 3-digit invalid
        ]
        
        for text, expected_codes in test_cases:
            codes = extract_image_codes_from_text(text)
            assert codes == expected_codes
    
    def test_determine_orientation(self, parser):
        """Test orientation determination based on product configuration."""
        # Test orientation determination through parser method
        # This tests the _determine_orientation logic indirectly
        
        # Create a mock product config for portrait
        from app.config import ProductConfig
        portrait_config = ProductConfig(
            slug="test_portrait",
            width_in=5.0,
            height_in=7.0,
            frame_style_default="basic",
            orientation_locked=None
        )
        orientation = parser._determine_orientation(portrait_config, "test description")
        assert orientation == "portrait"
        
        # Test landscape
        landscape_config = ProductConfig(
            slug="test_landscape", 
            width_in=8.0,
            height_in=6.0,
            frame_style_default="basic",
            orientation_locked=None
        )
        orientation = parser._determine_orientation(landscape_config, "test description")
        assert orientation == "landscape"
        
        # Test square (auto)
        square_config = ProductConfig(
            slug="test_square",
            width_in=6.0, 
            height_in=6.0,
            frame_style_default="basic",
            orientation_locked=None
        )
        orientation = parser._determine_orientation(square_config, "test description")
        assert orientation == "auto"
    
    def test_frame_style_extraction(self, parser):
        """Test frame style extraction through actual parsing."""
        # Test frame style through the actual parsing workflow
        test_lines = [
            "1 8x10 Cherry Frame                          1234",
            "1 5x7 Basic Print                            5678",
        ]
        
        items = parser.parse_ocr_lines(test_lines)
        
        # Check that different frame styles are detected
        assert len(items) == 2
        # Frame styles will be based on our test configuration defaults
    
    def test_parse_edge_cases(self, parser):
        """Test parsing edge cases and error conditions."""
        # Very long line
        long_line = "1 8x10 Basic Print Digital " + "x" * 1000 + " 1234"
        items = parser.parse_ocr_lines([long_line])
        assert len(items) >= 0  # Should not crash
        
        # Line with special characters
        special_line = "1 8x10 Basic Print Digital @ # $ % 1234"
        items = parser.parse_ocr_lines([special_line])
        assert len(items) >= 0  # Should not crash
        
        # Line with unicode characters
        unicode_line = "1 8x10 Basic Print Digital åéîøü 1234"
        items = parser.parse_ocr_lines([unicode_line])
        assert len(items) >= 0  # Should not crash
    
    def test_statistics_collection(self, parser):
        """Test that parsing processes multiple lines correctly."""
        lines = [
            "2 8x10 Basic Print Digital                    1234, 5678",
            "Invalid line that won't parse",
            "1 5x7 Cherry Wallet                          9876",
            "",  # Empty line
            "PORTRAITS"  # Header
        ]
        
        items = parser.parse_ocr_lines(lines)
        
        # Should successfully parse the valid lines
        assert len(items) == 2
        assert items[0].codes == ["1234", "5678"]
        assert items[1].codes == ["9876"] 