"""
Warungio Registration Service — Multi-step registration flow.

Supports:
- Step 1: Email/Phone submission
- Step 2: OTP verification  
- Step 3: Profile completion (name, address)
- Step 4: Store setup (for sellers)
- Complete: Account activation

Tracks registration funnel events for analytics.
"""

import logging
from uuid import uuid4

from django.db import transaction
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model

from .email_service import send_otp_email
from .whatsapp_service import send_whatsapp_otp

logger = logging.getLogger('django_backend.accounts.registration')

User = get_user_model()


def start_registration(
    email: str = None,
    phone: str = None,
    role: str = 'buyer',
    ip_address: str = None,
    user_agent: str = None,
    referrer: str = None,
    utm_source: str = None,
    utm_medium: str = None,
    utm_campaign: str = None,
) -> dict:
    """
    Step 1: Start registration process.
    
    Creates a partial user record or validates that the email/phone is available.
    Sends OTP to the provided email or phone.
    
    Returns:
        dict with user_id, message, next_step, and registration_id
    """
    if not email and not phone:
        return {
            'success': False,
            'error': 'Email atau nomor HP harus diisi.',
        }

    # Check if user already exists
    if email:
        if User.objects.filter(email=email).exists():
            return {
                'success': False,
                'error': 'Email sudah terdaftar. Silakan login.',
            }
    
    if phone:
        if User.objects.filter(phone=phone).exists():
            return {
                'success': False,
                'error': 'Nomor HP sudah terdaftar. Silakan login.',
            }

    # Create partial user
    username = (email or phone).split('@')[0] if email else f'user_{phone[-6:]}'
    
    with transaction.atomic():
        user = User.objects.create(
            email=email or f'{uuid4().hex[:8]}@temp.warungio.com',
            phone=phone,
            username=username,
            full_name='',
            role=role,
            is_active=True,
            is_verified=False,
            registration_step='email_phone',
            registration_started_at=timezone.now(),
        )
        
        # Send OTP
        otp_delivery = _send_registration_otp(user, email, phone, 'registration', ip_address, user_agent)
        
        # Track event
        _track_event(user, 'email_phone_submit', ip_address, user_agent)
    
    return {
        'success': True,
        'message': 'Kode OTP telah dikirim. Silakan verifikasi.',
        'user_id': user.id,
        'next_step': 'otp',
        'next_endpoint': '/api/auth/registration/verify-otp/',
        'otp_delivery': otp_delivery,
        **({'otp_code': otp_delivery.get('otp_code')} if settings.DEBUG else {}),
    }


def verify_registration_otp(
    user_id: int,
    otp_code: str,
    ip_address: str = None,
    user_agent: str = None,
) -> dict:
    """
    Step 2: Verify OTP code for registration.
    
    Returns:
        dict with success, message, next_step
    """
    from ..models import OTP
    
    try:
        user = User.objects.get(id=user_id, registration_step='email_phone')
    except User.DoesNotExist:
        return {'success': False, 'error': 'Pengguna tidak ditemukan atau langkah tidak valid.'}

    # Find valid OTP
    otp = OTP.objects.filter(
        user=user,
        purpose='registration',
        is_valid=True,
        is_used=False,
        otp_code=otp_code,
    ).first()

    if not otp:
        return {'success': False, 'error': 'Kode OTP tidak valid.'}

    if otp.is_expired():
        otp.is_valid = False
        otp.save()
        return {'success': False, 'error': 'Kode OTP sudah kadaluwarsa. Silakan minta ulang.'}

    if otp.is_locked():
        return {
            'success': False,
            'error': 'Terlalu banyak percobaan. Silakan minta OTP baru.',
            'needs_new_otp': True,
        }

    # Verify
    otp.is_used = True
    otp.is_valid = False
    otp.verified_at = timezone.now()
    otp.save()

    # Update user step
    user.registration_step = 'otp'
    user.save(update_fields=['registration_step'])

    # Track event
    _track_event(user, 'otp_verified', ip_address, user_agent)

    return {
        'success': True,
        'message': 'Verifikasi OTP berhasil.',
        'user_id': user.id,
        'next_step': 'profile',
        'next_endpoint': '/api/auth/registration/complete-profile/',
    }


def complete_profile(
    user_id: int,
    full_name: str,
    password: str,
    email: str = None,
    phone: str = None,
    address: str = None,
    province: str = None,
    city: str = None,
    district: str = None,
    postal_code: str = None,
    nik: str = None,
) -> dict:
    """
    Step 3: Complete user profile for registration.
    
    Sets the password and profile information.
    
    Returns:
        dict with success, message, next_step (store_setup for sellers, complete for buyers)
    """
    try:
        user = User.objects.get(id=user_id, registration_step='otp')
    except User.DoesNotExist:
        return {'success': False, 'error': 'Pengguna tidak ditemukan atau langkah tidak valid.'}

    with transaction.atomic():
        # Update profile
        if full_name:
            user.full_name = full_name
        if email:
            # Update temp email to real one
            user.email = email
        if phone:
            user.phone = phone
        if address:
            user.address = address
        
        # Set password
        if password:
            user.set_password(password)
        
        # Validate NIK if provided
        if nik:
            from .indonesia_validators import validate_nik
            nik_result = validate_nik(nik)
            if nik_result['valid']:
                user.nik = nik
            else:
                return {
                    'success': False,
                    'error': '; '.join(nik_result['errors']),
                    'nik_errors': nik_result['errors'],
                }

        # Determine next step
        if user.role == 'seller':
            user.registration_step = 'store_setup'
            next_step = 'store_setup'
            next_endpoint = '/api/auth/registration/setup-store/'
            message = 'Profil berhasil diisi. Silakan setup toko Anda.'
        else:
            user.registration_step = 'complete'
            user.is_verified = True
            user.registration_completed_at = timezone.now()
            next_step = 'complete'
            next_endpoint = ''
            message = 'Registrasi selesai! Selamat bergabung di Warungio.'

        user.save()

        # Track event
        _track_event(user, 'profile_submit')

    return {
        'success': True,
        'message': message,
        'user_id': user.id,
        'next_step': next_step,
        'next_endpoint': next_endpoint,
    }


def setup_seller_store(
    user_id: int,
    store_name: str,
    store_description: str = None,
    store_address: str = None,
    store_phone: str = None,
    operating_hours: dict = None,
) -> dict:
    """
    Step 4 (seller only): Create seller's store.
    
    Creates a Store record linked to the user.
    
    Returns:
        dict with success, message, store data
    """
    try:
        user = User.objects.get(id=user_id, registration_step='store_setup', role='seller')
    except User.DoesNotExist:
        return {'success': False, 'error': 'Pengguna tidak ditemukan atau bukan seller.'}

    from stores.models import Store
    
    with transaction.atomic():
        # Create store
        store = Store.objects.create(
            user=user,
            store_name=store_name,
            description=store_description or '',
            address=store_address or user.address or '',
            phone=store_phone or str(user.phone) if user.phone else '',
            operating_hours=operating_hours or {},
            status='active',
            is_active=True,
        )
        
        # Complete registration
        user.registration_step = 'complete'
        user.is_verified = True
        user.registration_completed_at = timezone.now()
        user.save()

        # Track event
        _track_event(user, 'store_setup')

    return {
        'success': True,
        'message': 'Toko berhasil dibuat! Selamat bergabung sebagai Mitra Warungio.',
        'store': {
            'id': store.id,
            'name': store.store_name,
            'slug': store.slug,
        },
        'next_step': 'complete',
    }


def get_registration_status(user_id: int) -> dict:
    """Get current registration step and progress."""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {'success': False, 'error': 'Pengguna tidak ditemukan.'}

    step_order = ['email_phone', 'otp', 'profile', 'store_setup', 'complete']
    current_idx = step_order.index(user.registration_step) if user.registration_step in step_order else 0
    total_steps = 4 if user.role == 'seller' else 3
    
    step_labels = {
        'email_phone': 'Email/Telepon',
        'otp': 'Verifikasi OTP',
        'profile': 'Profil',
        'store_setup': 'Setup Toko',
        'complete': 'Selesai',
    }

    return {
        'success': True,
        'current_step': user.registration_step,
        'current_step_label': step_labels.get(user.registration_step, ''),
        'progress': f'{current_idx}/{total_steps}',
        'progress_percent': int((current_idx / total_steps) * 100),
        'is_complete': user.registration_step == 'complete',
        'role': user.role,
    }


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _send_registration_otp(user, email, phone, purpose, ip_address, user_agent):
    """Send OTP for registration via email and/or WhatsApp."""
    from ..models import OTP
    
    otp = OTP.objects.create(
        user=user,
        email=email or user.email,
        phone=str(phone) if phone else None,
        purpose=purpose,
        ip_address=ip_address,
        user_agent=user_agent or '',
    )
    
    result = {'method': None, 'success': False}
    
    # Send via email
    if email:
        email_result = send_otp_email(
            email=email,
            otp_code=otp.otp_code,
            purpose=purpose,
            user_full_name='',
        )
        result['method'] = 'email'
        result['success'] = email_result.get('success', False)
        if not result['success']:
            result['warning'] = email_result.get('error', 'Gagal mengirim email OTP.')
    
    # Send via WhatsApp if phone available (uses Fonnte or configured provider)
    if phone:
        wa_result = send_whatsapp_otp(
            phone=str(phone),
            otp_code=otp.otp_code,
            purpose=purpose,
        )
        if wa_result.get('success'):
            result['method'] = 'whatsapp'
            result['success'] = True
            logger.info(
                'WhatsApp OTP sent via %s to %s',
                wa_result.get('provider', 'unknown'), phone
            )
    
    result['otp_code'] = otp.otp_code if settings.DEBUG else None
    
    # Track event
    _track_event(user, 'otp_sent', ip_address, user_agent)
    
    return result


def _track_event(user, event_type, ip_address=None, user_agent=None):
    """Track registration funnel event."""
    from ..models import RegistrationEvent
    
    try:
        RegistrationEvent.objects.create(
            user=user,
            email=user.email,
            phone=str(user.phone) if user.phone else None,
            event_type=event_type,
            role=user.role,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except Exception as e:
        logger.warning('Failed to track registration event: %s', e)
