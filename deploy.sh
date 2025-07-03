#!/bin/bash

# Home Inventory System - Proxmox LXC Deployment Script
# This script automates the deployment and redeployment process

set -e  # Exit on any error

# Configuration
PROJECT_NAME="home-inventory-system"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env.production"
GITHUB_REPO="https://github.com/yourusername/InventorySystem.git"  # Update this with your actual repo URL

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
    fi
    
    if ! command -v git &> /dev/null; then
        error "Git is not installed. Please install Git first."
    fi
    
    success "All prerequisites are available"
}

# Function to deploy fresh installation
fresh_deploy() {
    log "Starting fresh deployment..."
    
    # Clone repository
    log "Cloning repository..."
    if [ -d "/home/$PROJECT_NAME" ]; then
        warning "Project directory already exists. Use 'redeploy' command instead."
        exit 1
    fi
    
    git clone "$GITHUB_REPO" "/home/$PROJECT_NAME"
    cd "/home/$PROJECT_NAME"
    
    # Setup environment file
    setup_environment
    
    # Build and start services
    deploy_services
    
    success "Fresh deployment completed!"
}

# Function to redeploy (update existing installation)
redeploy() {
    log "Starting redeployment..."
    
    if [ ! -d "/home/$PROJECT_NAME" ]; then
        error "Project directory not found. Use 'deploy' command for fresh installation."
    fi
    
    cd "/home/$PROJECT_NAME"
    
    # Stop existing services
    log "Stopping existing services..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down || true
    
    # Pull latest changes
    log "Pulling latest changes from repository..."
    git pull origin main
    
    # Deploy services
    deploy_services
    
    success "Redeployment completed!"
}

# Function to setup environment file
setup_environment() {
    log "Setting up environment configuration..."
    
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f ".env.example" ]; then
            cp ".env.example" "$ENV_FILE"
            warning "Environment file created from template. Please edit $ENV_FILE with your configuration."
            warning "Especially set POSTGRES_PASSWORD before continuing."
            echo "Press Enter when you have configured $ENV_FILE..."
            read
        else
            error "No environment template found. Please create $ENV_FILE manually."
        fi
    else
        log "Environment file already exists: $ENV_FILE"
    fi
}

# Function to deploy services
deploy_services() {
    log "Building and starting services..."
    
    # Build and start services
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build
    
    # Wait for services to be healthy
    log "Waiting for services to be healthy..."
    sleep 30
    
    # Check service status
    check_services
}

# Function to check service status
check_services() {
    log "Checking service status..."
    
    # Check if services are running
    if docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps | grep -q "Up"; then
        success "Services are running"
        
        # Show service URLs
        echo ""
        echo "🌐 Service URLs:"
        echo "   Frontend: http://$(hostname -I | awk '{print $1}'):8501"
        echo "   Backend API: http://$(hostname -I | awk '{print $1}'):8000"
        echo "   Health Check: http://$(hostname -I | awk '{print $1}'):8000/health"
        echo ""
        
    else
        warning "Some services may not be running properly"
        echo "Service status:"
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
    fi
}

# Function to show logs
show_logs() {
    cd "/home/$PROJECT_NAME"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f
}

# Function to stop services
stop_services() {
    log "Stopping services..."
    cd "/home/$PROJECT_NAME"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
    success "Services stopped"
}

# Function to show status
show_status() {
    log "Service status:"
    cd "/home/$PROJECT_NAME"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
}

# Function to clean up
cleanup() {
    log "Cleaning up..."
    cd "/home/$PROJECT_NAME"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down -v
    docker system prune -f
    success "Cleanup completed"
}

# Main script logic
case "${1:-help}" in
    "deploy")
        check_prerequisites
        fresh_deploy
        ;;
    "redeploy")
        check_prerequisites
        redeploy
        ;;
    "logs")
        show_logs
        ;;
    "stop")
        stop_services
        ;;
    "status")
        show_status
        ;;
    "cleanup")
        cleanup
        ;;
    "help"|*)
        echo "Home Inventory System Deployment Script"
        echo ""
        echo "Usage: $0 [COMMAND]"
        echo ""
        echo "Commands:"
        echo "  deploy     Fresh deployment (clone repo and setup)"
        echo "  redeploy   Update existing deployment (git pull and rebuild)"
        echo "  logs       Show service logs (follow mode)"
        echo "  stop       Stop all services"
        echo "  status     Show service status"
        echo "  cleanup    Stop services and clean up Docker resources"
        echo "  help       Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 deploy       # Fresh installation"
        echo "  $0 redeploy     # Update existing deployment"
        echo "  $0 logs         # Monitor logs"
        echo ""
        ;;
esac