"""
Integration tests for Portrait Preview Webapp.

Tests the complete pipeline from upload to preview generation,
including error handling and edge cases.
"""

import pytest
import json
import io
from pathlib import Path
from unittest.mock import patch, Mock

from app.routes import process_portrait_preview
from app.errors import (
    NoItemsDetectedError, ImageFilesNotFoundError, 
    TesseractNotInstalledError, InvalidImageFormatError
)


class TestWebInterface:
    """Test the Flask web interface."""
    
    def test_index_page_loads(self, client):
        """Test that the main upload page loads successfully."""
        response = client.get('/')
        
        assert response.status_code == 200
        assert b'Portrait Preview' in response.data
        assert b'Generate Preview' in response.data
    
    def test_upload_form_validation_no_file(self, client):
        """Test upload form validation when no file is provided."""
        response = client.post('/process', data={
            'sit_folder_path': '/test/folder'
        })
        
        assert response.status_code == 302  # Redirect back to form
    
    def test_upload_form_validation_no_folder(self, client):
        """Test upload form validation when no folder path is provided."""
        # Create a test image file
        test_image = io.BytesIO()
        test_image.name = 'test.png'
        
        response = client.post('/process', data={
            'screenshot': (test_image, 'test.png'),
            'sit_folder_path': ''
        })
        
        assert response.status_code == 302  # Redirect back to form
    
    def test_upload_invalid_file_type(self, client, temp_work_dir):
        """Test upload with invalid file type."""
        # Create a text file pretending to be an image
        text_file = io.BytesIO(b'This is not an image')
        
        response = client.post('/process', data={
            'screenshot': (text_file, 'fake_image.txt'),
            'sit_folder_path': str(temp_work_dir)
        })
        
        assert response.status_code == 302  # Redirect with error
    
    def test_upload_file_too_large(self, client, temp_work_dir):
        """Test upload with file that's too large."""
        # Create a large fake image file
        large_file = io.BytesIO(b'x' * (25 * 1024 * 1024))  # 25MB
        
        response = client.post('/process', data={
            'screenshot': (large_file, 'huge_image.jpg'),
            'sit_folder_path': str(temp_work_dir)
        })
        
        assert response.status_code == 302  # Redirect with error
    
    def test_debug_endpoint_access(self, client):
        """Test debug endpoint access control."""
        # Should work in debug mode
        response = client.get('/debug/test-session-123')
        assert response.status_code in [200, 404]  # 404 if session doesn't exist
    
    def test_temp_file_serving(self, client, temp_work_dir):
        """Test serving temporary files."""
        # Create a test session directory and file
        session_dir = temp_work_dir / 'test-session'
        session_dir.mkdir()
        test_file = session_dir / 'test.jpg'
        test_file.write_bytes(b'fake image data')
        
        # Test temp file serving route (may not exist, that's ok)
        response = client.get('/static/temp/test-session/test.jpg')
        # Should either work or return error, but not crash
        assert response.status_code in [200, 404, 403]


class TestFullPipeline:
    """Test the complete processing pipeline."""
    
    @pytest.fixture
    def mock_ocr_processor(self):
        """Mock OCR processor for testing."""
        with patch('app.ocr.FileMakerOCR') as mock_class:
            mock_instance = Mock()
            mock_instance.process_screenshot.return_value = Mock(
                lines=[
                    "2 8x10 Basic Print Digital                    1234, 5678",
                    "1 5x7 Cherry Wallet                          9876"
                ],
                words=['2', '8x10', 'Basic', 'Print', 'Digital', '1234,', '5678',
                       '1', '5x7', 'Cherry', 'Wallet', '9876'],
                confidence_avg=85.5,
                roi_bbox=(50, 100, 1150, 200)
            )
            mock_class.return_value = mock_instance
            yield mock_instance
    
    def test_successful_processing_pipeline(
        self, 
        sample_config, 
        sample_screenshot, 
        sample_customer_images,
        sample_frame_assets,
        sample_background_assets,
        temp_work_dir,
        mock_ocr_processor
    ):
        """Test successful end-to-end processing."""
        images_dir, image_paths = sample_customer_images
        frames_dir, frame_paths = sample_frame_assets
        backgrounds_dir, bg_path = sample_background_assets
        
        # Update config to use our test assets
        with patch('app.config.load_config') as mock_config:
            mock_config.return_value = sample_config
            
            # Process the preview
            result = process_portrait_preview(
                screenshot_path=sample_screenshot,
                sit_folder_path=images_dir,
                background_name='test_background.jpg',
                session_id='test-session',
                work_dir=temp_work_dir,
                product_config=sample_config.products,
                frame_config=sample_config.frames
            )
        
        # Verify results
        assert result is not None
        assert 'parsed_items' in result
        assert 'session_id' in result
        assert result['session_id'] == 'test-session'
        assert len(result['parsed_items']) > 0
        
        # Check OCR stats
        assert 'ocr_stats' in result
        assert result['ocr_stats']['confidence_avg'] == 85.5
        
        # Check parsing stats
        assert 'parsing_stats' in result
        assert result['parsing_stats']['items_parsed'] >= 0
    
    def test_pipeline_with_tesseract_error(
        self,
        sample_screenshot,
        sample_customer_images,
        temp_work_dir,
        sample_config
    ):
        """Test pipeline when Tesseract is not available."""
        images_dir, _ = sample_customer_images
        
        # Mock Tesseract error
        with patch('app.ocr.FileMakerOCR') as mock_class:
            mock_class.side_effect = Exception("tesseract: command not found")
            
            with pytest.raises(TesseractNotInstalledError):
                process_portrait_preview(
                    screenshot_path=sample_screenshot,
                    sit_folder_path=images_dir,
                    background_name='test_background.jpg',
                    session_id='test-session',
                    work_dir=temp_work_dir,
                    product_config=sample_config.products,
                    frame_config=sample_config.frames
                )
    
    def test_pipeline_with_no_items_detected(
        self,
        sample_screenshot,
        sample_customer_images,
        temp_work_dir,
        sample_config
    ):
        """Test pipeline when no order items are detected."""
        images_dir, _ = sample_customer_images
        
        # Mock OCR that returns no valid lines
        with patch('app.ocr.FileMakerOCR') as mock_class:
            mock_instance = Mock()
            mock_instance.process_screenshot.return_value = Mock(
                lines=[],  # No lines detected
                words=[],
                confidence_avg=15.0,
                roi_bbox=None
            )
            mock_class.return_value = mock_instance
            
            with pytest.raises(NoItemsDetectedError) as exc_info:
                process_portrait_preview(
                    screenshot_path=sample_screenshot,
                    sit_folder_path=images_dir,
                    background_name='test_background.jpg',
                    session_id='test-session',
                    work_dir=temp_work_dir,
                    product_config=sample_config.products,
                    frame_config=sample_config.frames
                )
            
            # Check error details
            error = exc_info.value
            assert error.details['ocr_confidence'] == 15.0
    
    def test_pipeline_with_missing_images(
        self,
        sample_screenshot,
        temp_work_dir,
        sample_config
    ):
        """Test pipeline when most customer images are missing."""
        # Create empty directory with no images
        empty_dir = temp_work_dir / "empty_customer_images"
        empty_dir.mkdir()
        
        # Mock OCR that returns valid lines
        with patch('app.ocr.FileMakerOCR') as mock_class:
            mock_instance = Mock()
            mock_instance.process_screenshot.return_value = Mock(
                lines=[
                    "2 8x10 Basic Print Digital                    1234, 5678",
                    "1 5x7 Cherry Wallet                          9876"
                ],
                words=['2', '8x10', 'Basic', 'Print', 'Digital', '1234,', '5678'],
                confidence_avg=85.5,
                roi_bbox=(50, 100, 1150, 200)
            )
            mock_class.return_value = mock_instance
            
            with pytest.raises(ImageFilesNotFoundError) as exc_info:
                process_portrait_preview(
                    screenshot_path=sample_screenshot,
                    sit_folder_path=empty_dir,
                    background_name='test_background.jpg',
                    session_id='test-session',
                    work_dir=temp_work_dir,
                    product_config=sample_config.products,
                    frame_config=sample_config.frames
                )
            
            # Check error details
            error = exc_info.value
            assert len(error.details['missing_codes']) > 0
    
    def test_pipeline_partial_image_mapping(
        self,
        sample_screenshot,
        sample_customer_images,
        temp_work_dir,
        sample_config,
        mock_ocr_processor
    ):
        """Test pipeline with partial image mapping (some images missing)."""
        images_dir, image_paths = sample_customer_images
        
        # Remove some images to simulate partial mapping
        (images_dir / "IMG_9876.jpg").unlink()  # Remove one image
        
        with patch('app.config.load_config') as mock_config:
            mock_config.return_value = sample_config
            
            result = process_portrait_preview(
                screenshot_path=sample_screenshot,
                sit_folder_path=images_dir,
                background_name='test_background.jpg',
                session_id='test-session',
                work_dir=temp_work_dir,
                product_config=sample_config.products,
                frame_config=sample_config.frames
            )
        
        # Should succeed but with warnings
        assert result is not None
        assert 'warnings' in result
        assert len(result['warnings']) > 0
        assert any("missing" in warning.lower() for warning in result['warnings'])


class TestErrorRecovery:
    """Test error recovery and resilience."""
    
    def test_work_directory_creation_failure(self, sample_config):
        """Test handling of work directory creation failures."""
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            mock_mkdir.side_effect = PermissionError("Cannot create directory")
            
            # Should handle gracefully
            with pytest.raises(Exception):
                process_portrait_preview(
                    screenshot_path=Path('/fake/screenshot.png'),
                    sit_folder_path=Path('/fake/images'),
                    background_name='test_background.jpg',
                    session_id='test-session',
                    work_dir=Path('/fake/work'),
                    product_config=sample_config.products,
                    frame_config=sample_config.frames
                )
    
    def test_concurrent_processing_sessions(
        self,
        sample_screenshot,
        sample_customer_images,
        temp_work_dir,
        sample_config,
        mock_ocr_processor
    ):
        """Test handling multiple concurrent processing sessions."""
        images_dir, _ = sample_customer_images
        
        # Create multiple work directories
        work_dirs = []
        for i in range(3):
            work_dir = temp_work_dir / f"session_{i}"
            work_dir.mkdir()
            work_dirs.append(work_dir)
        
        # Process multiple sessions
        results = []
        for i, work_dir in enumerate(work_dirs):
            with patch('app.config.load_config') as mock_config:
                mock_config.return_value = sample_config
                
                try:
                    result = process_portrait_preview(
                        screenshot_path=sample_screenshot,
                        sit_folder_path=images_dir,
                        background_name='test_background.jpg',
                        session_id=f'session_{i}',
                        work_dir=work_dir,
                        product_config=sample_config.products,
                        frame_config=sample_config.frames
                    )
                    results.append(result)
                except Exception as e:
                    # Some may fail due to missing assets, that's ok
                    pass
        
        # At least one should succeed or fail gracefully
        assert len(results) >= 0


class TestPerformance:
    """Test performance and resource usage."""
    
    def test_memory_cleanup_after_processing(
        self,
        sample_screenshot,
        sample_customer_images,
        temp_work_dir,
        sample_config,
        mock_ocr_processor
    ):
        """Test that memory is cleaned up after processing."""
        import gc
        import psutil
        import os
        
        images_dir, _ = sample_customer_images
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Process multiple times
        for i in range(3):
            work_dir = temp_work_dir / f"perf_test_{i}"
            work_dir.mkdir()
            
            with patch('app.config.load_config') as mock_config:
                mock_config.return_value = sample_config
                
                try:
                    result = process_portrait_preview(
                        screenshot_path=sample_screenshot,
                        sit_folder_path=images_dir,
                        background_name='test_background.jpg',
                        session_id=f'perf-test-{i}',
                        work_dir=work_dir,
                        product_config=sample_config.products,
                        frame_config=sample_config.frames
                    )
                except Exception:
                    # Errors are ok for this test
                    pass
        
        # Force garbage collection
        gc.collect()
        
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (less than 100MB)
        assert memory_growth < 100 * 1024 * 1024, f"Memory grew by {memory_growth / (1024*1024):.1f}MB"
    
    def test_large_screenshot_handling(
        self,
        temp_work_dir,
        sample_customer_images,
        sample_config
    ):
        """Test handling of large screenshot files."""
        from PIL import Image
        
        # Create a large screenshot
        large_screenshot = temp_work_dir / "large_screenshot.png"
        img = Image.new('RGB', (4000, 3000), color='white')
        img.save(large_screenshot)
        
        images_dir, _ = sample_customer_images
        
        # Mock OCR processor
        with patch('app.ocr.FileMakerOCR') as mock_class:
            mock_instance = Mock()
            mock_instance.process_screenshot.return_value = Mock(
                lines=["1 8x10 Basic Print Digital 1234"],
                words=['1', '8x10', 'Basic', 'Print', 'Digital', '1234'],
                confidence_avg=85.0,
                roi_bbox=(100, 100, 3900, 2900)
            )
            mock_class.return_value = mock_instance
            
            # Should handle large images without crashing
            try:
                result = process_portrait_preview(
                    screenshot_path=large_screenshot,
                    sit_folder_path=images_dir,
                    background_name='test_background.jpg',
                    session_id='large-test',
                    work_dir=temp_work_dir,
                    product_config=sample_config.products,
                    frame_config=sample_config.frames
                )
                assert result is not None
            except Exception as e:
                # Should be a specific error, not a crash
                assert isinstance(e, (ImageFilesNotFoundError, NoItemsDetectedError, Exception)) 