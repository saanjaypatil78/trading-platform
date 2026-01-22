#!/bin/bash

# Deploy Script for Trading Platform Backend
# Usage: ./deploy.sh [branch_name]

BRANCH=${1:-main}
PROJECT_DIR="/opt/trading-platform"

echo "Starting deployment for branch: $BRANCH"

# Navigate to project directory
cd $PROJECT_DIR || { echo "Directory not found! Cloning..."; git clone https://github.com/yourusername/trading-platform.git $PROJECT_DIR; cd $PROJECT_DIR; }

# Pull latest changes
echo "Pulling latest changes..."
git fetch origin
git checkout $BRANCH
git pull origin $BRANCH

# Update environment variables if needed (assumes .env exists on server)
# cp .env.production .env

# Build and restart services
echo "Rebuilding and restarting services..."
docker-compose -f docker-compose.prod.yml up -d --build

# Run migrations (if any)
# echo "Running database migrations..."
# docker-compose exec -T postgres psql -U postgres -d trading_platform -f /docker-entrypoint-initdb.d/init.sql

echo "Cleaning up unused images..."
docker image prune -f

echo "Deployment completed successfully!"
