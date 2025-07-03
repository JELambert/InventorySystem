# 🚀 Deployment Guide

This guide covers deploying the Home Inventory System to production environments.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Database Setup](#database-setup)
- [Docker Deployment](#docker-deployment)
- [Manual Deployment](#manual-deployment)
- [Reverse Proxy Setup](#reverse-proxy-setup)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Health Monitoring](#health-monitoring)
- [Backup & Recovery](#backup--recovery)
- [Troubleshooting](#troubleshooting)
- [Production Checklist](#production-checklist)

## Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 20.04+ recommended) or macOS
- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 10GB+ for application and data
- **Python**: 3.12 or higher
- **Docker**: 20.10+ and Docker Compose 2.0+ (for containerized deployment)

### External Services
- **PostgreSQL**: 15+ (Proxmox LXC container)
- **Weaviate**: 1.23+ (Proxmox LXC container)

## Environment Setup

### 1. Clone Repository
```bash
git clone https://github.com/your-org/inventory-system.git
cd inventory-system
```

### 2. Create Environment File
```bash
cp .env.example .env
```

Edit `.env` with your production values:
```env
# Database Configuration
POSTGRES_HOST=192.168.68.88
POSTGRES_PORT=5432
POSTGRES_DB=inventory_system
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password_here

# Weaviate Configuration
WEAVIATE_HOST=192.168.68.97
WEAVIATE_PORT=8080
WEAVIATE_TIMEOUT=30

# Application Settings
ENVIRONMENT=production
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000

# Frontend Settings
API_BASE_URL=https://inventory-api.yourdomain.com
FRONTEND_PORT=8501
```

### 3. Generate Secure Passwords
```bash
# Generate secure database password
openssl rand -base64 32

# Store securely in password manager
```

## Database Setup

### PostgreSQL in Proxmox LXC

#### 1. Create LXC Container
```bash
# On Proxmox host
pct create 201 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
  --hostname postgres-inventory \
  --memory 4096 \
  --cores 2 \
  --rootfs local-lvm:32 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.68.88/24,gw=192.168.68.1 \
  --password
```

#### 2. Install PostgreSQL
```bash
# Inside LXC container
apt update && apt upgrade -y
apt install -y postgresql-15 postgresql-contrib-15

# Configure PostgreSQL
su - postgres
psql

# Create database and user
CREATE DATABASE inventory_system;
CREATE USER inventory_user WITH ENCRYPTED PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE inventory_system TO inventory_user;
\q
```

#### 3. Configure Remote Access
Edit `/etc/postgresql/15/main/postgresql.conf`:
```conf
listen_addresses = '*'
```

Edit `/etc/postgresql/15/main/pg_hba.conf`:
```conf
# Allow connections from application subnet
host    inventory_system    inventory_user    192.168.68.0/24    scram-sha-256
```

Restart PostgreSQL:
```bash
systemctl restart postgresql
```

### Run Database Migrations
```bash
cd backend
poetry install
poetry run alembic upgrade head
```

## Weaviate Setup

### Weaviate in Proxmox LXC

#### 1. Create LXC Container
```bash
pct create 202 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
  --hostname weaviate-inventory \
  --memory 8192 \
  --cores 4 \
  --rootfs local-lvm:64 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.68.97/24,gw=192.168.68.1 \
  --password
```

#### 2. Install Weaviate
```bash
# Inside LXC container
apt update && apt install -y docker.io docker-compose

# Create docker-compose.yml
cat > docker-compose.yml << EOF
version: '3.4'
services:
  weaviate:
    image: semitechnologies/weaviate:1.23.0
    ports:
      - "8080:8080"
      - "50051:50051"
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      DEFAULT_VECTORIZER_MODULE: 'none'
      CLUSTER_HOSTNAME: 'node1'
    volumes:
      - weaviate_data:/var/lib/weaviate
volumes:
  weaviate_data:
EOF

# Start Weaviate
docker-compose up -d
```

## Docker Deployment

### 1. Build Images
```bash
# Production build
docker-compose -f docker-compose.prod.yml build
```

### 2. Create Production Docker Compose
Create `docker-compose.prod.yml`:
```yaml
version: '3.8'

services:
  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_HOST=${POSTGRES_HOST}
      - POSTGRES_PORT=${POSTGRES_PORT}
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - WEAVIATE_HOST=${WEAVIATE_HOST}
      - WEAVIATE_PORT=${WEAVIATE_PORT}
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  frontend:
    build: 
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "8501:8501"
    environment:
      - API_BASE_URL=http://backend:8000
      - STREAMLIT_SERVER_ADDRESS=0.0.0.0
      - STREAMLIT_SERVER_PORT=8501
      - STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
    depends_on:
      - backend
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
      - frontend
    restart: unless-stopped
```

### 3. Deploy with Docker Compose
```bash
# Start all services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Scale backend if needed
docker-compose -f docker-compose.prod.yml up -d --scale backend=3
```

## Manual Deployment

### Backend Deployment

#### 1. Install Dependencies
```bash
cd backend
poetry install --no-dev
```

#### 2. Create systemd Service
Create `/etc/systemd/system/inventory-backend.service`:
```ini
[Unit]
Description=Home Inventory Backend API
After=network.target

[Service]
Type=exec
User=inventory
Group=inventory
WorkingDirectory=/opt/inventory-system/backend
Environment="PATH=/opt/inventory-system/backend/.venv/bin"
ExecStart=/opt/inventory-system/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 3. Start Service
```bash
systemctl daemon-reload
systemctl enable inventory-backend
systemctl start inventory-backend
```

### Frontend Deployment

#### 1. Install Dependencies
```bash
cd frontend
poetry install --no-dev
```

#### 2. Create systemd Service
Create `/etc/systemd/system/inventory-frontend.service`:
```ini
[Unit]
Description=Home Inventory Frontend
After=network.target inventory-backend.service

[Service]
Type=exec
User=inventory
Group=inventory
WorkingDirectory=/opt/inventory-system/frontend
Environment="PATH=/opt/inventory-system/frontend/.venv/bin"
Environment="API_BASE_URL=http://localhost:8000"
ExecStart=/opt/inventory-system/frontend/.venv/bin/streamlit run app.py --server.address 0.0.0.0 --server.port 8501
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Reverse Proxy Setup

### Nginx Configuration
Create `/etc/nginx/sites-available/inventory`:
```nginx
upstream backend {
    least_conn;
    server localhost:8000 max_fails=3 fail_timeout=30s;
}

upstream frontend {
    server localhost:8501 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name inventory.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name inventory.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/inventory.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/inventory.yourdomain.com/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Frontend (Streamlit)
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
    
    # API Backend
    location /api/ {
        proxy_pass http://backend/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers
        add_header Access-Control-Allow-Origin $http_origin always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
    }
    
    # Health checks
    location /health {
        proxy_pass http://backend/health;
        access_log off;
    }
}
```

Enable site:
```bash
ln -s /etc/nginx/sites-available/inventory /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

## SSL/TLS Configuration

### Let's Encrypt with Certbot
```bash
# Install Certbot
apt install -y certbot python3-certbot-nginx

# Obtain certificate
certbot --nginx -d inventory.yourdomain.com

# Auto-renewal
certbot renew --dry-run
```

## Health Monitoring

### 1. Health Check Endpoints
- Backend: `https://inventory.yourdomain.com/health`
- Search: `https://inventory.yourdomain.com/api/v1/search/health`

### 2. Monitoring with Prometheus
Add to `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'inventory-backend'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### 3. Uptime Monitoring
Use services like:
- UptimeRobot
- Pingdom
- Custom scripts with alerting

## Backup & Recovery

### Database Backup

#### Automated Daily Backups
Create `/opt/scripts/backup-inventory.sh`:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/inventory"
DB_NAME="inventory_system"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
PGPASSWORD=$POSTGRES_PASSWORD pg_dump \
  -h $POSTGRES_HOST \
  -U $POSTGRES_USER \
  -d $DB_NAME \
  -f $BACKUP_DIR/inventory_${DATE}.sql

# Compress backup
gzip $BACKUP_DIR/inventory_${DATE}.sql

# Delete backups older than 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

# Sync to remote storage (optional)
# rclone sync $BACKUP_DIR remote:inventory-backups/
```

Add to crontab:
```bash
0 2 * * * /opt/scripts/backup-inventory.sh
```

### Recovery Procedure
```bash
# Restore from backup
gunzip -c /backup/inventory/inventory_20250703_020000.sql.gz | \
  PGPASSWORD=$POSTGRES_PASSWORD psql \
  -h $POSTGRES_HOST \
  -U $POSTGRES_USER \
  -d $DB_NAME
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed
```bash
# Test connection
PGPASSWORD=$POSTGRES_PASSWORD psql \
  -h $POSTGRES_HOST \
  -U $POSTGRES_USER \
  -d $DB_NAME \
  -c "SELECT 1"

# Check firewall
ufw status
```

#### 2. Weaviate Not Responding
```bash
# Check Weaviate health
curl http://192.168.68.97:8080/v1/.well-known/ready

# Check logs
docker logs weaviate_weaviate_1
```

#### 3. Frontend Can't Connect to Backend
```bash
# Check backend is running
curl http://localhost:8000/health

# Check nginx proxy
curl -H "Host: inventory.yourdomain.com" http://localhost/api/v1/health
```

### Debug Mode
Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
systemctl restart inventory-backend
```

## Production Checklist

### Pre-Deployment
- [ ] Environment variables configured
- [ ] Database credentials secured
- [ ] SSL certificates obtained
- [ ] Firewall rules configured
- [ ] Backup system tested
- [ ] Monitoring configured

### Security
- [ ] Change all default passwords
- [ ] Enable firewall (ufw/iptables)
- [ ] Disable root SSH access
- [ ] Configure fail2ban
- [ ] Regular security updates scheduled

### Performance
- [ ] Database indexes created
- [ ] Nginx caching configured
- [ ] Static file serving optimized
- [ ] Connection pooling configured
- [ ] Resource limits set

### Monitoring
- [ ] Health checks active
- [ ] Log aggregation configured
- [ ] Alerts configured
- [ ] Backup verification scheduled
- [ ] Performance metrics collected

### Documentation
- [ ] Deployment steps documented
- [ ] Recovery procedures tested
- [ ] Team access documented
- [ ] Change log maintained
- [ ] Incident response plan created

## Maintenance

### Regular Tasks
- **Daily**: Check health endpoints, review logs
- **Weekly**: Verify backups, check disk space
- **Monthly**: Review performance metrics, update dependencies
- **Quarterly**: Security audit, disaster recovery test

### Updates
```bash
# Update application
cd /opt/inventory-system
git pull
poetry install

# Restart services
systemctl restart inventory-backend
systemctl restart inventory-frontend

# Run migrations if needed
cd backend
poetry run alembic upgrade head
```

## Support

For issues or questions:
1. Check application logs: `journalctl -u inventory-backend -f`
2. Review this guide's troubleshooting section
3. Contact system administrator
4. Create issue in project repository