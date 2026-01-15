#!/usr/bin/env python3
"""
Celery Worker Entry Point
Run with: celery -A celery_worker.celery worker --loglevel=info
Or: python celery_worker.py
"""
from app import create_app
from app.extensions import celery

# Create Flask app to initialize Celery
app = create_app()

# Import tasks so Celery can discover them
from tasks import dicom_tasks, report_tasks, sync_tasks

if __name__ == '__main__':
    # For development: run worker directly
    celery.worker_main([
        'worker',
        '--loglevel=info',
        '--concurrency=4'
    ])
