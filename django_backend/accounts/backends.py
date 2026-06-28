import logging
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

logger = logging.getLogger('django_backend.accounts')


class EmailBackend(ModelBackend):
    """
    Custom authentication backend that supports login via email or phone number.
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

        if user.check_password(password) and self.user_can_authenticate(user):
            logger.info('Login success: %s', user.email)
            return user

        logger.warning('Login failed: wrong password or user inactive (%s)', user.email)
        return None
