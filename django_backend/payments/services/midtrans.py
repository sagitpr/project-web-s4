"""
Midtrans Payment Gateway Service Layer — Warungio Marketplace.

Provides:
  - create_snap_token(order, customer_details, item_details)
  - verify_webhook_notification(body)
  - get_transaction_status(order_id)
  - cancel_transaction(order_id)
  - expire_transaction(order_id)
  - cancel_snap_session(snap_token)
  - map_midtrans_status(transaction_status, fraud_status)
  - is_configured()
  - get_client_key()
  - get_snap_js_url()

Uses requests library for HTTP calls. All secrets read from Django settings.
Signature verification uses hmac.compare_digest for timing-attack safety.
"""

import hashlib
import hmac
import logging
import base64
from decimal import Decimal
from datetime import datetime, timezone as dt_timezone

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('django_backend.payments.midtrans')


def _snap_base_url():
    """Snap API base URL based on environment."""
    if settings.MIDTRANS_IS_PRODUCTION:
        return 'https://app.midtrans.com'
    return 'https://app.sandbox.midtrans.com'


def _core_api_base_url():
    """Core API base URL based on environment."""
    if settings.MIDTRANS_IS_PRODUCTION:
        return 'https://api.midtrans.com'
    return 'https://api.sandbox.midtrans.com'


def _auth_header():
    """Basic Auth header using server key."""
    credentials = f'{settings.MIDTRANS_SERVER_KEY}:'
    encoded = base64.b64encode(credentials.encode()).decode()
    return {'Authorization': f'Basic {encoded}'}


def _headers():
    """Standard headers for Midtrans API requests."""
    return {
        **_auth_header(),
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }


def is_configured() -> bool:
    """Check if Midtrans is configured with a server key."""
    return bool(settings.MIDTRANS_SERVER_KEY) and bool(settings.MIDTRANS_CLIENT_KEY)


def get_client_key() -> str:
    """Return the client key (safe for frontend)."""
    return settings.MIDTRANS_CLIENT_KEY


def get_snap_js_url() -> str:
    """Return the correct Snap JS URL for the current environment."""
    return f'{_snap_base_url()}/snap/snap.js'


def create_snap_token(
    order,
    customer_details=None,
    item_details=None,
    enabled_payments=None,
    callbacks=None,
    expiry=None,
) -> dict:
    """
    Create a Midtrans Snap transaction token.

    Args:
        order: Order model instance (must have id, total_price, etc.)
        customer_details: Dict with first_name, email, phone (optional)
        item_details: List of item dicts with id, price, quantity, name
        enabled_payments: List of allowed payment methods
        callbacks: Dict with finish, unfinish, error URLs
        expiry: Dict with start_time, duration, unit

    Returns:
        Dict with success, token, redirect_url, transaction_id, error, raw_response
    """
    if not is_configured():
        logger.error('Midtrans not configured — missing SERVER_KEY or CLIENT_KEY')
        return {
            'success': False,
            'token': None,
            'redirect_url': None,
            'transaction_id': None,
            'error': 'Midtrans belum dikonfigurasi. Tambahkan MIDTRANS_SERVER_KEY dan MIDTRANS_CLIENT_KEY di .env',
        }

    # Build Midtrans order_id with timestamp to ensure uniqueness
    midtrans_order_id = f'WRG-{order.id}-{int(timezone.now().timestamp())}'

    # Default customer details from order
    # Phone must be converted to string — PhoneNumberField returns PhoneNumber object
    # which is not directly JSON serializable.
    _phone = getattr(order, 'user', None) and order.user.phone or ''
    _phone_str = str(_phone) if _phone else ''
    default_customer = {
        'first_name': getattr(order, 'user', None) and order.user.full_name or 'Customer',
        'email': getattr(order, 'user', None) and order.user.email or '',
        'phone': _phone_str,
    }

    # Gross amount must be integer (IDR)
    gross_amount = int(order.total_price)

    payload = {
        'transaction_details': {
            'order_id': midtrans_order_id,
            'gross_amount': gross_amount,
        },
        'customer_details': customer_details or default_customer,
        'item_details': item_details or _default_item_details(order, gross_amount),
    }

    if enabled_payments:
        payload['enabled_payments'] = enabled_payments

    if callbacks:
        payload['callbacks'] = callbacks

    if expiry:
        payload['expiry'] = expiry

    url = f'{_snap_base_url()}/snap/v1/transactions'

    try:
        logger.info('Creating Snap token for order %s (order_id: %s)', order.id, midtrans_order_id)
        response = requests.post(url, json=payload, headers=_headers(), timeout=30)

        if response.status_code in (200, 201):
            data = response.json()
            token = data.get('token', '')
            redirect_url = data.get('redirect_url', '')

            logger.info('Snap token created successfully for order %s', order.id)

            return {
                'success': True,
                'token': token,
                'redirect_url': redirect_url,
                'transaction_id': midtrans_order_id,
                'error': None,
                'raw_response': {
                    'token': token,
                    'redirect_url': redirect_url,
                    'transaction_id': midtrans_order_id,
                },
            }
        else:
            error_body = response.text[:1000] if response.text else 'No response body'
            logger.warning(
                'Snap token creation failed [%s] for order %s: %s',
                response.status_code, order.id, error_body,
            )

            try:
                error_json = response.json()
                error_message = error_json.get('error_message', error_body)
                status_message = error_json.get('status_message', '')
                error_detail = status_message or error_message
            except (ValueError, AttributeError):
                error_detail = error_body

            return {
                'success': False,
                'token': None,
                'redirect_url': None,
                'transaction_id': None,
                'error': f'Gagal membuat pembayaran: {error_detail}',
            }

    except requests.exceptions.Timeout:
        logger.error('Timeout creating Snap token for order %s', order.id)
        return {
            'success': False,
            'token': None,
            'redirect_url': None,
            'transaction_id': None,
            'error': 'Koneksi ke server pembayaran timeout. Silakan coba lagi.',
        }
    except requests.exceptions.ConnectionError:
        logger.error('Connection error creating Snap token for order %s', order.id)
        return {
            'success': False,
            'token': None,
            'redirect_url': None,
            'transaction_id': None,
            'error': 'Gagal terhubung ke server pembayaran. Periksa koneksi internet.',
        }
    except Exception as e:
        logger.exception('Unexpected error creating Snap token for order %s: %s', order.id, str(e))
        return {
            'success': False,
            'token': None,
            'redirect_url': None,
            'transaction_id': None,
            'error': f'Terjadi kesalahan: {str(e)}',
        }


def _default_item_details(order, gross_amount: int) -> list:
    """Generate default item details from order."""
    try:
        items = order.items.all()
        if items.exists():
            return [
                {
                    'id': str(getattr(item, 'product_id', 0)),
                    'price': int(item.price),
                    'quantity': item.qty,
                    'name': item.product_name[:50],
                }
                for i, item in enumerate(items, 1)
            ]
    except (AttributeError, Exception):
        pass

    return [
        {
            'id': f'ORDER-{order.id}',
            'price': gross_amount,
            'quantity': 1,
            'name': f'Pesanan #{order.id}',
        }
    ]


def verify_webhook_notification(body: dict) -> bool:
    """
    Verify Midtrans webhook notification signature using hmac.compare_digest.

    Classic Snap/Core API signature:
        SHA512(order_id + status_code + gross_amount + serverKey)

    Uses hmac.compare_digest for timing-attack-safe comparison.
    """
    signature_key = body.get('signature_key', '')
    order_id = body.get('order_id', '')
    status_code = body.get('status_code', '')
    gross_amount = str(body.get('gross_amount', ''))

    raw_server_key = settings.MIDTRANS_SERVER_KEY

    payload = order_id + status_code + gross_amount + raw_server_key
    expected_signature = hashlib.sha512(payload.encode()).hexdigest()

    is_valid = hmac.compare_digest(expected_signature, signature_key)

    if is_valid:
        logger.info('Webhook signature VALID for order %s', order_id)
    else:
        logger.warning(
            'Webhook signature INVALID for order %s. Expected: %s, Got: %s',
            order_id, expected_signature, signature_key,
        )

    return is_valid


def get_transaction_status(order_id: str) -> dict:
    """Get transaction status from Midtrans Core API."""
    url = f'{_core_api_base_url()}/v2/{order_id}/status'

    try:
        response = requests.get(url, headers=_headers(), timeout=15)

        if response.status_code == 200:
            data = response.json()
            transaction_status = data.get('transaction_status', '')

            if transaction_status:
                logger.info('Status for %s: %s', order_id, transaction_status)
            else:
                logger.info('Status for %s: not found (before method selection)', order_id)

            return {'success': True, 'data': data, 'error': None}
        else:
            error_body = response.text[:500]
            logger.warning('Status lookup failed [%s] for %s: %s', response.status_code, order_id, error_body)
            return {'success': False, 'data': None, 'error': f'Status lookup failed: {response.status_code}'}

    except requests.exceptions.RequestException as e:
        logger.error('Status lookup error for %s: %s', order_id, str(e))
        return {'success': False, 'data': None, 'error': f'Gagal mengecek status: {str(e)}'}


def cancel_transaction(order_id: str) -> dict:
    """Cancel/void a transaction via Core API."""
    url = f'{_core_api_base_url()}/v2/{order_id}/cancel'

    try:
        response = requests.post(url, headers=_headers(), timeout=15)

        if response.status_code in (200, 201):
            data = response.json()
            logger.info('Transaction %s cancelled successfully', order_id)
            return {'success': True, 'data': data, 'error': None}
        else:
            error_body = response.text[:500]
            logger.warning('Cancel failed [%s] for %s: %s', response.status_code, order_id, error_body)
            return {'success': False, 'data': None, 'error': f'Cancel failed: {response.status_code}'}

    except requests.exceptions.RequestException as e:
        logger.error('Cancel error for %s: %s', order_id, str(e))
        return {'success': False, 'data': None, 'error': str(e)}


def expire_transaction(order_id: str) -> dict:
    """Expire a pending transaction via Core API."""
    url = f'{_core_api_base_url()}/v2/{order_id}/expire'

    try:
        response = requests.post(url, headers=_headers(), timeout=15)

        if response.status_code in (200, 201):
            data = response.json()
            logger.info('Transaction %s expired successfully', order_id)
            return {'success': True, 'data': data, 'error': None}
        else:
            error_body = response.text[:500]
            logger.warning('Expire failed [%s] for %s: %s', response.status_code, order_id, error_body)
            return {'success': False, 'data': None, 'error': f'Expire failed: {response.status_code}'}

    except requests.exceptions.RequestException as e:
        logger.error('Expire error for %s: %s', order_id, str(e))
        return {'success': False, 'data': None, 'error': str(e)}


def cancel_snap_session(snap_token: str) -> dict:
    """Cancel an unused Snap session."""
    url = f'{_snap_base_url()}/snap/v1/transactions/{snap_token}/cancel'

    try:
        response = requests.post(url, headers=_headers(), timeout=15)
        if response.status_code in (200, 201):
            logger.info('Snap session %s cancelled', snap_token[:20])
            return {'success': True, 'data': response.json(), 'error': None}
        return {'success': False, 'data': None, 'error': f'Snap session cancel failed: {response.status_code}'}
    except requests.exceptions.RequestException as e:
        logger.error('Snap session cancel error: %s', str(e))
        return {'success': False, 'data': None, 'error': str(e)}


def expire_snap_session(snap_token: str) -> dict:
    """Expire an unused Snap session."""
    url = f'{_snap_base_url()}/snap/v1/transactions/{snap_token}/expire'

    try:
        response = requests.post(url, headers=_headers(), timeout=15)
        if response.status_code in (200, 201):
            logger.info('Snap session %s expired', snap_token[:20])
            return {'success': True, 'data': response.json(), 'error': None}
        return {'success': False, 'data': None, 'error': f'Snap session expire failed: {response.status_code}'}
    except requests.exceptions.RequestException as e:
        logger.error('Snap session expire error: %s', str(e))
        return {'success': False, 'data': None, 'error': str(e)}


def map_midtrans_status(transaction_status: str, fraud_status: str = '') -> str:
    """
    Map Midtrans transaction_status + fraud_status to local status string.

    Rules:
        settlement            → paid
        capture + accept      → paid
        capture + challenge   → awaiting_payment
        pending               → awaiting_payment
        deny / cancel / expire / failure → failed/cancelled/expired
        refund / partial_refund → refunded / partial_refund
    """
    status_map = {
        'settlement': 'paid',
        'capture': 'paid' if fraud_status == 'accept' else 'awaiting_payment',
        'pending': 'awaiting_payment',
        'deny': 'failed',
        'cancel': 'cancelled',
        'expire': 'expired',
        'failure': 'failed',
        'refund': 'refunded',
        'partial_refund': 'partial_refund',
        'authorize': 'awaiting_payment',
    }

    mapped = status_map.get(transaction_status, 'failed')

    if transaction_status == 'capture' and fraud_status:
        if fraud_status == 'deny':
            mapped = 'failed'
        elif fraud_status == 'challenge':
            mapped = 'awaiting_payment'

    logger.debug('Mapped status %s (fraud=%s) → %s', transaction_status, fraud_status, mapped)
    return mapped


def process_webhook_notification(data: dict) -> dict:
    """
    Process a Midtrans webhook notification and update local payment state.

    Extracted from MidtransNotificationView.post() so Celery reconciliation
    tasks can call it directly WITHOUT creating fake HTTP requests.
    Both the view and Celery tasks call this single function.
    """
    import logging
    from django.db import transaction
    from django.utils import timezone
    from django.utils.dateparse import parse_datetime
    from django.core.cache import cache
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    from copy import deepcopy
    from payments.models import MidtransTransaction, Payment
    from notifications.models import Notification
    from payments.services.wallet import credit_wallet

    logger = logging.getLogger(__name__)

    order_id = data.get('order_id', '')
    transaction_status = data.get('transaction_status', '')
    transaction_id = data.get('transaction_id', '')
    payment_type = data.get('payment_type', '')
    gross_amount = data.get('gross_amount', '0')
    fraud_status = data.get('fraud_status', 'accept')

    # Replay attack prevention
    transaction_time = data.get('transaction_time')
    if transaction_time:
        try:
            if isinstance(transaction_time, str):
                parsed_time = parse_datetime(transaction_time)
            else:
                parsed_time = transaction_time
            if parsed_time:
                if hasattr(parsed_time, 'tzinfo') and parsed_time.tzinfo is None:
                    from django.utils.timezone import make_aware
                    parsed_time = make_aware(parsed_time)
                age_seconds = abs((timezone.now() - parsed_time).total_seconds())
                if age_seconds > 120:
                    logger.warning('REPLAY: %s is %.0fs old - rejecting', order_id, age_seconds)
                    return {'status': 'rejected', 'message': 'Notification too old'}
        except Exception as e:
            logger.warning('Could not validate transaction_time: %s', str(e))

    # Idempotent dedup (2-minute cache window)
    dedup_key = f'midtrans_dedup:{order_id}:{transaction_status}:{transaction_id}'
    if cache.get(dedup_key):
        logger.info('DEDUP: %s already processed within 2min', order_id)
        return {'status': 'duplicate', 'message': 'Already processed'}
    cache.set(dedup_key, True, 120)

    # Find transaction
    midtrans_tx = MidtransTransaction.objects.filter(order_id=order_id).first()
    if not midtrans_tx:
        cache.set(f'midtrans_orphan:{order_id}', data, 3600)
        logger.warning('ORPHAN: %s not found locally - queued for reconciliation', order_id)
        return {'status': 'accepted_orphan', 'message': 'Logged for reconciliation'}

    payment = midtrans_tx.payment
    order = payment.order

    # Monotonic state machine
    if payment.payment_status in ('paid', 'refunded', 'chargeback'):
        if transaction_status in ('deny', 'cancel', 'expire', 'pending', 'authorize'):
            logger.warning('STATE GUARD: %s ignored for payment %s (current=%s)',
                           transaction_status, payment.id, payment.payment_status)
            return {'status': 'ignored', 'message': 'State protected'}

    def _notify(user_id, order_id, order_number, payment_status, message=''):
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f'notifications_{user_id}',
                    {'type': 'payment_update', 'order_id': order_id,
                     'order_number': order_number, 'status': payment_status,
                     'message': message,}
                )
        except Exception as e:
            logger.error('WS broadcast error: %s', str(e))

    with transaction.atomic():
        midtrans_tx.transaction_id = transaction_id
        midtrans_tx.transaction_status = transaction_status
        midtrans_tx.payment_type = payment_type
        midtrans_tx.transaction_time = data.get('transaction_time')
        midtrans_tx.status_code = data.get('status_code', '')
        midtrans_tx.status_message = data.get('status_message', '')
        midtrans_tx.fraud_status = fraud_status

        if data.get('va_number'):
            midtrans_tx.va_number = data['va_number']
            payment.va_number = data['va_number']
            payment.bank_name = data.get('bank', '')

        if data.get('settlement_time'):
            midtrans_tx.settlement_time = data['settlement_time']

        SENSITIVE_FIELDS = [
            'card_number', 'cvv', 'card_expire', 'card_token',
            'three_ds_authenticated', 'token_id', 'saved_token_id',
        ]
        safe_data = deepcopy(data) if isinstance(data, dict) else data
        if isinstance(safe_data, dict):
            for field in SENSITIVE_FIELDS:
                if field in safe_data:
                    safe_data[field] = '**REDACTED**'
        midtrans_tx.raw_response = safe_data
        midtrans_tx.save()

        # Fraud challenge handling
        if transaction_status == 'capture' and fraud_status == 'challenge':
            logger.warning('FRAUD CHALLENGE: order=%s', order_id)
            payment.payment_status = 'challenge'
            payment.save(update_fields=['payment_status'])
            if order:
                order.order_status = 'challenge'
                order.save(update_fields=['order_status'])
            return {'status': 'challenge_accepted'}

        # Chargeback handling
        if transaction_status == 'chargeback':
            logger.warning('CHARGEBACK: order=%s', order_id)
            payment.payment_status = 'chargeback'
            payment.save(update_fields=['payment_status'])
            if order:
                order.order_status = 'chargeback'
                order.save(update_fields=['order_status'])
            _notify(
                user_id=payment.user_id,
                order_id=order.id if order else 0,
                order_number=getattr(order, 'order_number', ''),
                payment_status='chargeback',
                message='Pembayaran di-chargeback. Tim kami akan menghubungi Anda.'
            )
            return {'status': 'chargeback_recorded'}

        # Refund / Partial Refund
        if transaction_status in ('refund', 'partial_refund'):
            mapped = 'partial_refund' if transaction_status == 'partial_refund' else 'refunded'
            payment.payment_status = mapped
            payment.save(update_fields=['payment_status'])
            if order:
                order.order_status = mapped
                order.save(update_fields=['order_status'])
            _notify(
                user_id=payment.user_id,
                order_id=order.id if order else 0,
                order_number=getattr(order, 'order_number', ''),
                payment_status=mapped,
                message=f'Pembayaran telah di-{mapped}'
            )
            return {'status': f'{mapped}_recorded'}

        # Settlement / Capture (Payment Success)
        if transaction_status in ('settlement', 'capture'):
            if fraud_status == 'accept':
                payment.mark_as_paid()

                is_topup = (order and getattr(order, 'notes', '') == 'TOPUP') or ('TOP-' in order_id)
                if is_topup:
                    # credit_wallet import at top of function ensures it's cached
                    try:
                        credit_wallet(
                            user=payment.user,
                            amount=float(gross_amount),
                            tx_type='topup',
                            description=f'Top Up saldo Warungio sebesar Rp {float(gross_amount):,}',
                            reference_type='midtrans',
                            reference_id=order_id,
                        )
                    except Exception as e:
                        logger.error('Wallet credit failed for top-up %s: %s', order_id, str(e))

                    _notify(
                        user_id=payment.user_id,
                        order_id=order.id if order else 0,
                        order_number=getattr(order, 'order_number', 'TOPUP'),
                        payment_status='paid',
                        message=f'Top Up berhasil! Rp {float(gross_amount):,}'
                    )
                else:
                    # Notification model imported at top of function (not in atomic block)
                    Notification.objects.create(
                        user_id=order.user_id,
                        notification_type='payment',
                        priority='high',
                        title='Pembayaran Berhasil',
                        description=f'Pembayaran untuk pesanan {order.order_number} berhasil!',
                        action_url=f'/buyer/order-detail/?id={order.id}',
                        action_text='Lihat Pesanan',
                    )
                    _notify(
                        user_id=order.user_id,
                        order_id=order.id,
                        order_number=order.order_number,
                        payment_status='paid',
                        message=f'Pembayaran untuk pesanan {order.order_number} berhasil!'
                    )

                    if order.store and order.store.user_id:
                        try:
                            channel_layer = get_channel_layer()
                            if channel_layer:
                                async_to_sync(channel_layer.group_send)(
                                    f'notifications_{order.store.user_id}',
                                    {'type': 'order_update', 'order_id': order.id,
                                     'order_number': order.order_number,
                                     'status': 'paid',
                                     'message': f'Pembayaran untuk {order.order_number} dikonfirmasi!',}
                                )
                                # Broadcast voice notification for successful payment
                                try:
                                    from notifications.voice_service import broadcast_online_order_voice
                                    customer_name = None
                                    if order.recipient_name:
                                        customer_name = order.recipient_name
                                    elif order.user:
                                        customer_name = order.user.full_name or order.user.email
                                    broadcast_online_order_voice(
                                        seller_user_id=order.store.user_id,
                                        customer_name=customer_name,
                                        amount=int(order.total_price),
                                        order_number=order.order_number,
                                        transaction_id=f'voice-{order.id}-{order.order_number}',
                                    )
                                except Exception as voice_err:
                                    logger.warning('Voice notification broadcast failed: %s', voice_err)
                        except Exception as exc:
                            logger.warning('Seller WS fail: %s', exc)

                midtrans_tx.settlement_time = timezone.now()
                midtrans_tx.save(update_fields=['settlement_time'])

        elif transaction_status in ('deny', 'cancel', 'expire'):
            payment.payment_status = 'failed' if transaction_status == 'deny' else transaction_status
            payment.save()
            if order:
                order.order_status = 'cancelled'
                order.save()
            _notify(
                user_id=order.user_id if order else payment.user_id,
                order_id=order.id if order else 0,
                order_number=getattr(order, 'order_number', ''),
                payment_status='failed',
                message='Pembayaran gagal. Silakan coba lagi.'
            )

        elif transaction_status == 'refund':
            payment.payment_status = 'refunded'
            payment.save()
            if order:
                order.order_status = 'refunded'
                order.save()
            _notify(
                user_id=order.user_id if order else payment.user_id,
                order_id=order.id if order else 0,
                order_number=getattr(order, 'order_number', ''),
                payment_status='refunded',
                message='Pembayaran telah direfund.'
            )

    return {'status': 'OK'}
