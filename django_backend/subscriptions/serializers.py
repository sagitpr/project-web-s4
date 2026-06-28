"""Subscription serializers for Warungio Marketplace."""

from rest_framework import serializers
from .models import Subscription


class SubscriptionSerializer(serializers.ModelSerializer):
    """Subscription serializer."""
    user_name = serializers.CharField(source='user.full_name', read_only=True, allow_null=True)
    store_name = serializers.CharField(source='store.store_name', read_only=True, allow_null=True)
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = ('id', 'user', 'user_name', 'store', 'store_name',
                  'package_name', 'start_date', 'end_date', 'status',
                  'auto_renew', 'amount_paid', 'payment_method', 'notes',
                  'is_expired', 'created_at', 'updated_at')
        read_only_fields = ('user', 'created_at', 'updated_at')

    def get_is_expired(self, obj):
        return obj.is_expired()
