#!/bin/bash

python manage.py migrate

python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
EOF

# Start Gunicorn with correct WSGI path
exec gunicorn --bind 0.0.0.0:8000 apps.recipes.wsgi:application
