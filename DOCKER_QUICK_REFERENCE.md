# Docker Quick Reference Card

## File Structure Overview

```
LMS_CHIETA/
├── Dockerfile                    # Development build
├── Dockerfile.prod               # Production build (optimized)
├── docker-compose.yml            # Local development stack
├── docker-compose.prod.yml       # Production stack with Nginx
├── .dockerignore                 # Build context excludes
├── .env.docker                   # Environment template
├── nginx.conf                    # Nginx reverse proxy config
├── docker-setup.sh               # Linux/macOS setup script
├── docker-setup.bat              # Windows setup script
├── DOCKER_SETUP.md               # Complete setup guide
├── DOCKERIZATION_SUMMARY.md      # Implementation details
├── DOCKER_CHECKLIST.md           # Pre-deployment checklist
└── core/settings.py              # Updated with env vars
```

---

## 🚀 Quick Start (30 seconds)

### Windows
```cmd
docker-setup.bat
```

### Linux/macOS
```bash
chmod +x docker-setup.sh
./docker-setup.sh
```

---

## 📋 Environment Variables (Most Important)

### Essential for Production

| Variable | Example | Purpose |
|----------|---------|---------|
| `SECRET_KEY` | `abc123def456...` | Django session security |
| `DEBUG` | `False` | Disable development mode |
| `ALLOWED_HOSTS` | `yourdomain.com,www.yourdomain.com` | Allowed domain names |
| `DATABASE_URL` | `postgresql://user:pass@host/db` | Production database |
| `POSTGRES_PASSWORD` | `strong-password-here` | Database password |
| `EMAIL_HOST_USER` | `your-email@gmail.com` | Gmail SMTP email |
| `EMAIL_HOST_PASSWORD` | `your-app-password` | Gmail app password |

---

## 🐳 Essential Docker Commands

```bash
# Start application
docker-compose up -d

# Stop application
docker-compose down

# View logs (follow mode)
docker-compose logs -f web

# See all running containers
docker-compose ps

# Rebuild image
docker-compose build

# Full reset (removes volumes)
docker-compose down -v
```

---

## 🔧 Django Management Commands

```bash
# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Django shell
docker-compose exec web python manage.py shell

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Custom command
docker-compose exec web python manage.py [your-command]
```

---

## 🌐 Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| Web App | http://localhost:8000 | Main application |
| Admin | http://localhost:8000/admin | Django admin |
| Database | localhost:5432 | PostgreSQL |
| Nginx | http://localhost (prod) | Reverse proxy |

---

## 🔑 Default Credentials

| Service | Username | Password |
|---------|----------|----------|
| Admin | admin | admin123 |
| Database | lms_user | lms_password_change_me |

⚠️ **CHANGE THESE IMMEDIATELY IN PRODUCTION!**

---

## 📊 Service Stack

### Development (docker-compose.yml)
- PostgreSQL 16 (Alpine)
- Django Web (Python 3.12)
- Redis 7 (Optional)

### Production (docker-compose.prod.yml)
- Nginx (Reverse proxy + static files)
- Django Web (Gunicorn + Uvicorn)
- PostgreSQL 16 (External recommended)

---

## 🐛 Quick Troubleshooting

### Port in use?
```bash
# Change in .env.local
WEB_PORT=8001
DB_PORT=5433
```

### Can't connect to database?
```bash
docker-compose logs db
docker-compose exec web python manage.py dbshell
```

### Rebuild everything?
```bash
docker-compose down -v --remove-orphans
docker-compose build --no-cache
docker-compose up -d
```

### See what's broken?
```bash
docker-compose logs web
# or
docker-compose exec web python manage.py check
```

---

## 📈 Performance Settings (Production)

In `docker-compose.prod.yml`:
- **Workers**: 4 (adjust based on CPU cores)
- **Timeout**: 120 seconds
- **Rate Limiting**: 10 req/s (general), 30 req/s (API)
- **Gzip Compression**: Enabled
- **Static Cache**: 30 days
- **Media Cache**: 7 days

---

## 🔐 Security Checklist

- [ ] `SECRET_KEY` is unique and strong
- [ ] `DEBUG = False` in production
- [ ] Database password is strong
- [ ] SSL/TLS enabled (nginx)
- [ ] `ALLOWED_HOSTS` configured correctly
- [ ] Email credentials from environment
- [ ] Admin password changed from default
- [ ] Database backups enabled

---

## 📚 Documentation Files

1. **DOCKER_SETUP.md** - Full setup guide (read first!)
2. **DOCKERIZATION_SUMMARY.md** - Technical details
3. **DOCKER_CHECKLIST.md** - Pre-deployment verification

---

## 🔄 CI/CD Integration Template

```yaml
# GitHub Actions example
deploy:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v2
    - uses: docker/setup-buildx-action@v1
    - uses: docker/build-push-action@v2
      with:
        context: .
        push: true
        tags: registry/app:latest
```

---

## 💡 Pro Tips

1. **Hot Reload in Development**: Code changes reflect immediately (volumes enabled)
2. **Database Shell**: `docker-compose exec db psql -U lms_user -d lms_db`
3. **Clear Cache**: `docker-compose exec web python manage.py clear_cache`
4. **Backup DB**: `docker-compose exec db pg_dump -U lms_user lms_db > backup.sql`
5. **Restore DB**: `docker-compose exec -T db psql -U lms_user lms_db < backup.sql`

---

## 🆘 Getting Help

1. Check `DOCKER_SETUP.md` troubleshooting section
2. Run `docker-compose logs [service]` to see errors
3. Use `docker-compose exec web python manage.py check` to validate
4. Check Django logs: `docker-compose logs -f web | grep ERROR`

---

## ✅ Verification Checklist

After starting the application:

```bash
# 1. Check all services running
docker-compose ps

# 2. Verify web connectivity
curl http://localhost:8000

# 3. Check database connection
docker-compose exec web python manage.py dbshell

# 4. Verify admin panel
curl http://localhost:8000/admin

# 5. Check static files
curl http://localhost:8000/static/

# 6. View application logs
docker-compose logs web | head -20
```

---

**Generated:** January 23, 2026  
**Django Version:** 5.2.1  
**Python Version:** 3.12
