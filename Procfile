web: gunicorn -c gunicorn_config.py "app:create_app()"
worker: celery -A celery_worker.celery worker --loglevel=info --concurrency=4
release: flask db upgrade
