"""
Analytics serializers for Warungio Marketplace.
Dashboard real-time analytics.
"""

from rest_framework import serializers
from .models import SalesAnalytics, DeviceAnalytics, UserActivity, DailyReport
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.openapi import OpenApiTypes


class SalesAnalyticsSerializer(serializers.ModelSerializer):
    """Sales analytics data serializer."""
    revenue_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = SalesAnalytics
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    @extend_schema_field(OpenApiTypes.STR)
    def get_revenue_formatted(self, obj):
        return f"Rp {obj.total_sales:,.0f}"


class SalesSummarySerializer(serializers.Serializer):
    """Sales summary for dashboard cards."""
    total_sales = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_orders = serializers.IntegerField()
    total_products_sold = serializers.IntegerField()
    total_revenue_growth = serializers.DecimalField(max_digits=5, decimal_places=2)
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    new_customers = serializers.IntegerField()
    period = serializers.CharField()


class SalesTrendSerializer(serializers.Serializer):
    """Sales trend data for charts."""
    labels = serializers.ListField(child=serializers.CharField())
    daily_sales = serializers.ListField(child=serializers.DecimalField(max_digits=15, decimal_places=2))
    daily_orders = serializers.ListField(child=serializers.IntegerField())
    daily_customers = serializers.ListField(child=serializers.IntegerField())


class DeviceAnalyticsSerializer(serializers.ModelSerializer):
    """Device analytics serializer."""
    class Meta:
        model = DeviceAnalytics
        fields = '__all__'


class DeviceBreakdownSerializer(serializers.Serializer):
    """Device usage breakdown for charts."""
    mobile_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    tablet_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    desktop_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    mobile_count = serializers.IntegerField()
    tablet_count = serializers.IntegerField()
    desktop_count = serializers.IntegerField()


class UserActivitySerializer(serializers.ModelSerializer):
    """User activity log serializer."""
    user_name = serializers.CharField(source='user.full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = UserActivity
        fields = '__all__'
        read_only_fields = ('created_at',)


class DailyReportSerializer(serializers.ModelSerializer):
    """Daily report serializer."""
    class Meta:
        model = DailyReport
        fields = '__all__'
        read_only_fields = ('generated_at',)


class DashboardStatsSerializer(serializers.Serializer):
    """Complete dashboard statistics."""
    total_sales = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_orders = serializers.IntegerField()
    products_sold = serializers.IntegerField()
    new_customers = serializers.IntegerField()
    total_followers = serializers.IntegerField()
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    total_products = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    
    sales_chart = SalesTrendSerializer()
    device_breakdown = DeviceBreakdownSerializer()
    recent_orders = serializers.ListField(child=serializers.DictField())
    top_products = serializers.ListField(child=serializers.DictField())
