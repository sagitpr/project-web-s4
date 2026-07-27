"""
Notifications serializers for Warungio Marketplace.
"""

from rest_framework import serializers
from .models import Notification, NotificationPreference
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.openapi import OpenApiTypes


class NotificationSerializer(serializers.ModelSerializer):
    """User notification serializer with type metadata."""
    time_ago = serializers.SerializerMethodField()
    type_icon = serializers.ReadOnlyField()
    type_color = serializers.ReadOnlyField()
    priority_icon = serializers.ReadOnlyField()

    class Meta:
        model = Notification
        fields = ('id', 'user', 'notification_type', 'priority', 'title',
                  'description', 'action_url', 'action_text', 'icon', 'image',
                  'is_read', 'read_at', 'is_archived', 'metadata',
                  'type_icon', 'type_color', 'priority_icon',
                  'time_ago', 'created_at', 'updated_at')
        read_only_fields = ('user', 'is_read', 'read_at', 'is_archived',
                           'created_at', 'updated_at', 'time_ago',
                           'type_icon', 'type_color', 'priority_icon')

    @extend_schema_field(OpenApiTypes.STR)
    def get_time_ago(self, obj):
        from django.utils import timezone
        now = timezone.now()
        diff = now - obj.created_at
        if diff.days > 0:
            return f"{diff.days} hari yang lalu"
        if diff.seconds >= 3600:
            return f"{diff.seconds // 3600} jam yang lalu"
        if diff.seconds >= 60:
            return f"{diff.seconds // 60} menit yang lalu"
        return "Baru saja"


class NotificationMarkReadSerializer(serializers.Serializer):
    """Mark notifications as read."""
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False
    )
    mark_all = serializers.BooleanField(default=False)


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = '__all__'
        read_only_fields = ('user', 'updated_at')


class NotificationCountSerializer(serializers.Serializer):
    """Unread notification count serializer with full type breakdown."""
    total_unread = serializers.IntegerField()
    order_unread = serializers.IntegerField()
    payment_unread = serializers.IntegerField()
    chat_unread = serializers.IntegerField()
    promo_unread = serializers.IntegerField()
    system_unread = serializers.IntegerField()
    inventory_unread = serializers.IntegerField()
    security_unread = serializers.IntegerField()
    delivery_unread = serializers.IntegerField()
    wallet_unread = serializers.IntegerField()
    loyalty_unread = serializers.IntegerField()
    ai_scan_unread = serializers.IntegerField()


class NotificationArchiveSerializer(serializers.Serializer):
    """Archive or unarchive notifications."""
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(), required=True
    )
    archive = serializers.BooleanField(default=True)


class NotificationBroadcastSerializer(serializers.Serializer):
    """Admin broadcast notification serializer."""
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    target_role = serializers.ChoiceField(
        choices=['all', 'buyer', 'seller', 'admin'],
        default='all'
    )
    notification_type = serializers.ChoiceField(
        choices=[t[0] for t in Notification.NOTIFICATION_TYPES],
        default='system'
    )
    action_url = serializers.CharField(max_length=500, required=False, allow_blank=True)
    action_text = serializers.CharField(max_length=100, required=False, default='Lihat')
