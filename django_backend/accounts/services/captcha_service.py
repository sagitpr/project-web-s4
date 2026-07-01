"""
Google reCAPTCHA verification service for Warungio.
Provides server-side validation of client-side captcha tokens to protect auth endpoints.
"""

import logging
import requests
from django.conf import settings

logger = logging.getLogger('django_backend.accounts.captcha')


def verify_captcha_token(token: str, ip_address: str = None) -> bool:
    """
    Verify reCAPTCHA token against Google's API.
    
    Parameters
    ----------
    token : str
        The reCAPTCHA token sent by the client.
    ip_address : str | None
        Optional client IP address.
        
    Returns
    -------
    bool
        True if verification succeeds, False otherwise.
    """
    # 1. Dev fallback: bypass if not configured or under DEBUG mode
    secret_key = getattr(settings, 'RECAPTCHA_SECRET_KEY', '')
    if not secret_key:
        if settings.DEBUG:
            logger.info("reCAPTCHA validation bypassed in DEBUG mode (no secret key configured).")
            return True
        logger.error("reCAPTCHA secret key is missing in production environment!")
        return False

    if not token:
        logger.warning("Empty reCAPTCHA token submitted.")
        return False

    # 2. Call Google siteverify API
    verify_url = "https://www.google.com/recaptcha/api/siteverify"
    payload = {
        'secret': secret_key,
        'response': token
    }
    if ip_address:
        payload['remoteip'] = ip_address

    try:
        response = requests.post(verify_url, data=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        success = result.get('success', False)
        if success:
            logger.info("reCAPTCHA token verified successfully.")
            return True
        else:
            logger.warning(f"reCAPTCHA token verification failed. Errors: {result.get('error-codes', [])}")
            return False
            
    except requests.RequestException as e:
        logger.error(f"Network error during reCAPTCHA verification: {str(e)}")
        # In case of service downtime, fall back to True in DEBUG, False in Production
        return settings.DEBUG
