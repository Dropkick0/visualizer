# 🚀 Portrait Preview Webapp - Deployment Guide

This guide covers production deployment, configuration, and maintenance of the Portrait Preview Webapp.

## 📋 Prerequisites

### System Requirements
- **Operating System**: Windows 10/11, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **Python**: 3.8 or higher
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 10GB free space minimum
- **Network**: Internet connection for initial setup

### Required Software
- **Tesseract OCR**: Version 4.0 or higher
- **Python Dependencies**: See `requirements.txt`

## 🔧 Installation Steps

### 1. Install Tesseract OCR

**Windows:**
```bash
# Download and install from:
# https://github.com/UB-Mannheim/tesseract/wiki
# Make sure tesseract.exe is in your PATH
```

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install tesseract-ocr
```

### 2. Clone and Setup Application

```bash
# Clone the repository
git clone <repository-url>
cd portrait-preview-webapp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import pytesseract; print('✅ Tesseract OK')"
```

### 3. Configuration Setup

```bash
# Copy configuration templates
cp config/products.yaml.example config/products.yaml
cp config/frames.yaml.example config/frames.yaml
cp config/settings.yaml.example config/settings.yaml

# Edit configurations as needed
# See Configuration section below
```

### 4. Asset Directory Setup

```bash
# Create asset directories
mkdir -p assets/frames
mkdir -p assets/backgrounds
mkdir -p assets/branding

# Copy your frame PNG files to assets/frames/
# Copy your background JPG files to assets/backgrounds/
# Copy logo files to assets/branding/
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Security
SECRET_KEY=your-secret-key-here-change-me

# Paths
TEMP_FOLDER=/tmp/portrait_preview
UPLOAD_FOLDER=/var/uploads/portrait_preview
ASSETS_DIRECTORY=/opt/portrait_preview/assets
LOG_FILE=/var/log/portrait_preview/app.log

# Server settings
HOST=0.0.0.0
PORT=8000
THREADS=4
LOG_LEVEL=INFO

# Upload limits
MAX_UPLOAD_SIZE=20971520  # 20MB

# HTTPS (if using reverse proxy)
HTTPS=true
```

### Configuration Files

**config/settings.yaml:**
```yaml
# Update paths to match your environment
ASSETS_DIRECTORY: "/opt/portrait_preview/assets"
DEFAULT_BACKGROUND: "your_background.jpg"

# OCR settings - tune based on your screenshots
OCR_PSM: 6
OCR_OEM: 3
OCR_MIN_CONFIDENCE: 50.0

# Image processing
OUTPUT_DPI: 300
AUTO_ENHANCE: true
CROP_METHOD: "center"
```

**config/products.yaml:**
```yaml
# Configure your product catalog
products:
  - slug: "8x10_basic_print"
    type: "basic"
    name: "8x10 Basic Print"
    width: 8.0
    height: 10.0
    # ... additional products
```

**config/frames.yaml:**
```yaml
# Configure your frame assets
frames:
  - name: "cherry"
    product_type: "single"
    filename: "cherry_single.png"
    openings:
      - x: 100
        y: 100
        width: 600
        height: 800
    # ... additional frames
```

## 🖥️ Running in Production

### Option 1: Direct Python Execution

```bash
# Set environment variables
export SECRET_KEY="your-secret-key"
export ASSETS_DIRECTORY="/path/to/assets"

# Run production server
python deployment/production.py
```

### Option 2: Using systemd (Linux)

Create `/etc/systemd/system/portrait-preview.service`:

```ini
[Unit]
Description=Portrait Preview Webapp
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/portrait-preview-webapp
Environment=SECRET_KEY=your-secret-key
Environment=ASSETS_DIRECTORY=/opt/portrait_preview/assets
Environment=TEMP_FOLDER=/tmp/portrait_preview
Environment=LOG_FILE=/var/log/portrait_preview/app.log
ExecStart=/opt/portrait-preview-webapp/venv/bin/python deployment/production.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable portrait-preview
sudo systemctl start portrait-preview
sudo systemctl status portrait-preview
```

### Option 3: Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create required directories
RUN mkdir -p /tmp/portrait_preview /var/log/portrait_preview

# Expose port
EXPOSE 8000

# Set environment variables
ENV FLASK_ENV=production
ENV SECRET_KEY=change-me-in-production

# Run application
CMD ["python", "deployment/production.py"]
```

```bash
# Build and run Docker container
docker build -t portrait-preview .
docker run -d \
  --name portrait-preview \
  -p 8000:8000 \
  -v /path/to/assets:/opt/portrait_preview/assets \
  -e SECRET_KEY=your-secret-key \
  portrait-preview
```

## 🔒 Security Considerations

### 1. Secret Key
```bash
# Generate a secure secret key
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. File Permissions
```bash
# Secure application files
sudo chown -R www-data:www-data /opt/portrait_preview-webapp
sudo chmod -R 755 /opt/portrait_preview-webapp
sudo chmod 600 /opt/portrait_preview-webapp/.env
```

### 3. Reverse Proxy (Nginx)

Create `/etc/nginx/sites-available/portrait-preview`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL configuration
    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/key.pem;

    # Upload size limit
    client_max_body_size 25M;

    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout settings for large uploads
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }

    # Serve static files directly
    location /static/ {
        alias /opt/portrait_preview-webapp/app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

## 📊 Monitoring and Maintenance

### Health Checks

```bash
# Check service status
curl -f http://localhost:8000/ || echo "Service down"

# Check logs
tail -f /var/log/portrait_preview/app.log

# Check disk space
df -h /tmp/portrait_preview
```

### Log Rotation

Create `/etc/logrotate.d/portrait-preview`:
```
/var/log/portrait_preview/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        systemctl reload portrait-preview
    endscript
}
```

### Backup Strategy

```bash
#!/bin/bash
# backup-portrait-preview.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/portrait-preview"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup configuration
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" \
    config/ \
    .env

# Backup assets
tar -czf "$BACKUP_DIR/assets_$DATE.tar.gz" \
    assets/

# Clean old backups (keep 30 days)
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

### Performance Tuning

```bash
# Monitor memory usage
ps aux | grep python | grep portrait

# Monitor file handles
lsof -p $(pgrep -f "portrait")

# Check processing times
grep "Processing complete" /var/log/portrait_preview/app.log | \
    tail -100 | awk '{print $NF}' | sort -n
```

## 🧪 Testing the Deployment

### 1. Health Check
```bash
curl -f http://localhost:8000/
```

### 2. Upload Test
```bash
# Upload a test screenshot
curl -X POST \
  -F "screenshot=@test_screenshot.png" \
  -F "sit_folder_path=/path/to/test/images" \
  http://localhost:8000/process
```

### 3. Load Testing
```bash
# Install siege
sudo apt install siege

# Run load test
siege -c 10 -t 60s http://localhost:8000/
```

## 🔧 Troubleshooting

### Common Issues

**Issue: Tesseract not found**
```bash
# Check Tesseract installation
tesseract --version

# Add to PATH if needed
export PATH=$PATH:/usr/local/bin
```

**Issue: Permission denied on temp folder**
```bash
# Fix permissions
sudo chown -R www-data:www-data /tmp/portrait_preview
sudo chmod -R 755 /tmp/portrait_preview
```

**Issue: Assets not found**
```bash
# Check asset paths
ls -la /opt/portrait_preview/assets/
cat config/settings.yaml | grep ASSETS_DIRECTORY
```

**Issue: High memory usage**
```bash
# Check for memory leaks
python -m memory_profiler deployment/production.py

# Restart service periodically
systemctl restart portrait-preview
```

### Debug Mode (Development Only)

```bash
# Run in debug mode
export FLASK_DEBUG=true
python run_dev.py
```

### Log Analysis

```bash
# Check error patterns
grep "ERROR" /var/log/portrait_preview/app.log | tail -20

# Monitor processing times
grep "Processing complete" /var/log/portrait_preview/app.log | \
    awk '{print $NF}' | sort -n | tail -10
```

## 📈 Scaling Considerations

### Horizontal Scaling
- Use load balancer (HAProxy/Nginx)
- Shared storage for assets and temp files
- Session storage (Redis/Database)

### Vertical Scaling
- Increase server memory/CPU
- Tune thread count based on load
- Optimize image processing settings

### Performance Optimization
- Use CDN for static assets
- Implement caching for common requests
- Background processing for large batches

## 🆘 Support

For technical support:
1. Check logs: `/var/log/portrait_preview/app.log`
2. Verify configuration files
3. Test with sample data
4. Contact IT support with session ID

---

**Last Updated**: $(date)
**Version**: 1.0.0 