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


def send_otp_email(
    email: str,
    otp_code: str,
    purpose: str = 'registration',
    expiry_minutes: int | None = None,
    user_full_name: str | None = None,
) -> dict:
    """Send an OTP email via Django's send_mail. Never raises on failure."""
    if not _email_configured():
        msg = (
            'Email tidak dikirim — SMTP belum dikonfigurasi. '
            'Silakan atur EMAIL_HOST_USER dan EMAIL_HOST_PASSWORD di .env.'
        )
        logger.warning('send_otp_email skipped — SMTP not configured')
        # Create in-app notification fallback so user still gets the OTP
        _create_otp_inapp_notification(email, otp_code, purpose, expiry_minutes)
        return {'success': False, 'message': msg, 'error': msg}

    # ── IN-APP NOTIFICATION FALLBACK on email failure ──
    # If email sending fails, we create an in-app notification so the user
    # can see the OTP in their Notification Center on the web/app.
    # This is a last-resort delivery method when SMTP is unavailable.
    def _create_otp_inapp_notification(email_addr, otp, otp_purpose, otp_expiry):
        """Create in-app notification fallback for OTP delivery."""
        try:
            from notifications.services import create_notification
            from accounts.models import User
            user = User.objects.filter(email=email_addr).first()
            if not user:
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
            
            create_notification(
                user_id=user.id,
                notification_type='system',
                priority='high',
                title=f'{label} — Kode OTP',
                description=desc,
                action_url=f'/auth/otp/?email={email_addr}&purpose={otp_purpose}',
                action_text='Verifikasi Sekarang',
                metadata={'otp_purpose': otp_purpose, 'email': email_addr},
            )
        except Exception as notif_err:
            logger.warning('Failed to create OTP in-app notification: %s', notif_err)

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
        except TemplateDoesNotExist:
            html_message = render_to_string('email/otp_email.txt', context)
        # Strip tags for the plain-text fallback
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
        _create_otp_inapp_notification(email, otp_code, purpose, expiry_minutes)
        return {'success': False, 'message': msg, 'error': msg}
    except (ConnectionError, TimeoutError) as exc:
        msg = f'Gagal mengirim email — koneksi timeout: {exc}'
        logger.exception('Network error for %s', email)
        return {'success': False, 'message': msg, 'error': str(exc)}
    except Exception:
        msg = 'Gagal mengirim email — kesalahan sistem. Silakan coba lagi nanti.'
        logger.exception('Unexpected error sending email to %s', email)
        return {'success': False, 'message': msg, 'error': msg}
