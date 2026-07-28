"""OTP email delivery via Django send_mail."""

import logging
from smtplib import SMTPException, SMTPAuthenticationError

from django.conf import settings
from django.core.mail import send_mail, BadHeaderError
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger('django_backend.accounts.email')


def _email_configured() -> bool:
    return bool(settings.EMAIL_HOST_USER) and bool(settings.EMAIL_HOST_PASSWORD)


def _subject_for_purpose(purpose: str, otp_code: str) -> str:
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


def validate_email_settings() -> dict:
    """Verify SMTP settings and attempt a connection handshake."""
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


def _create_otp_inapp_notification(email_addr, otp, otp_purpose, otp_expiry):
    """Create in-app notification fallback for OTP delivery.

    CRITICAL: This function is a MODULE-LEVEL helper (not nested inside send_otp_email)
    to avoid NameError when called at the top of send_otp_email() before any
    nested function definition would execute.

    Previously defined as a nested function DEEPER inside send_otp_email(), but
    the function was already being called at the TOP of send_otp_email() before
    the def statement was reached. This caused NameError every time SMTP was
    not configured — silently crashing the OTP delivery pipeline.
    """
    try:
        from notifications.services import notify_system
        from accounts.models import User
        user = User.objects.filter(email=email_addr).first()
        if not user:
            logger.warning('OTP in-app notification skipped — user not found for %s', email_addr)
            return
        purpose_labels = {
            'registration': 'Verifikasi Akun',
            'login': 'Verifikasi Login',
            'password_reset': 'Reset Password',
        }
        label = purpose_labels.get(otp_purpose, 'Verifikasi')

        # In production, only show "Cek email Anda" message (never expose OTP in notification)
        # In DEBUG mode, include OTP code for testing convenience
        if settings.DEBUG:
            desc = f'Kode {label} Anda: {otp} — Berlaku {otp_expiry} menit'
        else:
            desc = f'Kode {label} telah dikirim ke {email_addr}. Periksa inbox/spam Anda. Jika tidak ada, minta ulang.'

        notify_system(
            user_id=user.id,
            title=f'{label} — Kode OTP',
            description=desc,
            action_url=f'/auth/otp/?email={email_addr}&purpose={otp_purpose}',
        )
        logger.info('OTP in-app notification created for %s (purpose=%s)', email_addr, otp_purpose)
    except Exception as notif_err:
        logger.warning('Failed to create OTP in-app notification: %s', notif_err)


def send_otp_email(
    email: str,
    otp_code: str,
    purpose: str = 'registration',
    expiry_minutes: int | None = None,
    user_full_name: str | None = None,
) -> dict:
    """Send an OTP email via Django's send_mail. Never raises on failure.

    ENHANCED LOGGING: Every step is logged with timestamps so we can trace
    exactly where the pipeline fails:
    1. SMTP config check → log config status
    2. Template rendering → log success/failure
    3. send_mail() call → log send_mail response duration
    4. SMTP response → log sent_count and any error detail
    5. Each exception handler → log exception type and full trace
    """
    import time
    _start_ts = time.time()

    if not _email_configured():
        msg = (
            'Email tidak dikirim — SMTP belum dikonfigurasi. '
            'Silakan atur EMAIL_HOST_USER dan EMAIL_HOST_PASSWORD di .env.'
        )
        logger.warning(
            'OTP_EMAIL_DIAG [CONFIG MISSING] Email=%s Purpose=%s Elapsed=%.2fs | %s',
            email, purpose, time.time() - _start_ts, msg,
        )
        # Create in-app notification fallback so user still gets the OTP
        _create_otp_inapp_notification(email, otp_code, purpose, expiry_minutes)
        return {'success': False, 'message': msg, 'error': msg, 'in_app_fallback': True}

    logger.info(
        'OTP_EMAIL_DIAG [CONFIG OK] Email=%s Purpose=%s Host=%s:%s TLS=%s From=%s',
        email, purpose,
        settings.EMAIL_HOST, settings.EMAIL_PORT,
        settings.EMAIL_USE_TLS, settings.DEFAULT_FROM_EMAIL,
    )

    if expiry_minutes is None:
        expiry_minutes = getattr(settings, 'OTP_EXPIRE_MINUTES', 15)

    greeting = user_full_name or email.split('@')[0]

    purpose_labels = {
        'registration': 'pendaftaran',
        'login': 'masuk',
        'password_reset': 'reset password',
        'email_change': 'ubah email',
        'phone_change': 'ubah nomor HP',
        'payment': 'pembayaran',
    }

    # Build context for the template
    context = {
        'otp_code': otp_code,
        'expiry_minutes': expiry_minutes,
        'purpose': purpose,
        'purpose_label': purpose_labels.get(purpose, 'verifikasi'),
        'user_full_name': user_full_name or '',
        'greeting': greeting,
        'site_name': 'Warungio',
        'support_email': settings.DEFAULT_FROM_EMAIL,
    }

    try:
        # Try the .html template first, fall back to .txt for backward compat
        try:
            from django.template import TemplateDoesNotExist
            html_message = render_to_string('email/otp_email.html', context)
            logger.info(
                'OTP_EMAIL_DIAG [TEMPLATE OK] Email=%s Template=html Duration=%.2fs',
                email, time.time() - _start_ts,
            )
        except TemplateDoesNotExist:
            html_message = render_to_string('email/otp_email.txt', context)
            logger.info(
                'OTP_EMAIL_DIAG [TEMPLATE OK] Email=%s Template=txt Duration=%.2fs',
                email, time.time() - _start_ts,
            )
        # Strip tags for the plain-text fallback
        plain_message = strip_tags(html_message)
        subject = _subject_for_purpose(purpose, otp_code)

        _before_send = time.time()
        sent_count = send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        _send_duration = time.time() - _before_send

        if sent_count == 1:
            logger.info(
                'OTP_EMAIL_DIAG [DELIVERED] Email=%s Purpose=%s SendDuration=%.2fs '
                'TotalElapsed=%.2fs sent_count=%d',
                email, purpose, _send_duration, time.time() - _start_ts, sent_count,
            )
            return {
                'success': True,
                'message': 'Email OTP berhasil dikirim.',
                'error': None,
                'send_duration': round(_send_duration, 3),
                'sent_count': sent_count,
            }

        msg = 'Gagal mengirim email — jumlah penerima 0.'
        logger.error(
            'OTP_EMAIL_DIAG [SEND_FAILED] Email=%s Purpose=%s SendDuration=%.2fs sent_count=%d',
            email, purpose, _send_duration, sent_count,
        )
        return {
            'success': False, 'message': msg, 'error': msg,
            'send_duration': round(_send_duration, 3),
            'sent_count': sent_count,
        }

    except BadHeaderError:
        msg = 'Header email tidak valid.'
        logger.exception(
            'OTP_EMAIL_DIAG [ERROR BadHeaderError] Email=%s Purpose=%s Elapsed=%.2fs',
            email, purpose, time.time() - _start_ts,
        )
        return {'success': False, 'message': msg, 'error': msg}
    except SMTPAuthenticationError:
        msg = 'Gagal mengirim email — autentikasi SMTP ditolak. Periksa kredensial email.'
        logger.exception(
            'OTP_EMAIL_DIAG [ERROR SMTPAuth] Email=%s Purpose=%s Elapsed=%.2fs',
            email, purpose, time.time() - _start_ts,
        )
        _create_otp_inapp_notification(email, otp_code, purpose, expiry_minutes)
        return {'success': False, 'message': msg, 'error': msg, 'in_app_fallback': True}
    except SMTPException:
        msg = 'Gagal mengirim email — masalah koneksi SMTP. Silakan coba lagi.'
        logger.exception(
            'OTP_EMAIL_DIAG [ERROR SMTP] Email=%s Purpose=%s Elapsed=%.2fs',
            email, purpose, time.time() - _start_ts,
        )
        _create_otp_inapp_notification(email, otp_code, purpose, expiry_minutes)
        return {'success': False, 'message': msg, 'error': msg, 'in_app_fallback': True}
    except (ConnectionError, TimeoutError) as exc:
        msg = f'Gagal mengirim email — koneksi timeout: {exc}'
        logger.exception(
            'OTP_EMAIL_DIAG [ERROR Network] Email=%s Purpose=%s Elapsed=%.2fs error=%s',
            email, purpose, time.time() - _start_ts, exc,
        )
        return {'success': False, 'message': msg, 'error': str(exc)}
    except Exception:
        msg = 'Gagal mengirim email — kesalahan sistem. Silakan coba lagi nanti.'
        logger.exception(
            'OTP_EMAIL_DIAG [ERROR Unexpected] Email=%s Purpose=%s Elapsed=%.2fs',
            email, purpose, time.time() - _start_ts,
        )
        return {'success': False, 'message': msg, 'error': msg}
