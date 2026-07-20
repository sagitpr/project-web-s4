"""
Notification Intelligence Engine.
Handles quiet hours, cooldowns, adaptive frequency control,
duplicate prevention, retry queues, priority levels, timezone awareness,
spam prevention, and notification preferences.
"""

import json
import logging
from datetime import timedelta, datetime
from typing import Optional, Dict, List, Any, Tuple
from django.db.models import Count, Q
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from engagement.models import (
    NotificationQueue, NotificationCooldown, QuietHoursConfig,
    NotificationPreferenceExtension, UserBehaviorProfile,
    NotificationAnalytics, NotificationDeliveryLog, DeviceToken,
)
from engagement.services.timing_engine import get_timing_engine

logger = logging.getLogger(__name__)


class NotificationIntelligence:
    """
    Intelligent notification delivery management.
    Ensures notifications are delivered at the right time, with the right
    frequency, without spamming the user.
    """

    # Cooldown defaults (in minutes) by trigger type
    DEFAULT_COOLDOWNS = {
        'abandoned_cart': 120,      # 2 hours
        'inactivity': 86400,        # 24 hours
        'wishlist_update': 3600,    # 1 hour
        'new_product': 7200,        # 2 hours
        'low_stock': 14400,         # 4 hours
        'flash_sale': 300,          # 5 minutes
        'order_update': 300,        # 5 minutes
        'payment_event': 300,       # 5 minutes
        'delivery_tracking': 300,   # 5 minutes
        'ai_recommendation': 43200, # 12 hours
        'loyalty_reward': 86400,    # 24 hours
        'birthday': 86400,          # 24 hours (yearly anyway)
        'holiday': 86400,           # 24 hours
        'security_alert': 60,       # 1 minute
    }

    # Max notifications per day by trigger type
    MAX_PER_DAY = {
        'push': 15,
        'email': 3,
        'in_app': 30,
    }

    def can_send(self, user, trigger_type: str, channel: str = 'push',
                 priority: int = 1) -> Tuple[bool, str]:
        """
        Check if a notification can be sent to this user.
        Returns (can_send: bool, reason: str).
        """
        from notifications.models import NotificationPreference

        # 1. Check if user exists and is active
        if not user or not user.is_active:
            return False, 'User is inactive'

        # 2. Check global notification preferences
        try:
            prefs = NotificationPreference.objects.get(user=user)
            channel_map = {
                'push': 'push_system',
                'email': 'email_digest',
                'in_app': 'push_system',
            }
            if not getattr(prefs, channel_map.get(channel, 'push_system'), True):
                return False, f'{channel} notifications disabled by user'
        except NotificationPreference.DoesNotExist:
            pass  # Default to allow

        # 3. Check engagement-specific preferences
        try:
            eng_prefs = NotificationPreferenceExtension.objects.get(user=user)
            if eng_prefs.do_not_disturb:
                if eng_prefs.dnd_until and timezone.now() < eng_prefs.dnd_until:
                    return False, 'Do Not Disturb is active'
                elif eng_prefs.dnd_until and timezone.now() >= eng_prefs.dnd_until:
                    eng_prefs.do_not_disturb = False
                    eng_prefs.dnd_until = None
                    eng_prefs.save(update_fields=['do_not_disturb', 'dnd_until'])
        except NotificationPreferenceExtension.DoesNotExist:
            pass

        # 4. Check quiet hours
        quiet_config, _ = QuietHoursConfig.objects.get_or_create(user=user)
        timing_engine = get_timing_engine()
        now = timezone.now()
        profile, _ = UserBehaviorProfile.objects.get_or_create(user=user)

        if timing_engine._is_quiet_hours(now, quiet_config, profile):
            if priority < 2:  # Only non-urgent notifications are held
                return False, 'Quiet hours active'

        # 5. Check cooldown
        cooldown_pass, cooldown_reason = self._check_cooldown(user, trigger_type)
        if not cooldown_pass:
            return False, cooldown_reason

        # 6. Check daily frequency cap
        freq_pass, freq_reason = self._check_daily_frequency(user, channel)
        if not freq_pass:
            return False, freq_reason

        # 7. Check adaptive frequency
        adapt_pass, adapt_reason = self._check_adaptive_frequency(user)
        if not adapt_pass and priority < 2:
            return False, adapt_reason

        # 8. Check for duplicates
        dedup_pass, dedup_reason = self._check_duplicate(user, trigger_type)
        if not dedup_pass:
            return False, dedup_reason

        return True, 'OK'

    def enqueue_notification(
        self,
        user,
        title: str,
        body: str,
        trigger_type: str = '',
        channel: str = 'push',
        priority: int = 1,
        action_url: str = '',
        action_text: str = '',
        icon: str = '',
        image_url: str = '',
        data: Dict = None,
        psychological_trigger: str = '',
        ai_generated: bool = False,
        trigger_ref_id: str = '',
        campaign=None,
        ab_test_group: str = '',
        ab_test_variant: str = '',
        scheduled_for: datetime = None,
    ) -> Optional[NotificationQueue]:
        """
        Enqueue a notification for intelligent delivery.
        Checks all intelligence rules before enqueuing.
        
        Returns the NotificationQueue item or None if rejected.
        """
        # Check if we can send
        can_send, reason = self.can_send(user, trigger_type, channel, priority)
        if not can_send:
            status = self._map_rejection_to_status(reason)
            if status:
                logger.debug(
                    'Notification rejected for %s: %s (status: %s)',
                    user.email, reason, status
                )
                # Still create a queue item so we can track rejected notifications
                return NotificationQueue.objects.create(
                    user=user,
                    campaign=campaign,
                    title=title,
                    body=body,
                    trigger_type=trigger_type,
                    channel=channel,
                    priority=priority,
                    action_url=action_url,
                    action_text=action_text,
                    icon=icon,
                    image_url=image_url,
                    data=data or {},
                    psychological_trigger=psychological_trigger,
                    ai_generated=ai_generated,
                    trigger_ref_id=trigger_ref_id,
                    ab_test_group=ab_test_group,
                    ab_test_variant=ab_test_variant,
                    status=status,
                    status_message=reason,
                )
            return None

        # Determine optimal delivery time
        timing_engine = get_timing_engine()
        if not scheduled_for:
            scheduled_for = timing_engine.get_optimal_delivery_time(
                user, trigger_type, priority
            )

        # Create queue item
        queue_item = NotificationQueue.objects.create(
            user=user,
            campaign=campaign,
            title=title,
            body=body,
            trigger_type=trigger_type,
            channel=channel,
            priority=priority,
            action_url=action_url,
            action_text=action_text,
            icon=icon,
            image_url=image_url,
            data=data or {},
            psychological_trigger=psychological_trigger,
            ai_generated=ai_generated,
            trigger_ref_id=trigger_ref_id,
            ab_test_group=ab_test_group,
            ab_test_variant=ab_test_variant,
            scheduled_for=scheduled_for,
            status='queued',
        )

        # Update cooldown
        self._update_cooldown(user, trigger_type)

        logger.info(
            'Notification queued for %s: %s (trigger: %s, scheduled: %s)',
            user.email, title, trigger_type, scheduled_for
        )

        return queue_item

    def enqueue_ai_notification(self, user, trigger_type: str, context: Dict = None,
                                 priority: int = 1, campaign=None) -> Optional[NotificationQueue]:
        """
        Generate and enqueue an AI-powered notification.
        Combines AI generation with intelligence rules.
        """
        from engagement.services.ai_generator import get_ai_notification_generator

        # Generate AI notification
        generator = get_ai_notification_generator()
        ai_result = generator.generate(user, trigger_type, context)

        if not ai_result:
            logger.warning('AI generation failed for %s (trigger: %s)', user.email, trigger_type)
            return None

        # Extract data
        title = ai_result.get('title', '')
        body = ai_result.get('body', '')
        psychological_trigger = ai_result.get('psychological_trigger', trigger_type)

        if not title or not body:
            logger.warning('AI generated empty notification for %s', user.email)
            return None

        # Enqueue with intelligence checks
        return self.enqueue_notification(
            user=user,
            title=title,
            body=body,
            trigger_type=trigger_type,
            channel='push',
            priority=priority,
            psychological_trigger=psychological_trigger,
            ai_generated=True,
            campaign=campaign,
        )

    def process_queue(self, batch_size: int = 50) -> int:
        """
        Process the notification queue.
        Delivers notifications that are scheduled for now or past.
        Also reschedules items held for quiet hours or cooldown.
        
        Args:
            batch_size: Maximum number to process
            
        Returns:
            Number of notifications processed
        """
        from engagement.services.push_service import get_push_service

        now = timezone.now()
        processed = 0

        # 1. Get due notifications (queued + scheduled)
        due_notifications = NotificationQueue.objects.filter(
            status='queued',
            scheduled_for__lte=now,
        ).select_related('user').order_by('-priority', 'scheduled_for')[:batch_size]

        # 2. Reschedule items held for quiet hours that are now in active hours
        quiet_held = NotificationQueue.objects.filter(
            status='quiet_hours',
            scheduled_for__lte=now,
        )
        for item in quiet_held:
            item.status = 'queued'
            item.scheduled_for = now
            item.save(update_fields=['status', 'scheduled_for'])

        push_service = get_push_service()

        for item in due_notifications:
            try:
                with transaction.atomic():
                    # Mark as delivering
                    item.status = 'delivering'
                    item.save(update_fields=['status'])

                    # Send via appropriate channel
                    if item.channel == 'push':
                        success = push_service.send_push(
                            user=item.user,
                            title=item.title,
                            body=item.body,
                            action_url=item.action_url,
                            data=item.data,
                            icon=item.icon,
                        )
                    elif item.channel == 'in_app':
                        success = self._send_in_app(item)
                    else:
                        success = False

                    # Update status
                    if success:
                        item.status = 'delivered'
                        item.delivered_at = timezone.now()
                        
                        # Update delivery log
                        NotificationDeliveryLog.objects.create(
                            queue_item=item,
                            user=item.user,
                            status='delivered',
                            delivered_at=timezone.now(),
                        )
                    else:
                        item.retry_count += 1
                        if item.retry_count >= item.max_retries:
                            item.status = 'failed'
                            item.status_message = 'Max retries exceeded'
                        else:
                            item.status = 'queued'
                            item.scheduled_for = now + timedelta(
                                minutes=5 * item.retry_count
                            )
                            item.status_message = f'Retry {item.retry_count}/{item.max_retries}'

                    item.save()

            except Exception as e:
                logger.error('Failed to process queue item %s: %s', item.id, e)
                item.status = 'failed'
                item.status_message = str(e)[:200]
                item.save(update_fields=['status', 'status_message'])

            processed += 1

        return processed

    def _check_cooldown(self, user, trigger_type: str) -> Tuple[bool, str]:
        """Check if the notification type is in cooldown for this user."""
        now = timezone.now()

        try:
            cooldown = NotificationCooldown.objects.get(user=user, trigger_type=trigger_type)
            if now < cooldown.cooldown_until:
                remaining = (cooldown.cooldown_until - now).total_seconds()
                return False, f'Cooldown active for {trigger_type} ({remaining:.0f}s remaining)'
        except NotificationCooldown.DoesNotExist:
            pass

        return True, 'OK'

    def _update_cooldown(self, user, trigger_type: str):
        """Update cooldown after sending a notification."""
        cooldown_minutes = self.DEFAULT_COOLDOWNS.get(trigger_type, 60)
        now = timezone.now()

        NotificationCooldown.objects.update_or_create(
            user=user,
            trigger_type=trigger_type,
            defaults={
                'last_sent_at': now,
                'cooldown_until': now + timedelta(minutes=cooldown_minutes),
                'sent_count_today': self._get_today_count(user, trigger_type) + 1,
            }
        )

    def _get_today_count(self, user, trigger_type: str) -> int:
        """Get count of notifications sent today for this trigger type."""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return NotificationQueue.objects.filter(
            user=user,
            trigger_type=trigger_type,
            created_at__gte=today_start
        ).count()

    def _check_daily_frequency(self, user, channel: str) -> Tuple[bool, str]:
        """Check daily notification frequency cap."""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        max_per_day = self.MAX_PER_DAY.get(channel, 15)

        # Check quiet hours config for custom limits
        try:
            quiet_config = QuietHoursConfig.objects.get(user=user)
            if channel == 'push':
                max_per_day = quiet_config.max_push_per_day
        except QuietHoursConfig.DoesNotExist:
            pass

        sent_today = NotificationQueue.objects.filter(
            user=user,
            created_at__gte=today_start,
            status__in=['delivered', 'queued', 'delivering', 'scheduled']
        ).count()

        if sent_today >= max_per_day:
            return False, f'Daily frequency cap reached ({sent_today}/{max_per_day})'

        return True, 'OK'

    def _check_adaptive_frequency(self, user) -> Tuple[bool, str]:
        """
        Check adaptive frequency based on user engagement.
        Users with high engagement get more notifications.
        Users with low engagement or high fatigue get fewer.
        """
        try:
            profile = UserBehaviorProfile.objects.get(user=user)

            # High fatigue → reduce frequency
            if profile.notification_fatigue_score > 70:
                today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
                sent_today = NotificationQueue.objects.filter(
                    user=user, created_at__gte=today_start
                ).count()
                if sent_today >= 3:
                    return False, f'Fatigue score high ({profile.notification_fatigue_score:.0f}), limiting to 3/day'

            # Very low engagement → reduce frequency (don't annoy)
            if profile.engagement_score < 10 and profile.churn_risk_score > 50:
                today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
                sent_today = NotificationQueue.objects.filter(
                    user=user, created_at__gte=today_start
                ).count()
                if sent_today >= 2:
                    return False, f'Low engagement ({profile.engagement_score:.0f}), limiting to 2/day'

        except UserBehaviorProfile.DoesNotExist:
            pass

        return True, 'OK'

    def _check_duplicate(self, user, trigger_type: str) -> Tuple[bool, str]:
        """Check for duplicate notifications (same trigger type, same reference)."""
        recent_cutoff = timezone.now() - timedelta(hours=1)

        recent = NotificationQueue.objects.filter(
            user=user,
            trigger_type=trigger_type,
            created_at__gte=recent_cutoff,
            status__in=['delivered', 'queued', 'delivering', 'scheduled'],
        ).exists()

        if recent:
            return False, f'Duplicate notification for {trigger_type} within 1 hour'

        return True, 'OK'

    def _send_in_app(self, queue_item: NotificationQueue) -> bool:
        """Send in-app notification via WebSocket."""
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            group_name = f'notifications_{queue_item.user_id}'

            event = {
                'type': 'send_notification',
                'id': queue_item.id,
                'notification_type': 'engagement',
                'title': queue_item.title,
                'description': queue_item.body,
                'priority': queue_item.priority,
                'action_url': queue_item.action_url or '',
                'psychological_trigger': queue_item.psychological_trigger or '',
                'ai_generated': queue_item.ai_generated,
                'created_at': queue_item.created_at.isoformat() if queue_item.created_at else '',
            }

            async_to_sync(channel_layer.group_send)(group_name, event)
            return True
        except Exception as e:
            logger.warning('Failed to send in-app notification: %s', e)
            return False

    def _map_rejection_to_status(self, reason: str) -> str:
        """Map rejection reason to queue status."""
        reason_lower = reason.lower()
        if 'quiet' in reason_lower:
            return 'quiet_hours'
        if 'cooldown' in reason_lower:
            return 'cooldown'
        if 'frequency' in reason_lower or 'fatigue' in reason_lower or 'engagement' in reason_lower:
            return 'rate_limited'
        if 'duplicate' in reason_lower:
            return 'duplicate'
        if 'dnd' in reason_lower or 'do not disturb' in reason_lower:
            return 'quiet_hours'
        if 'disabled' in reason_lower or 'inactive' in reason_lower:
            return 'cancelled'
        if 'disturb' in reason_lower:
            return 'quiet_hours'
        return 'rate_limited'


# Singleton
_intelligence = None


def get_notification_intelligence() -> NotificationIntelligence:
    global _intelligence
    if _intelligence is None:
        _intelligence = NotificationIntelligence()
    return _intelligence
