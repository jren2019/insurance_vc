#!/bin/bash

# OIDC Production Deployment Script
set -e

echo "🚀 Starting OIDC Production Deployment..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy env.example to .env and configure your environment variables."
    exit 1
fi

# Load environment variables
source .env

# Create SSL directory if it doesn't exist
mkdir -p nginx/ssl

# Check if SSL certificates exist
if [ ! -f nginx/ssl/cert.pem ] || [ ! -f nginx/ssl/key.pem ]; then
    echo "⚠️  Warning: SSL certificates not found in nginx/ssl/"
    echo "For production, please add your SSL certificates:"
    echo "  - nginx/ssl/cert.pem (SSL certificate)"
    echo "  - nginx/ssl/key.pem (SSL private key)"
    echo ""
    echo "For development, you can generate self-signed certificates:"
    echo "  openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout nginx/ssl/key.pem -out nginx/ssl/cert.pem"
    echo ""
    read -p "Continue with self-signed certificates for development? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🔐 Generating self-signed SSL certificates..."
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/key.pem \
            -out nginx/ssl/cert.pem \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
    else
        echo "❌ Deployment aborted. Please add SSL certificates and try again."
        exit 1
    fi
fi

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Remove old volumes (optional - uncomment if you want to start fresh)
# echo "🗑️  Removing old volumes..."
# docker-compose down -v

# Build and start services
echo "🔨 Building and starting services..."
docker-compose up -d --build

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 30

# Check service health
echo "🏥 Checking service health..."
docker-compose ps

# Run database migrations
echo "🗄️  Running database migrations..."
docker-compose exec backend python -c "
from app_with_db import app, init_db
with app.app_context():
    init_db(app)
    print('Database initialized successfully')
"

# Show logs
echo "📋 Recent logs:"
docker-compose logs --tail=20

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Your OIDC application is now running at:"
echo "   - Frontend: https://localhost"
echo "   - Backend API: https://localhost/api"
echo "   - Health Check: https://localhost/health"
echo ""
echo "📊 To monitor the services:"
echo "   docker-compose logs -f"
echo ""
echo "🛠️  To stop the services:"
echo "   docker-compose down"
echo ""
echo "🔧 To restart a specific service:"
echo "   docker-compose restart [service_name]" 