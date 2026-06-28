"""
Stores app models for Warungio Marketplace.
"""

from django.db import models
from django.conf import settings


class Store(models.Model):
    """Seller store/profile model."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='store'
    )
    store_name = models.CharField(max_length=100, verbose_name='Nama Toko')
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    category = models.CharField(max_length=100, blank=True, null=True, verbose_name='Kategori')
    description = models.TextField(blank=True, null=True, verbose_name='Deskripsi')
    
    # Location
    address = models.TextField(blank=True, null=True, verbose_name='Alamat')
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name='Kota')
    province = models.CharField(max_length=100, blank=True, null=True, verbose_name='Provinsi')
    postal_code = models.CharField(max_length=10, blank=True, null=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    
    # Operating hours
    open_time = models.TimeField(blank=True, null=True)
    close_time = models.TimeField(blank=True, null=True)
    
    # Delivery
    delivery_type = models.CharField(max_length=100, blank=True, null=True)
    service_area = models.CharField(max_length=100, blank=True, null=True)
    
    # Bank account
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    bank_account = models.CharField(max_length=100, blank=True, null=True)
    bank_owner = models.CharField(max_length=100, blank=True, null=True)
    
    # Media
    store_logo = models.ImageField(
        upload_to='stores/logos/', blank=True, null=True,
        verbose_name='Logo Toko'
    )
    store_banner = models.ImageField(
        upload_to='stores/banners/', blank=True, null=True,
        verbose_name='Banner Toko'
    )
    
    # Status & Stats
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending',
        verbose_name='Status'
    )
    follower_count = models.IntegerField(default=0)
    product_count = models.IntegerField(default=0)
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_sales = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    
    # Metadata
    is_open = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'stores'
        verbose_name = 'Toko'
        verbose_name_plural = 'Toko'
        ordering = ['store_name']
        indexes = [
            models.Index(fields=['store_name']),
            models.Index(fields=['city']),
            models.Index(fields=['status']),
            models.Index(fields=['rating_avg']),
        ]

    def __str__(self):
        return self.store_name

    def save(self, *args, **kwargs):
        if not self.slug:
            import re
            from django.utils.text import slugify
            base_slug = slugify(self.store_name)
            slug = base_slug
            counter = 1
            while Store.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def update_follower_count(self):
        self.follower_count = self.followers.count()
        self.save(update_fields=['follower_count'])

    def update_rating_avg(self):
        from django.db.models import Avg
        from products.models import Review
        result = Review.objects.filter(
            product__store=self
        ).aggregate(avg_rating=Avg('rating'))
        self.rating_avg = result['avg_rating'] or 0.00
        self.save(update_fields=['rating_avg'])


class StoreFollower(models.Model):
    """Track store followers for analytics."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='following_stores'
    )
    store = models.ForeignKey(
        Store, on_delete=models.CASCADE, related_name='followers'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'store_followers'
        verbose_name = 'Pengikut Toko'
        verbose_name_plural = 'Pengikut Toko'
        unique_together = ['user', 'store']
        indexes = [
            models.Index(fields=['user', 'store']),
        ]

    def __str__(self):
        return f'{self.user.email} follows {self.store.store_name}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.store.update_follower_count()


class StoreCategory(models.Model):
    """Store category classification."""
    name = models.CharField(max_length=100, unique=True)
    icon = models.ImageField(upload_to='categories/', blank=True, null=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'store_categories'
        verbose_name = 'Kategori Toko'
        verbose_name_plural = 'Kategori Toko'
        ordering = ['order']

    def __str__(self):
        return self.name
