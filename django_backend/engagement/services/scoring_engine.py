"""
Scoring Engine for Engagement & Retention.
Calculates Engagement Score, Activity Score, Retention Score,
Loyalty Score, Churn Risk Score, and Notification Fatigue Score
from real behavioral data.
"""

import logging
import math
from datetime import timedelta, datetime
from typing import Dict, Optional
from django.db.models import Count, Sum, Avg, Q, F
from django.db import transaction
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


class ScoringEngine:
    """
    Core scoring engine that computes all user engagement metrics
    from real behavioral data stored in the database.
    """

    # ── Weights for composite scores ──
    ENGAGEMENT_WEIGHTS = {
        'login_frequency': 0.15,
        'session_duration': 0.10,
        'browsing_activity': 0.10,
        'cart_activity': 0.10,
        'purchase_frequency': 0.20,
        'purchase_value': 0.10,
        'search_activity': 0.05,
        'wishlist_activity': 0.05,
        'review_activity': 0.05,
        'ai_service_usage': 0.05,
        'social_activity': 0.05,
    }

    RETENTION_WEIGHTS = {
        'days_since_last_activity': 0.30,
        'login_streak': 0.20,
        'weekly_visits': 0.20,
        'repeat_purchase_rate': 0.15,
        'session_frequency': 0.15,
    }

    LOYALTY_WEIGHTS = {
        'total_spent': 0.20,
        'order_count': 0.15,
        'loyalty_tier': 0.20,
        'points_balance': 0.10,
        'store_follows': 0.05,
        'review_count': 0.10,
        'referral_count': 0.10,
        'account_age_days': 0.10,
    }

    CHURN_WEIGHTS = {
        'inactivity_days': 0.25,
        'login_frequency_decline': 0.15,
        'purchase_frequency_decline': 0.20,
        'cart_abandon_rate': 0.10,
        'decreased_browsing': 0.10,
        'notification_open_decline': 0.10,
        'negative_sentiment': 0.10,
    }

    FATIGUE_WEIGHTS = {
        'notifications_per_day': 0.30,
        'open_rate_decline': 0.25,
        'ctr_decline': 0.20,
        'dismissal_rate': 0.15,
        'cooldown_violations': 0.10,
    }

    @staticmethod
    def sigmoid(x: float, midpoint: float = 0.0, steepness: float = 1.0) -> float:
        """Sigmoid function for smooth scoring (0-100)."""
        return 100.0 / (1.0 + math.exp(-steepness * (x - midpoint)))

    @staticmethod
    def normalize(value: float, min_val: float, max_val: float) -> float:
        """Normalize a value to 0-100 range."""
        if max_val <= min_val:
            return 50.0
        return max(0.0, min(100.0, ((value - min_val) / (max_val - min_val)) * 100.0))

    # ═══════════════════════════════════════════════════════════════
    # ENGAGEMENT SCORE
    # ═══════════════════════════════════════════════════════════════

    def compute_engagement_score(self, user) -> float:
        """
        Compute overall Engagement Score (0-100).
        Measures how actively the user interacts with the platform.
        """
        from engagement.models import UserBehaviorProfile, BehaviorEvent, ActivityLog

        profile, _ = UserBehaviorProfile.objects.get_or_create(user=user)
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        seven_days_ago = now - timedelta(days=7)
        ninety_days_ago = now - timedelta(days=90)

        # ── 1. Login Frequency (15%) ──
        recent_logins = BehaviorEvent.objects.filter(
            user=user, event_type='login',
            event_time__gte=thirty_days_ago
        ).count()
        login_score = self.normalize(recent_logins, 0, 30)

        # ── 2. Session Duration (10%) ──
        avg_session = profile.avg_session_duration_minutes
        session_score = self.normalize(avg_session, 0, 60)

        # ── 3. Browsing Activity (10%) ──
        recent_views = BehaviorEvent.objects.filter(
            user=user, event_type='product_view',
            event_time__gte=seven_days_ago
        ).count()
        browse_score = self.normalize(recent_views, 0, 50)

        # ── 4. Cart Activity (10%) ──
        cart_adds = BehaviorEvent.objects.filter(
            user=user, event_type='cart_add',
            event_time__gte=thirty_days_ago
        ).count()
        cart_score = self.normalize(cart_adds, 0, 20)

        # ── 5. Purchase Frequency (20%) ──
        from orders.models import Order
        recent_orders = Order.objects.filter(
            user=user,
            created_at__gte=thirty_days_ago,
            order_status__in=['completed', 'shipped', 'paid']
        ).count()
        purchase_score = self.normalize(recent_orders, 0, 15)

        # ── 6. Purchase Value (10%) ──
        total_spent_30d = Order.objects.filter(
            user=user,
            created_at__gte=thirty_days_ago,
            order_status__in=['completed', 'shipped', 'paid']
        ).aggregate(total=Sum('total_price'))['total'] or 0
        value_score = self.normalize(float(total_spent_30d), 0, 5000000)

        # ── 7. Search Activity (5%) ──
        searches = BehaviorEvent.objects.filter(
            user=user, event_type='search_query',
            event_time__gte=seven_days_ago
        ).count()
        search_score = self.normalize(searches, 0, 30)

        # ── 8. Wishlist Activity (5%) ──
        wishlist_adds = BehaviorEvent.objects.filter(
            user=user, event_type='wishlist_add',
            event_time__gte=thirty_days_ago
        ).count()
        wishlist_score = self.normalize(wishlist_adds, 0, 10)

        # ── 9. Review Activity (5%) ──
        reviews = BehaviorEvent.objects.filter(
            user=user, event_type='review_written',
            event_time__gte=ninety_days_ago
        ).count()
        review_score = self.normalize(reviews, 0, 10)

        # ── 10. AI Service Usage (5%) ──
        ai_events = BehaviorEvent.objects.filter(
            user=user,
            event_type__in=['ai_scan', 'ai_search', 'ai_recommendation_click'],
            event_time__gte=ninety_days_ago
        ).count()
        ai_score = self.normalize(ai_events, 0, 20)

        # ── 11. Social Activity (5%) ──
        social_events = BehaviorEvent.objects.filter(
            user=user,
            event_type__in=['store_follow', 'chat_message', 'referral_made'],
            event_time__gte=ninety_days_ago
        ).count()
        social_score = self.normalize(social_events, 0, 30)

        # ── Weighted Composite ──
        engagement_score = (
            login_score * 0.15 +
            session_score * 0.10 +
            browse_score * 0.10 +
            cart_score * 0.10 +
            purchase_score * 0.20 +
            value_score * 0.10 +
            search_score * 0.05 +
            wishlist_score * 0.05 +
            review_score * 0.05 +
            ai_score * 0.05 +
            social_score * 0.05
        )

        return round(min(100.0, max(0.0, engagement_score)), 2)

    # ═══════════════════════════════════════════════════════════════
    # ACTIVITY SCORE
    # ═══════════════════════════════════════════════════════════════

    def compute_activity_score(self, user) -> float:
        """
        Compute Activity Score (0-100).
        Measures recency, frequency, and volume of user actions.
        Higher scores = more active user.
        """
        from engagement.models import BehaviorEvent

        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        # Total events in last 30 days
        total_events = BehaviorEvent.objects.filter(
            user=user, event_time__gte=thirty_days_ago
        ).count()

        # Unique event types (breadth of engagement)
        unique_types = BehaviorEvent.objects.filter(
            user=user, event_time__gte=thirty_days_ago
        ).values('event_type').distinct().count()

        # Recency score (days since last event)
        last_event = BehaviorEvent.objects.filter(
            user=user
        ).order_by('-event_time').first()

        recency_days = 30
        if last_event:
            recency_days = max(0, (now - last_event.event_time).days)
        recency_score = self.normalize(30 - recency_days, 0, 30)

        # Volume score
        volume_score = self.normalize(total_events, 0, 200)

        # Breadth score
        breadth_score = self.normalize(unique_types, 0, 20)

        activity_score = (
            recency_score * 0.35 +
            volume_score * 0.35 +
            breadth_score * 0.30
        )

        return round(min(100.0, max(0.0, activity_score)), 2)

    # ═══════════════════════════════════════════════════════════════
    # RETENTION SCORE
    # ═══════════════════════════════════════════════════════════════

    def compute_retention_score(self, user) -> float:
        """
        Compute Retention Score (0-100).
        Measures how well the platform retains the user over time.
        """
        from engagement.models import BehaviorEvent, UserBehaviorProfile

        profile, _ = UserBehaviorProfile.objects.get_or_create(user=user)
        now = timezone.now()

        # Days since last activity
        last_active = profile.last_active_at or user.last_login or now
        days_since = max(0, (now - last_active).days)
        recency_score = self.normalize(30 - days_since, 0, 30)

        # Login streak
        streak_days = profile.login_streak_days
        streak_score = self.normalize(streak_days, 0, 30)

        # Weekly visit consistency (last 4 weeks)
        four_weeks_ago = now - timedelta(weeks=4)
        weekly_visits = []
        for week in range(4):
            week_start = now - timedelta(weeks=week + 1)
            week_end = now - timedelta(weeks=week)
            visits = BehaviorEvent.objects.filter(
                user=user, event_type='login',
                event_time__gte=week_start,
                event_time__lt=week_end
            ).count()
            weekly_visits.append(visits)

        consistency = sum(1 for v in weekly_visits if v > 0) / 4.0
        consistency_score = consistency * 100

        # Repeat purchase rate
        from orders.models import Order
        total_orders = Order.objects.filter(user=user).count()
        repeat_orders = Order.objects.filter(
            user=user
        ).values('store').annotate(count=Count('id')).filter(count__gt=1).count()
        repeat_rate = repeat_orders / max(total_orders, 1)
        repeat_score = repeat_rate * 100

        retention_score = (
            recency_score * 0.30 +
            streak_score * 0.20 +
            consistency_score * 0.20 +
            repeat_score * 0.30
        )

        return round(min(100.0, max(0.0, retention_score)), 2)

    # ═══════════════════════════════════════════════════════════════
    # LOYALTY SCORE
    # ═══════════════════════════════════════════════════════════════

    def compute_loyalty_score(self, user) -> float:
        """
        Compute Loyalty Score (0-100).
        Measures user loyalty based on spending, history, and engagement.
        """
        from engagement.models import UserBehaviorProfile
        from orders.models import Order
        from django.contrib.auth import get_user_model

        now = timezone.now()

        profile, _ = UserBehaviorProfile.objects.get_or_create(user=user)

        # Total spent
        total_spent = float(Order.objects.filter(
            user=user,
            order_status__in=['completed', 'shipped', 'paid']
        ).aggregate(total=Sum('total_price'))['total'] or 0)
        spent_score = self.normalize(total_spent, 0, 10000000)

        # Order count
        order_count = Order.objects.filter(
            user=user,
            order_status__in=['completed', 'shipped', 'paid']
        ).count()
        order_score = self.normalize(order_count, 0, 50)

        # Account age
        account_age_days = max(1, (now - user.date_joined).days)
        age_score = self.normalize(account_age_days, 0, 730)

        # Store follows
        follows = profile.total_stores_followed
        follow_score = self.normalize(follows, 0, 20)

        # Reviews written
        review_count = profile.total_reviews
        review_score = self.normalize(review_count, 0, 20)

        # Referrals
        referrals = profile.total_referrals
        referral_score = self.normalize(referrals, 0, 10)

        # Loyalty tier value
        tier_values = {'bronze': 10, 'silver': 30, 'gold': 50, 'platinum': 70, 'diamond': 90}
        tier_score = tier_values.get(profile.loyalty_tier, 10)

        # Points balance
        points = profile.total_loyalty_points
        points_score = self.normalize(points, 0, 10000)

        loyalty_score = (
            spent_score * 0.20 +
            order_score * 0.15 +
            age_score * 0.10 +
            follow_score * 0.05 +
            review_score * 0.10 +
            referral_score * 0.10 +
            tier_score * 0.20 +
            points_score * 0.10
        )

        return round(min(100.0, max(0.0, loyalty_score)), 2)

    # ═══════════════════════════════════════════════════════════════
    # CHURN RISK SCORE
    # ═══════════════════════════════════════════════════════════════

    def compute_churn_risk_score(self, user) -> float:
        """
        Compute Churn Risk Score (0-100).
        Higher score = higher risk of churning.
        """
        from engagement.models import BehaviorEvent, UserBehaviorProfile
        from orders.models import Order

        profile, _ = UserBehaviorProfile.objects.get_or_create(user=user)
        now = timezone.now()
        sixty_days_ago = now - timedelta(days=60)

        # ── Inactivity days (25%) ──
        last_active = profile.last_active_at or user.last_login or user.date_joined
        inactivity_days = max(0, (now - last_active).days)
        inactivity_score = self.normalize(inactivity_days, 0, 60)

        # ── Login frequency decline (15%) ──
        logins_30d_ago = BehaviorEvent.objects.filter(
            user=user, event_type='login',
            event_time__gte=sixty_days_ago,
            event_time__lt=now - timedelta(days=30)
        ).count()
        logins_recent = BehaviorEvent.objects.filter(
            user=user, event_type='login',
            event_time__gte=now - timedelta(days=30)
        ).count()
        login_decline = max(0, logins_30d_ago - logins_recent)
        login_decline_score = self.normalize(login_decline, 0, 20)

        # ── Purchase frequency decline (20%) ──
        orders_60d = Order.objects.filter(
            user=user,
            created_at__gte=sixty_days_ago,
            created_at__lt=now - timedelta(days=30)
        ).count()
        orders_30d = Order.objects.filter(
            user=user,
            created_at__gte=now - timedelta(days=30)
        ).count()
        purchase_decline = max(0, orders_60d - orders_30d)
        purchase_decline_score = self.normalize(purchase_decline, 0, 10)

        # ── Cart abandon rate (10%) ──
        abandon_rate = profile.cart_abandon_rate
        abandon_score = abandon_rate * 100

        # ── Decreased browsing (10%) ──
        views_60d = BehaviorEvent.objects.filter(
            user=user, event_type='product_view',
            event_time__gte=sixty_days_ago,
            event_time__lt=now - timedelta(days=30)
        ).count()
        views_30d = BehaviorEvent.objects.filter(
            user=user, event_type='product_view',
            event_time__gte=now - timedelta(days=30)
        ).count()
        browse_decline = max(0, views_60d - views_30d)
        browse_decline_score = self.normalize(browse_decline, 0, 30)

        # ── Notification open rate decline (10%) ──
        notif_open_rate = profile.notification_open_rate
        notif_decline_score = (1.0 - notif_open_rate) * 100

        # ── Overall churn score ──
        churn_score = (
            inactivity_score * 0.25 +
            login_decline_score * 0.15 +
            purchase_decline_score * 0.20 +
            abandon_score * 0.10 +
            browse_decline_score * 0.10 +
            notif_decline_score * 0.10 +
            # Negative sentiment / refunds
            self._compute_negative_signal_score(user) * 0.10
        )

        return round(min(100.0, max(0.0, churn_score)), 2)

    def _compute_negative_signal_score(self, user) -> float:
        """Compute negative signal score from refunds, cancellations, and complaints."""
        from orders.models import Order
        from refunds.models import Refund

        now = timezone.now()
        ninety_days_ago = now - timedelta(days=90)

        total_orders = max(1, Order.objects.filter(
            user=user,
            created_at__gte=ninety_days_ago
        ).count())

        cancellations = Order.objects.filter(
            user=user,
            order_status='cancelled',
            created_at__gte=ninety_days_ago
        ).count()

        refunds = 0
        try:
            refunds = Refund.objects.filter(
                user=user,
                created_at__gte=ninety_days_ago
            ).count()
        except Exception:
            pass

        negative_ratio = (cancellations + refunds) / total_orders
        return min(100.0, negative_ratio * 100)

    # ═══════════════════════════════════════════════════════════════
    # NOTIFICATION FATIGUE SCORE
    # ═══════════════════════════════════════════════════════════════

    def compute_notification_fatigue_score(self, user) -> float:
        """
        Compute Notification Fatigue Score (0-100).
        Higher score = user is overwhelmed by notifications.
        """
        from engagement.models import NotificationQueue, NotificationAnalytics

        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)

        # Notifications sent per day (last 7 days)
        recent_notifs = NotificationQueue.objects.filter(
            user=user,
            created_at__gte=seven_days_ago
        ).count()
        daily_avg = recent_notifs / 7.0
        volume_score = self.normalize(daily_avg, 0, 10)

        # Open rate decline (compare current vs historical)
        # Get recent analytics
        recent_analytics = NotificationAnalytics.objects.filter(
            user=user,
            period='weekly',
            period_start__gte=now - timedelta(days=30)
        ).order_by('-period_start')[:4]

        if recent_analytics.count() >= 2:
            current_open = recent_analytics[0].open_rate
            prev_open = recent_analytics[-1].open_rate
            open_decline = max(0, prev_open - current_open)
            open_decline_score = open_decline * 100
        else:
            open_decline_score = 0.0

        # CTR decline
        if recent_analytics.count() >= 2:
            current_ctr = recent_analytics[0].click_through_rate
            prev_ctr = recent_analytics[-1].click_through_rate
            ctr_decline = max(0, prev_ctr - current_ctr)
            ctr_decline_score = ctr_decline * 100
        else:
            ctr_decline_score = 0.0

        # Dismissal rate
        total_delivered = sum(a.total_delivered for a in recent_analytics)
        total_dismissed = sum(a.total_dismissed for a in recent_analytics)
        dismissal_rate = total_dismissed / max(total_delivered, 1)
        dismissal_score = dismissal_rate * 100

        fatigue_score = (
            volume_score * 0.30 +
            open_decline_score * 0.25 +
            ctr_decline_score * 0.20 +
            dismissal_score * 0.25
        )

        return round(min(100.0, max(0.0, fatigue_score)), 2)

    # ═══════════════════════════════════════════════════════════════
    # COMPOSITE PROFILE UPDATE
    # ═══════════════════════════════════════════════════════════════

    @transaction.atomic
    def update_full_profile(self, user) -> Dict:
        """
        Compute all scores and update the user's behavior profile.
        Also updates ChurnPrediction and risk level.
        Returns dict of all computed scores.
        """
        from engagement.models import UserBehaviorProfile, ChurnPrediction

        scores = {
            'engagement_score': self.compute_engagement_score(user),
            'activity_score': self.compute_activity_score(user),
            'retention_score': self.compute_retention_score(user),
            'loyalty_score': self.compute_loyalty_score(user),
            'churn_risk_score': self.compute_churn_risk_score(user),
            'notification_fatigue_score': self.compute_notification_fatigue_score(user),
        }

        profile, created = UserBehaviorProfile.objects.get_or_create(user=user)

        # Update scores
        for key, value in scores.items():
            setattr(profile, key, value)

        # Determine risk level
        risk_level = self._determine_risk_level(scores['churn_risk_score'], scores['engagement_score'])
        if risk_level != profile.risk_level:
            profile.risk_level = risk_level
            profile.risk_level_changed_at = timezone.now()

        profile.computed_at = timezone.now()
        profile.profile_version += 1
        profile.save()

        # Update churn prediction
        self._update_churn_prediction(user, scores)

        logger.info(
            'Updated profile for %s: engagement=%.1f, activity=%.1f, retention=%.1f, '
            'loyalty=%.1f, churn=%.1f, fatigue=%.1f, risk=%s',
            user.email,
            scores['engagement_score'],
            scores['activity_score'],
            scores['retention_score'],
            scores['loyalty_score'],
            scores['churn_risk_score'],
            scores['notification_fatigue_score'],
            risk_level
        )

        return scores

    def _determine_risk_level(self, churn_score: float, engagement_score: float) -> str:
        """Determine risk level from churn and engagement scores."""
        if engagement_score >= 50 and churn_score < 20:
            return 'active'
        elif churn_score >= 70 or (engagement_score < 20 and churn_score >= 50):
            return 'churned'
        elif churn_score >= 50 or (engagement_score < 30):
            return 'at_risk'
        elif churn_score >= 30 or engagement_score < 40:
            return 'dormant'
        else:
            return 'active'

    def _update_churn_prediction(self, user, scores: Dict):
        """Update or create churn prediction record."""
        from engagement.models import ChurnPrediction

        churn_prob = scores['churn_risk_score'] / 100.0

        if churn_prob < 0.1:
            category = 'very_low'
        elif churn_prob < 0.25:
            category = 'low'
        elif churn_prob < 0.50:
            category = 'moderate'
        elif churn_prob < 0.75:
            category = 'high'
        else:
            category = 'very_high'

        # Determine recommended action
        if churn_prob >= 0.50:
            action = 'discount_offer'
        elif churn_prob >= 0.30:
            action = 're_engagement_push'
        elif scores['engagement_score'] < 30:
            action = 'personalized_recommendation'
        elif scores['loyalty_score'] < 30:
            action = 'loyalty_boost'
        else:
            action = 'no_action'

        ChurnPrediction.objects.update_or_create(
            user=user,
            defaults={
                'churn_probability': round(churn_prob, 4),
                'churn_risk_category': category,
                'top_factors': self._get_top_churn_factors(user),
                'confidence_score': 0.75,
                'features_used': 12,
                'recommended_action': action,
                'computed_at': timezone.now(),
            }
        )

    def _get_top_churn_factors(self, user) -> list:
        """Get top factors contributing to churn risk."""
        from engagement.models import BehaviorEvent, UserBehaviorProfile
        from orders.models import Order

        factors = []
        profile, _ = UserBehaviorProfile.objects.get_or_create(user=user)
        now = timezone.now()

        # Check inactivity
        last_active = profile.last_active_at or user.last_login or user.date_joined
        inactivity_days = max(0, (now - last_active).days)
        if inactivity_days > 7:
            factors.append({
                'factor': 'inactivity',
                'weight': round(min(inactivity_days / 60.0, 1.0), 2),
                'detail': f'{inactivity_days} days since last activity'
            })

        # Check purchase decline
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)
        recent_orders = Order.objects.filter(
            user=user, created_at__gte=thirty_days_ago
        ).count()
        prev_orders = Order.objects.filter(
            user=user,
            created_at__gte=sixty_days_ago,
            created_at__lt=thirty_days_ago
        ).count()
        if recent_orders < prev_orders:
            factors.append({
                'factor': 'purchase_decline',
                'weight': 0.8,
                'detail': f'Orders declined from {prev_orders} to {recent_orders}'
            })

        # Check browsing decline
        recent_views = BehaviorEvent.objects.filter(
            user=user, event_type='product_view',
            event_time__gte=thirty_days_ago
        ).count()
        prev_views = BehaviorEvent.objects.filter(
            user=user, event_type='product_view',
            event_time__gte=sixty_days_ago,
            event_time__lt=thirty_days_ago
        ).count()
        if recent_views < prev_views:
            factors.append({
                'factor': 'browsing_decline',
                'weight': 0.6,
                'detail': f'Product views declined from {prev_views} to {recent_views}'
            })

        # Check cart abandonment
        if profile.cart_abandon_rate > 0.5:
            factors.append({
                'factor': 'high_cart_abandonment',
                'weight': round(profile.cart_abandon_rate, 2),
                'detail': f'Cart abandon rate: {profile.cart_abandon_rate:.0%}'
            })

        return factors


# Singleton
_scoring_engine = None


def get_scoring_engine() -> ScoringEngine:
    global _scoring_engine
    if _scoring_engine is None:
        _scoring_engine = ScoringEngine()
    return _scoring_engine
