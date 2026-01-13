#!/bin/bash
# Start Celery Worker
# Usage: ./start_celery.sh

cd "$(dirname "$0")"

echo "Starting Celery Worker..."
echo "Make sure Redis is running: redis-server"

# Activate virtual environment if using one
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Start Celery worker
celery -A celery_worker.celery worker \
    --loglevel=info \
    --concurrency=4 \
    --hostname=worker@%h \
    --queues=default,reports,dicom

echo "Celery worker started!"
echo "Press Ctrl+C to stop"
