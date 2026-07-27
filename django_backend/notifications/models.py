"""
Notifications app models for Warungio Marketplace.
"""

from django.db import models
from django.conf import settings


class Notification(models.Model):
    """User notification model."""
    NOTIFICATION_TYPES = [
        ('order', 'Order'),
        ('payment', 'Payment'),
        ('chat', 'Chat'),
        ('promo', 'Promo'),
        ('system', 'System'),
        ('follow', 'Follow'),
        ('review', 'Review'),
        ('product', 'Product'),
        ('inventory', 'Inventory'),
        ('ai_scan', 'AI Scan'),
        ('flash_sale', 'Flash Sale'),
        ('loyalty', 'Loyalty'),
        ('voucher', 'Voucher'),
        ('security', 'Security'),
        ('delivery', 'Delivery'),
        ('wallet', 'Wallet'),
        ('report', 'Report'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
        ('info', 'Info'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]

    PRIORITY_ICONS = {
        'info': 'fa-circle-info',
        'success': 'fa-circle-check',
        'warning': 'fa-triangle-exclamation',
        'critical': 'fa-circle-exclamation',
    }

    TYPE_ICONS = {
        'order': 'fa-bag-shopping',
        'payment': 'fa-credit-card',
        'chat': 'fa-comment-dots',
        'promo': 'fa-tag',
        'system': 'fa-gear',
        'follow': 'fa-user-plus',
        'review': 'fa-star',
        'product': 'fa-box',
        'inventory': 'fa-warehouse',
        'ai_scan': 'fa-camera',
        'flash_sale': 'fa-bolt',
        'loyalty': 'fa-gem',
        'voucher': 'fa-ticket',
        'security': 'fa-shield-halved',
        'delivery': 'fa-truck',
        'wallet': 'fa-wallet',
        'report': 'fa-chart-simple',
    }

    TYPE_COLORS = {
        'order': '#2563eb',
        'payment': '#16a34a',
        'chat': '#7c3aed',
        'promo': '#d97706',
        'system': '#64748b',
        'follow': '#0891b2',
        'review': '#f59e0b',
        'product': '#4f46e5',
        'inventory': '#0f766e',
        'ai_scan': '#db2777',
        'flash_sale': '#dc2626',
        'loyalty': '#9333ea',
        'voucher': '#ca8a04',
        'security': '#b91c1c',
        'delivery': '#0284c7',
        'wallet': '#059669',
        'report': '#6366f1',
    }

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=20, choices=NOTIFICATION_TYPES, default='system'
    )
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default='medium'
    )
    
    # Content
    title = models.CharField(max_length=255, verbose_name='Judul')
    description = models.TextField(blank=True, null=True, verbose_name='Deskripsi')
    
    # Action
    action_url = models.CharField(max_length=500, blank=True, null=True)
    action_text = models.CharField(max_length=100, blank=True, null=True)
    
    # Icon/Image
    icon = models.CharField(max_length=100, blank=True, null=True)
    image = models.ImageField(
        upload_to='notifications/', blank=True, null=True
    )
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notifications'
        verbose_name = 'Notifikasi'
        verbose_name_plural = 'Notifikasi'
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'notification_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'{self.title} - {self.user.email}'

    @property
    def type_icon(self):
        return self.TYPE_ICONS.get(self.notification_type, 'fa-bell')

    @property
    def type_color(self):
        return self.TYPE_COLORS.get(self.notification_type, '#64748b')

    @property
    def priority_icon(self):
        return self.PRIORITY_ICONS.get(self.priority, 'fa-circle-info')

    def mark_as_read(self):
        from django.utils import timezone
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])


class NotificationPreference(models.Model):
    """User notification preferences."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notification_prefs'
    )
    
    # Push notifications
    push_orders = models.BooleanField(default=True)
    push_payments = models.BooleanField(default=True)
    push_chat = models.BooleanField(default=True)
    push_promos = models.BooleanField(default=True)
    push_system = models.BooleanField(default=True)
    
    # Email notifications
    email_orders = models.BooleanField(default=True)
    email_payments = models.BooleanField(default=True)
    email_promos = models.BooleanField(default=False)
    email_digest = models.BooleanField(default=False)
    
    # SMS notifications
    sms_orders = models.BooleanField(default=False)
    sms_payments = models.BooleanField(default=True)
    sms_otp = models.BooleanField(default=True)
    
    # Quiet hours
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_preferences'
        verbose_name = 'Preferensi Notifikasi'
        verbose_name_plural = 'Preferensi Notifikasi'

    def __str__(self):
        return f'Notification prefs for {self.user.email}'
