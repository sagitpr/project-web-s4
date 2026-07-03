"""
Payments app models for Warungio Marketplace.
Midtrans Snap payment integration.
"""

from django.db import models
from django.conf import settings


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
                    'owner_phone': '089667850425',
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
    """Store withdrawal bank accounts."""
    store = models.ForeignKey(
        'stores.Store', on_delete=models.CASCADE,
        related_name='bank_accounts'
    )
    bank_name = models.CharField(max_length=50, verbose_name='Nama Bank') # BCA, BRI, Mandiri, BNI
    account_number = models.CharField(max_length=50, verbose_name='Nomor Rekening')
    account_holder = models.CharField(max_length=100, verbose_name='Nama Pemilik Rekening')
    is_primary = models.BooleanField(default=False, verbose_name='Rekening Utama')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bank_accounts'
        verbose_name = 'Rekening Bank'
        verbose_name_plural = 'Rekening Bank'
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f'{self.bank_name} - {self.account_number} ({self.account_holder})'

    def save(self, *args, **kwargs):
        if self.is_primary:
            # Set other bank accounts of this store to non-primary
            BankAccount.objects.filter(store=self.store, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
        # Sync back to Store model to preserve legacy compatibility
        if self.is_primary:
            self.store.bank_name = self.bank_name
            self.store.bank_account = self.account_number
            self.store.bank_owner = self.account_holder
            self.store.save(update_fields=['bank_name', 'bank_account', 'bank_owner'])


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
    owner_phone = models.CharField(
        max_length=20, default='089667850425',
        verbose_name='No. HP Owner (E-Wallet)'
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin_fee_transactions'
        verbose_name = 'Fee Admin'
        verbose_name_plural = 'Fee Admin'
        ordering = ['-created_at']

    def __str__(self):
        return f'AdminFee Rp {self.amount} - Order #{self.order_id} ({self.payout_status})'
