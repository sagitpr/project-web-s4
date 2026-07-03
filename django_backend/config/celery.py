"""
Celery configuration for Warungio Marketplace.
Async task queue with Redis broker for tracking, notifications, and analytics.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('warungio')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# Namespace 'CELERY' means all celery-related config keys should have a 'CELERY_' prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# ── Periodic task schedule (beat) ──
@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Register periodic tasks for Celery Beat.
    Import tasks inside the function to avoid circular imports.
    """
    from orders.tasks import (
        poll_tracking_batch,
        poll_near_complete_tracking,
    )
    from accounts.tasks import clean_expired_otps_task
    from inventory.tasks import clean_expired_notifications_task

    # Poll tracking for shipped orders every 30 minutes
    sender.add_periodic_task(
        crontab(minute='*/30'),
        poll_tracking_batch.s(),
        name='Poll tracking status for all shipped orders',
    )

    # Quick-poll for orders nearing completion (every 5 minutes)
    sender.add_periodic_task(
        crontab(minute='*/5'),
        poll_near_complete_tracking.s(),
        name='Poll tracking for near-complete orders (every 5min)',
    )

    # Clean expired OTPs daily at 2 AM
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        clean_expired_otps_task.s(),
        name='Clean expired OTP records (daily)',
    )

    # Clean old notifications daily at 3 AM
    sender.add_periodic_task(
        crontab(hour=3, minute=0),
        clean_expired_notifications_task.s(),
        name='Clean old notifications and batches (daily)',
    )


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is running."""
    print(f'Request: {self.request!r}')
