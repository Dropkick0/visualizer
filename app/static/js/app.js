/**
 * Portrait Preview Webapp - Client-side JavaScript
 */

// Global app object
window.PortraitPreview = {
    init: function() {
        this.setupFormValidation();
        this.setupFileHandling();
        this.setupTooltips();
    },

    setupFormValidation: function() {
        // Real-time validation for file uploads
        const fileInput = document.getElementById('screenshot');
        if (fileInput) {
            fileInput.addEventListener('change', function(e) {
                const file = e.target.files[0];
                const errorDiv = document.getElementById('screenshot-error');
                
                if (file) {
                    // Check file size (20MB limit)
                    if (file.size > 20 * 1024 * 1024) {
                        fileInput.classList.add('is-invalid');
                        errorDiv.textContent = 'File too large. Maximum size is 20MB.';
                        return;
                    }
                    
                    // Check file type
                    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/tiff', 'image/tif'];
                    if (!validTypes.includes(file.type)) {
                        fileInput.classList.add('is-invalid');
                        errorDiv.textContent = 'Invalid file type. Please upload an image file.';
                        return;
                    }
                    
                    // File is valid
                    fileInput.classList.remove('is-invalid');
                    fileInput.classList.add('is-valid');
                    errorDiv.textContent = '';
                }
            });
        }
        
        // Real-time validation for folder path
        const folderInput = document.getElementById('sit_folder_path');
        if (folderInput) {
            folderInput.addEventListener('input', function(e) {
                const path = e.target.value.trim();
                const errorDiv = document.getElementById('folder-error');
                
                if (path.length > 0) {
                    // Basic path validation
                    if (path.length < 3) {
                        folderInput.classList.add('is-invalid');
                        errorDiv.textContent = 'Path too short.';
                        return;
                    }
                    
                    folderInput.classList.remove('is-invalid');
                    folderInput.classList.add('is-valid');
                    errorDiv.textContent = '';
                } else {
                    folderInput.classList.remove('is-valid', 'is-invalid');
                }
            });
        }
    },

    setupFileHandling: function() {
        // Drag and drop for file uploads
        const fileInput = document.getElementById('screenshot');
        if (fileInput) {
            const dropZone = fileInput.closest('.card-body');
            
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, preventDefaults, false);
            });
            
            function preventDefaults(e) {
                e.preventDefault();
                e.stopPropagation();
            }
            
            ['dragenter', 'dragover'].forEach(eventName => {
                dropZone.addEventListener(eventName, highlight, false);
            });
            
            ['dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, unhighlight, false);
            });
            
            function highlight(e) {
                dropZone.classList.add('border-primary', 'bg-light');
            }
            
            function unhighlight(e) {
                dropZone.classList.remove('border-primary', 'bg-light');
            }
            
            dropZone.addEventListener('drop', handleDrop, false);
            
            function handleDrop(e) {
                const dt = e.dataTransfer;
                const files = dt.files;
                
                if (files.length > 0) {
                    fileInput.files = files;
                    // Trigger change event for validation
                    fileInput.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        }
    },

    setupTooltips: function() {
        // Initialize Bootstrap tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    },

    showLoading: function(button, text) {
        if (button) {
            button.innerHTML = '<span class="loading-spinner me-2"></span>' + (text || 'Processing...');
            button.disabled = true;
        }
    },

    hideLoading: function(button, originalText) {
        if (button) {
            button.innerHTML = originalText;
            button.disabled = false;
        }
    },

    showAlert: function(message, type) {
        type = type || 'info';
        const alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                <i class="fas fa-${type === 'error' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        // Insert at top of main container
        const container = document.querySelector('.container');
        if (container) {
            container.insertAdjacentHTML('afterbegin', alertHtml);
        }
    },

    copyToClipboard: function(text) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(function() {
                this.showAlert('Copied to clipboard!', 'success');
            }.bind(this));
        } else {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            this.showAlert('Copied to clipboard!', 'success');
        }
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    PortraitPreview.init();
});

// Utility functions
function showPathHelp() {
    const modal = new bootstrap.Modal(document.getElementById('pathHelpModal'));
    modal.show();
}

function showHelp() {
    const helpText = `
Portrait Preview Webapp Help:

1. Take a clear screenshot of the FileMaker Item Entry screen
2. Copy the path to the customer's image folder from Dropbox  
3. Upload and wait for the preview to generate

Tips:
• Capture at 100% zoom for best OCR results
• Include the full PORTRAITS table with image codes
• Double-check folder path for typos
• Ensure image files exist in the specified folder

For technical support, contact the development team.
    `;
    alert(helpText.trim());
}

// Global error handler
window.addEventListener('error', function(e) {
    console.error('JavaScript error:', e.error);
    // Could send to logging service in production
});

// Handle form submission with loading states
document.addEventListener('submit', function(e) {
    if (e.target.id === 'uploadForm') {
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        
        setTimeout(function() {
            PortraitPreview.showLoading(submitBtn, 'Processing...');
        }, 100);
        
        // Re-enable button if form validation fails
        setTimeout(function() {
            if (e.target.querySelector('.is-invalid')) {
                PortraitPreview.hideLoading(submitBtn, originalText);
            }
        }, 500);
    }
}); 