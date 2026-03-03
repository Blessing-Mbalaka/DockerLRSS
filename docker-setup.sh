#!/bin/bash

# Docker setup script for LMS application
# This script helps initialize the Docker environment

set -e

echo "================================"
echo "LMS Docker Setup Script"
echo "================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker is installed${NC}"

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker Compose is installed${NC}"
echo ""

# Create .env.local if it doesn't exist
if [ ! -f .env.local ]; then
    echo -e "${YELLOW}Creating .env.local from .env.docker...${NC}"
    cp .env.docker .env.local
    echo -e "${GREEN}✓ .env.local created${NC}"
else
    echo -e "${YELLOW}✓ .env.local already exists${NC}"
fi

echo ""
echo -e "${YELLOW}Please edit .env.local with your configuration:${NC}"
echo "  - SECRET_KEY: Generate a strong key or use: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\""
echo "  - DEBUG: Set to True for development, False for production"
echo "  - ALLOWED_HOSTS: Add your domain names"
echo "  - Email credentials: Add your Gmail SMTP credentials"
echo ""

# Ask if user wants to build and run
read -p "Do you want to build and start the application now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${YELLOW}Building Docker image...${NC}"
    docker-compose build
    
    echo ""
    echo -e "${YELLOW}Starting services...${NC}"
    docker-compose up -d
    
    echo ""
    sleep 5
    
    echo -e "${YELLOW}Waiting for database to be ready...${NC}"
    docker-compose exec -T web python manage.py dbshell <<< "SELECT 1;" > /dev/null 2>&1 || sleep 10
    
    echo ""
    echo -e "${GREEN}✓ Application started successfully!${NC}"
    echo ""
    echo -e "${YELLOW}Application Details:${NC}"
    echo "  - Web Application: http://localhost:8000"
    echo "  - Admin Panel: http://localhost:8000/admin"
    echo "  - Default Admin: admin / admin123 (change immediately!)"
    echo "  - Database: localhost:5432"
    echo ""
    echo -e "${YELLOW}Useful Commands:${NC}"
    echo "  - View logs: docker-compose logs -f web"
    echo "  - Run migrations: docker-compose exec web python manage.py migrate"
    echo "  - Create superuser: docker-compose exec web python manage.py createsuperuser"
    echo "  - Stop services: docker-compose down"
    echo ""
else
    echo ""
    echo -e "${YELLOW}Setup complete. To start the application manually, run:${NC}"
    echo "  docker-compose up -d"
    echo ""
fi
