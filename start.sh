#!/bin/sh
set -x

echo "=== Starting initialization ==="
python init_db.py
EXIT_CODE=$?
echo "=== Init DB exit code: $EXIT_CODE ==="

if [ $EXIT_CODE -eq 0 ] || [ $EXIT_CODE -eq 1 ]; then
    echo "=== DB initialization completed or skipped ==="
else
    echo "=== DB initialization failed with exit code: $EXIT_CODE ==="
    exit $EXIT_CODE
fi

echo "=== Starting uvicorn ==="
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
