"""
Support / Help Center models for Warungio Marketplace.
Help articles, FAQ, banners, contact channels, and customer support.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone


class HelpCategory(models.Model):
    """Category for help articles."""
    name = models.CharField(max_length=100, verbose_name='Nama Kategori')
    slug = models.SlugField(max_length=120, unique=True)
    icon = models.CharField(max_length=50, blank=True, null=True, help_text='CSS class or emoji')
    description = models.TextField(blank=True, null=True, verbose_name='Deskripsi')
    sort_order = models.IntegerField(default=0, verbose_name='Urutan')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'help_categories'
        verbose_name = 'Kategori Bantuan'
        verbose_name_plural = 'Kategori Bantuan'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class HelpArticle(models.Model):
    """Help center article / FAQ entry."""
    category = models.ForeignKey(
        HelpCategory, on_delete=models.CASCADE,
        related_name='articles', verbose_name='Kategori'
    )
    title = models.CharField(max_length=255, verbose_name='Judul')
    slug = models.SlugField(max_length=280, unique=True)
    content = models.TextField(verbose_name='Konten')
    excerpt = models.TextField(blank=True, null=True, verbose_name='Ringkasan')

    # Media
    featured_image = models.ImageField(
        upload_to='help/articles/', blank=True, null=True
    )
    attachment = models.FileField(
        upload_to='help/attachments/', blank=True, null=True
    )

    # Stats
    views_count = models.PositiveIntegerField(default=0, verbose_name='Jumlah Dilihat')
    helpful_count = models.PositiveIntegerField(default=0, verbose_name='Membantu')
    not_helpful_count = models.PositiveIntegerField(default=0, verbose_name='Tidak Membantu')

    # Status
    is_published = models.BooleanField(default=True, verbose_name='Dipublikasi')
    is_featured = models.BooleanField(default=False, verbose_name='Unggulan')
    sort_order = models.IntegerField(default=0, verbose_name='Urutan')
    tags = models.CharField(max_length=500, blank=True, null=True, help_text='Comma-separated tags')

    # Metadata
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Penulis'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(default=timezone.now, verbose_name='Tanggal Publikasi')

    class Meta:
        db_table = 'help_articles'
        verbose_name = 'Artikel Bantuan'
        verbose_name_plural = 'Artikel Bantuan'
        ordering = ['-is_featured', 'sort_order', '-published_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['category', 'is_published']),
            models.Index(fields=['views_count']),
        ]

    def __str__(self):
        return self.title

    def increment_views(self):
        self.views_count += 1
        self.save(update_fields=['views_count'])


class FAQ(models.Model):
    """Frequently Asked Questions."""
    question = models.CharField(max_length=255, verbose_name='Pertanyaan')
    answer = models.TextField(verbose_name='Jawaban')
    category = models.ForeignKey(
        HelpCategory, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='faqs', verbose_name='Kategori'
    )
    sort_order = models.IntegerField(default=0, verbose_name='Urutan')
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'faqs'
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQ'
        ordering = ['sort_order']

    def __str__(self):
        return self.question


class BannerPromo(models.Model):
    """Promotional banner for help center and landing pages."""
    BANNER_POSITIONS = [
        ('help_hero', 'Help Hero'),
        ('help_bottom', 'Help Bottom'),
        ('home_hero', 'Home Hero'),
        ('sidebar', 'Sidebar'),
    ]

    title = models.CharField(max_length=255, verbose_name='Judul')
    subtitle = models.CharField(max_length=500, blank=True, null=True, verbose_name='Subjudul')
    image = models.ImageField(upload_to='banners/', verbose_name='Gambar Banner')
    link_url = models.CharField(max_length=500, blank=True, null=True, verbose_name='URL Tautan')
    link_text = models.CharField(max_length=100, default='Belanja Sekarang', verbose_name='Teks Tautan')
    position = models.CharField(
        max_length=30, choices=BANNER_POSITIONS, default='help_hero',
        verbose_name='Posisi'
    )
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    sort_order = models.IntegerField(default=0, verbose_name='Urutan')
    start_date = models.DateTimeField(null=True, blank=True, verbose_name='Mulai')
    end_date = models.DateTimeField(null=True, blank=True, verbose_name='Selesai')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'banner_promos'
        verbose_name = 'Banner Promo'
        verbose_name_plural = 'Banner Promo'
        ordering = ['sort_order']

    def __str__(self):
        return self.title

    def is_expired(self):
        if self.end_date and timezone.now() > self.end_date:
            return True
        return False


class ContactInfo(models.Model):
    """Contact channel information (WhatsApp, Email, Phone, Social Media)."""
    CONTACT_TYPES = [
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
        ('phone', 'Telepon'),
        ('instagram', 'Instagram'),
        ('facebook', 'Facebook'),
        ('twitter', 'Twitter'),
        ('telegram', 'Telegram'),
        ('line', 'LINE'),
    ]

    contact_type = models.CharField(
        max_length=30, choices=CONTACT_TYPES, unique=True,
        verbose_name='Tipe Kontak'
    )
    label = models.CharField(max_length=100, verbose_name='Label')
    value = models.CharField(max_length=255, verbose_name='Nilai Kontak')
    icon = models.CharField(max_length=100, blank=True, null=True, verbose_name='Ikon')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    sort_order = models.IntegerField(default=0, verbose_name='Urutan')
    operating_hours = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name='Jam Operasional',
        help_text='Contoh: Senin - Jumat, 08:00 - 20:00'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contact_infos'
        verbose_name = 'Info Kontak'
        verbose_name_plural = 'Info Kontak'
        ordering = ['sort_order']

    def __str__(self):
        return f'{self.get_contact_type_display()}: {self.label}'


class SupportInfo(models.Model):
    """Static support page info (hero section, stats, etc.)."""
    key = models.CharField(max_length=100, unique=True, verbose_name='Key')
    title = models.CharField(max_length=255, verbose_name='Judul')
    description = models.TextField(blank=True, null=True, verbose_name='Deskripsi')
    icon = models.CharField(max_length=100, blank=True, null=True, verbose_name='Ikon')
    sort_order = models.IntegerField(default=0, verbose_name='Urutan')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'support_infos'
        verbose_name = 'Info Dukungan'
        verbose_name_plural = 'Info Dukungan'
        ordering = ['sort_order']

    def __str__(self):
        return self.title


class ChatQuickReply(models.Model):
    """Pre-defined quick reply templates for chat categories."""
    CATEGORY_CHOICES = [
        ('order', 'Status Pesanan'),
        ('payment', 'Pembayaran'),
        ('return', 'Pengembalian Barang'),
        ('other', 'Lainnya'),
    ]

    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES,
        verbose_name='Kategori'
    )
    label = models.CharField(max_length=100, verbose_name='Label Tombol')
    message_template = models.TextField(verbose_name='Template Pesan')
    sort_order = models.IntegerField(default=0, verbose_name='Urutan')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_quick_replies'
        verbose_name = 'Balasan Cepat Chat'
        verbose_name_plural = 'Balasan Cepat Chat'
        ordering = ['category', 'sort_order']

    def __str__(self):
        return f'[{self.get_category_display()}] {self.label}'


class SupportConversation(models.Model):
    """Support/help chat conversation."""
    subject = models.CharField(max_length=255, default='Chat Bantuan', verbose_name='Subjek')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='support_conversations',
        verbose_name='Pengguna'
    )
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    is_resolved = models.BooleanField(default=False, verbose_name='Selesai')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'support_conversations'
        verbose_name = 'Percakapan Dukungan'
        verbose_name_plural = 'Percakapan Dukungan'
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.subject} ({self.created_at.date()})'


class SupportTicket(models.Model):
    """Customer support ticket model."""
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('resolved', 'Resolved'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='support_tickets',
        verbose_name='Pengguna'
    )
    subject = models.CharField(max_length=255, verbose_name='Subjek')
    message = models.TextField(verbose_name='Pesan')
    support_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='open',
        verbose_name='Status'
    )
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default='normal',
        verbose_name='Prioritas'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'supports'
        verbose_name = 'Tiket Dukungan'
        verbose_name_plural = 'Tiket Dukungan'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['support_status']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'Ticket #{self.id}: {self.subject[:50]}'


class SupportMessage(models.Model):
    """Individual message in a support conversation."""
    conversation = models.ForeignKey(
        SupportConversation, on_delete=models.CASCADE,
        related_name='messages', verbose_name='Percakapan'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='support_messages',
        verbose_name='Pengirim'
    )
    content = models.TextField(verbose_name='Pesan')
    is_from_user = models.BooleanField(default=True, verbose_name='Dari Pengguna')
    is_read = models.BooleanField(default=False, verbose_name='Terbaca')
    attachment = models.FileField(
        upload_to='support/attachments/', blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'support_messages'
        verbose_name = 'Pesan Dukungan'
        verbose_name_plural = 'Pesan Dukungan'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['is_read']),
        ]

    def __str__(self):
        return f'Pesan #{self.id} ({self.created_at:%H:%M})'
