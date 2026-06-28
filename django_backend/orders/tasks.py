"""
Celery tasks for async courier tracking polling.
Periodically polls BinderByte API (or mock) for shipped orders,
broadcasts real-time WebSocket updates when delivery status changes.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from orders.models import Order, Delivery

logger = logging.getLogger(__name__)


# =============================================================================
# Core Task: Poll tracking for a single order
# =============================================================================

@shared_task(bind=True, max_retries=5, default_retry_delay=120)
def poll_tracking_for_order(self, order_id):
    """
    Poll external courier tracking API for a single order.
    Updates the Delivery model and broadcasts WebSocket event if status changed.

    Retry up to 5 times with 2-minute delays on failure.
    """
    from orders.services.courier_tracking import get_tracking_status
    from orders.views import notify_delivery_update

    try:
        order = Order.objects.select_related('delivery').get(id=order_id)
    except Order.DoesNotExist:
        logger.warning(f'poll_tracking: Order {order_id} not found, skipping.')
        return {'order_id': order_id, 'status': 'not_found'}

    # Only poll for shipped/on_delivery orders that have tracking info
    if order.order_status != 'shipped' or not order.tracking_number:
        logger.info(
            f'poll_tracking: Order {order.order_number} status="{order.order_status}", '
            f'tracking="{order.tracking_number}" — skipping.'
        )
        return {
            'order_id': order_id,
            'order_number': order.order_number,
            'status': 'skipped',
            'reason': 'not_shipped_or_no_tracking',
        }

    courier = order.courier or ''
    tracking_number = order.tracking_number

    # Determine current delivery status from the Delivery model
    current_delivery_status = 'waiting'
    try:
        if hasattr(order, 'delivery') and order.delivery:
            current_delivery_status = order.delivery.delivery_status
    except Delivery.DoesNotExist:
        pass

    # ── Fetch tracking from external API or mock ──
    try:
        result = get_tracking_status(courier, tracking_number, current_delivery_status)
    except Exception as exc:
        logger.error(f'poll_tracking: Error fetching tracking for {order.order_number}: {exc}')
        raise self.retry(exc=exc)

    if not result:
        logger.warning(f'poll_tracking: Empty result for {order.order_number}, will retry.')
        raise self.retry()

    new_status = result.get('status', '')
    if not new_status:
        logger.info(f'poll_tracking: No status in result for {order.order_number}.')
        return {
            'order_id': order_id,
            'order_number': order.order_number,
            'status': 'no_status',
        }

    # ── Compare and update ──
    status_changed = new_status != current_delivery_status

    if status_changed:
        with transaction.atomic():
            try:
                delivery = order.delivery
                delivery.delivery_status = new_status

                if new_status == 'delivered':
                    delivery.delivered_at = timezone.now()
                    # Also mark order as completed if delivered
                    order.order_status = 'completed'
                    order.completed_at = timezone.now()
                    order.save(update_fields=['order_status', 'completed_at'])

                delivery.save(update_fields=[
                    'delivery_status', 'delivered_at'
                ] if new_status == 'delivered' else ['delivery_status'])

                logger.info(
                    f'poll_tracking: Order {order.order_number} delivery status '
                    f'changed: {current_delivery_status} → {new_status}'
                )

                # Broadcast WebSocket event to buyer
                notify_delivery_update(
                    user_id=order.user_id,
                    order_id=order.id,
                    order_number=order.order_number,
                    delivery_status=new_status,
                    tracking_number=tracking_number,
                    courier=courier,
                )

                # If delivered, also notify the seller
                if new_status == 'delivered' and order.store and order.store.user_id:
                    from orders.views import notify_order_update
                    notify_order_update(
                        user_id=order.store.user_id,
                        order_id=order.id,
                        order_number=order.order_number,
                        status='completed',
                        message=f'Pesanan {order.order_number} telah diterima pembeli.',
                    )

            except Delivery.DoesNotExist:
                logger.error(
                    f'poll_tracking: No Delivery record for order {order.order_number}. '
                    'Creating one.'
                )
                Delivery.objects.create(
                    order=order,
                    delivery_status=new_status,
                    tracking_number=tracking_number,
                    courier_name=courier,
                )
    else:
        logger.debug(
            f'poll_tracking: Order {order.order_number} status unchanged '
            f'({new_status}), no broadcast needed.'
        )

    # ── Update estimated delivery from result ──
    estimated = result.get('estimated_delivery')
    if estimated:
        try:
            delivery = order.delivery
            if delivery.estimated_time != estimated:
                delivery.estimated_time = str(estimated)[:100]
                delivery.save(update_fields=['estimated_time'])
        except (Delivery.DoesNotExist, AttributeError):
            pass

    return {
        'order_id': order_id,
        'order_number': order.order_number,
        'previous_status': current_delivery_status,
        'new_status': new_status,
        'status_changed': status_changed,
    }


# =============================================================================
# Batch Task: Poll all shipped orders (called every 30 min by Celery Beat)
# =============================================================================

@shared_task
def poll_tracking_batch():
    """
    Find all orders with status='shipped' and a tracking number,
    then spawn individual polling tasks for each.
    Runs every 30 minutes via Celery Beat.
    """
    cutoff = timezone.now() - timedelta(days=14)  # Don't poll orders older than 14 days
    orders = list(Order.objects.filter(
        order_status='shipped',
        tracking_number__isnull=False,
    ).exclude(
        tracking_number=''
    ).filter(
        created_at__gte=cutoff
    ).select_related('delivery'))

    total = len(orders)
    logger.info(f'poll_tracking_batch: Found {total} shipped orders to poll.')

    results = []
    for order in orders:
        try:
            # Only poll if delivery is NOT already delivered
            if hasattr(order, 'delivery') and order.delivery:
                if order.delivery.delivery_status == 'delivered':
                    continue
        except Delivery.DoesNotExist:
            pass

        task = poll_tracking_for_order.delay(order.id)
        results.append({
            'order_id': order.id,
            'order_number': order.order_number,
            'task_id': task.id,
        })

    logger.info(f'poll_tracking_batch: Dispatched {len(results)} tracking tasks.')
    return {
        'total_orders': total,
        'dispatched': len(results),
        'tasks': results,
    }


# =============================================================================
# Quick-Poll Task: Orders nearing completion (every 5 min)
# =============================================================================

@shared_task
def poll_near_complete_tracking():
    """
    Poll orders that are likely already delivered but not yet marked complete.
    This catches edge cases where the 30-min batch misses the window.
    Runs every 5 minutes via Celery Beat.
    """
    # Orders shipped more than 3 days ago with no delivered status
    threshold = timezone.now() - timedelta(days=3)
    stale_list = list(Order.objects.filter(
        order_status='shipped',
        tracking_number__isnull=False,
    ).exclude(
        tracking_number=''
    ).filter(
        created_at__lte=threshold
    ).select_related('delivery'))

    # Also check orders currently in 'on_delivery' delivery status
    on_delivery_list = list(Order.objects.filter(
        order_status='shipped',
        delivery__delivery_status='on_delivery',
        tracking_number__isnull=False,
    ).exclude(
        tracking_number=''
    ).select_related('delivery'))

    # Merge and deduplicate by ID
    seen = set()
    orders_to_poll = []
    for order in stale_list + on_delivery_list:
        if order.id not in seen:
            seen.add(order.id)
            orders_to_poll.append(order)

    logger.info(
        f'poll_near_complete: Polling {len(orders_to_poll)} '
        f'orders (stale={len(stale_list)}, on_delivery={len(on_delivery_list)})'
    )

    results = []
    for order in orders_to_poll:
        task = poll_tracking_for_order.delay(order.id)
        results.append({
            'order_id': order.id,
            'order_number': order.order_number,
            'task_id': task.id,
        })

    return {
        'stale_count': len(stale_list),
        'on_delivery_count': len(on_delivery_list),
        'total_dispatched': len(results),
        'tasks': results,
    }


# =============================================================================
# Admin / Manual Task: Force-poll a specific order
# =============================================================================

@shared_task
def force_poll_order(order_id):
    """
    Force-poll tracking for a specific order, ignoring status checks.
    Can be called manually from Django admin or API views.
    """
    return poll_tracking_for_order(order_id)
