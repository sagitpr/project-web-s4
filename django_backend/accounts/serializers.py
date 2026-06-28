import re
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.password_validation import validate_password

from .models import User, OTP


def normalize_indonesian_phone(value):
    if not value:
        raise serializers.ValidationError("Nomor HP wajib diisi.")
    
    # Strip spaces, hyphens, parentheses, and non-digit/non-plus characters
    cleaned = re.sub(r'[^\d+]', '', str(value))
    
    # Try parsing
    if cleaned.startswith('+62'):
        if not cleaned.startswith('+628'):
            raise serializers.ValidationError("Nomor HP harus menggunakan prefix provider Indonesia (08xx / 628xx / +628xx).")
        digits_only = cleaned[1:]
        if not (11 <= len(digits_only) <= 14):
            raise serializers.ValidationError("Panjang nomor HP tidak valid (harus 10-13 digit).")
        return cleaned
        
    elif cleaned.startswith('62'):
        if not cleaned.startswith('628'):
            raise serializers.ValidationError("Nomor HP harus menggunakan prefix provider Indonesia (08xx / 628xx / +628xx).")
        if not (11 <= len(cleaned) <= 14):
            raise serializers.ValidationError("Panjang nomor HP tidak valid (harus 10-13 digit).")
        return '+' + cleaned
        
    elif cleaned.startswith('08'):
        normalized = '+62' + cleaned[1:]
        digits_only = normalized[1:]
        if not (11 <= len(digits_only) <= 14):
            raise serializers.ValidationError("Panjang nomor HP tidak valid (harus 10-13 digit).")
        return normalized
        
    else:
        raise serializers.ValidationError("Format nomor HP tidak valid. Gunakan format seperti 08xxxxxxxxxx atau +628xxxxxxxxxx.")



class RegisterSerializer(serializers.ModelSerializer):
    """User registration serializer with OTP support."""
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)
    full_name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'phone', 'password', 'password2',
                  'address', 'role')

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email sudah terdaftar.")
        return value

    def validate_phone(self, value):
        normalized = normalize_indonesian_phone(value)
        if User.objects.filter(phone=normalized).exists():
            raise serializers.ValidationError("Nomor HP sudah terdaftar.")
        return normalized

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password2'):
            raise serializers.ValidationError({
                "password": "Password tidak cocok."
            })
        if attrs.get('role') not in ['buyer', 'seller']:
            attrs['role'] = 'buyer'
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.username = validated_data['email'].split('@')[0]
        user.is_active = True
        user.is_verified = False
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    """User login serializer."""
    email = serializers.CharField(required=True, max_length=254)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                email=email, password=password
            )
            if not user:
                raise serializers.ValidationError(
                    "Email atau password salah.", code='authorization'
                )
        else:
            raise serializers.ValidationError(
                "Email dan password harus diisi.", code='authorization'
            )

        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """Detailed user serializer."""
    wallet_balance = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()
    birth_date = serializers.SerializerMethodField()
    job = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    province = serializers.SerializerMethodField()
    zip_code = serializers.SerializerMethodField()
    business_name = serializers.SerializerMethodField()
    business_type = serializers.SerializerMethodField()
    business_scale = serializers.SerializerMethodField()
    business_description = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'phone', 'role', 'address',
                  'profile_photo', 'bio', 'is_verified', 'is_mobile',
                  'is_tablet', 'is_desktop', 'created_at',
                  'wallet_balance', 'gender', 'birth_date', 'job',
                  'city', 'province', 'zip_code',
                  'business_name', 'business_type', 'business_scale', 'business_description')
        read_only_fields = ('id', 'is_verified', 'created_at', 'wallet_balance')

    def get_wallet_balance(self, obj):
        if not obj.device_info:
            return 2350000.0
        return float(obj.device_info.get('wallet_balance', 2350000.0))

    def get_gender(self, obj):
        return obj.device_info.get('gender', '') if obj.device_info else ''

    def get_birth_date(self, obj):
        return obj.device_info.get('birth_date', '') if obj.device_info else ''

    def get_job(self, obj):
        return obj.device_info.get('job', '') if obj.device_info else ''

    def get_city(self, obj):
        return obj.device_info.get('city', '') if obj.device_info else ''

    def get_province(self, obj):
        return obj.device_info.get('province', '') if obj.device_info else ''

    def get_zip_code(self, obj):
        return obj.device_info.get('zip_code', '') if obj.device_info else ''

    def get_business_name(self, obj):
        return obj.device_info.get('business_name', '') if obj.device_info else ''

    def get_business_type(self, obj):
        return obj.device_info.get('business_type', '') if obj.device_info else ''

    def get_business_scale(self, obj):
        return obj.device_info.get('business_scale', '') if obj.device_info else ''

    def get_business_description(self, obj):
        return obj.device_info.get('business_description', '') if obj.device_info else ''


class UserUpdateSerializer(serializers.ModelSerializer):
    """User profile update serializer."""
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    gender = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    birth_date = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    job = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    city = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    province = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    zip_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    business_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    business_type = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    business_scale = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    business_description = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ('full_name', 'phone', 'address', 'bio', 'profile_photo',
                  'gender', 'birth_date', 'job', 'city', 'province', 'zip_code',
                  'business_name', 'business_type', 'business_scale', 'business_description')

    def validate_phone(self, value):
        if not value:
            return None
        normalized = normalize_indonesian_phone(value)
        user = self.instance
        if User.objects.filter(phone=normalized).exclude(pk=user.pk if user else None).exists():
            raise serializers.ValidationError("Nomor HP sudah terdaftar.")
        return normalized

    def update(self, instance, validated_data):
        virtual_fields = [
            'gender', 'birth_date', 'job', 'city', 'province', 'zip_code',
            'business_name', 'business_type', 'business_scale', 'business_description'
        ]
        if not instance.device_info:
            instance.device_info = {}
        for field in virtual_fields:
            if field in validated_data:
                instance.device_info[field] = validated_data.pop(field)
        return super().update(instance, validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    """Change password serializer."""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True, validators=[validate_password]
    )
    new_password2 = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Password lama tidak sesuai.")
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                "new_password": "Password baru tidak cocok."
            })
        return attrs


class OTPRequestSerializer(serializers.Serializer):
    """Request OTP code serializer."""
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    purpose = serializers.ChoiceField(
        choices=['registration', 'login', 'password_reset', 'email_change',
                 'phone_change', 'payment'],
        default='registration'
    )

    def validate(self, attrs):
        if not attrs.get('email') and not attrs.get('phone'):
            raise serializers.ValidationError(
                "Email atau nomor HP harus diisi."
            )
        return attrs


class OTPVerifySerializer(serializers.Serializer):
    """Verify OTP code serializer."""
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    otp_code = serializers.CharField(required=True, min_length=6, max_length=6)
    purpose = serializers.ChoiceField(
        choices=['registration', 'login', 'password_reset', 'email_change',
                 'phone_change', 'payment'],
        default='registration'
    )

    def validate_otp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Kode OTP harus berupa angka.")
        return value


class TokenSerializer(serializers.Serializer):
    """JWT token response serializer."""
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()


class ForgotPasswordSerializer(serializers.Serializer):
    """Forgot password request serializer."""
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Email tidak ditemukan dalam sistem."
            )
        return value


class ResetPasswordSerializer(serializers.Serializer):
    """Reset password with OTP serializer."""
    email = serializers.EmailField(required=True)
    otp_code = serializers.CharField(required=True, min_length=6, max_length=6)
    new_password = serializers.CharField(
        required=True, validators=[validate_password]
    )
    new_password2 = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                "new_password": "Password tidak cocok."
            })
        return attrs
