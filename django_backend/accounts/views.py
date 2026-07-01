"""
Accounts views for Warungio Marketplace.
Authentication, OTP verification, profile management.
"""

import logging
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from rest_framework import status, generics, permissions, views, throttling

logger = logging.getLogger(__name__)
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, OTP, LoginAttempt
from .services.notification_service import notification_service
from .services.whatsapp_service import send_whatsapp_otp, _whatsapp_configured
from .serializers import (
    RegisterSerializer, LoginSerializer, UserSerializer,
    UserUpdateSerializer, ChangePasswordSerializer,
    OTPRequestSerializer, OTPVerifySerializer,
    ForgotPasswordSerializer, ResetPasswordSerializer,
    TokenSerializer
)


class RegisterView(generics.CreateAPIView):
    """User registration endpoint."""
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
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

        # Send OTP via email (primary for email-based registration)
        email_result = notification_service.send_otp(
            identifier=user.email,
            otp_code=otp.otp_code,
            purpose='registration',
            user_full_name=user.full_name,
        )

        # Also send OTP via WhatsApp if user provided a phone number
        wa_result = None
        if user.phone and _whatsapp_configured():
            wa_result = send_whatsapp_otp(
                phone=str(user.phone),
                otp_code=otp.otp_code,
                purpose='registration',
                user_full_name=user.full_name,
            )

        response_data = {
            'message': 'Registrasi berhasil. Silakan verifikasi OTP.',
            'otp_channels': [],
        }
        if email_result.get('success'):
            response_data['otp_channels'].append('email')
        if wa_result and wa_result.get('success'):
            response_data['otp_channels'].append('whatsapp')
        
        if not email_result.get('success') and (not wa_result or not wa_result.get('success')):
            response_data['warning'] = 'Gagal mengirim kode verifikasi. Silakan coba lagi nanti.'

        if settings.DEBUG:
            response_data.update({
                'user': UserSerializer(user).data,
                'otp_code': otp.otp_code,
            })

        return Response(response_data, status=status.HTTP_201_CREATED)


class LoginView(views.APIView):
    """User login with JWT token response."""
    permission_classes = (permissions.AllowAny,)
    throttle_classes = [throttling.UserRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Check OTP verification
        if not user.is_verified:
            return Response({
                'error': 'Akun belum diverifikasi. Silakan verifikasi OTP terlebih dahulu.',
                'needs_verification': True,
                'email': user.email,
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        
        # Track login
        LoginAttempt.objects.create(
            email=user.email,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            was_successful=True,
        )
        
        # Update device info
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        user.last_login_ip = request.META.get('REMOTE_ADDR')
        user.save(update_fields=['last_login_ip'])
        
        return Response({
            'message': 'Login berhasil.',
            'access': access_token,
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        })


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
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data.get('email')
        phone = serializer.validated_data.get('phone')
        purpose = serializer.validated_data.get('purpose')
        user_full_name = None
        
        # Check rate limit
        recent_otps = OTP.objects.filter(
            email=email,
            purpose=purpose,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=1)
        )
        if recent_otps.count() >= 3:
            return Response({
                'error': 'Terlalu banyak permintaan OTP. Silakan coba lagi nanti.'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Invalidate old OTPs
        OTP.objects.filter(
            email=email, purpose=purpose, is_valid=True
        ).update(is_valid=False)
        
        # Create new OTP
        otp = OTP.objects.create(
            email=email,
            phone=phone,
            purpose=purpose,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )

        response_data = {
            'message': 'Kode OTP telah dikirim.',
            'expires_in_minutes': settings.OTP_EXPIRE_MINUTES,
        }

        if email:
            user_full_name = None
            user = User.objects.filter(email=email).first()
            if user:
                user_full_name = user.full_name

            email_result = notification_service.send_otp(
                identifier=email or phone,
                otp_code=otp.otp_code,
                purpose=purpose,
                user_full_name=user_full_name,
            )
            if not email_result.get('success'):
                response_data['warning'] = email_result.get(
                    'error', 'Gagal mengirim kode verifikasi OTP. Silakan coba lagi nanti.'
                )

        # Send OTP via WhatsApp if phone is provided and configured
        if phone and _whatsapp_configured():
            wa_result = send_whatsapp_otp(
                phone=phone,
                otp_code=otp.otp_code,
                purpose=purpose,
                user_full_name=user_full_name,
            )
            if wa_result.get('success'):
                response_data['otp_channels'] = ['email', 'whatsapp']
                response_data['message'] = 'Kode OTP telah dikirim via Email dan WhatsApp.'

        # Return OTP in debug mode
        if settings.DEBUG:
            response_data['otp_code'] = otp.otp_code

        return Response(response_data)


class OTPVerifyView(views.APIView):
    """Verify OTP code."""
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data.get('email')
        phone = serializer.validated_data.get('phone')
        otp_code = serializer.validated_data['otp_code']
        purpose = serializer.validated_data['purpose']
        
        # Find valid OTP — support both email-based and phone-based lookup
        otp = None
        if email:
            otp = OTP.objects.filter(
                email=email,
                purpose=purpose,
                is_valid=True,
                is_used=False,
                otp_code=otp_code,
            ).first()
        if not otp and phone:
            otp = OTP.objects.filter(
                phone=phone,
                purpose=purpose,
                is_valid=True,
                is_used=False,
                otp_code=otp_code,
            ).first()
        
        if not otp:
            return Response({
                'error': 'Kode OTP tidak valid.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if otp.is_expired():
            otp.is_valid = False
            otp.save()
            return Response({
                'error': 'Kode OTP sudah kadaluwarsa.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if otp.is_locked():
            return Response({
                'error': 'Terlalu banyak percobaan. Silakan minta OTP baru.'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Verify OTP
        otp.is_used = True
        otp.is_valid = False
        otp.verified_at = timezone.now()
        otp.save()
        
        # Update user verification status (support both email and phone verification)
        if purpose == 'registration' or purpose == 'email_change':
            if email:
                User.objects.filter(email=email).update(is_verified=True)
            elif phone:
                User.objects.filter(phone=phone).update(is_verified=True)
        
        return Response({
            'message': 'Verifikasi OTP berhasil.',
            'verified': True,
        })


class ResendOTPView(views.APIView):
    """Resend OTP code with cooldown check."""
    permission_classes = (permissions.AllowAny,)
    throttle_scope = 'otp'

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data.get('email')
        purpose = serializer.validated_data.get('purpose')
        
        # Check cooldown
        last_otp = OTP.objects.filter(
            email=email, purpose=purpose
        ).order_by('-created_at').first()
        
        if last_otp and not last_otp.can_resend():
            wait_seconds = settings.OTP_COOLDOWN_SECONDS - (
                timezone.now() - last_otp.created_at
            ).seconds
            return Response({
                'error': f'Silakan tunggu {wait_seconds} detik sebelum meminta ulang.',
                'cooldown_seconds': wait_seconds,
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Create new OTP
        otp = OTP.objects.create(
            email=email,
            purpose=purpose,
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        response_data = {
            'message': 'Kode OTP telah dikirim ulang.',
            'expires_in_minutes': settings.OTP_EXPIRE_MINUTES,
        }

        if email:
            user_full_name = None
            user = User.objects.filter(email=email).first()
            if user:
                user_full_name = user.full_name

            email_result = notification_service.send_otp(
                identifier=email,
                otp_code=otp.otp_code,
                purpose=purpose,
                user_full_name=user_full_name,
            )
            if not email_result.get('success'):
                response_data['warning'] = email_result.get(
                    'error', 'Gagal mengirim kode verifikasi OTP. Silakan coba lagi nanti.'
                )

        # Send OTP via WhatsApp if phone is provided and configured
        if phone and _whatsapp_configured():
            wa_result = send_whatsapp_otp(
                phone=phone,
                otp_code=otp.otp_code,
                purpose=purpose,
            )
            if wa_result.get('success'):
                response_data['otp_channels'] = ['email', 'whatsapp']
                response_data['message'] = 'Kode OTP telah dikirim ulang via Email dan WhatsApp.'

        if settings.DEBUG:
            response_data['otp_code'] = otp.otp_code

        return Response(response_data)


class ForgotPasswordView(views.APIView):
    """Forgot password - send OTP."""
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        # Create reset OTP
        otp = OTP.objects.create(
            email=email,
            purpose='password_reset',
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        response_data = {
            'message': 'Kode reset password telah dikirim ke email Anda.',
        }

        email_result = notification_service.send_otp(
            identifier=email,
            otp_code=otp.otp_code,
            purpose='password_reset',
            user_full_name=None,
        )
        if not email_result.get('success'):
            response_data['warning'] = email_result.get(
                'error', 'Gagal mengirim kode verifikasi OTP. Silakan coba lagi nanti.'
            )

        if settings.DEBUG:
            response_data['otp_code'] = otp.otp_code

        return Response(response_data)


class ResetPasswordView(views.APIView):
    """Reset password with OTP verification."""
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        otp_code = serializer.validated_data['otp_code']
        new_password = serializer.validated_data['new_password']
        
        # Verify OTP
        otp = OTP.objects.filter(
            email=email,
            purpose='password_reset',
            is_valid=True,
            is_used=False,
            otp_code=otp_code,
        ).first()
        
        if not otp or otp.is_expired():
            return Response({
                'error': 'Kode OTP tidak valid atau sudah kadaluwarsa.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update password
        user = User.objects.filter(email=email).first()
        if not user:
            return Response({
                'error': 'Pengguna tidak ditemukan.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        user.set_password(new_password)
        user.save()
        
        otp.is_used = True
        otp.is_valid = False
        otp.save()
        
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
    """Root view redirecting logged-in users based on role, rendering landing for guests.
    
    Unverified users (missing OTP) are redirected to the OTP verification page
    instead of the dashboard, regardless of role.
    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        from django.shortcuts import redirect, render
        if request.user.is_authenticated:
            # If user is not verified, redirect to OTP page
            if not request.user.is_verified:
                return redirect(f'/auth/otp/?email={request.user.email}&purpose=registration')
            
            role = getattr(request.user, 'role', 'buyer')
            if role == 'seller':
                return redirect('/seller/dashboard/')
            elif role == 'admin' or request.user.is_superuser:
                return redirect('/admin/')
            else:
                return redirect('/buyer/home/')
        return render(request, 'landing/index.html')
