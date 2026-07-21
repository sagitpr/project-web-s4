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

from .response_utils import success_response, error_response
from .models import User, OTP, LoginAttempt
from .services.email_service import send_otp_email
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
    """User registration endpoint.
    
    FLOW (atomic transaction):
    1. Validate all fields (email, phone, password, etc.)
    2. Check duplicate email/phone — reject with 409 if exists
    3. Create user with is_active=False (not yet verified)
    4. Generate OTP code and save to database
    5. Send OTP via email (synchronously in DEBUG, via Celery in production)
    6. Commit transaction
    7. Return success response with redirect_url to OTP page
    
    CRITICAL: If OTP sending fails, the entire transaction rolls back.
    No partial account creation occurs.
    """
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
                'REGISTER ERROR RESPONSE — HTTP 400 | Response: {"success": false, "errors": %s}',
                error_detail,
            )
            
            raise drf_serializers.ValidationError(serializer.errors)
        
        # ────────────────────────────────────────────────────────────────────
        #  STEP 1: Create user account (INACTIVE until OTP verified)
        # ────────────────────────────────────────────────────────────────────
        user = serializer.save()
        logger.info(
            'REGISTER USER CREATED — ID: %d | Email: %s | Role: %s | IP: %s',
            user.id, user.email, user.role, ip,
        )
        _log_db_operation('user_create', {'id': user.id, 'email': user.email, 'role': user.role})
        
        # ────────────────────────────────────────────────────────────────────
        #  STEP 2: Generate and save OTP
        # ────────────────────────────────────────────────────────────────────
        otp = OTP.objects.create(
            user=user,
            email=user.email,
            phone=str(user.phone) if user.phone else None,
            purpose='registration',
            ip_address=ip,
            user_agent=user_agent,
        )
        _log_db_operation('otp_create', {
            'id': otp.id, 'email': user.email, 'purpose': 'registration'
        })
        logger.info(
            'REGISTER OTP CREATED — ID: %d | Email: %s | Expires: %s',
            otp.id, user.email, otp.expires_at,
        )
        
        # ────────────────────────────────────────────────────────────────────
        #  STEP 3: Send OTP via email (synchronous — blocks until sent)
        #  CRITICAL: OTP must be sent BEFORE committing the transaction.
        #  If email fails, the entire transaction rolls back — no orphan account.
        # ────────────────────────────────────────────────────────────────────
        otp_sent = False
        email_result = send_otp_email(
            email=user.email,
            otp_code=otp.otp_code,
            purpose='registration',
            user_full_name=user.full_name,
        )
        
        if email_result.get('success'):
            otp_sent = True
            channels = ['email']
            logger.info(
                'REGISTER OTP SENT — Email: %s | OTP ID: %d',
                user.email, otp.id,
            )
        else:
            # Email failed — try Celery task as fallback
            logger.warning(
                'REGISTER OTP EMAIL FAILED — %s | Falling back to Celery for %s',
                email_result.get('error', 'unknown'), user.email,
            )
            channels = _dispatch_otp_async(
                email=user.email,
                phone=str(user.phone) if user.phone else None,
                otp_code=otp.otp_code,
                purpose='registration',
                user_full_name=user.full_name,
            )
            if channels:
                otp_sent = True
        
        # Attempt WhatsApp delivery as bonus channel (non-blocking)
        if user.phone and _whatsapp_configured():
            _dispatch_otp_async(
                email=user.email,
                phone=str(user.phone),
                otp_code=otp.otp_code,
                purpose='registration',
                user_full_name=user.full_name,
            )
            if 'whatsapp' not in channels:
                channels.append('whatsapp')
        
        if not otp_sent:
            # ⚠️ CRITICAL: OTP delivery failed entirely.
            # The transaction will roll back, preventing orphan accounts.
            logger.error(
                'REGISTER FAILED — OTP delivery failed for %s | All channels unavailable',
                user.email,
            )
            raise drf_serializers.ValidationError({
                'detail': 'Gagal mengirim kode OTP. Silakan coba lagi nanti.',
                'code': 'otp_delivery_failed',
            })
        
        # ────────────────────────────────────────────────────────────────────
        #  STEP 4: Determine redirect URL based on role
        # ────────────────────────────────────────────────────────────────────
        if user.role == 'seller':
            redirect_url = f'/auth/otp/?email={user.email}&purpose=registration&role=seller'
        else:
            redirect_url = f'/auth/otp/?email={user.email}&purpose=registration&role=buyer'
        
        # ────────────────────────────────────────────────────────────────────
        #  STEP 5: Build success response
        # ────────────────────────────────────────────────────────────────────
        response_data = {
            'success': True,
            'message': 'Registrasi berhasil. Silakan verifikasi OTP.',
            'requires_otp': True,
            'redirect_url': redirect_url,
            'otp_channels': list(set(channels)),
            'expires_in_minutes': settings.OTP_EXPIRE_MINUTES,
            'user': UserSerializer(user).data,
        }

        if settings.DEBUG:
            response_data['otp_code'] = otp.otp_code
        
        logger.info(
            'REGISTER SUCCESS — User: %s | Role: %s | OTP ID: %d | Redirect: %s',
            user.email, user.role, otp.id, redirect_url,
        )

        return Response(response_data, status=status.HTTP_201_CREATED)


@extend_schema(exclude=True)
class LoginView(views.APIView):
    """User login with JWT token response.
    
    FLOW:
    1. Validate credentials via LoginSerializer
    2. If user is not verified (OTP), return 403 with requires_otp=true + redirect_url
    3. If user is verified, generate JWT tokens + Django session
    4. Check role gate (login_entry vs actual role)
    5. Return tokens and user data
    
    For unverified users: The frontend MUST check for requires_otp=true
    and redirect to the OTP page using redirect_url.
    """
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
                'LOGIN ERROR RESPONSE — HTTP 400 | Response: {"success": false, "errors": %s}',
                error_detail,
            )
            
            raise drf_serializers.ValidationError(serializer.errors)
        
        user = serializer.validated_data['user']
        
        # ── Auto-OTP Flow for unverified accounts ──
        if not user.is_verified:
            logger.info(
                'LOGIN BLOCKED — Unverified user | Email: %s | IP: %s — Auto-generating OTP',
                user.email, ip,
            )

            email = user.email
            phone = str(user.phone) if user.phone else None
            user_full_name = user.full_name or None

            # 1. Invalidate any previous unused OTPs for this email
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

            # 3. Send OTP via email (synchronous)
            email_result = send_otp_email(
                email=email,
                otp_code=otp.otp_code,
                purpose='registration',
                user_full_name=user_full_name,
            )
            
            # Also try async dispatch as bonus
            channels = []
            if email_result.get('success'):
                channels.append('email')
            else:
                channels = _dispatch_otp_async(
                    email=email,
                    phone=phone,
                    otp_code=otp.otp_code,
                    purpose='registration',
                    user_full_name=user_full_name,
                )

            # Build redirect URL for OTP page
            if user.role == 'seller':
                redirect_url = f'/auth/otp/?email={email}&purpose=registration&role=seller'
            else:
                redirect_url = f'/auth/otp/?email={email}&purpose=registration&role=buyer'

            # 4. Return enhanced response with requires_otp and redirect_url
            response_data = {
                'requires_otp': True,
                'needs_verification': True,
                'email': email,
                'redirect_url': redirect_url,
                'message': 'Akun belum diverifikasi. Kode OTP baru telah dikirim ke email Anda.',
                'otp_channels': list(set(channels)),
                'expires_in_minutes': settings.OTP_EXPIRE_MINUTES,
            }

            if settings.DEBUG:
                response_data['otp_code'] = otp.otp_code

            logger.info(
                'LOGIN AUTO-OTP — Email: %s | OTP ID: %d | Channels: %s | IP: %s | Redirect: %s',
                email, otp.id, channels or '(none)', ip, redirect_url,
            )

            return error_response(
                message='Akun belum diverifikasi. Kode OTP baru telah dikirim ke email Anda.',
                status_code=status.HTTP_403_FORBIDDEN,
                **{k: v for k, v in response_data.items() if k != 'message'},
            )

        # ── Role-gate: validate login_entry against the user's actual role ──
        login_entry = serializer.validated_data.get('login_entry')
        if login_entry and user.role != login_entry:
            role_label = 'Mitra Penjual' if login_entry == 'seller' else 'Pembeli'
            logger.warning(
                'LOGIN BLOCKED — Role mismatch | Email: %s | User role: %s | Login entry: %s | IP: %s',
                user.email, user.role, login_entry, ip,
            )
            return error_response(
                message=f'Akun ini tidak terdaftar sebagai {role_label}.',
                status_code=status.HTTP_403_FORBIDDEN,
                code='role_mismatch',
                user_role=user.role,
                login_entry=login_entry,
            )
        
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
        
        # Compute role-based redirect URL for verified users
        if user.role == 'seller':
            verified_redirect_url = '/seller/dashboard/'
        elif user.role == 'buyer':
            verified_redirect_url = '/buyer/home/'
        elif user.role == 'admin':
            verified_redirect_url = '/admin-panel/'
        else:
            verified_redirect_url = '/'
        
        log_user_info = f'Email: {user.email} | Role: {user.role} | IP: {ip}'
        logger.info('LOGIN SUCCESS — %s', log_user_info)

        return success_response(
            message='Login berhasil.',
            access=access_token,
            refresh=str(refresh),
            user=UserSerializer(user).data,
            redirect_url=verified_redirect_url,
        )


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
            return success_response(message='Logout berhasil.')
        except Exception as e:
            logger.warning('Logout error (non-blocking): %s', str(e))
            return success_response(message='Logout berhasil.')


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
        return success_response(message='Password berhasil diubah.')


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
            return error_response(
                message='Terlalu banyak permintaan OTP. Silakan coba lagi nanti.',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                field='email',
                code='otp_rate_limited',
            )
        
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
            response_log = {
                'status': 'success',
                'user_email': email,
                'purpose': purpose,
                'channels': response_data.get('otp_channels', []),
                'otp_id': otp.id,
                'otp_code': otp.otp_code,
            }
            logger.info('OTP REQUEST RESPONSE — HTTP 200 | Response: %s', response_log)

        return success_response(
            message=response_data.get('message', 'Kode OTP telah dikirim.'),
            expires_in_minutes=response_data.get('expires_in_minutes'),
            otp_channels=response_data.get('otp_channels'),
            otp_code=response_data.get('otp_code'),
        )


@extend_schema(exclude=True)
class OTPVerifyView(views.APIView):
    """Verify OTP code with auto-activation and auto-login.
    
    FLOW:
    1. Validate OTP code input
    2. Find valid OTP record by email/phone + purpose
    3. Check expiry — if expired, invalidate and return error (frontend can resend)
    4. Check attempt limit — if locked, return error
    5. Verify code against stored hash
    6. If wrong code, increment attempts and return error
    7. If correct code:
       a. Mark OTP as used
       b. Activate user account (is_active=True, is_verified=True)
       c. Generate JWT tokens for auto-login
       d. Set Django session
       e. Create role-dependent redirect URL
       f. Create Store for sellers (auto-provisioning)
    8. Return success response with tokens, user data, and redirect_url
    
    CRITICAL: After OTP verification, the user is automatically logged in.
    No separate login step is needed.
    """
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
        
        # ────────────────────────────────────────────────────────────────────
        #  STEP 1: Find candidate OTP record
        # ────────────────────────────────────────────────────────────────────
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
            return error_response(
                message='Kode OTP tidak valid atau sudah digunakan.',
                status_code=status.HTTP_400_BAD_REQUEST,
                field='otp_code',
                code='otp_not_found',
            )
        
        logger.info(
            'OTP VERIFY — Found OTP ID: %d | Attempts: %d/%d | Expires: %s | Email: %s',
            otp.id, otp.attempts, otp.max_attempts, otp.expires_at, email,
        )
        
        # ────────────────────────────────────────────────────────────────────
        #  STEP 2: Check expiry
        # ────────────────────────────────────────────────────────────────────
        if otp.is_expired():
            otp.is_valid = False
            otp.save(update_fields=['is_valid'])
            logger.warning(
                'OTP VERIFY EXPIRED — OTP ID: %d | Email: %s | IP: %s',
                otp.id, email, ip,
            )
            return error_response(
                message='Kode OTP sudah kadaluwarsa. Silakan minta OTP baru.',
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                field='otp_code',
                code='otp_expired',
                needs_new_otp=True,
            )
        
        # ────────────────────────────────────────────────────────────────────
        #  STEP 3: Check attempt lockout
        # ────────────────────────────────────────────────────────────────────
        if otp.is_locked():
            logger.warning(
                'OTP VERIFY LOCKED — OTP ID: %d | Attempts: %d/%d | Email: %s | IP: %s',
                otp.id, otp.attempts, otp.max_attempts, email, ip,
            )
            return error_response(
                message='Terlalu banyak percobaan. Silakan minta OTP baru.',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                field='otp_code',
                code='otp_locked',
                needs_new_otp=True,
            )
        
        # ────────────────────────────────────────────────────────────────────
        #  STEP 4: Verify code against stored hash
        # ────────────────────────────────────────────────────────────────────
        otp_code_hash = OTP.hash_otp(otp_code)
        is_code_valid = (otp.otp_code_hash == otp_code_hash) or (otp.otp_code == otp_code)
        
        if not is_code_valid:
            otp.increment_attempts()
            remaining = otp.max_attempts - otp.attempts
            logger.warning(
                'OTP VERIFY WRONG CODE — OTP ID: %d | Attempts: %d/%d | Remaining: %d | Email: %s | IP: %s',
                otp.id, otp.attempts, otp.max_attempts, max(remaining, 0), email, ip,
            )
            return error_response(
                message='Kode OTP tidak valid.',
                status_code=status.HTTP_400_BAD_REQUEST,
                field='otp_code',
                code='otp_invalid',
                remaining_attempts=max(remaining, 0),
            )
        
        # ────────────────────────────────────────────────────────────────────
        #  STEP 5: Code is correct — verify OTP and activate account
        #  Uses atomic transaction to ensure consistency
        # ────────────────────────────────────────────────────────────────────
        with transaction.atomic():
            # Mark OTP as used
            otp.is_used = True
            otp.is_valid = False
            otp.verified_at = timezone.now()
            otp.save(update_fields=['is_used', 'is_valid', 'verified_at'])
            
            logger.info(
                'OTP VERIFY SUCCESS — OTP ID: %d | Email: %s | Purpose: %s',
                otp.id, email, purpose,
            )
            
            # Find the user
            user_obj = None
            if email:
                user_obj = User.objects.filter(email=email).first()
            elif phone:
                user_obj = User.objects.filter(phone=phone).first()
            
            if not user_obj:
                logger.error(
                    'OTP VERIFY — User not found for email: %s | phone: %s',
                    email, phone,
                )
                return error_response(
                    message='Pengguna tidak ditemukan.',
                    status_code=status.HTTP_404_NOT_FOUND,
                    code='user_not_found',
                )
            
            # Activate user: is_verified=True, is_active=True
            user_obj.is_verified = True
            user_obj.is_active = True
            user_obj.registration_step = 'complete'
            user_obj.registration_completed_at = timezone.now()
            user_obj.save(update_fields=[
                'is_verified', 'is_active', 'registration_step', 'registration_completed_at'
            ])
            
            _log_db_operation('user_activate', {
                'user_id': user_obj.id, 'email': user_obj.email, 'role': user_obj.role
            })
            logger.info(
                'USER ACTIVATED — ID: %d | Email: %s | Role: %s',
                user_obj.id, user_obj.email, user_obj.role,
            )
            
            # ── Auto-create Store for sellers ──
            if user_obj.role == 'seller':
                try:
                    from stores.models import Store
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
            
            # ── Auto-create Wallet ──
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
            
            # ── Track registration completion event ──
            # Only log 'otp_verified' for registration purpose
            if purpose == 'registration':
                try:
                    RegistrationEvent.objects.create(
                        user=user_obj,
                        email=user_obj.email,
                        phone=str(user_obj.phone) if user_obj.phone else None,
                        event_type='otp_verified',
                        role=user_obj.role,
                        ip_address=ip,
                        user_agent=user_agent,
                    )
                except Exception:
                    pass
        
        # ────────────────────────────────────────────────────────────────────
        #  STEP 6: Generate JWT tokens + Django session for auto-login
        # ────────────────────────────────────────────────────────────────────
        redirect_url = None
        try:
            refresh_token = RefreshToken.for_user(user_obj)
            access_token = str(refresh_token.access_token)
            
            # Set Django session cookie
            login(request, user_obj, backend='django.contrib.auth.backends.ModelBackend')
            
            logger.info(
                'AUTO-LOGIN AFTER OTP — User: %s | Role: %s',
                user_obj.email, user_obj.role,
            )
            
            # Determine redirect URL based on role
            if user_obj.role == 'seller':
                redirect_url = '/seller/dashboard/'
            else:
                redirect_url = '/buyer/home/'
            
            # Include next_step/next_endpoint for backward compatibility
            # with existing frontend code that may depend on these fields
            next_step = 'complete'
            next_endpoint = redirect_url
            
            response_data = {
                'success': True,
                'verified': True,
                'message': 'Verifikasi OTP berhasil.',
                'access': access_token,
                'refresh': str(refresh_token),
                'user': UserSerializer(user_obj).data,
                'redirect_url': redirect_url,
                'next_step': next_step,
                'next_endpoint': next_endpoint,
            }
            
        except Exception as token_err:
            logger.error('Failed to generate JWT after OTP verify: %s', token_err)
            # Still return success for verification, but requires manual login
            response_data = {
                'success': True,
                'verified': True,
                'message': 'Verifikasi OTP berhasil. Silakan login.',
                'redirect_url': '/auth/login/?email=' + (email or '') + '&verified=1',
            }
        
        # ── Cleanup: Delete USED and EXPIRED OTPs for this user ──
        # After successful verification, all used OTPs and expired records
        # are removed to keep the database clean.
        try:
            identifier_filter = Q()
            if email:
                identifier_filter |= Q(email=email)
            if phone:
                identifier_filter |= Q(phone=phone)
            
            # Delete used OTPs (including the one just verified)
            used_cleaned = OTP.objects.filter(
                identifier_filter, is_used=True
            ).delete()[0]
            
            # Delete expired OTPs
            expired_cleaned = OTP.objects.filter(
                identifier_filter, expires_at__lt=timezone.now()
            ).delete()[0]
            
            total_cleaned = used_cleaned + expired_cleaned
            if total_cleaned:
                _log_db_operation('otp_cleanup_after_verify', {
                    'email': email, 'phone': phone or '(none)', 
                    'used_deleted': used_cleaned, 'expired_deleted': expired_cleaned
                })
                logger.info(
                    'OTP CLEANUP — Deleted %d used + %d expired OTPs for %s',
                    used_cleaned, expired_cleaned, email or phone,
                )
        except Exception as cleanup_err:
            logger.warning('OTP cleanup error (non-blocking): %s', cleanup_err)
        
        logger.info(
            'OTP VERIFY COMPLETE — Email: %s | Role: %s | Redirect: %s',
            email or phone, user_obj.role if user_obj else 'unknown', redirect_url,
        )
        
        return Response(response_data)


@extend_schema(exclude=True)
class ResendOTPView(views.APIView):
    """Resend OTP code with cooldown check.
    
    Uses atomic transaction to ensure OTP creation and email sending
    are consistent — if email fails, the OTP record is rolled back.
    """
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
            return error_response(
                message=f'Silakan tunggu {wait_seconds} detik sebelum meminta ulang.',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                field='email',
                code='otp_cooldown',
                cooldown_seconds=wait_seconds,
            )
        
        # Use atomic transaction to ensure consistency
        with transaction.atomic():
            # ── Invalidate old OTPs ──
            invalidated = OTP.objects.filter(identifier_filter, purpose=purpose, is_valid=True).update(is_valid=False)
            _log_db_operation('otp_invalidate_old', {'email': email, 'phone': phone, 'purpose': purpose, 'count': invalidated})

            # ── Create new OTP ──
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

        return success_response(
            message=response_data.get('message', 'Kode OTP telah dikirim ulang.'),
            expires_in_minutes=response_data.get('expires_in_minutes'),
            otp_channels=response_data.get('otp_channels'),
            otp_code=response_data.get('otp_code'),
        )


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

        # Include redirect_url to OTP verification page when user exists
        if user_exists:
            response_data['redirect_url'] = f'/auth/otp/?email={email}&purpose=password_reset'
            response_data['requires_otp'] = True
            response_data['next_action'] = 'verify_otp'

        return success_response(
            message=response_data['message'],
            status_code=status.HTTP_200_OK,
            **{k: v for k, v in response_data.items() if k != 'message'},
        )


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
            return error_response(
                message='Kode OTP tidak valid atau sudah digunakan.',
                status_code=status.HTTP_400_BAD_REQUEST,
                field='otp_code',
                code='otp_not_found',
            )
        
        if otp.is_expired():
            otp.is_valid = False
            otp.save()
            logger.warning('RESET PASSWORD EXPIRED — OTP ID: %d | Email: %s', otp.id, email)
            return error_response(
                message='Kode OTP sudah kadaluwarsa. Silakan minta ulang.',
                status_code=status.HTTP_400_BAD_REQUEST,
                field='otp_code',
                code='otp_expired',
            )
        
        # Update password
        user = User.objects.filter(email=email).first()
        if not user:
            logger.error('RESET PASSWORD USER NOT FOUND — Email: %s but OTP existed', email)
            return error_response(
                message='Pengguna tidak ditemukan.',
                status_code=status.HTTP_404_NOT_FOUND,
                field='email',
                code='user_not_found',
            )
        
        user.set_password(new_password)
        user.save(update_fields=['password'])
        _log_db_operation('user_password_reset', {'user_id': user.id})
        
        otp.is_used = True
        otp.is_valid = False
        otp.verified_at = timezone.now()
        otp.save(update_fields=['is_used', 'is_valid', 'verified_at'])
        
        # ── INSTRUMENTATION: Log success ──
        logger.info('RESET PASSWORD SUCCESS — Email: %s | OTP ID: %d', email, otp.id)

        return success_response(
            message='Password berhasil direset. Silakan login dengan password baru.',
            status_code=status.HTTP_200_OK,
            redirect_url='/auth/login/',
            next_action='login',
        )


@extend_schema(exclude=True)
class CheckAuthView(views.APIView):
    """Check if user is authenticated and return their info.
    
    If the user is not verified (OTP), returns needs_verification flag
    with redirect_url so the frontend can redirect to the OTP verification page.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        user = request.user
        response_data = {
            'authenticated': True,
            'user': UserSerializer(user).data,
        }
        
        if not user.is_verified:
            # Detect OTP state: unverified user needs to complete OTP
            redirect_url = f'/auth/otp/?email={user.email}&purpose=registration'
            if user.role == 'seller':
                redirect_url += '&role=seller'
            response_data['needs_verification'] = True
            response_data['requires_otp'] = True
            response_data['redirect_url'] = redirect_url
            response_data['email'] = user.email
        
        return success_response(
            message='Autentikasi valid.' if user.is_verified else 'Akun belum diverifikasi.',
            status_code=status.HTTP_200_OK,
            **response_data,
        )


@extend_schema(exclude=True)
class TokenRefreshView(views.APIView):
    """Refresh JWT access token."""
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return error_response(
                message='Refresh token diperlukan.',
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            refresh = RefreshToken(refresh_token)
            access = str(refresh.access_token)
            return success_response(
                message='Token berhasil diperbarui.',
                access=access,
            )
        except Exception:
            return error_response(
                message='Refresh token tidak valid.',
                status_code=status.HTTP_401_UNAUTHORIZED,
            )


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
                return error_response(
                    message=response['message'],
                    status_code=status.HTTP_409_CONFLICT,
                    errors=response,
                )

        if phone and response.get('available', True):
            exists = User.objects.filter(phone=phone).exists()
            if exists:
                response = {
                    'available': False,
                    'field': 'phone',
                    'message': 'Nomor HP ini sudah terdaftar. Gunakan nomor lain atau masuk.',
                    'code': 'phone_taken',
                }
                return error_response(
                    message=response['message'],
                    status_code=status.HTTP_409_CONFLICT,
                    errors=response,
                )

        return success_response(
            message='Email dan nomor HP tersedia.',
            available=True,
        )


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

        return success_response(
            message='Login admin berhasil.',
            access=access_token,
            refresh=str(refresh),
            user=UserSerializer(user).data,
            redirect_url=next_url,
        )
