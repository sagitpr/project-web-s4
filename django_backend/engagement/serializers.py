"""
REST API serializers for Engagement & Retention Engine.
"""

from rest_framework import serializers
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.openapi import OpenApiTypes

from engagement.models import (
    UserBehaviorProfile, BehaviorEvent, ActivityLog,
    ChurnPrediction, DeviceToken, NotificationTemplate,
    NotificationCampaign, NotificationQueue, NotificationAnalytics,
    NotificationDeliveryLog, NotificationABTest, QuietHoursConfig,
    NotificationPreferenceExtension, NotificationCooldown, EngagementSignal,
)


class UserBehaviorProfileSerializer(serializers.ModelSerializer):
    """User behavior profile with computed scores."""

    class Meta:
        model = UserBehaviorProfile
        exclude = ('user', 'profile_version', 'created_at', 'updated_at')
        read_only_fields = [f.name for f in UserBehaviorProfile._meta.fields if f.name != 'id']


class BehaviorEventSerializer(serializers.ModelSerializer):
    """Behavior event serializer."""
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = BehaviorEvent
        fields = '__all__'
        read_only_fields = ('created_at',)

    @extend_schema_field(OpenApiTypes.STR)
    def get_time_ago(self, obj):
        now = timezone.now()
        diff = now - obj.event_time
        if diff.days > 0:
            return f"{diff.days} hari yang lalu"
        if diff.seconds >= 3600:
            return f"{diff.seconds // 3600} jam yang lalu"
        if diff.seconds >= 60:
            return f"{diff.seconds // 60} menit yang lalu"
        return "Baru saja"


class ActivityLogSerializer(serializers.ModelSerializer):
    """Activity log serializer."""

    class Meta:
        model = ActivityLog
        fields = '__all__'
        read_only_fields = ('created_at',)


class ChurnPredictionSerializer(serializers.ModelSerializer):
    """Churn prediction serializer."""
    churn_probability_pct = serializers.SerializerMethodField()

    class Meta:
        model = ChurnPrediction
        exclude = ('user', 'model_version', 'confidence_score', 'features_used')

    def get_churn_probability_pct(self, obj):
        return round(obj.churn_probability * 100, 1)


class DeviceTokenSerializer(serializers.ModelSerializer):
    """Device token serializer."""

    class Meta:
        model = DeviceToken
        fields = ('id', 'platform', 'token', 'device_name', 'device_id',
                  'app_version', 'is_active', 'created_at')
        read_only_fields = ('is_active', 'created_at')


class DeviceTokenRegisterSerializer(serializers.Serializer):
    """Device token registration serializer."""
    platform = serializers.ChoiceField(choices=DeviceToken.PLATFORM_CHOICES)
    token = serializers.CharField(max_length=2000)
    device_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    device_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    app_version = serializers.CharField(max_length=20, required=False, allow_blank=True)


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Notification template serializer."""

    class Meta:
        model = NotificationTemplate
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class NotificationCampaignSerializer(serializers.ModelSerializer):
    """Campaign serializer with computed stats."""
    completion_pct = serializers.SerializerMethodField()

    class Meta:
        model = NotificationCampaign
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'total_sent', 'total_delivered',
                           'total_opened', 'total_clicked', 'total_converted',
                           'started_at', 'completed_at', 'target_count')

    @extend_schema_field(OpenApiTypes.STR)


    def get_completion_pct(self, obj):
        if obj.target_count > 0:
            return round((obj.total_sent / obj.target_count) * 100, 1)
        return 0


class NotificationQueueSerializer(serializers.ModelSerializer):
    """Notification queue item serializer."""
    time_ago = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = NotificationQueue
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'retry_count', 'delivered_at',
                           'opened_at', 'clicked_at', 'converted_at')

    @extend_schema_field(OpenApiTypes.STR)
    def get_time_ago(self, obj):
        now = timezone.now()
        diff = now - obj.created_at
        if diff.days > 0:
            return f"{diff.days} hari yang lalu"
        if diff.seconds >= 3600:
            return f"{diff.seconds // 3600} jam yang lalu"
        if diff.seconds >= 60:
            return f"{diff.seconds // 60} menit yang lalu"
        return "Baru saja"


class NotificationAnalyticsSerializer(serializers.ModelSerializer):
    """Notification analytics serializer."""

    class Meta:
        model = NotificationAnalytics
        fields = '__all__'
        read_only_fields = ('created_at',)


class NotificationDeliveryLogSerializer(serializers.ModelSerializer):
    """Delivery log serializer."""

    class Meta:
        model = NotificationDeliveryLog
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class NotificationABTestSerializer(serializers.ModelSerializer):
    """A/B test serializer."""

    class Meta:
        model = NotificationABTest
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'results', 'winning_variant',
                           'significance_level')


class QuietHoursConfigSerializer(serializers.ModelSerializer):
    """Quiet hours configuration serializer."""

    class Meta:
        model = QuietHoursConfig
        exclude = ('user', 'created_at', 'updated_at')


class NotificationPreferenceExtensionSerializer(serializers.ModelSerializer):
    """Extended notification preferences serializer."""

    class Meta:
        model = NotificationPreferenceExtension
        exclude = ('user', 'created_at', 'updated_at')


class EngagementSignalSerializer(serializers.ModelSerializer):
    """Engagement signal configuration serializer."""

    class Meta:
        model = EngagementSignal
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


# ── Dashboard-specific serializers ──

class EngagementDashboardSerializer(serializers.Serializer):
    """Dashboard overview serializer."""
    total_active_users = serializers.IntegerField()
    total_at_risk_users = serializers.IntegerField()
    total_dormant_users = serializers.IntegerField()
    avg_engagement_score = serializers.FloatField()
    avg_retention_score = serializers.FloatField()
    avg_churn_risk = serializers.FloatField()
    total_queued_notifications = serializers.IntegerField()
    total_delivered_today = serializers.IntegerField()
    delivery_rate = serializers.FloatField()
    open_rate = serializers.FloatField()
    ctr = serializers.FloatField()
    queue_health = serializers.DictField()


class UserEngagementSummarySerializer(serializers.Serializer):
    """Single user engagement summary."""
    user_id = serializers.IntegerField()
    email = serializers.EmailField()
    full_name = serializers.CharField()
    role = serializers.CharField()
    engagement_score = serializers.FloatField()
    activity_score = serializers.FloatField()
    retention_score = serializers.FloatField()
    loyalty_score = serializers.FloatField()
    churn_risk_score = serializers.FloatField()
    fatigue_score = serializers.FloatField()
    risk_level = serializers.CharField()
    last_active = serializers.DateTimeField()
    total_orders = serializers.IntegerField()
    total_notifications_sent = serializers.IntegerField()
    notification_open_rate = serializers.FloatField()
    optimal_hour = serializers.IntegerField()
