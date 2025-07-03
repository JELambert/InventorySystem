# Quick Deployment Guide

## 🚀 Proxmox LXC Deployment

### Prerequisites
- LXC container with Docker installed
- PostgreSQL running on 192.168.68.88:5432
- Weaviate running on 192.168.68.89:8080

### Quick Deploy
```bash
# Clone repository
git clone [YOUR_REPO_URL] /home/inventory-system
cd /home/inventory-system

# Configure environment
cp .env.example .env.production
nano .env.production  # Update POSTGRES_PASSWORD

# Deploy
chmod +x deploy.sh
./deploy.sh deploy
```

### Quick Update
```bash
cd /home/inventory-system
./deploy.sh redeploy
```

### Access
- **Frontend**: `http://[LXC-IP]:8501`
- **API**: `http://[LXC-IP]:8000`
- **Docs**: `http://[LXC-IP]:8000/docs`

### Login Credentials
- **admin** / admin123
- **user** / user123  
- **demo** / demo123

### Troubleshooting
```bash
./deploy.sh logs    # View logs
./deploy.sh status  # Check status
./deploy.sh stop    # Stop services
```

📖 **Full Guide**: See `PROXMOX_DEPLOYMENT_GUIDE.md`