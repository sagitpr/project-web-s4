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
        self.total_price = self.subtotal + shipping - disc
        self.save(update_fields=['subtotal', 'total_price'])


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

    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name='delivery'
    )
    shipping_method = models.ForeignKey(
        ShippingMethod, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='deliveries',
        verbose_name='Metode Pengiriman'
    )

    # Courier / Driver info
    courier_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='Nama Kurir')
    courier_phone = models.CharField(max_length=30, blank=True, null=True, verbose_name='Nomor Kurir')
    driver_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='Nama Driver')
    driver_phone = models.CharField(max_length=30, blank=True, null=True, verbose_name='Nomor Driver')
    tracking_number = models.CharField(max_length=100, blank=True, null=True, verbose_name='Kode Tracking')
    pickup_code = models.CharField(max_length=20, blank=True, null=True, verbose_name='Kode Penjemputan')

    # Distance and Coordinates
    distance = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='Jarak (km)')
    buyer_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name='Latitude Pembeli')
    buyer_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name='Longitude Pembeli')

    # Status
    delivery_status = models.CharField(
        max_length=30, choices=HYPELOCAL_STATUS,
        default='menunggu_konfirmasi', verbose_name='Status Pengiriman'
    )
    estimated_time = models.CharField(max_length=100, blank=True, null=True, verbose_name='Estimasi Tiba')
    estimated_pickup = models.CharField(max_length=100, blank=True, null=True, verbose_name='Estimasi Penjemputan')

    # Timestamps
    driver_assigned_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True, null=True, verbose_name='Catatan')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'deliveries'
        verbose_name = 'Pengiriman'
        verbose_name_plural = 'Pengiriman'

    def __str__(self):
        return f'Delivery for Order #{self.order.order_number}'
