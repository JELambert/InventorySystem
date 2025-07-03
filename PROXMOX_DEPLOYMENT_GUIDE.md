# Proxmox LXC Deployment Guide - Home Inventory System

This guide provides step-by-step instructions for deploying the Home Inventory System to a Proxmox LXC container with Docker.

## 📋 Prerequisites

### Infrastructure Requirements
- **Proxmox LXC Container** with Docker installed
- **External PostgreSQL Database** (192.168.68.88:5432)
- **External Weaviate Instance** (192.168.68.89:8080)
- **Git** installed in the LXC container
- **Internet access** for pulling Docker images

### Network Configuration
- LXC container has network access to PostgreSQL and Weaviate instances
- Ports 8000 (Backend API) and 8501 (Frontend) are accessible
- Firewall rules allow database connections

## 🚀 Deployment Methods

### Method 1: Automated Deployment (Recommended)

Use the included deployment script for easy setup and updates:

```bash
# Make script executable
chmod +x deploy.sh

# Fresh deployment (first time)
./deploy.sh deploy

# Update existing deployment
./deploy.sh redeploy

# Monitor logs
./deploy.sh logs

# Check status
./deploy.sh status
```

### Method 2: Manual Deployment

#### Step 1: Clone Repository
```bash
# Clone to /home directory
cd /home
git clone https://github.com/yourusername/InventorySystem.git home-inventory-system
cd home-inventory-system
```

#### Step 2: Configure Environment
```bash
# Copy environment template
cp .env.example .env.production

# Edit configuration file
nano .env.production
```

**Required Configuration:**
```bash
# Update these values in .env.production
POSTGRES_PASSWORD=your_actual_postgres_password
POSTGRES_HOST=192.168.68.88
WEAVIATE_URL=http://192.168.68.89:8080
```

#### Step 3: Deploy Services
```bash
# Build and start services
docker-compose --env-file .env.production up -d --build

# Verify services are running
docker-compose --env-file .env.production ps
```

## 🔄 Regular Update Process

### Quick Update Commands
```bash
cd /home/home-inventory-system

# Stop services
docker-compose --env-file .env.production down

# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose --env-file .env.production up -d --build

# Check status
docker-compose --env-file .env.production ps
```

### Using the Deployment Script
```bash
# Simple one-command update
./deploy.sh redeploy
```

## 🌐 Service Access

After successful deployment, access the services at:

- **Frontend Application**: `http://[LXC-IP]:8501`
- **Backend API**: `http://[LXC-IP]:8000`
- **API Documentation**: `http://[LXC-IP]:8000/docs`
- **Health Check**: `http://[LXC-IP]:8000/health`

### Default Authentication Credentials
- **Admin**: username=`admin`, password=`admin123`
- **User**: username=`user`, password=`user123`
- **Demo**: username=`demo`, password=`demo123`

## 🔍 Troubleshooting

### Check Service Status
```bash
# View service status
docker-compose --env-file .env.production ps

# View logs
docker-compose --env-file .env.production logs -f

# Check individual service logs
docker-compose --env-file .env.production logs backend
docker-compose --env-file .env.production logs frontend
```

### Common Issues

#### Database Connection Errors
1. Verify PostgreSQL is running on 192.168.68.88:5432
2. Check network connectivity: `ping 192.168.68.88`
3. Verify credentials in `.env.production`
4. Check firewall rules

#### Weaviate Connection Issues
1. Verify Weaviate is running on 192.168.68.89:8080
2. Test connectivity: `curl http://192.168.68.89:8080/v1/.well-known/live`
3. Check if semantic search features work in the application

#### Container Build Failures
1. Check Docker disk space: `docker system df`
2. Clean up unused resources: `docker system prune -f`
3. Rebuild without cache: `docker-compose --env-file .env.production build --no-cache`

#### Authentication Issues
1. Verify `frontend/config/auth_config.yaml` is properly mounted
2. Check if streamlit-authenticator dependency is installed
3. Review frontend logs for authentication errors

### Service Health Checks
```bash
# Backend health check
curl http://localhost:8000/health

# Frontend health check (if exposed)
curl http://localhost:8501/_stcore/health

# Database connectivity test
docker-compose --env-file .env.production exec backend python -c "
from app.database.base import get_session
import asyncio
async def test():
    async for session in get_session():
        print('Database connection successful')
        break
asyncio.run(test())
"
```

## 🔧 Advanced Configuration

### Environment Variables Reference
```bash
# Application Settings
ENVIRONMENT=production              # Set to 'production'
DEBUG=false                        # Disable debug mode
LOG_LEVEL=INFO                     # Logging level

# Database Configuration
POSTGRES_HOST=192.168.68.88        # PostgreSQL server IP
POSTGRES_PORT=5432                 # PostgreSQL port
POSTGRES_DB=inventory_system       # Database name
POSTGRES_USER=postgres             # Database username
POSTGRES_PASSWORD=your_password    # Database password

# Weaviate Configuration
WEAVIATE_URL=http://192.168.68.89:8080  # Weaviate server URL
WEAVIATE_ENABLED=true              # Enable semantic search

# API Configuration
API_CORS_ORIGINS=*                 # CORS settings (restrict in production)
```

### Custom Docker Compose Overrides
Create `docker-compose.override.yml` for environment-specific customizations:

```yaml
version: '3.8'
services:
  backend:
    ports:
      - "80:8000"  # Map to port 80
  frontend:
    ports:
      - "8080:8501"  # Map to port 8080
```

### Resource Limits
Add resource constraints to `docker-compose.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
  frontend:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.3'
```

## 🔐 Security Considerations

### Production Hardening
1. **Change default passwords** in `auth_config.yaml`
2. **Restrict CORS origins** in production
3. **Use strong database passwords**
4. **Enable firewall rules** for database access only
5. **Consider HTTPS** with reverse proxy (nginx/Caddy)
6. **Regular updates** of Docker images and dependencies

### Secrets Management
- Store sensitive credentials in `.env.production` (not in Git)
- Consider using Docker secrets in production
- Regularly rotate database passwords
- Monitor access logs

## 📊 Monitoring and Maintenance

### Regular Maintenance Tasks
```bash
# Update system packages (in LXC)
apt update && apt upgrade

# Clean up Docker resources
docker system prune -f

# Check disk usage
df -h
docker system df

# Backup database (on PostgreSQL server)
pg_dump -h 192.168.68.88 -U postgres inventory_system > backup.sql
```

### Performance Monitoring
- Monitor container resource usage: `docker stats`
- Check application logs regularly
- Monitor database performance on PostgreSQL server
- Track Weaviate performance and memory usage

## 📝 Deployment Checklist

### Pre-Deployment
- [ ] PostgreSQL server is running and accessible
- [ ] Weaviate server is running and accessible
- [ ] LXC container has Docker installed
- [ ] Network connectivity between services verified
- [ ] `.env.production` configured with correct credentials

### Post-Deployment
- [ ] All services started successfully
- [ ] Frontend accessible at `http://[LXC-IP]:8501`
- [ ] Backend API accessible at `http://[LXC-IP]:8000`
- [ ] Health check returns successful response
- [ ] Authentication system working
- [ ] Database connections established
- [ ] Semantic search functionality tested

### Maintenance Schedule
- **Daily**: Check service status and logs
- **Weekly**: Review resource usage and performance
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Full backup and disaster recovery test

---

## 📞 Support

For deployment issues:
1. Check logs first: `./deploy.sh logs`
2. Verify service status: `./deploy.sh status`
3. Review this troubleshooting guide
4. Check network connectivity to external services
5. Consult the main project documentation

Happy deploying! 🚀