#!/bin/bash
set -e

echo "Running database initialization..."
python init_db.py || true

echo "Starting uvicorn server..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
