#!/usr/bin/env bash
# Build and restart the Beezents production stack on the EC2 instance.
# Database migrations run automatically inside the container entrypoint, so
# this script only needs to pull, rebuild and restart.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[deploy] Pulling latest code..."
git pull --ff-only

echo "[deploy] Rebuilding and restarting the stack..."
docker compose -f docker-compose.prod.yml up -d --build

echo "[deploy] Done. Status:"
docker compose -f docker-compose.prod.yml ps