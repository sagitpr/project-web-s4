"""
Products app models for Warungio Marketplace.
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class Category(models.Model):
    """Product category model."""
    category_name = models.CharField(max_length=100, verbose_name='Nama Kategori')
    category_icon = models.ImageField(
        upload_to='categories/icons/', blank=True, null=True,
        verbose_name='Ikon Kategori'
    )
    category_image = models.ImageField(
        upload_to='categories/images/', blank=True, null=True,
        verbose_name='Gambar Kategori'
    )
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'categories'
        verbose_name = 'Kategori'
        verbose_name_plural = 'Kategori'
        ordering = ['order']

    def __str__(self):
        return self.category_name


class Product(models.Model):
    """Product model for seller listings."""
    STATUS_CHOICES = [
        ('fresh', 'Fresh'),
        ('normal', 'Normal'),
        ('low', 'Low'),
        ('bad', 'Bad'),
    ]

    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='products', verbose_name='Toko'
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='products',
        verbose_name='Kategori'
    )
    
    # Product info
    product_name = models.CharField(max_length=150, verbose_name='Nama Produk')
    slug = models.SlugField(max_length=170, blank=True)
    description = models.TextField(blank=True, null=True, verbose_name='Deskripsi')
    
    # SKU & Barcode
    sku = models.CharField(max_length=100, blank=True, null=True, verbose_name='SKU')
    barcode = models.CharField(max_length=100, blank=True, null=True, verbose_name='Barcode')
    brand = models.CharField(max_length=100, blank=True, null=True, verbose_name='Merek')
    
    # Physical attributes
    weight = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name='Berat (gram)')
    length = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name='Panjang (cm)')
    width = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name='Lebar (cm)')
    height = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name='Tinggi (cm)')
    volume = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='Volume (liter)')
    
    # Expiry tracking
    production_date = models.DateField(blank=True, null=True, verbose_name='Tanggal Produksi')
    expired_date = models.DateField(blank=True, null=True, verbose_name='Tanggal Kedaluwarsa')
    
    # Media
    product_photo = models.ImageField(
        upload_to='products/', blank=True, null=True,
        verbose_name='Foto Produk'
    )
    
    # Pricing & Stock
    price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Harga'
    )
    stock = models.IntegerField(
        validators=[MinValueValidator(0)], default=0,
        verbose_name='Stok'
    )
    reserved_stock = models.IntegerField(
        validators=[MinValueValidator(0)], default=0,
        verbose_name='Stok Dipesan',
        help_text='Jumlah yang sudah dipesan buyer tapi belum di-scan untuk packing'
    )
    unit = models.CharField(max_length=50, default='pcs', verbose_name='Satuan')
    
    # Quality
    quality_score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0, verbose_name='Skor Kualitas'
    )
    product_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='fresh',
        verbose_name='Status Produk'
    )
    
    # Stats
    sold_count = models.IntegerField(default=0)
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    review_count = models.IntegerField(default=0)
    
    # Flags
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    is_featured = models.BooleanField(default=False, verbose_name='Unggulan')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        verbose_name = 'Produk'
        verbose_name_plural = 'Produk'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['store', 'is_active']),
            models.Index(fields=['category']),
            models.Index(fields=['product_name']),
            models.Index(fields=['price']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_active', '-created_at']),
        ]

    def __str__(self):
        return self.product_name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            import re
            base_slug = slugify(self.product_name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def store_name(self):
        return self.store.store_name if self.store else ''

    @property
    def available_stock(self):
        """Stok yang benar-benar tersedia untuk dijual (total - reserved)."""
        return max(0, self.stock - self.reserved_stock)

    @property
    def is_low_stock(self):
        """Stock is critically low (≤ 5 units)."""
        return self.stock > 0 and self.stock <= 5

    @property
    def is_out_of_stock(self):
        """Stock is completely depleted."""
        return self.stock <= 0

    @property
    def needs_restock(self):
        """Alias for low stock check."""
        return self.is_low_stock or self.is_out_of_stock

    def update_rating(self):
        from django.db.models import Avg, Count
        result = Review.objects.filter(product=self).aggregate(
            avg_rating=Avg('rating'),
            count=Count('id')
        )
        self.rating_avg = result['avg_rating'] or 0.00
        self.review_count = result['count']
        self.save(update_fields=['rating_avg', 'review_count'])

        # Cascade rating update up to the store level
        # This ensures Store.rating_avg reflects all product reviews across the store
        if hasattr(self, 'store') and self.store:
            self.store.update_rating_avg()


class ProductGallery(models.Model):
    """Additional product images."""
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='gallery'
    )
    image = models.ImageField(upload_to='products/gallery/')
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_gallery'
        verbose_name = 'Galeri Produk'
        verbose_name_plural = 'Galeri Produk'
        ordering = ['order']
        indexes = [
            models.Index(fields=['product', 'order']),
        ]

    def __str__(self):
        return f'Gallery image for {self.product.product_name}'


class Review(models.Model):
    """Product reviews and ratings."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='reviews'
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='reviews'
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Rating'
    )
    comment = models.TextField(blank=True, null=True, verbose_name='Komentar')
    is_verified = models.BooleanField(default=False)
    
    # Seller reply
    seller_reply = models.TextField(blank=True, null=True, verbose_name='Balasan Penjual')
    seller_reply_at = models.DateTimeField(blank=True, null=True, verbose_name='Waktu Balasan')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reviews'
        verbose_name = 'Ulasan'
        verbose_name_plural = 'Ulasan'
        unique_together = ['user', 'product']
        indexes = [
            models.Index(fields=['product', 'rating']),
            models.Index(fields=['created_at'],
                         name='review_created_at_idx'),
            models.Index(fields=['user', 'product'],
                         name='review_user_product_idx'),
        ]

    def __str__(self):
        return f'{self.rating}★ by {self.user.email if self.user else "Anonymous"}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.product.update_rating()

    def delete(self, *args, **kwargs):
        product = self.product
        super().delete(*args, **kwargs)
        product.update_rating()


class Favorite(models.Model):
    """User favorite/wishlist products."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='favorites'
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='favorited_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'favorites'
        verbose_name = 'Favorit'
        verbose_name_plural = 'Favorit'
        ordering = ['-created_at']
        unique_together = ['user', 'product']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f'{self.user.email} ♥ {self.product.product_name}'


class Promo(models.Model):
    """Promotions and discounts for seller stores."""
    PROMO_TYPE_CHOICES = [
        ('free_shipping', 'Gratis Ongkir'),
        ('percentage', 'Diskon Persentase'),
        ('fixed', 'Diskon Nominal'),
        ('flash_sale', 'Flash Sale'),
        ('buy_x_get_y', 'Beli X Gratis Y'),
    ]

    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        null=True, blank=True, related_name='promos',
        verbose_name='Toko'
    )
    promo_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    promo_type = models.CharField(
        max_length=30, choices=PROMO_TYPE_CHOICES, default='percentage',
        verbose_name='Jenis Promo'
    )
    promo_code = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name='Kode Promo'
    )
    discount_percent = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Jumlah Diskon (Rp)'
    )
    min_purchase = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Minimum Belanja'
    )
    max_usage = models.IntegerField(
        default=0, verbose_name='Maksimum Penggunaan',
        help_text='0 = unlimited'
    )
    usage_count = models.IntegerField(default=0, verbose_name='Jumlah Penggunaan')
    start_date = models.DateField()
    end_date = models.DateField()
    promo_banner = models.ImageField(upload_to='promos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'promos'
        verbose_name = 'Promo'
        verbose_name_plural = 'Promo'
        constraints = [
            models.UniqueConstraint(
                fields=['store', 'promo_code'],
                name='unique_store_promo_code'
            )
        ]
        indexes = [
            models.Index(fields=['store', 'is_active', 'start_date', 'end_date'],
                         name='promo_store_active_date_idx'),
            models.Index(fields=['start_date', 'end_date'],
                         name='promo_date_range_idx'),
        ]

    def __str__(self):
        return self.promo_name

    @property
    def computed_status(self):
        """Auto-compute promo status based on dates."""
        from django.utils import timezone
        today = timezone.now().date()
        if not self.is_active:
            return 'inactive'
        if today < self.start_date:
            return 'scheduled'
        if today > self.end_date:
            return 'expired'
        days_left = (self.end_date - today).days
        if days_left <= 3:
            return 'ending_soon'
        return 'active'


class QualityCheck(models.Model):
    """AI product quality analysis results."""
    QUALITY_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('fresh', 'Fresh'),
        ('normal', 'Normal'),
        ('warning', 'Warning'),
        ('rejected', 'Rejected'),
    ]

    STOCK_STATUS_CHOICES = [
        ('sufficient', 'Sufficient'),
        ('low', 'Low'),
        ('critical', 'Critical'),
    ]

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name='quality_checks', verbose_name='Produk'
    )
    freshness_score = models.IntegerField(
        null=True, blank=True, verbose_name='Skor Kesegaran',
        help_text='0-100'
    )
    stock_status = models.CharField(
        max_length=100, choices=STOCK_STATUS_CHOICES,
        null=True, blank=True, verbose_name='Status Stok'
    )
    ai_result = models.TextField(
        null=True, blank=True, verbose_name='Hasil AI',
        help_text='Raw AI analysis result'
    )
    quality_status = models.CharField(
        max_length=20, choices=QUALITY_STATUS_CHOICES,
        default='pending', verbose_name='Status Kualitas'
    )
    checked_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Waktu Cek'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'quality_checks'
        verbose_name = 'Pengecekan Kualitas'
        verbose_name_plural = 'Pengecekan Kualitas'
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['quality_status']),
            models.Index(fields=['checked_at']),
        ]
        ordering = ['-checked_at']

    def __str__(self):
        return f'QualityCheck #{self.id} - {self.product.product_name} ({self.quality_status})'


class RecentlyViewed(models.Model):
    """Track products recently viewed by users.
    Maintains max 50 entries per user — oldest auto-pruned.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='recently_viewed'
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='viewed_by'
    )
    viewed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'recently_viewed'
        verbose_name = 'Baru Dilihat'
        verbose_name_plural = 'Baru Dilihat'
        unique_together = ['user', 'product']
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['user', '-viewed_at']),
        ]

    def __str__(self):
        return f'{self.user.email} → {self.product.product_name}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Prune old entries beyond the latest 50
        total = RecentlyViewed.objects.filter(user=self.user).count()
        if total > 50:
            old_ids = RecentlyViewed.objects.filter(
                user=self.user
            ).values_list('id', flat=True).order_by('-viewed_at')[50:]
            RecentlyViewed.objects.filter(id__in=list(old_ids)).delete()


class GuestReview(models.Model):
    """Guest reviews — no account required, verified by order_number + phone."""
    order_number = models.CharField(max_length=50, db_index=True)
    phone = models.CharField(max_length=20)
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='guest_reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'guest_reviews'
        verbose_name = 'Ulasan Tamu'
        verbose_name_plural = 'Ulasan Tamu'
        unique_together = ['order_number', 'product']

    def __str__(self):
        return f'Guest review: {self.product} (Order {self.order_number})'


class Voucher(models.Model):
    """Discount vouchers."""
    voucher_code = models.CharField(max_length=50, unique=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    min_purchase = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    expired_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vouchers'
        verbose_name = 'Voucher'
        verbose_name_plural = 'Voucher'
        indexes = [
            models.Index(fields=['is_active', 'expired_date']),
        ]

    def __str__(self):
        return self.voucher_code
