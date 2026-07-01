"""
Expiry notification service.
Checks all active batches for:
- Products expiring within 30 days → 'expiring_soon' alert
- Products already expired → 'expired' alert
- Products disposed → 'disposal' record

Integrates with Warungio notification system to send WebSocket + DB notifications.
"""

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from ..models import ProductBatch, ExpiryNotification
from notifications.services import send_notification

logger = logging.getLogger('django_backend.inventory.expiry')


def check_and_notify_expiry(store):
    """
    Check all batches for a store and send expiry notifications.
    
    Idempotent: only sends each notification type once per batch.
    Call this from a Celery periodic task or management command.
    
    Returns:
        dict with counts of notifications sent
    """
    today = timezone.now().date()
    next_month = today + timedelta(days=30)
    sent = {'expiring_soon': 0, 'expired': 0}

    # ── Expiring soon (within 30 days) ──
    expiring_batches = ProductBatch.objects.filter(
        store=store,
        is_active=True,
        current_quantity__gt=0,
        expiry_date__range=[today, next_month],
        status__in=['fresh', 'expiring_soon'],
    ).select_related('master_product')

    for batch in expiring_batches:
        days_left = (batch.expiry_date - today).days
        # Check if already notified for this type
        already_sent = ExpiryNotification.objects.filter(
            batch=batch,
            notification_type='expiring_soon',
        ).exists()

        if not already_sent:
            with transaction.atomic():
                ExpiryNotification.objects.create(
                    batch=batch,
                    store=store,
                    notification_type='expiring_soon',
                    days_until_expiry=days_left,
                )

                # Create user notification via Warungio notification system
                store_users = store.user
                _send_expiry_notification(
                    user_id=store_users.id if store_users else None,
                    master_product=batch.master_product,
                    batch=batch,
                    days_left=days_left,
                )
                sent['expiring_soon'] += 1

    # ── Already expired ──
    expired_batches = ProductBatch.objects.filter(
        store=store,
        is_active=True,
        status='expired',
        current_quantity__gt=0,
    ).select_related('master_product')

    for batch in expired_batches:
        already_sent = ExpiryNotification.objects.filter(
            batch=batch,
            notification_type='expired',
        ).exists()

        if not already_sent:
            with transaction.atomic():
                ExpiryNotification.objects.create(
                    batch=batch,
                    store=store,
                    notification_type='expired',
                    days_until_expiry=-1,
                )

                store_users = store.user
                _send_expiry_notification(
                    user_id=store_users.id if store_users else None,
                    master_product=batch.master_product,
                    batch=batch,
                    days_left=-1,
                    is_expired=True,
                )
                sent['expired'] += 1

    return sent


def _send_expiry_notification(user_id, master_product, batch, days_left, is_expired=False):
    """Send expiry notification via Warungio notification system."""
    if not user_id:
        return

    product_name = master_product.product_name
    quantity = float(batch.current_quantity)
    unit = batch.unit

    if is_expired:
        title = f'⚠️ Produk Kadaluwarsa: {product_name}'
        description = (
            f'{product_name} batch {batch.batch_number} sudah kadaluwarsa '
            f'(tgl: {batch.expiry_date}). Sisa stok: {quantity} {unit}. '
            f'Segera lakukan disposal!'
        )
        priority = 'urgent'
        ntype = 'expired'
    else:
        title = f'⏰ Produk Akan Kadaluwarsa: {product_name}'
        description = (
            f'{product_name} batch {batch.batch_number} akan kadaluwarsa '
            f'dalam {days_left} hari ({batch.expiry_date}). '
            f'Sisa stok: {quantity} {unit}. Prioritaskan penjualan!'
        )
        priority = 'high'
        ntype = 'expiring'

    send_notification(
        user_id=user_id,
        title=title,
        description=description,
        notification_type=ntype,
        priority=priority,
        action_url=f'/seller/products/?batch={batch.id}',
        action_text='Lihat Batch',
        metadata={
            'batch_id': batch.id,
            'master_product_id': master_product.id,
            'expiry_date': batch.expiry_date.isoformat(),
            'days_left': days_left,
            'quantity': quantity,
        },
    )
