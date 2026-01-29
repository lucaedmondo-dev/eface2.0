#!/usr/bin/env bash
# Simple run script for addon/container: start FastAPI via Uvicorn
set -e
echo "Starting e-face API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
