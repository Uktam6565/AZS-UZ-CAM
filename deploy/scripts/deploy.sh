#!/usr/bin/env bash
set -e

echo "Starting GasQ deploy..."

echo "Pulling latest code..."
git pull origin develop

echo "Rebuilding containers..."
docker compose -f docker-compose.prod.yml build

echo "Restarting containers..."
docker compose -f docker-compose.prod.yml up -d

echo "Cleaning old images..."
docker image prune -f

echo "Deploy finished."