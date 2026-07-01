"""
Loyalty & Reward Points serializers for Warungio Marketplace.
Flutter-ready JSON response contracts.
"""

from rest_framework import serializers
from .models import (
    LoyaltyTier, LoyaltyAccount, LoyaltyTransaction,
    LoyaltyReward, LoyaltyRedemption, LoyaltyReferral
)


class LoyaltyTierSerializer(serializers.ModelSerializer):
    """Loyalty tier serializer."""

    class Meta:
        model = LoyaltyTier
        fields = '__all__'


class LoyaltyTransactionSerializer(serializers.ModelSerializer):
    """Loyalty transaction serializer."""
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = LoyaltyTransaction
        fields = '__all__'
        read_only_fields = ['created_at']


class LoyaltyRewardSerializer(serializers.ModelSerializer):
    """Loyalty reward serializer."""
    valid_tier_names = serializers.SerializerMethodField()

    class Meta:
        model = LoyaltyReward
        fields = '__all__'
        read_only_fields = ['usage_count', 'created_at']

    def get_valid_tier_names(self, obj):
        return [t.get_name_display() for t in obj.valid_for_tiers.all()]


class LoyaltyRedemptionSerializer(serializers.ModelSerializer):
    """Loyalty redemption serializer."""
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    reward_name = serializers.CharField(source='reward.name', read_only=True)
    reward_type = serializers.CharField(source='reward.reward_type', read_only=True)

    class Meta:
        model = LoyaltyRedemption
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class LoyaltyAccountSerializer(serializers.ModelSerializer):
    """Loyalty account serializer."""
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    tier_name = serializers.CharField(source='tier.get_name_display', read_only=True, allow_null=True)
    tier_display_name = serializers.CharField(source='tier.display_name', read_only=True, allow_null=True)
    tier_icon = serializers.CharField(source='tier.icon', read_only=True, allow_null=True)
    tier_badge_color = serializers.CharField(source='tier.badge_color', read_only=True, allow_null=True)
    tier_multiplier = serializers.DecimalField(
        source='tier.point_multiplier', max_digits=4, decimal_places=2,
        read_only=True, allow_null=True
    )
    next_tier = serializers.SerializerMethodField()
    points_to_next_tier = serializers.SerializerMethodField()

    class Meta:
        model = LoyaltyAccount
        fields = [
            'id', 'user', 'user_name', 'tier', 'tier_name', 'tier_display_name',
            'tier_icon', 'tier_badge_color', 'tier_multiplier',
            'points_balance', 'total_points_earned', 'total_points_redeemed',
            'lifetime_points', 'total_orders', 'total_spent',
            'next_tier', 'points_to_next_tier',
            'last_earned_at', 'last_redeemed_at', 'joined_at',
        ]
        read_only_fields = [
            'points_balance', 'total_points_earned', 'total_points_redeemed',
            'lifetime_points', 'total_orders', 'total_spent',
            'joined_at',
        ]

    def get_next_tier(self, obj):
        """Get next tier info."""
        if not obj.tier:
            next_tier = LoyaltyTier.objects.filter(is_active=True, sort_order__gt=0).first()
            return LoyaltyTierSerializer(next_tier).data if next_tier else None
        next_tier = LoyaltyTier.objects.filter(
            is_active=True, sort_order__gt=obj.tier.sort_order
        ).order_by('sort_order').first()
        return LoyaltyTierSerializer(next_tier).data if next_tier else None

    def get_points_to_next_tier(self, obj):
        """Points needed to reach next tier."""
        if not obj.tier:
            next_tier = LoyaltyTier.objects.filter(is_active=True, sort_order__gt=0).first()
            if next_tier:
                return next_tier.min_points - obj.points_balance
            return 0
        next_tier = LoyaltyTier.objects.filter(
            is_active=True, sort_order__gt=obj.tier.sort_order
        ).order_by('sort_order').first()
        if next_tier:
            return max(0, next_tier.min_points - obj.points_balance)
        return 0


class LoyaltyReferralSerializer(serializers.ModelSerializer):
    """Loyalty referral serializer."""
    referrer_name = serializers.CharField(source='referrer.full_name', read_only=True)
    referred_name = serializers.CharField(source='referred.full_name', read_only=True)

    class Meta:
        model = LoyaltyReferral
        fields = '__all__'
        read_only_fields = ['created_at']


# =============================================================================
# FLUTTER DTO — API Response Contracts for Mobile
# =============================================================================

class FlutterLoyaltyDashboardDTO(serializers.Serializer):
    """DTO for Flutter: Complete loyalty dashboard."""
    account = LoyaltyAccountSerializer()
    recent_transactions = LoyaltyTransactionSerializer(many=True)
    available_rewards = LoyaltyRewardSerializer(many=True)
    active_redemptions = LoyaltyRedemptionSerializer(many=True)
    tiers = LoyaltyTierSerializer(many=True)
    stats = serializers.SerializerMethodField()

    def get_stats(self, obj):
        return {
            'total_points_earned': obj['account'].total_points_earned,
            'points_to_next_tier': obj['account'].get('points_to_next_tier', 0),
            'this_month_earned': obj.get('this_month_earned', 0),
            'this_month_redeemed': obj.get('this_month_redeemed', 0),
            'days_until_points_expiry': obj.get('days_until_points_expiry', None),
        }


class FlutterPointsEarnDTO(serializers.Serializer):
    """DTO for Flutter: Points earning calculation."""
    order_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    points_earned = serializers.IntegerField()
    multiplier_applied = serializers.DecimalField(max_digits=4, decimal_places=2)
    tier_name = serializers.CharField()
    breakdown = serializers.DictField(child=serializers.IntegerField())


class FlutterRewardRedemptionDTO(serializers.Serializer):
    """DTO for Flutter: Reward redemption result."""
    redemption_id = serializers.IntegerField()
    reward_name = serializers.CharField()
    points_spent = serializers.IntegerField()
    points_balance_after = serializers.IntegerField()
    voucher_code = serializers.CharField(allow_null=True)
    valid_until = serializers.DateTimeField(allow_null=True)
    status = serializers.CharField()
    message = serializers.CharField()
