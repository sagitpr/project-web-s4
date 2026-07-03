"""
Celery tasks for accounts — async OTP delivery.
Moves SMTP/WhatsApp HTTP calls (blocking) out of the request thread.
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def send_otp_task(self, identifier, otp_code, purpose='registration', user_full_name=None):
    """
    Send OTP code via email and/or WhatsApp asynchronously.
    Returns delivery status without blocking the register/login view.
    
    Retry up to 3 times with 5-second delays on failure.
    """
    from accounts.services.notification_service import notification_service
    
    try:
        result = notification_service.send_otp(
            identifier=identifier,
            otp_code=otp_code,
            purpose=purpose,
            user_full_name=user_full_name,
        )
        
        if result.get('success'):
            logger.info('OTP sent successfully to %s via %s', identifier, result.get('provider', 'unknown'))
        else:
            logger.warning('OTP delivery failed for %s: %s', identifier, result.get('error'))
        
        return {
            'success': result.get('success', False),
            'identifier': identifier,
            'purpose': purpose,
        }
        
    except Exception as exc:
        logger.error('OTP task error for %s: %s', identifier, str(exc))
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def send_whatsapp_only_otp_task(self, phone, otp_code, purpose='registration', user_full_name=None):
    """
    Send OTP via WhatsApp only (for phone-only identifiers).
    Separate task to avoid delays from email sending.
    """
    from accounts.services.whatsapp_service import send_whatsapp_otp, _whatsapp_configured
    
    if not _whatsapp_configured():
        logger.info('WhatsApp not configured, skipping OTP to %s', phone)
        return {'success': False, 'reason': 'not_configured', 'phone': phone}
    
    try:
        result = send_whatsapp_otp(
            phone=phone,
            otp_code=otp_code,
            purpose=purpose,
            user_full_name=user_full_name,
        )
        return {
            'success': result.get('success', False),
            'phone': phone,
            'provider': result.get('provider', 'unknown'),
        }
    except Exception as exc:
        logger.error('WhatsApp OTP error for %s: %s', phone, str(exc))
        raise self.retry(exc=exc)


@shared_task
def clean_expired_otps_task():
    """
    Periodically clean expired OTP records from the database.
    Runs daily via Celery Beat.
    """
    from django.utils import timezone
    from accounts.models import OTP
    
    cutoff = timezone.now() - timezone.timedelta(days=7)
    deleted, _ = OTP.objects.filter(created_at__lt=cutoff).delete()
    logger.info('Cleaned %s expired OTP records', deleted)
    return {'deleted': deleted}
