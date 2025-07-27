"""
Unit tests for the enhanced error handling system.

Tests custom exception classes, error context, suggestions,
and diagnostic functions.
"""

import pytest
from app.errors import (
    PortraitPreviewError, ValidationError, ProcessingError,
    NoItemsDetectedError, ImageFilesNotFoundError, FrameAssetMissingError,
    BackgroundAssetMissingError, TesseractNotInstalledError,
    InvalidImageFormatError, FileTooLargeError, InsufficientDiskSpaceError,
    diagnose_ocr_failure, create_error_recovery_suggestions
)


class TestPortraitPreviewError:
    """Test the base PortraitPreviewError class."""
    
    def test_basic_error_creation(self):
        """Test creating a basic error with message only."""
        error = PortraitPreviewError("Test error message")
        
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.details == {}
        assert error.suggestions == []
    
    def test_error_with_details_and_suggestions(self):
        """Test creating an error with details and suggestions."""
        details = {'file_path': '/test/path', 'line_number': 42}
        suggestions = ['Try this', 'Or try that']
        
        error = PortraitPreviewError("Test error", details=details, suggestions=suggestions)
        
        assert error.details == details
        assert error.suggestions == suggestions
    
    def test_error_to_dict(self):
        """Test converting error to dictionary."""
        details = {'key': 'value'}
        suggestions = ['suggestion']
        error = PortraitPreviewError("Test", details=details, suggestions=suggestions)
        
        result = error.to_dict()
        
        assert result['error_type'] == 'PortraitPreviewError'
        assert result['message'] == 'Test'
        assert result['details'] == details
        assert result['suggestions'] == suggestions


class TestSpecificErrorTypes:
    """Test specific error type implementations."""
    
    def test_no_items_detected_error(self):
        """Test NoItemsDetectedError creation and content."""
        error = NoItemsDetectedError(ocr_confidence=25.5, lines_detected=3)
        
        assert "No valid order items detected" in str(error)
        assert error.details['ocr_confidence'] == 25.5
        assert error.details['lines_detected'] == 3
        assert len(error.suggestions) > 0
        assert any("screenshot" in s.lower() for s in error.suggestions)
    
    def test_image_files_not_found_error(self):
        """Test ImageFilesNotFoundError creation and content."""
        missing_codes = ['1234', '5678', '9999']
        search_path = '/test/customer/folder'
        
        error = ImageFilesNotFoundError(missing_codes, search_path)
        
        assert "Could not find image files" in str(error)
        assert "1234, 5678, 9999" in str(error)
        assert error.details['missing_codes'] == missing_codes
        assert error.details['search_path'] == search_path
        assert error.details['missing_count'] == 3
        assert len(error.suggestions) > 0
    
    def test_frame_asset_missing_error(self):
        """Test FrameAssetMissingError creation and content."""
        error = FrameAssetMissingError('cherry', 'trio', '/assets/frames/cherry_trio.png')
        
        assert "Frame asset not found" in str(error)
        assert "cherry" in str(error)
        assert "trio" in str(error)
        assert error.details['frame_style'] == 'cherry'
        assert error.details['product_type'] == 'trio'
        assert error.details['expected_path'] == '/assets/frames/cherry_trio.png'
    
    def test_background_asset_missing_error(self):
        """Test BackgroundAssetMissingError creation and content."""
        error = BackgroundAssetMissingError('test_bg.jpg', '/assets/backgrounds/test_bg.jpg')
        
        assert "Background asset not found" in str(error)
        assert "test_bg.jpg" in str(error)
        assert error.details['background_name'] == 'test_bg.jpg'
        assert error.details['expected_path'] == '/assets/backgrounds/test_bg.jpg'
    
    def test_tesseract_not_installed_error(self):
        """Test TesseractNotInstalledError creation and content."""
        error = TesseractNotInstalledError('/usr/bin/tesseract')
        
        assert "Tesseract OCR is not installed" in str(error)
        assert error.details['tesseract_path'] == '/usr/bin/tesseract'
        assert len(error.suggestions) > 0
        assert any("install" in s.lower() for s in error.suggestions)
    
    def test_invalid_image_format_error(self):
        """Test InvalidImageFormatError creation and content."""
        error = InvalidImageFormatError('test.txt', 'text/plain')
        
        assert "Invalid image format" in str(error)
        assert "test.txt" in str(error)
        assert error.details['filename'] == 'test.txt'
        assert error.details['detected_type'] == 'text/plain'
    
    def test_file_too_large_error(self):
        """Test FileTooLargeError creation and content."""
        error = FileTooLargeError('huge_file.jpg', 25.5, 20.0)
        
        assert "File too large" in str(error)
        assert "25.5MB" in str(error)
        assert "20.0MB" in str(error)
        assert error.details['size_mb'] == 25.5
        assert error.details['limit_mb'] == 20.0
    
    def test_insufficient_disk_space_error(self):
        """Test InsufficientDiskSpaceError creation and content."""
        error = InsufficientDiskSpaceError(100.0, 50.0)
        
        assert "Insufficient disk space" in str(error)
        assert "100.0MB" in str(error)
        assert "50.0MB" in str(error)
        assert error.details['required_mb'] == 100.0
        assert error.details['available_mb'] == 50.0
        assert error.details['shortfall_mb'] == 50.0


class TestDiagnosticFunctions:
    """Test error diagnostic and recovery functions."""
    
    def test_diagnose_ocr_failure_low_confidence(self):
        """Test OCR failure diagnosis with low confidence."""
        class MockOCRResult:
            confidence_avg = 15.0
            lines = ['line1', 'line2']
            words = ['word1', 'word2', 'word3']
        
        result = MockOCRResult()
        diagnostics = diagnose_ocr_failure(result, '/test/screenshot.png')
        
        assert diagnostics['confidence_avg'] == 15.0
        assert diagnostics['lines_detected'] == 2
        assert diagnostics['words_detected'] == 3
        assert len(diagnostics['likely_causes']) > 0
        assert len(diagnostics['recommendations']) > 0
        assert any("confidence" in cause.lower() for cause in diagnostics['likely_causes'])
    
    def test_diagnose_ocr_failure_few_lines(self):
        """Test OCR failure diagnosis with too few lines detected."""
        class MockOCRResult:
            confidence_avg = 85.0
            lines = ['line1']  # Too few lines
            words = ['word1', 'word2']
        
        result = MockOCRResult()
        diagnostics = diagnose_ocr_failure(result, '/test/screenshot.png')
        
        assert "few text lines" in ' '.join(diagnostics['likely_causes']).lower()
        assert any("table" in rec.lower() for rec in diagnostics['recommendations'])
    
    def test_diagnose_ocr_failure_few_words(self):
        """Test OCR failure diagnosis with minimal text detected."""
        class MockOCRResult:
            confidence_avg = 85.0
            lines = ['line1', 'line2', 'line3', 'line4', 'line5']
            words = ['word1']  # Too few words
        
        result = MockOCRResult()
        diagnostics = diagnose_ocr_failure(result, '/test/screenshot.png')
        
        assert "minimal text" in ' '.join(diagnostics['likely_causes']).lower()
    
    def test_create_error_recovery_suggestions_with_portrait_error(self):
        """Test recovery suggestions for PortraitPreviewError."""
        error = NoItemsDetectedError(ocr_confidence=25.0)
        suggestions = create_error_recovery_suggestions(error)
        
        # Should include the error's built-in suggestions
        assert len(suggestions) > 0
        assert any("screenshot" in s.lower() for s in suggestions)
    
    def test_create_error_recovery_suggestions_with_context(self):
        """Test recovery suggestions with context information."""
        error = ProcessingError("Test error")
        context = {
            'ocr_confidence': 25.0,
            'missing_images_count': 5,
            'render_failures': 2
        }
        
        suggestions = create_error_recovery_suggestions(error, context)
        
        assert len(suggestions) > 0
        # Should include context-specific suggestions
        assert any("screenshot" in s.lower() for s in suggestions)
        assert any("folder" in s.lower() for s in suggestions)
        assert any("assets" in s.lower() for s in suggestions)
    
    def test_create_error_recovery_suggestions_generic(self):
        """Test recovery suggestions for generic exceptions."""
        error = Exception("Generic error")
        suggestions = create_error_recovery_suggestions(error)
        
        # Should provide generic fallback suggestions
        assert len(suggestions) > 0
        assert any("try" in s.lower() for s in suggestions)
    
    def test_create_error_recovery_suggestions_empty_context(self):
        """Test recovery suggestions with empty context."""
        error = ProcessingError("Test error")
        suggestions = create_error_recovery_suggestions(error, {})
        
        assert len(suggestions) > 0


class TestErrorInheritance:
    """Test error class inheritance and polymorphism."""
    
    def test_validation_error_inheritance(self):
        """Test ValidationError inherits from PortraitPreviewError."""
        error = ValidationError("Validation failed")
        
        assert isinstance(error, PortraitPreviewError)
        assert isinstance(error, ValidationError)
    
    def test_processing_error_inheritance(self):
        """Test ProcessingError inherits from PortraitPreviewError."""
        error = ProcessingError("Processing failed")
        
        assert isinstance(error, PortraitPreviewError)
        assert isinstance(error, ProcessingError)
    
    def test_specific_error_inheritance(self):
        """Test specific errors inherit from appropriate base classes."""
        # NoItemsDetectedError should inherit from ParsingError
        error = NoItemsDetectedError()
        assert isinstance(error, PortraitPreviewError)
        
        # InvalidImageFormatError should inherit from ValidationError
        error = InvalidImageFormatError("test.txt")
        assert isinstance(error, ValidationError)
        assert isinstance(error, PortraitPreviewError)
    
    def test_error_handling_polymorphism(self):
        """Test that all errors can be handled polymorphically."""
        errors = [
            ValidationError("Validation error"),
            ProcessingError("Processing error"),
            NoItemsDetectedError(),
            ImageFilesNotFoundError(['1234'], '/test'),
            TesseractNotInstalledError()
        ]
        
        for error in errors:
            # All should be PortraitPreviewError instances
            assert isinstance(error, PortraitPreviewError)
            
            # All should have required attributes
            assert hasattr(error, 'message')
            assert hasattr(error, 'details')
            assert hasattr(error, 'suggestions')
            
            # All should be convertible to dict
            error_dict = error.to_dict()
            assert 'error_type' in error_dict
            assert 'message' in error_dict
            assert 'details' in error_dict
            assert 'suggestions' in error_dict 