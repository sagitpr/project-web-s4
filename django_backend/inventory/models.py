"""
Inventory management models for Warungio Marketplace.
Master product database with barcode lookup, batch tracking,
expiry management, FEFO (First Expired First Out) support,
and AI Smart Inventory Scanning.
"""

from datetime import timedelta, date
from decimal import Decimal

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import Sum, Q


class MasterProduct(models.Model):
    """
    Master product database — canonical product reference.
    Scanned barcodes look up this table to auto-populate product info.
    """
    UNIT_CHOICES = [
        ('pcs', 'Piece'),
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('liter', 'Liter'),
        ('ml', 'Mililiter'),
        ('pack', 'Pack'),
        ('dus', 'Dus (Karton)'),
        ('karung', 'Karung'),
        ('botol', 'Botol'),
        ('kaleng', 'Kaleng'),
        ('sachet', 'Sachet'),
        ('box', 'Box'),
    ]

    barcode = models.CharField(
        max_length=13, unique=True, db_index=True,
        verbose_name='Barcode (EAN-13)',
        help_text='13-digit EAN-13 barcode number'
    )
    product_name = models.CharField(max_length=200, verbose_name='Nama Produk')
    brand = models.CharField(max_length=100, blank=True, verbose_name='Merek')
    category = models.CharField(
        max_length=100, db_index=True, verbose_name='Kategori',
        help_text='Seperti: Makanan, Minuman, Sembako, Produk Rumah Tangga'
    )
    subcategory = models.CharField(
        max_length=100, blank=True, verbose_name='Subkategori'
    )
    unit = models.CharField(
        max_length=20, choices=UNIT_CHOICES, default='pcs',
        verbose_name='Satuan'
    )
    weight_value = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name='Berat/Volume',
        help_text='Berat bersih dalam gram atau volume dalam ml'
    )
    weight_unit = models.CharField(
        max_length=10, blank=True, verbose_name='Satuan Berat',
        help_text='g, kg, ml, liter'
    )
    image_url = models.URLField(
        blank=True, verbose_name='URL Gambar',
        help_text='Product image URL from barcode database'
    )
    manufacturer = models.CharField(
        max_length=200, blank=True, verbose_name='Produsen'
    )
    bpom_number = models.CharField(
        max_length=30, blank=True, verbose_name='Nomor BPOM',
        help_text='BPOM/POM registration number for Indonesian products'
    )
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventory_master_product'
        verbose_name = 'Master Produk'
        verbose_name_plural = 'Master Produk'
        ordering = ['product_name']
        indexes = [
            models.Index(fields=['barcode']),
            models.Index(fields=['product_name']),
            models.Index(fields=['category']),
            models.Index(fields=['brand']),
        ]

    def __str__(self):
        return f"{self.product_name} ({self.barcode})"


class ProductBatch(models.Model):
    """
    Product batch/lot tracking with expiry management.
    Each batch is a specific production run with its own expiry date.
    """
    STATUS_CHOICES = [
        ('fresh', 'Fresh'),
        ('expiring_soon', 'Expiring Soon'),
        ('expired', 'Expired'),
        ('disposed', 'Disposed'),
    ]

    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='product_batches', verbose_name='Toko'
    )
    master_product = models.ForeignKey(
        MasterProduct, on_delete=models.CASCADE,
        related_name='batches', verbose_name='Master Produk'
    )
    product = models.ForeignKey(
        'products.Product', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='batches',
        verbose_name='Product Listing'
    )
    batch_number = models.CharField(
        max_length=100, verbose_name='Nomor Batch/Lot',
        help_text='Batch number from manufacturer'
    )
    production_date = models.DateField(
        verbose_name='Tanggal Produksi'
    )
    expiry_date = models.DateField(
        verbose_name='Tanggal Kadaluwarsa'
    )
    initial_quantity = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Jumlah Awal'
    )
    current_quantity = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Jumlah Tersisa'
    )
    unit = models.CharField(
        max_length=20, default='pcs', verbose_name='Satuan'
    )
    purchase_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='Harga Beli',
        help_text='Purchase price per unit'
    )
    
    # Auto-calculated shelf life
    shelf_life_days = models.IntegerField(
        editable=False, verbose_name='Masa Simpan (hari)'
    )
    shelf_life_remaining_pct = models.DecimalField(
        max_digits=5, decimal_places=2, editable=False,
        default=100.00, verbose_name='Sisa Masa Simpan (%)'
    )
    
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='fresh', db_index=True, verbose_name='Status'
    )
    notes = models.TextField(blank=True, verbose_name='Catatan')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventory_product_batch'
        verbose_name = 'Batch Produk'
        verbose_name_plural = 'Batch Produk'
        ordering = ['expiry_date', 'batch_number']
        indexes = [
            models.Index(fields=['store', 'status']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['batch_number']),
            models.Index(fields=['master_product', 'expiry_date']),
        ]

    def __str__(self):
        return (
            f"Batch {self.batch_number} - {self.master_product.product_name} "
            f"(exp: {self.expiry_date})"
        )

    def save(self, *args, **kwargs):
        """Auto-calculate shelf life and status on save."""
        today = timezone.now().date()

        # Calculate total shelf life in days
        if self.production_date and self.expiry_date:
            delta = self.expiry_date - self.production_date
            self.shelf_life_days = delta.days if delta.days > 0 else 0

            # Calculate remaining percentage
            total_shelf = self.shelf_life_days
            if total_shelf > 0:
                days_elapsed = (today - self.production_date).days
                remaining = max(0, total_shelf - days_elapsed)
                self.shelf_life_remaining_pct = round(
                    (remaining / total_shelf) * 100, 2
                )
            else:
                self.shelf_life_remaining_pct = Decimal('0.00')
        else:
            self.shelf_life_days = 0
            self.shelf_life_remaining_pct = Decimal('0.00')

        # Auto-determine status
        self.status = self._calculate_status(today)

        super().save(*args, **kwargs)

    def _calculate_status(self, today=None):
        """Calculate batch status based on expiry date."""
        if today is None:
            today = timezone.now().date()

        if self.current_quantity <= 0:
            return 'disposed'

        if self.expiry_date < today:
            return 'expired'

        days_until_expiry = (self.expiry_date - today).days
        if days_until_expiry <= 30:
            return 'expiring_soon'

        return 'fresh'

    def refresh_status(self):
        """Re-calculate and save status (for scheduled tasks)."""
        today = timezone.now().date()
        self.status = self._calculate_status(today)
        self.save(update_fields=['status', 'shelf_life_remaining_pct'])

    @property
    def days_until_expiry(self):
        today = timezone.now().date()
        return (self.expiry_date - today).days


class InventoryStock(models.Model):
    """
    Stock-in/Stock-out transaction log.
    Records all inventory movements for FEFO tracking and audit.
    """
    TRANSACTION_TYPE_CHOICES = [
        ('stock_in', 'Stock In'),
        ('stock_out', 'Stock Out'),
        ('adjustment', 'Adjustment'),
        ('disposal', 'Disposal'),
        ('return', 'Return'),
        ('transfer', 'Transfer'),
    ]

    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='inventory_transactions', verbose_name='Toko'
    )
    master_product = models.ForeignKey(
        MasterProduct, on_delete=models.CASCADE,
        related_name='stock_transactions', verbose_name='Master Produk'
    )
    product = models.ForeignKey(
        'products.Product', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='stock_transactions',
        verbose_name='Product Listing'
    )
    batch = models.ForeignKey(
        ProductBatch, on_delete=models.CASCADE,
        related_name='stock_transactions', verbose_name='Batch',
        help_text='FEFO: pick the batch with nearest expiry'
    )
    transaction_type = models.CharField(
        max_length=20, choices=TRANSACTION_TYPE_CHOICES,
        verbose_name='Tipe Transaksi'
    )
    quantity = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Jumlah'
    )
    quantity_before = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name='Stok Sebelum'
    )
    quantity_after = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name='Stok Sesudah'
    )
    reference_type = models.CharField(
        max_length=50, blank=True, verbose_name='Tipe Referensi',
        help_text='e.g., order_id, purchase_order_id'
    )
    reference_id = models.CharField(
        max_length=50, blank=True, verbose_name='ID Referensi'
    )
    notes = models.TextField(blank=True, verbose_name='Catatan')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Dibuat Oleh'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inventory_stock_transactions'
        verbose_name = 'Transaksi Stok'
        verbose_name_plural = 'Transaksi Stok'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['store', 'transaction_type']),
            models.Index(fields=['batch']),
            models.Index(fields=['created_at']),
            models.Index(fields=['master_product']),
        ]

    def __str__(self):
        return (
            f"{self.get_transaction_type_display()} - "
            f"{self.master_product.product_name} x{self.quantity} "
            f"(Batch: {self.batch.batch_number})"
        )


class ExpiryNotification(models.Model):
    """
    Tracks expiry-related notifications sent for each batch.
    Prevents duplicate notifications.
    """
    NOTIFICATION_TYPE_CHOICES = [
        ('expiring_soon', 'Akan Kadaluwarsa'),
        ('expired', 'Kadaluwarsa'),
        ('disposal', 'Buang Stok'),
    ]

    batch = models.ForeignKey(
        ProductBatch, on_delete=models.CASCADE,
        related_name='expiry_notifications', verbose_name='Batch'
    )
    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='expiry_notifications', verbose_name='Toko'
    )
    notification_type = models.CharField(
        max_length=20, choices=NOTIFICATION_TYPE_CHOICES,
        verbose_name='Tipe Notifikasi'
    )
    days_until_expiry = models.IntegerField(
        verbose_name='Hari Menuju Kadaluwarsa'
    )
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inventory_expiry_notifications'
        verbose_name = 'Notifikasi Kadaluwarsa'
        verbose_name_plural = 'Notifikasi Kadaluwarsa'
        unique_together = ['batch', 'notification_type']
        indexes = [
            models.Index(fields=['store', 'notification_type']),
        ]

    def __str__(self):
        return (
            f"{self.get_notification_type_display()} - "
            f"{self.batch.master_product.product_name}"
        )


class StockAlert(models.Model):
    """
    Configurable stock thresholds per store.
    Used for low-stock and overstock alerts.
    """
    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='stock_alerts', verbose_name='Toko'
    )
    master_product = models.ForeignKey(
        MasterProduct, on_delete=models.CASCADE,
        related_name='stock_alerts', verbose_name='Master Produk'
    )
    min_stock = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        default=10, verbose_name='Stok Minimum'
    )
    max_stock = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True, blank=True, verbose_name='Stok Maksimum'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventory_stock_alerts'
        verbose_name = 'Alert Stok'
        verbose_name_plural = 'Alert Stok'
        unique_together = ['store', 'master_product']

    def __str__(self):
        return (
            f"{self.store.store_name} - "
            f"{self.master_product.product_name} (min: {self.min_stock})"
        )


# =============================================================================
# AI SMART INVENTORY SCANNING MODELS
# =============================================================================


class SmartScanSession(models.Model):
    """
    Tracks an AI-powered inventory scanning session.
    
    A session begins when the seller opens the camera scanner
    and ends when all detected items have been reviewed and saved.
    Supports real-time frame submission from Flutter camera.
    """
    SCAN_MODE_CHOICES = [
        ('single', 'Single Product'),
        ('multi', 'Multi Product'),
        ('bulk', 'Bulk / Shelf Scan'),
    ]
    STATUS_CHOICES = [
        ('scanning', 'Scanning'),
        ('review', 'Awaiting Review'),
        ('confirmed', 'Confirmed'),
        ('saved', 'Saved to Inventory'),
        ('cancelled', 'Cancelled'),
    ]

    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='ai_scan_sessions', verbose_name='Toko'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='ai_scan_sessions', verbose_name='Pengguna'
    )
    scan_mode = models.CharField(
        max_length=20, choices=SCAN_MODE_CHOICES,
        default='multi', verbose_name='Mode Scan'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='scanning', db_index=True, verbose_name='Status'
    )
    
    # Session metadata
    frame_count = models.IntegerField(default=0, verbose_name='Jumlah Frame')
    total_items_detected = models.IntegerField(default=0, verbose_name='Item Terdeteksi')
    total_items_confirmed = models.IntegerField(default=0, verbose_name='Item Dikonfirmasi')
    total_batches_created = models.IntegerField(default=0, verbose_name='Batch Dibuat')
    
    # Duration tracking
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='Mulai')
    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name='Selesai'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_scan_sessions'
        verbose_name = 'Sesi Scan AI'
        verbose_name_plural = 'Sesi Scan AI'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['store', 'status']),
            models.Index(fields=['user']),
            models.Index(fields=['started_at']),
        ]

    def __str__(self):
        return (
            f"Sesi #{self.id} - {self.store.store_name} "
            f"({self.get_status_display()})"
        )

    @property
    def duration_seconds(self):
        if self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return int((timezone.now() - self.started_at).total_seconds())

    @property
    def completion_rate(self):
        if self.total_items_detected > 0:
            return round(
                (self.total_items_confirmed / self.total_items_detected) * 100, 1
            )
        return 0.0


class DetectedItem(models.Model):
    """
    A single product detected during an AI scan session.
    
    Each item represents one product instance identified by
    object detection, barcode recognition, or OCR.
    Multiple identical items (e.g., 12 bottles of same product)
    are represented by a single DetectedItem with count > 1.
    """
    DETECTION_METHOD_CHOICES = [
        ('object_detection', 'Object Detection'),
        ('barcode', 'Barcode Recognition'),
        ('ocr', 'OCR Text Recognition'),
        ('manual', 'Manual Entry'),
        ('combined', 'Combined (AI Aggregate)'),
    ]
    CONFIRMATION_CHOICES = [
        ('pending', 'Pending Review'),
        ('accepted', 'Accepted by User'),
        ('corrected', 'Corrected by User'),
        ('rejected', 'Rejected by User'),
    ]

    session = models.ForeignKey(
        SmartScanSession, on_delete=models.CASCADE,
        related_name='detected_items', verbose_name='Sesi Scan'
    )
    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='ai_detected_items', verbose_name='Toko'
    )
    
    # Detection method
    detection_method = models.CharField(
        max_length=30, choices=DETECTION_METHOD_CHOICES,
        verbose_name='Metode Deteksi'
    )
    confidence_score = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name='Skor Keyakinan',
        help_text='Overall AI confidence (0.00 - 1.00)'
    )
    
    # Product linkage (filled after matching)
    master_product = models.ForeignKey(
        MasterProduct, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ai_detections',
        verbose_name='Master Produk'
    )
    
    # Count and quantity
    detected_count = models.IntegerField(
        validators=[MinValueValidator(1)], default=1,
        verbose_name='Jumlah Terdeteksi',
        help_text='Number of identical items found (e.g., 12 bottles)'
    )
    confirmed_count = models.IntegerField(
        validators=[MinValueValidator(0)], default=0,
        verbose_name='Jumlah Dikonfirmasi',
        help_text='User-confirmed quantity before saving'
    )
    unit = models.CharField(
        max_length=20, default='pcs', verbose_name='Satuan'
    )
    
    # Barcode data
    detected_barcode = models.CharField(
        max_length=20, blank=True, verbose_name='Barcode Terdeteksi',
        help_text='Barcode value detected via camera'
    )
    barcode_confidence = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name='Confidence Barcode'
    )
    
    # OCR data
    detected_batch_number = models.CharField(
        max_length=100, blank=True, verbose_name='Batch Terdeteksi (OCR)'
    )
    detected_expiry_date = models.DateField(
        null=True, blank=True, verbose_name='Expiry Terdeteksi (OCR)'
    )
    detected_product_name = models.CharField(
        max_length=200, blank=True, verbose_name='Nama Produk Terdeteksi (OCR)'
    )
    detected_brand = models.CharField(
        max_length=100, blank=True, verbose_name='Merek Terdeteksi (OCR)'
    )
    ocr_confidence = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name='Confidence OCR'
    )
    
    # Object detection metadata
    bounding_box = models.JSONField(
        null=True, blank=True, verbose_name='Bounding Box',
        help_text='Bounding box coordinates: {x, y, width, height}'
    )
    detection_features = models.JSONField(
        null=True, blank=True, verbose_name='Fitur Deteksi',
        help_text='Visual features: color, shape, detected labels, stacked/hanging flags'
    )
    
    # Frame position reference
    frame_number = models.IntegerField(
        default=0, verbose_name='Frame Number',
        help_text='Camera frame number where this item was detected'
    )
    
    # Confirmation
    confirmation_status = models.CharField(
        max_length=20, choices=CONFIRMATION_CHOICES,
        default='pending', verbose_name='Status Konfirmasi'
    )
    user_notes = models.TextField(
        blank=True, verbose_name='Catatan Pengguna',
        help_text='User corrections or notes before saving'
    )
    
    # Post-save linkage
    created_batch = models.ForeignKey(
        ProductBatch, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ai_scan_items',
        verbose_name='Batch Dibuat'
    )
    
    # Timestamps
    detected_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_detected_items'
        verbose_name = 'Item Terdeteksi AI'
        verbose_name_plural = 'Item Terdeteksi AI'
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['session', 'confirmation_status']),
            models.Index(fields=['master_product']),
            models.Index(fields=['detection_method']),
            models.Index(fields=['detected_barcode']),
        ]

    def __str__(self):
        name = self.master_product.product_name if self.master_product else self.detected_product_name or 'Unknown'
        return f"[{self.detection_method}] {name} x{self.detected_count} ({self.confidence_score})"

    def save(self, *args, **kwargs):
        if self.confirmed_count <= 0 and self.confirmation_status in ('accepted', 'corrected'):
            self.confirmed_count = self.detected_count
        super().save(*args, **kwargs)
