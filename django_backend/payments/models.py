"""
Payments app models for Warungio Marketplace.
Midtrans Snap payment integration.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator


class PaymentMethod(models.Model):
    """Available payment methods."""
    METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('gopay', 'GoPay'),
        ('shopeepay', 'ShopeePay'),
        ('ovo', 'OVO'),
        ('dana', 'DANA'),
        ('linkaja', 'LinkAja'),
        ('qris', 'QRIS'),
        ('cod', 'Cash on Delivery'),
    ]

    name = models.CharField(max_length=50, choices=METHOD_CHOICES)
    display_name = models.CharField(max_length=100)
    icon = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    order = models.IntegerField(default=0)

    class Meta:
        db_table = 'payment_methods'
        verbose_name = 'Metode Pembayaran'
        verbose_name_plural = 'Metode Pembayaran'
        ordering = ['order']

    def __str__(self):
        return self.display_name


class Payment(models.Model):
    """Payment transaction record."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('expired', 'Expired'),
    ]

    order = models.ForeignKey(
        'orders.Order', on_delete=models.CASCADE,
        related_name='payments',
        null=True,
        blank=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='payments'
    )
    
    # Payment info
    payment_type = models.CharField(max_length=100, blank=True, null=True)
    payment_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    
    # Transaction tracking
    transaction_code = models.CharField(max_length=100, unique=True, blank=True, null=True)
    midtrans_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    midtrans_order_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Bank info (for bank transfer)
    bank_name = models.CharField(max_length=50, blank=True, null=True)
    va_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Payment raw response
    payment_response = models.JSONField(blank=True, null=True, default=dict)
    
    # Metadata
    paid_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'
        verbose_name = 'Pembayaran'
        verbose_name_plural = 'Pembayaran'
        indexes = [
            models.Index(fields=['transaction_code']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['order']),
        ]

    def __str__(self):
        return f'Payment {self.transaction_code} - {self.payment_status}'

    def save(self, *args, **kwargs):
        if not self.transaction_code:
            import uuid
            self.transaction_code = f'PAY-{uuid.uuid4().hex[:12].upper()}'
        if self.amount and self.fee is not None:
            self.net_amount = self.amount - self.fee
        super().save(*args, **kwargs)

    def mark_as_paid(self):
        from django.utils import timezone
        self.payment_status = 'paid'
        self.paid_at = timezone.now()
        self.save(update_fields=['payment_status', 'paid_at'])
        # Update order status
        self.order.payment_status = 'paid'
        self.order.order_status = 'paid'
        self.order.save(update_fields=['payment_status', 'order_status'])
        # Record admin fee seller for platform owner payout (Rp 1.000 per transaksi)
        if self.order.store_id and float(self.order.admin_fee) > 0:
            AdminFeeTransaction.objects.get_or_create(
                order=self.order,
                defaults={
                    'store': self.order.store,
                    'amount': self.order.admin_fee,
                    'owner_phone': AdminFeeTransaction.get_default_owner_phone(),
                }
            )


class MidtransTransaction(models.Model):
    """Midtrans Snap API transaction tracking."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('settlement', 'Settlement'),
        ('capture', 'Capture'),
        ('deny', 'Deny'),
        ('cancel', 'Cancel'),
        ('expire', 'Expire'),
        ('refund', 'Refund'),
        ('partial_refund', 'Partial Refund'),
        ('authorize', 'Authorize'),
    ]

    payment = models.OneToOneField(
        Payment, on_delete=models.CASCADE, related_name='midtrans'
    )
    order_id = models.CharField(max_length=100, unique=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    transaction_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending'
    )
    transaction_time = models.DateTimeField(null=True, blank=True)
    settlement_time = models.DateTimeField(null=True, blank=True)
    
    # Payment details
    payment_type = models.CharField(max_length=50, blank=True, null=True)
    bank = models.CharField(max_length=50, blank=True, null=True)
    va_number = models.CharField(max_length=50, blank=True, null=True)
    bill_key = models.CharField(max_length=100, blank=True, null=True)
    biller_code = models.CharField(max_length=100, blank=True, null=True)
    
    # Status code mapping
    status_code = models.CharField(max_length=10, blank=True, null=True)
    status_message = models.TextField(blank=True, null=True)
    
    # Raw data
    raw_response = models.JSONField(blank=True, null=True, default=dict)
    
    # Fraud
    fraud_status = models.CharField(max_length=20, blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'midtrans_transactions'
        verbose_name = 'Transaksi Midtrans'
        verbose_name_plural = 'Transaksi Midtrans'
        indexes = [
            models.Index(fields=['order_id']),
            models.Index(fields=['transaction_status']),
        ]

    def __str__(self):
        return f'Midtrans {self.order_id} - {self.transaction_status}'


class BankAccount(models.Model):
    """Store withdrawal bank accounts.
    
    The first bank account added during/after registration is automatically
    set as the PRIMARY WITHDRAWAL ACCOUNT (is_primary=True, is_verified=True).
    
    Primary accounts are READ-ONLY in the settings UI to prevent misuse.
    To change the primary account, the seller must use the "Ajukan Perubahan
    Rekening" flow which requires:
      1. OTP verification via email/phone
      2. Password confirmation
      3. Identity verification (if applicable)
      4. Waiting period before new account becomes active
    
    All change requests are logged in BankAccountChangeRequest with
    full audit trail (IP, device, timestamps, old/new accounts).
    """
    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='bank_accounts'
    )
    bank_name = models.CharField(max_length=50, verbose_name='Nama Bank') # BCA, BRI, Mandiri, BNI
    account_number = models.CharField(max_length=50, verbose_name='Nomor Rekening')
    account_holder = models.CharField(max_length=100, verbose_name='Nama Pemilik Rekening')
    is_primary = models.BooleanField(default=False, verbose_name='Rekening Utama')
    is_verified = models.BooleanField(default=False, verbose_name='Terverifikasi',
        help_text='Rekening utama yang telah terverifikasi dan menjadi tujuan pencairan dana')
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name='Terverifikasi Pada')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bank_accounts'
        verbose_name = 'Rekening Bank'
        verbose_name_plural = 'Rekening Bank'
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f'{self.bank_name} - {self.masked_account} ({self.account_holder})'

    @property
    def masked_account(self) -> str:
        """Return masked account number for display (e.g. 'BCA ••••1234')."""
        if not self.account_number or len(self.account_number) < 4:
            return self.account_number or ''
        return f'{self.bank_name} ••••{self.account_number[-4:]}'

    def save(self, *args, **kwargs):
        # Auto-verify when set as primary (first account or explicitly set)
        has_update_fields = bool(kwargs.get('update_fields'))
        if self.is_primary and not self.verified_at and not has_update_fields:
            # Only auto-set timestamps on full save, never on partial update_fields
            self.is_verified = True
            self.verified_at = timezone.now()
            
        if self.is_primary:
            # Set other bank accounts of this store to non-primary
            BankAccount.objects.filter(store=self.store, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
        # Sync back to Store model to preserve legacy compatibility
        if self.is_primary and not has_update_fields:
            self.store.bank_name = self.bank_name
            self.store.bank_account = self.account_number
            self.store.bank_owner = self.account_holder
            self.store.save(update_fields=['bank_name', 'bank_account', 'bank_owner'])


class BankAccountChangeRequest(models.Model):
    """
    Track and secure bank account change requests.
    
    Sellers cannot freely change their primary withdrawal account.
    Any change must go through this secure flow:
      1. Seller submits change request with new account details
      2. System sends OTP to email/phone for verification
      3. Seller confirms with OTP + password
      4. Waiting period before change takes effect (configurable)
      5. Notification sent to seller about the change
      6. Full audit trail recorded
    
    During the waiting period, the OLD account remains active for withdrawals.
    """
    STATUS_CHOICES = [
        ('pending_otp', 'Menunggu Verifikasi OTP'),
        ('pending_password', 'Menunggu Konfirmasi Password'),
        ('pending_approval', 'Menunggu Persetujuan'),
        ('pending_waiting_period', 'Masa Tunggu'),
        ('approved', 'Disetujui'),
        ('completed', 'Selesai'),
        ('rejected', 'Ditolak'),
        ('cancelled', 'Dibatalkan'),
        ('expired', 'Kadaluwarsa'),
    ]

    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='account_change_requests'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='account_change_requests'
    )
    
    # Old account (read-only reference)
    old_bank_name = models.CharField(max_length=50, verbose_name='Bank Lama')
    old_account_number = models.CharField(max_length=50, verbose_name='No. Rekening Lama')
    old_account_holder = models.CharField(max_length=100, verbose_name='Pemilik Rekening Lama')
    
    # New requested account
    new_bank_name = models.CharField(max_length=50, verbose_name='Bank Baru')
    new_account_number = models.CharField(max_length=50, verbose_name='No. Rekening Baru')
    new_account_holder = models.CharField(max_length=100, verbose_name='Pemilik Rekening Baru')
    
    # Verification
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES,
        default='pending_otp', verbose_name='Status'
    )
    otp_verified = models.BooleanField(default=False, verbose_name='OTP Terverifikasi')
    password_verified = models.BooleanField(default=False, verbose_name='Password Terverifikasi')
    otp_verified_at = models.DateTimeField(null=True, blank=True)
    password_verified_at = models.DateTimeField(null=True, blank=True)
    
    # Security
    otp_code_hash = models.CharField(max_length=64, blank=True, null=True)
    verification_token = models.CharField(max_length=255, blank=True, null=True)
    
    # Waiting period (default 24 hours, configurable)
    waiting_period_hours = models.IntegerField(default=24, verbose_name='Masa Tunggu (Jam)')
    waiting_started_at = models.DateTimeField(null=True, blank=True)
    waiting_ends_at = models.DateTimeField(null=True, blank=True)
    
    # Audit trail
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True, verbose_name='Catatan')
    
    # Admin approval (optional — for high-value changes)
    requires_admin_approval = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='approved_account_changes'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'bank_account_change_requests'
        verbose_name = 'Permintaan Perubahan Rekening'
        verbose_name_plural = 'Permintaan Perubahan Rekening'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['store', 'status']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return (f'Change Req #{self.id}: {self.old_bank_name} → {self.new_bank_name} '
                f'({self.get_status_display()})')

    def can_activate(self) -> bool:
        """Check if the new account can be activated."""
        if not self.otp_verified or not self.password_verified:
            return False
        if self.status != 'pending_waiting_period':
            return False
        if self.waiting_ends_at and timezone.now() < self.waiting_ends_at:
            return False
        return True

    def activate(self):
        """Activate the new bank account as primary."""
        from django.utils import timezone
        
        # Create the new bank account as primary
        new_account = BankAccount.objects.create(
            store=self.store,
            bank_name=self.new_bank_name,
            account_number=self.new_account_number,
            account_holder=self.new_account_holder,
            is_primary=True,
            is_verified=True,
            verified_at=timezone.now(),
        )
        
        # Mark old primary account as non-primary (BUT keep it for audit)
        old_accounts = BankAccount.objects.filter(
            store=self.store, is_primary=True
        ).exclude(pk=new_account.pk)
        old_accounts.update(is_primary=False)
        
        # Update request status
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
        
        return new_account


class AdminFeeTransaction(models.Model):
    """
    Mencatat biaya admin seller Rp 1.000 per transaksi yang masuk ke platform owner.
    
    Setiap kali order selesai (completed), Rp 1.000 dari admin_fee_seller dicatat di sini
    sebagai pending payout ke e-wallet owner (089667850425).
    """
    PAYOUT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ]

    order = models.OneToOneField(
        'orders.Order', on_delete=models.CASCADE,
        related_name='admin_fee_record',
        verbose_name='Pesanan'
    )
    store = models.ForeignKey(
        'stores.Store', on_delete=models.SET_NULL,
        null=True, related_name='admin_fees',
        verbose_name='Toko'
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name='Jumlah Fee'
    )
    payout_status = models.CharField(
        max_length=20, choices=PAYOUT_STATUS_CHOICES,
        default='pending', verbose_name='Status Pencairan'
    )
    # Target e-wallet owner
    # The default is read from settings.ADMIN_OWNER_PHONE at runtime so it can be
    # configured via environment variable instead of hardcoding a phone number.
    # Fallback to '089667850425' for backward compatibility if setting is not defined.
    owner_phone = models.CharField(
        max_length=20,
        default='089667850425',
        verbose_name='No. HP Owner (E-Wallet)'
    )

    @classmethod
    def get_default_owner_phone(cls):
        """
        Return the configured admin owner phone from settings or env var.
        Falls back to hardcoded default for backward compatibility.
        """
        from django.conf import settings as django_settings
        return getattr(django_settings, 'ADMIN_OWNER_PHONE', '089667850425')
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin_fee_transactions'
        verbose_name = 'Fee Admin'
        verbose_name_plural = 'Fee Admin'
        ordering = ['-created_at']

    def __str__(self):
        return f'AdminFee Rp {self.amount} - Order #{self.order_id} ({self.payout_status})'


class Wallet(models.Model):
    """
    Dompet Warungio — saldo database-driven, bukan di JSON device_info.
    
    Setiap user memiliki satu Wallet. Semua perubahan saldo dilakukan
    secara atomik melalui WalletService untuk mencegah race condition.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='wallet', verbose_name='Pengguna'
    )
    balance = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Saldo'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wallets'
        verbose_name = 'Dompet'
        verbose_name_plural = 'Dompet'

    def __str__(self):
        return f'Wallet {self.user.email} - Rp {self.balance}'


class WalletTransaction(models.Model):
    """
    Riwayat transaksi Dompet Warungio.
    
    Mencatat setiap perubahan saldo: top-up, pembayaran pesanan,
    refund, penarikan, bonus, dll.
    """
    TX_TYPES = [
        ('topup', 'Top Up'),
        ('payment', 'Pembayaran'),
        ('refund', 'Refund'),
        ('withdrawal', 'Penarikan'),
        ('bonus', 'Bonus'),
        ('adjustment', 'Penyesuaian'),
    ]

    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE,
        related_name='transactions', verbose_name='Dompet'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='wallet_transactions'
    )
    tx_type = models.CharField(
        max_length=20, choices=TX_TYPES,
        verbose_name='Tipe Transaksi'
    )
    amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        verbose_name='Jumlah'
    )
    balance_before = models.DecimalField(
        max_digits=14, decimal_places=2,
        verbose_name='Saldo Sebelum'
    )
    balance_after = models.DecimalField(
        max_digits=14, decimal_places=2,
        verbose_name='Saldo Sesudah'
    )
    description = models.CharField(
        max_length=255, blank=True, null=True,
        verbose_name='Deskripsi'
    )
    reference_type = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name='Tipe Referensi',
        help_text='order, midtrans, withdrawal'
    )
    reference_id = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name='ID Referensi'
    )
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wallet_transactions'
        verbose_name = 'Transaksi Dompet'
        verbose_name_plural = 'Transaksi Dompet'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['tx_type']),
        ]

    def __str__(self):
        return f'{self.get_tx_type_display()} Rp {self.amount} - {self.wallet.user.email}'
