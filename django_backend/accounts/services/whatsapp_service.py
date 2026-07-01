"""
Warungio WhatsApp Service — OTP delivery via WhatsApp for Indonesian users.

Provides:
- send_whatsapp_otp() — send OTP via WhatsApp
- Supports multiple providers: Fonnte, Twilio WhatsApp, WATI, or direct API
- Fonnte is the primary provider for Indonesian users
- Falls back gracefully when not configured
"""

import logging
from django.conf import settings

logger = logging.getLogger('django_backend.accounts.whatsapp')


def _whatsapp_configured() -> bool:
    """
    Return True if any WhatsApp provider credentials are configured.
    
    Priority:
    1. Fonnte (if WHATSAPP_FONNTE_API_KEY is set)
    2. Other providers (if WHATSAPP_PROVIDER + WHATSAPP_API_KEY + WHATSAPP_PHONE_NUMBER_ID are set)
    """
    # Check Fonnte first (primary provider for Indonesian users)
    if settings.WHATSAPP_FONNTE_API_KEY:
        return True
    # Fallback to other providers
    return bool(
        settings.WHATSAPP_PROVIDER
        and settings.WHATSAPP_API_KEY
        and settings.WHATSAPP_PHONE_NUMBER_ID
    )


def send_whatsapp_otp(
    phone: str,
    otp_code: str,
    purpose: str = 'registration',
    user_full_name: str | None = None,
) -> dict:
    """
    Send an OTP code via WhatsApp.
    
    Parameters
    ----------
    phone : str
        Recipient phone number in international format (+628xx...).
    otp_code : str
        The 6-digit OTP code.
    purpose : str
        One of 'registration', 'login', 'password_reset'.
    user_full_name : str | None
        Personalise the greeting.
    
    Returns
    -------
    dict
        {'success': bool, 'message': str, 'error': str | None}
    
    NEVER raises. Returns success=False with error message on failure.
    """
    if not _whatsapp_configured():
        msg = (
            'WhatsApp OTP tidak terkirim — kredensial WhatsApp belum dikonfigurasi. '
            'Set WHATSAPP_PROVIDER, WHATSAPP_API_KEY, dan WHATSAPP_PHONE_NUMBER_ID di .env.'
        )
        logger.warning('send_whatsapp_otp skipped — WhatsApp not configured')
        return {'success': False, 'message': msg, 'error': msg}

    # Fonnte is the primary provider — check if Fonnte API key is configured
    if settings.WHATSAPP_FONNTE_API_KEY:
        return _send_via_fonnte(phone, otp_code, purpose, user_full_name)

    provider = (settings.WHATSAPP_PROVIDER or '').lower()

    if provider == 'fonnte':
        return _send_via_fonnte(phone, otp_code, purpose, user_full_name)
    elif provider == 'twilio':
        return _send_via_twilio(phone, otp_code, purpose, user_full_name)
    elif provider == 'wati':
        return _send_via_wati(phone, otp_code, purpose, user_full_name)
    elif provider == 'direct':
        return _send_via_direct_api(phone, otp_code, purpose, user_full_name)
    else:
        return {
            'success': False,
            'message': f'WhatsApp provider "{provider}" tidak dikenal.',
            'error': f'Unknown provider: {provider}',
        }


def _send_via_twilio(
    phone: str,
    otp_code: str,
    purpose: str = 'registration',
    user_full_name: str | None = None,
) -> dict:
    """Send OTP via Twilio WhatsApp API."""
    try:
        from twilio.rest import Client

        account_sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        from_number = f'whatsapp:{settings.WHATSAPP_PHONE_NUMBER_ID}'
        to_number = f'whatsapp:{phone}'

        purpose_labels = {
            'registration': 'verifikasi akun',
            'login': 'masuk',
            'password_reset': 'reset password',
        }
        label = purpose_labels.get(purpose, 'verifikasi')

        greeting = f"Hai {user_full_name},\n\n" if user_full_name else "Hai,\n\n"
        body = (
            f"{greeting}"
            f"Kode OTP {label} Warungio Anda adalah:\n\n"
            f"*{otp_code}*\n\n"
            f"Kode berlaku selama {settings.OTP_EXPIRE_MINUTES} menit.\n"
            f"Jangan bagikan kode ini kepada siapa pun.\n\n"
            f"Warungio — Belanja dari Warung Terdekat"
        )

        client = Client(account_sid, auth_token)
        message = client.messages.create(
            from_=from_number,
            body=body,
            to=to_number,
        )

        logger.info(
            'WhatsApp OTP sent via Twilio to %s (purpose=%s, sid=%s)',
            phone, purpose, message.sid
        )
        return {
            'success': True,
            'message': 'Kode OTP berhasil dikirim via WhatsApp.',
            'error': None,
            'provider_message_id': message.sid,
        }

    except Exception as e:
        logger.exception('Twilio WhatsApp error for %s', phone)
        return {
            'success': False,
            'message': 'Gagal mengirim OTP via WhatsApp. Silakan coba lagi.',
            'error': str(e),
        }


def _send_via_wati(
    phone: str,
    otp_code: str,
    purpose: str = 'registration',
    user_full_name: str | None = None,
) -> dict:
    """Send OTP via WATI (whatsapp team inbox) API."""
    try:
        import requests

        api_key = settings.WHATSAPP_API_KEY
        base_url = settings.WHATSAPP_BASE_URL or 'https://wati.com/api/v1'

        purpose_labels = {
            'registration': 'verifikasi akun',
            'login': 'masuk',
            'password_reset': 'reset password',
        }
        label = purpose_labels.get(purpose, 'verifikasi')

        greeting = f"Hai {user_full_name},\n" if user_full_name else "Hai,\n"
        body = (
            f"{greeting}"
            f"Kode OTP {label} Warungio Anda: {otp_code}\n"
            f"Berlaku {settings.OTP_EXPIRE_MINUTES} menit.\n"
            f"Jangan bagikan kode ini.\n\n"
            f"Warungio"
        )

        response = requests.post(
            f'{base_url}/sendTemplateMessage',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'phone': phone,
                'template_name': 'otp_message',
                'parameters': [
                    {'name': 'otp_code', 'value': otp_code},
                    {'name': 'purpose', 'value': label},
                    {'name': 'expiry', 'value': str(settings.OTP_EXPIRE_MINUTES)},
                ],
            },
            timeout=15,
        )

        if response.status_code in (200, 201):
            logger.info('WhatsApp OTP sent via WATI to %s', phone)
            return {
                'success': True,
                'message': 'Kode OTP berhasil dikirim via WhatsApp.',
                'error': None,
                'provider_message_id': response.json().get('messageId'),
            }
        else:
            logger.error(
                'WATI API error: %s %s', response.status_code, response.text
            )
            return {
                'success': False,
                'message': 'Gagal mengirim OTP via WhatsApp.',
                'error': f'WATI API error: {response.status_code}',
            }

    except ImportError:
        return {
            'success': False,
            'message': 'Modul requests tidak tersedia.',
            'error': 'requests library not installed',
        }
    except Exception as e:
        logger.exception('WATI error for %s', phone)
        return {
            'success': False,
            'message': 'Gagal mengirim OTP via WhatsApp.',
            'error': str(e),
        }


def _send_via_fonnte(
    phone: str,
    otp_code: str,
    purpose: str = 'registration',
    user_full_name: str | None = None,
) -> dict:
    """
    Send OTP via Fonnte WhatsApp Gateway (Indonesia).
    
    Fonnte is the primary WhatsApp provider for Indonesian users.
    API docs: https://docs.fonnte.com/api-send-message/
    
    Authentication uses token (WITHOUT 'Bearer' prefix) in Authorization header.
    API key format typically starts with 'fsk_'.
    """
    try:
        import requests

        api_key = settings.WHATSAPP_FONNTE_API_KEY
        api_url = 'https://api.fonnte.com/send'

        purpose_labels = {
            'registration': 'verifikasi akun',
            'login': 'masuk',
            'password_reset': 'reset password',
        }
        label = purpose_labels.get(purpose, 'verifikasi')

        # Build OTP message in Indonesian
        greeting = f"Hai {user_full_name},\n\n" if user_full_name else "Hai Pengguna Warungio,\n\n"
        message = (
            f"{greeting}"
            f"Kode OTP {label} Warungio Anda adalah:\n\n"
            f"*{otp_code}*\n\n"
            f"Kode ini berlaku selama {settings.OTP_EXPIRE_MINUTES} menit.\n"
            f"Jangan bagikan kode ini kepada siapa pun, termasuk pihak yang mengaku dari Warungio.\n\n"
            f"Abaikan jika Anda tidak melakukan permintaan ini.\n\n"
            f"— Warungio"
        )

        # Fonnte API: Authorization WITHOUT 'Bearer' prefix
        response = requests.post(
            api_url,
            headers={
                'Authorization': api_key,  # Fonnte does NOT use 'Bearer' prefix
            },
            data={
                'target': phone,
                'message': message,
                'countryCode': '62',  # Indonesia
                'typing': False,
            },
            timeout=15,
        )

        result = response.json()

        if response.status_code in (200, 201) and result.get('status'):
            logger.info(
                'WhatsApp OTP sent via Fonnte to %s (purpose=%s, id=%s)',
                phone, purpose, result.get('id'),
            )
            return {
                'success': True,
                'message': 'Kode OTP berhasil dikirim via WhatsApp.',
                'error': None,
                'provider': 'fonnte',
                'provider_message_id': result.get('id', []),
            }
        else:
            error_msg = result.get('reason', 'Unknown error')
            logger.error(
                'Fonnte API error for %s: %s %s',
                phone, response.status_code, response.text,
            )
            return {
                'success': False,
                'message': 'Gagal mengirim OTP via WhatsApp.',
                'error': f'Fonnte API error: {error_msg}',
                'provider': 'fonnte',
            }

    except ImportError:
        return {
            'success': False,
            'message': 'Modul requests tidak tersedia.',
            'error': 'requests library not installed',
            'provider': 'fonnte',
        }
    except requests.exceptions.Timeout:
        logger.exception('Fonnte timeout for %s', phone)
        return {
            'success': False,
            'message': 'Gagal mengirim OTP via WhatsApp — koneksi timeout.',
            'error': 'Fonnte API timeout',
            'provider': 'fonnte',
        }
    except Exception as e:
        logger.exception('Fonnte API error for %s', phone)
        return {
            'success': False,
            'message': 'Gagal mengirim OTP via WhatsApp. Silakan coba lagi.',
            'error': str(e),
            'provider': 'fonnte',
        }


def _send_via_direct_api(
    phone: str,
    otp_code: str,
    purpose: str = 'registration',
    user_full_name: str | None = None,
) -> dict:
    """Send OTP via direct WhatsApp API (e.g., Wabox, Chat-API, etc.)."""
    try:
        import requests

        api_key = settings.WHATSAPP_API_KEY
        api_url = settings.WHATSAPP_API_URL or 'https://api.chat-api.com/instance/sendMessage'
        phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID

        purpose_labels = {
            'registration': 'verifikasi akun',
            'login': 'masuk',
            'password_reset': 'reset password',
        }
        label = purpose_labels.get(purpose, 'verifikasi')

        body = (
            f"Hai {user_full_name or 'Pengguna Warungio'},\n\n"
            f"Kode OTP {label} Anda: {otp_code}\n"
            f"Berlaku {settings.OTP_EXPIRE_MINUTES} menit.\n"
            f"Jangan bagikan kode ini kepada siapa pun.\n\n"
            f"Warungio"
        )

        response = requests.post(
            api_url,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'phone': phone,
                'body': body,
                'token': api_key,
            },
            timeout=15,
        )

        if response.status_code in (200, 201):
            logger.info('WhatsApp OTP sent via Direct API to %s', phone)
            return {
                'success': True,
                'message': 'Kode OTP berhasil dikirim via WhatsApp.',
                'error': None,
            }
        else:
            return {
                'success': False,
                'message': 'Gagal mengirim OTP via WhatsApp.',
                'error': f'API error: {response.status_code}',
            }

    except ImportError:
        return {
            'success': False,
            'message': 'Modul requests tidak tersedia.',
            'error': 'requests library not installed',
        }
    except Exception as e:
        logger.exception('Direct WhatsApp API error for %s', phone)
        return {
            'success': False,
            'message': 'Gagal mengirim OTP via WhatsApp.',
            'error': str(e),
        }
