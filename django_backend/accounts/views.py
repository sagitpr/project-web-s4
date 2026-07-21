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

from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, OTP, LoginAttempt
from .services.whatsapp_service import _whatsapp_configured

# Celery task imports — wrapped so registration doesn't fail if Celery/Redis is down
try:
    from .tasks import send_otp_task, send_whatsapp_only_otp_task
except ImportError:
    send_otp_task = None
    send_whatsapp_only_otp_task = None
    logger.warning('Celery tasks unavailable — OTP will skip async delivery')

from drf_spectacular.utils import extend_schema

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

    if send_otp_task is None:
        logger.warning('OTP delivery skipped — Celery tasks not available (import failed at module load)')
        return []

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
    authentication_classes = ()  # No auth required — prevents JWTAuthentication from rejecting stale tokens
    serializer_class = RegisterSerializer
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:200]
        
        # ── Guard: verbose request payload logging only in DEBUG mode ──
        # In production (DEBUG=False), we skip _mask_payload to avoid CPU overhead
        # of stringifying the entire request body on every registration.
        if settings.DEBUG:
            logger.info(
                'REGISTER REQUEST — IP: %s | User-Agent: %s | Complete payload: %s',
                ip,
                user_agent,
                _mask_payload(dict(request.data.items())),
            )
        
        if not serializer.is_valid():
            error_detail = dict(serializer.errors)
            
            logger.warning(
                'REGISTER VALIDATION FAILED — IP: %s | Errors: %s',
                ip,
                error_detail,
            )
            
            # Log every single field error with received value (production-safe)
            if logger.isEnabledFor(logging.WARNING):
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
        
        if settings.DEBUG:
            response_log = {
                'status': 'success',
                'user_id': user.id,
                'email': user.email,
                'role': user.role,
                'otp_channels': list(set(channels)),
                'otp_code': otp.otp_code,
            }
            logger.info('REGISTER RESPONSE — HTTP 201 | Response: %s', response_log)

        return Response(response_data, status=status.HTTP_201_CREATED)


@extend_schema(exclude=True)
class LoginView(views.APIView):
    """User login with JWT token response."""
    permission_classes = (permissions.AllowAny,)
    throttle_classes = [throttling.AnonRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:200]
        login_entry = request.data.get('login_entry')
        
        serializer = LoginSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            error_detail = dict(serializer.errors)
            
            logger.warning(
                'LOGIN VALIDATION FAILED — IP: %s | Errors: %s',
                ip, error_detail,
            )
            
            # Log every single field error with received value (production-safe)
            if logger.isEnabledFor(logging.WARNING):
                for field, field_errors in serializer.errors.items():
                    for err in field_errors:
                        raw_val = request.data.get(field, 'MISSING')
                        val_preview = '***MASKED***' if field in LOGIN_SENSITIVE_FIELDS else str(raw_val)[:200]
                        logger.warning(
                            '  LOGIN FIELD ERROR — Field: "%s" | Error: %s | Received: %s',
                            field, str(err), val_preview,
                        )
            
            logger.warning(
                'LOGIN ERROR RESPONSE — HTTP 400 | Response: {\"success\": false, \"errors\": %s}',
                error_detail,
            )
            
            raise drf_serializers.ValidationError(serializer.errors)
        
        user = serializer.validated_data['user']
        
        # ── Auto-OTP Flow for unverified accounts ──
        if not user.is_verified:
            logger.warning(
                'LOGIN BLOCKED — Unverified user | Email: %s | IP: %s — Auto-generating OTP',
                user.email, ip,
            )

            email = user.email
            phone = str(user.phone) if user.phone else None
            user_full_name = user.full_name or None

            # 1. Invalidate any previous unused OTPs for this email (purpose='registration')
            stale_count = OTP.objects.filter(
                email=email, purpose='registration', is_valid=True, is_used=False
            ).update(is_valid=False)
            if stale_count:
                _log_db_operation('login_otp_invalidate_old', {
                    'email': email, 'purpose': 'registration', 'count': stale_count
                })

            # 2. Create a fresh OTP with a new expiration time
            otp = OTP.objects.create(
                user=user,
                email=email,
                phone=phone,
                purpose='registration',
                ip_address=ip,
                user_agent=user_agent,
            )
            _log_db_operation('login_otp_create', {
                'id': otp.id, 'email': email, 'purpose': 'registration'
            })

            # 3. Dispatch OTP delivery asynchronously via configured providers
            channels = _dispatch_otp_async(
                email=email,
                phone=phone,
                otp_code=otp.otp_code,
                purpose='registration',
                user_full_name=user_full_name,
            )

            # 4. Return enhanced response with redirect information
            response_data = {
                'needs_verification': True,
                'email': email,
                'message': 'Akun belum diverifikasi. Kode OTP baru telah dikirim ke email Anda.',
                'otp_channels': list(set(channels)),
                'expires_in_minutes': settings.OTP_EXPIRE_MINUTES,
            }

            if settings.DEBUG:
                response_data['otp_code'] = otp.otp_code

            logger.info(
                'LOGIN AUTO-OTP — Email: %s | OTP ID: %d | Channels: %s | IP: %s',
                email, otp.id, channels or '(none)', ip,
            )

            return Response(response_data, status=status.HTTP_403_FORBIDDEN)
        
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
        
        if settings.DEBUG:
            logger.info(
                'LOGIN SUCCESS — Email: %s | Role: %s | IP: %s',
                user.email, user.role, ip,
            )
        
        return Response(response_data)


@extend_schema(exclude=True)
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
        # Use select_related to avoid N+1 wallet query in UserSerializer.get_wallet_balance
        return User.objects.select_related('wallet').get(pk=self.request.user.pk)

    def patch(self, request, *args, **kwargs):
        serializer = UserUpdateSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


@extend_schema(exclude=True)
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


@extend_schema(exclude=True)
class OTPRequestView(views.APIView):
    """Request OTP code for verification."""
    permission_classes = (permissions.AllowAny,)
    throttle_scope = 'otp'

    def post(self, request):
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:200]
        
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data.get('email')
        phone = serializer.validated_data.get('phone')
        purpose = serializer.validated_data.get('purpose')
        user_full_name = None
        
        # Check rate limit — track count without full payload log in production
        recent_otps = OTP.objects.filter(
            email=email,
            purpose=purpose,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=1)
        )
        recent_count = recent_otps.count()
        
        if recent_count >= 3:
            logger.warning('OTP RATE LIMIT EXCEEDED — Email: %s | IP: %s', email or phone, ip)
            return Response({
                'detail': 'Terlalu banyak permintaan OTP. Silakan coba lagi nanti.',
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

        if settings.DEBUG:
            response_log = {
                'status': 'success',
                'user_email': email,
                'purpose': purpose,
                'channels': list(set(channels)) if email else [],
                'otp_id': otp.id,
                'otp_code': otp.otp_code,
            }
            logger.info('OTP REQUEST RESPONSE — HTTP 200 | Response: %s', response_log)

        return Response(response_data)


@extend_schema(exclude=True)
class OTPVerifyView(views.APIView):
    """Verify OTP code."""
    permission_classes = (permissions.AllowAny,)
    throttle_scope = 'otp'

    def post(self, request):
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:200]
        
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
            # Return a top-level 'detail' key so the frontend's auth.js api()
            # can parse it via data.detail || data.message || data.error
            return Response({
                'detail': 'Kode OTP tidak valid atau sudah digunakan.',
                'field': 'otp_code',
                'code': 'otp_not_found',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info('OTP VERIFY FOUND — OTP ID: %d | Attempts: %d/%d | Expires: %s',
                     otp.id, otp.attempts, otp.max_attempts, otp.expires_at)
        
        if otp.is_expired():
            otp.is_valid = False
            otp.save()
            logger.warning('OTP VERIFY EXPIRED — OTP ID: %d | Email: %s', otp.id, email)
            return Response({
                'detail': 'Kode OTP sudah kadaluwarsa. Silakan minta OTP baru.',
                'field': 'otp_code',
                'code': 'otp_expired',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if otp.is_locked():
            logger.warning('OTP VERIFY LOCKED — OTP ID: %d | Attempts: %d/%d | Email: %s',
                           otp.id, otp.attempts, otp.max_attempts, email)
            return Response({
                'detail': 'Terlalu banyak percobaan. Silakan minta OTP baru.',
                'field': 'otp_code',
                'message': 'Terlalu banyak percobaan. Silakan minta OTP baru.',
                'code': 'otp_locked',
                'needs_new_otp': True,
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Step 2: Verify the code against stored hash (with plaintext fallback)
        # Security note: The plaintext fallback (otp.otp_code == otp_code) exists for
        # legacy OTP records created before the hash migration. New OTP records always
        # store the SHA256 hash via the model's save() method. This dual comparison
        # ensures backward compatibility without breaking existing user flows.
        # Once all old OTP records have expired (max 15 min lifetime), this fallback
        # will naturally become unreachable and can be removed in a future cleanup.
        otp_code_hash = OTP.hash_otp(otp_code)
        is_code_valid = (otp.otp_code_hash == otp_code_hash) or (otp.otp_code == otp_code)
        
        if not is_code_valid:
            otp.increment_attempts()
            remaining = otp.max_attempts - otp.attempts
            logger.warning(
                'OTP VERIFY WRONG CODE — OTP ID: %d | Attempts: %d/%d | Remaining: %d | Email: %s',
                otp.id, otp.attempts, otp.max_attempts, max(remaining, 0), email,
            )
            return Response({
                'detail': 'Kode OTP tidak valid.',
                'field': 'otp_code',
                'code': 'otp_invalid',
            }, status=status.HTTP_400_BAD_REQUEST)
        
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
                        next_endpoint = '/seller/dashboard/'
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
                    
                    # ── Auto-create Wallet (via service for legacy balance migration) ──
                    try:
                        from payments.services.wallet import get_wallet
                        get_wallet(user_obj, lock=False)
                    except Exception:
                        pass
                    # ── Auto-create NotificationPreference ──
                    try:
                        from notifications.models import NotificationPreference
                        NotificationPreference.objects.get_or_create(user=user_obj)
                    except Exception:
                        pass
                    
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
        
        # ── Generate JWT tokens for auto-login ──
        # After successful OTP verification, return tokens so the frontend
        # can stay authenticated without requiring the user to log in again.
        # This is critical for the Seller registration wizard flow where the
        # user must remain authenticated after OTP verification.
        # Reuse user_obj from the lookup above if available, otherwise look up again.
        user_for_token = user_obj if purpose in ('registration', 'email_change') and user_obj else None
        if not user_for_token:
            if email:
                user_for_token = User.objects.filter(email=email).first()
            elif phone:
                user_for_token = User.objects.filter(phone=phone).first()

        if user_for_token and user_for_token.is_active:
            try:
                refresh_token = RefreshToken.for_user(user_for_token)
                access_token = str(refresh_token.access_token)
                response_data['access'] = access_token
                response_data['refresh'] = str(refresh_token)
                response_data['user'] = UserSerializer(user_for_token).data

                # Set Django session cookie so session-based auth also works
                # login() is already imported at the top of this module
                # Must specify backend because multiple auth backends are configured
                login(request, user_for_token, backend='django.contrib.auth.backends.ModelBackend')
            except Exception as token_err:
                logger.error('Failed to generate JWT after OTP verify: %s', token_err)

        # ── Cleanup: Delete expired OTPs for this user after successful verification ──
        try:
            deleted_count = OTP.objects.filter(
                Q(email=email) | (Q(phone=phone) if phone else Q()),
                expires_at__lt=timezone.now()
            ).delete()[0]
            if deleted_count:
                _log_db_operation('otp_cleanup_expired', {
                    'email': email, 'phone': phone or '(none)', 'deleted': deleted_count
                })
        except Exception as cleanup_err:
            logger.warning('OTP cleanup error (non-blocking): %s', cleanup_err)

        if settings.DEBUG:
            logger.info(
                'OTP VERIFY RESPONSE — HTTP 200 | Email: %s | Next: %s',
                email, next_step or '(none)',
            )
        
        return Response(response_data)


@extend_schema(exclude=True)
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
        # Reuse the same identifier_filter from the cooldown check above
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


@extend_schema(exclude=True)
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


@extend_schema(exclude=True)
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
            return Response({
                'detail': 'Kode OTP tidak valid atau sudah digunakan.',
                'field': 'otp_code',
                'code': 'otp_not_found',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if otp.is_expired():
            otp.is_valid = False
            otp.save()
            logger.warning('RESET PASSWORD EXPIRED — OTP ID: %d | Email: %s', otp.id, email)
            return Response({
                'detail': 'Kode OTP sudah kadaluwarsa. Silakan minta ulang.',
                'field': 'otp_code',
                'code': 'otp_expired',
            }, status=status.HTTP_400_BAD_REQUEST)
        
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


@extend_schema(exclude=True)
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


@extend_schema(exclude=True)
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


@extend_schema(exclude=True)
class CheckAvailabilityView(views.APIView):
    """Check if email or phone is already registered (no side effects, no record creation)."""
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()  # No auth required — anyone can check availability before registering

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        phone = request.data.get('phone', '').strip()

        response = {'available': True}

        if email:
            exists = User.objects.filter(email=email).exists()
            if exists:
                response = {
                    'available': False,
                    'field': 'email',
                    'message': 'Email ini sudah terdaftar. Gunakan email lain atau masuk.',
                    'code': 'email_taken',
                }
                return Response(response, status=status.HTTP_409_CONFLICT)

        if phone and response.get('available', True):
            exists = User.objects.filter(phone=phone).exists()
            if exists:
                response = {
                    'available': False,
                    'field': 'phone',
                    'message': 'Nomor HP ini sudah terdaftar. Gunakan nomor lain atau masuk.',
                    'code': 'phone_taken',
                }
                return Response(response, status=status.HTTP_409_CONFLICT)

        return Response(response)


@extend_schema(exclude=True)
class RootView(views.APIView):
    """Root view — multi-tenant entry point.
    
    Separates the Public Application from the Administration Application:
    - Unauthenticated users → Public Landing Page
    - Authenticated buyers → Redirect to /buyer/home/
    - Authenticated sellers → Redirect to /seller/dashboard/
    - Authenticated admins → Redirect to /admin-panel/
    - Register Mitra users (unverified) → Continue public flow
    
    Admins who access the root are redirected to the admin panel immediately,
    bypassing the landing page entirely.
    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        from django.shortcuts import render, redirect

        user = request.user

        # If authenticated, redirect to role-appropriate dashboard
        if user.is_authenticated:
            role = getattr(user, 'role', None)
            is_staff = user.is_staff or user.is_superuser

            if is_staff or role == 'admin':
                # Admin users bypass landing page entirely
                return redirect('/admin-panel/')

            if role == 'seller' and user.is_verified:
                # Verified sellers go to their dashboard
                return redirect('/seller/dashboard/')

            if role == 'buyer' and user.is_verified:
                # Verified buyers go to their home
                return redirect('/buyer/home/')

            # Unverified users (including Register Mitra) continue public flow
            return render(request, 'landing/index.html')

        # Unauthenticated: always show landing page
        return render(request, 'landing/index.html')


@extend_schema(exclude=True)
class AdminLoginView(views.APIView):
    """
    Dedicated admin login view.
    
    Only staff users (is_staff=True or role='admin') may log in here.
    Uses AdminLoginSerializer which checks admin status BEFORE authenticating
    to prevent leaking authentication success to non-admin users.
    
    Admin login has a tighter rate limit (5/minute) than public login (10/minute)
    to prevent brute force attacks on admin accounts.
    
    Returns JWT tokens AND sets Django session for template-based navigation.
    """
    permission_classes = (permissions.AllowAny,)
    throttle_classes = [throttling.ScopedRateThrottle]
    throttle_scope = 'admin_login'

    def post(self, request):
        from .serializers_admin import AdminLoginSerializer

        serializer = AdminLoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Set Django session cookie for template-based admin navigation
        from django.contrib.auth import login
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        # Extract ?next= parameter for post-login redirect
        next_url = request.GET.get('next', '/admin-panel/')

        return Response({
            'message': 'Login admin berhasil.',
            'access': access_token,
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
            'redirect': next_url,
        })
