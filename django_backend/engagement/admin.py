"""
Django Admin configuration for Engagement & Retention Engine.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg

from engagement.models import (
    UserBehaviorProfile, BehaviorEvent, ActivityLog,
    ChurnPrediction, DeviceToken, NotificationTemplate,
    NotificationCampaign, NotificationQueue, NotificationAnalytics,
    NotificationDeliveryLog, NotificationABTest, QuietHoursConfig,
    NotificationPreferenceExtension, NotificationCooldown, EngagementSignal,
)


# ═══════════════════════════════════════════════════════════════
# INLINE ADMINS
# ═══════════════════════════════════════════════════════════════

class BehaviorEventInline(admin.TabularInline):
    model = BehaviorEvent
    fields = ('event_type', 'event_category', 'event_time', 'source')
    readonly_fields = ('event_time',)
    extra = 0
    max_num = 10
    ordering = ('-event_time',)
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class ActivityLogInline(admin.TabularInline):
    model = ActivityLog
    fields = ('activity_type', 'period', 'count', 'period_start')
    readonly_fields = ('period_start',)
    extra = 0
    max_num = 5
    ordering = ('-period_start',)
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ═══════════════════════════════════════════════════════════════
# MODEL ADMINS
# ═══════════════════════════════════════════════════════════════

@admin.register(UserBehaviorProfile)
class UserBehaviorProfileAdmin(admin.ModelAdmin):
    """Admin for user behavior profiles with score visualization."""
    list_display = ('user_email', 'user_role', 'engagement_score', 'retention_score',
                   'churn_risk_score', 'loyalty_score', 'fatigue_score',
                   'risk_level_colored', 'inactivity_days', 'last_active_at')
    list_filter = ('risk_level', 'loyalty_tier', 'computed_at')
    search_fields = ('user__email', 'user__full_name', 'city')
    readonly_fields = ('computed_at', 'created_at', 'updated_at', 'profile_version')
    ordering = ('-churn_risk_score',)
    list_select_related = ('user',)

    fieldsets = (
        ('User Info', {
            'fields': ('user', 'inactivity_days', 'last_active_at', 'last_login_at')
        }),
        ('Scores', {
            'fields': ('engagement_score', 'activity_score', 'retention_score',
                      'loyalty_score', 'notification_fatigue_score'),
            'classes': ('wide',),
        }),
        ('Risk Assessment', {
            'fields': ('churn_risk_score', 'risk_level', 'is_at_risk', 'risk_level_changed_at'),
            'classes': ('wide',),
        }),
        ('Behavior Stats', {
            'fields': ('total_logins', 'login_streak_days', 'longest_streak_days',
                      'total_orders', 'total_spent', 'avg_order_value'),
            'classes': ('wide',),
        }),
        ('Notification Stats', {
            'fields': ('total_notifications_sent', 'total_notifications_opened',
                      'total_notification_clicks', 'notification_open_rate',
                      'notification_ctr', 'optimal_notification_hour'),
            'classes': ('wide',),
        }),
        ('Location & Time', {
            'fields': ('timezone', 'city', 'province', 'preferred_hour_start',
                      'preferred_hour_end', 'peak_activity_hour'),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('computed_at', 'created_at', 'updated_at', 'profile_version'),
            'classes': ('collapse',),
        }),
    )

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'

    def user_role(self, obj):
        return obj.user.role
    user_role.short_description = 'Role'

    def fatigue_score(self, obj):
        return obj.notification_fatigue_score
    fatigue_score.short_description = 'Fatigue'

    def risk_level_colored(self, obj):
        colors = {
            'active': '#28a745',
            'at_risk': '#ffc107',
            'dormant': '#fd7e14',
            'churned': '#dc3545',
            'reactivated': '#17a2b8',
        }
        color = colors.get(obj.risk_level, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_risk_level_display()
        )
    risk_level_colored.short_description = 'Risk Level'
    risk_level_colored.admin_order_field = 'risk_level'


@admin.register(BehaviorEvent)
class BehaviorEventAdmin(admin.ModelAdmin):
    """Admin for behavioral events."""
    list_display = ('user_email', 'event_type', 'event_category', 'event_time',
                   'value', 'source', 'device_type')
    list_filter = ('event_type', 'event_category', 'source', 'device_type', 'event_time')
    search_fields = ('user__email', 'event_type', 'data')
    readonly_fields = ('event_time', 'created_at')
    date_hierarchy = 'event_time'
    ordering = ('-event_time',)
    list_select_related = ('user',)

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    """Admin for aggregated activity logs."""
    list_display = ('user_email', 'activity_type', 'period', 'count',
                   'duration_minutes', 'period_start', 'period_end')
    list_filter = ('activity_type', 'period')
    search_fields = ('user__email',)
    date_hierarchy = 'period_start'
    ordering = ('-period_start',)
    list_select_related = ('user',)

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'


@admin.register(ChurnPrediction)
class ChurnPredictionAdmin(admin.ModelAdmin):
    """Admin for churn predictions."""
    list_display = ('user_email', 'churn_probability_pct', 'churn_risk_category',
                   'recommended_action', 'computed_at', 'confidence_score')
    list_filter = ('churn_risk_category', 'recommended_action')
    search_fields = ('user__email',)
    readonly_fields = ('computed_at', 'created_at', 'updated_at')
    ordering = ('-churn_probability',)
    list_select_related = ('user',)

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'

    def churn_probability_pct(self, obj):
        return f'{obj.churn_probability:.1%}'
    churn_probability_pct.short_description = 'Churn Probability'


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    """Admin for device tokens."""
    list_display = ('user_email', 'platform', 'device_name', 'is_active',
                   'app_version', 'last_used_at', 'created_at')
    list_filter = ('platform', 'is_active')
    search_fields = ('user__email', 'device_name', 'token')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-last_used_at',)
    list_select_related = ('user',)

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """Admin for notification templates."""
    list_display = ('name', 'trigger_type_colored', 'channel', 'priority',
                   'use_ai_generation', 'ab_test_enabled', 'is_active', 'is_system')
    list_filter = ('trigger_type', 'channel', 'priority', 'is_active', 'use_ai_generation')
    search_fields = ('name', 'title_template', 'body_template')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('name',)

    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'trigger_type', 'channel', 'priority')
        }),
        ('Content Templates', {
            'fields': ('title_template', 'body_template', 'action_text_template', 'action_url_template'),
            'classes': ('wide',),
        }),
        ('AI Generation', {
            'fields': ('use_ai_generation', 'ai_temperature', 'ai_system_prompt'),
            'classes': ('wide',),
        }),
        ('Delivery Config', {
            'fields': ('icon', 'image_url', 'ttl_seconds', 'cooldown_hours', 'max_per_day'),
            'classes': ('wide',),
        }),
        ('A/B Testing', {
            'fields': ('ab_test_enabled', 'ab_test_variants'),
            'classes': ('collapse',),
        }),
        ('Status', {
            'fields': ('is_active', 'is_system'),
        }),
    )

    def trigger_type_colored(self, obj):
        return obj.get_trigger_type_display()
    trigger_type_colored.short_description = 'Psychological Trigger'


@admin.register(NotificationCampaign)
class NotificationCampaignAdmin(admin.ModelAdmin):
    """Admin for notification campaigns."""
    list_display = ('name', 'status_colored', 'target_type', 'target_count',
                   'channel', 'total_sent', 'total_opened', 'completion_bar',
                   'scheduled_at', 'created_at')
    list_filter = ('status', 'target_type', 'channel')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'total_sent', 'total_delivered',
                      'total_opened', 'total_clicked', 'total_converted')
    ordering = ('-created_at',)

    fieldsets = (
        ('Campaign Info', {
            'fields': ('name', 'description', 'template')
        }),
        ('Targeting', {
            'fields': ('target_type', 'target_filter', 'channel'),
            'classes': ('wide',),
        }),
        ('Scheduling', {
            'fields': ('status', 'scheduled_at', 'started_at', 'completed_at'),
            'classes': ('wide',),
        }),
        ('AI & Limits', {
            'fields': ('use_ai_personalization', 'max_notifications_per_user'),
        }),
        ('Results', {
            'fields': ('target_count', 'total_sent', 'total_delivered',
                      'total_opened', 'total_clicked', 'total_converted'),
            'classes': ('wide',),
        }),
        ('Audit', {
            'fields': ('created_by',),
            'classes': ('collapse',),
        }),
    )

    def status_colored(self, obj):
        colors = {
            'draft': '#6c757d',
            'scheduled': '#007bff',
            'running': '#28a745',
            'paused': '#ffc107',
            'completed': '#17a2b8',
            'cancelled': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_colored.short_description = 'Status'

    def completion_bar(self, obj):
        if obj.target_count > 0:
            pct = min(100, int((obj.total_sent / obj.target_count) * 100))
            bar_color = 'success' if pct >= 80 else ('warning' if pct >= 50 else 'info')
            return format_html(
                '<div style="width: 100px; background: #e9ecef; border-radius: 4px;">'
                '<div style="width: {}%; background: {}; height: 16px; border-radius: 4px; '
                'text-align: center; color: white; font-size: 10px; line-height: 16px;">{}%</div>'
                '</div>',
                pct,
                {'success': '#28a745', 'warning': '#ffc107', 'info': '#17a2b8'}.get(bar_color, '#6c757d'),
                pct
            )
        return '-'
    completion_bar.short_description = 'Progress'


@admin.register(NotificationQueue)
class NotificationQueueAdmin(admin.ModelAdmin):
    """Admin for notification queue."""
    list_display = ('id', 'user_email', 'title_short', 'trigger_type', 'status_colored',
                   'priority', 'psychological_trigger', 'scheduled_for', 'created_at')
    list_filter = ('status', 'trigger_type', 'priority', 'ai_generated', 'psychological_trigger')
    search_fields = ('user__email', 'title', 'body')
    readonly_fields = ('created_at', 'updated_at', 'delivered_at', 'opened_at',
                      'clicked_at', 'converted_at', 'retry_count')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    list_select_related = ('user',)

    fieldsets = (
        ('Notification Content', {
            'fields': ('title', 'body', 'action_url', 'action_text', 'icon', 'image_url')
        }),
        ('User & Trigger', {
            'fields': ('user', 'trigger_type', 'trigger_ref_id', 'campaign')
        }),
        ('AI Metadata', {
            'fields': ('psychological_trigger', 'ai_generated', 'ai_model_version',
                      'personalization_score'),
            'classes': ('wide',),
        }),
        ('Delivery', {
            'fields': ('channel', 'priority', 'scheduled_for', 'status', 'status_message'),
            'classes': ('wide',),
        }),
        ('Timestamps', {
            'fields': ('delivered_at', 'opened_at', 'clicked_at', 'converted_at',
                      'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
        ('A/B Testing', {
            'fields': ('ab_test_group', 'ab_test_variant'),
            'classes': ('collapse',),
        }),
    )

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'

    def title_short(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_short.short_description = 'Title'

    def status_colored(self, obj):
        colors = {
            'queued': '#007bff',
            'scheduled': '#6f42c1',
            'delivering': '#17a2b8',
            'delivered': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d',
            'expired': '#868e96',
            'rate_limited': '#ffc107',
            'cooldown': '#fd7e14',
            'duplicate': '#e83e8c',
            'quiet_hours': '#20c997',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_colored.short_description = 'Status'


@admin.register(NotificationAnalytics)
class NotificationAnalyticsAdmin(admin.ModelAdmin):
    """Admin for notification analytics."""
    list_display = ('user_email', 'period', 'period_start', 'total_sent',
                   'delivery_rate_pct', 'open_rate_pct', 'ctr_pct')
    list_filter = ('period',)
    search_fields = ('user__email',)
    date_hierarchy = 'period_start'
    list_select_related = ('user',)

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'

    def delivery_rate_pct(self, obj):
        return f'{obj.delivery_rate:.1%}'
    delivery_rate_pct.short_description = 'Delivery Rate'

    def open_rate_pct(self, obj):
        return f'{obj.open_rate:.1%}'
    open_rate_pct.short_description = 'Open Rate'

    def ctr_pct(self, obj):
        return f'{obj.click_through_rate:.1%}'
    ctr_pct.short_description = 'CTR'


@admin.register(NotificationDeliveryLog)
class NotificationDeliveryLogAdmin(admin.ModelAdmin):
    """Admin for delivery logs."""
    list_display = ('id', 'user_email', 'status', 'platform', 'sent_at',
                   'delivered_at', 'attempt_number', 'send_latency_ms')
    list_filter = ('status', 'platform', 'is_retry')
    search_fields = ('user__email',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'sent_at'
    list_select_related = ('user',)

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'


@admin.register(NotificationABTest)
class NotificationABTestAdmin(admin.ModelAdmin):
    """Admin for A/B tests."""
    list_display = ('name', 'status_colored', 'test_size', 'control_percentage',
                   'winning_variant', 'significance_level', 'started_at')
    list_filter = ('status',)
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at', 'results', 'winning_variant')

    def status_colored(self, obj):
        colors = {
            'draft': '#6c757d',
            'running': '#28a745',
            'completed': '#17a2b8',
            'cancelled': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_colored.short_description = 'Status'


@admin.register(QuietHoursConfig)
class QuietHoursConfigAdmin(admin.ModelAdmin):
    """Admin for quiet hours configuration."""
    list_display = ('user_email', 'quiet_hours_start', 'quiet_hours_end',
                   'global_cooldown_minutes', 'max_push_per_day',
                   'adaptive_frequency_enabled', 'use_ai_optimization')
    list_filter = ('adaptive_frequency_enabled', 'use_ai_optimization', 'weekend_quiet_mode')
    search_fields = ('user__email',)

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'


@admin.register(NotificationPreferenceExtension)
class NotificationPreferenceExtensionAdmin(admin.ModelAdmin):
    """Admin for extended notification preferences."""
    list_display = ('user_email', 'ai_optimization_enabled', 'ai_learning_enabled',
                   'personalization_level', 'do_not_disturb',
                   'push_engagement', 'push_recommendations')
    list_filter = ('ai_optimization_enabled', 'personalization_level', 'do_not_disturb')
    search_fields = ('user__email',)

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'


@admin.register(NotificationCooldown)
class NotificationCooldownAdmin(admin.ModelAdmin):
    """Admin for notification cooldowns."""
    list_display = ('user_email', 'trigger_type', 'last_sent_at', 'cooldown_until',
                   'sent_count_today', 'is_active_cooldown')
    list_filter = ('trigger_type',)
    search_fields = ('user__email',)
    list_select_related = ('user',)

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'

    def is_active_cooldown(self, obj):
        from django.utils import timezone
        is_active = timezone.now() < obj.cooldown_until
        return format_html(
            '<span style="color: {};">{}</span>',
            '#dc3545' if is_active else '#28a745',
            'Active' if is_active else 'Expired'
        )
    is_active_cooldown.short_description = 'Cooldown Active'


@admin.register(EngagementSignal)
class EngagementSignalAdmin(admin.ModelAdmin):
    """Admin for engagement signals."""
    list_display = ('name', 'signal_type', 'event_type', 'template_name',
                   'priority', 'cooldown_minutes', 'is_active')
    list_filter = ('signal_type', 'is_active', 'priority')
    search_fields = ('name', 'event_type')
    readonly_fields = ('created_at', 'updated_at')

    def template_name(self, obj):
        return obj.template.name if obj.template else '-'
    template_name.short_description = 'Template'
