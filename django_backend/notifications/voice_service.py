"""
Voice Notification Service for Warungio Marketplace.

Broadcasts text-to-speech (TTS) voice notification events to sellers
via the existing WebSocket infrastructure (notifications_{user_id} group).

The frontend uses the Web Speech API (SpeechSynthesis) to convert the
notification text into spoken Indonesian — no external TTS API needed.

Usage:
    from notifications.voice_service import broadcast_voice_notification

    # For online marketplace payment
    broadcast_voice_notification(
        seller_user_id=store.user_id,
        transaction_type='online_order',
        customer_name='Budi',
        amount=125000,
        order_number='WRG-001',
    )

    # For offline POS transaction
    broadcast_voice_notification(
        seller_user_id=store.user_id,
        transaction_type='pos_sale',
        customer_name=None,
        amount=50000,
        order_number='POS-20240101-001',
    )
"""

import logging
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

# ── Voice Notification Types ──
TYPE_ONLINE_ORDER = 'online_order'    # Marketplace order payment confirmed
TYPE_POS_SALE = 'pos_sale'            # Offline POS/cashier transaction


def _format_rupiah(amount):
    """Format amount to Indonesian rupiah string (e.g., '125.000')."""
    try:
        # Format with Indonesian thousands separator (.)
        s = f"{int(amount):,}".replace(',', '.')
        return s
    except (ValueError, TypeError):
        return '0'


def _build_voice_text(transaction_type, customer_name, amount, order_number):
    """
    Build the natural Indonesian speech text for the notification.

    Returns None for non-success transaction types (only success is spoken).
    """
    if transaction_type == TYPE_ONLINE_ORDER:
        # Online marketplace order — payment confirmed
        name = customer_name or 'Pelanggan'
        amount_str = _format_rupiah(amount)
        return (
            f"Pesanan baru dari {name}. "
            f"Total pesanan Rp{amount_str}. "
            "Pembayaran telah diterima. Silakan segera diproses."
        )

    elif transaction_type == TYPE_POS_SALE:
        # Offline POS transaction — payment confirmed at cashier
        amount_str = _format_rupiah(amount)
        return (
            f"Transaksi berhasil. "
            f"Total pembayaran Rp{amount_str}. "
            "Terima kasih."
        )

    return None


def broadcast_voice_notification(
    seller_user_id,
    transaction_type,
    customer_name=None,
    amount=0,
    order_number='',
    transaction_id=None,
):
    """
    Broadcast a voice notification event via WebSocket to the seller.

    The frontend VoiceNotificationManager listens for this event and
    speaks the text using the Web Speech API.

    Idempotency: The frontend uses transaction_id to prevent duplicate
    playback if the same event is received multiple times (e.g., after
    WebSocket reconnection or page refresh).

    Args:
        seller_user_id: The seller's user ID (notification group recipient)
        transaction_type: TYPE_ONLINE_ORDER or TYPE_POS_SALE
        customer_name: Buyer/customer name (optional, defaults to 'Pelanggan')
        amount: Transaction amount in IDR
        order_number: Order reference number
        transaction_id: Unique ID for idempotency (auto-generated if not provided)
    """
    voice_text = _build_voice_text(
        transaction_type=transaction_type,
        customer_name=customer_name,
        amount=amount,
        order_number=order_number,
    )

    # Server-wide kill switch via environment variable
    if not settings.VOICE_NOTIFICATION_ENABLED:
        logger.debug(
            'Voice notification skipped — VOICE_NOTIFICATION_ENABLED=False '
            'for type=%s order=%s',
            transaction_type, order_number,
        )
        return

    if not voice_text:
        logger.debug(
            'Voice notification skipped — no text generated '
            'for type=%s amount=%s order=%s',
            transaction_type, amount, order_number,
        )
        return

    # Generate a deterministic transaction ID if not provided
    if not transaction_id:
        import hashlib
        unique_str = f"{transaction_type}:{order_number}:{amount}:{customer_name or ''}"
        transaction_id = hashlib.md5(unique_str.encode()).hexdigest()[:16]

    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.warning('Channel layer unavailable — voice notification not sent')
            return

        group_name = f'notifications_{seller_user_id}'

        event = {
            'type': 'voice_notification',
            'voice_type': 'tts',
            'transaction_type': transaction_type,
            'text': voice_text,
            'amount': int(amount),
            'order_number': order_number,
            'customer_name': customer_name or '',
            'transaction_id': transaction_id,
        }

        async_to_sync(channel_layer.group_send)(group_name, event)

        logger.info(
            'Voice notification broadcast — user=%s type=%s order=%s '
            'amount=%s customer=%s tx_id=%s',
            seller_user_id, transaction_type, order_number,
            amount, customer_name or '(anon)', transaction_id,
        )

    except Exception as e:
        logger.error(
            'Failed to broadcast voice notification — user=%s type=%s: %s',
            seller_user_id, transaction_type, e,
        )


def broadcast_pos_transaction_voice(seller_user_id, amount, order_number, transaction_id=None):
    """
    Shorthand: broadcast voice for an offline POS transaction.
    """
    broadcast_voice_notification(
        seller_user_id=seller_user_id,
        transaction_type=TYPE_POS_SALE,
        customer_name=None,
        amount=amount,
        order_number=order_number,
        transaction_id=transaction_id,
    )


def broadcast_online_order_voice(seller_user_id, customer_name, amount, order_number, transaction_id=None):
    """
    Shorthand: broadcast voice for an online marketplace order payment.
    """
    broadcast_voice_notification(
        seller_user_id=seller_user_id,
        transaction_type=TYPE_ONLINE_ORDER,
        customer_name=customer_name,
        amount=amount,
        order_number=order_number,
        transaction_id=transaction_id,
    )
