# Deployment Guide

## Overview

This guide covers deploying AI-ContentGen-Pro to production environments. Choose the deployment method that best fits your infrastructure and requirements.

## Table of Contents

- [Quick Deployment Options](#quick-deployment-options)
- [Production Considerations](#production-considerations)
- [Gunicorn Deployment](#gunicorn-deployment)
- [Docker Deployment](#docker-deployment)
- [Cloud Platform Deployment](#cloud-platform-deployment)
- [Nginx Reverse Proxy](#nginx-reverse-proxy)
- [Environment Configuration](#environment-configuration)
- [Monitoring & Logging](#monitoring--logging)
- [Security Best Practices](#security-best-practices)

---

## Quick Deployment Options

### Option 1: Gunicorn (Recommended)

```bash
# Install Gunicorn
pip install gunicorn

# Run with 4 workers
gunicorn -w 4 -b 0.0.0.0:5000 "gui.app:app"
```

### Option 2: Docker

```bash
# Build image
docker build -t ai-contentgen-pro .

# Run container
docker run -p 5000:5000 --env-file .env ai-contentgen-pro
```

### Option 3: Systemd Service

```bash
# Copy service file
sudo cp deployment/ai-contentgen.service /etc/systemd/system/

# Enable and start
sudo systemctl enable ai-contentgen
sudo systemctl start ai-contentgen
```

---

## Production Considerations

### Performance

- **Workers**: Use `(2 × CPU cores) + 1` workers for Gunicorn
- **Threads**: 2-4 threads per worker for I/O-bound workloads
- **Timeout**: Set to 120s for OpenAI API calls
- **Keep-alive**: 5 seconds for HTTP connections

### Scalability

- Use Redis for session storage across multiple instances
- Implement rate limiting at the API gateway level
- Cache responses to reduce API costs
- Use CDN for static assets

### Security

- Always use HTTPS in production
- Keep API keys in environment variables, never in code
- Implement API authentication/authorization
- Use security headers (CSP, HSTS, etc.)
- Regular security updates

### Monitoring

- Log all API calls and errors
- Monitor API costs and usage
- Track response times
- Set up alerts for failures

---

## Gunicorn Deployment

### Basic Configuration

Create `gunicorn_config.py`:

```python
# gunicorn_config.py
import multiprocessing

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = "logs/gunicorn_access.log"
errorlog = "logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "ai-contentgen-pro"

# Server mechanics
daemon = False
pidfile = "gunicorn.pid"
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = "/path/to/key.pem"
# certfile = "/path/to/cert.pem"
```

### Run Gunicorn

```bash
# Using config file
gunicorn -c gunicorn_config.py "gui.app:app"

# Or with command-line options
gunicorn \
  --workers 4 \
  --threads 2 \
  --timeout 120 \
  --bind 0.0.0.0:5000 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log \
  --log-level info \
  "gui.app:app"
```

### Systemd Service

Create `/etc/systemd/system/ai-contentgen.service`:

```ini
[Unit]
Description=AI Content Generator Pro
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/ai-contentgen-pro
Environment="PATH=/opt/ai-contentgen-pro/venv/bin"
EnvironmentFile=/opt/ai-contentgen-pro/.env
ExecStart=/opt/ai-contentgen-pro/venv/bin/gunicorn \
  -c gunicorn_config.py \
  "gui.app:app"
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Commands:

```bash
# Enable service
sudo systemctl enable ai-contentgen

# Start service
sudo systemctl start ai-contentgen

# Check status
sudo systemctl status ai-contentgen

# View logs
sudo journalctl -u ai-contentgen -f

# Restart
sudo systemctl restart ai-contentgen

# Stop
sudo systemctl stop ai-contentgen
```

---

## Docker Deployment

### Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/health')"

# Run application
CMD ["gunicorn", "-c", "gunicorn_config.py", "gui.app:app"]
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  app:
    build: .
    container_name: ai-contentgen-pro
    ports:
      - "5000:5000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_MODEL=${OPENAI_MODEL:-gpt-3.5-turbo}
      - TEMPERATURE=${TEMPERATURE:-0.7}
      - MAX_TOKENS=${MAX_TOKENS:-500}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  nginx:
    image: nginx:alpine
    container_name: ai-contentgen-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - app
    restart: unless-stopped
```

### Build and Run

```bash
# Build image
docker build -t ai-contentgen-pro .

# Run container
docker run -d \
  --name ai-contentgen-pro \
  -p 5000:5000 \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  ai-contentgen-pro

# Or use Docker Compose
docker-compose up -d

# View logs
docker logs -f ai-contentgen-pro

# Stop container
docker stop ai-contentgen-pro

# Remove container
docker rm ai-contentgen-pro
```

---

## Cloud Platform Deployment

### AWS Elastic Beanstalk

1. **Install EB CLI**:
```bash
pip install awsebcli
```

2. **Initialize**:
```bash
eb init -p python-3.11 ai-contentgen-pro
```

3. **Create environment**:
```bash
eb create production-env
```

4. **Deploy**:
```bash
eb deploy
```

5. **Set environment variables**:
```bash
eb setenv OPENAI_API_KEY=sk-... OPENAI_MODEL=gpt-3.5-turbo
```

### Google Cloud Run

1. **Build container**:
```bash
gcloud builds submit --tag gcr.io/PROJECT-ID/ai-contentgen-pro
```

2. **Deploy**:
```bash
gcloud run deploy ai-contentgen-pro \
  --image gcr.io/PROJECT-ID/ai-contentgen-pro \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=sk-...
```

### Heroku

1. **Create app**:
```bash
heroku create ai-contentgen-pro
```

2. **Set environment variables**:
```bash
heroku config:set OPENAI_API_KEY=sk-...
```

3. **Deploy**:
```bash
git push heroku main
```

4. **Scale**:
```bash
heroku ps:scale web=2
```

### Azure App Service

1. **Create resource**:
```bash
az webapp up --name ai-contentgen-pro --runtime "PYTHON:3.11"
```

2. **Configure**:
```bash
az webapp config appsettings set \
  --name ai-contentgen-pro \
  --resource-group myResourceGroup \
  --settings OPENAI_API_KEY=sk-...
```

---

## Nginx Reverse Proxy

### Configuration

Create `/etc/nginx/sites-available/ai-contentgen`:

```nginx
upstream ai_contentgen {
    server 127.0.0.1:5000 fail_timeout=0;
}

server {
    listen 80;
    server_name example.com www.example.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com www.example.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    # Logs
    access_log /var/log/nginx/ai-contentgen-access.log;
    error_log /var/log/nginx/ai-contentgen-error.log;
    
    # Max upload size
    client_max_body_size 10M;
    
    # Static files
    location /static {
        alias /opt/ai-contentgen-pro/gui/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Proxy to Gunicorn
    location / {
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;
        
        # Timeouts
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
        
        proxy_pass http://ai_contentgen;
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        proxy_pass http://ai_contentgen/api/health;
    }
}
```

### Enable Site

```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/ai-contentgen /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### SSL with Let's Encrypt

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d example.com -d www.example.com

# Auto-renewal is set up automatically
```

---

## Environment Configuration

### Production `.env`

```bash
# API Configuration
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-3.5-turbo
TEMPERATURE=0.7
MAX_TOKENS=500

# Application
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
LOG_LEVEL=INFO

# Security
ALLOWED_ORIGINS=https://example.com,https://www.example.com
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax

# Performance
CACHE_ENABLED=true
CACHE_TTL=3600
WORKERS=4
THREADS=2

# Monitoring
SENTRY_DSN=https://...
```

### Environment-specific Configs

Create multiple `.env` files:

- `.env.development`
- `.env.staging`
- `.env.production`

Load based on environment:

```bash
export ENV=production
gunicorn --env-file .env.${ENV} "gui.app:app"
```

---

## Monitoring & Logging

### Application Monitoring

Install Sentry:

```bash
pip install sentry-sdk[flask]
```

Add to `gui/app.py`:

```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FlaskIntegration()],
    environment=os.getenv("FLASK_ENV", "development"),
    traces_sample_rate=0.1
)
```

### Log Rotation

Configure log rotation in `/etc/logrotate.d/ai-contentgen`:

```
/opt/ai-contentgen-pro/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload ai-contentgen > /dev/null 2>&1 || true
    endscript
}
```

### Prometheus Metrics

Add prometheus client:

```bash
pip install prometheus-flask-exporter
```

In `gui/app.py`:

```python
from prometheus_flask_exporter import PrometheusMetrics

metrics = PrometheusMetrics(app)
```

Access metrics at `/metrics`

---

## Security Best Practices

### 1. Environment Variables

Never commit `.env` files. Use secrets management:

```bash
# AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id ai-contentgen-prod

# HashiCorp Vault
vault kv get secret/ai-contentgen

# Kubernetes Secrets
kubectl create secret generic ai-contentgen-secrets \
  --from-literal=OPENAI_API_KEY=sk-...
```

### 2. API Rate Limiting

Implement rate limiting:

```python
from flask_limiter import Limiter

limiter = Limiter(
    app,
    key_func=lambda: request.remote_addr,
    default_limits=["100 per hour"]
)

@app.route("/api/generate")
@limiter.limit("10 per minute")
def generate():
    pass
```

### 3. Input Validation

Validate all inputs:

```python
from marshmallow import Schema, fields, validate

class GenerateSchema(Schema):
    template = fields.Str(required=True)
    variables = fields.Dict(required=True)
    temperature = fields.Float(
        validate=validate.Range(min=0, max=1)
    )
    max_tokens = fields.Int(
        validate=validate.Range(min=1, max=4000)
    )
```

### 4. CORS Configuration

Configure CORS properly:

```python
from flask_cors import CORS

CORS(app, resources={
    r"/api/*": {
        "origins": os.getenv("ALLOWED_ORIGINS", "").split(","),
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})
```

---

## Performance Tuning

### 1. Caching

Use Redis for caching:

```python
import redis
from functools import lru_cache

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0
)

@lru_cache(maxsize=1000)
def get_template(name):
    # Cache template lookups
    pass
```

### 2. Database Connection Pooling

If using a database:

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
```

### 3. Async Workers

For high concurrency, use async workers:

```bash
pip install gunicorn[gevent]

gunicorn -k gevent -w 4 --worker-connections 1000 "gui.app:app"
```

---

## Backup & Recovery

### Backup Strategy

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/ai-contentgen"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup logs
tar -czf "$BACKUP_DIR/logs_$DATE.tar.gz" logs/

# Backup data
tar -czf "$BACKUP_DIR/data_$DATE.tar.gz" data/

# Backup config
cp .env "$BACKUP_DIR/.env_$DATE"

# Keep only last 30 days
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete
```

Add to crontab:

```bash
# Daily backup at 2 AM
0 2 * * * /opt/ai-contentgen-pro/backup.sh
```

---

## Troubleshooting

### Check Logs

```bash
# Application logs
tail -f logs/app.log

# Gunicorn logs
tail -f logs/gunicorn_error.log

# Nginx logs
tail -f /var/log/nginx/error.log

# Systemd logs
journalctl -u ai-contentgen -f
```

### Common Issues

**Issue**: High memory usage
**Solution**: Reduce workers or implement worker recycling

**Issue**: Slow response times
**Solution**: Enable caching, increase worker timeout

**Issue**: Connection timeouts
**Solution**: Increase proxy timeouts in Nginx

---

## Checklist

Before deploying to production:

- [ ] Environment variables configured
- [ ] SSL/TLS certificates installed
- [ ] Firewall rules configured
- [ ] Rate limiting enabled
- [ ] Monitoring set up
- [ ] Logging configured
- [ ] Backups automated
- [ ] Health checks working
- [ ] Security headers added
- [ ] CORS configured
- [ ] Secret keys rotated
- [ ] Dependencies updated
- [ ] Tests passing
- [ ] Documentation updated

---

## Support

For deployment issues:
- Check [docs/](.) for more guides
- Open an issue on GitHub
- Contact support team
