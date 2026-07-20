"""
Signal handlers for the Engagement Engine.
Captures user behavior events and triggers engagement notifications.
Connects to existing models via lazy imports to avoid circular imports.
"""

import logging
from datetime import timedelta
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


def connect_all():
    """Connect all engagement signals."""
    _connect_user_signals()
    _connect_order_signals()
    _connect_cart_signals()
    _connect_favorite_signals()
    _connect_review_signals()
    _connect_payment_signals()
    _connect_ai_service_signals()
    _connect_store_signals()
    logger.info('All engagement signals connected')


def _record_behavior_event(user, event_type: str, event_category: str = '',
                            data: dict = None, value: float = None,
                            source: str = 'system', request=None):
    """Helper to record a behavior event."""
    from engagement.models import BehaviorEvent

    try:
        BehaviorEvent.objects.create(
            user=user,
            event_type=event_type,
            event_category=event_category,
            source=source,
            data=data or {},
            value=value,
            ip_address=getattr(request, 'META', {}).get('REMOTE_ADDR', None) if request else None,
            user_agent=getattr(request, 'META', {}).get('HTTP_USER_AGENT', '') if request else '',
            event_time=timezone.now(),
        )
    except Exception as e:
        logger.warning('Failed to record behavior event %s for %s: %s',
                       event_type, user.email if hasattr(user, 'email') else user, e)


def _update_behavior_profile(user):
    """Update user behavior profile asynchronously."""
    try:
        from engagement.tasks import update_user_profile_task
        update_user_profile_task.delay(user.id)
    except Exception as e:
        logger.debug('Failed to dispatch profile update: %s', e)


def _trigger_engagement_notification(user, trigger_type: str, context: dict = None):
    """Trigger an AI-powered engagement notification."""
    try:
        from engagement.tasks import generate_engagement_notification_task
        generate_engagement_notification_task.delay(user.id, trigger_type, context or {})
    except Exception as e:
        logger.debug('Failed to trigger engagement notification: %s', e)


# ── USER SIGNALS ──

def _connect_user_signals():
    """Connect user-related signals."""
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()

        @receiver(post_save, sender=User)
        def on_user_login(sender, instance, created, **kwargs):
            if created:
                return  # Registration handled separately
            
            # Track login via last_login field update
            if instance.last_login and hasattr(instance, '_old_last_login'):
                old_login = instance._old_last_login
                if old_login != instance.last_login:
                    _record_behavior_event(
                        instance, 'login', 'auth',
                        {'method': 'password'},
                        source='system'
                    )
                    _update_behavior_profile(instance)

        @receiver(pre_save, sender=User)
        def on_user_pre_save(sender, instance, **kwargs):
            if instance.pk:
                try:
                    old = sender.objects.get(pk=instance.pk)
                    instance._old_last_login = old.last_login
                    instance._old_registration_step = old.registration_step
                except sender.DoesNotExist:
                    pass

        logger.info('User engagement signals connected')
    except Exception as e:
        logger.debug('Failed to connect user signals: %s', e)


# ── ORDER SIGNALS ──

def _connect_order_signals():
    """Connect order-related signals."""
    try:
        from orders.models import Order

        @receiver(post_save, sender=Order)
        def on_order_saved(sender, instance, created, **kwargs):
            if created:
                _record_behavior_event(
                    instance.user, 'order_created', 'purchase',
                    {
                        'order_id': instance.id,
                        'order_number': instance.order_number,
                        'total': float(instance.total_price),
                        'store_id': instance.store_id,
                        'item_count': instance.items.count() if hasattr(instance, 'items') else 0,
                    },
                    value=float(instance.total_price),
                    source='system'
                )
                _update_behavior_profile(instance.user)
            else:
                # Check for status changes
                old_status = getattr(instance, '_old_order_status', None)
                if old_status and old_status != instance.order_status:
                    event_type_map = {
                        'paid': 'order_paid',
                        'completed': 'order_completed',
                        'cancelled': 'order_cancelled',
                        'refunded': 'order_refunded',
                    }
                    event_type = event_type_map.get(instance.order_status)
                    if event_type:
                        _record_behavior_event(
                            instance.user, event_type, 'purchase',
                            {
                                'order_id': instance.id,
                                'order_number': instance.order_number,
                                'status': instance.order_status,
                            },
                            source='system'
                        )
                        _update_behavior_profile(instance.user)

                        # Trigger engagement notification for completed orders
                        if instance.order_status == 'completed':
                            _trigger_engagement_notification(
                                instance.user, 'positive_reinforcement',
                                {
                                    'order_number': instance.order_number,
                                    'total': float(instance.total_price),
                                }
                            )

        logger.info('Order engagement signals connected')
    except Exception as e:
        logger.debug('Failed to connect order signals: %s', e)


# ── CART SIGNALS ──

def _connect_cart_signals():
    """Connect cart-related signals."""
    try:
        from orders.models import Cart

        @receiver(post_save, sender=Cart)
        def on_cart_saved(sender, instance, created, **kwargs):
            if created:
                _record_behavior_event(
                    instance.user, 'cart_add', 'cart',
                    {
                        'product_id': instance.product_id,
                        'product_name': instance.product.product_name if instance.product else '',
                        'qty': instance.qty,
                        'price': float(instance.product.price) if instance.product else 0,
                    },
                    source='system'
                )
                _update_behavior_profile(instance.user)

        # Use post_delete to track when cart items are removed
        from django.db.models.signals import post_delete

        @receiver(post_delete, sender=Cart, dispatch_uid='engagement_cart_deleted')
        def on_cart_deleted(sender, instance, **kwargs):
            # Track if all cart items are removed (abandon)
            from orders.models import Cart
            remaining = Cart.objects.filter(user=instance.user).count()
            if remaining == 0:
                _record_behavior_event(
                    instance.user, 'cart_abandon', 'cart',
                    {'last_product_id': instance.product_id},
                    source='system'
                )
                # Trigger abandoned cart notification after delay
                from engagement.tasks import check_abandoned_cart_task
                check_abandoned_cart_task.delay(instance.user.id)

        logger.info('Cart engagement signals connected')
    except Exception as e:
        logger.debug('Failed to connect cart signals: %s', e)


# ── FAVORITE SIGNALS ──

def _connect_favorite_signals():
    """Connect favorite/wishlist signals."""
    try:
        from products.models import Favorite

        @receiver(post_save, sender=Favorite)
        def on_favorite_added(sender, instance, created, **kwargs):
            if created:
                _record_behavior_event(
                    instance.user, 'wishlist_add', 'wishlist',
                    {
                        'product_id': instance.product_id,
                        'product_name': instance.product.product_name if instance.product else '',
                        'store_id': instance.product.store_id if instance.product else None,
                    },
                    source='system'
                )
                _update_behavior_profile(instance.user)

        logger.info('Favorite engagement signals connected')
    except Exception as e:
        logger.debug('Failed to connect favorite signals: %s', e)


# ── REVIEW SIGNALS ──

def _connect_review_signals():
    """Connect review signals."""
    try:
        from products.models import Review

        @receiver(post_save, sender=Review)
        def on_review_saved(sender, instance, created, **kwargs):
            if created:
                _record_behavior_event(
                    instance.user, 'review_written', 'social',
                    {
                        'product_id': instance.product_id,
                        'rating': instance.rating,
                        'has_comment': bool(instance.comment),
                    },
                    value=float(instance.rating),
                    source='system'
                )
                _update_behavior_profile(instance.user)

        logger.info('Review engagement signals connected')
    except Exception as e:
        logger.debug('Failed to connect review signals: %s', e)


# ── PAYMENT SIGNALS ──

def _connect_payment_signals():
    """Connect payment signals."""
    try:
        from payments.models import Payment

        @receiver(post_save, sender=Payment)
        def on_payment_saved(sender, instance, created, **kwargs):
            if created:
                _record_behavior_event(
                    instance.order.user if instance.order else None,
                    'payment_started', 'payment',
                    {
                        'order_id': instance.order_id,
                        'amount': float(instance.amount or 0),
                        'method': instance.payment_method or '',
                    },
                    value=float(instance.amount or 0),
                    source='system'
                )
            else:
                old_status = getattr(instance, '_old_payment_status', None)
                if old_status and old_status != instance.payment_status:
                    if instance.payment_status in ('settlement', 'capture'):
                        _record_behavior_event(
                            instance.order.user if instance.order else None,
                            'payment_success', 'payment',
                            {
                                'order_id': instance.order_id,
                                'amount': float(instance.amount or 0),
                            },
                            value=float(instance.amount or 0),
                            source='system'
                        )
                        _update_behavior_profile(instance.order.user if instance.order else None)
                    elif instance.payment_status in ('failed', 'deny', 'expire'):
                        _record_behavior_event(
                            instance.order.user if instance.order else None,
                            'payment_failed', 'payment',
                            {
                                'order_id': instance.order_id,
                                'status': instance.payment_status,
                            },
                            source='system'
                        )

        logger.info('Payment engagement signals connected')
    except Exception as e:
        logger.debug('Failed to connect payment signals: %s', e)


# ── AI SERVICE SIGNALS ──

def _connect_ai_service_signals():
    """Connect AI service usage signals."""
    try:
        # Track when AI product vision/freshness checks are created
        # Try multiple possible model locations for compatibility
        scan_model = None
        possible_models = [
            ('inventory.ai_scan.models', 'AIScanSession'),
            ('products.models', 'QualityCheck'),
        ]
        for module_path, class_name in possible_models:
            try:
                import importlib
                mod = importlib.import_module(module_path)
                scan_model = getattr(mod, class_name, None)
                if scan_model:
                    break
            except (ImportError, AttributeError):
                continue

        if scan_model:
            @receiver(post_save, sender=scan_model)
            def on_ai_scan_completed(sender, instance, created, **kwargs):
                if created:
                    user = getattr(instance, 'user', None) or getattr(instance, 'created_by', None)
                    if user:
                        _record_behavior_event(
                            user, 'ai_scan', 'ai_service',
                            {
                                'scan_id': instance.id,
                                'product_id': getattr(instance, 'product_id', None),
                                'scan_type': getattr(instance, 'scan_type', getattr(instance, 'quality_status', 'full')),
                            },
                            source='system'
                        )
                        _update_behavior_profile(user)

            logger.info('AI service engagement signals connected via %s', scan_model.__name__)
        else:
            logger.debug('No AI scan model found, AI service signals not connected')
    except Exception as e:
        logger.debug('AI service signals not available: %s', e)


# ── STORE SIGNALS ──

def _connect_store_signals():
    """Connect store follow signals."""
    try:
        from stores.models import StoreFollower

        @receiver(post_save, sender=StoreFollower)
        def on_store_follow(sender, instance, created, **kwargs):
            if created:
                _record_behavior_event(
                    instance.user, 'store_follow', 'social',
                    {
                        'store_id': instance.store_id,
                        'store_name': instance.store.store_name if instance.store else '',
                    },
                    source='system'
                )
                _update_behavior_profile(instance.user)

        logger.info('Store engagement signals connected')
    except Exception as e:
        logger.debug('Failed to connect store signals: %s', e)
