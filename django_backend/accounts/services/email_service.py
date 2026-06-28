"""
Warungio Email Service — OTP email delivery via Django send_mail.

Provides:
- validate_email_settings()   — verify SMTP can connect
- send_otp_email(...)         — send a formatted OTP email
"""

import logging
from smtplib import SMTPException, SMTPAuthenticationError

from django.conf import settings
from django.core.mail import send_mail, BadHeaderError
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger('django_backend.accounts.email')


# ───────────────────────────── helpers ─────────────────────────────

def _email_configured() -> bool:
    """Return True if SMTP credentials are present."""
    return bool(settings.EMAIL_HOST_USER) and bool(settings.EMAIL_HOST_PASSWORD)


def _subject_for_purpose(purpose: str, otp_code: str) -> str:
    """Return a human-readable email subject based on OTP purpose."""
    labels = {
        'registration': 'Kode Verifikasi Akun Warungio',
        'login':        'Kode OTP Masuk Warungio',
        'password_reset': 'Kode OTP Reset Password Warungio',
        'email_change': 'Kode Verifikasi Email Baru',
        'phone_change': 'Kode Verifikasi Nomor HP',
        'payment':      'Kode Verifikasi Pembayaran',
    }
    base = labels.get(purpose, 'Kode Verifikasi Warungio')
    return f'{base} — {otp_code}'


# ───────────────────────── public functions ─────────────────────────

def validate_email_settings() -> dict:
    """
    Verify that the current EMAIL_* settings are plausible.

    Checks:
      - SMTP host / port are set
      - Credentials are non-empty
      - Django can connect (handshake)

    Returns a dict with keys:
      success  (bool)
      message  (str)
      error    (str | None)
    """
    errors = []

    if not settings.EMAIL_HOST:
        errors.append('EMAIL_HOST is not configured.')

    if not settings.EMAIL_PORT:
        errors.append('EMAIL_PORT is not configured.')

    if not _email_configured():
        errors.append('EMAIL_HOST_USER or EMAIL_HOST_PASSWORD is empty.')

    if not settings.DEFAULT_FROM_EMAIL:
        errors.append('DEFAULT_FROM_EMAIL is not set.')

    if errors:
        return {'success': False, 'message': '; '.join(errors), 'error': '; '.join(errors)}

    # Attempt a real SMTP handshake
    from smtplib import SMTP
    try:
        smtp = SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=10)
        smtp.ehlo_or_helo_if_needed()
        if settings.EMAIL_USE_TLS:
            smtp.starttls()
            smtp.ehlo_or_helo_if_needed()
        smtp.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        smtp.quit()
        return {'success': True, 'message': 'SMTP connection successful.', 'error': None}
    except SMTPAuthenticationError:
        msg = 'SMTP Authentication failed — check EMAIL_HOST_USER / EMAIL_HOST_PASSWORD.'
        logger.warning(msg)
        return {'success': False, 'message': msg, 'error': msg}
    except SMTPException as exc:
        msg = f'SMTP connection failed: {exc}'
        logger.warning(msg)
        return {'success': False, 'message': msg, 'error': str(exc)}
    except OSError as exc:
        msg = f'SMTP connection error (network): {exc}'
        logger.warning(msg)
        return {'success': False, 'message': msg, 'error': str(exc)}
    except Exception as exc:
        msg = f'Unexpected SMTP error: {exc}'
        logger.warning(msg)
        return {'success': False, 'message': msg, 'error': str(exc)}


def send_otp_email(
    email: str,
    otp_code: str,
    purpose: str = 'registration',
    expiry_minutes: int | None = None,
    user_full_name: str | None = None,
) -> dict:
    """
    Send an OTP email via Django's send_mail.

    Parameters
    ----------
    email : str
        Recipient email address.
    otp_code : str
        The 6-digit OTP code to embed in the message.
    purpose : str
        One of 'registration', 'login', 'password_reset', 'email_change',
        'phone_change', 'payment'.
    expiry_minutes : int | None
        Override the default OTP expiry from settings.
    user_full_name : str | None
        Personalise the greeting.

    Returns
    -------
    dict
        {
            'success': bool,
            'message': str,
            'error': str | None,
        }

    Behaviour on failure
    --------------------
    NEVER raises.  Returns a dict with ``success=False`` and a human-readable
    ``error`` so callers can issue a warning without rolling back the user/OTP.
    """
    if not _email_configured():
        msg = (
            'Email tidak dikirim — SMTP belum dikonfigurasi. '
            'Silakan atur EMAIL_HOST_USER dan EMAIL_HOST_PASSWORD di .env.'
        )
        logger.warning('send_otp_email skipped — SMTP not configured')
        return {'success': False, 'message': msg, 'error': msg}

    if expiry_minutes is None:
        expiry_minutes = getattr(settings, 'OTP_EXPIRE_MINUTES', 15)

    greeting = user_full_name or email.split('@')[0]

    # Build context for the template
    context = {
        'otp_code': otp_code,
        'expiry_minutes': expiry_minutes,
        'purpose': purpose,
        'user_full_name': user_full_name or '',
        'greeting': greeting,
        'site_name': 'Warungio',
        'support_email': settings.DEFAULT_FROM_EMAIL,
    }

    try:
        html_message = render_to_string('email/otp_email.txt', context)
        # The .txt template is actually HTML — strip tags for the plain-text fallback
        plain_message = strip_tags(html_message)
        subject = _subject_for_purpose(purpose, otp_code)

        sent_count = send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )

        if sent_count == 1:
            logger.info('OTP email sent to %s (purpose=%s)', email, purpose)
            return {'success': True, 'message': 'Email OTP berhasil dikirim.', 'error': None}

        msg = 'Gagal mengirim email — jumlah penerima 0.'
        logger.error('send_mail returned 0 for %s', email)
        return {'success': False, 'message': msg, 'error': msg}

    except BadHeaderError:
        msg = 'Header email tidak valid.'
        logger.exception('BadHeaderError for %s', email)
        return {'success': False, 'message': msg, 'error': msg}
    except SMTPAuthenticationError:
        msg = 'Gagal mengirim email — autentikasi SMTP ditolak. Periksa kredensial email.'
        logger.exception('SMTP auth failed for %s', email)
        return {'success': False, 'message': msg, 'error': msg}
    except SMTPException:
        msg = 'Gagal mengirim email — masalah koneksi SMTP. Silakan coba lagi.'
        logger.exception('SMTP error for %s', email)
        return {'success': False, 'message': msg, 'error': msg}
    except (ConnectionError, TimeoutError) as exc:
        msg = f'Gagal mengirim email — koneksi timeout: {exc}'
        logger.exception('Network error for %s', email)
        return {'success': False, 'message': msg, 'error': str(exc)}
    except Exception:
        msg = 'Gagal mengirim email — kesalahan sistem. Silakan coba lagi nanti.'
        logger.exception('Unexpected error sending email to %s', email)
        return {'success': False, 'message': msg, 'error': msg}
