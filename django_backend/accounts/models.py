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
