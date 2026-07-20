"""
AI Customer Segmentation Engine.
RFM analysis, behavioral clustering, and persona-based segmentation.
"""

import logging
from datetime import timedelta
from typing import Dict, List
from django.db.models import Sum, Count, Q
from django.utils import timezone

logger = logging.getLogger(__name__)


class SegmentationEngine:
    """
    Customer segmentation using RFM (Recency, Frequency, Monetary) 
    and behavioral clustering.
    """

    RFM_SEGMENTS = [
        {'name': 'Champions', 'min_recency': 0, 'max_recency': 7, 'min_frequency': 5, 'min_monetary': 500000},
        {'name': 'Loyal Customers', 'min_recency': 0, 'max_recency': 14, 'min_frequency': 3, 'min_monetary': 200000},
        {'name': 'Potential Loyalists', 'min_recency': 0, 'max_recency': 30, 'min_frequency': 2, 'min_monetary': 100000},
        {'name': 'New Customers', 'min_recency': 0, 'max_recency': 14, 'min_frequency': 1, 'min_monetary': 0},
        {'name': 'Promising', 'min_recency': 0, 'max_recency': 30, 'min_frequency': 1, 'min_monetary': 50000},
        {'name': 'Need Attention', 'min_recency': 15, 'max_recency': 45, 'min_frequency': 2, 'min_monetary': 100000},
        {'name': 'About to Sleep', 'min_recency': 30, 'max_recency': 60, 'min_frequency': 1, 'min_monetary': 0},
        {'name': 'At Risk', 'min_recency': 31, 'max_recency': 90, 'min_frequency': 2, 'min_monetary': 100000},
        {'name': 'Cannot Lose', 'min_recency': 31, 'max_recency': 90, 'min_frequency': 5, 'min_monetary': 500000},
        {'name': 'Hibernating', 'min_recency': 61, 'max_recency': 180, 'min_frequency': 1, 'min_monetary': 0},
        {'name': 'Lost', 'min_recency': 181, 'max_recency': 9999, 'min_frequency': 0, 'min_monetary': 0},
    ]

    def segment_user(self, user) -> str:
        """Determine RFM segment for a user."""
        from orders.models import Order
        from engagement.models import UserBehaviorProfile

        now = timezone.now()
        profile, _ = UserBehaviorProfile.objects.get_or_create(user=user)

        # Recency: days since last order
        last_order = Order.objects.filter(user=user).order_by('-created_at').first()
        if last_order:
            recency = (now - last_order.created_at).days
        else:
            recency = 999

        # Frequency: total orders
        frequency = Order.objects.filter(user=user).count()

        # Monetary: total spent
        monetary = float(Order.objects.filter(user=user).aggregate(
            total=Sum('total_price'))['total'] or 0)

        # Find matching segment
        for segment in self.RFM_SEGMENTS:
            if (segment['min_recency'] <= recency <= segment['max_recency'] and
                frequency >= segment['min_frequency'] and
                monetary >= segment['min_monetary']):
                return segment['name']

        return 'New Customers'

    def get_segment_characteristics(self, segment_name: str) -> Dict:
        """Get characteristics and strategy for a segment."""
        strategies = {
            'Champions': {
                'description': 'Best customers — high value, frequent buyers',
                'strategy': 'Reward loyalty, ask for referrals, give early access',
                'color': '#6C5CE7', 'icon': '👑',
            },
            'Loyal Customers': {
                'description': 'Regular shoppers — solid revenue base',
                'strategy': 'Upsell, cross-sell, loyalty program perks',
                'color': '#00B894', 'icon': '⭐',
            },
            'Potential Loyalists': {
                'description': 'Recent buyers showing promise',
                'strategy': 'Personalize recommendations, nurture relationship',
                'color': '#74B9FF', 'icon': '🌟',
            },
            'New Customers': {
                'description': 'First purchase — high potential',
                'strategy': 'Great onboarding, first-time buyer perks',
                'color': '#FDCB6E', 'icon': '🆕',
            },
            'Promising': {
                'description': 'Shows interest but low spend',
                'strategy': 'Send relevant offers, bundle deals',
                'color': '#E17055', 'icon': '📈',
            },
            'Need Attention': {
                'description': 'Used to buy more — showing decline',
                'strategy': 'Re-engage with win-back offers',
                'color': '#FD79A8', 'icon': '⚠️',
            },
            'About to Sleep': {
                'description': 'Dormant — at risk of churning',
                'strategy': 'Re-activation campaign, special discount',
                'color': '#FDCB6E', 'icon': '😴',
            },
            'At Risk': {
                'description': 'Haven\'t bought in a while',
                'strategy': 'Urgent re-engagement, big incentive',
                'color': '#E17055', 'icon': '🚨',
            },
            'Cannot Lose': {
                'description': 'High value but slipping away',
                'strategy': 'Personal outreach, VIP treatment',
                'color': '#D63031', 'icon': '💎',
            },
            'Hibernating': {
                'description': 'Long time no see',
                'strategy': 'Big comeback offer, remind of value',
                'color': '#636E72', 'icon': '💤',
            },
            'Lost': {
                'description': 'Effectively churned',
                'strategy': 'Too far gone — focus on acquisition',
                'color': '#2D3436', 'icon': '💔',
            },
        }
        return strategies.get(segment_name, {
            'description': 'Unknown segment',
            'strategy': 'Generic engagement',
            'color': '#6C757D', 'icon': '❓',
        })


# Singleton
_segmentation_engine = None


def get_segmentation_engine() -> SegmentationEngine:
    global _segmentation_engine
    if _segmentation_engine is None:
        _segmentation_engine = SegmentationEngine()
    return _segmentation_engine
