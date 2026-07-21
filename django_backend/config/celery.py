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
# Using string task names instead of imported callables ensures Celery resolves
# them lazily from the task registry (populated by autodiscover_tasks above).
# This avoids 'Task never registered' errors in eager mode (CELERY_TASK_ALWAYS_EAGER=True)
# where on_after_configure fires before the registry is fully populated.
app.conf.beat_schedule = {
    # ── Courier Tracking Polling ──
    'poll-tracking-shipped': {
        'task': 'orders.tasks.poll_tracking_batch',
        'schedule': crontab(minute='*/30'),
        'options': {'queue': 'default'},
    },
    'poll-tracking-near-complete': {
        'task': 'orders.tasks.poll_near_complete_tracking',
        'schedule': crontab(minute='*/5'),
        'options': {'queue': 'default'},
    },

    # ── Cleanup Tasks ──
    'clean-expired-otps': {
        'task': 'accounts.tasks.clean_expired_otps_task',
        'schedule': crontab(hour=2, minute=0),
    },
    'clean-old-notifications': {
        'task': 'inventory.tasks.clean_expired_notifications_task',
        'schedule': crontab(hour=3, minute=0),
    },
    'clean-expired-jwt-blacklist': {
        'task': 'accounts.tasks.clean_expired_blacklisted_tokens_task',
        'schedule': crontab(hour=4, minute=0),
    },

    # ── Engagement Engine ──
    'process-notification-queue': {
        'task': 'engagement.tasks.process_notification_queue_task',
        'schedule': 30.0,  # seconds
    },
    'batch-update-profiles': {
        'task': 'engagement.tasks.batch_update_profiles_task',
        'schedule': crontab(hour='*/6', minute=0),
    },
    'scan-at-risk-users': {
        'task': 'engagement.tasks.scan_at_risk_users_task',
        'schedule': crontab(hour='8,20', minute=0),
    },
    'detect-inactive-users': {
        'task': 'engagement.tasks.detect_inactive_users_task',
        'schedule': crontab(hour=2, minute=30),
    },
    'aggregate-notification-analytics': {
        'task': 'engagement.tasks.aggregate_notification_analytics_task',
        'schedule': crontab(hour=1, minute=0),
    },
    'update-optimal-notification-hours': {
        'task': 'engagement.tasks.update_optimal_notification_hours_task',
        'schedule': crontab(hour=5, minute=0),
    },
    'schedule-campaigns': {
        'task': 'engagement.tasks.schedule_campaigns_task',
        'schedule': crontab(minute='*/5'),
    },
    'clean-expired-queue-items': {
        'task': 'engagement.tasks.clean_expired_queue_items_task',
        'schedule': crontab(hour=3, minute=30),
    },
    'clean-old-behavior-events': {
        'task': 'engagement.tasks.clean_old_behavior_events_task',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),
    },

    # ── Payment Reconciliation ──
    'reconcile-orphan-webhooks': {
        'task': 'payments.tasks.reconcile_orphan_webhooks_task',
        'schedule': crontab(minute='*/15'),
    },
    'verify-pending-payments': {
        'task': 'payments.tasks.verify_pending_payments_task',
        'schedule': crontab(minute='*/30'),
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is running."""
    print(f'Request: {self.request!r}')
