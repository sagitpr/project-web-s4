"""
Monitoring serializers for Warungio Marketplace.
"""

from rest_framework import serializers
from .models import SystemHealth, PerformanceMetric, UptimeRecord, ErrorLog, ScheduledTask


class ErrorLogSerializer(serializers.ModelSerializer):
    """Error log serializer."""

    class Meta:
        model = ErrorLog
        fields = '__all__'
        read_only_fields = ['created_at']


class SystemHealthSerializer(serializers.ModelSerializer):
    """System health serializer."""

    class Meta:
        model = SystemHealth
        fields = '__all__'
        read_only_fields = ['checked_at']


class PerformanceMetricSerializer(serializers.ModelSerializer):
    """Performance metric serializer."""

    class Meta:
        model = PerformanceMetric
        fields = '__all__'
        read_only_fields = ['recorded_at']
