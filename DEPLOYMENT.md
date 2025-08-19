# OIDC Production Deployment Guide

This guide explains how to deploy the OIDC application using Docker Compose in a production environment.

## 🏗️ Architecture

The deployment consists of 4 main services:

- **PostgreSQL**: Database for storing credentials and verification logs
- **Flask Backend**: Python API server handling OIDC operations
- **Angular Frontend**: Static web application served by Nginx
- **Nginx**: Reverse proxy with SSL termination and load balancing

## 📋 Prerequisites

- Docker and Docker Compose installed
- SSL certificates for your domain (for production)
- At least 2GB RAM and 10GB disk space

## 🚀 Quick Start

### 1. Configure Environment Variables

```bash
# Copy the environment template
cp env.example .env

# Edit the .env file with your production values
nano .env
```

**Required environment variables:**
- `POSTGRES_PASSWORD`: Secure password for PostgreSQL
- `SECRET_KEY`: Flask secret key for session management
- `ISSUER`: Your OIDC issuer URL (e.g., https://your-domain.com)
- `API_URL`: Frontend API URL (e.g., https://your-domain.com)

### 2. SSL Certificates

For production, place your SSL certificates in `nginx/ssl/`:
- `nginx/ssl/cert.pem` - SSL certificate
- `nginx/ssl/key.pem` - SSL private key

For development, the deployment script can generate self-signed certificates.

### 3. Deploy

```bash
# Run the deployment script
./deploy.sh
```

Or manually:
```bash
# Build and start all services
docker-compose up -d --build

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

## 🔧 Service Configuration

### PostgreSQL
- **Port**: 5432 (internal only)
- **Database**: oidc_db
- **User**: oidc_user
- **Data**: Persisted in Docker volume

### Flask Backend
- **Port**: 5000 (internal only)
- **Workers**: 4 Gunicorn workers
- **Health Check**: `/health` endpoint
- **Dependencies**: PostgreSQL

### Angular Frontend
- **Build**: Multi-stage Docker build
- **Output**: Static files served by Nginx
- **Environment**: Production optimized

### Nginx
- **Ports**: 80 (HTTP → HTTPS redirect), 443 (HTTPS)
- **Features**: 
  - SSL termination
  - Reverse proxy to backend
  - Static file serving
  - Rate limiting
  - Security headers
  - Gzip compression

## 📊 Monitoring

### Health Checks
All services include health checks:
```bash
# Check service health
docker-compose ps

# View health check logs
docker-compose logs nginx
docker-compose logs backend
docker-compose logs postgres
```

### Logs
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f nginx
```

### Metrics
- Backend health: `https://your-domain.com/health`
- Database connection: Monitored by backend health check

## 🔒 Security Features

### Nginx Security Headers
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security: max-age=31536000
- Referrer-Policy: strict-origin-when-cross-origin

### Rate Limiting
- API endpoints: 10 requests/second
- Login endpoints: 5 requests/second

### SSL/TLS
- TLS 1.2 and 1.3 only
- Strong cipher suites
- HSTS enabled

## 🛠️ Maintenance

### Database Backups
```bash
# Create backup
docker-compose exec postgres pg_dump -U oidc_user oidc_db > backup.sql

# Restore backup
docker-compose exec -T postgres psql -U oidc_user oidc_db < backup.sql
```

### Updates
```bash
# Pull latest images
docker-compose pull

# Rebuild and restart
docker-compose up -d --build

# Run migrations
docker-compose exec backend python -c "
from app_with_db import app, init_db
with app.app_context():
    init_db(app)
"
```

### Scaling
```bash
# Scale backend workers
docker-compose up -d --scale backend=3

# Scale with load balancer (requires external load balancer)
```

## 🚨 Troubleshooting

### Common Issues

**1. Database Connection Failed**
```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Check database connectivity
docker-compose exec backend python -c "
from database import get_db_session
session = get_db_session()
session.execute('SELECT 1')
print('Database connection OK')
"
```

**2. SSL Certificate Issues**
```bash
# Check certificate validity
openssl x509 -in nginx/ssl/cert.pem -text -noout

# Regenerate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/ssl/key.pem \
    -out nginx/ssl/cert.pem
```

**3. Frontend Not Loading**
```bash
# Check frontend build
docker-compose logs frontend

# Rebuild frontend
docker-compose build frontend
docker-compose up -d frontend
```

**4. API Endpoints Not Working**
```bash
# Check backend logs
docker-compose logs backend

# Test API directly
curl -k https://localhost/api/health
```

### Performance Tuning

**Nginx Configuration**
- Adjust worker processes in `nginx/nginx.conf`
- Modify rate limiting based on your needs
- Tune gzip compression settings

**Database Optimization**
- Add database indexes for frequently queried columns
- Configure connection pooling
- Monitor query performance

**Backend Optimization**
- Adjust Gunicorn workers based on CPU cores
- Configure logging levels
- Enable caching where appropriate

## 📈 Production Checklist

- [ ] SSL certificates installed and valid
- [ ] Environment variables configured securely
- [ ] Database backups scheduled
- [ ] Monitoring and alerting configured
- [ ] Log rotation configured
- [ ] Security updates automated
- [ ] Load testing completed
- [ ] Disaster recovery plan documented

## 🔗 Useful Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart specific service
docker-compose restart backend

# View service status
docker-compose ps

# View logs
docker-compose logs -f

# Execute command in container
docker-compose exec backend python manage.py shell

# Backup database
docker-compose exec postgres pg_dump -U oidc_user oidc_db > backup.sql

# Update and restart
docker-compose pull && docker-compose up -d --build
```

## 📞 Support

For deployment issues:
1. Check the logs: `docker-compose logs -f`
2. Verify environment variables: `docker-compose config`
3. Test individual services: `docker-compose exec [service] [command]`
4. Check health endpoints: `curl https://your-domain.com/health` 