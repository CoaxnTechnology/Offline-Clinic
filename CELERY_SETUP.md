# Celery Worker Setup Guide

Complete guide for setting up and running Celery workers for background tasks.

## Prerequisites

1. **Redis Server** - Required for Celery message broker
2. **Python Dependencies** - Already in requirements.txt

## Installation

### 1. Install Redis

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Verify Redis is running:**
```bash
redis-cli ping
# Should return: PONG
```

### 2. Install Python Dependencies

```bash
uv pip install celery redis
```

## Configuration

Celery is configured in `app/config.py`:
- **Broker**: Redis (default: `redis://localhost:6379/0`)
- **Result Backend**: Redis (default: `redis://localhost:6379/0`)
- **Serialization**: JSON

Update `.env` if needed:
```bash
REDIS_URL=redis://localhost:6379/0
```

## Running Celery Worker

### Method 1: Using Start Script (Recommended)

```bash
./start_celery.sh
```

### Method 2: Using Celery Command

```bash
celery -A celery_worker.celery worker --loglevel=info
```

### Method 3: With Concurrency Options

```bash
celery -A celery_worker.celery worker \
    --loglevel=info \
    --concurrency=4 \
    --queues=default,reports,dicom
```

### Method 4: Development Mode

```bash
python celery_worker.py
```

## Available Tasks

### DICOM Tasks

**Process DICOM Image:**
```python
from tasks.dicom_tasks import process_dicom_image

# Async
result = process_dicom_image.delay(image_id)

# Sync (for testing)
result = process_dicom_image(image_id)
```

**Batch Process Images:**
```python
from tasks.dicom_tasks import batch_process_dicom_images

result = batch_process_dicom_images.delay([1, 2, 3, 4])
```

**Cleanup Old Files:**
```python
from tasks.dicom_tasks import cleanup_old_dicom_files

result = cleanup_old_dicom_files.delay(days_old=90)
```

### Report Tasks

**Generate PDF Report:**
```python
from tasks.report_tasks import generate_pdf_report_task

result = generate_pdf_report_task.delay(study_instance_uid)
```

**Batch Generate Reports:**
```python
from tasks.report_tasks import batch_generate_reports

result = batch_generate_reports.delay([uid1, uid2, uid3])
```

### Sync Tasks

**Update Appointment Statuses:**
```python
from tasks.sync_tasks import update_appointment_statuses

result = update_appointment_statuses.delay()
```

**Sync Patient Data:**
```python
from tasks.sync_tasks import sync_patient_data

result = sync_patient_data.delay(patient_id)
```

**Daily Maintenance:**
```python
from tasks.sync_tasks import daily_maintenance

result = daily_maintenance.delay()
```

## Monitoring Celery

### Check Worker Status

```bash
celery -A celery_worker.celery inspect active
celery -A celery_worker.celery inspect stats
```

### Check Task Status

```python
from celery.result import AsyncResult
from app.extensions import celery

task_id = "task-id-here"
result = AsyncResult(task_id, app=celery)
print(result.state)  # PENDING, STARTED, SUCCESS, FAILURE
print(result.get())  # Get result (blocks until ready)
```

### Flower (Web-based Monitoring)

Install Flower:
```bash
uv pip install flower
```

Run Flower:
```bash
celery -A celery_worker.celery flower
```

Access at: http://localhost:5555

## Scheduled Tasks (Celery Beat)

### Setup Celery Beat

Create `celery_beat.py`:
```python
from celery_worker import celery

# Schedule periodic tasks
celery.conf.beat_schedule = {
    'update-appointment-statuses': {
        'task': 'tasks.update_appointment_statuses',
        'schedule': 300.0,  # Every 5 minutes
    },
    'daily-maintenance': {
        'task': 'tasks.daily_maintenance',
        'schedule': 86400.0,  # Daily
    },
}
```

Run Beat:
```bash
celery -A celery_beat beat --loglevel=info
```

## Production Setup

### Using Supervisor

Create `/etc/supervisor/conf.d/celery.conf`:
```ini
[program:celery]
command=/path/to/venv/bin/celery -A celery_worker.celery worker --loglevel=info
directory=/path/to/project
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/celery/worker.log
```

### Using Systemd

Create `/etc/systemd/system/celery.service`:
```ini
[Unit]
Description=Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=www-data
WorkingDirectory=/path/to/project
ExecStart=/path/to/venv/bin/celery -A celery_worker.celery worker --loglevel=info --detach
ExecStop=/bin/kill -s TERM $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable celery
sudo systemctl start celery
```

## Troubleshooting

### Issue: "Connection refused" to Redis
**Solution:** Start Redis server: `sudo systemctl start redis-server`

### Issue: Tasks not executing
**Solution:** 
- Check worker is running: `celery -A celery_worker.celery inspect active`
- Check Redis connection: `redis-cli ping`
- Check task imports: `python -c "from tasks import dicom_tasks"`

### Issue: "No module named 'tasks'"
**Solution:** Run from project root directory or set PYTHONPATH

### Issue: Database errors in tasks
**Solution:** Ensure Flask app context is available (already handled in FlaskAppContextTask)

## Quick Start

1. **Start Redis:**
   ```bash
   redis-server
   ```

2. **Start Celery Worker:**
   ```bash
   ./start_celery.sh
   ```

3. **Test Task:**
   ```python
   from tasks.dicom_tasks import process_dicom_image
   result = process_dicom_image.delay(1)
   print(result.id)
   ```

4. **Check Status:**
   ```bash
   celery -A celery_worker.celery inspect active
   ```

---

**Last Updated:** 2024-01-08
