"""
Loyalty admin configuration for Warungio Marketplace.
"""
from django.contrib import admin
from .models import (
    LoyaltyTier, LoyaltyAccount, LoyaltyTransaction,
    LoyaltyReward, LoyaltyRedemption, LoyaltyReferral
)


# Note: LoyaltyTransactionInline is intentionally removed because
# LoyaltyTransaction has FK to User, not LoyaltyAccount.
# Use LoyaltyTransactionAdmin to manage transactions directly.


@admin.register(LoyaltyTier)
class LoyaltyTierAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'min_points', 'max_points', 'point_multiplier',
                    'member_count', 'is_active', 'sort_order']
    list_filter = ['is_active']
    search_fields = ['name', 'display_name']
    ordering = ['sort_order']
    readonly_fields = ['created_at']

    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = 'Jumlah Anggota'


@admin.register(LoyaltyAccount)
class LoyaltyAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'email', 'tier', 'points_balance', 'total_points_earned',
                    'total_orders', 'total_spent', 'joined_at']
    list_filter = ['tier']
    search_fields = ['user__email', 'user__full_name']
    readonly_fields = ['points_balance', 'total_points_earned', 'total_points_redeemed',
                       'lifetime_points', 'total_orders', 'total_spent',
                       'last_earned_at', 'last_redeemed_at', 'joined_at']
    actions = ['add_bonus_points']

    def email(self, obj):
        return obj.user.email
    email.short_description = 'Email'

    def add_bonus_points(self, request, queryset):
        points = 1000
        for account in queryset:
            account.add_points(points, 'Bonus from admin')
        self.message_user(request, f'Added {points} points to {queryset.count()} accounts.')
    add_bonus_points.short_description = 'Add 1000 bonus points'


@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'points', 'balance_after', 'description', 'created_at']
    list_filter = ['transaction_type']
    search_fields = ['user__email', 'description']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(LoyaltyReward)
class LoyaltyRewardAdmin(admin.ModelAdmin):
    list_display = ['name', 'reward_type', 'points_required', 'discount_value',
                    'usage_count', 'is_active', 'is_featured']
    list_filter = ['reward_type', 'is_active', 'is_featured']
    search_fields = ['name']
    ordering = ['sort_order']
    filter_horizontal = ['valid_for_tiers']


@admin.register(LoyaltyRedemption)
class LoyaltyRedemptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'reward', 'points_spent', 'status', 'voucher_code', 'created_at']
    list_filter = ['status']
    search_fields = ['user__email', 'voucher_code']
    readonly_fields = ['created_at']


@admin.register(LoyaltyReferral)
class LoyaltyReferralAdmin(admin.ModelAdmin):
    list_display = ['referrer', 'referred', 'referral_code', 'first_purchase_made', 'created_at']
    list_filter = ['first_purchase_made', 'referrer_bonus_given']
    search_fields = ['referrer__email', 'referred__email', 'referral_code']
    readonly_fields = ['created_at']
