#!/usr/bin/env bash
# Start both API and Web in dev mode
set -e
cd "$(dirname "$0")/.."

trap 'kill 0' EXIT
(cd apps/api && uvicorn verify_api.main:app --reload --port 8000) &
(cd apps/web && npm run dev) &
wait
