@echo off
REM Docker setup script for LMS application (Windows)
REM This script helps initialize the Docker environment

setlocal enabledelayedexpansion

echo.
echo ================================
echo LMS Docker Setup Script
echo ================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed. Please install Docker Desktop first.
    exit /b 1
)

echo [OK] Docker is installed

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker Compose is not installed. Please install Docker Desktop first.
    exit /b 1
)

echo [OK] Docker Compose is installed
echo.

REM Create .env.local if it doesn't exist
if not exist .env.local (
    echo [INFO] Creating .env.local from .env.docker...
    copy .env.docker .env.local
    echo [OK] .env.local created
) else (
    echo [OK] .env.local already exists
)

echo.
echo [INFO] Please edit .env.local with your configuration:
echo   - SECRET_KEY: Generate a strong key
echo   - DEBUG: Set to True for development, False for production
echo   - ALLOWED_HOSTS: Add your domain names
echo   - Email credentials: Add your Gmail SMTP credentials
echo.

REM Ask if user wants to build and run
set /p response="Do you want to build and start the application now? (y/n): "

if /i "%response%"=="y" (
    echo.
    echo [INFO] Building Docker image...
    docker-compose build
    
    echo.
    echo [INFO] Starting services...
    docker-compose up -d
    
    echo.
    echo [INFO] Waiting for services to be ready...
    timeout /t 5 /nobreak
    
    echo.
    echo [OK] Application started successfully!
    echo.
    echo [INFO] Application Details:
    echo   - Web Application: http://localhost:8000
    echo   - Admin Panel: http://localhost:8000/admin
    echo   - Default Admin: admin / admin123 (change immediately!)
    echo   - Database: localhost:5432
    echo.
    echo [INFO] Useful Commands:
    echo   - View logs: docker-compose logs -f web
    echo   - Run migrations: docker-compose exec web python manage.py migrate
    echo   - Create superuser: docker-compose exec web python manage.py createsuperuser
    echo   - Stop services: docker-compose down
    echo.
    
    REM Open browser automatically
    timeout /t 2 /nobreak
    start http://localhost:8000
) else (
    echo.
    echo [INFO] Setup complete. To start the application manually, run:
    echo   docker-compose up -d
    echo.
)

endlocal
