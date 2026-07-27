"""
Celery tasks for inventory — async expiry check and batch sync.
"""

import logging
from celery import shared_task
from config.celery import TRANSIENT_ERRORS
from django.core.cache import cache

logger = logging.getLogger(__name__)

EXPIRY_CACHE_TTL = 60 * 5  # 5 minutes
LOW_STOCK_CACHE_TTL = 60 * 3  # 3 minutes


@shared_task(bind=True, max_retries=3, default_retry_delay=30, autoretry_for=TRANSIENT_ERRORS)
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


@shared_task(max_retries=2, default_retry_delay=60, autoretry_for=TRANSIENT_ERRORS)
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


@shared_task(bind=True, max_retries=3, default_retry_delay=120, autoretry_for=TRANSIENT_ERRORS)
def ai_global_expiry_check_task(self):
    """
    Global AI-powered expiry check for ALL stores.
    Runs daily via Celery Beat (06:00).
    
    Uses AIExpiredReminder service to:
    1. Check all batches across all stores
    2. Send expiry notifications (deduplicated)
    3. Broadcast WebSocket events for urgent items (<=7 days)
    4. Generate discount recommendations
    5. Identify flash sale candidates
    6. Auto-update batch status (fresh → expiring_soon → expired)
    7. Calculate financial impact (stock value at risk)
    
    Returns summary dict with all results.
    """
    from inventory.services.expired_reminder import get_expired_reminder
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    from django.db import connection

    logger.info('Starting global AI expiry check task...')

    # Close idle connections to prevent pool exhaustion
    connection.close_if_unusable_or_obsolete()

    try:
        reminder = get_expired_reminder()
        result = reminder.run_global_expiry_check()

        # Broadcast WebSocket notifications for stores with urgent items
        channel_layer = get_channel_layer()
        if channel_layer and result.get('store_results'):
            for store_result in result['store_results']:
                store_id = store_result.get('store_id')
                flash_sale_count = len(store_result.get('flash_sale_candidates', []))
                expiring_count = store_result.get('expiring_batches', 0)
                expired_count = store_result.get('expired_batches', 0)

                if flash_sale_count > 0 or expiring_count > 0:
                    try:
                        async_to_sync(channel_layer.group_send)(
                            f'store_{store_id}',
                            {
                                'type': 'expiry_update',
                                'store_id': store_id,
                                'flash_sale_count': flash_sale_count,
                                'expiring_count': expiring_count,
                                'expired_count': expired_count,
                                'checked_at': result.get('checked_at', ''),
                                'message': (
                                    f'{flash_sale_count} produk butuh flash sale segera! '
                                    f'{expiring_count} produk mendekati kedaluwarsa.'
                                ),
                            }
                        )
                    except Exception as e:
                        logger.warning(f'WebSocket broadcast error for store {store_id}: {e}')

                # Also notify seller directly for urgent items
                if flash_sale_count > 0:
                    from stores.models import Store
                    try:
                        store = Store.objects.get(id=store_id)
                        if store.user_id:
                            async_to_sync(channel_layer.group_send)(
                                f'notifications_{store.user_id}',
                                {
                                    'type': 'expiry_alert',
                                    'store_id': store_id,
                                    'flash_sale_count': flash_sale_count,
                                    'expiring_count': expiring_count,
                                    'message': f'⚠️ {flash_sale_count} produk mendekati kedaluwarsa! Segera beri diskon atau flash sale.',
                                }
                            )
                    except Exception:
                        pass

        logger.info(
            'Global AI expiry check complete: %d stores, %d notifications',
            result.get('stores_checked', 0),
            result.get('total_notifications_sent', 0),
        )

        return {
            'success': True,
            'stores_checked': result.get('stores_checked', 0),
            'total_batches_checked': result.get('total_batches_checked', 0),
            'total_notifications_sent': result.get('total_notifications_sent', 0),
            'checked_at': result.get('checked_at', ''),
        }

    except Exception as exc:
        logger.exception('Global AI expiry check task failed')
        return {
            'success': False,
            'error': str(exc),
        }
