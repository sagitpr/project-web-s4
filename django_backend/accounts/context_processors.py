"""
Template context processors for Warungio Marketplace.
Provides site-wide variables to all templates.
"""

from django.conf import settings
from django.contrib.auth import get_user_model


def site_settings(request):
    """Provide site-wide settings to templates."""
    return {
        'site_name': 'Warungio',
        'site_description': 'Platform belanja kebutuhan sehari-hari langsung dari warung terdekat.',
        'debug': settings.DEBUG,
        'midtrans_client_key': settings.MIDTRANS_CLIENT_KEY,
        'midtrans_is_production': settings.MIDTRANS_IS_PRODUCTION,
        'otp_expire_minutes': settings.OTP_EXPIRE_MINUTES,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
        'google_client_id': settings.GOOGLE_CLIENT_ID,
        'current_year': 2026,
    }


def user_context(request):
    """Provide user-specific context to templates."""
    context = {
        'is_authenticated': request.user.is_authenticated,
    }

    if request.user.is_authenticated:
        user = request.user
        context.update({
            'user_full_name': user.full_name,
            'user_email': user.email,
            'user_role': user.role,
            'user_photo': user.profile_photo.url if user.profile_photo else None,
            'is_buyer': user.role == 'buyer',
            'is_seller': user.role == 'seller',
            'is_admin': user.role == 'admin' or user.is_superuser,
            'is_verified': user.is_verified,
        })

        # Add store info for sellers
        if user.role == 'seller' and hasattr(user, 'store'):
            store = user.store
            context.update({
                'store_name': store.store_name,
                'store_slug': store.slug,
                'store_id': store.id,
            })

    return context
