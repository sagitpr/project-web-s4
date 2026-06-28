"""
Accounts app models - User, OTP, Address management.
Warungio Marketplace - Hybrid Django + PHP.
"""

import uuid
import random
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
        ]

    def __str__(self):
        return self.full_name or self.email

    def save(self, *args, **kwargs):
        if not self.full_name:
            self.full_name = self.get_full_name() or self.email.split('@')[0]
        if not self.username:
            self.username = self.email.split('@')[0]
        super().save(*args, **kwargs)


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
        """Generate a secure random OTP code."""
        return ''.join([str(random.randint(0, 9)) for _ in range(length)])

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
