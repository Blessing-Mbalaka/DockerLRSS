#!/bin/bash
set -e

# Run migrations
python manage.py migrate

# Create superuser if it doesn't exist
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email="admin@example.com").exists():
    User.objects.create_superuser("admin", "admin@example.com", "admin123")
    print("Superuser created")
else:
    print("Superuser already exists")
END

# Start the application
exec "$@"
