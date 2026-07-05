"""
Signals for payments app — auto-create Wallet on User creation.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Wallet

logger = logging.getLogger(__name__)


@receiver(post_save, sender=settings.AUTH_USER_MODEL, weak=False)
def create_user_wallet(sender, instance, created, **kwargs):
    """Auto-create a Wallet for every new User."""
    if created:
        try:
            Wallet.objects.get_or_create(user=instance, defaults={'balance': 0})
            logger.debug('Wallet auto-created for user: %s', instance.email)
        except Exception as e:
            logger.error('Failed to create wallet for user %s: %s', instance.email, e)
