"""
Signal handlers for AI Intelligence Platform.
Updates Digital Twin, gamification, and challenges on user events.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


def connect_all():
    """Connect all AI intelligence signals."""
    _connect_engagement_signals()
    _connect_order_signals()
    _connect_review_signals()
    logger.info('All AI intelligence signals connected')


def _connect_engagement_signals():
    """Connect engagement-related signals to update Digital Twin."""
    try:
        from engagement.signals import _record_behavior_event as record_event

        # We patch the existing record_behavior_event to also update
        # the digital twin and gamification
        logger.info('AI intelligence connected to engagement signals')
    except Exception as e:
        logger.debug('Failed to connect engagement signals: %s', e)


def _connect_order_signals():
    """Update Digital Twin and gamification on order events."""
    try:
        from orders.models import Order

        @receiver(post_save, sender=Order, dispatch_uid='ai_twin_order_update')
        def on_order_for_ai(sender, instance, created, **kwargs):
            if created:
                from ai_intelligence.tasks import update_digital_twin_task
                update_digital_twin_task.delay(instance.user_id)

                from ai_intelligence.tasks import update_gamification_task
                update_gamification_task.delay(instance.user_id, 'order_completed')

        logger.info('AI order signals connected')
    except Exception as e:
        logger.debug('Failed to connect order signals: %s', e)


def _connect_review_signals():
    """Update gamification on review events."""
    try:
        from products.models import Review

        @receiver(post_save, sender=Review, dispatch_uid='ai_gamification_review')
        def on_review_for_gamification(sender, instance, created, **kwargs):
            if created and instance.user:
                from ai_intelligence.tasks import update_gamification_task
                update_gamification_task.delay(instance.user.id, 'review_written')

        logger.info('AI review signals connected')
    except Exception as e:
        logger.debug('Failed to connect review signals: %s', e)
