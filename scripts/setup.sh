#!/usr/bin/env bash
# 15code Verify — local dev setup
set -e
cd "$(dirname "$0")/.."

echo "🔧 Installing Python core package..."
pip install -e packages/core

echo "🔧 Installing API deps..."
pip install -r apps/api/requirements.txt

echo "🔧 Installing CLI..."
pip install -e apps/cli

echo "🔧 Installing web deps..."
(cd apps/web && npm install)

echo ""
echo "✅ Setup complete!"
echo ""
echo "Run:"
echo "  uvicorn verify_api.main:app --reload --app-dir apps/api"
echo "  (in another shell) cd apps/web && npm run dev"
echo "  verify --help"
