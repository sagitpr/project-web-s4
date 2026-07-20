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
    from accounts.tasks import clean_expired_otps_task, clean_expired_blacklisted_tokens_task
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

    # Clean expired JWT blacklist tokens daily at 4 AM
    sender.add_periodic_task(
        crontab(hour=4, minute=0),
        clean_expired_blacklisted_tokens_task.s(),
        name='Clean expired blacklisted JWT tokens (daily)',
    )

    # ── Engagement Engine Periodic Tasks ──
    from engagement.tasks import (
        process_notification_queue_task,
        batch_update_profiles_task,
        scan_at_risk_users_task,
        detect_inactive_users_task,
        aggregate_notification_analytics_task,
        update_optimal_notification_hours_task,
        schedule_campaigns_task,
        clean_expired_queue_items_task,
        clean_old_behavior_events_task,
    )

    # Process notification queue every 30 seconds
    sender.add_periodic_task(
        30.0,  # seconds
        process_notification_queue_task.s(),
        name='Process engagement notification queue (30s)',
    )

    # Batch update user profiles every 6 hours
    sender.add_periodic_task(
        crontab(hour='*/6', minute=0),
        batch_update_profiles_task.s(),
        name='Batch update user engagement profiles (6h)',
    )

    # Scan at-risk users daily at 8 AM and 8 PM
    sender.add_periodic_task(
        crontab(hour='8,20', minute=0),
        scan_at_risk_users_task.s(),
        name='Scan at-risk users for re-engagement (daily)',
    )

    # Detect inactive users daily at 2 AM
    sender.add_periodic_task(
        crontab(hour=2, minute=30),
        detect_inactive_users_task.s(),
        name='Detect inactive users and mark risk (daily)',
    )

    # Aggregate notification analytics daily at 1 AM
    sender.add_periodic_task(
        crontab(hour=1, minute=0),
        aggregate_notification_analytics_task.s(),
        name='Aggregate notification analytics (daily)',
    )

    # Update optimal notification hours daily at 5 AM
    sender.add_periodic_task(
        crontab(hour=5, minute=0),
        update_optimal_notification_hours_task.s(),
        name='Update optimal notification hours (daily)',
    )

    # Check for campaigns to execute every 5 minutes
    sender.add_periodic_task(
        crontab(minute='*/5'),
        schedule_campaigns_task.s(),
        name='Schedule pending campaigns (every 5min)',
    )

    # Clean expired queue items daily at 3:30 AM
    sender.add_periodic_task(
        crontab(hour=3, minute=30),
        clean_expired_queue_items_task.s(),
        name='Clean expired notification queue items (daily)',
    )

    # Clean old behavior events weekly on Sunday at 4 AM
    sender.add_periodic_task(
        crontab(hour=4, minute=0, day_of_week=0),
        clean_old_behavior_events_task.s(),
        name='Clean old behavior events (weekly)',
    )


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is running."""
    print(f'Request: {self.request!r}')
