"""
AI Marketplace Health Monitor.
Tracks platform-wide health metrics and computes composite health scores.
"""

import logging
from datetime import timedelta, date
from decimal import Decimal
from typing import Dict
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone

logger = logging.getLogger(__name__)


class MarketplaceHealthService:
    """
    Monitors the health of the entire Warungio marketplace.
    Computes health scores, growth indices, and trend indicators.
    """

    def capture_snapshot(self) -> Dict:
        """Capture a full marketplace health snapshot."""
        from django.contrib.auth import get_user_model
        from ai_intelligence.models import MarketplaceHealthSnapshot
        from orders.models import Order
        from stores.models import Store
        from products.models import Product
        from engagement.models import UserBehaviorProfile, NotificationAnalytics, BehaviorEvent

        User = get_user_model()
        now = timezone.now()
        today = now.date()
        yesterday = today - timedelta(days=1)
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)

        # Active users
        active_users = User.objects.filter(is_active=True).count()
        active_buyers = User.objects.filter(is_active=True, role='buyer').count()
        active_sellers = User.objects.filter(is_active=True, role='seller').count()
        active_stores = Store.objects.filter(is_active=True).count()
        total_listings = Product.objects.filter(is_active=True).count()

        # Orders
        orders_24h = Order.objects.filter(created_at__date=today).count()
        orders_7d = Order.objects.filter(created_at__gte=seven_days_ago).count()
        orders_30d = Order.objects.filter(created_at__gte=thirty_days_ago).count()

        # GMV
        gmv_24h = Order.objects.filter(
            created_at__date=today,
            order_status__in=['paid', 'processed', 'shipped', 'completed']
        ).aggregate(total=Sum('total_price'))['total'] or 0

        gmv_7d = Order.objects.filter(
            created_at__gte=seven_days_ago,
            order_status__in=['paid', 'processed', 'shipped', 'completed']
        ).aggregate(total=Sum('total_price'))['total'] or 0

        gmv_30d = Order.objects.filter(
            created_at__gte=thirty_days_ago,
            order_status__in=['paid', 'processed', 'shipped', 'completed']
        ).aggregate(total=Sum('total_price'))['total'] or 0

        avg_order = Order.objects.filter(created_at__gte=seven_days_ago).aggregate(
            avg=Avg('total_price'))['avg'] or 0

        # Engagement
        avg_engagement = UserBehaviorProfile.objects.aggregate(
            avg=Avg('engagement_score'))['avg'] or 0
        avg_retention = UserBehaviorProfile.objects.aggregate(
            avg=Avg('retention_score'))['avg'] or 0
        avg_churn = UserBehaviorProfile.objects.aggregate(
            avg=Avg('churn_risk_score'))['avg'] or 0

        at_risk = UserBehaviorProfile.objects.filter(
            risk_level__in=['at_risk', 'dormant']
        ).count()

        churned = UserBehaviorProfile.objects.filter(risk_level='churned').count()

        new_regs = User.objects.filter(date_joined__gte=seven_days_ago).count()

        # Delivery
        from orders.models import Delivery
        completed_deliveries = Delivery.objects.filter(
            delivery_status='pesanan_diterima',
            updated_at__gte=seven_days_ago
        ).count()
        total_deliveries = Delivery.objects.filter(updated_at__gte=seven_days_ago).exclude(
            delivery_status='dibatalkan'
        ).count()
        delivery_rate = completed_deliveries / max(total_deliveries, 1) * 100

        # Financial
        from payments.models import Wallet
        wallet_balance = Wallet.objects.aggregate(total=Sum('balance'))['total'] or 0

        # Conversion rate
        unique_visitors = BehaviorEvent.objects.filter(
            event_type='login',
            event_time__gte=seven_days_ago
        ).values('user').distinct().count()

        conversion_rate = orders_7d / max(unique_visitors, 1)

        # Composite health score
        health_score = self._compute_health_score(
            orders_7d=orders_7d,
            gmv_7d=float(gmv_7d),
            avg_engagement=float(avg_engagement),
            delivery_rate=delivery_rate,
            conversion_rate=conversion_rate,
            at_risk_pct=(at_risk / max(active_users, 1)) * 100,
        )

        # Trend direction
        prev_7d_start = seven_days_ago - timedelta(days=7)
        prev_gmv = float(Order.objects.filter(
            created_at__gte=prev_7d_start,
            created_at__lt=seven_days_ago,
            order_status__in=['paid', 'processed', 'shipped', 'completed']
        ).aggregate(total=Sum('total_price'))['total'] or 0)

        growth_index = ((float(gmv_7d) - prev_gmv) / max(prev_gmv, 1)) * 100

        if growth_index > 10:
            trend = 'growing'
        elif growth_index < -10:
            trend = 'declining'
        else:
            trend = 'stable'

        if health_score < 30:
            trend = 'critical'

        snapshot = MarketplaceHealthSnapshot.objects.create(
            snapshot_time=now,
            total_active_users=active_users,
            total_active_sellers=active_sellers,
            total_active_buyers=active_buyers,
            total_active_stores=active_stores,
            total_listings=total_listings,
            orders_last_24h=orders_24h,
            orders_last_7d=orders_7d,
            orders_last_30d=orders_30d,
            gmv_last_24h=gmv_24h,
            gmv_last_7d=gmv_7d,
            gmv_last_30d=gmv_30d,
            avg_order_value=avg_order,
            conversion_rate=round(conversion_rate, 4),
            avg_engagement_score=round(float(avg_engagement), 2),
            avg_retention_score=round(float(avg_retention), 2),
            avg_churn_risk=round(float(avg_churn), 2),
            total_at_risk_users=at_risk,
            total_churned_users=churned,
            new_registrations_24h=User.objects.filter(date_joined__date=today).count(),
            re_engagements_24h=UserBehaviorProfile.objects.filter(
                risk_level='reactivated',
                risk_level_changed_at__date=today
            ).count(),
            delivery_success_rate=round(delivery_rate, 2),
            total_wallet_balance=wallet_balance,
            refund_rate=0.0,
            total_ai_scans_24h=BehaviorEvent.objects.filter(
                event_type='ai_scan', event_time__date=today
            ).count(),
            marketplace_health_score=round(health_score, 2),
            growth_index=round(growth_index, 2),
            trend_direction=trend,
        )

        logger.info(
            'Marketplace health snapshot: score=%.1f, trend=%s, GMV 7d=%s',
            health_score, trend, gmv_7d
        )
        return snapshot

    def _compute_health_score(self, orders_7d: int, gmv_7d: float,
                               avg_engagement: float, delivery_rate: float,
                               conversion_rate: float, at_risk_pct: float) -> float:
        """Compute composite marketplace health score (0-100)."""
        # Transaction health (30%)
        tx_score = min(30, (orders_7d * 2) + (gmv_7d / 1000000))

        # Engagement health (25%)
        eng_score = avg_engagement * 0.25

        # Delivery health (20%)
        del_score = delivery_rate * 0.20

        # Conversion health (15%)
        conv_score = min(15, conversion_rate * 100)

        # Risk health (10%) — lower at_risk = better
        risk_score = max(0, 10 - (at_risk_pct * 0.2))

        score = tx_score + eng_score + del_score + conv_score + risk_score
        return round(max(0, min(100, score)), 2)


# Singleton
_health_service = None


def get_marketplace_health_service() -> MarketplaceHealthService:
    global _health_service
    if _health_service is None:
        _health_service = MarketplaceHealthService()
    return _health_service
