#!/bin/bash
set -e

# Start nginx
service nginx start

cd /app

# Apply migrations & collect static
python manage.py migrate
python manage.py collectstatic --noinput

# Create superuser if not exists
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
EOF

# Start Gunicorn in the background
gunicorn --bind 127.0.0.1:8001 apps.recipes.wsgi:application &

# Keep container running
tail -f /var/log/nginx/access.log