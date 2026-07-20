"""
Admin-specific serializers for Warungio Marketplace.
Separated from public serializers to enforce strict role-based access.

The AdminLoginSerializer checks admin status BEFORE authenticating to
prevent leaking authentication success to non-admin users.
"""

import logging
from rest_framework import serializers
from django.contrib.auth import authenticate

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
            # Use the same error message to prevent user enumeration
            raise serializers.ValidationError(
                "Email atau password salah.", code='authorization'
            )

        attrs['user'] = user
        return attrs
