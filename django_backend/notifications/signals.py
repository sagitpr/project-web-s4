"""
Signal handlers for auto-generating notifications.
Listens for model events across the application and creates notifications.
"""

import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from django.core.cache import cache

from .services import (
    notify_new_order, notify_payment_confirmed, notify_order_status_change,
    notify_new_review, notify_stock_warning, notify_promotion, notify_system,
    notify_buyer_order_confirmed, notify_delivery_update,
    notify_refund_status, notify_wallet_topup, notify_review_reminder,
    notify_store_update, notify_account_activity, notify_new_follower,
    notify_user_welcome,
)


def _clear_dashboard_cache(store_id):
    """
    Invalidate dashboard and finance summary caches for a store.
    Called automatically when underlying data changes (new order, payment, etc.)
    to ensure the dashboard always displays live database values.
    """
    if store_id:
        cache.delete(f'dashboard_summary_{store_id}_week')
        cache.delete(f'dashboard_summary_{store_id}_month')
        cache.delete(f'dashboard_summary_{store_id}_year')
        cache.delete(f'finance_summary_{store_id}')

logger = logging.getLogger(__name__)


# ── Order Signals ──

def connect_order_signals():
    """Connect order-related signals (imported lazily to avoid circular imports)."""
    try:
        from orders.models import Order
        
        @receiver(post_save, sender=Order, weak=False, dispatch_uid='notif_new_order')
        def on_order_created(sender, instance, created, **kwargs):
            if not created:
                return
            # Clear dashboard cache so seller sees new order immediately
            if hasattr(instance, 'store_id') and instance.store_id:
                _clear_dashboard_cache(instance.store_id)

            # Notify seller of new order — use store owner
            if hasattr(instance, 'store') and instance.store and hasattr(instance.store, 'user'):
                seller_id = instance.store.user_id
                notify_new_order(
                    user_id=seller_id,
                    order_number=instance.order_number or f'#{instance.id}',
                    order_id=instance.id,
                    store_name=instance.store.store_name if hasattr(instance.store, 'store_name') else None,
                )

            # Notify buyer of order confirmation
            buyer_id = instance.user_id
            if buyer_id:
                notify_buyer_order_confirmed(
                    user_id=buyer_id,
                    order_number=instance.order_number or f'#{instance.id}',
                    order_id=instance.id,
                )
        
        # Pre-save to capture old status for change detection
        @receiver(pre_save, sender=Order, weak=False, dispatch_uid='notif_order_presave')
        def on_order_pre_save(sender, instance, **kwargs):
            if instance.pk:
                try:
                    old = sender.objects.get(pk=instance.pk)
                    instance._old_order_status = old.order_status
                    if hasattr(old, 'store_id'):
                        instance._old_store_id = old.store_id
                    instance._old_user_id = old.user_id if hasattr(old, 'user_id') else None
                except sender.DoesNotExist:
                    pass
        
        @receiver(post_save, sender=Order, weak=False, dispatch_uid='notif_order_status')
        def on_order_status_change(sender, instance, created, **kwargs):
            if created:
                return
            old_status = getattr(instance, '_old_order_status', None)
            if old_status and old_status != instance.order_status:
                # Clear dashboard cache — order status change affects stats
                if hasattr(instance, 'store_id') and instance.store_id:
                    _clear_dashboard_cache(instance.store_id)

                if hasattr(instance, 'store') and instance.store and hasattr(instance.store, 'user'):
                    seller_id = instance.store.user_id
                    notify_order_status_change(
                        user_id=seller_id,
                        order_number=instance.order_number or f'#{instance.id}',
                        order_id=instance.id,
                        old_status=old_status,
                        new_status=instance.order_status,
                    )
                # Also notify buyer (with buyer page URL)
                buyer_id = getattr(instance, '_old_user_id', None) or getattr(instance, 'user_id', None)
                if buyer_id:
                    notify_order_status_change(
                        user_id=buyer_id,
                        order_number=instance.order_number or f'#{instance.id}',
                        order_id=instance.id,
                        old_status=old_status,
                        new_status=instance.order_status,
                        is_buyer=True,
                    )
                    
                    # When order is completed, send review reminder to buyer
                    if instance.order_status == 'completed':
                        from .services import notify_review_reminder
                        notify_review_reminder(
                            user_id=buyer_id,
                            order_number=instance.order_number or f'#{instance.id}',
                            order_id=instance.id,
                        )
        
        logger.info('Order notification signals connected')
    except ImportError:
        logger.debug('Orders app not available, skipping order signals')
    except Exception as e:
        logger.warning('Failed to connect order signals: %s', e)


# ── Payment Signals ──

def connect_payment_signals():
    """Connect payment-related signals."""
    try:
        from payments.models import Payment
        
        # Pre-save to capture old payment_status
        @receiver(pre_save, sender=Payment, weak=False, dispatch_uid='notif_payment_presave')
        def on_payment_pre_save(sender, instance, **kwargs):
            if instance.pk:
                try:
                    old = sender.objects.get(pk=instance.pk)
                    instance._old_payment_status = old.payment_status
                    instance._old_transaction_status = getattr(old, 'transaction_status', None)
                except sender.DoesNotExist:
                    pass
        
        @receiver(post_save, sender=Payment, weak=False, dispatch_uid='notif_payment_confirmed')
        def on_payment_confirmed(sender, instance, created, **kwargs):
            if created:
                return
            old_status = getattr(instance, '_old_payment_status', None)
            new_status = instance.payment_status
            
            # Check if payment just transitioned to settlement
            is_newly_settled = (
                new_status == 'settlement' and old_status != 'settlement'
            ) or (
                hasattr(instance, 'transaction_status') and
                instance.transaction_status in ('settlement', 'capture') and
                getattr(instance, '_old_transaction_status', None) not in ('settlement', 'capture')
            )
            
            if is_newly_settled:
                order = getattr(instance, 'order', None)
                if order:
                    # Clear dashboard cache — payment confirmation affects revenue stats
                    if hasattr(order, 'store_id') and order.store_id:
                        _clear_dashboard_cache(order.store_id)

                    seller_id = order.store.user_id if hasattr(order, 'store') and order.store else None
                    buyer_id = order.user_id if hasattr(order, 'user_id') else None
                    
                    if seller_id:
                        notify_payment_confirmed(
                            user_id=seller_id,
                            order_number=order.order_number or f'#{order.id}',
                            order_id=order.id,
                            amount=float(instance.amount or 0),
                        )
                    if buyer_id:
                        from .services import create_notification
                        create_notification(
                            user_id=buyer_id,
                            notification_type='payment',
                            priority='high',
                            title='Pembayaran Berhasil',
                            description=f'Pembayaran untuk {order.order_number} berhasil dikonfirmasi.',
                            action_url=f'/buyer/orders/index.html?id={order.id}',
                            action_text='Lihat Pesanan',
                            metadata={'order_id': order.id, 'amount': str(instance.amount)},
                        )
        
        logger.info('Payment notification signals connected')
    except ImportError:
        logger.debug('Payments app not available, skipping payment signals')
    except Exception as e:
        logger.warning('Failed to connect payment signals: %s', e)


# ── Review Signals ──

def connect_review_signals():
    """Connect review-related signals."""
    try:
        from products.models import Review
        
        @receiver(post_save, sender=Review, weak=False, dispatch_uid='notif_new_review')
        def on_review_created(sender, instance, created, **kwargs):
            if not created:
                return
            product = getattr(instance, 'product', None)
            if product and hasattr(product, 'store') and product.store:
                # Clear dashboard cache — new review affects rating stats
                _clear_dashboard_cache(product.store.id)

                seller_id = product.store.user_id
                store_name = product.store.store_name if hasattr(product.store, 'store_name') else None
                notify_new_review(
                    user_id=seller_id,
                    store_name=store_name,
                    rating=float(instance.rating or 0),
                    review_id=instance.id,
                )
        
        logger.info('Review notification signals connected')
    except ImportError:
        logger.debug('Products app not available, skipping review signals')
    except Exception as e:
        logger.warning('Failed to connect review signals: %s', e)


# ── Product Signals (Low Stock) ──

def connect_product_signals():
    """Connect product-related signals (low stock)."""
    try:
        from products.models import Product
        
        # Pre-save to capture old stock value for change detection
        @receiver(pre_save, sender=Product, weak=False, dispatch_uid='notif_product_presave')
        def on_product_pre_save(sender, instance, **kwargs):
            if instance.pk:
                try:
                    old = sender.objects.get(pk=instance.pk)
                    instance._old_stock = old.stock
                except sender.DoesNotExist:
                    pass
        
        @receiver(post_save, sender=Product, weak=False, dispatch_uid='notif_low_stock')
        def on_product_stock_change(sender, instance, created, **kwargs):
            if created:
                return
            old_stock = getattr(instance, '_old_stock', None)
            current_stock = instance.stock
            
            # Only fire if stock actually decreased (or is at zero from any state)
            if current_stock is None:
                return
            if old_stock is not None and current_stock >= old_stock:
                return
            if current_stock <= 5:
                if hasattr(instance, 'store') and instance.store and hasattr(instance.store, 'user'):
                    seller_id = instance.store.user_id
                    notify_stock_warning(
                        user_id=seller_id,
                        product_name=instance.product_name if hasattr(instance, 'product_name') else 'Produk',
                        current_stock=current_stock,
                        threshold=5,
                    )
        
        logger.info('Product stock notification signals connected')
    except ImportError:
        logger.debug('Products app not available, skipping product signals')
    except Exception as e:
        logger.warning('Failed to connect product signals: %s', e)


# ── Delivery Signals ──

def connect_delivery_signals():
    """Connect delivery/shipping signals — notify buyer of status changes."""
    try:
        from orders.models import Delivery
        
        @receiver(pre_save, sender=Delivery, weak=False, dispatch_uid='notif_delivery_presave')
        def on_delivery_pre_save(sender, instance, **kwargs):
            if instance.pk:
                try:
                    old = sender.objects.get(pk=instance.pk)
                    instance._old_delivery_status = old.delivery_status
                except sender.DoesNotExist:
                    pass
        
        @receiver(post_save, sender=Delivery, weak=False, dispatch_uid='notif_delivery_update')
        def on_delivery_update(sender, instance, created, **kwargs):
            old_status = getattr(instance, '_old_delivery_status', None)
            # Only notify on actual status changes, not on initial creation (avoids spam)
            if not created and old_status and old_status != instance.delivery_status:
                order = getattr(instance, 'order', None)
                if order:
                    buyer_id = order.user_id
                    if buyer_id:
                        notify_delivery_update(
                            user_id=buyer_id,
                            order_number=order.order_number or f'#{order.id}',
                            order_id=order.id,
                            delivery_status=instance.delivery_status,
                            courier=instance.courier_name or None,
                        )
        
        logger.info('Delivery notification signals connected')
    except ImportError:
        logger.debug('Orders app not available, skipping delivery signals')
    except Exception as e:
        logger.warning('Failed to connect delivery signals: %s', e)


# ── Refund Signals ──

def connect_refund_signals():
    """Connect refund signals — notify seller on new refund, buyer on status change."""
    try:
        from refunds.models import Refund
        
        @receiver(post_save, sender=Refund, weak=False, dispatch_uid='notif_refund_created')
        def on_refund_created(sender, instance, created, **kwargs):
            if not created:
                return
            # Notify seller of new refund request
            if instance.store and hasattr(instance.store, 'user'):
                seller_id = instance.store.user_id
                notify_refund_status(
                    user_id=seller_id,
                    refund_number=instance.refund_number or f'#{instance.id}',
                    refund_id=instance.id,
                    status='pending',
                    amount=float(instance.amount_requested or 0),
                    is_buyer=False,
                )
        
        @receiver(pre_save, sender=Refund, weak=False, dispatch_uid='notif_refund_presave')
        def on_refund_pre_save(sender, instance, **kwargs):
            if instance.pk:
                try:
                    old = sender.objects.get(pk=instance.pk)
                    instance._old_refund_status = old.refund_status
                except sender.DoesNotExist:
                    pass
        
        @receiver(post_save, sender=Refund, weak=False, dispatch_uid='notif_refund_status')
        def on_refund_status_change(sender, instance, created, **kwargs):
            if created:
                return
            old_status = getattr(instance, '_old_refund_status', None)
            if old_status and old_status != instance.refund_status:
                # Notify buyer of status change
                if instance.user_id:
                    notify_refund_status(
                        user_id=instance.user_id,
                        refund_number=instance.refund_number or f'#{instance.id}',
                        refund_id=instance.id,
                        status=instance.refund_status,
                        amount=float(instance.amount_approved or instance.amount_requested or 0),
                        is_buyer=True,
                    )
        
        logger.info('Refund notification signals connected')
    except ImportError:
        logger.debug('Refunds app not available, skipping refund signals')
    except Exception as e:
        logger.warning('Failed to connect refund signals: %s', e)


# ── Wallet Transaction Signals ──

def connect_wallet_signals():
    """Connect wallet transaction signals — notify user of wallet activity."""
    try:
        from payments.models import WalletTransaction
        
        @receiver(post_save, sender=WalletTransaction, weak=False, dispatch_uid='notif_wallet_tx')
        def on_wallet_transaction(sender, instance, created, **kwargs):
            if not created:
                return
            user_id = instance.user_id or instance.wallet.user_id
            if not user_id:
                return
            
            amount = float(instance.amount or 0)
            
            if instance.tx_type == 'topup':
                notify_wallet_topup(
                    user_id=user_id,
                    amount=amount,
                    method=instance.description or 'Bank Transfer',
                )
            elif instance.tx_type == 'withdrawal':
                from .services import create_notification
                create_notification(
                    user_id=user_id,
                    notification_type='payment',
                    priority='medium',
                    title='Penarikan Saldo',
                    description=f'Penarikan saldo sebesar Rp {amount:,.0f} telah diproses.',
                    action_url='/seller/keuangan/index.html',
                    action_text='Lihat Keuangan',
                    metadata={'amount': str(amount), 'tx_type': 'withdrawal'},
                )
            elif instance.tx_type == 'refund':
                from .services import create_notification
                create_notification(
                    user_id=user_id,
                    notification_type='payment',
                    priority='high',
                    title='Dana Refund Masuk',
                    description=f'Dana refund sebesar Rp {amount:,.0f} telah masuk ke dompet Anda.',
                    action_url='/buyer/wallet/index.html',
                    action_text='Lihat Dompet',
                    metadata={'amount': str(amount), 'tx_type': 'refund'},
                )
        
        logger.info('Wallet transaction notification signals connected')
    except ImportError:
        logger.debug('Payments app not available, skipping wallet signals')
    except Exception as e:
        logger.warning('Failed to connect wallet signals: %s', e)


# ── Store Update Signals ──

def connect_store_signals():
    """Connect store update signals — notify seller of profile changes."""
    try:
        from stores.models import Store
        
        @receiver(pre_save, sender=Store, weak=False, dispatch_uid='notif_store_presave')
        def on_store_pre_save(sender, instance, **kwargs):
            if instance.pk:
                try:
                    old = sender.objects.get(pk=instance.pk)
                    changed_fields = []
                    tracked_fields = [
                        'store_name', 'description', 'address',
                        'store_logo', 'store_banner', 'open_time', 'close_time', 'status'
                    ]
                    for field in tracked_fields:
                        old_val = getattr(old, field, None)
                        new_val = getattr(instance, field, None)
                        if old_val != new_val:
                            changed_fields.append(field)
                    instance._changed_fields = changed_fields
                except sender.DoesNotExist:
                    pass
        
        @receiver(post_save, sender=Store, weak=False, dispatch_uid='notif_store_updated')
        def on_store_updated(sender, instance, created, **kwargs):
            if created:
                return
            changed = getattr(instance, '_changed_fields', None) or []
            if changed:
                for field in changed:
                    notify_store_update(
                        user_id=instance.user_id,
                        store_name=instance.store_name,
                        field_changed=field,
                    )
        
        logger.info('Store notification signals connected')
    except ImportError:
        logger.debug('Stores app not available, skipping store signals')
    except Exception as e:
        logger.warning('Failed to connect store signals: %s', e)


# ── Store Follow Signals ──

def connect_follow_signals():
    """Connect store follow/unfollow signals — notify seller on new follower."""
    try:
        from stores.models import StoreFollower

        @receiver(post_save, sender=StoreFollower, weak=False, dispatch_uid='notif_new_follower')
        def on_store_follow(sender, instance, created, **kwargs):
            if not created:
                return
            seller_id = instance.store.user_id
            follower_name = instance.user.full_name if hasattr(instance.user, 'full_name') else instance.user.email
            notify_new_follower(
                user_id=seller_id,
                store_name=instance.store.store_name,
                follower_name=follower_name[:50],  # truncate to avoid long names
            )

        logger.info('Follow notification signals connected')
    except ImportError:
        logger.debug('Stores app not available, skipping follow signals')
    except Exception as e:
        logger.warning('Failed to connect follow signals: %s', e)


# ── Promotion Signals ──

def connect_promotion_signals():
    """Connect promotion signals — notify store followers when promo is created."""
    try:
        from products.models import Promo

        @receiver(post_save, sender=Promo, weak=False, dispatch_uid='notif_promo_created')
        def on_promo_created(sender, instance, created, **kwargs):
            if not created:
                return
            if not instance.is_active or not instance.store:
                return

            # Build discount description
            if instance.discount_percent:
                discount_desc = f'Diskon {instance.discount_percent}%'
            elif instance.discount_amount > 0:
                discount_desc = f'Diskon Rp {float(instance.discount_amount):,.0f}'
            elif instance.promo_type == 'free_shipping':
                discount_desc = 'Gratis Ongkir!'
            elif instance.promo_type == 'flash_sale':
                discount_desc = 'Flash Sale — Jangan sampai kehabisan!'
            else:
                discount_desc = 'Promo spesial untuk Anda!'

            if instance.min_purchase > 0:
                discount_desc += f' (min. Rp {float(instance.min_purchase):,.0f})'

            # Notify store followers
            try:
                from stores.models import StoreFollower
                follower_ids = list(StoreFollower.objects.filter(
                    store=instance.store
                ).values_list('user_id', flat=True))

                notified_count = 0
                for follower_id in follower_ids:
                    notify_promotion(
                        user_id=follower_id,
                        promo_name=instance.promo_name,
                        promo_code=instance.promo_code or '',
                        discount_desc=discount_desc,
                        store_name=instance.store.store_name,
                        store_id=instance.store.id,
                    )
                    notified_count += 1

                if notified_count:
                    logger.info(
                        'Promo notification sent to %d followers for promo %s (store %s)',
                        notified_count, instance.id, instance.store_id,
                    )
            except Exception as inner_e:
                logger.warning('Failed to notify followers about promo %s: %s', instance.id, inner_e)

        logger.info('Promotion notification signals connected')
    except ImportError:
        logger.debug('Products app not available, skipping promotion signals')
    except Exception as e:
        logger.warning('Failed to connect promotion signals: %s', e)


# ── User Registration Signals ──

def connect_user_signals():
    """Connect user registration signals — send welcome notification on OTP verification."""
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()

        @receiver(post_save, sender=User, weak=False, dispatch_uid='notif_user_welcome')
        def on_user_verified(sender, instance, created, **kwargs):
            """
            Send welcome notification when a user completes registration.
            Detects completion by checking is_verified + registration_step == 'complete'.
            Uses pre-save tracking to only fire on the actual transition to 'complete'.
            """
            if created:
                return
            step = getattr(instance, 'registration_step', None)
            old_step = getattr(instance, '_old_registration_step', None)
            if step == 'complete' and old_step != 'complete':
                role = getattr(instance, 'role', 'buyer')
                full_name = getattr(instance, 'full_name', instance.email.split('@')[0])
                notify_user_welcome(
                    user_id=instance.id,
                    full_name=full_name,
                    role=role,
                )

        @receiver(pre_save, sender=User, weak=False, dispatch_uid='notif_user_presave')
        def on_user_pre_save(sender, instance, **kwargs):
            """Capture old registration_step before save to detect transitions."""
            if instance.pk:
                try:
                    old = sender.objects.get(pk=instance.pk)
                    instance._old_registration_step = old.registration_step
                except sender.DoesNotExist:
                    pass

        logger.info('User welcome notification signals connected')
    except ImportError:
        logger.debug('Auth user model not available, skipping user signals')
    except Exception as e:
        logger.warning('Failed to connect user signals: %s', e)


# ── Connect all signals ──

def connect_all():
    """Connect all notification signals."""
    connect_order_signals()
    connect_payment_signals()
    connect_delivery_signals()
    connect_refund_signals()
    connect_wallet_signals()
    connect_store_signals()
    connect_review_signals()
    connect_product_signals()
    connect_follow_signals()
    connect_promotion_signals()
    connect_user_signals()
    logger.info('All notification signals connected')
