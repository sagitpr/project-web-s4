"""
Refunds app models for Warungio Marketplace.
Complete Refund & Return management system.
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal


class Refund(models.Model):
    """Refund/Return request model."""
    
    REASON_CHOICES = [
        ('wrong_product', 'Produk Tidak Sesuai'),
        ('product_damaged', 'Produk Rusak/Cacat'),
        ('not_as_described', 'Tidak Sesuai Deskripsi'),
        ('expired', 'Produk Kadaluarsa'),
        ('missing_items', 'Barang Kurang'),
        ('defective', 'Produk Cacat'),
        ('change_mind', 'Berubah Pikiran'),
        ('other', 'Lainnya'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Menunggu Review'),
        ('under_review', 'Sedang Ditinjau'),
        ('waiting_buyer', 'Menunggu Pembeli'),
        ('waiting_seller', 'Menunggu Penjual'),
        ('approved', 'Disetujui'),
        ('rejected', 'Ditolak'),
        ('cancelled', 'Dibatalkan'),
        ('refunded', 'Telah Direfund'),
        ('partial_refund', 'Refund Sebagian'),
    ]
    
    RESOLUTION_CHOICES = [
        ('full_refund', 'Refund Penuh'),
        ('partial_refund', 'Refund Sebagian'),
        ('replacement', 'Penggantian Barang'),
        ('store_credit', 'Kredit Toko'),
        ('no_refund', 'Tidak Ada Refund'),
    ]
    
    # Identifiers
    refund_number = models.CharField(max_length=30, unique=True, blank=True, verbose_name='No. Refund')
    order = models.ForeignKey(
        'orders.Order', on_delete=models.CASCADE,
        related_name='refunds', verbose_name='Pesanan'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='refunds', verbose_name='Pembeli'
    )
    store = models.ForeignKey(
        'stores.Store', on_delete=models.SET_NULL,
        null=True, related_name='refunds', verbose_name='Toko'
    )
    
    # Refund Details
    reason = models.CharField(
        max_length=30, choices=REASON_CHOICES,
        default='other', verbose_name='Alasan Refund'
    )
    reason_text = models.TextField(blank=True, null=True, verbose_name='Penjelasan Alasan')
    amount_requested = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Jumlah Diminta'
    )
    amount_approved = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True, verbose_name='Jumlah Disetujui'
    )
    
    # Status
    refund_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='pending', verbose_name='Status Refund'
    )
    resolution = models.CharField(
        max_length=20, choices=RESOLUTION_CHOICES,
        null=True, blank=True, verbose_name='Resolusi'
    )
    
    # Evidence
    evidence_images = models.JSONField(
        blank=True, default=list, verbose_name='Bukti Foto/Video',
        help_text='List of uploaded image URLs'
    )
    evidence_description = models.TextField(
        blank=True, null=True, verbose_name='Deskripsi Bukti'
    )
    
    # Notes
    buyer_notes = models.TextField(blank=True, null=True, verbose_name='Catatan Pembeli')
    seller_notes = models.TextField(blank=True, null=True, verbose_name='Catatan Penjual')
    admin_notes = models.TextField(blank=True, null=True, verbose_name='Catatan Admin')
    
    # Items to refund (JSON: list of item IDs and qty)
    refund_items = models.JSONField(
        blank=True, default=list, verbose_name='Item yang Direfund',
        help_text='[{"item_id": 1, "qty": 2, "product_name": "Bayam Segar"}]'
    )
    
    # Metadata
    is_escalated = models.BooleanField(default=False, verbose_name='Dirujuk ke Admin')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='Waktu Selesai')

    class Meta:
        db_table = 'refunds'
        verbose_name = 'Refund'
        verbose_name_plural = 'Refund'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'refund_status']),
            models.Index(fields=['user', 'refund_status']),
            models.Index(fields=['store', 'refund_status']),
            models.Index(fields=['refund_number']),
            models.Index(fields=['refund_status']),
        ]

    def __str__(self):
        return f'Refund #{self.refund_number}'

    def save(self, *args, **kwargs):
        if not self.refund_number:
            import uuid
            self.refund_number = f'RFN-{uuid.uuid4().hex[:8].upper()}'
        super().save(*args, **kwargs)


class RefundTimelineEvent(models.Model):
    """Timeline events for refund lifecycle tracking."""
    
    EVENT_TYPE_CHOICES = [
        ('created', 'Refund Diajukan'),
        ('review_started', 'Review Dimulai'),
        ('seller_responded', 'Penjual Merespon'),
        ('buyer_responded', 'Pembeli Merespon'),
        ('approved', 'Refund Disetujui'),
        ('rejected', 'Refund Ditolak'),
        ('cancelled', 'Refund Dibatalkan'),
        ('refunded', 'Dana Direfund'),
        ('partial_refunded', 'Refund Sebagian'),
        ('escalated', 'Dirujuk ke Admin'),
        ('admin_intervened', 'Admin Turun Tangan'),
        ('resolved', 'Selesai'),
        ('evidence_added', 'Bukti Ditambahkan'),
        ('note_added', 'Catatan Ditambahkan'),
        ('negotiated', 'Negosiasi Harga'),
    ]
    
    refund = models.ForeignKey(
        Refund, on_delete=models.CASCADE,
        related_name='timeline', verbose_name='Refund'
    )
    event_type = models.CharField(
        max_length=30, choices=EVENT_TYPE_CHOICES,
        verbose_name='Tipe Kejadian'
    )
    description = models.TextField(verbose_name='Deskripsi')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Dibuat Oleh'
    )
    created_by_role = models.CharField(
        max_length=20, blank=True, null=True,
        verbose_name='Peran Pembuat'
    )
    metadata = models.JSONField(blank=True, default=dict, verbose_name='Data Tambahan')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'refund_timeline'
        verbose_name = 'Kejadian Timeline Refund'
        verbose_name_plural = 'Kejadian Timeline Refund'
        ordering = ['created_at']

    def __str__(self):
        refund_num = getattr(self.refund, 'refund_number', 'N/A') if self.refund_id else 'N/A'
        return f'{self.get_event_type_display()} - Refund #{refund_num}'
