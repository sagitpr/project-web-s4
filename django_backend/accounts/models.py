"""
Accounts app models - User, OTP, Address management.
Warungio Marketplace - Hybrid Django + PHP.
"""

import uuid
import hashlib
from datetime import timedelta

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings
from django.core.validators import RegexValidator
from phonenumber_field.modelfields import PhoneNumberField


class User(AbstractUser):
    """Custom user model extending Django's AbstractUser."""
    ROLE_CHOICES = [
        ('buyer', 'Buyer'),
        ('seller', 'Seller'),
        ('admin', 'Admin'),
    ]

    REGISTRATION_STEP_CHOICES = [
        ('email_phone', 'Email/Phone'),     # Step 1: Email or phone
        ('otp', 'OTP'),                     # Step 2: Verify OTP
        ('profile', 'Profile'),             # Step 3: Fill profile
        ('store_setup', 'Store Setup'),     # Step 4: Store setup (seller only)
        ('complete', 'Complete'),           # Done
    ]

    id = models.BigAutoField(primary_key=True)
    email = models.EmailField(unique=True, verbose_name='Email')
    phone = PhoneNumberField(unique=True, null=True, blank=True, verbose_name='Nomor HP')
    full_name = models.CharField(max_length=100, verbose_name='Nama Lengkap')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='buyer', verbose_name='Role')
    
    # Verification
    is_verified = models.BooleanField(default=False, verbose_name='Terverifikasi')
    otp_secret = models.CharField(max_length=32, blank=True, null=True)
    
    # Profile
    address = models.TextField(blank=True, null=True, verbose_name='Alamat')
    profile_photo = models.ImageField(
        upload_to='profiles/', blank=True, null=True, verbose_name='Foto Profil'
    )
    bio = models.TextField(blank=True, null=True, verbose_name='Bio')
    
    # Indonesian-specific fields
    nik = models.CharField(
        max_length=16, unique=True, null=True, blank=True,
        verbose_name='NIK', help_text='Nomor Induk Kependudukan (16 digit)'
    )
    whatsapp_phone = PhoneNumberField(
        null=True, blank=True, verbose_name='Nomor WhatsApp',
        help_text='Nomor WhatsApp untuk OTP dan notifikasi'
    )
    
    # Multi-step registration
    registration_step = models.CharField(
        max_length=20, choices=REGISTRATION_STEP_CHOICES,
        default='email_phone', verbose_name='Langkah Registrasi'
    )
    registration_started_at = models.DateTimeField(
        null=True, blank=True, verbose_name='Registrasi Dimulai'
    )
    registration_completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name='Registrasi Selesai'
    )
    
    # Enhanced security
    failed_login_attempts = models.IntegerField(default=0, verbose_name='Gagal Login')
    locked_until = models.DateTimeField(null=True, blank=True, verbose_name='Terkunci Hingga')
    device_fingerprint = models.CharField(
        max_length=255, blank=True, null=True, verbose_name='Sidik Jari Perangkat'
    )
    
    # Metadata
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    device_info = models.JSONField(blank=True, null=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Device tracking fields
    is_mobile = models.BooleanField(default=False)
    is_tablet = models.BooleanField(default=False)
    is_desktop = models.BooleanField(default=True)
    browser_family = models.CharField(max_length=50, blank=True, null=True)
    os_family = models.CharField(max_length=50, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'username']

    class Meta:
        db_table = 'users'
        verbose_name = 'Pengguna'
        verbose_name_plural = 'Pengguna'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['role']),
            models.Index(fields=['nik']),
            models.Index(fields=['registration_step']),
        ]

    def __str__(self):
        return self.full_name or self.email

    def save(self, *args, **kwargs):
        if not self.full_name:
            self.full_name = self.get_full_name() or self.email.split('@')[0]
        if not self.username:
            self.username = self.email.split('@')[0]
        # Auto-verify superusers/staff so they can login without OTP
        if (self.is_superuser or self.is_staff) and not self.is_verified:
            self.is_verified = True
        super().save(*args, **kwargs)

    def is_account_locked(self):
        """Check if account is temporarily locked due to failed attempts."""
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        if self.locked_until and timezone.now() >= self.locked_until:
            self.locked_until = None
            self.failed_login_attempts = 0
            self.save(update_fields=['locked_until', 'failed_login_attempts'])
        return False

    def increment_failed_login(self):
        """Increment failed login counter and lock account if threshold reached."""
        from django.conf import settings
        self.failed_login_attempts += 1
        max_attempts = getattr(settings, 'LOGIN_MAX_ATTEMPTS', 5)
        lockout_minutes = getattr(settings, 'LOGIN_LOCKOUT_MINUTES', 15)
        
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = timezone.now() + timedelta(minutes=lockout_minutes)
        
        self.save(update_fields=['failed_login_attempts', 'locked_until'])

    def reset_failed_login(self):
        """Reset failed login counter after successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=['failed_login_attempts', 'locked_until'])


class OTP(models.Model):
    """OTP verification model with expiry and rate limiting."""
    OTP_TYPES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
    ]
    PURPOSE_CHOICES = [
        ('registration', 'Registration'),
        ('login', 'Login'),
        ('password_reset', 'Password Reset'),
        ('email_change', 'Email Change'),
        ('phone_change', 'Phone Change'),
        ('payment', 'Payment Verification'),
    ]

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='otps', null=True, blank=True
    )
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    otp_code = models.CharField(max_length=6)
    otp_code_hash = models.CharField(max_length=64, blank=True, null=True,
                                     verbose_name='Hash OTP',
                                     help_text='SHA256 hash of OTP for secure storage')
    otp_type = models.CharField(max_length=20, choices=OTP_TYPES, default='email')
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES, default='registration')
    is_used = models.BooleanField(default=False)
    is_valid = models.BooleanField(default=True)
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=5)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)

    # Rate limiting
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'otps'
        verbose_name = 'Kode OTP'
        verbose_name_plural = 'Kode OTP'
        indexes = [
            models.Index(fields=['email', 'purpose']),
            models.Index(fields=['otp_code']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f'OTP {self.otp_code} for {self.email or self.phone} ({self.purpose})'

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_locked(self):
        return self.attempts >= self.max_attempts

    def can_resend(self):
        cooldown = timedelta(seconds=settings.OTP_COOLDOWN_SECONDS)
        return timezone.now() > self.created_at + cooldown

    def increment_attempts(self):
        self.attempts += 1
        if self.attempts >= self.max_attempts:
            self.is_valid = False
        self.save(update_fields=['attempts', 'is_valid'])

    @staticmethod
    def generate_otp(length=6):
        """Generate a cryptographically secure random OTP code."""
        import secrets
        return ''.join([str(secrets.randbelow(10)) for _ in range(length)])

    @staticmethod
    def hash_otp(otp_code):
        """Hash OTP for secure storage."""
        return hashlib.sha256(otp_code.encode()).hexdigest()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(
                minutes=settings.OTP_EXPIRE_MINUTES
            )
        if not self.otp_code:
            self.otp_code = self.generate_otp()
            self.otp_code_hash = self.hash_otp(self.otp_code)
        super().save(*args, **kwargs)


class UserSession(models.Model):
    """Track user sessions and device info."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sessions'
    )
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, null=True)
    device_type = models.CharField(max_length=20, choices=[
        ('mobile', 'Mobile'), ('tablet', 'Tablet'), ('desktop', 'Desktop')
    ], default='desktop')
    is_active = models.BooleanField(default=True)
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_sessions'
        verbose_name = 'Sesi Pengguna'
        verbose_name_plural = 'Sesi Pengguna'
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]

    def __str__(self):
        return f'Session {self.user.email} - {self.device_type}'


class SocialAccount(models.Model):
    """Social authentication accounts for Google, Facebook, Apple."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='social_accounts'
    )
    provider = models.CharField(
        max_length=20, choices=[
            ('google', 'Google'),
            ('facebook', 'Facebook'),
            ('apple', 'Apple'),
        ]
    )
    provider_id = models.CharField(max_length=255)
    extra_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'social_accounts'
        verbose_name = 'Akun Sosial'
        verbose_name_plural = 'Akun Sosial'
        unique_together = ['provider', 'provider_id']
        indexes = [
            models.Index(fields=['provider', 'provider_id']),
            models.Index(fields=['user', 'provider']),
        ]

    def __str__(self):
        return f'{self.user.email} - {self.provider} ({self.provider_id[:10]}...)'


class LoginAttempt(models.Model):
    """Track login attempts for security monitoring."""
    email = models.EmailField()
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, null=True)
    was_successful = models.BooleanField(default=False)
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'login_attempts'
        verbose_name = 'Percobaan Login'
        verbose_name_plural = 'Percobaan Login'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['attempted_at']),
        ]


# =============================================================================
# NEW MODELS: Indonesian Address & KYC
# =============================================================================

class IndonesianAddress(models.Model):
    """
    Hierarchical Indonesian address model.
    References official Kemendagri codes for provinces, cities, districts, and villages.
    
    Usage:
        address = IndonesianAddress.objects.create(
            province='DKI Jakarta',
            city='Jakarta Selatan',
            district='Kebayoran Baru',
            village='Senayan',
            street='Jl. Asia Afrika No. 8',
            postal_code='10270',
        )
    """
    province = models.CharField(max_length=100, verbose_name='Provinsi')
    province_code = models.CharField(max_length=2, blank=True, verbose_name='Kode Provinsi')
    city = models.CharField(max_length=100, verbose_name='Kota/Kabupaten')
    city_code = models.CharField(max_length=4, blank=True, verbose_name='Kode Kota')
    district = models.CharField(max_length=100, verbose_name='Kecamatan')
    district_code = models.CharField(max_length=6, blank=True, verbose_name='Kode Kecamatan')
    village = models.CharField(max_length=100, blank=True, verbose_name='Kelurahan/Desa')
    village_code = models.CharField(max_length=10, blank=True, verbose_name='Kode Desa')
    street = models.TextField(verbose_name='Jalan / Detail Alamat')
    postal_code = models.CharField(max_length=5, blank=True, verbose_name='Kode Pos')
    
    # Latitude/longitude for map display
    latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'indonesian_addresses'
        verbose_name = 'Alamat Indonesia'
        verbose_name_plural = 'Alamat Indonesia'
        indexes = [
            models.Index(fields=['province']),
            models.Index(fields=['city']),
            models.Index(fields=['district']),
            models.Index(fields=['postal_code']),
        ]

    def __str__(self):
        parts = [self.street]
        if self.village:
            parts.append(self.village)
        if self.district:
            parts.append(f"Kec. {self.district}")
        parts.append(f"{self.city}, {self.province}")
        if self.postal_code:
            parts.append(self.postal_code)
        return ', '.join(parts)

    def to_display(self):
        """Return formatted Indonesian address string."""
        return str(self)


class KYCVerification(models.Model):
    """
    Know Your Customer verification for Indonesian users.
    Stores NIK (KTP) verification data and status.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Terverifikasi'),
        ('rejected', 'Ditolak'),
        ('expired', 'Kadaluwarsa'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='kyc'
    )
    nik = models.CharField(
        max_length=16, unique=True, verbose_name='NIK',
        help_text='Nomor Induk Kependudukan (16 digit)'
    )
    full_name_on_ktp = models.CharField(
        max_length=150, verbose_name='Nama di KTP'
    )
    birth_place = models.CharField(
        max_length=100, blank=True, verbose_name='Tempat Lahir'
    )
    birth_date = models.DateField(null=True, blank=True, verbose_name='Tanggal Lahir')
    gender = models.CharField(
        max_length=10, choices=[
            ('male', 'Laki-laki'),
            ('female', 'Perempuan'),
        ], blank=True, verbose_name='Jenis Kelamin'
    )
    religion = models.CharField(
        max_length=20, blank=True, verbose_name='Agama',
        choices=[
            ('islam', 'Islam'),
            ('kristen', 'Kristen Protestan'),
            ('katholik', 'Kristen Katolik'),
            ('hindu', 'Hindu'),
            ('buddha', 'Buddha'),
            ('konghucu', 'Konghucu'),
            ('other', 'Lainnya'),
        ]
    )
    marital_status = models.CharField(
        max_length=20, blank=True, verbose_name='Status Pernikahan',
        choices=[
            ('single', 'Belum Menikah'),
            ('married', 'Menikah'),
            ('divorced', 'Cerai'),
            ('widowed', 'Cerai Mati'),
        ]
    )
    
    # Address from KTP
    ktp_address = models.TextField(blank=True, verbose_name='Alamat KTP')
    ktp_province = models.CharField(max_length=100, blank=True)
    ktp_city = models.CharField(max_length=100, blank=True)
    ktp_district = models.CharField(max_length=100, blank=True)
    ktp_postal_code = models.CharField(max_length=5, blank=True)
    
    # Verification
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending'
    )
    verification_method = models.CharField(
        max_length=30, blank=True,
        choices=[
            ('manual', 'Verifikasi Manual'),
            ('ocr', 'OCR Otomatis'),
            ('api', 'API Pihak Ketiga'),
        ]
    )
    verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='kyc_verifications',
        verbose_name='Diverifikasi Oleh'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, verbose_name='Alasan Penolakan')
    
    # Document files
    ktp_photo = models.ImageField(
        upload_to='kyc/ktp/', blank=True, null=True,
        verbose_name='Foto KTP'
    )
    selfie_photo = models.ImageField(
        upload_to='kyc/selfie/', blank=True, null=True,
        verbose_name='Foto Selfie dengan KTP'
    )
    
    # Metadata
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # NIK validation result (from NIK validation algorithm)
    nik_validation = models.JSONField(
        blank=True, null=True, default=dict,
        verbose_name='Hasil Validasi NIK'
    )

    class Meta:
        db_table = 'kyc_verifications'
        verbose_name = 'Verifikasi KYC'
        verbose_name_plural = 'Verifikasi KYC'
        indexes = [
            models.Index(fields=['nik']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'KYC {self.nik} - {self.get_status_display()}'


class RegistrationEvent(models.Model):
    """
    Track registration funnel analytics.
    Each step in the registration process creates an event.
    """
    EVENT_TYPES = [
        ('start', 'Memulai Registrasi'),
        ('email_phone_submit', 'Submit Email/Phone'),
        ('otp_sent', 'OTP Terkirim'),
        ('otp_verified', 'OTP Terverifikasi'),
        ('profile_submit', 'Submit Profil'),
        ('store_setup', 'Setup Toko'),
        ('complete', 'Registrasi Selesai'),
        ('abandon', 'Meninggalkan Registrasi'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='registration_events',
        null=True, blank=True
    )
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    role = models.CharField(max_length=20, blank=True, help_text='buyer/seller')
    
    # Context data
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    referrer = models.URLField(blank=True, null=True)
    utm_source = models.CharField(max_length=100, blank=True)
    utm_medium = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)
    
    # Timing
    duration_seconds = models.IntegerField(
        null=True, blank=True,
        help_text='Detik sejak event sebelumnya'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'registration_events'
        verbose_name = 'Event Registrasi'
        verbose_name_plural = 'Event Registrasi'
        indexes = [
            models.Index(fields=['event_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f'{self.get_event_type_display()} - {self.email or self.phone}'


# =============================================================================
# ENTERPRISE ADMIN MANAGEMENT
# =============================================================================

class AdminRole(models.Model):
    """
    Enterprise RBAC — defines admin roles with granular permissions.
    
    Roles hierarchy (by level):
        super_admin (100) — Full access, can manage other admins
        admin       (80)  — Full system access except admin management
        moderator   (60)  — Content moderation, user management
        support     (50)  — Customer support, order inquiries
        finance     (40)  — Payment, refund, financial reports
        content     (30)  — Content management, SEO, promotions
        viewer      (10)  — Read-only access to reports and analytics
    
    Admins can only manage accounts with a LOWER level than their own.
    """
    LEVEL_CHOICES = [
        (100, 'Super Admin'),
        (80,  'Admin'),
        (60,  'Moderator'),
        (50,  'Support'),
        (40,  'Finance'),
        (30,  'Content Manager'),
        (10,  'Viewer'),
    ]

    PERMISSION_CHOICES = [
        ('view_dashboard', 'View Dashboard'),
        ('manage_products', 'Manage Products'),
        ('manage_orders', 'Manage Orders'),
        ('manage_payments', 'Manage Payments'),
        ('manage_users', 'Manage Users'),
        ('manage_sellers', 'Manage Sellers'),
        ('manage_buyers', 'Manage Buyers'),
        ('manage_content', 'Manage Content'),
        ('manage_promotions', 'Manage Promotions'),
        ('manage_reports', 'Manage Reports'),
        ('manage_ai', 'Manage AI'),
        ('manage_system', 'Manage System'),
        ('manage_administrators', 'Manage Administrators'),
        ('view_audit_logs', 'View Audit Logs'),
        ('export_data', 'Export Data'),
    ]

    # Each role has a fixed name and level
    name = models.CharField(max_length=30, unique=True, verbose_name='Nama Role')
    level = models.IntegerField(choices=LEVEL_CHOICES, unique=True, verbose_name='Level')
    description = models.TextField(blank=True, verbose_name='Deskripsi')
    permissions = models.JSONField(
        default=list, blank=True,
        verbose_name='Permissions',
        help_text='Daftar permission yang dimiliki role ini'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin_roles'
        verbose_name = 'Role Administrator'
        verbose_name_plural = 'Role Administrator'
        ordering = ['-level']

    def __str__(self):
        return f'{self.get_level_display()} (Level {self.level})'

    def has_permission(self, permission):
        """Check if this role has a specific permission."""
        return permission in self.permissions

    @classmethod
    def get_default_permissions(cls, level):
        """Return default permission set for a given level."""
        all_perms = [p[0] for p in cls.PERMISSION_CHOICES]
        
        if level >= 100:  # Super Admin
            return all_perms
        if level >= 80:  # Admin
            return [p for p in all_perms if p != 'manage_administrators']
        if level >= 60:  # Moderator
            return ['view_dashboard', 'manage_products', 'manage_orders', 'manage_users',
                    'manage_sellers', 'manage_buyers', 'manage_content', 'view_audit_logs']
        if level >= 50:  # Support
            return ['view_dashboard', 'manage_orders', 'manage_users',
                    'manage_buyers', 'manage_sellers']
        if level >= 40:  # Finance
            return ['view_dashboard', 'manage_payments', 'manage_reports', 'manage_orders', 'export_data']
        if level >= 30:  # Content Manager
            return ['view_dashboard', 'manage_content', 'manage_promotions',
                    'manage_products', 'manage_sellers', 'export_data']
        # Viewer (10)
        return ['view_dashboard', 'manage_reports', 'view_audit_logs', 'export_data']


class AdminAuditLog(models.Model):
    """
    Enterprise audit trail for all administrator actions.
    
    Records every action performed by admin users for compliance
    and security monitoring. Logs are immutable — never deleted.
    """
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('login_failed', 'Login Gagal'),
        ('logout', 'Logout'),
        ('create_admin', 'Membuat Admin'),
        ('update_admin', 'Mengubah Admin'),
        ('delete_admin', 'Menghapus Admin'),
        ('activate_admin', 'Mengaktifkan Admin'),
        ('deactivate_admin', 'Menonaktifkan Admin'),
        ('change_password', 'Mengubah Password'),
        ('reset_password', 'Reset Password'),
        ('change_role', 'Mengubah Role'),
        ('verify_admin', 'Verifikasi Admin'),
        ('admin_verified_otp', 'Admin Verifikasi OTP'),
        ('system_config', 'Konfigurasi Sistem'),
    ]

    admin = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='audit_logs', verbose_name='Administrator'
    )
    admin_email = models.EmailField(verbose_name='Email Admin')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, verbose_name='Aksi')
    description = models.TextField(blank=True, verbose_name='Deskripsi')
    
    # Target of the action (if applicable)
    target_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='targeted_audit_logs', verbose_name='Target'
    )
    target_email = models.EmailField(blank=True, null=True, verbose_name='Email Target')
    
    # Request context
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    device_type = models.CharField(max_length=20, blank=True, null=True)
    browser = models.CharField(max_length=50, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    
    # Details stored as JSON for flexibility
    details = models.JSONField(default=dict, blank=True, verbose_name='Detail')
    
    # Automatic timestamp (immutable)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'admin_audit_logs'
        verbose_name = 'Log Audit Admin'
        verbose_name_plural = 'Log Audit Admin'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['admin', 'created_at']),
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['admin_email']),
        ]

    def __str__(self):
        return f'{self.admin_email} — {self.get_action_display()} at {self.created_at.strftime("%Y-%m-%d %H:%M")}'


class AdminVerification(models.Model):
    """
    Tracks email verification for newly created admin accounts.
    
    When a Super Admin creates a new admin account, a verification
    token/OTP is generated and sent to the new admin's email.
    The new admin must verify their email before first login.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Terverifikasi'),
        ('expired', 'Kadaluwarsa'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='admin_verifications'
    )
    email = models.EmailField(verbose_name='Email')
    otp_code = models.CharField(max_length=6, verbose_name='Kode OTP')
    otp_code_hash = models.CharField(max_length=64, verbose_name='Hash OTP')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=5)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_verifications'
    )

    class Meta:
        db_table = 'admin_verifications'
        verbose_name = 'Verifikasi Admin'
        verbose_name_plural = 'Verifikasi Admin'

    def __str__(self):
        return f'Verifikasi {self.email} — {self.get_status_display()}'

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def is_locked(self):
        return self.attempts >= self.max_attempts

    def increment_attempts(self):
        self.attempts += 1
        if self.attempts >= self.max_attempts:
            self.status = 'expired'
        self.save(update_fields=['attempts', 'status'])

    @staticmethod
    def generate_otp():
        import secrets
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])

    @staticmethod
    def hash_otp(code):
        import hashlib
        return hashlib.sha256(code.encode()).hexdigest()

    def save(self, *args, **kwargs):
        from django.utils import timezone
        from datetime import timedelta
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=15)
        if not self.otp_code:
            self.otp_code = self.generate_otp()
            self.otp_code_hash = self.hash_otp(self.otp_code)
        super().save(*args, **kwargs)
