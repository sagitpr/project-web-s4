"""
Admin-specific serializers for Warungio Marketplace.
Separated from public serializers to enforce strict role-based access.

The AdminLoginSerializer checks admin status BEFORE authenticating to
prevent leaking authentication success to non-admin users.
"""

import logging
from rest_framework import serializers
from django.contrib.auth import authenticate, password_validation

from .models import User

logger = logging.getLogger(__name__)


class AdminLoginSerializer(serializers.Serializer):
    """
    Admin-only login serializer.
    
    Differs from the public LoginSerializer in two ways:
    1. Only accepts email (not phone) for admin accounts
    2. Checks is_staff status after authentication and rejects non-staff users
    3. Uses a consistent error message regardless of whether the user exists
       (prevents user enumeration)
    """
    email = serializers.EmailField(required=True, max_length=254)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        email = attrs.get('email', '').strip().lower()
        password = attrs.get('password')

        if not email or not password:
            raise serializers.ValidationError(
                "Email dan password harus diisi.", code='authorization'
            )

        # Authenticate using EmailBackend
        user = authenticate(
            request=self.context.get('request'),
            email=email,
            password=password,
        )

        if not user:
            logger.warning(
                'ADMIN LOGIN FAILED — Email: %s | Authentication failed',
                email,
            )
            raise serializers.ValidationError(
                "Email atau password salah.", code='authorization'
            )

        # Enforce admin-only access — check AFTER authentication to avoid
        # leaking whether a valid non-admin account exists
        if user.role != 'admin' and not user.is_staff and not user.is_superuser:
            logger.warning(
                'ADMIN LOGIN REJECTED — User %s (role=%s) authenticated but is not staff',
                user.email, user.role
            )
            raise serializers.ValidationError(
                "Email atau password salah.", code='authorization'
            )

        # ── Zero Trust Authentication Messages ──
        # Use a SINGLE generic error message for ALL auth failures after initial
        # credential check, regardless of whether the account is inactive,
        # unverified, or has any other restriction.
        #
        # This prevents account enumeration attacks where an attacker could
        # distinguish between "account doesn't exist" vs "account exists but
        # is inactive/unverified" by comparing error messages.
        #
        # Detailed reasons are ONLY logged to the audit trail for internal
        # monitoring, NEVER returned to the client.
        if not user.is_active or (not user.is_verified and not user.is_superuser):
            if not user.is_active:
                logger.warning(
                    'ADMIN LOGIN REJECTED — User %s account is deactivated',
                    user.email,
                )
            if not user.is_verified and not user.is_superuser:
                logger.warning(
                    'ADMIN LOGIN REJECTED — User %s has not verified email',
                    user.email,
                )
            raise serializers.ValidationError(
                "Email atau password salah.",
                code='authorization'
            )

        attrs['user'] = user
        return attrs


class AdminForgotPasswordSerializer(serializers.Serializer):
    """
    Admin forgot password serializer.
    Validates email format and returns consistent response
    regardless of whether the email exists (prevents enumeration).
    """
    email = serializers.EmailField(required=True, max_length=254)


class AdminVerifyOTPSerializer(serializers.Serializer):
    """
    Admin OTP verification serializer.
    Validates OTP code format before database lookup.
    """
    email = serializers.EmailField(required=True, max_length=254)
    otp_code = serializers.CharField(required=True, min_length=6, max_length=6)

    def validate_otp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Kode OTP harus berupa angka.")
        return value


class AdminResetPasswordSerializer(serializers.Serializer):
    """
    Admin reset password serializer.
    
    Uses `verification_token` (TimestampSigner) as the primary auth factor
    since step 2 already verified the OTP. The `otp_code` is optional —
    when provided it's used for defense-in-depth re-verification, but
    the verification token alone is sufficient proof of prior OTP verification.
    """
    email = serializers.EmailField(required=True, max_length=254)
    otp_code = serializers.CharField(
        required=False, allow_blank=True
    )
    verification_token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True, validators=[password_validation.validate_password]
    )
    new_password2 = serializers.CharField(required=True)

    def validate_otp_code(self, value):
        if value and not value.isdigit():
            raise serializers.ValidationError("Kode OTP harus berupa angka.")
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                "new_password": "Password baru tidak cocok."
            })
        return attrs


# =============================================================================
# ENTERPRISE ADMIN MANAGEMENT SERIALIZERS
# =============================================================================

class AdminUserListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing administrators in the admin management table.
    Includes computed fields for role display, status, and activity.
    """
    role_display = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    last_login_display = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'username', 'role', 'role_display',
            'status', 'is_active', 'is_verified', 'is_staff', 'is_superuser',
            'last_login', 'last_login_display', 'date_joined',
            'profile_photo', 'created_by',
        ]

    def get_role_display(self, obj):
        if obj.is_superuser:
            return 'Super Admin'
        if obj.role == 'admin' or obj.is_staff:
            return 'Admin'
        return 'Staff'

    def get_status(self, obj):
        if not obj.is_active:
            return 'nonaktif'
        if not obj.is_verified:
            return 'pending'
        return 'aktif'

    def get_last_login_display(self, obj):
        if obj.last_login:
            from django.utils.timesince import timesince
            return f'{timesince(obj.last_login)} yang lalu'
        return 'Belum pernah login'

    def get_created_by(self, obj):
        # This is a simplified version — in production, track via AdminAuditLog
        return None


class AdminUserCreateSerializer(serializers.Serializer):
    """Serializer for creating a new administrator account."""
    email = serializers.EmailField(required=True, max_length=254)
    username = serializers.CharField(required=False, max_length=100)
    full_name = serializers.CharField(required=True, max_length=100)
    password = serializers.CharField(
        required=True, validators=[password_validation.validate_password],
        write_only=True
    )
    password2 = serializers.CharField(required=True, write_only=True)
    phone = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        from .models import User
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email sudah terdaftar.')
        return value

    def validate_username(self, value):
        from .models import User
        if value and User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username sudah digunakan.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': 'Password tidak cocok.'})
        return attrs


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating an administrator's information."""
    full_name = serializers.CharField(required=False, max_length=100)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ['full_name', 'phone']

    def validate_phone(self, value):
        if not value:
            return None
        return value


class AdminDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for a single administrator."""
    role_display = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    last_login_display = serializers.SerializerMethodField()
    date_joined_display = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'username', 'role', 'role_display',
            'status', 'is_active', 'is_verified', 'is_staff', 'is_superuser',
            'last_login', 'last_login_display', 'date_joined', 'date_joined_display',
            'profile_photo', 'phone', 'last_login_ip', 'is_mobile', 'is_desktop',
            'browser_family', 'os_family',
        ]

    def get_role_display(self, obj):
        if obj.is_superuser:
            return 'Super Admin'
        if obj.is_staff:
            return 'Admin'
        return obj.get_role_display() if hasattr(obj, 'get_role_display') else obj.role

    def get_status(self, obj):
        if not obj.is_active:
            return 'nonaktif'
        if not obj.is_verified:
            return 'pending'
        return 'aktif'

    def get_last_login_display(self, obj):
        if obj.last_login:
            from django.utils.timesince import timesince
            return f'{timesince(obj.last_login)} yang lalu'
        return 'Belum pernah login'

    def get_date_joined_display(self, obj):
        if obj.date_joined:
            return obj.date_joined.strftime('%d %B %Y, %H:%M')
        return ''


class AdminVerifyOTPSerializer(serializers.Serializer):
    """Serializer for verifying admin OTP during email verification."""
    email = serializers.EmailField(required=True, max_length=254)
    otp_code = serializers.CharField(required=True, min_length=6, max_length=6)
    verification_id = serializers.IntegerField(required=False)

    def validate_otp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError('Kode OTP harus berupa angka.')
        return value


class AdminResendOTPSerializer(serializers.Serializer):
    """Serializer for resending admin verification OTP."""
    email = serializers.EmailField(required=True, max_length=254)
    verification_id = serializers.IntegerField(required=False)
