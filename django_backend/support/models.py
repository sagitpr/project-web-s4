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
    CATEGORY_CHOICES = [
        ('general', 'General'),
        ('order', 'Pesanan'),
        ('payment', 'Pembayaran'),
        ('refund', 'Refund'),
        ('complaint', 'Komplain'),
        ('report', 'Laporan'),
        ('technical', 'Teknis'),
        ('account', 'Akun'),
        ('ai_escalation', 'AI Escalation'),
    ]
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('pending', 'Pending'),
        ('solved', 'Solved'),
        ('closed', 'Closed'),
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
    category = models.CharField(
        max_length=30, choices=CATEGORY_CHOICES, default='general',
        verbose_name='Kategori'
    )
    subject = models.CharField(max_length=255, verbose_name='Subjek')
    message = models.TextField(verbose_name='Pesan')
    attachment = models.FileField(
        upload_to='support/tickets/', blank=True, null=True,
        verbose_name='Lampiran'
    )
    support_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='open',
        verbose_name='Status'
    )
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default='normal',
        verbose_name='Prioritas'
    )
    
    # Assignment & SLA
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_tickets',
        verbose_name='Ditugaskan Ke'
    )
    sla_deadline = models.DateTimeField(null=True, blank=True, verbose_name='Batas SLA')
    sla_met = models.BooleanField(default=False, verbose_name='SLA Terpenuhi')
    first_response_at = models.DateTimeField(null=True, blank=True, verbose_name='Respon Pertama')
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='Selesai Pada')
    
    # CSAT
    csat_score = models.IntegerField(null=True, blank=True, verbose_name='Skor CSAT')
    csat_feedback = models.TextField(blank=True, null=True, verbose_name='Umpan Balik CSAT')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'supports'
        verbose_name = 'Tiket Dukungan'
        verbose_name_plural = 'Tiket Dukungan'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['support_status']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'Ticket #{self.id}: {self.subject[:50]}'

    def assign_to(self, admin_user):
        """Assign ticket to an admin/staff user."""
        self.assigned_to = admin_user
        self.support_status = 'pending'
        self.save(update_fields=['assigned_to', 'support_status', 'updated_at'])

    def resolve(self):
        """Mark ticket as resolved."""
        from django.utils import timezone
        self.support_status = 'solved'
        self.resolved_at = timezone.now()
        self.save(update_fields=['support_status', 'resolved_at', 'updated_at'])

    def close(self):
        """Close the ticket."""
        if not self.resolved_at:
            self.resolved_at = timezone.now()
        self.support_status = 'closed'
        self.save(update_fields=['support_status', 'resolved_at', 'updated_at'])


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


# =============================================================================
# CUSTOMER SUPPORT CENTER — Complaints, Reports, Disputes
# =============================================================================


class Complaint(models.Model):
    """Customer complaint against an order."""
    COMPLAINT_TYPES = [
        ('product_not_as_described', 'Produk Tidak Sesuai'),
        ('damaged_product', 'Produk Rusak'),
        ('expired_product', 'Produk Kadaluwarsa'),
        ('missing_items', 'Barang Kurang'),
        ('wrong_items', 'Barang Salah'),
        ('late_delivery', 'Terlambat'),
        ('seller_unresponsive', 'Penjual Tidak Responsif'),
        ('other', 'Lainnya'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='complaints', verbose_name='Pengguna'
    )
    order = models.ForeignKey(
        'orders.Order', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='complaints',
        verbose_name='Pesanan'
    )
    complaint_type = models.CharField(
        max_length=40, choices=COMPLAINT_TYPES, verbose_name='Tipe Komplain'
    )
    description = models.TextField(verbose_name='Deskripsi')
    desired_resolution = models.TextField(
        blank=True, null=True, verbose_name='Resolusi Diinginkan'
    )
    
    # Evidence
    attachment_1 = models.FileField(
        upload_to='complaints/', blank=True, null=True
    )
    attachment_2 = models.FileField(
        upload_to='complaints/', blank=True, null=True
    )
    attachment_3 = models.FileField(
        upload_to='complaints/', blank=True, null=True
    )
    
    # Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending',
        verbose_name='Status'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_complaints',
        verbose_name='Ditugaskan Ke'
    )
    
    # Resolution
    resolution_notes = models.TextField(
        blank=True, null=True, verbose_name='Catatan Resolusi'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'complaints'
        verbose_name = 'Komplain'
        verbose_name_plural = 'Komplain'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['order']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'Complaint #{self.id} - {self.get_complaint_type_display()}'


class ReportProduct(models.Model):
    """Report a product for policy violation."""
    REASON_CHOICES = [
        ('illegal', 'Barang Ilegal'),
        ('prohibited', 'Barang Terlarang'),
        ('counterfeit', 'Barang Palsu'),
        ('misleading', 'Informasi Menyesatkan'),
        ('inappropriate', 'Konten Tidak Pantas'),
        ('spam', 'Spam'),
        ('fraud', 'Penipuan'),
        ('other', 'Lainnya'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('approved', 'Disetujui'),
        ('rejected', 'Ditolak'),
    ]

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='reported_products', verbose_name='Pelapor'
    )
    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE,
        related_name='reports', verbose_name='Produk'
    )
    reason = models.CharField(
        max_length=30, choices=REASON_CHOICES, verbose_name='Alasan'
    )
    description = models.TextField(verbose_name='Deskripsi')
    
    # Moderation
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending',
        verbose_name='Status'
    )
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='moderated_products',
        verbose_name='Dimoderasi Oleh'
    )
    moderation_notes = models.TextField(
        blank=True, null=True, verbose_name='Catatan Moderasi'
    )
    
    # Auto-moderation
    risk_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name='Skor Risiko'
    )
    is_auto_flagged = models.BooleanField(default=False, verbose_name='Auto Flag')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'report_products'
        verbose_name = 'Laporan Produk'
        verbose_name_plural = 'Laporan Produk'
        indexes = [
            models.Index(fields=['product', 'status']),
            models.Index(fields=['reporter']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'Report #{self.id} - {self.product} ({self.get_reason_display()})'


class ReportSeller(models.Model):
    """Report a seller for policy violation."""
    REASON_CHOICES = [
        ('fraud', 'Penipuan'),
        ('counterfeit', 'Barang Palsu'),
        ('harassment', 'Pelecehan'),
        ('spam', 'Spam'),
        ('bad_service', 'Pelayanan Buruk'),
        ('prohibited_items', 'Menjual Barang Terlarang'),
        ('fake_reviews', 'Ulasan Palsu'),
        ('other', 'Lainnya'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('approved', 'Disetujui'),
        ('rejected', 'Ditolak'),
    ]

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='reported_sellers', verbose_name='Pelapor'
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='seller_reports', verbose_name='Penjual'
    )
    store = models.ForeignKey(
        'stores.Store', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reports',
        verbose_name='Toko'
    )
    reason = models.CharField(
        max_length=30, choices=REASON_CHOICES, verbose_name='Alasan'
    )
    description = models.TextField(verbose_name='Deskripsi')
    
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending',
        verbose_name='Status'
    )
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='moderated_sellers',
        verbose_name='Dimoderasi Oleh'
    )
    moderation_notes = models.TextField(
        blank=True, null=True, verbose_name='Catatan Moderasi'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'report_sellers'
        verbose_name = 'Laporan Penjual'
        verbose_name_plural = 'Laporan Penjual'
        indexes = [
            models.Index(fields=['seller', 'status']),
            models.Index(fields=['reporter']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'Seller Report #{self.id} - {self.seller} ({self.get_reason_display()})'


class ReportBuyer(models.Model):
    """Report a buyer for policy violation (by seller)."""
    REASON_CHOICES = [
        ('fraud', 'Penipuan'),
        ('harassment', 'Pelecehan'),
        ('false_complaint', 'Komplain Palsu'),
        ('chargeback', 'Chargeback'),
        ('fake_review', 'Ulasan Palsu'),
        ('other', 'Lainnya'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('approved', 'Disetujui'),
        ('rejected', 'Ditolak'),
    ]

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='reported_buyers', verbose_name='Pelapor (Seller)'
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='buyer_reports', verbose_name='Pembeli'
    )
    order = models.ForeignKey(
        'orders.Order', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='buyer_reports',
        verbose_name='Pesanan'
    )
    reason = models.CharField(
        max_length=30, choices=REASON_CHOICES, verbose_name='Alasan'
    )
    description = models.TextField(verbose_name='Deskripsi')
    
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending',
        verbose_name='Status'
    )
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='moderated_buyers',
        verbose_name='Dimoderasi Oleh'
    )
    moderation_notes = models.TextField(
        blank=True, null=True, verbose_name='Catatan Moderasi'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'report_buyers'
        verbose_name = 'Laporan Pembeli'
        verbose_name_plural = 'Laporan Pembeli'
        indexes = [
            models.Index(fields=['buyer', 'status']),
            models.Index(fields=['reporter']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'Buyer Report #{self.id} - {self.buyer} ({self.get_reason_display()})'


class Dispute(models.Model):
    """Dispute resolution between buyer and seller."""
    DISPUTE_TYPES = [
        ('refund', 'Refund'),
        ('return', 'Pengembalian Barang'),
        ('cancellation', 'Pembatalan'),
        ('quality', 'Kualitas Produk'),
        ('delivery', 'Pengiriman'),
        ('other', 'Lainnya'),
    ]
    STATUS_CHOICES = [
        ('opened', 'Dibuka'),
        ('investigation', 'Investigasi'),
        ('mediation', 'Mediasi'),
        ('resolved', 'Selesai'),
        ('escalated', 'Naik Banding'),
    ]
    RESOLUTION_CHOICES = [
        ('buyer_win', 'Pembeli Menang'),
        ('seller_win', 'Penjual Menang'),
        ('partial', 'Sebagian'),
        ('cancelled', 'Dibatalkan'),
    ]

    order = models.ForeignKey(
        'orders.Order', on_delete=models.CASCADE,
        related_name='disputes', verbose_name='Pesanan'
    )
    dispute_type = models.CharField(
        max_length=20, choices=DISPUTE_TYPES, verbose_name='Tipe Sengketa'
    )
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='opened_disputes', verbose_name='Dibuka Oleh'
    )
    against_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='disputes_against', verbose_name='Terhadap'
    )
    
    description = models.TextField(verbose_name='Deskripsi')
    desired_outcome = models.TextField(
        blank=True, null=True, verbose_name='Hasil Diinginkan'
    )
    
    # Evidence
    evidence_notes = models.TextField(
        blank=True, null=True, verbose_name='Catatan Bukti'
    )
    
    # Mediation
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='opened',
        verbose_name='Status'
    )
    mediator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='mediated_disputes',
        verbose_name='Mediator'
    )
    
    # Resolution
    resolution = models.CharField(
        max_length=20, choices=RESOLUTION_CHOICES,
        null=True, blank=True, verbose_name='Resolusi'
    )
    resolution_notes = models.TextField(
        blank=True, null=True, verbose_name='Catatan Resolusi'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'disputes'
        verbose_name = 'Sengketa'
        verbose_name_plural = 'Sengketa'
        indexes = [
            models.Index(fields=['order', 'status']),
            models.Index(fields=['opened_by']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'Dispute #{self.id} - Order #{self.order_id} ({self.get_dispute_type_display()})'


class InternalNote(models.Model):
    """Internal notes for CS agents on tickets, complaints, or disputes."""
    NOTE_TYPES = [
        ('ticket', 'Tiket'),
        ('complaint', 'Komplain'),
        ('dispute', 'Sengketa'),
        ('report', 'Laporan'),
    ]

    note_type = models.CharField(
        max_length=20, choices=NOTE_TYPES, verbose_name='Tipe'
    )
    
    # Polymorphic reference (which record this note belongs to)
    reference_id = models.IntegerField(verbose_name='ID Referensi')
    
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='internal_notes', verbose_name='Penulis'
    )
    content = models.TextField(verbose_name='Isi Catatan')
    is_private = models.BooleanField(
        default=True, verbose_name='Internal Only'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'internal_notes'
        verbose_name = 'Catatan Internal'
        verbose_name_plural = 'Catatan Internal'
        indexes = [
            models.Index(fields=['note_type', 'reference_id']),
            models.Index(fields=['author']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'Note #{self.id} on {self.note_type} #{self.reference_id}'
