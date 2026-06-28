"""
Notifications serializers for Warungio Marketplace.
"""

from rest_framework import serializers
from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    """User notification serializer."""
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ('id', 'user', 'notification_type', 'priority', 'title',
                  'description', 'action_url', 'action_text', 'icon', 'image',
                  'is_read', 'read_at', 'time_ago', 'created_at')
        read_only_fields = ('user', 'is_read', 'read_at', 'created_at', 'time_ago')

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
    """Unread notification count serializer."""
    total_unread = serializers.IntegerField()
    order_unread = serializers.IntegerField()
    chat_unread = serializers.IntegerField()
    promo_unread = serializers.IntegerField()
    system_unread = serializers.IntegerField()
