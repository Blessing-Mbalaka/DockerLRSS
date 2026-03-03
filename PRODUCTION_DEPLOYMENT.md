# Production Deployment Guide

## Prerequisites

- Docker and Docker Compose installed on production server
- Domain name configured
- SSL/TLS certificates ready
- PostgreSQL database setup (managed or self-hosted)
- Email service credentials (Gmail, SendGrid, etc.)

## Step-by-Step Production Deployment

### 1. Prepare Production Environment File

Create `.env.prod` based on `.env.docker`:

```bash
# Django Configuration
DEBUG=False
SECRET_KEY=<generate-strong-secret-key>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database (external PostgreSQL recommended)
DATABASE_URL=postgresql://user:password@db-host:5432/lms_db

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Static/Media Files
STATIC_URL=/static/
STATIC_ROOT=/app/staticfiles
MEDIA_URL=/media/
MEDIA_ROOT=/app/media

# Server Configuration
WEB_PORT=8000
```

### 2. Generate Strong Secret Key

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 3. Configure SSL Certificates

Place SSL certificates in `ssl/` directory:

```
ssl/
├── certificate.crt    (or certificate.pem)
└── private.key        (or private-key.pem)
```

### 4. Update Nginx Configuration

Uncomment HTTPS section in `nginx.conf`:

```nginx
# Uncomment and configure:
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/certificate.crt;
    ssl_certificate_key /etc/nginx/ssl/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # HSTS (enforce HTTPS)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # ... rest of configuration
}

# HTTP redirect
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}
```

### 5. Build Production Image

```bash
docker-compose build -f docker-compose.prod.yml
```

### 6. Deploy with Production Compose

```bash
# Using production config
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Or with specific image tag
docker-compose -f docker-compose.prod.yml -e REGISTRY=your-registry up -d
```

### 7. Verify Deployment

```bash
# Check all services
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f

# Health check
curl https://your-domain.com/health

# Admin panel test
curl https://your-domain.com/admin
```

### 8. Database Setup

```bash
# Run migrations (if using external database)
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate --noinput

# Create superuser
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

# Collect static files (if needed)
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

### 9. Setup Backups

Create a backup script (`backup.sh`):

```bash
#!/bin/bash
# Daily backup script

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/lms"

mkdir -p $BACKUP_DIR

# Backup database
docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U $POSTGRES_USER $POSTGRES_DB \
    > $BACKUP_DIR/lms_db_$DATE.sql

# Backup media files
tar -czf $BACKUP_DIR/lms_media_$DATE.tar.gz /app/media

# Keep only last 30 days
find $BACKUP_DIR -name "lms_*" -mtime +30 -delete

echo "Backup completed: $DATE"
```

Add to crontab:
```bash
crontab -e
# Add: 0 2 * * * /path/to/backup.sh
```

### 10. Monitor Application

```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f web

# Check memory usage
docker-compose -f docker-compose.prod.yml stats

# Performance monitoring
docker-compose -f docker-compose.prod.yml top web
```

---

## Production Checklist

### Pre-Deployment
- [ ] Django migrations created and tested locally
- [ ] `DEBUG=False` set in `.env.prod`
- [ ] Strong `SECRET_KEY` generated
- [ ] SSL certificates obtained and validated
- [ ] Database created and accessible
- [ ] Email credentials verified
- [ ] Static files configuration tested
- [ ] Media directory permissions set

### Deployment
- [ ] Production image built successfully
- [ ] Containers running and healthy
- [ ] Database migrations applied
- [ ] Superuser created
- [ ] Static files collected
- [ ] Nginx serving correctly

### Post-Deployment
- [ ] Application accessible via HTTPS
- [ ] Admin panel working
- [ ] Email sending verified
- [ ] Database backup scheduled
- [ ] Monitoring configured
- [ ] Performance acceptable
- [ ] Security scan passed

---

## Scaling Recommendations

### For High Traffic

Update `docker-compose.prod.yml`:

```yaml
web:
  environment:
    - GUNICORN_WORKERS=8  # Increase from 4
    - GUNICORN_THREADS=2
```

Or use Docker Swarm/Kubernetes for multiple instances.

### Database Optimization

```sql
-- Create indexes for common queries
CREATE INDEX idx_user_email ON auth_user(email);
CREATE INDEX idx_paper_user ON core_paper(created_by_id);
```

### Caching Strategy

Enable Redis in production:

```yaml
# In docker-compose.prod.yml
redis:
  image: redis:7-alpine
  
# In settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
    }
}
```

---

## Troubleshooting Production Issues

### Container Won't Start
```bash
docker-compose -f docker-compose.prod.yml logs web | grep ERROR
docker-compose -f docker-compose.prod.yml build --no-cache
```

### Database Connection Error
```bash
# Check if database is accessible
docker-compose -f docker-compose.prod.yml exec web python manage.py dbshell
```

### HTTPS Issues
```bash
# Check certificate validity
openssl x509 -in ssl/certificate.crt -text -noout

# Verify nginx config
docker-compose -f docker-compose.prod.yml exec nginx nginx -t
```

### Performance Issues
```bash
# Check resource usage
docker-compose -f docker-compose.prod.yml stats

# Increase workers if CPU-bound
# Increase memory if memory-bound
# Add caching if database-bound
```

---

## Maintenance Tasks

### Weekly
- [ ] Check disk space
- [ ] Review error logs
- [ ] Verify backups completed

### Monthly
- [ ] Update security patches
- [ ] Review resource usage
- [ ] Clean up old logs
- [ ] Check SSL certificate expiration

### Quarterly
- [ ] Performance optimization
- [ ] Database maintenance
- [ ] Security audit
- [ ] Disaster recovery drill

---

## Environment Variables Reference

| Variable | Type | Recommended Value |
|----------|------|-------------------|
| `SECRET_KEY` | string | 50+ character random string |
| `DEBUG` | bool | False |
| `ALLOWED_HOSTS` | list | yourdomain.com,www.yourdomain.com |
| `DATABASE_URL` | URL | postgresql://user:pass@host/db |
| `POSTGRES_PASSWORD` | string | 16+ character random |
| `EMAIL_HOST_USER` | email | your-email@gmail.com |
| `EMAIL_HOST_PASSWORD` | string | Gmail app password |
| `STATIC_ROOT` | path | /app/staticfiles |
| `MEDIA_ROOT` | path | /app/media |
| `WEB_PORT` | int | 8000 |

---

## Security Best Practices

1. **SSL/TLS**: Always use HTTPS in production
2. **Secrets**: Never commit `.env` files
3. **Updates**: Keep Docker images updated
4. **Monitoring**: Set up alerts for failures
5. **Backups**: Test restoration regularly
6. **Logs**: Centralize and monitor logs
7. **Firewall**: Restrict access to necessary ports
8. **Database**: Use strong passwords, encrypted connections
9. **CDN**: Consider CDN for static assets
10. **DDoS**: Implement rate limiting

---

## Disaster Recovery

### Database Recovery
```bash
# Restore from backup
docker-compose -f docker-compose.prod.yml exec -T db psql -U $POSTGRES_USER $POSTGRES_DB < backup.sql
```

### Application Recovery
```bash
# Rebuild from scratch
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

### Media Files Recovery
```bash
# Restore media backup
tar -xzf backup/media_backup.tar.gz -C /app/
```

---

## Monitoring and Alerting

### Docker Health Checks
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Logging
```bash
# View all logs
docker-compose -f docker-compose.prod.yml logs

# Follow logs in real-time
docker-compose -f docker-compose.prod.yml logs -f

# Filter by service
docker-compose -f docker-compose.prod.yml logs web | grep ERROR
```

---

## Support Resources

- Django Deployment: https://docs.djangoproject.com/en/5.2/howto/deployment/
- Docker in Production: https://docs.docker.com/config/containers/
- PostgreSQL: https://www.postgresql.org/docs/
- Nginx: https://nginx.org/en/docs/

---

**Last Updated:** January 23, 2026  
**Status:** Production Ready
