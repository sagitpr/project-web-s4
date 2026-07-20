"""
AI Digital Twin Engine.
Builds continuously updated predictive models of every user.
Computes CLV, growth score, interest score, trust score, sentiment.
"""

import logging
from datetime import timedelta
from decimal import Decimal
from typing import Dict, Optional
from django.db import transaction
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone

logger = logging.getLogger(__name__)


class DigitalTwinEngine:
    """
    Builds and maintains AI Digital Twins for all users.
    Each twin is a predictive model that learns from real behavior.
    """

    def update_digital_twin(self, user) -> Dict:
        """Full update of a user's digital twin."""
        from ai_intelligence.models import DigitalTwin
        from engagement.models import UserBehaviorProfile

        twin, _ = DigitalTwin.objects.get_or_create(user=user)
        profile, _ = UserBehaviorProfile.objects.get_or_create(user=user)

        scores = {
            'customer_lifetime_value': self._compute_clv(user, profile),
            'growth_score': self._compute_growth_score(user, profile),
            'buyer_interest_score': self._compute_interest_score(user, profile),
            'trust_score': self._compute_trust_score(user, profile),
            'reputation_score': self._compute_reputation_score(user, profile),
            'seller_performance_score': self._compute_seller_performance(user),
            'store_health_score': self._compute_store_health(user),
            'inventory_health_score': self._compute_inventory_health(user),
            'product_opportunity_score': self._compute_product_opportunity(user),
            'predicted_next_purchase_days': self._predict_next_purchase(user, profile),
            'repeat_purchase_probability': self._compute_repeat_probability(user, profile),
            'buyer_persona': self._determine_persona(user, profile),
            'emotional_state': self._determine_emotional_state(user, profile),
            'sentiment_trend': self._determine_sentiment_trend(profile),
            'community_engagement_score': self._compute_community_score(user),
        }

        # Update twin fields
        for key, value in scores.items():
            if value is not None:
                setattr(twin, key, value)

        twin.twin_version += 1
        twin.last_prediction_at = timezone.now()
        twin.save()

        # Update predicted revenue
        twin.predicted_revenue_7d = self._predict_revenue(user, days=7)
        twin.predicted_revenue_30d = self._predict_revenue(user, days=30)
        twin.predicted_revenue_90d = self._predict_revenue(user, days=90)
        twin.save(update_fields=['predicted_revenue_7d', 'predicted_revenue_30d', 'predicted_revenue_90d'])

        logger.info(
            'Digital Twin updated for %s: CLV=%s, growth=%.1f, persona=%s',
            user.email, twin.customer_lifetime_value, twin.growth_score, twin.buyer_persona
        )
        return scores

    def _compute_clv(self, user, profile) -> Decimal:
        """Compute Customer Lifetime Value prediction."""
        from orders.models import Order
        from datetime import date

        now = timezone.now()
        days_since_joined = max(1, (now - user.date_joined).days)

        # Total spent to date
        total_spent = float(Order.objects.filter(
            user=user,
            order_status__in=['completed', 'shipped', 'paid']
        ).aggregate(total=Sum('total_price'))['total'] or 0)

        # Daily spend rate
        daily_rate = total_spent / days_since_joined

        # Projected 3-year value
        projected_clv = daily_rate * 365 * 3

        # Adjust for engagement
        engagement_multiplier = 0.5 + (profile.engagement_score / 200.0)
        adjusted_clv = projected_clv * engagement_multiplier

        return Decimal(str(max(0, round(adjusted_clv, 2))))

    def _compute_growth_score(self, user, profile) -> float:
        """Compute user growth score (0-100)."""
        from engagement.models import BehaviorEvent

        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        # Order growth
        orders_30d = BehaviorEvent.objects.filter(
            user=user, event_type__in=['order_created', 'order_paid'],
            event_time__gte=thirty_days_ago
        ).count()

        orders_60d = BehaviorEvent.objects.filter(
            user=user, event_type__in=['order_created', 'order_paid'],
            event_time__gte=now - timedelta(days=60),
            event_time__lt=thirty_days_ago
        ).count()

        if orders_60d > 0:
            growth = ((orders_30d - orders_60d) / orders_60d) * 100
        else:
            growth = orders_30d * 10

        score = 50 + (growth / 2)
        return round(max(0, min(100, score)), 2)

    def _compute_interest_score(self, user, profile) -> float:
        """Compute buyer interest score (0-100)."""
        from engagement.models import BehaviorEvent

        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)

        recent_views = BehaviorEvent.objects.filter(
            user=user, event_type='product_view',
            event_time__gte=seven_days_ago
        ).count()

        recent_searches = BehaviorEvent.objects.filter(
            user=user, event_type='search_query',
            event_time__gte=seven_days_ago
        ).count()

        recent_cart = BehaviorEvent.objects.filter(
            user=user, event_type='cart_add',
            event_time__gte=seven_days_ago
        ).count()

        score = min(100, (
            (recent_views * 5) +
            (recent_searches * 10) +
            (recent_cart * 15)
        ))
        return round(score, 2)

    def _compute_trust_score(self, user, profile) -> float:
        """Compute user trust score (0-100)."""
        from orders.models import Order
        from engagement.models import BehaviorEvent

        base_score = 50.0

        # Account age adds trust
        days_joined = (timezone.now() - user.date_joined).days
        age_bonus = min(20, days_joined / 15)

        # Verified users get bonus
        if user.is_verified:
            age_bonus += 10

        # Completed orders add trust
        completed = Order.objects.filter(
            user=user, order_status='completed'
        ).count()
        order_bonus = min(15, completed * 3)

        # Payment failures reduce trust
        failures = BehaviorEvent.objects.filter(
            user=user, event_type='payment_failed'
        ).count()
        failure_penalty = min(20, failures * 5)

        score = base_score + age_bonus + order_bonus - failure_penalty
        return round(max(0, min(100, score)), 2)

    def _compute_reputation_score(self, user, profile) -> float:
        """Compute user reputation score (0-100)."""
        from products.models import Review

        # This is primarily for sellers
        if user.role != 'seller':
            return round(profile.engagement_score, 2)

        from stores.models import Store
        store = getattr(user, 'store', None)
        if not store:
            return 50.0

        # Average rating
        avg_rating = float(Review.objects.filter(
            product__store=store
        ).aggregate(avg=Avg('rating'))['avg'] or 0)
        rating_score = (avg_rating / 5.0) * 60

        # Review count bonus
        review_count = Review.objects.filter(product__store=store).count()
        count_bonus = min(20, review_count * 2)

        # Completion rate
        from orders.models import Order
        total = Order.objects.filter(store=store).count()
        completed = Order.objects.filter(store=store, order_status='completed').count()
        completion_rate = completed / max(total, 1)
        completion_score = completion_rate * 20

        return round(min(100, rating_score + count_bonus + completion_score), 2)

    def _compute_seller_performance(self, user) -> float:
        """Compute seller performance score (0-100)."""
        if user.role != 'seller':
            return 0.0

        from stores.models import Store
        from orders.models import Order

        store = getattr(user, 'store', None)
        if not store:
            return 0.0

        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        # Order volume
        orders_30d = Order.objects.filter(store=store, created_at__gte=thirty_days_ago).count()
        volume_score = min(30, orders_30d * 3)

        # Completion rate
        completed = Order.objects.filter(
            store=store, order_status='completed',
            created_at__gte=thirty_days_ago
        ).count()
        cancelled = Order.objects.filter(
            store=store, order_status='cancelled',
            created_at__gte=thirty_days_ago
        ).count()
        total_30d = completed + cancelled
        completion_rate = completed / max(total_30d, 1)
        completion_score = completion_rate * 30

        # Response time
        response_score = 20  # Default

        # Review rating
        avg_rating = self._compute_reputation_score(user)
        review_score = avg_rating * 0.2

        return round(min(100, volume_score + completion_score + response_score + review_score), 2)

    def _compute_store_health(self, user) -> float:
        """Compute store health score (0-100)."""
        if user.role != 'seller':
            return 0.0

        from stores.models import Store
        store = getattr(user, 'store', None)
        if not store:
            return 0.0

        score = 50.0

        # Products listed
        product_count = store.products.filter(is_active=True).count()
        score += min(15, product_count * 2)

        # Orders
        from orders.models import Order
        order_count = Order.objects.filter(store=store).count()
        score += min(15, order_count)

        # Average rating
        if hasattr(store, 'rating_avg') and store.rating_avg:
            score += (float(store.rating_avg) / 5.0) * 20

        return round(max(0, min(100, score)), 2)

    def _compute_inventory_health(self, user) -> float:
        """Compute inventory health score (0-100)."""
        if user.role != 'seller':
            return 0.0

        from stores.models import Store
        store = getattr(user, 'store', None)
        if not store:
            return 0.0

        products = store.products.filter(is_active=True)
        total = products.count()
        if total == 0:
            return 0.0

        out_of_stock = products.filter(stock=0).count()
        low_stock = products.filter(stock__gt=0, stock__lte=5).count()
        healthy = products.filter(stock__gt=5).count()

        health_pct = (healthy / total) * 100
        low_penalty = (low_stock / total) * 20
        oos_penalty = (out_of_stock / total) * 40

        return round(max(0, min(100, health_pct - low_penalty - oos_penalty)), 2)

    def _compute_product_opportunity(self, user) -> float:
        """Compute product opportunity score (0-100)."""
        if user.role != 'seller':
            return 0.0

        from stores.models import Store
        store = getattr(user, 'store', None)
        if not store:
            return 0.0

        # Analyze which categories have high demand but low supply from this store
        from products.models import Product, Category
        from orders.models import OrderItem

        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        # Seller's category distribution
        seller_cats = Product.objects.filter(
            store=store, is_active=True
        ).values('category').annotate(count=Count('id'))

        # Marketplace demand by category
        demand_by_cat = OrderItem.objects.filter(
            order__created_at__gte=thirty_days_ago,
            product__store__is_active=True
        ).values('product__category').annotate(
            total_demand=Sum('qty')
        ).order_by('-total_demand')[:10]

        # Find gaps: high demand categories the seller doesn't serve
        seller_cat_ids = set(c['category'] for c in seller_cats if c['category'])
        opportunity_cats = [
            c for c in demand_by_cat
            if c['product__category'] and c['product__category'] not in seller_cat_ids
        ]

        opportunity_score = len(opportunity_cats) * 10
        return round(min(100, opportunity_score), 2)

    def _predict_next_purchase(self, user, profile) -> int:
        """Predict days until next purchase."""
        from engagement.models import BehaviorEvent
        from orders.models import Order

        # Get purchase interval
        orders = Order.objects.filter(
            user=user,
            order_status__in=['completed', 'shipped', 'paid']
        ).order_by('created_at')

        if orders.count() < 2:
            if orders.count() == 1:
                days_since = (timezone.now() - orders[0].created_at).days
                return max(1, 30 - days_since)
            return 30

        # Average interval between orders
        intervals = []
        prev_date = None
        for order in orders:
            if prev_date:
                interval = (order.created_at - prev_date).days
                if interval > 0:
                    intervals.append(interval)
            prev_date = order.created_at

        avg_interval = sum(intervals) / len(intervals) if intervals else 30

        # Adjust for recent activity
        recent_activity = BehaviorEvent.objects.filter(
            user=user,
            event_time__gte=timezone.now() - timedelta(days=7)
        ).count()
        activity_multiplier = max(0.5, 1.0 - (recent_activity / 20.0))

        return max(1, int(avg_interval * activity_multiplier))

    def _compute_repeat_probability(self, user, profile) -> float:
        """Compute probability of repeat purchase (0-1)."""
        from orders.models import Order

        total_orders = Order.objects.filter(user=user).count()
        if total_orders == 0:
            return 0.0

        # Users with 2+ orders have higher repeat probability
        if total_orders >= 2:
            base = 0.6
        elif total_orders == 1:
            base = 0.3
        else:
            base = 0.1

        # Adjust by engagement
        engagement_factor = profile.engagement_score / 100.0
        return round(min(0.99, base + (engagement_factor * 0.3)), 4)

    def _determine_persona(self, user, profile) -> str:
        """Determine buyer persona based on behavior."""
        if profile.total_orders == 0:
            if profile.total_products_viewed > 20:
                return 'browser'
            return 'new_visitor'

        avg_order = float(profile.avg_order_value)
        total_orders = profile.total_orders
        engagement = profile.engagement_score

        if total_orders > 20 and avg_order > 200000:
            return 'premium_shopper'
        elif total_orders > 10 and engagement > 60:
            return 'power_shopper'
        elif total_orders > 5:
            return 'regular_buyer'
        elif avg_order > 150000:
            return 'quality_seeker'
        elif profile.cart_abandon_rate > 0.5:
            return 'cart_abandoner'
        elif profile.total_searches > profile.total_orders * 3:
            return 'researcher'
        else:
            return 'occasional_buyer'

    def _determine_emotional_state(self, user, profile) -> str:
        """Determine user's emotional state based on recent signals."""
        from engagement.models import BehaviorEvent
        from orders.models import Order

        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)

        # Recent refunds/cancellations
        recent_cancels = Order.objects.filter(
            user=user,
            order_status='cancelled',
            created_at__gte=seven_days_ago
        ).count()

        recent_refunds = Order.objects.filter(
            user=user,
            order_status='refunded',
            created_at__gte=seven_days_ago
        ).count()

        payment_failures = BehaviorEvent.objects.filter(
            user=user, event_type='payment_failed',
            event_time__gte=seven_days_ago
        ).count()

        negative_signals = recent_cancels + recent_refunds + payment_failures
        if negative_signals >= 3:
            return 'frustrated'
        elif negative_signals >= 1:
            if profile.churn_risk_score > 50:
                return 'at_risk'
            return 'frustrated'

        # Positive signals
        completed = Order.objects.filter(
            user=user, order_status='completed',
            created_at__gte=seven_days_ago
        ).count()

        if completed >= 2 and profile.engagement_score > 60:
            return 'delighted'
        elif completed >= 1:
            return 'satisfied'

        return 'neutral'

    def _determine_sentiment_trend(self, profile) -> str:
        """Determine sentiment trend."""
        if profile.engagement_score > profile.retention_score:
            return 'improving'
        elif profile.retention_score > profile.engagement_score + 10:
            return 'declining'
        return 'stable'

    def _compute_community_score(self, user) -> float:
        """Compute community engagement score."""
        from engagement.models import BehaviorEvent

        reviews = BehaviorEvent.objects.filter(user=user, event_type='review_written').count()
        follows = BehaviorEvent.objects.filter(user=user, event_type='store_follow').count()
        referrals = BehaviorEvent.objects.filter(user=user, event_type='referral_made').count()
        chats = BehaviorEvent.objects.filter(user=user, event_type='chat_message').count()

        score = (reviews * 10) + (follows * 5) + (referrals * 20) + (chats * 2)
        return round(min(100, score), 2)

    def _predict_revenue(self, user, days: int) -> Decimal:
        """Predict revenue for a given period."""
        from orders.models import Order

        now = timezone.now()
        past_period = now - timedelta(days=days)

        # Historical revenue for same period
        historical = Order.objects.filter(
            user=user,
            created_at__gte=past_period,
            order_status__in=['completed', 'paid']
        ).aggregate(total=Sum('total_price'))['total'] or 0

        return Decimal(str(historical))


# Singleton
_twin_engine = None


def get_digital_twin_engine() -> DigitalTwinEngine:
    global _twin_engine
    if _twin_engine is None:
        _twin_engine = DigitalTwinEngine()
    return _twin_engine
