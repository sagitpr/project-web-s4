"""
Analytics app models for Warungio Marketplace.
Real-time dashboard analytics tracking.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone


class SalesAnalytics(models.Model):
    """Daily sales analytics aggregated per store."""
    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='sales_analytics'
    )
    date = models.DateField()
    
    # Revenue metrics
    total_sales = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_orders = models.IntegerField(default=0)
    total_products_sold = models.IntegerField(default=0)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Customer metrics
    new_customers = models.IntegerField(default=0)
    returning_customers = models.IntegerField(default=0)
    
    # Hourly breakdown (JSON)
    hourly_sales = models.JSONField(default=dict, blank=True)
    hourly_orders = models.JSONField(default=list, blank=True)
    
    # Payment breakdown
    payment_methods = models.JSONField(default=dict, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'sales_analytics'
        verbose_name = 'Analitik Penjualan'
        verbose_name_plural = 'Analitik Penjualan'
        unique_together = ['store', 'date']
        indexes = [
            models.Index(fields=['store', 'date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f'Sales {self.store.store_name} - {self.date}'


class DeviceAnalytics(models.Model):
    """Device usage analytics for user sessions."""
    DEVICE_TYPES = [
        ('mobile', 'Mobile'),
        ('tablet', 'Tablet'),
        ('desktop', 'Desktop'),
    ]

    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='device_analytics', null=True, blank=True
    )
    date = models.DateField()
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES)
    browser = models.CharField(max_length=50, blank=True, null=True)
    os = models.CharField(max_length=50, blank=True, null=True)
    visitors_count = models.IntegerField(default=0)
    page_views = models.IntegerField(default=0)
    bounce_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        db_table = 'device_analytics'
        verbose_name = 'Analitik Perangkat'
        verbose_name_plural = 'Analitik Perangkat'
        indexes = [
            models.Index(fields=['store', 'date']),
        ]

    def __str__(self):
        return f'{self.device_type} - {self.date}'


class UserActivity(models.Model):
    """Track user activities for analytics."""
    ACTIVITY_TYPES = [
        ('page_view', 'Page View'),
        ('search', 'Search'),
        ('add_to_cart', 'Add to Cart'),
        ('checkout', 'Checkout'),
        ('purchase', 'Purchase'),
        ('review', 'Review'),
        ('follow_store', 'Follow Store'),
        ('share', 'Share'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='activities'
    )
    store = models.ForeignKey(
        'stores.Store', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='visitor_activities'
    )
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    device_type = models.CharField(max_length=20, blank=True, null=True)
    page_url = models.TextField(blank=True, null=True)
    referrer = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_activities'
        verbose_name = 'Aktivitas Pengguna'
        verbose_name_plural = 'Aktivitas Pengguna'
        indexes = [
            models.Index(fields=['store', 'activity_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['activity_type']),
        ]

    def __str__(self):
        return f'{self.activity_type} - {self.created_at}'


class DailyReport(models.Model):
    """Daily summary report for seller dashboard."""
    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='daily_reports'
    )
    date = models.DateField()
    
    # Summary metrics
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_orders = models.IntegerField(default=0)
    total_products_sold = models.IntegerField(default=0)
    new_customers_count = models.IntegerField(default=0)
    total_visitors = models.IntegerField(default=0)
    
    # Best performers
    top_product_id = models.IntegerField(null=True, blank=True)
    top_product_name = models.CharField(max_length=150, blank=True, null=True)
    top_product_sales = models.IntegerField(default=0)
    
    # Performance indicators
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    revenue_growth = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Status
    is_completed = models.BooleanField(default=False)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'daily_reports'
        verbose_name = 'Laporan Harian'
        verbose_name_plural = 'Laporan Harian'
        unique_together = ['store', 'date']

    def __str__(self):
        return f'Report {self.store.store_name} - {self.date}'
