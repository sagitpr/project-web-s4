"""
QR Code generation & verification for Delivery Pickup & Delivery.

Generates unique, tamper-resistant QR code strings using UUID + HMAC signature.
Stores codes in Delivery model (qr_pickup_code, qr_delivery_code).
Verification checks both the stored code AND the HMAC signature.

No external QR library required — the QR string can be rendered as a QR image
on the frontend using any JS QR library (e.g., qrcode.js, QRCodeStyling).
"""

import hashlib
import hmac
import uuid
from typing import Dict, Optional

from django.conf import settings


def _get_hmac_key() -> str:
    """Get HMAC key for QR code signing. Uses SECRET_KEY as base."""
    return hashlib.sha256(settings.SECRET_KEY.encode()).hexdigest()[:32]


def generate_qr_code(delivery, code_type: str) -> str:
    """
    Generate a unique, signed QR code string for pickup or delivery.

    Format: WRG-{TYPE}-{DELIVERY_ID}-{UUID}-{HMAC_SIG}

    Args:
        delivery: Delivery model instance
        code_type: 'pickup' or 'delivery'

    Returns:
        str: The QR code string
    """
    prefix = 'PICKUP' if code_type == 'pickup' else 'DELIVERY'
    unique_id = uuid.uuid4().hex[:12].upper()
    order_id = delivery.order_id

    # Base payload
    payload = f'{prefix}-{delivery.id}-{order_id}-{unique_id}'

    # Sign with HMAC
    hmac_key = _get_hmac_key()
    signature = hmac.new(
        hmac_key.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()[:8].upper()

    qr_code = f'WRG-{payload}-{signature}'
    return qr_code


def verify_qr_code(delivery, qr_code: str, code_type: str) -> Dict:
    """
    Verify a QR code for pickup or delivery.

    Checks:
    1. The stored QR code matches the provided one
    2. The HMAC signature is valid (tamper resistance)
    3. The code hasn't already been used (delivery already completed)

    Args:
        delivery: Delivery model instance
        qr_code: The QR code string to verify
        code_type: 'pickup' or 'delivery'

    Returns:
        dict with 'valid': True/False, and optional 'error' message
    """
    stored_code = delivery.qr_pickup_code if code_type == 'pickup' else delivery.qr_delivery_code

    if not stored_code:
        return {'valid': False, 'error': 'QR Code belum dibuat.'}

    # Check if already completed
    if code_type == 'pickup' and delivery.picked_up_at:
        return {'valid': False, 'error': 'Pickup sudah dilakukan sebelumnya.'}

    if code_type == 'delivery' and delivery.delivered_at:
        return {'valid': False, 'error': 'Pengiriman sudah selesai sebelumnya.'}

    # Match stored code
    if qr_code.strip().upper() != stored_code.strip().upper():
        return {'valid': False, 'error': 'QR Code tidak cocok.'}

    # Verify HMAC signature
    try:
        parts = qr_code.split('-')
        # Format: WRG-PICKUP/TYPE-DELIVERY_ID-ORDER_ID-UUID-SIGNATURE
        if len(parts) < 6:
            return {'valid': False, 'error': 'Format QR Code tidak valid.'}

        prefix = parts[1].upper()
        expected_prefix = 'PICKUP' if code_type == 'pickup' else 'DELIVERY'
        if prefix != expected_prefix:
            return {'valid': False, 'error': f'QR Code bukan untuk {code_type}.'}

        received_sig = parts[-1].upper()

        hmac_key = _get_hmac_key()
        uuid_part = (parts[4] if len(parts) > 4 else '').upper()
        expected_sig = hmac.new(
            hmac_key.encode(),
            f'{prefix}-{delivery.id}-{delivery.order_id}-{uuid_part}'.encode(),
            hashlib.sha256
        ).hexdigest()[:8].upper()

        if received_sig != expected_sig:
            return {'valid': False, 'error': 'Tanda tangan QR Code tidak valid.'}

    except (ValueError, IndexError, KeyError, TypeError) as e:
        return {'valid': False, 'error': f'Gagal memverifikasi QR Code: {str(e)}'}

    return {'valid': True}
