# Docker Setup for LMS Application

This guide explains how to build and run the LMS Django application using Docker.

## Prerequisites

- [Docker](https://www.docker.com/products/docker-desktop) installed
- [Docker Compose](https://docs.docker.com/compose/install/) installed (included with Docker Desktop)

## Quick Start

### 1. Configure Environment Variables

Copy the example environment file and customize it:

```bash
cp .env.docker .env.local
```

Edit `.env.local` with your specific configuration:
- `SECRET_KEY`: Generate a strong secret key for production
- `DEBUG`: Set to `False` for production
- `ALLOWED_HOSTS`: Add your domain names
- `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD`: Gmail SMTP credentials
- `POSTGRES_PASSWORD`: Change the default database password

### 2. Build the Docker Image

```bash
docker-compose build
```

This will:
- Build the Django application image with Python 3.12
- Install all dependencies from requirements.txt
- Collect static files
- Prepare the application for running

### 3. Start the Services

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database (accessible at `localhost:5432`)
- Django web application (accessible at `http://localhost:8000`)
- Redis cache (optional, with `--profile with-cache`)

### 4. Run Migrations and Create Superuser

The entrypoint script automatically runs migrations and creates a default superuser.

To access the admin panel:
- URL: `http://localhost:8000/admin`
- Username: `admin`
- Password: `admin123` (change this immediately in production!)

### 5. Verify the Application

```bash
# View logs
docker-compose logs -f web

# Access the shell
docker-compose exec web python manage.py shell

# Create additional superuser
docker-compose exec web python manage.py createsuperuser
```

## Environment Variables

### Required Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `False` | Enable debug mode (development only) |
| `SECRET_KEY` | Generated | Django secret key for sessions/CSRF |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated allowed hosts |
| `DATABASE_URL` | Uses PostgreSQL in compose | Database connection string |

### Database Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | `lms_db` | Database name |
| `POSTGRES_USER` | `lms_user` | Database user |
| `POSTGRES_PASSWORD` | `lms_password_change_me` | Database password |
| `DB_PORT` | `5432` | Database port |

### Email Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EMAIL_BACKEND` | Console (dev) / SMTP (prod) | Email backend service |
| `EMAIL_HOST` | `smtp.gmail.com` | SMTP server address |
| `EMAIL_PORT` | `587` | SMTP server port |
| `EMAIL_HOST_USER` | `` | Gmail email address |
| `EMAIL_HOST_PASSWORD` | `` | Gmail app password |
| `EMAIL_USE_TLS` | `True` | Use TLS for email |
| `DEFAULT_FROM_EMAIL` | `noreply@lms.com` | Default sender email |

## Common Commands

### View logs for a specific service

```bash
# Django web logs
docker-compose logs -f web

# Database logs
docker-compose logs -f db

# All logs
docker-compose logs -f
```

### Execute Django commands

```bash
# Create migrations
docker-compose exec web python manage.py makemigrations

# Apply migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Run custom management command
docker-compose exec web python manage.py [command]
```

### Access the database

```bash
# PostgreSQL shell
docker-compose exec db psql -U lms_user -d lms_db

# Common PostgreSQL commands:
# \dt - list tables
# \du - list users
# SELECT VERSION(); - show database version
```

### Stop and clean up

```bash
# Stop containers (keeps data)
docker-compose down

# Stop containers and remove volumes (removes database data)
docker-compose down -v

# Remove all containers, networks (nuclear option)
docker-compose down -v --remove-orphans
```

## Production Deployment

For production deployment:

1. **Security**: 
   - Set `DEBUG=False`
   - Generate a strong `SECRET_KEY`
   - Use strong `POSTGRES_PASSWORD`
   - Enable `EMAIL_USE_TLS`

2. **Environment**: Create `.env.production` with production settings

3. **Database**: 
   - Use a managed database service (RDS, Cloud SQL, etc.)
   - Update `DATABASE_URL` accordingly

4. **Static Files**: 
   - Configure S3 or similar for static file storage
   - Update `STATIC_URL` and `STATIC_ROOT`

5. **Email**: 
   - Configure a transactional email service (SendGrid, Mailgun, etc.)
   - Update email configuration variables

6. **Docker Registry**: 
   - Build and push image to Docker registry (Docker Hub, ECR, etc.)
   - Use the registry image in production compose file

Example production docker-compose:
```yaml
services:
  web:
    image: your-registry/lms:latest
    env_file: .env.production
    # ... rest of config
```

## Troubleshooting

### Application won't start

```bash
# Check logs
docker-compose logs web

# Verify environment variables are set
docker-compose exec web env | grep DJANGO

# Recreate container
docker-compose up --build web
```

### Database connection errors

```bash
# Check if database is healthy
docker-compose ps

# Check database logs
docker-compose logs db

# Manually test connection
docker-compose exec web python manage.py dbshell
```

### Permission denied errors

On Linux, you may need to adjust permissions:
```bash
sudo chown -R 1000:1000 media/
```

### Port conflicts

If port 8000 or 5432 is already in use, modify in `.env.local`:
```bash
WEB_PORT=8001
DB_PORT=5433
```

Then update docker-compose.yml port mappings accordingly.

## Additional Resources

- [Django Docker Documentation](https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/gunicorn/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [Best Practices for Django in Docker](https://docs.docker.com/language/python/build-images/)
