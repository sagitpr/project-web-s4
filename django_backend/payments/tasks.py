"""
Celery tasks for payments — Midtrans async processing.
Moves blocking HTTP calls (requests.post timeout=30s) out of the request thread.
Includes scheduled reconciliation tasks for orphan webhook recovery and
pending transaction verification.
"""

import logging
from celery import shared_task
from django.db import transaction as db_transaction
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=4, default_retry_delay=30)
def create_snap_transaction_task(self, order_id, payment_method, bank=None):
    """Create Midtrans Snap transaction asynchronously."""
    import requests
    import base64
    from orders.models import Order
    from payments.models import Payment, MidtransTransaction

    try:
        order = Order.objects.select_related('user').get(id=order_id)
    except Order.DoesNotExist:
        logger.error('create_snap_task: Order %s not found', order_id)
        return {'error': 'Pesanan tidak ditemukan.', 'order_id': order_id}

    if order.order_status not in ['pending', 'paid']:
        return {'error': 'Pesanan sudah diproses.', 'order_id': order_id}

    tx_order_id = f"WRG-{order.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
    gross_amount = int(float(order.total_price))

    customer_details = {
        'first_name': order.user.full_name or order.user.email,
        'email': order.user.email,
        'phone': str(order.user.phone) if order.user.phone else '',
    }

    item_details = []
    for item in order.items.all():
        item_details.append({
            'id': str(item.product_id or 0),
            'price': int(float(item.price)),
            'quantity': item.qty,
            'name': item.product_name[:50],
        })

    if float(order.shipping_cost) > 0:
        item_details.append({
            'id': 'SHIPPING', 'price': int(float(order.shipping_cost)),
            'quantity': 1, 'name': 'Biaya Pengiriman',
        })
    if float(order.admin_fee_buyer) > 0:
        item_details.append({
            'id': 'ADMIN_FEE', 'price': int(float(order.admin_fee_buyer)),
            'quantity': 1, 'name': 'Biaya Admin Pembelian',
        })

    payload = {
        'transaction_details': {'order_id': tx_order_id, 'gross_amount': gross_amount},
        'customer_details': customer_details,
        'item_details': item_details,
        'credit_card': {'secure': True},
    }

    snap_url = settings.MIDTRANS_SNAP_URL
    server_key = settings.MIDTRANS_SERVER_KEY

    if payment_method == 'bank_transfer':
        payload['bank_transfer'] = {'bank': bank or 'bca'}
    elif payment_method in ['gopay', 'shopeepay', 'ovo', 'dana']:
        payload['payment_type'] = payment_method
    elif payment_method == 'qris':
        payload['qris'] = {'acquirer': 'gopay'}

    try:
        auth_str = base64.b64encode(f'{server_key}:'.encode()).decode()
        headers = {
            'Content-Type': 'application/json', 'Accept': 'application/json',
            'Authorization': f'Basic {auth_str}',
        }
        response = requests.post(snap_url, json=payload, headers=headers, timeout=30)

        if response.status_code not in [200, 201]:
            error_detail = response.text[:500]
            logger.warning('Snap API error [%s] for order %s: %s',
                           response.status_code, order.id, error_detail)
            raise self.retry(exc=Exception(f'Snap API returned {response.status_code}'))

        snap_response = response.json()

        with db_transaction.atomic():
            payment, created = Payment.objects.get_or_create(
                order=order,
                defaults={
                    'user': order.user, 'amount': order.total_price,
                    'payment_type': payment_method, 'midtrans_order_id': tx_order_id,
                }
            )
            if not created:
                payment.midtrans_order_id = tx_order_id
                payment.amount = order.total_price
                payment.save()
            MidtransTransaction.objects.update_or_create(
                payment=payment,
                defaults={
                    'order_id': tx_order_id,
                    'transaction_id': snap_response.get('transaction_id', ''),
                    'transaction_status': 'pending',
                    'payment_type': payment_method,
                    'raw_response': snap_response,
                }
            )

        return {
            'success': True, 'token': snap_response.get('token', ''),
            'redirect_url': snap_response.get('redirect_url', ''),
            'transaction_id': tx_order_id, 'order_id': order.id,
        }

    except requests.RequestException as exc:
        logger.error('Midtrans HTTP error for order %s: %s', order.id, str(exc))
        raise self.retry(exc=exc)
    except Exception as exc:
        logger.exception('Unexpected error in Snap task for order %s', order.id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=4, default_retry_delay=30)
def poll_midtrans_payment_status_task(self, order_id):
    """Poll Midtrans transaction status for a specific order."""
    from payments.services.midtrans import get_transaction_status
    from orders.models import Order
    from payments.models import Payment, MidtransTransaction

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return {'error': 'Order not found', 'order_id': order_id}

    payment = Payment.objects.filter(order=order).first()
    if not payment or not payment.midtrans_order_id:
        return {'error': 'No payment record', 'order_id': order_id}

    midtrans_tx = MidtransTransaction.objects.filter(payment=payment).first()
    if not midtrans_tx:
        return {'error': 'No Midtrans transaction', 'order_id': order_id}

    result = get_transaction_status(payment.midtrans_order_id)
    if not result.get('success'):
        raise self.retry(exc=Exception(f'Status lookup failed: {result.get("error")}'))

    data = result['data']
    transaction_status = data.get('transaction_status', '')

    if transaction_status in ('settlement', 'capture'):
        # Use the shared service function directly - no fake HTTP request needed
        from payments.services.midtrans import process_webhook_notification
        process_webhook_notification(result['data'])

    return {
        'order_id': order_id,
        'transaction_status': transaction_status,
    }


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def reconcile_orphan_webhooks_task(self):
    """
    Scheduled reconciliation task (every 15 minutes).
    
    Processes orphan webhooks cached during notification handling.
    Attempts to match orphan order_ids with local payment records
    and processes them if found.
    """
    from django.core.cache import cache
    from payments.models import MidtransTransaction, Payment
    
    # Scan cache keys for orphan webhooks
    # Use a simple approach: check all pending Midtrans transactions
    # that haven't received a settlement webhook within the last hour
    
    one_hour_ago = timezone.now() - timedelta(hours=1)
    pending_txns = MidtransTransaction.objects.filter(
        transaction_status='pending',
        created_at__lte=one_hour_ago
    ).select_related('payment__order')[:50]

    reconciled = 0
    for txn in pending_txns:
        try:
            from payments.services.midtrans import get_transaction_status
            result = get_transaction_status(txn.order_id)
            if result.get('success'):
                status = result['data'].get('transaction_status', '')
                if status in ('settlement', 'capture'):
                    logger.info(
                        'RECONCILIATION: Order %s status=%s - processing via shared service',
                        txn.order_id, status
                    )
                    from payments.services.midtrans import process_webhook_notification
                    process_webhook_notification(result['data'])
                    reconciled += 1
                elif status in ('expire', 'deny', 'cancel'):
                    txn.transaction_status = status
                    txn.save(update_fields=['transaction_status'])
                    reconciled += 1
        except Exception as e:
            logger.error('Reconciliation error for %s: %s', txn.order_id, str(e))

    logger.info('Reconciliation complete: %d transactions updated', reconciled)
    return {'reconciled': reconciled}


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def verify_pending_payments_task(self):
    """
    Scheduled task (every 30 minutes) to verify payments stuck in 'pending' status
    that are older than 2 hours. Either marks them as expired or attempts
    to reconcile via Midtrans API.
    """
    from payments.models import Payment
    from django.core.cache import cache
    
    two_hours_ago = timezone.now() - timedelta(hours=2)
    stuck_payments = Payment.objects.filter(
        payment_status='pending',
        created_at__lte=two_hours_ago
    ).select_related('midtrans')[:50]

    verified = 0
    expired = 0
    for payment in stuck_payments:
        try:
            mt = getattr(payment, 'midtrans', None)
            if mt and mt.order_id:
                from payments.services.midtrans import get_transaction_status
                result = get_transaction_status(mt.order_id)
                if result.get('success'):
                    status = result['data'].get('transaction_status', '')
                    if status in ('expire', 'deny', 'cancel'):
                        payment.payment_status = 'expired' if status == 'expire' else 'failed'
                        payment.save(update_fields=['payment_status'])
                        if payment.order:
                            payment.order.order_status = 'cancelled'
                            payment.order.save(update_fields=['order_status'])
                        expired += 1
                    elif status in ('settlement', 'capture'):
                        from payments.services.midtrans import process_webhook_notification
                        process_webhook_notification(result['data'])
                        verified += 1
            else:
                # No Midtrans record — this is a stale local payment
                if payment.created_at < timezone.now() - timedelta(days=1):
                    payment.payment_status = 'expired'
                    payment.save(update_fields=['payment_status'])
                    expired += 1
        except Exception as e:
            logger.error('Verify error for payment %s: %s', payment.id, str(e))

    logger.info(
        'Payment verification complete: %d reconciled, %d expired',
        verified, expired
    )
    return {'verified': verified, 'expired': expired}
