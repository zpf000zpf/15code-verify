#!/usr/bin/env bash
# Zero-downtime update script
set -euo pipefail
INSTALL_DIR="${INSTALL_DIR:-/opt/15code-verify}"
cd "$INSTALL_DIR"
echo "→ Pulling latest source..."
git pull --ff-only
cd deploy/docker
echo "→ Rebuilding & recreating containers..."
docker compose up -d --build
echo "→ Pruning old images..."
docker image prune -f
echo "✓ Update complete."
