"""
Celery tasks for Engagement & Retention Engine.
Handles async scoring, notification generation, delivery, analytics, and cleanup.
"""

import json
import logging
from datetime import timedelta
from typing import Optional, Dict, List

from celery import shared_task
from django.db.models import Count, Sum, Q
from django.db import connection
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# USER PROFILE & SCORING TASKS
# ═══════════════════════════════════════════════════════════════

@shared_task(bind=True, max_retries=3, default_retry_delay=10, autoretry_for=(Exception,))
def update_user_profile_task(self, user_id: int):
    """
    Update a single user's behavior profile and scores.
    Dispatched after relevant user events.
    """
    from django.contrib.auth import get_user_model
    from engagement.services.scoring_engine import get_scoring_engine
    from engagement.models import UserBehaviorProfile, BehaviorEvent

    User = get_user_model()
    connection.close_if_unusable_or_obsolete()

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.warning('User %s not found for profile update', user_id)
        return {'error': 'User not found', 'user_id': user_id}

    try:
        # Compute all scores
        engine = get_scoring_engine()
        scores = engine.update_full_profile(user)

        # Update real-time profile stats
        profile, _ = UserBehaviorProfile.objects.get_or_create(user=user)
        now = timezone.now()

        # Update login streak
        recent_login = BehaviorEvent.objects.filter(
            user=user, event_type='login'
        ).order_by('-event_time').first()

        if recent_login:
            profile.last_login_at = recent_login.event_time
            days_since = (now - recent_login.event_time).days
            profile.inactivity_days = max(0, days_since)
            if days_since <= 1:
                profile.login_streak_days += 1
                if profile.login_streak_days > profile.longest_streak_days:
                    profile.longest_streak_days = profile.login_streak_days
            elif days_since > 1:
                profile.login_streak_days = 0
                profile.last_streak_broken_at = now

        # Update last active
        profile.last_active_at = now

        # Update total logins count
        profile.total_logins = BehaviorEvent.objects.filter(
            user=user, event_type='login'
        ).count()

        profile.save()

        logger.info('Profile updated for user %s: scores=%s', user.email, scores)
        return {
            'user_id': user_id,
            'scores': scores,
            'risk_level': profile.risk_level,
        }

    except Exception as exc:
        logger.exception('Profile update failed for user %s', user_id)
        try:
            self.retry(exc=exc)
        except Exception:
            return {'error': str(exc), 'user_id': user_id}


@shared_task(max_retries=2, default_retry_delay=60, autoretry_for=(Exception,))
def batch_update_profiles_task(batch_size: int = 100):
    """
    Batch update user profiles.
    Processes users who haven't had their profile updated recently.
    """
    from engagement.models import UserBehaviorProfile

    cutoff = timezone.now() - timedelta(hours=6)
    outdated = UserBehaviorProfile.objects.filter(
        computed_at__lt=cutoff
    ).select_related('user')[:batch_size]

    count = 0
    for profile in outdated:
        try:
            update_user_profile_task.delay(profile.user_id)
            count += 1
        except Exception as e:
            logger.warning('Failed to dispatch profile update for user %s: %s', profile.user_id, e)

    logger.info('Dispatched %d profile updates', count)
    return {'dispatched': count}


# ═══════════════════════════════════════════════════════════════
# NOTIFICATION GENERATION TASKS
# ═══════════════════════════════════════════════════════════════

@shared_task(bind=True, max_retries=2, default_retry_delay=30, autoretry_for=(Exception,))
def generate_engagement_notification_task(self, user_id: int, trigger_type: str,
                                           context: dict = None):
    """
    Generate and enqueue an AI-powered engagement notification.
    Uses Gemini AI for personalized content.
    """
    from django.contrib.auth import get_user_model
    from engagement.services.notification_intelligence import get_notification_intelligence

    User = get_user_model()
    connection.close_if_unusable_or_obsolete()

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {'error': 'User not found'}

    try:
        intelligence = get_notification_intelligence()
        queue_item = intelligence.enqueue_ai_notification(
            user=user,
            trigger_type=trigger_type,
            context=context or {},
            priority=1,
        )

        if queue_item:
            logger.info(
                'Engagement notification generated for %s: %s (trigger: %s, status: %s)',
                user.email, queue_item.title, trigger_type, queue_item.status
            )
            return {
                'user_id': user_id,
                'queue_id': queue_item.id,
                'status': queue_item.status,
                'title': queue_item.title,
            }
        else:
            logger.info('Engagement notification not generated for %s (trigger: %s)',
                        user.email, trigger_type)
            return {'user_id': user_id, 'status': 'skipped'}

    except Exception as exc:
        logger.exception('Failed to generate engagement notification for %s', user_id)
        try:
            self.retry(exc=exc)
        except Exception:
            return {'error': str(exc), 'user_id': user_id}


@shared_task(max_retries=2, default_retry_delay=30, autoretry_for=(Exception,))
def generate_abandoned_cart_notification_task(user_id: int):
    """
    Generate abandoned cart reminder for users with items in cart.
    Checks if cart is still abandoned before generating.
    """
    from django.contrib.auth import get_user_model
    from orders.models import Cart
    from engagement.services.notification_intelligence import get_notification_intelligence

    User = get_user_model()
    connection.close_if_unusable_or_obsolete()

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {'error': 'User not found'}

    # Check if user still has items in cart
    cart_items = Cart.objects.filter(user=user).select_related('product')
    if not cart_items.exists():
        return {'status': 'cart_empty', 'user_id': user_id}

    # Check if abandoned (no order created from cart)
    from orders.models import Order
    has_recent_order = Order.objects.filter(
        user=user,
        created_at__gte=timezone.now() - timedelta(hours=1)
    ).exists()
    if has_recent_order:
        return {'status': 'order_completed', 'user_id': user_id}

    # Build context
    context = {
        'cart_items': [
            {
                'product_id': item.product_id,
                'product_name': item.product.product_name if item.product else 'Produk',
                'qty': item.qty,
                'price': float(item.product.price) if item.product else 0,
            }
            for item in cart_items
        ],
        'total_value': sum(
            float(item.product.price) * item.qty
            for item in cart_items if item.product
        ),
        'item_count': cart_items.count(),
    }

    # Generate notification
    intelligence = get_notification_intelligence()
    queue_item = intelligence.enqueue_ai_notification(
        user=user,
        trigger_type='abandoned_cart',
        context=context,
        priority=2,
    )

    if queue_item:
        logger.info('Abandoned cart notification for %s: %s', user.email, queue_item.title)
        return {'user_id': user_id, 'queue_id': queue_item.id, 'status': queue_item.status}

    return {'user_id': user_id, 'status': 'skipped'}


@shared_task(max_retries=2, default_retry_delay=30, autoretry_for=(Exception,))
def check_abandoned_cart_task(user_id: int):
    """
    Check if user has abandoned cart and trigger notification after delay.
    Called when cart becomes empty (all items removed).
    """
    # Schedule the actual abandoned cart check after a delay
    # This gives the user time to complete checkout
    generate_abandoned_cart_notification_task.apply_async(
        args=[user_id],
        countdown=1800,  # 30 minutes delay
    )


# ═══════════════════════════════════════════════════════════════
# NOTIFICATION DELIVERY TASKS
# ═══════════════════════════════════════════════════════════════

@shared_task(max_retries=3, default_retry_delay=15, autoretry_for=(Exception,))
def process_notification_queue_task(batch_size: int = 50):
    """
    Process the notification queue for due notifications.
    Runs frequently to deliver scheduled notifications on time.
    """
    from engagement.services.notification_intelligence import get_notification_intelligence

    intelligence = get_notification_intelligence()
    processed = intelligence.process_queue(batch_size=batch_size)

    if processed > 0:
        logger.info('Processed %d notifications from queue', processed)

    return {'processed': processed}


# ═══════════════════════════════════════════════════════════════
# ANALYTICS & AGGREGATION TASKS
# ═══════════════════════════════════════════════════════════════

@shared_task(max_retries=2, default_retry_delay=120, autoretry_for=(Exception,))
def aggregate_notification_analytics_task():
    """
    Aggregate notification analytics for all active users.
    Runs daily to compute delivery rates, open rates, etc.
    """
    from engagement.models import NotificationQueue, NotificationAnalytics, UserBehaviorProfile

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    # Get all users with recent activity
    active_users = UserBehaviorProfile.objects.filter(
        last_active_at__gte=month_start
    ).values_list('user_id', flat=True)

    for user_id in active_users:
        try:
            _aggregate_single_user(user_id, 'daily', yesterday_start, today_start)
            _aggregate_single_user(user_id, 'weekly', week_start, today_start)
            _aggregate_single_user(user_id, 'monthly', month_start, today_start)
        except Exception as e:
            logger.warning('Analytics aggregation failed for user %s: %s', user_id, e)

    logger.info('Notification analytics aggregated for %d users', len(active_users))
    return {'users_processed': len(active_users)}


def _aggregate_single_user(user_id: int, period: str, period_start, period_end):
    """Aggregate analytics for a single user for a specific period."""
    from engagement.models import NotificationQueue, NotificationAnalytics

    notifications = NotificationQueue.objects.filter(
        user_id=user_id,
        created_at__gte=period_start,
        created_at__lt=period_end,
    )

    total_queued = notifications.count()
    total_sent = notifications.filter(
        status__in=['delivered', 'delivering']
    ).count()
    total_delivered = notifications.filter(status='delivered').count()
    total_failed = notifications.filter(status='failed').count()
    total_opened = notifications.filter(opened_at__isnull=False).count()
    total_clicked = notifications.filter(clicked_at__isnull=False).count()
    total_dismissed = notifications.exclude(
        opened_at__isnull=True, clicked_at__isnull=True
    ).count()

    # Ratios
    delivery_rate = total_delivered / max(total_sent, 1)
    open_rate = total_opened / max(total_delivered, 1)
    ctr = total_clicked / max(total_delivered, 1)

    # By trigger type
    by_trigger = {}
    for item in notifications.values('trigger_type').annotate(
        count=Count('id'),
        opened=Count('id', filter=Q(opened_at__isnull=False)),
    ):
        by_trigger[item['trigger_type']] = {
            'count': item['count'],
            'opened': item['opened'],
        }

    # By psychological trigger
    by_psych = {}
    for item in notifications.values('psychological_trigger').annotate(
        count=Count('id'),
        opened=Count('id', filter=Q(opened_at__isnull=False)),
    ):
        if item['psychological_trigger']:
            by_psych[item['psychological_trigger']] = {
                'count': item['count'],
                'opened': item['opened'],
            }

    # By hour (24-element array)
    by_hour = [0] * 24
    for item in notifications.filter(delivered_at__isnull=False):
        hour = item.delivered_at.hour
        if 0 <= hour <= 23:
            by_hour[hour] += 1

    NotificationAnalytics.objects.update_or_create(
        user_id=user_id,
        period=period,
        period_start=period_start,
        defaults={
            'period_end': period_end,
            'total_queued': total_queued,
            'total_sent': total_sent,
            'total_delivered': total_delivered,
            'total_failed': total_failed,
            'total_opened': total_opened,
            'total_clicked': total_clicked,
            'total_dismissed': total_dismissed,
            'delivery_rate': round(delivery_rate, 4),
            'open_rate': round(open_rate, 4),
            'click_through_rate': round(ctr, 4),
            'by_trigger': by_trigger,
            'by_psychological_trigger': by_psych,
            'by_hour': by_hour,
        }
    )


@shared_task(max_retries=2, default_retry_delay=60, autoretry_for=(Exception,))
def update_optimal_notification_hours_task():
    """
    Compute optimal notification hours for each user based on
    their historical open rates by hour.
    """
    from engagement.models import NotificationAnalytics, UserBehaviorProfile

    # Find users with enough analytics data
    users_with_data = NotificationAnalytics.objects.filter(
        period='weekly',
        total_delivered__gte=5,
    ).values_list('user_id', flat=True).distinct()

    for user_id in users_with_data:
        try:
            analytics = NotificationAnalytics.objects.filter(
                user_id=user_id,
                period='weekly',
            ).order_by('-period_start').first()

            if analytics and analytics.by_hour:
                by_hour = analytics.by_hour
                if isinstance(by_hour, list) and len(by_hour) >= 24:
                    # Find the hour with most deliveries
                    best_hour = max(
                        range(24),
                        key=lambda h: by_hour[h] if isinstance(by_hour[h], (int, float)) else 0
                    )

                    # Find optimal hours (hours with activity)
                    active_hours = [
                        h for h in range(24)
                        if isinstance(by_hour[h], (int, float)) and by_hour[h] > 0
                    ]
                    if active_hours:
                        UserBehaviorProfile.objects.filter(user_id=user_id).update(
                            optimal_notification_hour=best_hour,
                            peak_activity_hour=best_hour,
                            preferred_hour_start=min(active_hours),
                            preferred_hour_end=max(active_hours),
                        )
        except Exception as e:
            logger.warning('Failed to update optimal hours for user %s: %s', user_id, e)


# ═══════════════════════════════════════════════════════════════
# RE-ENGAGEMENT & CHURN PREVENTION TASKS
# ═══════════════════════════════════════════════════════════════

@shared_task(max_retries=2, default_retry_delay=60, autoretry_for=(Exception,))
def scan_at_risk_users_task(max_users: int = 50):
    """
    Scan for users at risk of churning and trigger re-engagement.
    Uses churn prediction scores to prioritize.
    """
    from engagement.models import UserBehaviorProfile, ChurnPrediction
    from engagement.services.scoring_engine import get_scoring_engine

    # Find users at risk who haven't been engaged recently
    now = timezone.now()
    cutoff = now - timedelta(days=3)

    # Get users with high churn risk and no recent re-engagement
    at_risk = UserBehaviorProfile.objects.filter(
        is_at_risk=True,
        risk_level__in=['at_risk', 'dormant'],
    ).select_related('user').order_by('-churn_risk_score')[:max_users]

    engaged_count = 0
    for profile in at_risk:
        try:
            # Check if we've already sent a re-engagement notification recently
            from engagement.models import NotificationQueue
            recent_reengagement = NotificationQueue.objects.filter(
                user=profile.user,
                trigger_type__in=['inactivity', 'fomo', 'loss_aversion'],
                created_at__gte=now - timedelta(days=7),
            ).exists()

            if not recent_reengagement:
                # Trigger re-engagement notification
                generate_engagement_notification_task.delay(
                    profile.user_id,
                    'inactivity',
                    {
                        'days_inactive': profile.inactivity_days,
                        'engagement_score': profile.engagement_score,
                    }
                )
                engaged_count += 1

        except Exception as e:
            logger.warning('Failed to re-engage user %s: %s', profile.user_id, e)

    logger.info('Re-engagement triggered for %d at-risk users', engaged_count)
    return {'engaged': engaged_count}


@shared_task(max_retries=2, default_retry_delay=60, autoretry_for=(Exception,))
def detect_inactive_users_task(min_inactive_days: int = 7):
    """
    Detect users who have been inactive for too long and mark them.
    """
    from engagement.models import UserBehaviorProfile

    now = timezone.now()
    cutoff = now - timedelta(days=min_inactive_days)

    inactive = UserBehaviorProfile.objects.filter(
        last_active_at__lt=cutoff,
        risk_level='active',
    ).select_related('user')

    count = 0
    for profile in inactive:
        # Compute churn score to determine risk level
        from engagement.services.scoring_engine import get_scoring_engine
        engine = get_scoring_engine()
        churn_score = engine.compute_churn_risk_score(profile.user)

        profile.churn_risk_score = churn_score
        profile.is_at_risk = churn_score >= 30
        profile.risk_level = engine._determine_risk_level(churn_score, profile.engagement_score)
        profile.risk_level_changed_at = now
        profile.save()

        count += 1

    logger.info('Checked %d inactive users, updated risk levels', count)
    return {'checked': count}


# ═══════════════════════════════════════════════════════════════
# NOTIFICATION CAMPAIGN TASKS
# ═══════════════════════════════════════════════════════════════

@shared_task(max_retries=3, default_retry_delay=30, autoretry_for=(Exception,))
def execute_campaign_task(campaign_id: int):
    """
    Execute a notification campaign.
    Sends targeted notifications to the campaign's target users.
    """
    from engagement.models import NotificationCampaign, NotificationQueue
    from engagement.services.notification_intelligence import get_notification_intelligence

    connection.close_if_unusable_or_obsolete()

    try:
        campaign = NotificationCampaign.objects.get(id=campaign_id)
    except NotificationCampaign.DoesNotExist:
        logger.warning('Campaign %s not found', campaign_id)
        return {'error': 'Campaign not found'}

    if campaign.status != 'scheduled':
        logger.warning('Campaign %s is not scheduled (status: %s)', campaign_id, campaign.status)
        return {'error': f'Campaign status is {campaign.status}, not scheduled'}

    # Mark as running
    campaign.status = 'running'
    campaign.started_at = timezone.now()
    campaign.save(update_fields=['status', 'started_at'])

    # Get target users
    target_users = _get_campaign_target_users(campaign)
    campaign.target_count = len(target_users)

    # Send notifications
    intelligence = get_notification_intelligence()
    sent_count = 0

    for user in target_users:
        try:
            if campaign.template and campaign.use_ai_personalization:
                # Use AI to generate personalized notification
                queue_item = intelligence.enqueue_ai_notification(
                    user=user,
                    trigger_type=campaign.template.trigger_type,
                    context={'campaign_id': campaign.id, 'campaign_name': campaign.name},
                    priority=1,
                    campaign=campaign,
                )
            elif campaign.template:
                # Use template directly
                queue_item = intelligence.enqueue_notification(
                    user=user,
                    title=campaign.template.title_template,
                    body=campaign.template.body_template,
                    trigger_type=campaign.template.trigger_type,
                    channel=campaign.channel,
                    campaign=campaign,
                )
            else:
                continue

            if queue_item and queue_item.status in ('queued', 'delivered'):
                sent_count += 1

        except Exception as e:
            logger.warning('Campaign send failed for user %s: %s', user.id, e)

    # Update campaign stats
    campaign.total_sent = sent_count
    campaign.status = 'completed'
    campaign.completed_at = timezone.now()
    campaign.save()

    logger.info('Campaign %s executed: %d/%d sent', campaign.name, sent_count, campaign.target_count)
    return {
        'campaign_id': campaign_id,
        'target_count': campaign.target_count,
        'sent_count': sent_count,
    }


def _get_campaign_target_users(campaign):
    """Get target users for a campaign based on target_type and filter."""
    from django.contrib.auth import get_user_model
    from engagement.models import UserBehaviorProfile

    User = get_user_model()

    if campaign.target_type == 'all_users':
        return User.objects.filter(is_active=True)[:10000]
    elif campaign.target_type == 'buyers':
        return User.objects.filter(is_active=True, role='buyer')[:10000]
    elif campaign.target_type == 'sellers':
        return User.objects.filter(is_active=True, role='seller')[:5000]
    elif campaign.target_type == 'risk_segment':
        risk_levels = campaign.target_filter.get('risk_levels', ['at_risk', 'dormant'])
        user_ids = UserBehaviorProfile.objects.filter(
            risk_level__in=risk_levels
        ).values_list('user_id', flat=True)[:5000]
        return User.objects.filter(id__in=user_ids, is_active=True)
    elif campaign.target_type == 'inactive_users':
        min_days = campaign.target_filter.get('min_inactive_days', 7)
        cutoff = timezone.now() - timedelta(days=min_days)
        user_ids = UserBehaviorProfile.objects.filter(
            last_active_at__lt=cutoff
        ).values_list('user_id', flat=True)[:5000]
        return User.objects.filter(id__in=user_ids, is_active=True)
    elif campaign.target_type == 'tier_segment':
        tiers = campaign.target_filter.get('tiers', ['silver', 'gold', 'platinum'])
        user_ids = UserBehaviorProfile.objects.filter(
            loyalty_tier__in=tiers
        ).values_list('user_id', flat=True)[:5000]
        return User.objects.filter(id__in=user_ids, is_active=True)
    else:
        # custom_segment - use filter as JSON query
        return User.objects.filter(is_active=True)[:1000]


@shared_task(max_retries=2, default_retry_delay=30, autoretry_for=(Exception,))
def schedule_campaigns_task():
    """
    Check for campaigns that need to be started.
    Runs every minute.
    """
    from engagement.models import NotificationCampaign

    now = timezone.now()
    due_campaigns = NotificationCampaign.objects.filter(
        status='scheduled',
        scheduled_at__lte=now,
    )

    count = 0
    for campaign in due_campaigns:
        execute_campaign_task.delay(campaign.id)
        count += 1

    if count > 0:
        logger.info('Scheduled %d campaigns for execution', count)

    return {'scheduled': count}


# ═══════════════════════════════════════════════════════════════
# CLEANUP & MAINTENANCE TASKS
# ═══════════════════════════════════════════════════════════════

@shared_task(max_retries=2, default_retry_delay=60, autoretry_for=(Exception,))
def clean_expired_queue_items_task():
    """
    Clean up expired and old notification queue items.
    """
    from engagement.models import NotificationQueue

    now = timezone.now()
    cutoff = now - timedelta(days=30)

    # Expire old queued items that were never delivered
    expired = NotificationQueue.objects.filter(
        created_at__lt=cutoff,
        status__in=['queued', 'scheduled', 'quiet_hours', 'cooldown', 'rate_limited'],
    ).update(status='expired', status_message='Expired after 30 days')

    # Delete old delivered items (older than 90 days)
    old_cutoff = now - timedelta(days=90)
    deleted, _ = NotificationQueue.objects.filter(
        created_at__lt=old_cutoff,
        status__in=['delivered', 'failed', 'expired', 'cancelled'],
    ).delete()

    logger.info('Cleaned %d expired and %d old queue items', expired, deleted)
    return {'expired': expired, 'deleted': deleted}


@shared_task(max_retries=1, default_retry_delay=120, autoretry_for=(Exception,))
def clean_old_behavior_events_task():
    """
    Clean up old behavior events (older than 90 days).
    Keeps only essential events for long-term analysis.
    """
    from engagement.models import BehaviorEvent

    cutoff = timezone.now() - timedelta(days=90)
    deleted, _ = BehaviorEvent.objects.filter(
        event_time__lt=cutoff
    ).delete()

    logger.info('Cleaned %d old behavior events', deleted)
    return {'deleted': deleted}
