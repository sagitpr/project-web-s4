"""
Celery tasks for accounts — async OTP delivery.
Moves SMTP/WhatsApp HTTP calls (blocking) out of the request thread.
"""

import logging
from celery import shared_task
from config.celery import TRANSIENT_ERRORS

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5, autoretry_for=TRANSIENT_ERRORS)
def send_otp_task(self, identifier, otp_code, purpose='registration', user_full_name=None):
    """
    Send OTP code via email and/or WhatsApp asynchronously.
    Returns delivery status without blocking the register/login view.
    
    Retry up to 3 times with 5-second delays on failure.
    
    DIAGNOSTIC LOGGING: Each execution logs timing, retry count, and result.
    """
    import time
    _task_start = time.time()
    _retry_count = self.request.retries if hasattr(self, 'request') else 0
    
    logger.info(
        'CELERY_OTP_TASK [START] identifier=%s purpose=%s retry=%d/3',
        identifier, purpose, _retry_count,
    )
    
    from accounts.services.notification_service import notification_service
    
    try:
        result = notification_service.send_otp(
            identifier=identifier,
            otp_code=otp_code,
            purpose=purpose,
            user_full_name=user_full_name,
        )
        
        _task_elapsed = time.time() - _task_start
        
        if result.get('success'):
            logger.info(
                'CELERY_OTP_TASK [SUCCESS] identifier=%s purpose=%s retry=%d/3 '
                'duration=%.2fs provider=%s',
                identifier, purpose, _retry_count,
                _task_elapsed, result.get('provider', 'unknown'),
            )
        else:
            logger.warning(
                'CELERY_OTP_TASK [FAILED] identifier=%s purpose=%s retry=%d/3 '
                'duration=%.2fs error=%s result=%s',
                identifier, purpose, _retry_count,
                _task_elapsed, result.get('error'),
                {k: v for k, v in result.items() if k != 'otp_code'},
            )
        
        return {
            'success': result.get('success', False),
            'identifier': identifier,
            'purpose': purpose,
            'duration': round(_task_elapsed, 3),
            'retry_count': _retry_count,
        }
        
    except Exception as exc:
        _task_elapsed = time.time() - _task_start
        logger.error(
            'CELERY_OTP_TASK [EXCEPTION] identifier=%s purpose=%s retry=%d/3 '
            'duration=%.2fs error=%s',
            identifier, purpose, _retry_count,
            _task_elapsed, exc,
        )
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=10, autoretry_for=TRANSIENT_ERRORS)
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


@shared_task(max_retries=2, default_retry_delay=60, autoretry_for=TRANSIENT_ERRORS)
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


@shared_task(max_retries=2, default_retry_delay=60, autoretry_for=TRANSIENT_ERRORS)
def clean_expired_blacklisted_tokens_task():
    """
    Periodically clean expired blacklisted JWT tokens from the database.
    
    rest_framework_simplejwt stores all blacklisted tokens in the
    token_blacklist_blacklistedtoken table. Over time, this table grows
    and can slow down queries. This task removes tokens whose associated
    OutstandingToken has expired.
    
    Runs daily via Celery Beat at 4 AM.
    """
    from django.utils import timezone
    from rest_framework_simplejwt.token_blacklist.models import (
        BlacklistedToken, OutstandingToken
    )

    now = timezone.now()
    
    # Find all expired outstanding tokens and their blacklisted counterparts
    expired_outstanding = OutstandingToken.objects.filter(expires_at__lt=now)
    expired_count = expired_outstanding.count()
    
    if expired_count > 0:
        # Delete blacklisted tokens first (FK to outstanding)
        deleted_blacklisted = BlacklistedToken.objects.filter(
            token__in=expired_outstanding.values_list('id', flat=True)
        ).delete()[0]
        
        # Then delete expired outstanding tokens
        expired_outstanding.delete()
        
        logger.info(
            'Cleaned %d expired outstanding tokens and %d blacklisted tokens',
            expired_count, deleted_blacklisted
        )
        return {
            'deleted_outstanding': expired_count,
            'deleted_blacklisted': deleted_blacklisted,
        }
    
    logger.info('No expired tokens to clean')
    return {'deleted_outstanding': 0, 'deleted_blacklisted': 0}
