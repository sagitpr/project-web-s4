"""
Loyalty & Reward Points models for Warungio Marketplace.
Points earning, redemption, loyalty tiers, and history.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class LoyaltyTier(models.Model):
    """Loyalty membership tiers/levels."""
    TIER_CHOICES = [
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
        ('diamond', 'Diamond'),
    ]

    name = models.CharField(max_length=50, choices=TIER_CHOICES, unique=True, verbose_name='Nama Tier')
    display_name = models.CharField(max_length=100, verbose_name='Nama Tampilan')
    icon = models.CharField(max_length=255, blank=True, null=True, verbose_name='Ikon URL')
    
    # Points range for this tier
    min_points = models.IntegerField(default=0, verbose_name='Min. Poin')
    max_points = models.IntegerField(default=99999, verbose_name='Maks. Poin')
    
    # Benefits
    point_multiplier = models.DecimalField(
        max_digits=4, decimal_places=2, default=1.0,
        verbose_name='Multiplier Poin',
        help_text='1.0 = 1 point per Rp 1000 spent'
    )
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Diskon Khusus (%)'
    )
    free_shipping = models.BooleanField(default=False, verbose_name='Gratis Ongkir')
    priority_support = models.BooleanField(default=False, verbose_name='Prioritas Support')
    birthday_reward = models.IntegerField(default=0, verbose_name='Reward Ulang Tahun (Poin)')
    monthly_voucher = models.BooleanField(default=False, verbose_name='Voucher Bulanan')
    
    # Badge/Color
    badge_color = models.CharField(max_length=20, default='#CD7F32', verbose_name='Warna Badge')
    badge_icon = models.CharField(max_length=100, blank=True, null=True, verbose_name='Ikon Badge')
    
    sort_order = models.IntegerField(default=0, verbose_name='Urutan')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'loyalty_tiers'
        verbose_name = 'Tier Loyalty'
        verbose_name_plural = 'Tier Loyalty'
        ordering = ['sort_order']

    def __str__(self):
        return self.get_name_display()


class LoyaltyAccount(models.Model):
    """Loyalty points account for each user."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='loyalty_account', verbose_name='Pengguna'
    )
    tier = models.ForeignKey(
        LoyaltyTier, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='members',
        verbose_name='Tier'
    )
    
    # Points
    total_points_earned = models.IntegerField(default=0, verbose_name='Total Poin Diterima')
    total_points_redeemed = models.IntegerField(default=0, verbose_name='Total Poin Ditukar')
    points_balance = models.IntegerField(default=0, verbose_name='Saldo Poin')
    lifetime_points = models.IntegerField(default=0, verbose_name='Seumur Hidup')
    
    # Stats
    total_orders = models.IntegerField(default=0, verbose_name='Total Pesanan')
    total_spent = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        verbose_name='Total Belanja'
    )
    last_earned_at = models.DateTimeField(null=True, blank=True, verbose_name='Terakhir Mendapat')
    last_redeemed_at = models.DateTimeField(null=True, blank=True, verbose_name='Terakhir Menukar')
    
    # Member since
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='Bergabung')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loyalty_accounts'
        verbose_name = 'Akun Loyalty'
        verbose_name_plural = 'Akun Loyalty'
        indexes = [
            models.Index(fields=['user', 'points_balance']),
            models.Index(fields=['tier']),
        ]

    def __str__(self):
        return f'{self.user.email} - {self.points_balance} pts ({self.tier})'

    def update_tier(self):
        """Auto-upgrade/downgrade tier based on points balance."""
        new_tier = LoyaltyTier.objects.filter(
            is_active=True,
            min_points__lte=self.points_balance,
            max_points__gte=self.points_balance
        ).first()
        if new_tier and new_tier != self.tier:
            self.tier = new_tier
            self.save(update_fields=['tier'])

    def add_points(self, points, description=''):
        """Add points to account."""
        self.points_balance += points
        self.total_points_earned += points
        self.lifetime_points += points
        self.last_earned_at = timezone.now()
        self.save(update_fields=[
            'points_balance', 'total_points_earned', 'lifetime_points', 'last_earned_at'
        ])
        self.update_tier()
        return LoyaltyTransaction.objects.create(
            user=self.user,
            transaction_type='earn',
            points=points,
            balance_after=self.points_balance,
            description=description or 'Poin diterima',
        )

    def redeem_points(self, points, description=''):
        """Redeem points if sufficient balance."""
        if self.points_balance < points:
            raise ValueError('Saldo poin tidak mencukupi.')
        self.points_balance -= points
        self.total_points_redeemed += points
        self.last_redeemed_at = timezone.now()
        self.save(update_fields=[
            'points_balance', 'total_points_redeemed', 'last_redeemed_at'
        ])
        return LoyaltyTransaction.objects.create(
            user=self.user,
            transaction_type='redeem',
            points=-points,
            balance_after=self.points_balance,
            description=description or 'Poin ditukarkan',
        )


class LoyaltyTransaction(models.Model):
    """Individual points transaction history."""
    TRANSACTION_TYPES = [
        ('earn', 'Earned'),
        ('redeem', 'Redeemed'),
        ('expire', 'Expired'),
        ('bonus', 'Bonus'),
        ('adjustment', 'Adjustment'),
        ('refund', 'Refund'),
        ('referral', 'Referral Bonus'),
        ('birthday', 'Birthday Reward'),
        ('review', 'Review Bonus'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='loyalty_transactions', verbose_name='Pengguna'
    )
    transaction_type = models.CharField(
        max_length=20, choices=TRANSACTION_TYPES,
        verbose_name='Tipe Transaksi'
    )
    points = models.IntegerField(verbose_name='Poin')
    balance_before = models.IntegerField(default=0, verbose_name='Saldo Sebelum')
    balance_after = models.IntegerField(default=0, verbose_name='Saldo Sesudah')
    description = models.TextField(blank=True, null=True, verbose_name='Deskripsi')
    
    # Reference
    reference_type = models.CharField(max_length=50, blank=True, null=True, verbose_name='Tipe Referensi')
    reference_id = models.IntegerField(null=True, blank=True, verbose_name='ID Referensi')
    order_number = models.CharField(max_length=30, blank=True, null=True, verbose_name='No. Pesanan')
    
    # Expiry
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='Kadaluwarsa')
    is_expired = models.BooleanField(default=False, verbose_name='Kadaluwarsa')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Waktu')

    class Meta:
        db_table = 'loyalty_transactions'
        verbose_name = 'Transaksi Poin'
        verbose_name_plural = 'Transaksi Poin'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f'{self.get_transaction_type_display()}: {self.points} pts - {self.user.email}'


class LoyaltyReward(models.Model):
    """Redeemable rewards in the loyalty program."""
    REWARD_TYPES = [
        ('voucher', 'Voucher Diskon'),
        ('product', 'Produk Gratis'),
        ('free_shipping', 'Gratis Ongkir'),
        ('cashback', 'Cashback'),
        ('exchange', 'Tukar Poin'),
    ]

    name = models.CharField(max_length=200, verbose_name='Nama Reward')
    description = models.TextField(blank=True, null=True, verbose_name='Deskripsi')
    reward_type = models.CharField(
        max_length=20, choices=REWARD_TYPES, verbose_name='Tipe Reward'
    )
    
    # Cost
    points_required = models.IntegerField(verbose_name='Poin Dibutuhkan')
    discount_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Nilai Diskon (Rp)'
    )
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Diskon (%)',
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Conditions
    min_purchase = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='Min. Belanja'
    )
    max_usage = models.IntegerField(default=0, verbose_name='Maks. Pakai', help_text='0 = unlimited')
    usage_count = models.IntegerField(default=0, verbose_name='Sudah Dipakai')
    
    # Validity
    valid_days = models.IntegerField(default=30, verbose_name='Masa Berlaku (Hari)')
    valid_for_tiers = models.ManyToManyField(
        LoyaltyTier, blank=True, verbose_name='Tier yang Berlaku',
        help_text='Kosongkan jika berlaku untuk semua tier'
    )
    
    # Media
    image = models.ImageField(upload_to='loyalty/rewards/', blank=True, null=True, verbose_name='Gambar')
    icon = models.CharField(max_length=255, blank=True, null=True, verbose_name='Ikon')
    
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    is_featured = models.BooleanField(default=False, verbose_name='Unggulan')
    sort_order = models.IntegerField(default=0, verbose_name='Urutan')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'loyalty_rewards'
        verbose_name = 'Reward Poin'
        verbose_name_plural = 'Reward Poin'
        ordering = ['sort_order']

    def __str__(self):
        return f'{self.name} ({self.points_required} pts)'


class LoyaltyRedemption(models.Model):
    """Record of a user redeeming a reward."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('used', 'Used'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='loyalty_redemptions'
    )
    reward = models.ForeignKey(
        LoyaltyReward, on_delete=models.CASCADE,
        related_name='redemptions'
    )
    transaction = models.OneToOneField(
        LoyaltyTransaction, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='redemption'
    )
    
    points_spent = models.IntegerField(verbose_name='Poin Digunakan')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending',
        verbose_name='Status'
    )
    
    # Voucher code if applicable
    voucher_code = models.CharField(max_length=50, blank=True, null=True, verbose_name='Kode Voucher')
    
    # Validity
    valid_until = models.DateTimeField(null=True, blank=True, verbose_name='Berlaku Sampai')
    used_at = models.DateTimeField(null=True, blank=True, verbose_name='Digunakan')
    
    # Reference order
    applied_to_order = models.ForeignKey(
        'orders.Order', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='loyalty_redemptions',
        verbose_name='Digunakan di Pesanan'
    )
    
    notes = models.TextField(blank=True, null=True, verbose_name='Catatan')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loyalty_redemptions'
        verbose_name = 'Penukaran Poin'
        verbose_name_plural = 'Penukaran Poin'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} → {self.reward.name} ({self.points_spent} pts)'


class LoyaltyReferral(models.Model):
    """Referral tracking for referral bonuses."""
    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='referrals_made', verbose_name='Pengundang'
    )
    referred = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='referred_by', verbose_name='Diundang'
    )
    referral_code = models.CharField(max_length=50, verbose_name='Kode Referral')
    
    # Bonus
    referrer_bonus = models.IntegerField(default=0, verbose_name='Bonus Pengundang')
    referred_bonus = models.IntegerField(default=0, verbose_name='Bonus Diundang')
    referrer_bonus_given = models.BooleanField(default=False)
    referred_bonus_given = models.BooleanField(default=False)
    
    # When referred user makes first purchase
    first_purchase_made = models.BooleanField(default=False)
    first_purchase_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'loyalty_referrals'
        verbose_name = 'Referral'
        verbose_name_plural = 'Referral'
        unique_together = ['referrer', 'referred']

    def __str__(self):
        return f'{self.referrer.email} → {self.referred.email}'
