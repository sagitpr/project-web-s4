"""Google reCAPTCHA verification service."""

import logging
import requests
from django.conf import settings

logger = logging.getLogger('django_backend.accounts.captcha')


def verify_captcha_token(token: str, ip_address: str = None) -> bool:
    """Verify reCAPTCHA token against Google's API. Bypasses in DEBUG mode if unconfigured."""
    secret_key = getattr(settings, 'RECAPTCHA_SECRET_KEY', '')
    if not secret_key:
        if settings.DEBUG:
            return True
        logger.error("reCAPTCHA secret key missing in production")
        return False

    if not token:
        logger.warning("Empty reCAPTCHA token")
        return False

    verify_url = "https://www.google.com/recaptcha/api/siteverify"
    payload = {'secret': secret_key, 'response': token}
    if ip_address:
        payload['remoteip'] = ip_address

    try:
        res = requests.post(verify_url, data=payload, timeout=10)
        res.raise_for_status()
        result = res.json()
        if result.get('success'):
            return True
        logger.warning("reCAPTCHA failed: %s", result.get('error-codes'))
        return False
    except requests.RequestException:
        return settings.DEBUG
