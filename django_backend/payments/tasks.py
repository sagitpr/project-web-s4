"""
Celery tasks for payments — Midtrans async processing.
Moves blocking HTTP calls (requests.post timeout=30s) out of the request thread.
"""

import logging
from celery import shared_task
from django.db import transaction as db_transaction
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def create_snap_transaction_task(self, order_id, payment_method, bank=None):
    """
    Create Midtrans Snap transaction asynchronously.
    Returns token/redirect_url without blocking the web worker.

    Retry up to 3 times with 10-second delays on failure.
    """
    import requests
    import base64

    from orders.models import Order
    from payments.models import Payment, MidtransTransaction
    from payments.serializers import PaymentSerializer

    try:
        order = Order.objects.select_related('user').get(id=order_id)
    except Order.DoesNotExist:
        logger.error('create_snap_task: Order %s not found', order_id)
        return {'error': 'Pesanan tidak ditemukan.', 'order_id': order_id}

    if order.order_status not in ['pending', 'paid']:
        return {'error': 'Pesanan sudah diproses.', 'order_id': order_id}

    # Build Midtrans payload (same logic as original CreateSnapTransactionView)
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
            'id': 'SHIPPING',
            'price': int(float(order.shipping_cost)),
            'quantity': 1,
            'name': 'Biaya Pengiriman',
        })
    if float(order.admin_fee_buyer) > 0:
        item_details.append({
            'id': 'ADMIN_FEE',
            'price': int(float(order.admin_fee_buyer)),
            'quantity': 1,
            'name': 'Biaya Admin Pembelian',
        })

    payload = {
        'transaction_details': {'order_id': tx_order_id, 'gross_amount': gross_amount},
        'customer_details': customer_details,
        'item_details': item_details,
        'credit_card': {'secure': True},
    }

    snap_url = settings.MIDTRANS_SNAP_URL
    server_key = settings.MIDTRANS_SERVER_KEY

    # Payment method specific
    if payment_method == 'bank_transfer':
        payload['payment_type'] = 'bank_transfer'
        payload['bank_transfer'] = {'bank': bank or 'bca'}
    elif payment_method in ['gopay', 'shopeepay', 'ovo', 'dana']:
        payload['payment_type'] = payment_method
    elif payment_method == 'qris':
        payload['payment_type'] = 'qris'
        payload['qris'] = {'acquirer': 'gopay'}

    try:
        auth_str = base64.b64encode(f'{server_key}:'.encode()).decode()
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Basic {auth_str}',
        }

        response = requests.post(snap_url, json=payload, headers=headers, timeout=30)

        if response.status_code not in [200, 201]:
            error_detail = response.text[:500]
            logger.warning('Snap API error [%s] for order %s: %s',
                           response.status_code, order.id, error_detail)
            raise self.retry(exc=Exception(f'Snap API returned {response.status_code}'))

        snap_response = response.json()

        # Save payment & transaction records (atomic)
        with db_transaction.atomic():
            payment, created = Payment.objects.get_or_create(
                order=order,
                defaults={
                    'user': order.user,
                    'amount': order.total_price,
                    'payment_type': payment_method,
                    'midtrans_order_id': tx_order_id,
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
            'success': True,
            'token': snap_response.get('token', ''),
            'redirect_url': snap_response.get('redirect_url', ''),
            'transaction_id': tx_order_id,
            'order_id': order.id,
        }

    except requests.RequestException as exc:
        logger.error('Midtrans HTTP error for order %s: %s', order.id, str(exc))
        raise self.retry(exc=exc)
    except Exception as exc:
        logger.exception('Unexpected error in Snap task for order %s', order.id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def poll_midtrans_payment_status_task(self, order_id):
    """
    Poll Midtrans transaction status for a specific order.
    Used when webhook might not fire (e.g. network issues).
    """
    from payments.services.midtrans import get_transaction_status
    from orders.models import Order

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return {'error': 'Order not found', 'order_id': order_id}

    from payments.models import Payment, MidtransTransaction
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
        from payments.views import MidtransNotificationView
        # Re-use the same notification handler
        notification_view = MidtransNotificationView()
        notification_view.post(type('Request', (), {
            'data': lambda: data,
            '__class__': type('FakeRequest', (), {}),
        }))

    return {
        'order_id': order_id,
        'transaction_status': transaction_status,
    }
