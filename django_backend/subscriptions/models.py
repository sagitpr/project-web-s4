"""Subscription plan models for seller subscriptions."""

from django.db import models
from django.conf import settings


class Subscription(models.Model):
    """Seller subscription plan model."""
    PACKAGE_CHOICES = [
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('enterprise', 'Enterprise'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='subscriptions',
        verbose_name='Pengguna'
    )
    store = models.ForeignKey(
        'stores.Store', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='subscriptions',
        verbose_name='Toko'
    )
    package_name = models.CharField(
        max_length=100, choices=PACKAGE_CHOICES,
        default='free', verbose_name='Paket'
    )
    start_date = models.DateField(verbose_name='Tanggal Mulai')
    end_date = models.DateField(verbose_name='Tanggal Berakhir')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='active',
        verbose_name='Status'
    )
    auto_renew = models.BooleanField(default=False, verbose_name='Perpanjang Otomatis')
    amount_paid = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Jumlah Dibayar'
    )
    payment_method = models.CharField(
        max_length=50, blank=True, null=True, verbose_name='Metode Pembayaran'
    )
    notes = models.TextField(blank=True, null=True, verbose_name='Catatan')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subscriptions'
        verbose_name = 'Langganan'
        verbose_name_plural = 'Langganan'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['store']),
            models.Index(fields=['status']),
            models.Index(fields=['end_date']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.package_name} - {self.user.full_name if self.user else "N/A"} ({self.status})'

    def is_expired(self):
        from django.utils import timezone
        return timezone.now().date() > self.end_date
