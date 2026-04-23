#!/usr/bin/env bash
# Build downloadable artifacts and place them under dist/ for nginx to serve.
# Run this after every release, or in CI.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DIST="$ROOT/dist"
mkdir -p "$DIST"

echo "→ Building Python wheels..."
python3 -m pip install --quiet --user --break-system-packages build
python3 -m build --outdir "$DIST" "$ROOT/packages/core"
python3 -m build --outdir "$DIST" "$ROOT/apps/cli"

echo "→ Copying docker-compose.yml..."
cp "$ROOT/deploy/docker/docker-compose.yml" "$DIST/docker-compose.yml"
cp "$ROOT/deploy/docker/.env.example" "$DIST/env.example.txt"

echo "→ Creating source tarball..."
tar --exclude='node_modules' --exclude='.next' --exclude='__pycache__' \
    --exclude='dist' --exclude='.git' -czf \
    "$DIST/15code-verify-src.tar.gz" -C "$(dirname "$ROOT")" "$(basename "$ROOT")"

echo "→ Generating checksums..."
(cd "$DIST" && sha256sum * > SHA256SUMS.txt)

ls -lh "$DIST"
echo "✓ Artifacts ready in $DIST"
echo "  Nginx will serve them at https://verify.15code.com/download/*"
