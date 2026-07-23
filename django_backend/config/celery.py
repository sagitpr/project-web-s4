"""
Celery configuration for Warungio Marketplace.
Async task queue with Redis broker for tracking, notifications, and analytics.
"""

import os
import threading
import time
from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init

# ── Transient Error Types (used by all tasks via import) ──
# These are errors that are safe to retry because they represent temporary
# infrastructure/network failures. Business logic errors (ValidationError,
# DoesNotExist) are NOT included — those should fail fast, not retry.
TRANSIENT_ERRORS = (
    ConnectionError,
    ConnectionRefusedError,
    ConnectionResetError,
    BrokenPipeError,
    TimeoutError,
    IOError,
    OSError,
)

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

    # ── Celery Heartbeat (Healthcheck) ──
    # Writes `celery:heartbeat:beat` key to Redis every 60 seconds.
    # If beat crashes or scheduler hangs, key TTL (180s) expires and
    # Docker healthcheck (redis-cli exists) detects failure → restart.
    #
    # Worker heartbeat is handled by `on_worker_process_init` signal
    # (background daemon thread, not a scheduled task) so that
    # worker health works even without Celery Beat running.
    'celery-heartbeat-beat': {
        'task': 'config.celery.celery_heartbeat_beat',
        'schedule': 60.0,
        'options': {'queue': 'default'},
    },
}


# =========================================================================
# 🔴 REDIS HEARTBEAT — Production Healthcheck untuk Celery Worker
# =========================================================================
# Sebelumnya healthcheck menggunakan `pgrep -f 'celery.*worker'` yang hanya
# memeriksa apakah proses masih hidup, TIDAK bisa mendeteksi worker hang,
# deadlock, broker disconnect, atau queue macet.
#
# Solusi: Worker menulis heartbeat ke Redis SETEX setiap 30 detik dengan TTL
# 90 detik (3x missed beats). Docker healthcheck membaca key via `redis-cli`.
# Total overhead: ~1ms per write, ~0 byte Django loading, ~0.1MB RAM.
#
# Untuk Celery Beat: scheduled task `celery_heartbeat_beat` berjalan setiap
# 60 detik yang menulis key `celery:heartbeat:beat`. Jika beat crash/stuck,
# TTL expired dalam 180 detik → healthcheck gagal → container restart.
# =========================================================================

_HEARTBEAT_REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
_HEARTBEAT_WORKER_KEY = 'celery:heartbeat:worker'
_HEARTBEAT_BEAT_KEY = 'celery:heartbeat:beat'
_HEARTBEAT_WORKER_TTL = 90   # 90 detik = 3 missed beats (30s interval)
_HEARTBEAT_BEAT_TTL = 180    # 180 detik = 3 missed beats (60s interval)


def _send_heartbeat(key, ttl, broker_url=None):
    """Write heartbeat to Redis SETEX. Silent fail jika Redis down."""
    try:
        import redis as redis_mod
        url = broker_url or _HEARTBEAT_REDIS_URL
        r = redis_mod.StrictRedis.from_url(url)
        r.setex(key, ttl, 'alive')
    except Exception:
        pass  # Heartbeat failure is non-fatal


def _start_heartbeat_thread():
    """
    Background daemon thread: menulis heartbeat ke Redis setiap 30 detik.
    Thread daemon akan mati otomatis saat worker process berhenti.
    Overhead: ~0.1MB RAM, ~1ms CPU per 30 detik.

    🔴 FIX: Gunakan fixed key (tanpa hostname) untuk menghindari mismatch
    antara key yang ditulis worker (worker@abc123) dan key yang dibaca
    healthcheck ($(hostname) = abc123). Docker healthcheck menggunakan
    `redis-cli exists celery:heartbeat:worker` — cocok dengan key fixed ini.
    """
    def _beat():
        while True:
            _send_heartbeat(_HEARTBEAT_WORKER_KEY, _HEARTBEAT_WORKER_TTL)
            time.sleep(30)

    t = threading.Thread(target=_beat, daemon=True, name='celery-hb')
    t.start()


@worker_process_init.connect
def on_worker_process_init(sender=None, **kwargs):
    """
    Celery signal: dipanggil saat worker process (atau child process pool)
    dimulai. Memulai background thread heartbeat ke Redis.

    Mendeteksi:
    - Worker hang: thread berhenti → key TTL expired → healthcheck fail
    - Broker disconnect: Redis write exception (silent, non-fatal)
    - Worker crash: thread mati → key expired → healthcheck fail
    """
    _start_heartbeat_thread()


@app.task(ignore_result=True, name='config.celery.celery_heartbeat_beat')
def celery_heartbeat_beat():
    """
    Heartbeat task untuk Celery Beat scheduler.
    Dijadwalkan setiap 60 detik via beat_schedule.
    Jika beat crash/stuck, key TTL expired → healthcheck gagal.
    """
    _send_heartbeat(_HEARTBEAT_BEAT_KEY, _HEARTBEAT_BEAT_TTL)
