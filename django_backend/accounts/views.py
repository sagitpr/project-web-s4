"""
Accounts views for Warungio Marketplace.
Authentication, OTP verification, profile management.
"""

import logging
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from rest_framework import serializers as drf_serializers, status, generics, permissions, views, throttling

logger = logging.getLogger(__name__)

# ── Instrumentation helpers ──
REGISTER_SENSITIVE_FIELDS = frozenset({'password', 'password2', 'captcha_token'})
OTP_SENSITIVE_FIELDS = frozenset({'otp_code'})
LOGIN_SENSITIVE_FIELDS = frozenset({'password'})

def _mask_payload(data):
    """Return a copy of request data with sensitive field values masked."""
    masked = {}
    sensitive = REGISTER_SENSITIVE_FIELDS | OTP_SENSITIVE_FIELDS | LOGIN_SENSITIVE_FIELDS
    for k, v in data.items():
        if k in sensitive:
            masked[k] = '***MASKED***'
        else:
            masked[k] = str(v)[:200] if v is not None else None
    return masked

def _log_db_operation(op_name, details, duration_ms=None):
    """Log a database operation with optional duration."""
    log_data = {'operation': op_name, 'details': details}
    if duration_ms is not None:
        log_data['duration_ms'] = round(duration_ms, 1)
    logger.debug('DB: %s | %s', op_name, details)
    return log_data

def _make_field_error(field, message, code):
    """Build a structured field-specific error response."""
    return Response(
        {'field': field, 'message': message, 'code': code},
        status=status.HTTP_400_BAD_REQUEST
    )

from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, OTP, LoginAttempt
from .services.whatsapp_service import _whatsapp_configured
from .serializers import (
    RegisterSerializer, LoginSerializer, UserSerializer,
    UserUpdateSerializer, ChangePasswordSerializer,
    OTPRequestSerializer, OTPVerifySerializer,
    ForgotPasswordSerializer, ResetPasswordSerializer,
    TokenSerializer
)


def get_client_ip(request):
    """Extract client IP from request."""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', None)


def _dispatch_otp_async(email, phone, otp_code, purpose, user_full_name=None):
   
    from .tasks import send_otp_task, send_whatsapp_only_otp_task
    
    channels = []
    
    def safe_delay(task_func, **kwargs):
        """Call task.delay() with a timeout-safe wrapper."""
        try:
            task_func.delay(**kwargs)
            return True
        except Exception as exc:
            logger.warning(
                'Celery unavailable — OTP delivery skipped for %s/%s: %s',
                kwargs.get('identifier', kwargs.get('phone', 'unknown')),
                kwargs.get('purpose', 'unknown'),
                exc,
            )
            return False
    
    if email:
        safe_delay(
            send_otp_task,
            identifier=email,
            otp_code=otp_code,
            purpose=purpose,
            user_full_name=user_full_name,
        )
        channels.append('email')
    
    if phone and _whatsapp_configured():
        safe_delay(
            send_whatsapp_only_otp_task,
            phone=phone,
            otp_code=otp_code,
            purpose=purpose,
            user_full_name=user_full_name,
        )
        if 'whatsapp' not in channels:
            channels.append('whatsapp')
    
    return channels


class RegisterView(generics.CreateAPIView):
    """User registration endpoint."""
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:200]
        
        # ────────────────────────────────────────────────────────────────────
        #  INSTRUMENTATION: Log the COMPLETE incoming request payload
        #  (sensitive fields masked, non-sensitive shown in full)
        # ────────────────────────────────────────────────────────────────────
        logger.info(
            'REGISTER REQUEST — IP: %s | User-Agent: %s | Complete payload: %s',
            ip,
            user_agent,
            _mask_payload(dict(request.data.items())),
        )
        
        # ────────────────────────────────────────────────────────────────────
        #  VALIDATION
        # ────────────────────────────────────────────────────────────────────
        if not serializer.is_valid():
            error_detail = dict(serializer.errors)
            payload_masked = _mask_payload(dict(request.data.items()))
            
            logger.warning(
                'REGISTER VALIDATION FAILED — IP: %s | Errors: %s | Payload: %s',
                ip,
                error_detail,
                payload_masked,
            )
            
            # Log every single field error with received value (or MASKED for sensitive)
            for field, field_errors in serializer.errors.items():
                for err in field_errors:
                    raw_val = request.data.get(field, 'MISSING')
                    val_preview = '***MASKED***' if field in REGISTER_SENSITIVE_FIELDS else str(raw_val)[:200]
                    logger.warning(
                        '  REGISTER FIELD ERROR — Field: "%s" | Error: %s | Value: %s',
                        field,
                        str(err),
                        val_preview,
                    )
            
            # Log the error response that will be sent back
            logger.warning(
                'REGISTER ERROR RESPONSE — HTTP 400 | Response: {\"success\": false, \"errors\": %s}',
                error_detail,
            )
            
            raise drf_serializers.ValidationError(serializer.errors)
        
        # ────────────────────────────────────────────────────────────────────
        #  SUCCESS: Create user, send OTP
        # ────────────────────────────────────────────────────────────────────
        user = serializer.save()

        # Send OTP for verification
        otp = OTP.objects.create(
            user=user,
            email=user.email,
            phone=str(user.phone) if user.phone else None,
            purpose='registration',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )

        # Dispatch OTP delivery to Celery worker (non-blocking)
        channels = _dispatch_otp_async(
            email=user.email,
            phone=str(user.phone) if user.phone else None,
            otp_code=otp.otp_code,
            purpose='registration',
            user_full_name=user.full_name,
        )

        response_data = {
            'message': 'Registrasi berhasil. Silakan verifikasi OTP.',
            'otp_channels': list(set(channels)),
            'user': UserSerializer(user).data,
        }

        if settings.DEBUG:
            response_data['otp_code'] = otp.otp_code
        
        # ────────────────────────────────────────────────────────────────────
        #  INSTRUMENTATION: Log the response body (without full user data)
        # ────────────────────────────────────────────────────────────────────
        response_log = {
            'status': 'success',
            'user_id': user.id,
            'email': user.email,
            'role': user.role,
            'otp_channels': list(set(channels)),
        }
        if settings.DEBUG:
            response_log['otp_code'] = otp.otp_code
        logger.info('REGISTER RESPONSE — HTTP 201 | Response: %s', response_log)

        return Response(response_data, status=status.HTTP_201_CREATED)


class LoginView(views.APIView):
    """User login with JWT token response."""
    permission_classes = (permissions.AllowAny,)
    throttle_classes = [throttling.AnonRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:200]
        login_entry = request.data.get('login_entry')
        
        # ── INSTRUMENTATION: Log incoming payload ──
        raw_payload = dict(request.data.items())
        logger.info(
            'LOGIN REQUEST — IP: %s | User-Agent: %s | Complete payload: %s | login_entry: %s',
            ip, user_agent,
            _mask_payload(raw_payload),
            login_entry or '(none)',
        )
        
        serializer = LoginSerializer(data=request.data, context={'request': request})
        
        # ── INSTRUMENTATION: Validate and log errors ──
        if not serializer.is_valid():
            error_detail = dict(serializer.errors)
            payload_masked = _mask_payload(raw_payload)
            
            logger.warning(
                'LOGIN VALIDATION FAILED — IP: %s | Request payload: %s | Errors: %s',
                ip, payload_masked, error_detail,
            )
            
            # Log every single field error with received value
            for field, field_errors in serializer.errors.items():
                for err in field_errors:
                    raw_val = request.data.get(field, 'MISSING')
                    val_preview = '***MASKED***' if field in LOGIN_SENSITIVE_FIELDS else str(raw_val)[:200]
                    logger.warning(
                        '  LOGIN FIELD ERROR — Field: "%s" | Error: %s | Received: %s',
                        field, str(err), val_preview,
                    )
            
            # Log the full error response that will be returned
            logger.warning(
                'LOGIN ERROR RESPONSE — HTTP 400 | Response: {\"success\": false, \"errors\": %s}',
                error_detail,
            )
            
            raise drf_serializers.ValidationError(serializer.errors)
        
        user = serializer.validated_data['user']
        
        # ── INSTRUMENTATION: Log authentication result ──
        logger.info(
            'LOGIN AUTH SUCCESS — Email: %s | User ID: %d | Role: %s | IsVerified: %s | IP: %s',
            user.email, user.id, user.role, user.is_verified, ip,
        )
        
        # Check OTP verification
        if not user.is_verified:
            logger.warning(
                'LOGIN BLOCKED — Unverified user | Email: %s | IP: %s',
                user.email, ip,
            )
            return Response({
                'error': 'Akun belum diverifikasi. Silakan verifikasi OTP terlebih dahulu.',
                'needs_verification': True,
                'email': user.email,
            }, status=status.HTTP_403_FORBIDDEN)
        
        # ── Role-gate: validate login_entry against the user's actual role ──
        login_entry = serializer.validated_data.get('login_entry')
        if login_entry and user.role != login_entry:
            role_label = 'Mitra Penjual' if login_entry == 'seller' else 'Pembeli'
            logger.warning(
                'LOGIN BLOCKED — Role mismatch | Email: %s | User role: %s | Login entry: %s | IP: %s',
                user.email, user.role, login_entry, ip,
            )
            return Response({
                'error': f'Akun ini tidak terdaftar sebagai {role_label}.',
                'code': 'role_mismatch',
                'user_role': user.role,
                'login_entry': login_entry,
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        
        # ── Set Django session cookie ──
        # Required for login_protected template pages (/buyer/, /seller/, etc.)
        # to recognize the user. Without this, login_required decorator would
        # redirect back to /auth/login/ creating a redirect loop.
        login(request, user)
        
        # Reset failed login counters + update IP (single save)
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_ip = get_client_ip(request)
        user.save(update_fields=['failed_login_attempts', 'locked_until', 'last_login_ip'])
        _log_db_operation('user_reset_failed_login', {'user_id': user.id})
        
        # Track login
        LoginAttempt.objects.create(
            email=user.email,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            was_successful=True,
        )
        _log_db_operation('login_attempt_create', {'email': user.email, 'success': True})
        
        response_data = {
            'message': 'Login berhasil.',
            'access': access_token,
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        }
        
        # ── INSTRUMENTATION: Log response ──
        response_log = {
            'status': 'success',
            'user_id': user.id,
            'email': user.email,
            'role': user.role,
            'is_verified': user.is_verified,
            'registration_step': user.registration_step,
        }
        logger.info('LOGIN RESPONSE — HTTP 200 | Response: %s', response_log)
        
        return Response(response_data)


class LogoutView(views.APIView):
    """User logout - blacklist refresh token."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            logout(request)
            return Response({'message': 'Logout berhasil.'})
        except Exception as e:
            logger.warning('Logout error (non-blocking): %s', str(e))
            return Response({'message': 'Logout berhasil.'})


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get/update user profile."""
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def patch(self, request, *args, **kwargs):
        serializer = UserUpdateSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(views.APIView):
    """Change password for authenticated user."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({'message': 'Password berhasil diubah.'})


class OTPRequestView(views.APIView):
    """Request OTP code for verification."""
    permission_classes = (permissions.AllowAny,)
    throttle_scope = 'otp'

    def post(self, request):
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:200]
        
        # ── INSTRUMENTATION: Log incoming payload ──
        logger.info(
            'OTP REQUEST — IP: %s | User-Agent: %s | Payload: %s',
            ip, user_agent,
            _mask_payload(dict(request.data.items())),
        )
        
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data.get('email')
        phone = serializer.validated_data.get('phone')
        purpose = serializer.validated_data.get('purpose')
        user_full_name = None
        
        # ── INSTRUMENTATION: Check rate limit ──
        recent_otps = OTP.objects.filter(
            email=email,
            purpose=purpose,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=1)
        )
        recent_count = recent_otps.count()
        logger.info('OTP RATE CHECK — Email: %s | Recent count: %d', email or '(phone)', recent_count)
        
        if recent_count >= 3:
            logger.warning('OTP RATE LIMIT EXCEEDED — Email: %s | IP: %s', email or phone, ip)
            return Response({
                'field': 'email',
                'message': 'Terlalu banyak permintaan OTP. Silakan coba lagi nanti.',
                'code': 'otp_rate_limited',
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # ── INSTRUMENTATION: Invalidate old OTPs (by email AND/OR phone) ──
        identifier_filter = Q()
        if email:
            identifier_filter |= Q(email=email)
        if phone:
            identifier_filter |= Q(phone=phone)
        invalidated = OTP.objects.filter(identifier_filter, purpose=purpose, is_valid=True).update(is_valid=False)
        _log_db_operation('otp_invalidate_old', {'email': email, 'phone': phone, 'purpose': purpose, 'count': invalidated})
        
        # ── INSTRUMENTATION: Create new OTP ──
        otp = OTP.objects.create(
            email=email,
            phone=phone,
            purpose=purpose,
            ip_address=ip,
            user_agent=user_agent,
        )
        _log_db_operation('otp_create', {'id': otp.id, 'email': email, 'phone': phone, 'purpose': purpose})

        response_data = {
            'message': 'Kode OTP telah dikirim.',
            'expires_in_minutes': settings.OTP_EXPIRE_MINUTES,
        }

        if email:
            user = User.objects.filter(email=email).first()
            user_full_name = user.full_name if user else None

            # Dispatch OTP delivery to Celery worker (non-blocking)
            channels = _dispatch_otp_async(
                email=email,
                phone=phone,
                otp_code=otp.otp_code,
                purpose=purpose,
                user_full_name=user_full_name,
            )
            if channels:
                response_data['otp_channels'] = channels
                if 'whatsapp' in channels:
                    response_data['message'] = 'Kode OTP telah dikirim via Email dan WhatsApp.'

        # Return OTP in debug mode
        if settings.DEBUG:
            response_data['otp_code'] = otp.otp_code

        # ── INSTRUMENTATION: Log response ──
        response_log = {
            'status': 'success',
            'user_email': email,
            'purpose': purpose,
            'channels': list(set(channels)) if email else [],
            'otp_id': otp.id,
        }
        if settings.DEBUG:
            response_log['otp_code'] = otp.otp_code
        logger.info('OTP REQUEST RESPONSE — HTTP 200 | Response: %s', response_log)

        return Response(response_data)


class OTPVerifyView(views.APIView):
    """Verify OTP code."""
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:200]
        
        # ── INSTRUMENTATION: Log incoming payload (masked) ──
        logger.info(
            'OTP VERIFY REQUEST — IP: %s | User-Agent: %s | Payload: %s',
            ip, user_agent,
            _mask_payload(dict(request.data.items())),
        )
        
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data.get('email')
        phone = serializer.validated_data.get('phone')
        otp_code = serializer.validated_data['otp_code']
        purpose = serializer.validated_data['purpose']
        
        # Step 1: Find candidate OTP record(s) by identifier + purpose (WITHOUT code comparison)
        # This allows us to track failed attempts even when the code is wrong.
        otp = None
        if email:
            otp = OTP.objects.filter(
                email=email, purpose=purpose, is_valid=True, is_used=False
            ).order_by('-created_at').first()
        if not otp and phone:
            otp = OTP.objects.filter(
                phone=phone, purpose=purpose, is_valid=True, is_used=False
            ).order_by('-created_at').first()
        
        if not otp:
            logger.warning(
                'OTP VERIFY FAILED — No OTP found | Email: %s | Phone: %s | Purpose: %s | IP: %s',
                email, phone, purpose, ip,
            )
            return _make_field_error('otp_code', 'Kode OTP tidak valid atau sudah digunakan.', 'otp_not_found')
        
        logger.info('OTP VERIFY FOUND — OTP ID: %d | Attempts: %d/%d | Expires: %s',
                     otp.id, otp.attempts, otp.max_attempts, otp.expires_at)
        
        if otp.is_expired():
            otp.is_valid = False
            otp.save()
            logger.warning('OTP VERIFY EXPIRED — OTP ID: %d | Email: %s', otp.id, email)
            return _make_field_error('otp_code', 'Kode OTP sudah kadaluwarsa. Silakan minta OTP baru.', 'otp_expired')
        
        if otp.is_locked():
            logger.warning('OTP VERIFY LOCKED — OTP ID: %d | Attempts: %d/%d | Email: %s',
                           otp.id, otp.attempts, otp.max_attempts, email)
            return Response({
                'field': 'otp_code',
                'message': 'Terlalu banyak percobaan. Silakan minta OTP baru.',
                'code': 'otp_locked',
                'needs_new_otp': True,
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Step 2: Verify the code against stored hash (with plaintext fallback)
        otp_code_hash = OTP.hash_otp(otp_code)
        is_code_valid = (otp.otp_code_hash == otp_code_hash) or (otp.otp_code == otp_code)
        
        if not is_code_valid:
            otp.increment_attempts()
            remaining = otp.max_attempts - otp.attempts
            logger.warning(
                'OTP VERIFY WRONG CODE — OTP ID: %d | Attempts: %d/%d | Remaining: %d | Email: %s',
                otp.id, otp.attempts, otp.max_attempts, max(remaining, 0), email,
            )
            return _make_field_error('otp_code', 'Kode OTP tidak valid.', 'otp_invalid')
        
        # Step 3: Code is correct — verify OTP
        otp.is_used = True
        otp.is_valid = False
        otp.verified_at = timezone.now()
        otp.save(update_fields=['is_used', 'is_valid', 'verified_at'])
        
        logger.info('OTP VERIFY SUCCESS — OTP ID: %d | Email: %s | Purpose: %s', otp.id, email, purpose)
        
        # Auto-activate account after OTP verification
        # Determine next step based on role and registration completeness
        next_step = None
        next_endpoint = None
        
        if purpose == 'registration' or purpose == 'email_change':
            # Find the user to check registration completeness
            user_obj = None
            if email:
                user_obj = User.objects.filter(email=email).first()
            elif phone:
                user_obj = User.objects.filter(phone=phone).first()
            
            if user_obj:
                # Detect path: if full_name is populated, this is the single-step
                # RegisterView path where the user is complete after OTP.
                # If full_name is empty, this is the multi-step service path
                # where complete_profile will be called next.
                if user_obj.full_name:
                    # Single-step registration (RegisterView) — user is complete
                    # Separate Buyer and Seller OTP workflows
                    if user_obj.role == 'seller':
                        # Seller workflow: auto-initialize Store profile, redirect to Seller Login
                        try:
                            from stores.models import Store
                            # Strip leading "Toko " if already present to avoid "Toko Toko ..."
                            raw_name = user_obj.full_name or user_obj.email.split('@')[0]
                            if raw_name.lower().startswith('toko '):
                                raw_name = raw_name[5:].strip()
                            store_name = f"Toko {raw_name}"
                            Store.objects.create(
                                user=user_obj,
                                store_name=store_name,
                                description=f"{store_name} — Mitra Warungio",
                                address=user_obj.address or '',
                                status='pending',
                            )
                            logger.info('Store auto-created for seller %s', user_obj.email)
                        except Exception as store_err:
                            logger.error('Failed to auto-create store for %s: %s', user_obj.email, store_err)
                        
                        update_fields = {
                            'is_verified': True,
                            'is_active': True,
                            'registration_step': 'complete',
                            'registration_completed_at': timezone.now(),
                        }
                        next_step = 'complete'
                        next_endpoint = '/auth/login-seller/'
                    else:
                        # Buyer workflow: mark complete, redirect to Buyer Login
                        update_fields = {
                            'is_verified': True,
                            'is_active': True,
                            'registration_step': 'complete',
                            'registration_completed_at': timezone.now(),
                        }
                        next_step = 'complete'
                        next_endpoint = '/auth/login/'
                    
                    User.objects.filter(id=user_obj.id).update(**update_fields)
                    _log_db_operation('user_activate', {'user_id': user_obj.id, 'role': user_obj.role})
                    
                    # Track registration completion event
                    try:
                        from .models import RegistrationEvent
                        RegistrationEvent.objects.create(
                            user=user_obj,
                            email=user_obj.email,
                            phone=str(user_obj.phone) if user_obj.phone else None,
                            event_type='otp_verified',
                            role=user_obj.role,
                            ip_address=getattr(otp, 'ip_address', None),
                            user_agent=getattr(otp, 'user_agent', None),
                        )
                    except Exception:
                        pass
                else:
                    # Multi-step registration — user still needs complete_profile
                    User.objects.filter(id=user_obj.id).update(
                        is_verified=True,
                        registration_step='otp',
                    )
                    _log_db_operation('user_step_advance', {'user_id': user_obj.id, 'step': 'otp'})
                    next_step = 'profile'
                    next_endpoint = '/api/auth/registration/complete-profile/'
        
        response_data = {
            'message': 'Verifikasi OTP berhasil.',
            'verified': True,
        }
        if next_step:
            response_data['next_step'] = next_step
        if next_endpoint:
            response_data['next_endpoint'] = next_endpoint
        
        # ── INSTRUMENTATION: Log response ──
        logger.info(
            'OTP VERIFY RESPONSE — HTTP 200 | Email: %s | Next: %s',
            email, next_step or '(none)',
        )
        
        return Response(response_data)


class ResendOTPView(views.APIView):
    """Resend OTP code with cooldown check."""
    permission_classes = (permissions.AllowAny,)
    throttle_scope = 'otp'

    def post(self, request):
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:200]
        
        # ── INSTRUMENTATION: Log incoming payload ──
        logger.info(
            'OTP RESEND REQUEST — IP: %s | User-Agent: %s | Payload: %s',
            ip, user_agent,
            _mask_payload(dict(request.data.items())),
        )
        
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data.get('email')
        phone = serializer.validated_data.get('phone')
        purpose = serializer.validated_data.get('purpose')
        
        # ── INSTRUMENTATION: Check cooldown (by email OR phone) ──
        identifier_filter = Q()
        if email:
            identifier_filter |= Q(email=email)
        if phone:
            identifier_filter |= Q(phone=phone)
        last_otp = OTP.objects.filter(identifier_filter, purpose=purpose).order_by('-created_at').first()
        
        if last_otp and not last_otp.can_resend():
            elapsed = (timezone.now() - last_otp.created_at).total_seconds()
            wait_seconds = max(0, int(settings.OTP_COOLDOWN_SECONDS - elapsed))
            logger.warning(
                'OTP RESEND COOLDOWN — Email: %s | Phone: %s | Wait: %ds | IP: %s',
                email, phone, wait_seconds, ip,
            )
            return Response({
                'field': 'email',
                'message': f'Silakan tunggu {wait_seconds} detik sebelum meminta ulang.',
                'code': 'otp_cooldown',
                'cooldown_seconds': wait_seconds,
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # ── INSTRUMENTATION: Invalidate old OTPs (by email AND/OR phone) ──
        identifier_filter = Q()
        if email:
            identifier_filter |= Q(email=email)
        if phone:
            identifier_filter |= Q(phone=phone)
        invalidated = OTP.objects.filter(identifier_filter, purpose=purpose, is_valid=True).update(is_valid=False)
        _log_db_operation('otp_invalidate_old', {'email': email, 'phone': phone, 'purpose': purpose, 'count': invalidated})

        # ── INSTRUMENTATION: Create new OTP ──
        otp = OTP.objects.create(
            email=email,
            phone=phone,
            purpose=purpose,
            ip_address=ip,
            user_agent=user_agent,
        )
        _log_db_operation('otp_create_resend', {'id': otp.id, 'email': email, 'phone': phone, 'purpose': purpose})

        response_data = {
            'message': 'Kode OTP telah dikirim ulang.',
            'expires_in_minutes': settings.OTP_EXPIRE_MINUTES,
        }

        if email:
            user = User.objects.filter(email=email).first()
            user_full_name = user.full_name if user else None

            # Dispatch OTP delivery to Celery worker (non-blocking)
            channels = _dispatch_otp_async(
                email=email,
                phone=phone,
                otp_code=otp.otp_code,
                purpose=purpose,
                user_full_name=user_full_name,
            )
            if channels:
                response_data['otp_channels'] = channels

        if settings.DEBUG:
            response_data['otp_code'] = otp.otp_code

        # ── INSTRUMENTATION: Log response ──
        logger.info(
            'OTP RESEND RESPONSE — HTTP 200 | Email: %s | Phone: %s | OTP ID: %d',
            email, phone, otp.id,
        )

        return Response(response_data)


class ForgotPasswordView(views.APIView):
    """Forgot password - send OTP."""
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:200]
        
        # ── INSTRUMENTATION: Log incoming payload ──
        logger.info(
            'FORGOT PASSWORD REQUEST — IP: %s | Payload: %s',
            ip, _mask_payload(dict(request.data.items())),
        )
        
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        # Cegah user enumeration: selalu return response yang sama
        # baik email terdaftar maupun tidak
        user_exists = User.objects.filter(email=email).exists()
        _log_db_operation('user_lookup', {'email': email, 'exists': user_exists})
        
        if user_exists:
            # Create reset OTP
            otp = OTP.objects.create(
                email=email,
                purpose='password_reset',
                ip_address=ip,
                user_agent=user_agent,
            )
            _log_db_operation('otp_create_reset', {'id': otp.id, 'email': email})

            # Dispatch OTP delivery to Celery worker (non-blocking)
            _dispatch_otp_async(
                email=email,
                phone=None,
                otp_code=otp.otp_code,
                purpose='password_reset',
                user_full_name=None,
            )

        response_data = {
            'message': 'Jika email terdaftar, kode reset password telah dikirim.',
        }

        if settings.DEBUG and user_exists:
            response_data['otp_code'] = otp.otp_code

        # ── INSTRUMENTATION: Log response (without leaking user_exists to prevent enumeration) ──
        logger.info(
            'FORGOT PASSWORD RESPONSE — HTTP 200 | Email: %s | otp_id: %s',
            email, otp.id if user_exists else 'N/A',
        )

        return Response(response_data)


class ResetPasswordView(views.APIView):
    """Reset password with OTP verification."""
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:200]
        
        # ── INSTRUMENTATION: Log incoming payload ──
        logger.info(
            'RESET PASSWORD REQUEST — IP: %s | Payload: %s',
            ip, _mask_payload(dict(request.data.items())),
        )
        
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        otp_code = serializer.validated_data['otp_code']
        new_password = serializer.validated_data['new_password']
        
        # Verify OTP — use hash comparison with plaintext fallback
        otp_code_hash = OTP.hash_otp(otp_code)
        otp = OTP.objects.filter(
            email=email,
            purpose='password_reset',
            is_valid=True,
            is_used=False,
        ).filter(
            Q(otp_code_hash=otp_code_hash) | Q(otp_code=otp_code)
        ).first()
        
        if not otp:
            logger.warning('RESET PASSWORD FAILED — No OTP found | Email: %s', email)
            return _make_field_error('otp_code', 'Kode OTP tidak valid atau sudah digunakan.', 'otp_not_found')
        
        if otp.is_expired():
            otp.is_valid = False
            otp.save()
            logger.warning('RESET PASSWORD EXPIRED — OTP ID: %d | Email: %s', otp.id, email)
            return _make_field_error('otp_code', 'Kode OTP sudah kadaluwarsa. Silakan minta ulang.', 'otp_expired')
        
        # Update password
        user = User.objects.filter(email=email).first()
        if not user:
            logger.error('RESET PASSWORD USER NOT FOUND — Email: %s but OTP existed', email)
            return Response({
                'field': 'email',
                'message': 'Pengguna tidak ditemukan.',
                'code': 'user_not_found',
            }, status=status.HTTP_404_NOT_FOUND)
        
        user.set_password(new_password)
        user.save(update_fields=['password'])
        _log_db_operation('user_password_reset', {'user_id': user.id})
        
        otp.is_used = True
        otp.is_valid = False
        otp.verified_at = timezone.now()
        otp.save(update_fields=['is_used', 'is_valid', 'verified_at'])
        
        # ── INSTRUMENTATION: Log success ──
        logger.info('RESET PASSWORD SUCCESS — Email: %s | OTP ID: %d', email, otp.id)
        
        return Response({
            'message': 'Password berhasil direset. Silakan login dengan password baru.'
        })


class CheckAuthView(views.APIView):
    """Check if user is authenticated and return their info.
    
    If the user is not verified (OTP), returns needs_verification flag
    so the frontend can redirect to the OTP verification page.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        user = request.user
        response_data = {
            'authenticated': True,
            'user': UserSerializer(user).data,
        }
        
        if not user.is_verified:
            response_data['needs_verification'] = True
            response_data['email'] = user.email
        
        return Response(response_data)


class TokenRefreshView(views.APIView):
    """Refresh JWT access token."""
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({
                'error': 'Refresh token diperlukan.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            refresh = RefreshToken(refresh_token)
            access = str(refresh.access_token)
            return Response({'access': access})
        except Exception:
            return Response({
                'error': 'Refresh token tidak valid.'
            }, status=status.HTTP_401_UNAUTHORIZED)


class RootView(views.APIView):
    """Root view — always renders the public Landing Page.
    
    The Landing Page is the main public entry point and is accessible to everyone,
    including authenticated users. No automatic redirects are performed here.
    Authenticated users who want their dashboard navigate there explicitly.
    
    Unverified users (missing OTP) also see the Landing Page — OTP reminders
    are handled via banners or the login flow, not forced redirects.
    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        from django.shortcuts import render
        return render(request, 'landing/index.html')
