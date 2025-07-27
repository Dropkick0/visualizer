"""
Enhanced error handling for Portrait Preview Webapp.

Provides specific exception types for different failure modes
and better error context for debugging and user feedback.
"""

from typing import Dict, List, Optional, Any


class PortraitPreviewError(Exception):
    """Base exception for all Portrait Preview errors."""
    
    def __init__(self, message: str, details: Dict[str, Any] = None, suggestions: List[str] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.suggestions = suggestions or []
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'details': self.details,
            'suggestions': self.suggestions
        }


class ValidationError(PortraitPreviewError):
    """Raised when user input validation fails."""
    pass


class ConfigurationError(PortraitPreviewError):
    """Raised when configuration is invalid or missing."""
    pass


class ProcessingError(PortraitPreviewError):
    """Raised when processing pipeline fails."""
    pass


class OCRError(ProcessingError):
    """Raised when OCR processing fails."""
    pass


class ParsingError(ProcessingError):
    """Raised when text parsing fails."""
    pass


class ImageMappingError(ProcessingError):
    """Raised when image mapping fails."""
    pass


class RenderError(ProcessingError):
    """Raised when image rendering fails."""
    pass


class AssetError(RenderError):
    """Raised when required assets (frames, backgrounds) are missing."""
    pass


class CompositeError(RenderError):
    """Raised when image compositing fails."""
    pass


# Specific error classes for common failure modes

class NoItemsDetectedError(ParsingError):
    """Raised when no valid order items are found in the screenshot."""
    
    def __init__(self, ocr_confidence: float = None, lines_detected: int = None):
        super().__init__(
            "No valid order items detected in the screenshot",
            details={
                'ocr_confidence': ocr_confidence,
                'lines_detected': lines_detected
            },
            suggestions=[
                "Ensure the screenshot shows the PORTRAITS table clearly",
                "Check that the image has good contrast and is not blurry",
                "Verify the screenshot includes product names and quantities",
                "Try cropping the screenshot to focus on just the order table"
            ]
        )


class ImageFilesNotFoundError(ImageMappingError):
    """Raised when required image files cannot be found."""
    
    def __init__(self, missing_codes: List[str], search_path: str):
        super().__init__(
            f"Could not find image files for codes: {', '.join(missing_codes)}",
            details={
                'missing_codes': missing_codes,
                'search_path': search_path,
                'missing_count': len(missing_codes)
            },
            suggestions=[
                "Double-check the folder path for typos",
                "Ensure image files exist in the specified folder or subfolders",
                "Verify 4-digit codes match filename suffixes (e.g., IMG_1234.jpg)",
                "Check if files might be in a different folder or drive",
                "Ensure you have read access to the folder"
            ]
        )


class FrameAssetMissingError(AssetError):
    """Raised when required frame assets are missing."""
    
    def __init__(self, frame_style: str, product_type: str, asset_path: str):
        super().__init__(
            f"Frame asset not found: {frame_style} for {product_type}",
            details={
                'frame_style': frame_style,
                'product_type': product_type,
                'expected_path': asset_path
            },
            suggestions=[
                f"Ensure frame asset exists at: {asset_path}",
                "Check the frames.yaml configuration file",
                "Verify the assets directory path in settings.yaml",
                "Download missing frame assets from the design team"
            ]
        )


class BackgroundAssetMissingError(AssetError):
    """Raised when background assets are missing."""
    
    def __init__(self, background_name: str, asset_path: str):
        super().__init__(
            f"Background asset not found: {background_name}",
            details={
                'background_name': background_name,
                'expected_path': asset_path
            },
            suggestions=[
                f"Ensure background exists at: {asset_path}",
                "Check the assets/backgrounds directory",
                "Verify the assets directory path in settings.yaml",
                "Use a different background from the dropdown"
            ]
        )


class InsufficientDiskSpaceError(ProcessingError):
    """Raised when there's insufficient disk space for processing."""
    
    def __init__(self, required_mb: float, available_mb: float):
        super().__init__(
            f"Insufficient disk space: need {required_mb:.1f}MB, have {available_mb:.1f}MB",
            details={
                'required_mb': required_mb,
                'available_mb': available_mb,
                'shortfall_mb': required_mb - available_mb
            },
            suggestions=[
                "Free up disk space by deleting temporary files",
                "Clean up old preview sessions",
                "Move files to external storage",
                "Contact IT to increase disk space"
            ]
        )


class TesseractNotInstalledError(OCRError):
    """Raised when Tesseract OCR is not installed or not found."""
    
    def __init__(self, tesseract_path: str = None):
        super().__init__(
            "Tesseract OCR is not installed or not found in PATH",
            details={'tesseract_path': tesseract_path},
            suggestions=[
                "Install Tesseract OCR from https://github.com/tesseract-ocr/tesseract",
                "On Windows: Download and install the Windows installer",
                "On macOS: Run 'brew install tesseract'", 
                "On Ubuntu: Run 'sudo apt install tesseract-ocr'",
                "Ensure tesseract is in your system PATH"
            ]
        )


class InvalidImageFormatError(ValidationError):
    """Raised when uploaded image format is invalid."""
    
    def __init__(self, filename: str, detected_type: str = None):
        super().__init__(
            f"Invalid image format: {filename}",
            details={
                'filename': filename,
                'detected_type': detected_type
            },
            suggestions=[
                "Use JPG, PNG, or TIFF format images",
                "Convert the file to a supported format",
                "Ensure the file is not corrupted",
                "Try saving the screenshot again"
            ]
        )


class FileTooLargeError(ValidationError):
    """Raised when uploaded file exceeds size limit."""
    
    def __init__(self, filename: str, size_mb: float, limit_mb: float):
        super().__init__(
            f"File too large: {filename} ({size_mb:.1f}MB exceeds {limit_mb:.1f}MB limit)",
            details={
                'filename': filename,
                'size_mb': size_mb,
                'limit_mb': limit_mb
            },
            suggestions=[
                f"Reduce file size to under {limit_mb:.1f}MB",
                "Compress the image using image editing software",
                "Take a new screenshot at lower resolution",
                "Crop the screenshot to show only the essential parts"
            ]
        )


# Error recovery and diagnostics

def diagnose_ocr_failure(ocr_result, screenshot_path: str) -> Dict[str, Any]:
    """Analyze OCR failure and provide diagnostic information."""
    diagnostics = {
        'confidence_avg': getattr(ocr_result, 'confidence_avg', 0),
        'lines_detected': len(getattr(ocr_result, 'lines', [])),
        'words_detected': len(getattr(ocr_result, 'words', [])),
        'screenshot_exists': screenshot_path and os.path.exists(screenshot_path),
        'likely_causes': [],
        'recommendations': []
    }
    
    # Analyze potential causes
    if diagnostics['confidence_avg'] < 30:
        diagnostics['likely_causes'].append("Low OCR confidence - image quality issues")
        diagnostics['recommendations'].append("Improve image quality: increase contrast, reduce blur")
    
    if diagnostics['lines_detected'] < 5:
        diagnostics['likely_causes'].append("Too few text lines detected")
        diagnostics['recommendations'].append("Ensure screenshot shows the full PORTRAITS table")
    
    if diagnostics['words_detected'] < 10:
        diagnostics['likely_causes'].append("Minimal text detected")
        diagnostics['recommendations'].append("Check that screenshot is not mostly blank or corrupted")
    
    return diagnostics


def create_error_recovery_suggestions(error: Exception, context: Dict[str, Any] = None) -> List[str]:
    """Generate contextual recovery suggestions for any error."""
    suggestions = []
    
    if isinstance(error, PortraitPreviewError):
        suggestions.extend(error.suggestions)
    
    # Add context-specific suggestions
    if context:
        if context.get('ocr_confidence', 100) < 50:
            suggestions.append("Try adjusting the screenshot crop or lighting")
        
        if context.get('missing_images_count', 0) > 0:
            suggestions.append("Verify the customer folder path and image file names")
        
        if context.get('render_failures', 0) > 0:
            suggestions.append("Check that frame and background assets are available")
    
    # Generic fallback suggestions
    if not suggestions:
        suggestions = [
            "Try uploading a different screenshot",
            "Check that all required files and folders exist",
            "Contact support if the problem persists"
        ]
    
    return suggestions


import os 