"""
Orders app models for Warungio Marketplace.

Hyperlocal Delivery System:
- ShippingMethod: GoSend, GrabExpress, Maxim Delivery, Antar Sendiri
- Delivery: hyperlocal statuses, driver info, pickup codes
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal


class ShippingMethod(models.Model):
    """
    Hyperlocal delivery methods for Warungio.
    Only: GoSend, GrabExpress, Maxim Delivery, Antar Sendiri.
    """
    HYPELOCAL_METHODS = [
        ('gosend', 'GoSend'),
        ('grabexpress', 'GrabExpress'),
        ('maxim', 'Maxim Delivery'),
        ('antar_sendiri', 'Antar Sendiri'),
    ]

    code = models.CharField(
        max_length=30, unique=True,
        choices=HYPELOCAL_METHODS,
        verbose_name='Kode Kurir'
    )
    name = models.CharField(max_length=100, verbose_name='Nama Kurir')
    description = models.TextField(blank=True, null=True, verbose_name='Deskripsi')
    icon = models.CharField(max_length=255, blank=True, null=True, verbose_name='Ikon URL')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    estimated_time = models.CharField(max_length=100, blank=True, null=True, verbose_name='Estimasi Waktu')
    base_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Biaya Dasar')
    sort_order = models.IntegerField(default=0, verbose_name='Urutan')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shipping_methods'
        verbose_name = 'Metode Pengiriman'
        verbose_name_plural = 'Metode Pengiriman'
        ordering = ['sort_order']

    def __str__(self):
        return self.name


class Cart(models.Model):
    """Shopping cart model."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='cart_items'
    )
    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE,
        related_name='cart_items'
    )
    qty = models.IntegerField(
        validators=[MinValueValidator(1)], default=1,
        verbose_name='Jumlah'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cart'
        verbose_name = 'Keranjang'
        verbose_name_plural = 'Keranjang'
        unique_together = ['user', 'product']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f'{self.user.email} - {self.product.product_name} x{self.qty}'

    @property
    def subtotal(self):
        return self.product.price * self.qty


class Order(models.Model):
    """Order model."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('processed', 'Processed'),
        ('shipped', 'Shipped'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    PAYMENT_CHOICES = [
        ('midtrans', 'Midtrans'),
        ('cod', 'Cash on Delivery'),
        ('transfer', 'Bank Transfer'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='orders'
    )
    store = models.ForeignKey(
        'stores.Store', on_delete=models.SET_NULL,
        null=True, related_name='orders'
    )
    
    # Order Info
    order_number = models.CharField(max_length=30, unique=True, blank=True)
    notes = models.TextField(blank=True, null=True, verbose_name='Catatan')
    
    # Pricing
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    admin_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1000.00'),
                                    verbose_name='Biaya Admin (Seller)')
    admin_fee_buyer = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1500.00'),
                                         verbose_name='Biaya Admin (Buyer)')
    admin_fee_seller = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('1000.00'),
                                          verbose_name='Biaya Admin Seller (legacy)')
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Payment
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_CHOICES, default='midtrans'
    )
    payment_status = models.CharField(
        max_length=20, default='pending'
    )
    
    # Status
    order_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending',
        verbose_name='Status Pesanan'
    )
    
    # Shipping
    delivery_address = models.TextField(verbose_name='Alamat Pengiriman')
    recipient_name = models.CharField(max_length=100, blank=True, null=True)
    recipient_phone = models.CharField(max_length=20, blank=True, null=True)
    courier = models.CharField(max_length=50, blank=True, null=True)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    estimated_delivery = models.DateTimeField(null=True, blank=True)
    shipping_method = models.ForeignKey(
        ShippingMethod, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='orders',
        verbose_name='Metode Pengiriman'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'orders'
        verbose_name = 'Pesanan'
        verbose_name_plural = 'Pesanan'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'order_status']),
            models.Index(fields=['store', 'order_status']),
            models.Index(fields=['order_number']),
            models.Index(fields=['created_at']),
            models.Index(fields=['order_status']),
        ]

    def __str__(self):
        return f'Order #{self.order_number}'

    def save(self, *args, **kwargs):
        if not self.order_number:
            import uuid
            self.order_number = f'WRG-{uuid.uuid4().hex[:8].upper()}'
        super().save(*args, **kwargs)

    def calculate_totals(self):
        from decimal import Decimal
        items = self.items.all()
        self.subtotal = sum(item.subtotal for item in items)
        shipping = Decimal(str(self.shipping_cost))
        disc = Decimal(str(self.discount))
        # Buyer: total_price = subtotal + shipping - discount + admin_fee_buyer (Rp 1.500)
        # Seller: admin_fee_seller (Rp 1.000) dipotong dari pendapatan seller ke e-wallet owner.
        self.total_price = self.subtotal + shipping - disc + Decimal(str(self.admin_fee_buyer))
        self.save(update_fields=['subtotal', 'total_price', 'admin_fee', 'admin_fee_buyer', 'admin_fee_seller'])


class OrderItem(models.Model):
    """Individual items within an order."""
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items'
    )
    product = models.ForeignKey(
        'products.Product', on_delete=models.SET_NULL,
        null=True, related_name='order_items'
    )
    product_name = models.CharField(max_length=150, blank=True)
    product_photo = models.CharField(max_length=255, blank=True)
    qty = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'order_items'
        verbose_name = 'Item Pesanan'
        verbose_name_plural = 'Item Pesanan'

    def __str__(self):
        return f'{self.product_name} x{self.qty}'

    def save(self, *args, **kwargs):
        if not self.product_name and self.product:
            self.product_name = self.product.product_name
            if hasattr(self.product, 'product_photo') and self.product.product_photo:
                self.product_photo = str(self.product.product_photo.url) if hasattr(
                    self.product.product_photo, 'url'
                ) else str(self.product.product_photo)
        self.subtotal = self.price * self.qty
        super().save(*args, **kwargs)
        self.order.calculate_totals()


class Delivery(models.Model):
    """
    Delivery/tracking information for hyperlocal marketplace.
    Supports: GrabExpress, GoSend, Mitra Pengiriman (internal), Antar Sendiri.

    Status flow:
    menunggu_konfirmasi -> diproses_penjual -> menunggu_penjemputan -> kurir_menjemput -> dalam_perjalanan -> pesanan_diterima
    OR menunggu_konfirmasi -> dibatalkan
    """
    HYPELOCAL_STATUS = [
        ('menunggu_konfirmasi', 'Menunggu Konfirmasi'),
        ('diproses_penjual', 'Diproses Penjual'),
        ('menunggu_penjemputan', 'Menunggu Penjemputan'),
        ('kurir_menjemput', 'Kurir Menjemput'),
        ('dalam_perjalanan', 'Dalam Perjalanan'),
        ('pesanan_diterima', 'Pesanan Diterima'),
        ('dibatalkan', 'Dibatalkan'),
    ]

    # Provider type: grabexpress, gosend, mitra_pengiriman, antar_sendiri
    PROVIDER_CHOICES = [
        ('grabexpress', 'GrabExpress'),
        ('gosend', 'GoSend'),
        ('mitra_pengiriman', 'Mitra Pengiriman'),
        ('antar_sendiri', 'Antar Sendiri'),
        ('maxim', 'Maxim Delivery'),
    ]

    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name='delivery'
    )
    shipping_method = models.ForeignKey(
        ShippingMethod, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='deliveries',
        verbose_name='Metode Pengiriman'
    )

    # Provider
    courier_provider = models.CharField(
        max_length=30, choices=PROVIDER_CHOICES,
        blank=True, null=True, verbose_name='Provider Kurir'
    )

    # Grab/Gojek delivery IDs
    grab_delivery_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='Grab Delivery ID')
    gojek_order_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='Gojek Order ID')
    mitra_delivery_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='Mitra Delivery ID')

    # Courier / Driver info
    courier_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='Nama Kurir')
    courier_phone = models.CharField(max_length=30, blank=True, null=True, verbose_name='Nomor Kurir')
    driver_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='Nama Driver')
    driver_phone = models.CharField(max_length=30, blank=True, null=True, verbose_name='Nomor Driver')
    driver_photo_url = models.URLField(max_length=500, blank=True, null=True, verbose_name='Foto Driver')
    driver_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True, verbose_name='Rating Driver')
    tracking_number = models.CharField(max_length=100, blank=True, null=True, verbose_name='Kode Tracking')
    tracking_url = models.URLField(max_length=500, blank=True, null=True, verbose_name='URL Tracking')
    pickup_code = models.CharField(max_length=20, blank=True, null=True, verbose_name='Kode Penjemputan')

    # Vehicle info
    vehicle_type = models.CharField(max_length=50, blank=True, null=True, verbose_name='Tipe Kendaraan')
    vehicle_brand = models.CharField(max_length=50, blank=True, null=True, verbose_name='Merk Kendaraan')
    vehicle_plate = models.CharField(max_length=20, blank=True, null=True, verbose_name='Nomor Polisi')
    vehicle_color = models.CharField(max_length=30, blank=True, null=True, verbose_name='Warna Kendaraan')

    # Distance and Coordinates
    distance = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='Jarak (km)')
    buyer_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name='Latitude Pembeli')
    buyer_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name='Longitude Pembeli')

    # Live position (updated via API polling)
    last_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name='Latitude Terakhir')
    last_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name='Longitude Terakhir')
    position_updated_at = models.DateTimeField(null=True, blank=True, verbose_name='Update Posisi')

    # Status
    delivery_status = models.CharField(
        max_length=30, choices=HYPELOCAL_STATUS,
        default='menunggu_konfirmasi', verbose_name='Status Pengiriman'
    )
    estimated_time = models.CharField(max_length=100, blank=True, null=True, verbose_name='Estimasi Tiba')
    estimated_pickup = models.CharField(max_length=100, blank=True, null=True, verbose_name='Estimasi Penjemputan')
    estimated_arrival = models.DateTimeField(null=True, blank=True, verbose_name='Estimasi Sampai')

    # Pickup & Delivery timestamps
    driver_assigned_at = models.DateTimeField(null=True, blank=True, verbose_name='Driver Ditugaskan')
    picked_up_at = models.DateTimeField(null=True, blank=True, verbose_name='Pickup')
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name='Terkirim')
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name='Dibatalkan')

    # Proof of Delivery (POD)
    pod_photo = models.ImageField(upload_to='pod/', blank=True, null=True, verbose_name='Foto POD')
    pod_signature = models.TextField(blank=True, null=True, verbose_name='Tanda Tangan POD')
    pod_signed_at = models.DateTimeField(null=True, blank=True, verbose_name='POD Ditandatangani')
    pod_notes = models.TextField(blank=True, null=True, verbose_name='Catatan POD')

    # QR code for pickup/delivery verification
    qr_pickup_code = models.CharField(max_length=64, blank=True, null=True, verbose_name='QR Pickup')
    qr_delivery_code = models.CharField(max_length=64, blank=True, null=True, verbose_name='QR Delivery')

    # Internal driver assignment
    assigned_driver = models.ForeignKey(
        'MitraDriver', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='deliveries',
        verbose_name='Driver Ditugaskan'
    )

    # Notes
    delivery_notes = models.TextField(blank=True, null=True, verbose_name='Catatan Pengiriman')
    notes = models.TextField(blank=True, null=True, verbose_name='Catatan')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'deliveries'
        verbose_name = 'Pengiriman'
        verbose_name_plural = 'Pengiriman'
        indexes = [
            models.Index(fields=['delivery_status']),
            models.Index(fields=['courier_provider', 'delivery_status']),
        ]

    def __str__(self):
        return f'Delivery for Order #{self.order.order_number}'


class OfflineSale(models.Model):
    """
    Offline purchase record — untuk pembelian langsung di toko (offline).
    Saat pembeli datang ke toko dan membeli barang secara offline,
    seller mencatat penjualan di sini, dan stok produk otomatis berkurang.
    """
    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='offline_sales', verbose_name='Toko'
    )
    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE,
        related_name='offline_sales', verbose_name='Produk'
    )
    product_name = models.CharField(
        max_length=150, blank=True, verbose_name='Nama Produk (snapshot)'
    )
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)], verbose_name='Jumlah'
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Harga Satuan'
    )
    total = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name='Total'
    )
    buyer_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name='Nama Pembeli'
    )
    buyer_phone = models.CharField(
        max_length=20, blank=True, null=True, verbose_name='No. HP Pembeli'
    )
    notes = models.TextField(
        blank=True, null=True, verbose_name='Catatan'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('cash', 'Tunai'),
            ('transfer', 'Transfer'),
            ('qris', 'QRIS'),
        ],
        default='cash', verbose_name='Metode Pembayaran'
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='recorded_offline_sales',
        verbose_name='Dicatat Oleh'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'offline_sales'
        verbose_name = 'Penjualan Offline'
        verbose_name_plural = 'Penjualan Offline'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['store', '-created_at']),
            models.Index(fields=['product']),
        ]

    def __str__(self):
        return f'Offline: {self.product_name} x{self.quantity} (Rp {self.total})'

    def save(self, *args, **kwargs):
        if not self.product_name and self.product:
            self.product_name = self.product.product_name
        self.total = self.price * self.quantity
        super().save(*args, **kwargs)


class PackingSession(models.Model):
    """
    Mencatat sesi packing untuk pesanan online.
    Seller scan barang yang keluar → FEFO stock_out → stok berkurang.
    """
    STATUS_CHOICES = [
        ('packing', 'Packing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE,
        related_name='packing_sessions', verbose_name='Pesanan'
    )
    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='packing_sessions', verbose_name='Toko'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='packing',
        verbose_name='Status Packing'
    )
    total_items = models.IntegerField(default=0, verbose_name='Total Item')
    scanned_items = models.IntegerField(default=0, verbose_name='Sudah Di-scan')
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='Mulai')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Selesai')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'packing_sessions'
        verbose_name = 'Sesi Packing'
        verbose_name_plural = 'Sesi Packing'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['order', 'status']),
            models.Index(fields=['store', 'status']),
        ]

    def __str__(self):
        return f'Packing #{self.id} - Order #{self.order.order_number} ({self.get_status_display()})'


# =============================================================================
# MITRA PENGIRIMAN (Internal Delivery Fleet)
# =============================================================================

class MitraDriver(models.Model):
    """
    Driver internal untuk Mitra Pengiriman Warungio.
    Seller dapat mengelola driver sendiri untuk pengiriman internal.
    """
    DRIVER_STATUS = [
        ('available', 'Tersedia'),
        ('on_delivery', 'Sedang Mengantar'),
        ('offline', 'Offline'),
        ('inactive', 'Nonaktif'),
    ]

    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='mitra_drivers', verbose_name='Toko'
    )
    name = models.CharField(max_length=100, verbose_name='Nama Driver')
    phone = models.CharField(max_length=20, verbose_name='Nomor HP')
    email = models.EmailField(blank=True, null=True, verbose_name='Email')
    photo = models.ImageField(upload_to='drivers/', blank=True, null=True, verbose_name='Foto Driver')

    # Vehicle
    vehicle_type = models.CharField(max_length=50, blank=True, null=True, verbose_name='Tipe Kendaraan',
                                     help_text='Motor, Mobil, Pickup, dll')
    vehicle_brand = models.CharField(max_length=50, blank=True, null=True, verbose_name='Merk')
    vehicle_plate = models.CharField(max_length=20, blank=True, null=True, verbose_name='Nomor Polisi')
    vehicle_color = models.CharField(max_length=30, blank=True, null=True, verbose_name='Warna')

    # Status & area
    status = models.CharField(max_length=20, choices=DRIVER_STATUS, default='available', verbose_name='Status')
    service_area = models.CharField(max_length=255, blank=True, null=True, verbose_name='Area Layanan',
                                     help_text='Kecamatan atau radius yang dilayani')
    max_distance_km = models.DecimalField(max_digits=5, decimal_places=1, default=10.0, verbose_name='Max Jarak (km)')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')

    # Live position (updated by driver app or WebSocket)
    current_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    position_updated_at = models.DateTimeField(null=True, blank=True)

    # Stats
    total_deliveries = models.IntegerField(default=0, verbose_name='Total Pengiriman')
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=5.0, verbose_name='Rating Rata-rata')

    # Auth
    auth_token = models.CharField(max_length=255, blank=True, null=True, verbose_name='Token Autentikasi')
    fcm_token = models.CharField(max_length=500, blank=True, null=True, verbose_name='FCM Token')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mitra_drivers'
        verbose_name = 'Driver Mitra'
        verbose_name_plural = 'Driver Mitra'
        ordering = ['-total_deliveries']
        indexes = [
            models.Index(fields=['store', 'status']),
            models.Index(fields=['store', 'is_active']),
        ]

    def __str__(self):
        return f'{self.name} - {self.store.store_name}'


class MitraDeliveryTariff(models.Model):
    """
    Tarif pengiriman untuk Mitra Pengiriman.
    Seller dapat mengatur tarif sendiri berdasarkan jarak.
    """
    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='mitra_tariffs', verbose_name='Toko'
    )
    name = models.CharField(max_length=100, verbose_name='Nama Tarif', default='Standar')
    base_fee = models.DecimalField(max_digits=10, decimal_places=2, default=5000, verbose_name='Biaya Dasar')
    price_per_km = models.DecimalField(max_digits=10, decimal_places=2, default=2000, verbose_name='Biaya per Km')
    free_km = models.DecimalField(max_digits=5, decimal_places=1, default=2.0, verbose_name='Km Gratis')
    min_fee = models.DecimalField(max_digits=10, decimal_places=2, default=5000, verbose_name='Minimal Biaya')
    max_fee = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='Maksimal Biaya')
    max_distance_km = models.DecimalField(max_digits=5, decimal_places=1, default=20.0, verbose_name='Max Jarak (km)')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mitra_delivery_tariffs'
        verbose_name = 'Tarif Mitra'
        verbose_name_plural = 'Tarif Mitra'

    def __str__(self):
        return f'{self.name} - {self.store.store_name}'

    def calculate_fee(self, distance_km: float) -> Decimal:
        """Calculate delivery fee based on distance."""
        from decimal import Decimal
        dist = Decimal(str(max(distance_km, 0)))
        free = Decimal(str(self.free_km))
        per_km = Decimal(str(self.price_per_km))
        base = Decimal(str(self.base_fee))

        if dist <= free:
            fee = base
        else:
            extra = dist - free
            fee = base + (extra * per_km)

        if fee < Decimal(str(self.min_fee)):
            fee = Decimal(str(self.min_fee))

        if self.max_fee and fee > Decimal(str(self.max_fee)):
            fee = Decimal(str(self.max_fee))

        return fee

    @property
    def progress_pct(self):
        if self.total_items > 0:
            return round((self.scanned_items / self.total_items) * 100, 1)
        return 0


class PackedItem(models.Model):
    """
    Mencatat setiap item yang sudah di-scan saat packing.
    Terkait dengan batch inventory (FEFO) yang dipilih.
    """
    packing_session = models.ForeignKey(
        PackingSession, on_delete=models.CASCADE,
        related_name='packed_items', verbose_name='Sesi Packing'
    )
    order_item = models.ForeignKey(
        'OrderItem', on_delete=models.CASCADE,
        related_name='packed_items', verbose_name='Item Pesanan'
    )
    product = models.ForeignKey(
        'products.Product', on_delete=models.SET_NULL,
        null=True, related_name='packed_items', verbose_name='Produk'
    )
    batch = models.ForeignKey(
        'inventory.ProductBatch', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='packed_items',
        verbose_name='Batch (FEFO)'
    )
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)], verbose_name='Jumlah'
    )
    scanned_at = models.DateTimeField(auto_now_add=True, verbose_name='Waktu Scan')

    class Meta:
        db_table = 'packed_items'
        verbose_name = 'Item Ter-packing'
        verbose_name_plural = 'Item Ter-packing'

    def __str__(self):
        return f'{self.product.product_name if self.product else "?"} x{self.quantity}'
