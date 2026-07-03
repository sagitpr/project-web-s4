import logging
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger('django_backend.accounts')


def get_client_ip(request):
    """Extract client IP from request."""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', None)


class EmailBackend(ModelBackend):
    """
    Custom authentication backend that supports login via email or phone number.
    Includes account lockout (brute force protection) and failed login tracking.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        if username is None:
            username = kwargs.get('email')

        if not username or not password:
            return None

        # Build standard lookups (by email or raw username)
        lookups = Q(email__iexact=username) | Q(phone=username)
        
        # Try normalizing as Indonesian phone number to match DB format (+628...)
        import re
        cleaned = re.sub(r'[^\d+]', '', str(username))
        if cleaned.startswith('+628'):
            lookups |= Q(phone=cleaned)
        elif cleaned.startswith('628'):
            lookups |= Q(phone='+' + cleaned)
        elif cleaned.startswith('08'):
            lookups |= Q(phone='+62' + cleaned[1:])
            
        try:
            user = User.objects.get(lookups)
        except User.DoesNotExist:
            logger.warning('Login failed: user not found (%s)', username[:30])
            return None
        except User.MultipleObjectsReturned:
            logger.warning('Login failed: multiple users found (%s)', username[:30])
            return None

        # ── Brute Force Protection ──
        if user.is_account_locked():
            remaining = int((user.locked_until - timezone.now()).total_seconds() // 60)
            logger.warning('Login rejected: account locked for user %s (%d min remaining)', user.email, remaining)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            logger.info('Login success: %s', user.email)
            return user

        # ── Failed Login Tracking ──
        logger.warning('Login failed: wrong password or user inactive (%s)', user.email)
        user.increment_failed_login()
        return None
