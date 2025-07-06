# Recipe Manager - Docker Setup

A Django-based recipe management application with Docker Compose setup for easy development and deployment.

## Quick Start with Docker

### Prerequisites
- Docker
- Docker Compose

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd recipes
   ```

2. **Copy environment variables**
   ```bash
   cp .env.example .env
   ```

3. **Start the application**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - Web application: http://localhost:8000
   - Admin interface: http://localhost:8000/admin
   - Default admin credentials: admin/admin123

### Services

The Docker setup includes:

- **Django Web Application** (Port 8000)
  - Python 3.11
  - Django with all dependencies
  - Live code reloading for development
  
- **PostgreSQL Database** (Port 5432)
  - PostgreSQL 15
  - Persistent data storage
  
- **Redis Cache** (Port 6379)
  - Redis 7-alpine
  - Session storage and caching

### Environment Variables

Key environment variables (see `.env.example`):

```env
# Django Configuration
SECRET_KEY=your-secret-key-change-this-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database Configuration
POSTGRES_DB=recipes_db
POSTGRES_USER=recipes_user
POSTGRES_PASSWORD=recipes_password

# Redis Configuration
REDIS_URL=redis://redis:6379/1

# Superuser Configuration
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=admin123
```

### Common Commands

```bash
# Start services
docker-compose up

# Start services in background
docker-compose up -d

# Build and start services
docker-compose up --build

# Stop services
docker-compose down

# View logs
docker-compose logs -f web

# Run Django commands
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py collectstatic

# Access Django shell
docker-compose exec web python manage.py shell

# Access database
docker-compose exec db psql -U recipes_user -d recipes_db
```

### Development Features

- **Live Code Reloading**: Code changes are automatically reflected
- **Volume Mounts**: Source code, media files, and database data persist
- **Health Checks**: Services monitor their own health
- **Environment Variables**: Easy configuration management

### Production Deployment

For production deployment:

1. **Update environment variables**
   ```bash
   cp .env.example .env.prod
   # Edit .env.prod with production values
   ```

2. **Use production compose file**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Troubleshooting

**Database Connection Issues:**
```bash
# Check if database is running
docker-compose ps

# Check database logs
docker-compose logs db

# Restart database service
docker-compose restart db
```

**Permission Issues:**
```bash
# Fix file permissions
sudo chown -R $USER:$USER .
```

**Clean Start:**
```bash
# Remove all containers and volumes
docker-compose down -v
docker-compose up --build
```

## Local Development (without Docker)

If you prefer to run without Docker:

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run migrations**
   ```bash
   python manage.py migrate
   ```

3. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

4. **Run development server**
   ```bash
   python manage.py runserver
   ```

Note: Local development uses SQLite by default. Set `DATABASE_URL` environment variable to use PostgreSQL locally.