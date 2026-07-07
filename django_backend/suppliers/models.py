"""
Supplier/Vendor management models for Warungio Marketplace.
Suppliers provide products to seller stores.
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class SupplierCategory(models.Model):
    """Category classification for suppliers."""
    name = models.CharField(max_length=100, verbose_name='Nama Kategori')
    description = models.TextField(blank=True, null=True, verbose_name='Deskripsi')
    icon = models.CharField(max_length=255, blank=True, null=True, verbose_name='Ikon')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    sort_order = models.IntegerField(default=0, verbose_name='Urutan')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'supplier_categories'
        verbose_name = 'Kategori Supplier'
        verbose_name_plural = 'Kategori Supplier'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Supplier(models.Model):
    """Core supplier/vendor model."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('blacklisted', 'Blacklisted'),
        ('inactive', 'Inactive'),
    ]

    VERIFICATION_CHOICES = [
        ('unverified', 'Unverified'),
        ('verified', 'Verified'),
        ('premium', 'Premium'),
    ]

    PAYMENT_TERM_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('7days', '7 Hari'),
        ('14days', '14 Hari'),
        ('30days', '30 Hari'),
        ('dp', 'DP 50%'),
    ]

    # Identity
    supplier_name = models.CharField(max_length=200, verbose_name='Nama Supplier')
    slug = models.SlugField(max_length=220, unique=True, blank=True, verbose_name='Slug')
    category = models.ForeignKey(
        SupplierCategory, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='suppliers',
        verbose_name='Kategori'
    )
    description = models.TextField(blank=True, null=True, verbose_name='Deskripsi')

    # Contact
    contact_person = models.CharField(max_length=150, verbose_name='Kontak Person')
    email = models.EmailField(blank=True, null=True, verbose_name='Email')
    phone = models.CharField(max_length=30, verbose_name='No. Telepon')
    whatsapp = models.CharField(max_length=30, blank=True, null=True, verbose_name='WhatsApp')
    website = models.URLField(blank=True, null=True, verbose_name='Website')

    # Address
    address = models.TextField(verbose_name='Alamat')
    city = models.CharField(max_length=100, verbose_name='Kota')
    province = models.CharField(max_length=100, verbose_name='Provinsi')
    postal_code = models.CharField(max_length=10, blank=True, null=True, verbose_name='Kode Pos')
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    # Business Info
    npwp = models.CharField(max_length=30, blank=True, null=True, verbose_name='NPWP')
    business_license = models.CharField(max_length=100, blank=True, null=True, verbose_name='SIUP/NIB')
    bank_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='Nama Bank')
    bank_account = models.CharField(max_length=50, blank=True, null=True, verbose_name='No. Rekening')
    bank_owner = models.CharField(max_length=150, blank=True, null=True, verbose_name='Pemilik Rekening')

    # Payment terms
    payment_terms = models.CharField(
        max_length=20, choices=PAYMENT_TERM_CHOICES,
        default='cod', verbose_name='Termin Pembayaran'
    )
    min_order = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Min. Pesanan (Rp)'
    )
    shipping_cost_borne = models.CharField(
        max_length=10, choices=[('supplier', 'Supplier'), ('store', 'Toko'), ('split', 'Bagi Dua')],
        default='supplier', verbose_name='Ongkos Kirim'
    )

    # Status & Verification
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending',
        verbose_name='Status'
    )
    verification_level = models.CharField(
        max_length=20, choices=VERIFICATION_CHOICES, default='unverified',
        verbose_name='Level Verifikasi'
    )
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name='Terverifikasi Pada')
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='verified_suppliers',
        verbose_name='Diverifikasi Oleh'
    )

    # Ratings & Stats
    rating_avg = models.DecimalField(
        max_digits=3, decimal_places=2, default=0.00,
        verbose_name='Rating Rata-rata'
    )
    rating_count = models.IntegerField(default=0, verbose_name='Jumlah Rating')
    total_products_supplied = models.IntegerField(default=0, verbose_name='Total Produk')
    total_orders = models.IntegerField(default=0, verbose_name='Total Pesanan')
    total_revenue = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name='Total Pendapatan'
    )
    on_time_delivery_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=100.00,
        verbose_name='Tepat Waktu (%)',
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    quality_score = models.IntegerField(
        default=0, verbose_name='Skor Kualitas',
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # Lead time
    lead_time_days = models.IntegerField(default=3, verbose_name='Lead Time (Hari)')
    delivery_coverage = models.JSONField(default=list, blank=True, verbose_name='Area Pengiriman')
    product_categories = models.JSONField(default=list, blank=True, verbose_name='Kategori Produk')

    # Media
    logo = models.ImageField(upload_to='suppliers/logos/', blank=True, null=True, verbose_name='Logo')
    banner = models.ImageField(upload_to='suppliers/banners/', blank=True, null=True, verbose_name='Banner')
    documents = models.JSONField(default=list, blank=True, verbose_name='Dokumen')

    # Notes
    notes = models.TextField(blank=True, null=True, verbose_name='Catatan Internal')
    tags = models.CharField(max_length=500, blank=True, null=True, verbose_name='Tags')

    # Metadata
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    is_featured = models.BooleanField(default=False, verbose_name='Unggulan')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'suppliers'
        verbose_name = 'Supplier'
        verbose_name_plural = 'Supplier'
        ordering = ['supplier_name']
        indexes = [
            models.Index(fields=['supplier_name']),
            models.Index(fields=['city']),
            models.Index(fields=['status']),
            models.Index(fields=['verification_level']),
            models.Index(fields=['rating_avg']),
            models.Index(fields=['category']),
        ]
        permissions = [
            ('verify_supplier', 'Can verify supplier'),
            ('blacklist_supplier', 'Can blacklist supplier'),
        ]

    def __str__(self):
        return self.supplier_name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.supplier_name)
            slug = base_slug
            counter = 1
            while Supplier.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class SupplierProduct(models.Model):
    """Products supplied by a supplier to stores."""
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE,
        related_name='supplier_products', verbose_name='Supplier'
    )
    product_name = models.CharField(max_length=200, verbose_name='Nama Produk')
    sku = models.CharField(max_length=100, blank=True, null=True, verbose_name='SKU')
    category = models.CharField(max_length=100, blank=True, null=True, verbose_name='Kategori')
    description = models.TextField(blank=True, null=True, verbose_name='Deskripsi')

    # Pricing
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Harga Satuan'
    )
    unit = models.CharField(max_length=50, default='pcs', verbose_name='Satuan')
    min_order_qty = models.IntegerField(default=1, verbose_name='Min. Pesan')
    price_history = models.JSONField(default=list, blank=True, verbose_name='Riwayat Harga')

    # Stock
    stock_available = models.IntegerField(default=0, verbose_name='Stok Tersedia')
    stock_unit = models.CharField(max_length=50, default='pcs', verbose_name='Satuan Stok')

    # Status
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    is_available = models.BooleanField(default=True, verbose_name='Tersedia')
    estimated_delivery_days = models.IntegerField(default=3, verbose_name='Estimasi Kirim (Hari)')

    # Metadata
    notes = models.TextField(blank=True, null=True, verbose_name='Catatan')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'supplier_products'
        verbose_name = 'Produk Supplier'
        verbose_name_plural = 'Produk Supplier'
        ordering = ['supplier', 'product_name']
        indexes = [
            models.Index(fields=['supplier', 'is_active']),
            models.Index(fields=['sku']),
        ]

    def __str__(self):
        return f'{self.product_name} ({self.supplier.supplier_name})'


class SupplierOrder(models.Model):
    """Purchase order from stores to suppliers."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent to Supplier'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    order_number = models.CharField(max_length=30, unique=True, verbose_name='No. Pesanan')
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE,
        related_name='purchase_orders', verbose_name='Supplier'
    )
    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='supplier_orders', verbose_name='Toko'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_supplier_orders',
        verbose_name='Dibuat Oleh'
    )

    # Order details
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='draft',
        verbose_name='Status'
    )
    notes = models.TextField(blank=True, null=True, verbose_name='Catatan')
    internal_notes = models.TextField(blank=True, null=True, verbose_name='Catatan Internal')

    # Financial
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Payment
    payment_terms = models.CharField(max_length=20, verbose_name='Termin')
    payment_status = models.CharField(
        max_length=20, choices=[
            ('unpaid', 'Unpaid'),
            ('partial', 'Partial'),
            ('paid', 'Paid'),
            ('overdue', 'Overdue'),
        ],
        default='unpaid', verbose_name='Status Bayar'
    )
    due_date = models.DateField(null=True, blank=True, verbose_name='Jatuh Tempo')
    paid_at = models.DateTimeField(null=True, blank=True)

    # Delivery
    shipping_address = models.TextField(verbose_name='Alamat Kirim')
    courier = models.CharField(max_length=100, blank=True, null=True, verbose_name='Kurir')
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    estimated_delivery = models.DateField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    ordered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'supplier_orders'
        verbose_name = 'Pesanan Supplier'
        verbose_name_plural = 'Pesanan Supplier'
        ordering = ['-ordered_at']
        indexes = [
            models.Index(fields=['supplier', 'status']),
            models.Index(fields=['store', 'status']),
            models.Index(fields=['order_number']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f'PO #{self.order_number} - {self.supplier.supplier_name}'

    def save(self, *args, **kwargs):
        if not self.order_number:
            import uuid
            self.order_number = f'PO-{uuid.uuid4().hex[:8].upper()}'
        super().save(*args, **kwargs)

    def calculate_totals(self):
        items = self.items.all()
        self.subtotal = sum(item.subtotal for item in items)
        self.total_amount = self.subtotal + self.shipping_cost + self.tax - self.discount
        self.save(update_fields=['subtotal', 'total_amount'])


class SupplierOrderItem(models.Model):
    """Individual items within a supplier purchase order."""
    order = models.ForeignKey(
        SupplierOrder, on_delete=models.CASCADE,
        related_name='items'
    )
    supplier_product = models.ForeignKey(
        SupplierProduct, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='order_items'
    )
    product_name = models.CharField(max_length=200, verbose_name='Nama Produk')
    sku = models.CharField(max_length=100, blank=True, null=True)
    qty = models.IntegerField(validators=[MinValueValidator(1)], verbose_name='Jumlah')
    unit = models.CharField(max_length=50, default='pcs', verbose_name='Satuan')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Harga Satuan')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Subtotal')

    # Receiving
    qty_received = models.IntegerField(default=0, verbose_name='Diterima')
    qty_approved = models.IntegerField(default=0, verbose_name='Disetujui')
    qty_rejected = models.IntegerField(default=0, verbose_name='Ditolak')
    receiving_notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'supplier_order_items'
        verbose_name = 'Item Pesanan Supplier'
        verbose_name_plural = 'Item Pesanan Supplier'

    def __str__(self):
        return f'{self.product_name} x{self.qty}'

    def save(self, *args, **kwargs):
        self.subtotal = self.unit_price * self.qty
        super().save(*args, **kwargs)
        self.order.calculate_totals()


class SupplierReview(models.Model):
    """Ratings and reviews for suppliers."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='supplier_reviews'
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE,
        related_name='reviews'
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Rating'
    )
    comment = models.TextField(blank=True, null=True, verbose_name='Komentar')
    delivery_timeliness = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5, verbose_name='Ketepatan Waktu'
    )
    product_quality = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5, verbose_name='Kualitas Produk'
    )
    communication = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5, verbose_name='Komunikasi'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'supplier_reviews'
        verbose_name = 'Review Supplier'
        verbose_name_plural = 'Review Supplier'
        unique_together = ['user', 'supplier']

    def __str__(self):
        return f'{self.rating}★ for {self.supplier.supplier_name}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._update_supplier_rating()

    def delete(self, *args, **kwargs):
        supplier = self.supplier
        super().delete(*args, **kwargs)
        # Recalculate supplier rating after deletion
        from django.db.models import Avg
        result = SupplierReview.objects.filter(supplier=supplier).aggregate(
            avg=Avg('rating'), count=models.Count('id')
        )
        supplier.rating_avg = result['avg'] or 0
        supplier.rating_count = result['count']
        supplier.save(update_fields=['rating_avg', 'rating_count'])

    def _update_supplier_rating(self):
        """Recalculate and persist the supplier's average rating and count."""
        from django.db.models import Avg
        result = SupplierReview.objects.filter(supplier=self.supplier).aggregate(
            avg=Avg('rating'), count=models.Count('id')
        )
        self.supplier.rating_avg = result['avg'] or 0
        self.supplier.rating_count = result['count']
        self.supplier.save(update_fields=['rating_avg', 'rating_count'])


class SupplierContract(models.Model):
    """Contracts/agreements with suppliers."""
    CONTRACT_TYPE_CHOICES = [
        ('trial', 'Trial'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('perpetual', 'Perpetual'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated'),
    ]

    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE,
        related_name='contracts', verbose_name='Supplier'
    )
    contract_number = models.CharField(max_length=50, unique=True, verbose_name='No. Kontrak')
    contract_type = models.CharField(
        max_length=20, choices=CONTRACT_TYPE_CHOICES, default='monthly',
        verbose_name='Tipe Kontrak'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='draft',
        verbose_name='Status'
    )

    # Terms
    start_date = models.DateField(verbose_name='Mulai')
    end_date = models.DateField(null=True, blank=True, verbose_name='Selesai')
    terms_conditions = models.TextField(blank=True, null=True, verbose_name='Syarat & Ketentuan')
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Komisi (%)',
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    special_pricing = models.JSONField(default=dict, blank=True, verbose_name='Harga Khusus')

    # Documents
    contract_file = models.FileField(upload_to='suppliers/contracts/', blank=True, null=True)
    signed_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    notes = models.TextField(blank=True, null=True, verbose_name='Catatan')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_contracts'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'supplier_contracts'
        verbose_name = 'Kontrak Supplier'
        verbose_name_plural = 'Kontrak Supplier'
        indexes = [
            models.Index(fields=['supplier', 'status']),
            models.Index(fields=['end_date']),
        ]

    def __str__(self):
        return f'{self.contract_number} - {self.supplier.supplier_name}'


class SupplierPayment(models.Model):
    """Payment records to suppliers."""
    PAYMENT_METHOD_CHOICES = [
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Tunai'),
        ('cheque', 'Cek/BG'),
        ('virtual_account', 'Virtual Account'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]

    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE,
        related_name='payments', verbose_name='Supplier'
    )
    purchase_order = models.ForeignKey(
        SupplierOrder, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='payments',
        verbose_name='Pesanan'
    )
    payment_number = models.CharField(max_length=50, unique=True, verbose_name='No. Pembayaran')
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Jumlah')
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES,
        default='bank_transfer', verbose_name='Metode'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending',
        verbose_name='Status'
    )
    payment_date = models.DateField(verbose_name='Tanggal Bayar')
    proof_file = models.FileField(upload_to='suppliers/payments/', blank=True, null=True)
    notes = models.TextField(blank=True, null=True, verbose_name='Catatan')
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='supplier_payments'
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'supplier_payments'
        verbose_name = 'Pembayaran Supplier'
        verbose_name_plural = 'Pembayaran Supplier'
        ordering = ['-payment_date']

    def __str__(self):
        return f'{self.payment_number} - {self.supplier.supplier_name}'
