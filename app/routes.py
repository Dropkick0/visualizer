"""
Flask routes for Portrait Preview Webapp
Handles upload form and processing workflow
"""

import os
import uuid
import shutil
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from werkzeug.utils import secure_filename
from loguru import logger

# Optional import for file type detection (not required for testing)
try:
    import magic
except ImportError:
    magic = None

from .config import load_product_config, load_frame_config
from .utils import validate_folder_path, get_available_backgrounds
from .errors import (
    ValidationError, ProcessingError, OCRError, ParsingError, 
    ImageMappingError, RenderError, AssetError,
    NoItemsDetectedError, ImageFilesNotFoundError, FrameAssetMissingError,
    BackgroundAssetMissingError, TesseractNotInstalledError,
    InvalidImageFormatError, FileTooLargeError, InsufficientDiskSpaceError,
    diagnose_ocr_failure, create_error_recovery_suggestions
)


bp = Blueprint('main', __name__)


@bp.route('/', methods=['GET'])
def index():
    """Render upload form"""
    try:
        backgrounds = get_available_backgrounds()
        default_bg = current_app.config.get('BACKGROUND_DEFAULT', 'Virtual Background 2021.jpg')
        
        return render_template('index.html', 
                             backgrounds=backgrounds,
                             default_background=default_bg)
    
    except Exception as e:
        logger.error(f"Error loading index page: {e}")
        return render_template('error.html', 
                             error_message="Error loading application. Please try again."), 500


@bp.route('/process', methods=['POST'])
def process():
    """Process uploaded screenshot and folder path"""
    session_id = str(uuid.uuid4())
    work_dir = Path(current_app.config['TEMP_FOLDER']) / session_id
    work_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Validate form data
        if 'screenshot' not in request.files:
            raise ValidationError("No screenshot file uploaded")
        
        screenshot_file = request.files['screenshot']
        if screenshot_file.filename == '':
            raise ValidationError("No screenshot file selected")
        
        sit_folder_path = request.form.get('sit_folder_path', '').strip()
        if not sit_folder_path:
            raise ValidationError("Sit folder path is required")
        
        background_name = request.form.get('background', current_app.config.get('BACKGROUND_DEFAULT'))
        
        # Validate and save screenshot
        screenshot_path = validate_and_save_screenshot(screenshot_file, work_dir)
        
        # Validate and normalize folder path
        normalized_folder_path = validate_and_normalize_folder_path(sit_folder_path)
        
        # Load configurations
        product_config = load_product_config()
        frame_config = load_frame_config()
        
        # Log session start
        logger.info(f"Session {session_id} started - Screenshot: {screenshot_file.filename}, "
                   f"Folder: {normalized_folder_path}, Background: {background_name}")
        
        # Process the request (this will be implemented in later phases)
        result = process_portrait_preview(
            screenshot_path=screenshot_path,
            sit_folder_path=normalized_folder_path,
            background_name=background_name,
            session_id=session_id,
            work_dir=work_dir,
            product_config=product_config,
            frame_config=frame_config
        )
        
        return render_template('result.html', 
                             session_id=session_id,
                             result=result)
    
    except (ValidationError, InvalidImageFormatError, FileTooLargeError) as e:
        logger.warning(f"Validation error in session {session_id}: {e}")
        # Enhanced error display with suggestions
        if hasattr(e, 'suggestions'):
            for suggestion in e.suggestions:
                flash(suggestion, 'info')
        flash(str(e), 'error')
        cleanup_work_dir(work_dir)
        return redirect(url_for('main.index'))
    
    except (NoItemsDetectedError, ImageFilesNotFoundError, TesseractNotInstalledError) as e:
        logger.error(f"Processing error in session {session_id}: {e}")
        error_context = {
            'error': e,
            'suggestions': getattr(e, 'suggestions', []),
            'details': getattr(e, 'details', {}),
            'session_id': session_id
        }
        cleanup_work_dir(work_dir)
        return render_template('enhanced_error.html', **error_context), 400
    
    except (OCRError, ParsingError, ImageMappingError, RenderError, AssetError) as e:
        logger.error(f"Processing error in session {session_id}: {e}")
        error_context = {
            'error': e,
            'suggestions': getattr(e, 'suggestions', []),
            'details': getattr(e, 'details', {}),
            'session_id': session_id
        }
        return render_template('enhanced_error.html', **error_context), 500
    
    except ProcessingError as e:
        logger.error(f"Processing error in session {session_id}: {e}")
        return render_template('error.html', 
                             error_message=str(e),
                             session_id=session_id), 500
    
    except Exception as e:
        logger.error(f"Unexpected error in session {session_id}: {e}")
        
        # Generate recovery suggestions based on context
        context = {
            'session_id': session_id,
            'has_screenshot': screenshot_path.exists() if 'screenshot_path' in locals() else False,
            'has_folder_path': 'sit_folder_path' in locals()
        }
        suggestions = create_error_recovery_suggestions(e, context)
        
        return render_template('enhanced_error.html', 
                             error=e,
                             suggestions=suggestions,
                             details={'error_type': type(e).__name__},
                             session_id=session_id), 500
    
    finally:
        # Cleanup work directory on validation errors
        if 'e' in locals() and isinstance(e, (ValidationError, InvalidImageFormatError, FileTooLargeError)):
            cleanup_work_dir(work_dir)


def validate_and_save_screenshot(file, work_dir: Path) -> Path:
    """Validate and save uploaded screenshot file with enhanced error handling"""
    
    # Check disk space first
    try:
        free_space = shutil.disk_usage(work_dir.parent).free
        required_space = 50 * 1024 * 1024  # 50MB minimum
        if free_space < required_space:
            raise InsufficientDiskSpaceError(
                required_mb=required_space / (1024 * 1024),
                available_mb=free_space / (1024 * 1024)
            )
    except (OSError, AttributeError):
        # Skip disk space check if not available
        pass
    
    # Check file size
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset to beginning
    
    max_size = current_app.config.get('MAX_UPLOAD_SIZE', 20 * 1024 * 1024)
    if size > max_size:
        raise FileTooLargeError(
            filename=file.filename,
            size_mb=size / (1024 * 1024),
            limit_mb=max_size / (1024 * 1024)
        )
    
    # Validate file type using python-magic
    file_data = file.read(2048)  # Read first 2KB for magic detection
    file.seek(0)  # Reset
    
    try:
        if magic:
            mime_type = magic.from_buffer(file_data, mime=True)
            if not mime_type.startswith('image/'):
                raise InvalidImageFormatError(file.filename, mime_type)
        else:
            # Magic not available, use extension check
            raise Exception("Magic not available")
    except Exception:
        # Fallback to extension check
        allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', ['.jpg', '.jpeg', '.png'])
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            raise InvalidImageFormatError(file.filename, f"Extension: {file_ext}")
    
    # Validate image can be opened
    try:
        file_copy = file.read()
        file.seek(0)  # Reset for saving
        from PIL import Image
        import io
        test_image = Image.open(io.BytesIO(file_copy))
        test_image.verify()  # Check if image is valid
    except Exception as e:
        raise InvalidImageFormatError(file.filename, f"Corrupted image: {str(e)}")
    
    # Save file
    filename = secure_filename(file.filename)
    if not filename:
        filename = f"screenshot_{uuid.uuid4().hex[:8]}.png"
    
    screenshot_path = work_dir / filename
    try:
        file.save(screenshot_path)
    except Exception as e:
        raise ProcessingError(f"Failed to save screenshot: {e}")
    
    logger.info(f"Screenshot saved: {screenshot_path} ({size} bytes)")
    return screenshot_path


def validate_and_normalize_folder_path(path_str: str) -> Path:
    """Validate and normalize the sit folder path"""
    
    # Strip quotes if user copied path with quotes
    path_str = path_str.strip('\'"')
    
    # Handle environment variables
    path_str = os.path.expandvars(path_str)
    
    # Convert to Path object
    folder_path = Path(path_str)
    
    # If relative path, join with DROPBOX_ROOT if configured
    if not folder_path.is_absolute():
        dropbox_root = current_app.config.get('DROPBOX_ROOT')
        if dropbox_root:
            folder_path = Path(dropbox_root) / folder_path
        else:
            folder_path = folder_path.resolve()
    
    # Validate path exists and is accessible
    if not folder_path.exists():
        raise ValidationError(f"Folder not found: {folder_path}")
    
    if not folder_path.is_dir():
        raise ValidationError(f"Path is not a directory: {folder_path}")
    
    # Basic path traversal protection
    try:
        folder_path.resolve()
    except (OSError, ValueError) as e:
        raise ValidationError(f"Invalid folder path: {e}")
    
    logger.info(f"Validated folder path: {folder_path}")
    return folder_path


def process_portrait_preview(screenshot_path, sit_folder_path, background_name, 
                           session_id, work_dir, product_config, frame_config):
    """
    Main processing function implementing phases 4-9
    OCR -> Parsing -> Image Mapping -> Render Prep -> Layout -> Compositing
    """
    from .ocr_windows import WindowsOCR
    from .parse import FileMakerParser
    from .mapping import ImageMapper
    from .render import create_render_prep, CustomerImage
    from .layout import create_layout_engine
    from .composite import create_composite_engine, CompositeSettings
    from .config import load_config
    
    try:
        # Load application configuration
        app_config = load_config()
        
        # Phase 4: OCR processing with Windows built-in OCR
        logger.info(f"Starting Windows OCR processing for session {session_id}")
        try:
            ocr_processor = WindowsOCR(app_config)
            ocr_result = ocr_processor.process_screenshot(screenshot_path, work_dir)
        except Exception as e:
            # Check if Windows OCR is available
            if "winocr" in str(e).lower() or "not available" in str(e).lower():
                raise OCRError(f"Windows OCR not available: {e}", 
                             details={'screenshot_path': str(screenshot_path)},
                             suggestions=["Ensure you're running on Windows 10/11 with OCR language packs installed",
                                        "Install required OCR language pack using: Add-WindowsCapability -Online -Name 'Language.OCR~~~en-US~0.0.1.0'"])
            else:
                raise OCRError(f"OCR processing failed: {e}", 
                             details={'screenshot_path': str(screenshot_path)},
                             suggestions=["Check that the screenshot is clear and readable",
                                        "Ensure Windows OCR is properly configured"])
                                        
        
        # Save OCR stats to work dir
        ocr_stats = {
            'lines_detected': len(ocr_result.lines),
            'words_detected': len(ocr_result.words),
            'confidence_avg': ocr_result.confidence_avg,
            'roi_bbox': ocr_result.roi_bbox
        }
        
        import json
        with open(work_dir / "ocr_stats.json", 'w') as f:
            json.dump(ocr_stats, f, indent=2)
        
        # Phase 5: Parse OCR text into structured items
        logger.info(f"Starting text parsing for session {session_id}")
        try:
            parser = FileMakerParser(product_config)
            parsed_items = parser.parse_ocr_lines(ocr_result.lines)
            
            if not parsed_items:
                # Generate diagnostic information
                diagnostics = diagnose_ocr_failure(ocr_result, str(screenshot_path))
                raise NoItemsDetectedError(
                    ocr_confidence=diagnostics.get('confidence_avg'),
                    lines_detected=diagnostics.get('lines_detected')
                )
        except NoItemsDetectedError:
            raise  # Re-raise specific error
        except Exception as e:
            raise ParsingError(f"Text parsing failed: {e}",
                             details={'lines_count': len(ocr_result.lines)},
                             suggestions=["Verify the screenshot shows the PORTRAITS table clearly",
                                        "Check that product names and quantities are visible"])
        
        # Phase 6: Map image codes to actual files
        logger.info(f"Starting image mapping for session {session_id}")
        try:
            image_mapper = ImageMapper(sit_folder_path)
            mapped_items = image_mapper.map_order_items(parsed_items)
            
            # Check for missing images and provide specific error if too many missing
            missing_codes = image_mapper.find_missing_codes(parsed_items)
            total_codes = sum(len(item.codes) for item in parsed_items)
            
            if missing_codes and len(missing_codes) >= total_codes * 0.8:  # 80% or more missing
                raise ImageFilesNotFoundError(missing_codes, str(sit_folder_path))
            
        except ImageFilesNotFoundError:
            raise  # Re-raise specific error
        except Exception as e:
            raise ImageMappingError(f"Image mapping failed: {e}",
                                  details={'folder_path': str(sit_folder_path)},
                                  suggestions=["Verify the folder path exists and is accessible",
                                             "Check that image files are in the correct location"])
        
        # Collect overall warnings
        warnings = []
        missing_codes = image_mapper.find_missing_codes(parsed_items)
        if missing_codes:
            warnings.append(f"Missing image files for codes: {', '.join(missing_codes)}")
        
        # Save parsing results to work dir
        parsing_stats = {
            'items_parsed': len(parsed_items),
            'items_with_images': len([item for item in mapped_items if getattr(item, 'image_paths', [])]),
            'total_codes_requested': sum(len(item.codes) for item in parsed_items),
            'total_codes_found': len(image_mapper.code_map),
            'mapping_stats': image_mapper.get_scan_statistics()
        }
        
        with open(work_dir / "parsing_stats.json", 'w') as f:
            json.dump(parsing_stats, f, indent=2)
        
        # Phase 7-9: Generate preview images
        preview_url = None
        preview_images = []
        render_stats = {'successful_renders': 0, 'failed_renders': 0, 'total_items': len(mapped_items)}
        
        try:
            # Initialize render engines
            render_prep = create_render_prep()
            layout_engine = create_layout_engine()
            composite_engine = create_composite_engine()
            
            logger.info(f"Initialized render engines for {len(mapped_items)} items")
            
            # Process each item that has mapped images
            for item_idx, item in enumerate(mapped_items):
                image_paths = getattr(item, 'image_paths', [])
                if not image_paths:
                    logger.info(f"Skipping item {item_idx}: no images mapped")
                    continue
                
                try:
                    logger.info(f"Rendering item {item_idx + 1}/{len(mapped_items)}: {item.product_slug}")
                    
                    # Create CustomerImage objects
                    customer_images = []
                    for code, path in zip(item.codes, image_paths):
                        if path:
                            customer_images.append(CustomerImage(str(path), code))
                    
                    if not customer_images:
                        continue
                    
                    # Find matching product configuration
                    product_match = None
                    for product in product_config.products:
                        if product.slug == item.product_slug:
                            product_match = product
                            break
                    
                    if not product_match:
                        logger.warning(f"No product config found for {item.product_slug}")
                        continue
                    
                    # Phase 7: Render preparation
                    render_context = render_prep.create_render_context(
                        customer_images=customer_images,
                        frame_style=item.frame_style or 'none',
                        product_type=product_match.type,
                        product_config=product_match.dict(),
                        background_name=background_name
                    )
                    
                    # Phase 8: Layout planning
                    layout_elements = layout_engine.create_layout_plan(render_context)
                    
                    # Add branding elements if enabled
                    layout_elements = layout_engine.add_branding_elements(
                        layout_elements,
                        render_context['canvas_size'],
                        render_context['product_config']
                    )
                    
                    # Optimize layout
                    layout_elements = layout_engine.optimize_layout(layout_elements)
                    
                    # Phase 9: Compositing
                    final_image = composite_engine.composite_elements(
                        layout_elements,
                        render_context['canvas_size']
                    )
                    
                    # Apply final adjustments
                    final_image = composite_engine.apply_final_adjustments(final_image)
                    
                    # Save the preview image
                    preview_filename = f"preview_{item_idx + 1}_{item.product_slug}.jpg"
                    preview_path = work_dir / preview_filename
                    
                    settings = CompositeSettings(
                        output_format='JPEG',
                        quality=85,
                        optimize=True
                    )
                    
                    success = composite_engine.save_image(final_image, str(preview_path), settings)
                    
                    if success:
                        # Create thumbnail
                        thumbnail = composite_engine.create_thumbnail(final_image)
                        thumb_path = work_dir / f"thumb_{preview_filename}"
                        composite_engine.save_image(thumbnail, str(thumb_path), settings)
                        
                        preview_images.append({
                            'item_index': item_idx,
                            'product_slug': item.product_slug,
                            'preview_url': f"/static/temp/{session_id}/{preview_filename}",
                            'thumbnail_url': f"/static/temp/{session_id}/thumb_{preview_filename}",
                            'canvas_size': render_context['canvas_size'],
                            'codes_used': [img.image_code for img in customer_images]
                        })
                        
                        render_stats['successful_renders'] += 1
                        logger.info(f"Successfully rendered item {item_idx + 1}")
                    else:
                        render_stats['failed_renders'] += 1
                        warnings.append(f"Failed to save preview for item {item_idx + 1}")
                        
                except Exception as e:
                    logger.error(f"Failed to render item {item_idx}: {e}")
                    render_stats['failed_renders'] += 1
                    warnings.append(f"Failed to render item {item_idx + 1}: {str(e)}")
                    continue
            
            # Set main preview URL to first successful render
            if preview_images:
                preview_url = preview_images[0]['preview_url']
                logger.info(f"Generated {len(preview_images)} preview images")
            else:
                warnings.append("No preview images could be generated")
                
        except Exception as e:
            logger.error(f"Render pipeline failed for session {session_id}: {e}")
            warnings.append(f"Preview generation failed: {str(e)}")
        
        # Save render stats
        with open(work_dir / "render_stats.json", 'w') as f:
            json.dump(render_stats, f, indent=2)
        
        # Convert structured items to result format
        result_items = []
        for item in mapped_items:
            result_item = {
                'product_slug': item.product_slug,
                'quantity': item.quantity,
                'width_in': item.width_in,
                'height_in': item.height_in,
                'orientation': item.orientation,
                'frame_style': item.frame_style,
                'codes': item.codes,
                'warnings': item.warnings,
                'source_line': item.source_line_text,
                'image_paths': getattr(item, 'image_paths', [])
            }
            result_items.append(result_item)
        
        logger.info(f"Processing complete for session {session_id}: "
                   f"{len(result_items)} items, {len(warnings)} warnings, "
                   f"{render_stats['successful_renders']} previews generated")
        
        return {
            'preview_url': preview_url,
            'preview_images': preview_images,
            'parsed_items': result_items,
            'warnings': warnings,
            'background': background_name,
            'folder_path': str(sit_folder_path),
            'session_id': session_id,
            'ocr_stats': ocr_stats,
            'parsing_stats': parsing_stats,
            'render_stats': render_stats
        }
        
    except Exception as e:
        logger.error(f"Processing failed for session {session_id}: {e}")
        raise ProcessingError(f"Failed to process preview: {e}")


def cleanup_work_dir(work_dir: Path):
    """Clean up temporary work directory"""
    try:
        if work_dir.exists():
            shutil.rmtree(work_dir)
            logger.info(f"Cleaned up work directory: {work_dir}")
    except Exception as e:
        logger.warning(f"Failed to cleanup work directory {work_dir}: {e}")


@bp.route('/static/temp/<session_id>/<filename>')
def serve_temp_file(session_id, filename):
    """Serve temporary files from work directory"""
    work_dir = Path(current_app.config['TEMP_FOLDER']) / session_id
    file_path = work_dir / filename
    
    # Security check - ensure file is within work directory
    try:
        file_path.resolve().relative_to(work_dir.resolve())
    except ValueError:
        return "Invalid file path", 403
    
    if not file_path.exists():
        return f"File not found", 404
    
    # Determine content type
    content_type = 'image/jpeg'
    if filename.lower().endswith('.png'):
        content_type = 'image/png'
    elif filename.lower().endswith('.json'):
        content_type = 'application/json'
    
    from flask import send_file
    return send_file(str(file_path), mimetype=content_type)


@bp.route('/debug/<session_id>')
def debug_session(session_id):
    """Debug endpoint to view session artifacts"""
    if not current_app.config.get('DEBUG'):
        return "Debug mode not enabled", 403
    
    work_dir = Path(current_app.config['TEMP_FOLDER']) / session_id
    if not work_dir.exists():
        return f"Session {session_id} not found", 404
    
    files = list(work_dir.glob('*'))
    return jsonify({
        'session_id': session_id,
        'work_dir': str(work_dir),
        'files': [str(f.name) for f in files]
    }) 