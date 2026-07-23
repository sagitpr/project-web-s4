"""
Celery tasks for inventory — async expiry check and batch sync.
"""

import logging
from celery import shared_task
from django.core.cache import cache

logger = logging.getLogger(__name__)

EXPIRY_CACHE_TTL = 60 * 5  # 5 minutes
LOW_STOCK_CACHE_TTL = 60 * 3  # 3 minutes


@shared_task(bind=True, max_retries=3, default_retry_delay=30, autoretry_for=(Exception,))
def run_expiry_check_task(self, store_id):
    """
    Check all batches for a store and send expiry notifications.
    Runs periodically or on-demand via API trigger.
    """
    from inventory.services.expiry_service import check_and_notify_expiry
    from stores.models import Store
    from django.db import connection

    try:
        store = Store.objects.get(id=store_id)
    except Store.DoesNotExist:
        return {'error': 'Store not found', 'store_id': store_id}

    # Close idle connections to prevent pool exhaustion
    connection.close_if_unusable_or_obsolete()

    try:
        result = check_and_notify_expiry(store)
        logger.info('Expiry check complete for store %s: %s', store_id, result)
        return {
            'store_id': store_id,
            'notifications_sent': result,
        }
    except Exception as exc:
        logger.exception('Expiry check error for store %s', store_id)
        return {'error': str(exc), 'store_id': store_id}


@shared_task(max_retries=2, default_retry_delay=60, autoretry_for=(Exception,))
def clean_expired_notifications_task():
    """
    Clean up old notifications and expired batch records.
    Runs daily via Celery Beat.
    """
    from django.utils import timezone
    from notifications.models import Notification
    from inventory.models import ExpiryNotification, ProductBatch

    # Delete read notifications older than 90 days
    cutoff = timezone.now() - timezone.timedelta(days=90)
    deleted_notifs, _ = Notification.objects.filter(
        is_read=True, created_at__lt=cutoff
    ).delete()
    logger.info('Cleaned %s old notifications', deleted_notifs)

    # Delete expiry notifications older than 60 days
    cutoff_60 = timezone.now() - timezone.timedelta(days=60)
    deleted_expiry, _ = ExpiryNotification.objects.filter(
        sent_at__lt=cutoff_60
    ).delete()
    logger.info('Cleaned %s old expiry notifications', deleted_expiry)

    # Mark disposed batches older than 30 days as inactive
    cutoff_30 = timezone.now() - timezone.timedelta(days=30)
    expired_batches = ProductBatch.objects.filter(
        status='expired', updated_at__lt=cutoff_30, is_active=True
    )
    count = expired_batches.update(is_active=False)
    logger.info('Deactivated %s old expired batches', count)

    return {
        'deleted_notifications': deleted_notifs,
        'deleted_expiry': deleted_expiry,
        'deactivated_batches': count,
    }
