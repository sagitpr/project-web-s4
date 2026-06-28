"""
Notifications service layer for Warungio Marketplace.

Provides helper functions for creating and broadcasting notifications
across the application. Centralizes Notification model creation +
WebSocket broadcasting logic.
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from .models import Notification


def send_notification(
    user_id,
    title,
    description='',
    notification_type='system',
    priority='medium',
    action_url='',
    action_text='',
    metadata=None,
) -> Notification:
    """
    Create a Notification record and broadcast via WebSocket.

    Args:
        user_id: User ID to notify
        title: Notification title
        description: Notification description/body
        notification_type: 'order', 'payment', 'chat', 'promo', 'system', etc.
        priority: 'low', 'medium', 'high', 'urgent'
        action_url: URL to navigate when clicked
        action_text: Button text for action
        metadata: Optional dict for additional data

    Returns:
        Notification model instance
    """
    notification = Notification.objects.create(
        user_id=user_id,
        title=title,
        description=description,
        notification_type=notification_type,
        priority=priority,
        action_url=action_url,
        action_text=action_text,
        metadata=metadata or {},
    )

    # Broadcast via WebSocket
    _broadcast_to_user(
        user_id=user_id,
        message={
            'type': 'notification',
            'id': notification.id,
            'notification_type': notification.notification_type,
            'title': notification.title,
            'description': notification.description,
            'priority': notification.priority,
            'action_url': notification.action_url,
            'created_at': notification.created_at.isoformat(),
        },
    )

    return notification


def send_order_notification(user_id, order_id, order_number, status, message):
    """
    Send order update notification + broadcast.
    """
    notification = Notification.objects.create(
        user_id=user_id,
        notification_type='order',
        priority='high' if status in ('paid', 'shipped', 'on_delivery', 'completed', 'cancelled') else 'medium',
        title=f'Pesanan {order_number}',
        description=message,
        action_url=f'/buyer/orders/index.html?id={order_id}',
        action_text='Lihat Pesanan',
        metadata={'order_id': order_id, 'order_number': order_number, 'status': status},
    )

    _broadcast_to_user(
        user_id=user_id,
        message={
            'type': 'order_update',
            'order_id': order_id,
            'order_number': order_number,
            'status': status,
            'message': message,
        },
    )

    return notification


def send_payment_notification(user_id, order_id, order_number, payment_status, message=''):
    """
    Send payment update notification + broadcast.
    """
    notification = Notification.objects.create(
        user_id=user_id,
        notification_type='payment',
        priority='high' if payment_status == 'paid' else 'medium',
        title=f'Pembayaran {order_number}' if order_number else 'Pembayaran',
        description=message,
        action_url=f'/buyer/orders/index.html?id={order_id}' if order_id else '',
        action_text='Lihat Detail',
        metadata={'order_id': order_id, 'order_number': order_number, 'payment_status': payment_status},
    )

    _broadcast_to_user(
        user_id=user_id,
        message={
            'type': 'payment_update',
            'order_id': order_id,
            'order_number': order_number,
            'status': payment_status,
            'message': message,
        },
    )

    return notification


def send_delivery_notification(user_id, order_id, order_number, delivery_status, tracking_number='', courier=''):
    """
    Send delivery tracking update via WebSocket (without creating DB record
    to avoid flooding the notification list with transient status updates).
    """
    status_messages = {
        'diproses_penjual': 'Pesanan sedang diproses oleh penjual.',
        'menunggu_penjemputan': 'Pesanan siap dijemput kurir!',
        'kurir_menjemput': 'Kurir sedang menuju ke toko untuk mengambil pesanan.',
        'dalam_perjalanan': 'Pesanan sedang dalam perjalanan menuju alamat kamu.',
        'pesanan_diterima': 'Pesanan telah sampai di alamat tujuan!',
        'dibatalkan': 'Pengiriman pesanan dibatalkan.',
    }
    message = status_messages.get(delivery_status, f'Status pengiriman: {delivery_status}')

    _broadcast_to_user(
        user_id=user_id,
        message={
            'type': 'delivery_update',
            'order_id': order_id,
            'order_number': order_number,
            'delivery_status': delivery_status,
            'tracking_number': tracking_number,
            'courier': courier,
            'message': message,
        },
    )


def notify_multiple_users(user_ids, title, description='', notification_type='system', priority='medium'):
    """
    Send the same notification to multiple users.
    Creates individual Notification records for each user.
    """
    notifications = []
    for user_id in user_ids:
        notification = send_notification(
            user_id=user_id,
            title=title,
            description=description,
            notification_type=notification_type,
            priority=priority,
        )
        notifications.append(notification)
    return notifications


def _broadcast_to_user(user_id, message):
    """Internal helper to broadcast a message via WebSocket channel layer."""
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'notifications_{user_id}',
                message,
            )
    except Exception:
        pass  # WebSocket layer unavailable silently
