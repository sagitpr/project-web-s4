"""
Notification service for Warungio Marketplace.
Handles creating notifications and broadcasting them via WebSocket.
"""

import json
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone

logger = logging.getLogger(__name__)


def create_notification(user_id, notification_type, title, description=None,
                        priority='medium', action_url=None, action_text=None,
                        metadata=None, send_ws=True):
    """
    Create a notification and optionally broadcast it via WebSocket.
    
    Returns the created Notification instance or None on failure.
    """
    from .models import Notification
    
    try:
        notification = Notification.objects.create(
            user_id=user_id,
            notification_type=notification_type,
            priority=priority,
            title=title,
            description=description or '',
            action_url=action_url or '',
            action_text=action_text or '',
            metadata=metadata or {},
        )
        
        if send_ws:
            broadcast_notification(notification)
        
        return notification
    except Exception as e:
        logger.warning('Failed to create notification: %s', e)
        return None


def broadcast_notification(notification):
    """
    Broadcast a notification to the user via WebSocket channel layer.
    Falls back to InMemoryChannelLayer if Redis is unavailable.
    """
    try:
        channel_layer = get_channel_layer()
        group_name = f'notifications_{notification.user_id}'
        
        event = {
            'type': 'send_notification',
            'id': notification.id,
            'notification_type': notification.notification_type,
            'title': notification.title,
            'description': notification.description or '',
            'priority': notification.priority,
            'action_url': notification.action_url or '',
            'created_at': notification.created_at.isoformat() if notification.created_at else '',
        }
        
        async_to_sync(channel_layer.group_send)(group_name, event)
    except Exception as e:
        logger.warning('Failed to broadcast notification: %s', e)


# ==============================================================================
# Convenience helpers for specific notification types
# ==============================================================================

def notify_new_order(user_id, order_number, order_id, store_name=None):
    """Notify about a new order."""
    return create_notification(
        user_id=user_id,
        notification_type='order',
        priority='high' if store_name else 'medium',
        title='Pesanan Baru',
        description=f'Pesanan {order_number} telah dibuat.' +
                    (f' oleh {store_name}' if store_name else ''),
        action_url=f'/seller/orders/index.html?id={order_id}',
        action_text='Lihat Pesanan',
        metadata={'order_id': order_id, 'order_number': order_number},
    )


def notify_payment_confirmed(user_id, order_number, order_id, amount):
    """Notify about payment confirmation."""
    return create_notification(
        user_id=user_id,
        notification_type='payment',
        priority='high',
        title='Pembayaran Dikonfirmasi',
        description=f'Pembayaran untuk pesanan {order_number} sebesar Rp {amount:,.0f} telah dikonfirmasi.',
        action_url=f'/seller/orders/index.html?id={order_id}',
        action_text='Lihat Detail',
        metadata={'order_id': order_id, 'order_number': order_number, 'amount': str(amount)},
    )


def notify_order_status_change(user_id, order_number, order_id, old_status, new_status, is_buyer=False):
    """Notify about order status change.
    
    Routes to buyer or seller page based on is_buyer flag.
    """
    status_labels = {
        'pending': 'Menunggu',
        'paid': 'Dibayar',
        'processed': 'Diproses',
        'shipped': 'Dikirim',
        'completed': 'Selesai',
        'cancelled': 'Dibatalkan',
        'refunded': 'Direfund',
    }
    old_label = status_labels.get(old_status, old_status)
    new_label = status_labels.get(new_status, new_status)
    
    action_url = f'/buyer/orders/index.html?id={order_id}' if is_buyer else f'/seller/orders/index.html?id={order_id}'
    
    return create_notification(
        user_id=user_id,
        notification_type='order',
        priority='medium',
        title=f'Pesanan {new_label}',
        description=f'Status pesanan {order_number} berubah dari {old_label} menjadi {new_label}.',
        action_url=action_url,
        action_text='Lihat Pesanan',
        metadata={
            'order_id': order_id, 'order_number': order_number,
            'old_status': old_status, 'new_status': new_status,
        },
    )


def notify_buyer_order_confirmed(user_id, order_number, order_id):
    """Notify buyer that their order is confirmed."""
    return create_notification(
        user_id=user_id,
        notification_type='order',
        priority='high',
        title='Pesanan Dikonfirmasi',
        description=f'Pesanan {order_number} telah dikonfirmasi dan sedang diproses.',
        action_url=f'/buyer/orders/index.html?id={order_id}',
        action_text='Lihat Pesanan',
        metadata={'order_id': order_id, 'order_number': order_number},
    )


def notify_delivery_update(user_id, order_number, order_id, delivery_status, courier=None):
    """Notify buyer about delivery/shipping update."""
    status_labels = {
        'menunggu_konfirmasi': 'Menunggu Konfirmasi',
        'diproses_penjual': 'Diproses Penjual',
        'menunggu_penjemputan': 'Menunggu Penjemputan',
        'kurir_menjemput': 'Kurir Menjemput',
        'dalam_perjalanan': 'Dalam Perjalanan',
        'pesanan_diterima': 'Pesanan Diterima',
        'dibatalkan': 'Dibatalkan',
    }
    label = status_labels.get(delivery_status, delivery_status)
    courier_info = f' via {courier}' if courier else ''
    
    return create_notification(
        user_id=user_id,
        notification_type='order',
        priority='high',
        title=f'Pengiriman {label}',
        description=f'Status pengiriman untuk {order_number}: {label}{courier_info}.',
        action_url=f'/buyer/orders/index.html?id={order_id}',
        action_text='Lacak Pesanan',
        metadata={
            'order_id': order_id, 'order_number': order_number,
            'delivery_status': delivery_status, 'courier': courier,
        },
    )


def notify_refund_status(user_id, refund_number, refund_id, status, amount, is_buyer=False):
    """Notify about refund status change."""
    status_labels = {
        'pending': 'Menunggu Review',
        'under_review': 'Sedang Ditinjau',
        'approved': 'Disetujui',
        'rejected': 'Ditolak',
        'cancelled': 'Dibatalkan',
        'refunded': 'Telah Direfund',
    }
    label = status_labels.get(status, status)
    target = 'Pembeli' if is_buyer else 'Penjual'
    action_url = f'/seller/refunds/{refund_id}/' if not is_buyer else f'/buyer/orders/index.html?refund={refund_id}'
    
    return create_notification(
        user_id=user_id,
        notification_type='payment',
        priority='high',
        title=f'Refund {label}',
        description=f'Status refund {refund_number}: {label} (Rp {amount:,.0f}).',
        action_url=action_url,
        action_text='Lihat Refund',
        metadata={
            'refund_id': refund_id, 'refund_number': refund_number,
            'refund_status': status, 'amount': str(amount),
        },
    )


def notify_wallet_topup(user_id, amount, method=None):
    """Notify user about wallet top-up."""
    method_info = f' melalui {method}' if method else ''
    return create_notification(
        user_id=user_id,
        notification_type='payment',
        priority='medium',
        title='Top Up Berhasil',
        description=f'Saldo Warungio Anda bertambah Rp {amount:,.0f}{method_info}.',
        action_url='/buyer/wallet/index.html',
        action_text='Lihat Dompet',
        metadata={'amount': str(amount), 'method': method or ''},
    )


def notify_review_reminder(user_id, order_number, order_id):
    """Send review reminder to buyer after order completion."""
    return create_notification(
        user_id=user_id,
        notification_type='review',
        priority='low',
        title='Beri Ulasan',
        description=f'Pesanan {order_number} sudah selesai. Beri ulasan untuk membantu penjual lain!',
        action_url=f'/buyer/orders/index.html?id={order_id}',
        action_text='Beri Ulasan',
        metadata={'order_id': order_id, 'order_number': order_number},
    )


def notify_store_update(user_id, store_name, field_changed):
    """Notify seller about store profile updates."""
    field_labels = {
        'store_name': 'Nama Toko',
        'description': 'Deskripsi Toko',
        'address': 'Alamat',
        'phone': 'No. Telepon',
        'store_logo': 'Logo Toko',
        'store_banner': 'Banner Toko',
        'open_time': 'Jam Buka',
        'close_time': 'Jam Tutup',
        'status': 'Status Toko',
    }
    label = field_labels.get(field_changed, field_changed)
    
    return create_notification(
        user_id=user_id,
        notification_type='system',
        priority='low',
        title='Toko Diperbarui',
        description=f'{store_name}: {label} berhasil diperbarui.',
        action_url='/seller/pengaturan/index.html',
        action_text='Pengaturan',
        metadata={'store_name': store_name, 'field_changed': field_changed},
    )


def notify_new_review(user_id, store_name, rating, review_id=None):
    """Notify about a new product review."""
    return create_notification(
        user_id=user_id,
        notification_type='review',
        priority='medium',
        title='Ulasan Baru',
        description=f'{store_name} menerima ulasan baru dengan rating {rating} bintang.' if store_name else 'Pembeli memberikan ulasan baru.',
        action_url='/seller/ulasan/index.html',
        action_text='Lihat Ulasan',
        metadata={'review_id': review_id, 'rating': rating},
    )


def notify_stock_warning(user_id, product_name, current_stock, threshold=5):
    """Notify about low stock."""
    priority = 'urgent' if current_stock == 0 else 'high'
    title = 'Stok Habis' if current_stock == 0 else 'Peringatan Stok'
    desc = f'Stok {product_name} habis!' if current_stock == 0 else f'Stok {product_name} tersisa {current_stock}. Segera restok!'
    
    return create_notification(
        user_id=user_id,
        notification_type='product',
        priority=priority,
        title=title,
        description=desc,
        action_url='/seller/products/index.html',
        action_text='Lihat Produk',
        metadata={'product_name': product_name, 'current_stock': current_stock, 'threshold': threshold},
    )


def notify_wallet_transaction(user_id, amount, transaction_type, description=''):
    """Notify about a wallet transaction."""
    if transaction_type == 'credit':
        title = 'Saldo Masuk'
        desc = description or f'Saldo Warungio Anda bertambah Rp {amount:,.0f}.'
    else:
        title = 'Penarikan Saldo'
        desc = description or f'Penarikan saldo sebesar Rp {amount:,.0f} telah diproses.'
    
    return create_notification(
        user_id=user_id,
        notification_type='payment',
        priority='medium',
        title=title,
        description=desc,
        action_url='/seller/keuangan/index.html',
        action_text='Lihat Keuangan',
        metadata={'amount': str(amount), 'transaction_type': transaction_type},
    )


def notify_promotion(user_id, promo_name, promo_code, discount_desc, store_name=None, store_id=None):
    """Notify about a promotion."""
    action_url = f'/seller/promo-diskon/index.html'
    if store_id:
        action_url = f'/stores/{store_id}/promos/'
    description = f'{store_name}: {discount_desc}' if store_name else discount_desc
    return create_notification(
        user_id=user_id,
        notification_type='promo',
        priority='medium',
        title=f'Promo: {promo_name}',
        description=description,
        action_url=action_url,
        action_text='Lihat Promo',
        metadata={'promo_name': promo_name, 'promo_code': promo_code, 'store_name': store_name, 'store_id': store_id},
    )


def notify_system(user_id, title, description, action_url=None):
    """Send a system announcement."""
    return create_notification(
        user_id=user_id,
        notification_type='system',
        priority='low',
        title=title,
        description=description,
        action_url=action_url or '',
        action_text='Detail' if action_url else '',
    )


def notify_account_activity(user_id, activity, description):
    """Notify about account activity."""
    return create_notification(
        user_id=user_id,
        notification_type='system',
        priority='low',
        title=activity,
        description=description,
        action_url='/seller/pengaturan/index.html',
        action_text='Pengaturan',
        metadata={'activity': activity},
    )


def notify_new_follower(user_id, store_name, follower_name):
    """Notify seller that someone followed their store."""
    return create_notification(
        user_id=user_id,
        notification_type='follow',
        priority='medium',
        title='Pengikut Baru',
        description=f'{follower_name} mulai mengikuti {store_name}.',
        action_url='/seller/dashboard/',
        action_text='Lihat Dashboard',
        metadata={'store_name': store_name, 'follower_name': follower_name},
    )


def notify_user_welcome(user_id, full_name, role='buyer'):
    """Send welcome notification to newly registered user."""
    if role == 'seller':
        title = 'Selamat Datang, Mitra Warungio!'
        description = f'{full_name}, toko Anda sudah siap! Mulai tambahkan produk dan terima pesanan pertama Anda.'
        action_url = '/seller/dashboard/'
        action_text = 'Mulai Berjualan'
    else:
        title = 'Selamat Datang di Warungio!'
        description = f'Halo {full_name}, jelajahi berbagai produk segar dari pedagang sekitar Anda.'
        action_url = '/'
        action_text = 'Mulai Belanja'
    
    return create_notification(
        user_id=user_id,
        notification_type='system',
        priority='low',
        title=title,
        description=description,
        action_url=action_url,
        action_text=action_text,
        metadata={'role': role},
    )


# ═══════════════════════════════════════════════════════════════════════════
# Alias for backward compatibility (used by inventory.expiry_service)
# ═══════════════════════════════════════════════════════════════════════════

send_notification = create_notification
