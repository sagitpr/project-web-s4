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
