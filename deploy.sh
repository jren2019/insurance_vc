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

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

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
docker-compose exec backend python manage_db.py migrate
docker-compose exec backend python populate_test_data.py

# Show logs
echo "📋 Recent logs:"
docker-compose logs --tail=20

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Your OIDC application is now running at:"
echo "   - Frontend: http://insurance-vc-nz.australiaeast.cloudapp.azure.com"
echo "   - Backend API: http://insurance-vc-nz.australiaeast.cloudapp.azure.com/api"
echo "   - Health Check: http://insurance-vc-nz.australiaeast.cloudapp.azure.com/health"
echo ""
echo "📊 To monitor the services:"
echo "   docker-compose logs -f"
echo ""
echo "🛠️  To stop the services:"
echo "   docker-compose down"
echo ""
echo "🔧 To restart a specific service:"
echo "   docker-compose restart [service_name]" 