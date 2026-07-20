"""
Django Admin for AI Intelligence Platform.
"""
from django.contrib import admin
from django.utils.html import format_html
from ai_intelligence.models import (
    DigitalTwin, MarketplaceHealthSnapshot, DemandPrediction,
    PricingRecommendation, SalesForecast, CustomerSegment,
    UserSegmentAssignment, GamificationProfile, Challenge,
    UserChallengeProgress, BusinessCoachInsight, PersonalShoppingInsight,
    AIModelRegistry, ExperimentResult,
)


@admin.register(DigitalTwin)
class DigitalTwinAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'buyer_persona', 'customer_lifetime_value',
                   'growth_score', 'trust_score', 'emotional_state', 'twin_version')
    list_filter = ('buyer_persona', 'emotional_state', 'sentiment_trend')
    search_fields = ('user__email', 'buyer_persona')
    readonly_fields = ('twin_version', 'created_at', 'computed_at')
    ordering = ('-customer_lifetime_value',)

    def user_email(self, obj): return obj.user.email


@admin.register(MarketplaceHealthSnapshot)
class MarketplaceHealthSnapshotAdmin(admin.ModelAdmin):
    list_display = ('snapshot_time', 'marketplace_health_score_colored', 'trend_direction',
                   'total_active_users', 'gmv_last_7d', 'avg_engagement_score')
    list_filter = ('trend_direction',)
    readonly_fields = ('created_at',)
    ordering = ('-snapshot_time',)

    def marketplace_health_score_colored(self, obj):
        colors = {'growing': '#00B894', 'stable': '#74B9FF', 'declining': '#E17055', 'critical': '#D63031'}
        color = colors.get(obj.trend_direction, '#636E72')
        return format_html('<span style="color:{};font-weight:bold;">{:.1f}</span>', color, obj.marketplace_health_score)
    marketplace_health_score_colored.short_description = 'Health Score'


@admin.register(DemandPrediction)
class DemandPredictionAdmin(admin.ModelAdmin):
    list_display = ('product', 'forecast_date', 'predicted_demand', 'confidence_score',
                   'restock_urgency_colored', 'recommended_stock')
    list_filter = ('restock_urgency', 'forecast_period')
    search_fields = ('product__product_name',)
    ordering = ('-forecast_date',)

    def restock_urgency_colored(self, obj):
        colors = {'critical': '#D63031', 'high': '#E17055', 'normal': '#74B9FF', 'low': '#00B894'}
        color = colors.get(obj.restock_urgency, '#636E72')
        return format_html('<span style="color:{};font-weight:bold;">{}</span>', color, obj.get_restock_urgency_display())
    restock_urgency_colored.short_description = 'Urgency'


@admin.register(PricingRecommendation)
class PricingRecommendationAdmin(admin.ModelAdmin):
    list_display = ('product', 'current_price', 'recommended_price', 'strategy',
                   'expected_revenue_change', 'is_applied')
    list_filter = ('strategy', 'is_applied')
    search_fields = ('product__product_name',)


@admin.register(SalesForecast)
class SalesForecastAdmin(admin.ModelAdmin):
    list_display = ('store_name', 'forecast_date', 'period', 'predicted_revenue',
                   'predicted_orders', 'confidence_score')
    list_filter = ('period',)
    ordering = ('-forecast_date',)
    def store_name(self, obj): return obj.store.store_name if obj.store else 'Marketplace'


@admin.register(CustomerSegment)
class CustomerSegmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'segment_type', 'color', 'is_active')
    list_filter = ('segment_type', 'is_active')


@admin.register(UserSegmentAssignment)
class UserSegmentAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'segment', 'score', 'is_primary')
    list_filter = ('is_primary', 'segment')
    search_fields = ('user__email',)
    def user_email(self, obj): return obj.user.email


@admin.register(GamificationProfile)
class GamificationProfileAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'level', 'xp_points', 'current_streak_days',
                   'longest_streak_days', 'total_badges', 'habit_loop_phase')
    list_filter = ('level', 'habit_loop_phase')
    search_fields = ('user__email',)
    def user_email(self, obj): return obj.user.email


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ('name', 'challenge_type', 'difficulty', 'xp_reward', 'is_active', 'is_featured')
    list_filter = ('challenge_type', 'difficulty', 'is_active')


@admin.register(UserChallengeProgress)
class UserChallengeProgressAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'challenge', 'progress_bar', 'is_completed')
    list_filter = ('is_completed',)
    def user_email(self, obj): return obj.user.email
    def progress_bar(self, obj):
        pct = min(100, int((obj.current_value / max(obj.target_value, 1)) * 100))
        return format_html('<div style="width:100px;background:#e9ecef;border-radius:4px;"><div style="width:{}%;background:#6C5CE7;height:16px;border-radius:4px;text-align:center;color:white;font-size:10px;line-height:16px;">{}%</div></div>', pct, pct)
    progress_bar.short_description = 'Progress'


@admin.register(BusinessCoachInsight)
class BusinessCoachInsightAdmin(admin.ModelAdmin):
    list_display = ('title', 'store_name', 'category', 'priority_colored', 'is_read', 'computed_at')
    list_filter = ('category', 'priority', 'is_read')
    search_fields = ('title', 'store__store_name')
    ordering = ('-priority', '-computed_at')
    def store_name(self, obj): return obj.store.store_name
    def priority_colored(self, obj):
        colors = {0: '#636E72', 1: '#74B9FF', 2: '#00B894', 3: '#E17055', 4: '#D63031'}
        color = colors.get(obj.priority, '#636E72')
        return format_html('<span style="color:{};font-weight:bold;">P{}</span>', color, obj.priority)
    priority_colored.short_description = 'Priority'


@admin.register(PersonalShoppingInsight)
class PersonalShoppingInsightAdmin(admin.ModelAdmin):
    list_display = ('title', 'user_email', 'insight_type', 'is_read', 'computed_at')
    list_filter = ('insight_type', 'is_read')
    search_fields = ('user__email', 'title')
    def user_email(self, obj): return obj.user.email


@admin.register(AIModelRegistry)
class AIModelRegistryAdmin(admin.ModelAdmin):
    list_display = ('name', 'model_type', 'version', 'accuracy', 'is_active', 'last_trained_at')
    list_filter = ('model_type', 'is_active', 'is_deprecated')


@admin.register(ExperimentResult)
class ExperimentResultAdmin(admin.ModelAdmin):
    list_display = ('name', 'experiment_type', 'status_colored', 'winner', 'sample_size', 'started_at')
    list_filter = ('experiment_type', 'status')
    def status_colored(self, obj):
        colors = {'running': '#00B894', 'completed': '#74B9FF', 'cancelled': '#E17055'}
        color = colors.get(obj.status, '#636E72')
        return format_html('<span style="color:{};font-weight:bold;">{}</span>', color, obj.status)
    status_colored.short_description = 'Status'
