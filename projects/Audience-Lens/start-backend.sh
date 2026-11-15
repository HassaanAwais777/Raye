#!/usr/bin/env bash
# Start the AudienceLens Python backend (FastAPI) on port 8000.
# The Next.js frontend (port 3000) calls it via ?XTransformPort=8000.
set -e
cd "$(dirname "$0")/.."
exec python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 "$@"
