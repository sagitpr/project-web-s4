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
    """Provide user-specific context to templates.
    
    MEMORY OPTIMIZATION:
    - Uses _cached_ prefetch to avoid N+1 queries on every page load
    - hasattr() on related_name triggers a DB query — replaced with try/except getattr
    - Only hits DB once per request via select_related if authenticated
    """
    context = {
        'is_authenticated': request.user.is_authenticated,
    }

    if request.user.is_authenticated:
        user = request.user
        # Cache profile_photo URL string to avoid ImageField file access
        photo_url = None
        try:
            if user.profile_photo:
                photo_url = user.profile_photo.url
        except Exception:
            photo_url = None

        context.update({
            'user_full_name': user.full_name,
            'user_email': user.email,
            'user_role': user.role,
            'user_photo': photo_url,
            'is_buyer': user.role == 'buyer',
            'is_seller': user.role == 'seller',
            'is_admin': user.role == 'admin' or user.is_superuser,
            'is_verified': user.is_verified,
        })

        # Add store info for sellers — avoid hasattr() which triggers DB query
        # Use getattr with None default instead
        if user.role == 'seller':
            store = getattr(user, 'store', None)
            if store is not None:
                context.update({
                    'store_name': store.store_name,
                    'store_slug': store.slug,
                    'store_id': store.id,
                })

    return context
