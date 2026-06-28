"""
Social Authentication Views for Warungio Marketplace.
Handles Google, Facebook, and Apple Sign-In via client-side OAuth tokens.
"""

import json
import logging
import requests
from django.conf import settings
from django.contrib.auth import login
from django.utils import timezone
from django.db import transaction
from rest_framework import status, views, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, LoginAttempt
from .serializers import UserSerializer

logger = logging.getLogger('django_backend')


class SocialLoginBase:
    """Base class for social authentication providers."""

    def get_or_create_user(self, email, full_name, provider, provider_id, extra_data=None):
        """Find existing user by email or create a new one."""
        if not email:
            raise ValueError("Email is required from the social provider.")

        from .models import SocialAccount

        # First check if this social account is already linked to any user
        existing_social = SocialAccount.objects.filter(
            provider=provider,
            provider_id=str(provider_id)
        ).select_related('user').first()

        if existing_social:
            # Social account already linked - return the existing user
            existing_social.extra_data = extra_data or {}
            existing_social.save(update_fields=['extra_data'])
            return existing_social.user, False

        # Check by email
        user = User.objects.filter(email=email).first()

        if user:
            # User exists - link social account if not already linked
            self._link_social_account(user, provider, provider_id, extra_data)
            return user, False

        # Create new user
        with transaction.atomic():
            username = email.split('@')[0]
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user = User.objects.create_user(
                username=username,
                email=email,
                full_name=full_name or email.split('@')[0],
                is_verified=True,
                is_active=True,
                role='buyer',
            )
            user.set_unusable_password()
            user.save()

            # Link social account
            self._link_social_account(user, provider, provider_id, extra_data)

        return user, True

    def _link_social_account(self, user, provider, provider_id, extra_data=None):
        """Link or update a social account for the user."""
        from .models import SocialAccount
        account, created = SocialAccount.objects.get_or_create(
            user=user,
            provider=provider,
            provider_id=str(provider_id),
            defaults={'extra_data': extra_data or {}}
        )
        if not created:
            account.extra_data = extra_data or {}
            account.save(update_fields=['extra_data'])
        return account

    def generate_jwt_tokens(self, user, request):
        """Generate JWT tokens for the user."""
        login(request, user, backend='accounts.backends.EmailBackend')
        refresh = RefreshToken.for_user(user)

        # Track login attempt
        LoginAttempt.objects.create(
            email=user.email,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            was_successful=True,
        )

        # Update user metadata
        user.last_login_ip = request.META.get('REMOTE_ADDR')
        user.save(update_fields=['last_login_ip'])

        return {
            'message': 'Login berhasil.',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
            'is_new_user': False,
        }


class GoogleLoginView(views.APIView, SocialLoginBase):
    """
    Google Sign-In authentication.
    Accepts a Google ID token (credential) from the client-side Google Sign-In button.
    """
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        id_token = request.data.get('id_token') or request.data.get('credential')
        if not id_token:
            return Response(
                {'error': 'Token Google tidak ditemukan.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Verify the Google ID token
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests

            id_info = google_id_token.verify_oauth2_token(
                id_token,
                google_requests.Request(),
                audience=settings.GOOGLE_CLIENT_ID
            )

            if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Invalid issuer.')

            email = id_info.get('email')
            if not email:
                return Response(
                    {'error': 'Email tidak ditemukan dari akun Google.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            full_name = id_info.get('name', '')
            provider_id = id_info.get('sub', '')

            user, is_new = self.get_or_create_user(
                email=email,
                full_name=full_name,
                provider='google',
                provider_id=provider_id,
                extra_data={
                    'picture': id_info.get('picture', ''),
                    'locale': id_info.get('locale', ''),
                }
            )

            result = self.generate_jwt_tokens(user, request)
            result['is_new_user'] = is_new
            return Response(result)

        except ValueError as e:
            logger.warning(f"Google token verification failed: {str(e)}")
            return Response(
                {'error': 'Token Google tidak valid.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            logger.error(f"Google login error: {str(e)}")
            return Response(
                {'error': 'Terjadi kesalahan saat memproses login Google.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FacebookLoginView(views.APIView, SocialLoginBase):
    """
    Facebook Login authentication.
    Accepts a Facebook access token from the Facebook Login SDK.
    """
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        access_token = request.data.get('access_token')
        if not access_token:
            return Response(
                {'error': 'Token Facebook tidak ditemukan.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Verify the Facebook access token using Graph API
            app_id = settings.FACEBOOK_APP_ID
            app_secret = settings.FACEBOOK_APP_SECRET

            # First, verify the token is valid
            verify_url = (
                f"https://graph.facebook.com/debug_token"
                f"?input_token={access_token}"
                f"&access_token={app_id}|{app_secret}"
            )
            verify_resp = requests.get(verify_url, timeout=10)
            verify_data = verify_resp.json()

            if 'error' in verify_data or not verify_data.get('data', {}).get('is_valid'):
                return Response(
                    {'error': 'Token Facebook tidak valid.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Get user info from Graph API
            user_info_url = (
                f"https://graph.facebook.com/me"
                f"?fields=id,name,email,picture"
                f"&access_token={access_token}"
            )
            user_resp = requests.get(user_info_url, timeout=10)
            user_data = user_resp.json()

            if 'error' in user_data:
                return Response(
                    {'error': 'Gagal mengambil data pengguna dari Facebook.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            email = user_data.get('email')
            provider_id = user_data.get('id', '')
            full_name = user_data.get('name', '')

            if not email:
                # Facebook might not return email for some accounts
                # Try to get email from the linked accounts
                return Response(
                    {'error': 'Email tidak ditemukan dari akun Facebook. Pastikan email Anda publik di Facebook.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user, is_new = self.get_or_create_user(
                email=email,
                full_name=full_name,
                provider='facebook',
                provider_id=provider_id,
                extra_data={
                    'picture': user_data.get('picture', {}).get('data', {}).get('url', ''),
                }
            )

            result = self.generate_jwt_tokens(user, request)
            result['is_new_user'] = is_new
            return Response(result)

        except requests.RequestException as e:
            logger.error(f"Facebook API error: {str(e)}")
            return Response(
                {'error': 'Gagal terhubung ke Facebook. Silakan coba lagi.'},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            logger.error(f"Facebook login error: {str(e)}")
            return Response(
                {'error': 'Terjadi kesalahan saat memproses login Facebook.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AppleLoginView(views.APIView, SocialLoginBase):
    """
    Apple Sign-In authentication.
    Accepts an Apple identity token from Sign in with Apple JS.
    """
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        identity_token = request.data.get('identity_token')
        authorization_code = request.data.get('authorization_code')
        user_data = request.data.get('user', {})  # Initial user data from Apple (first name, last name)

        if not identity_token and not authorization_code:
            return Response(
                {'error': 'Token Apple tidak ditemukan.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Decode and verify the Apple identity token
            import jwt as pyjwt
            from jwt import PyJWKClient

            # Apple's public key URL
            keys_url = 'https://appleid.apple.com/auth/keys'
            jwks_client = PyJWKClient(keys_url)

            if identity_token:
                try:
                    # Get the signing key
                    signing_key = jwks_client.get_signing_key_from_jwt(identity_token)

                    # Verify the token
                    decoded = pyjwt.decode(
                        identity_token,
                        signing_key.key,
                        algorithms=['RS256'],
                        audience=settings.APPLE_CLIENT_ID,
                        issuer='https://appleid.apple.com',
                    )
                except pyjwt.ExpiredSignatureError:
                    return Response(
                        {'error': 'Token Apple sudah kadaluwarsa.'},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
                except pyjwt.InvalidTokenError as e:
                    logger.warning(f"Apple token verification failed: {str(e)}")
                    return Response(
                        {'error': 'Token Apple tidak valid.'},
                        status=status.HTTP_401_UNAUTHORIZED
                    )

                email = decoded.get('email')
                apple_sub = decoded.get('sub', '')

                # Apple returns email only on first sign-in
                # For subsequent sign-ins, we use the 'sub' to find the user
                if not email:
                    # Try to find user by Apple social account
                    from .models import SocialAccount
                    social_account = SocialAccount.objects.filter(
                        provider='apple',
                        provider_id=apple_sub
                    ).first()
                    if social_account:
                        email = social_account.user.email
                    else:
                        return Response(
                            {'error': 'Email tidak tersedia dari Apple. Silakan masuk menggunakan email untuk akun yang sudah terdaftar.'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
            else:
                # No identity token, try to use the authorization code
                # This is a fallback - exchange the code for tokens
                return Response(
                    {'error': 'Identity token diperlukan untuk autentikasi Apple.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Extract name from Apple's response (only provided on first sign-in)
            full_name = ''
            if isinstance(user_data, dict):
                first_name = user_data.get('name', {}).get('firstName', '')
                last_name = user_data.get('name', {}).get('lastName', '')
                if first_name or last_name:
                    full_name = f"{first_name} {last_name}".strip()

            user, is_new = self.get_or_create_user(
                email=email,
                full_name=full_name,
                provider='apple',
                provider_id=apple_sub,
                extra_data={
                    'has_email': bool(email),
                }
            )

            result = self.generate_jwt_tokens(user, request)
            result['is_new_user'] = is_new
            return Response(result)

        except requests.RequestException as e:
            logger.error(f"Apple API error: {str(e)}")
            return Response(
                {'error': 'Gagal terhubung ke Apple. Silakan coba lagi.'},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            logger.error(f"Apple login error: {str(e)}")
            return Response(
                {'error': 'Terjadi kesalahan saat memproses login Apple.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SocialAccountStatusView(views.APIView):
    """
    Get the social accounts linked to the current user.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        from .models import SocialAccount
        accounts = SocialAccount.objects.filter(user=request.user)
        return Response({
            'accounts': [
                {
                    'provider': acc.provider,
                    'provider_id': acc.provider_id,
                    'created_at': acc.created_at.isoformat() if acc.created_at else None,
                }
                for acc in accounts
            ]
        })

    def delete(self, request):
        """Unlink a social account."""
        provider = request.data.get('provider')
        if not provider:
            return Response(
                {'error': 'Provider harus diisi.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from .models import SocialAccount
        deleted, _ = SocialAccount.objects.filter(
            user=request.user,
            provider=provider
        ).delete()

        if deleted:
            return Response({'message': f'Akun {provider} berhasil diputuskan.'})
        return Response(
            {'error': 'Akun tidak ditemukan.'},
            status=status.HTTP_404_NOT_FOUND
        )


class GoogleAuthConfigView(views.APIView):
    """
    Returns the Google Client ID for the frontend.
    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        return Response({
            'google_client_id': settings.GOOGLE_CLIENT_ID,
        })


class FacebookAuthConfigView(views.APIView):
    """
    Returns the Facebook App ID for the frontend.
    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        return Response({
            'facebook_app_id': settings.FACEBOOK_APP_ID,
        })
