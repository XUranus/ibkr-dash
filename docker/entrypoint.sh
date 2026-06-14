#!/bin/sh
set -e

# Start the worker scheduler in the background
echo "Starting worker scheduler..."
python -m worker.main run-scheduler &

# Start the backend in the foreground
echo "Starting backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
