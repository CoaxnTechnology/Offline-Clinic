"""
Celery tasks module
Import all tasks here so Celery can discover them
"""
from . import dicom_tasks, report_tasks, sync_tasks

__all__ = ['dicom_tasks', 'report_tasks', 'sync_tasks']
