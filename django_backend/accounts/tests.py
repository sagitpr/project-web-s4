"""
Comprehensive test suite for Warungio authentication system.
Tests email/password auth, OTP verification, and social auth (Google, Facebook, Apple).
"""

import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from django.core import mail
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, OTP, SocialAccount, LoginAttempt


class BaseTestCase(TestCase):
    """Base test class with common setup."""

    @classmethod
    def setUpTestData(cls):
        """Create shared data once per class (avoids 153× password hashing)."""
        cls.register_url = reverse('register')
        cls.login_url = reverse('login')
        cls.logout_url = reverse('logout')
        cls.check_auth_url = reverse('check-auth')
        cls.profile_url = reverse('profile')
        cls.change_password_url = reverse('change-password')
        cls.otp_request_url = reverse('otp-request')
        cls.otp_verify_url = reverse('otp-verify')
        cls.forgot_password_url = reverse('forgot-password')
        cls.reset_password_url = reverse('reset-password')
        cls.social_google_url = reverse('social-google')
        cls.social_facebook_url = reverse('social-facebook')
        cls.social_apple_url = reverse('social-apple')

        cls.user_data = {
            'email': 'test@warungio.com',
            'full_name': 'Test User',
            'password': 'TestPass123!',
            'password2': 'TestPass123!',
            'phone': '+6281234567890',
            'address': 'Jl. Test No. 123',
            'role': 'buyer',
        }

        cls.verified_user = User.objects.create_user(
            username='verified',
            email='verified@warungio.com',
            password='TestPass123!',
            full_name='Verified User',
            is_verified=True,
        )
        cls.unverified_user = User.objects.create_user(
            username='unverified',
            email='unverified@warungio.com',
            password='TestPass123!',
            full_name='Unverified User',
            is_verified=False,
        )
        cls.seller_user = User.objects.create_user(
            username='seller',
            email='seller@warungio.com',
            password='TestPass123!',
            full_name='Seller User',
            role='seller',
            is_verified=True,
        )

    def setUp(self):
        self.client = APIClient()


# =============================================================================
# REGISTRATION TESTS
# =============================================================================

@override_settings(DEBUG=True)
class RegistrationTests(BaseTestCase):
    """Test user registration flow."""

    def test_register_success(self):
        """Test successful user registration."""
        response = self.client.post(
            self.register_url, self.user_data, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        self.assertIn('user', response.data)

        # Verify user was created
        self.assertTrue(User.objects.filter(email='test@warungio.com').exists())

    def test_register_duplicate_email(self):
        """Test registration with existing email."""
        self.client.post(self.register_url, self.user_data, format='json')
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_password_mismatch(self):
        """Test registration with mismatched passwords."""
        data = self.user_data.copy()
        data['password2'] = 'DifferentPass123!'
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_fields(self):
        """Test registration with missing required fields."""
        response = self.client.post(self.register_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_creates_otp(self):
        """Test that registration creates an OTP for verification."""
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email='test@warungio.com')
        otps = OTP.objects.filter(user=user, purpose='registration')
        self.assertTrue(otps.exists())

    def test_register_seller_role(self):
        """Test registration with seller role."""
        data = self.user_data.copy()
        data['role'] = 'seller'
        data['email'] = 'newseller@test.com'
        data['full_name'] = 'New Seller'
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['role'], 'seller')


# =============================================================================
# LOGIN TESTS
# =============================================================================

class LoginTests(BaseTestCase):
    """Test user login flow."""

    def test_login_success(self):
        """Test successful login with valid credentials."""
        response = self.client.post(self.login_url, {
            'email': 'verified@warungio.com',
            'password': 'TestPass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['role'], 'buyer')

    def test_login_wrong_password(self):
        """Test login with wrong password."""
        response = self.client.post(self.login_url, {
            'email': 'verified@warungio.com',
            'password': 'WrongPass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_nonexistent_email(self):
        """Test login with unregistered email."""
        response = self.client.post(self.login_url, {
            'email': 'nonexistent@warungio.com',
            'password': 'TestPass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_unverified_user(self):
        """Test login with unverified account."""
        response = self.client.post(self.login_url, {
            'email': 'unverified@warungio.com',
            'password': 'TestPass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(response.data.get('needs_verification', False))

    def test_login_missing_fields(self):
        """Test login with missing fields."""
        response = self.client.post(self.login_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_tracks_attempt(self):
        """Test that login creates a LoginAttempt record."""
        self.client.post(self.login_url, {
            'email': 'verified@warungio.com',
            'password': 'TestPass123!',
        }, format='json')
        attempt = LoginAttempt.objects.filter(email='verified@warungio.com').first()
        self.assertIsNotNone(attempt)
        self.assertTrue(attempt.was_successful)


# =============================================================================
# AUTH STATE / SESSION TESTS
# =============================================================================

class AuthStateTests(BaseTestCase):
    """Test authentication state, session, and logout."""

    def test_check_auth_authenticated(self):
        """Test checking auth status when logged in."""
        # Login first
        login_response = self.client.post(self.login_url, {
            'email': 'verified@warungio.com',
            'password': 'TestPass123!',
        }, format='json')
        token = login_response.data['access']

        # Check auth
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(self.check_auth_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['authenticated'])

    def test_check_auth_unauthenticated(self):
        """Test checking auth status without token."""
        response = self.client.get(self.check_auth_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_success(self):
        """Test successful logout."""
        login_response = self.client.post(self.login_url, {
            'email': 'verified@warungio.com',
            'password': 'TestPass123!',
        }, format='json')
        token = login_response.data['access']
        refresh = login_response.data['refresh']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.post(self.logout_url, {
            'refresh': refresh
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_token_refresh(self):
        """Test JWT token refresh."""
        login_response = self.client.post(self.login_url, {
            'email': 'verified@warungio.com',
            'password': 'TestPass123!',
        }, format='json')
        refresh = login_response.data['refresh']

        response = self.client.post(reverse('token-refresh'), {
            'refresh': refresh
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_seller_role_redirect(self):
        """Test that seller users get seller role in response."""
        response = self.client.post(self.login_url, {
            'email': 'seller@warungio.com',
            'password': 'TestPass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['role'], 'seller')


# =============================================================================
# SOCIAL AUTHENTICATION TESTS
# =============================================================================

class SocialAuthTests(BaseTestCase):
    """Test social authentication flows."""

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_google_login_new_user(self, mock_verify):
        """Test Google login creates a new user."""
        mock_verify.return_value = {
            'email': 'googleuser@gmail.com',
            'name': 'Google User',
            'sub': '123456789',
            'picture': 'https://example.com/pic.jpg',
            'iss': 'accounts.google.com',
        }

        response = self.client.post(self.social_google_url, {
            'credential': 'fake-google-token',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertTrue(response.data['is_new_user'])

        # Verify user was created
        user = User.objects.filter(email='googleuser@gmail.com').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.is_verified)

        # Verify social account was linked
        social_account = SocialAccount.objects.filter(
            user=user, provider='google'
        ).first()
        self.assertIsNotNone(social_account)

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_google_login_existing_user(self, mock_verify):
        """Test Google login links to existing user."""
        # Create a user with same email first
        User.objects.create_user(
            username='existing',
            email='existing@gmail.com',
            password='TestPass123!',
            full_name='Existing User',
            is_verified=True,
        )

        mock_verify.return_value = {
            'email': 'existing@gmail.com',
            'name': 'Existing User',
            'sub': '987654321',
            'picture': 'https://example.com/pic.jpg',
            'iss': 'accounts.google.com',
        }

        response = self.client.post(self.social_google_url, {
            'credential': 'fake-google-token',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_new_user'])

        # Verify social account was linked
        user = User.objects.get(email='existing@gmail.com')
        social_account = SocialAccount.objects.filter(
            user=user, provider='google'
        ).first()
        self.assertIsNotNone(social_account)

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_google_login_duplicate_provider_id(self, mock_verify):
        """Test duplicate social account linking uses existing account."""
        # First login
        mock_verify.return_value = {
            'email': 'first@gmail.com',
            'name': 'First User',
            'sub': 'same-sub-id',
            'iss': 'accounts.google.com',
        }

        response1 = self.client.post(self.social_google_url, {
            'credential': 'fake-token-1',
        }, format='json')
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Second login with different email but same sub (should not create duplicate)
        mock_verify.return_value = {
            'email': 'second@gmail.com',
            'name': 'Second User',
            'sub': 'same-sub-id',  # Same Google account
            'iss': 'accounts.google.com',
        }

        response2 = self.client.post(self.social_google_url, {
            'credential': 'fake-token-2',
        }, format='json')
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        # Should still only have 1 social account with this sub
        accounts = SocialAccount.objects.filter(
            provider='google', provider_id='same-sub-id'
        )
        self.assertEqual(accounts.count(), 1)

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_google_login_invalid_token(self, mock_verify):
        """Test Google login with invalid token."""
        mock_verify.side_effect = ValueError('Invalid token')

        response = self.client.post(self.social_google_url, {
            'credential': 'invalid-token',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('requests.get')
    def test_facebook_login_new_user(self, mock_get):
        """Test Facebook login creates a new user."""
        # Mock token verification
        mock_verify_response = MagicMock()
        mock_verify_response.json.return_value = {
            'data': {
                'is_valid': True,
                'app_id': '123456',
            }
        }

        # Mock user info response
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {
            'id': 'facebook-id-123',
            'name': 'Facebook User',
            'email': 'fbuser@facebook.com',
            'picture': {
                'data': {
                    'url': 'https://example.com/fb-pic.jpg'
                }
            }
        }

        mock_get.side_effect = [mock_verify_response, mock_user_response]

        response = self.client.post(self.social_facebook_url, {
            'access_token': 'fake-facebook-token',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_new_user'])

        # Verify user was created
        user = User.objects.filter(email='fbuser@facebook.com').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.is_verified)

    @patch('requests.get')
    def test_facebook_login_existing_user(self, mock_get):
        """Test Facebook login with existing email links account."""
        # Create user first
        User.objects.create_user(
            username='existingfb',
            email='existingfb@gmail.com',
            password='TestPass123!',
            full_name='Existing FB User',
            is_verified=True,
        )

        mock_verify_response = MagicMock()
        mock_verify_response.json.return_value = {
            'data': {'is_valid': True, 'app_id': '123456'}
        }
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {
            'id': 'fb-id-existing',
            'name': 'Existing FB User',
            'email': 'existingfb@gmail.com',
        }
        mock_get.side_effect = [mock_verify_response, mock_user_response]

        response = self.client.post(self.social_facebook_url, {
            'access_token': 'fake-fb-token',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_new_user'])

        # Verify social account linked
        user = User.objects.get(email='existingfb@gmail.com')
        self.assertTrue(
            SocialAccount.objects.filter(
                user=user, provider='facebook'
            ).exists()
        )

    @patch('requests.get')
    def test_facebook_login_invalid_token(self, mock_get):
        """Test Facebook login with invalid token."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'error': {'message': 'Invalid token', 'type': 'OAuthException'}
        }
        mock_get.return_value = mock_response

        response = self.client.post(self.social_facebook_url, {
            'access_token': 'invalid-token',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('jwt.PyJWKClient')
    @patch('jwt.decode')
    def test_apple_login_new_user(self, mock_decode, mock_jwks_client):
        """Test Apple Sign-In creates a new user."""
        mock_decode.return_value = {
            'email': 'appleuser@icloud.com',
            'sub': 'apple-sub-001',
            'iss': 'https://appleid.apple.com',
        }

        mock_jwks_instance = MagicMock()
        mock_jwks_instance.get_signing_key_from_jwt.return_value = MagicMock()
        mock_jwks_client.return_value = mock_jwks_instance

        response = self.client.post(self.social_apple_url, {
            'identity_token': 'fake-apple-token',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_new_user'])

        # Verify user was created
        user = User.objects.filter(email='appleuser@icloud.com').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.is_verified)

    @patch('jwt.PyJWKClient')
    @patch('jwt.decode')
    def test_apple_login_with_name(self, mock_decode, mock_jwks_client):
        """Test Apple Sign-In with user name from initial sign-up."""
        mock_decode.return_value = {
            'email': 'appleuser2@icloud.com',
            'sub': 'apple-sub-002',
            'iss': 'https://appleid.apple.com',
        }

        mock_jwks_instance = MagicMock()
        mock_jwks_instance.get_signing_key_from_jwt.return_value = MagicMock()
        mock_jwks_client.return_value = mock_jwks_instance

        response = self.client.post(self.social_apple_url, {
            'identity_token': 'fake-apple-token',
            'user': {
                'name': {
                    'firstName': 'John',
                    'lastName': 'Appleseed',
                }
            },
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(email='appleuser2@icloud.com')
        self.assertEqual(user.full_name, 'John Appleseed')

    def test_apple_login_missing_token(self):
        """Test Apple Sign-In without identity token."""
        response = self.client.post(self.social_apple_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_social_auth_no_token(self):
        """Test social auth endpoints without token."""
        response = self.client.post(self.social_google_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(self.social_facebook_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_social_duplicate_email_prevention(self):
        """Test that social login doesn't create duplicate accounts for same email."""
        # Create user with email
        User.objects.create_user(
            username='dupuser',
            email='duplicate@gmail.com',
            password='TestPass123!',
            full_name='Dup User',
            is_verified=True,
        )

        # Both Google and Facebook should link to the same user
        from unittest.mock import patch as _patch

        with _patch('google.oauth2.id_token.verify_oauth2_token') as mock_google:
            mock_google.return_value = {
                'email': 'duplicate@gmail.com',
                'name': 'Dup User',
                'sub': 'google-sub-dup',
                'iss': 'accounts.google.com',
            }
            response = self.client.post(self.social_google_url, {
                'credential': 'fake-token',
            }, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should be 1 user with this email
        users = User.objects.filter(email='duplicate@gmail.com')
        self.assertEqual(users.count(), 1)

    def test_role_assignment_after_social_login(self):
        """Test that social login users get 'buyer' role by default."""
        from unittest.mock import patch as _patch

        with _patch('google.oauth2.id_token.verify_oauth2_token') as mock_verify:
            mock_verify.return_value = {
                'email': 'socialbuyer@gmail.com',
                'name': 'Social Buyer',
                'sub': 'social-sub-1',
                'iss': 'accounts.google.com',
            }
            response = self.client.post(self.social_google_url, {
                'credential': 'fake-token',
            }, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['user']['role'], 'buyer')


# =============================================================================
# SECURITY TESTS
# =============================================================================

class SecurityTests(BaseTestCase):
    """Test authentication security measures."""

    def test_sql_injection_login(self):
        """Test SQL injection attempt on login."""
        response = self.client.post(self.login_url, {
            'email': "' OR '1'='1",
            'password': "' OR '1'='1",
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_xss_injection(self):
        """Test XSS attempt on registration."""
        data = self.user_data.copy()
        data['email'] = '<script>alert("xss")</script>@test.com'
        response = self.client.post(self.register_url, data, format='json')
        # Should still work (Django escapes automatically) or fail validation
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_201_CREATED])

    def test_empty_password(self):
        """Test login with empty password."""
        response = self.client.post(self.login_url, {
            'email': 'verified@warungio.com',
            'password': '',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_long_email(self):
        """Test login with extremely long email."""
        response = self.client.post(self.login_url, {
            'email': 'a' * 500 + '@test.com',
            'password': 'TestPass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_jwt_access(self):
        """Test accessing protected endpoint with invalid JWT."""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid-token-here')
        response = self.client.get(self.check_auth_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_auth_header(self):
        """Test accessing protected endpoint without auth."""
        response = self.client.get(self.check_auth_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_session_persistence(self):
        """Test that JWT tokens persist across requests."""
        login_response = self.client.post(self.login_url, {
            'email': 'verified@warungio.com',
            'password': 'TestPass123!',
        }, format='json')
        token = login_response.data['access']

        # First request
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response1 = self.client.get(self.check_auth_url)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Second request (same token)
        response2 = self.client.get(self.check_auth_url)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        # Verify same user
        self.assertEqual(
            response1.data['user']['id'],
            response2.data['user']['id']
        )

    def test_password_hashing(self):
        """Test that passwords are stored hashed."""
        User.objects.create_user(
            username='hash_test',
            email='hash@test.com',
            password='SecurePass123!',
            full_name='Hash Test',
        )
        user = User.objects.get(email='hash@test.com')
        self.assertNotEqual(user.password, 'SecurePass123!')
        self.assertTrue(user.password.startswith('pbkdf2_') or
                       user.password.startswith('bcrypt') or
                       user.password.startswith('argon2'))

    def test_refresh_token_blacklist(self):
        """Test that refresh tokens can be blacklisted."""
        login_response = self.client.post(self.login_url, {
            'email': 'verified@warungio.com',
            'password': 'TestPass123!',
        }, format='json')
        refresh = login_response.data['refresh']

        # Blacklist the token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_response.data["access"]}')
        response = self.client.post(self.logout_url, {'refresh': refresh}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Try to use blacklisted refresh token
        response = self.client.post(reverse('token-refresh'), {
            'refresh': refresh
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# =============================================================================
# PROFILE & PASSWORD CHANGE TESTS
# =============================================================================

class ProfileTests(BaseTestCase):
    """Test profile management."""

    def setUp(self):
        self.client = APIClient()
        # Login using shared users from setUpTestData
        login_response = self.client.post(self.login_url, {
            'email': 'verified@warungio.com',
            'password': 'TestPass123!',
        }, format='json')
        self.token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_get_profile(self):
        """Test getting user profile."""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'verified@warungio.com')

    def test_update_profile(self):
        """Test updating user profile."""
        response = self.client.patch(self.profile_url, {
            'full_name': 'Updated Name',
            'address': 'Jl. Baru No. 456',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['full_name'], 'Updated Name')

    def test_change_password(self):
        """Test changing password."""
        response = self.client.post(self.change_password_url, {
            'old_password': 'TestPass123!',
            'new_password': 'NewPass456!',
            'new_password2': 'NewPass456!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_change_password_wrong_old(self):
        """Test changing password with wrong old password."""
        response = self.client.post(self.change_password_url, {
            'old_password': 'WrongOldPass!',
            'new_password': 'NewPass456!',
            'new_password2': 'NewPass456!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# =============================================================================
# OTP TESTS
# =============================================================================

class OTPTests(BaseTestCase):
    """Test OTP verification flow."""

    def test_request_otp(self):
        """Test requesting an OTP code."""
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            response = self.client.post(self.otp_request_url, {
                'email': 'verified@warungio.com',
                'purpose': 'login',
            }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Kode OTP Masuk Warungio', mail.outbox[0].subject)
        self.assertIn('verified@warungio.com', mail.outbox[0].to)

    @override_settings(DEBUG=True)
    def test_otp_returns_code_in_debug(self):
        """Test OTP code returned in debug mode."""
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            response = self.client.post(self.otp_request_url, {
                'email': 'verified@warungio.com',
                'purpose': 'login',
            }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('otp_code', response.data)
        self.assertEqual(len(mail.outbox), 1)

    def test_verify_otp_success(self):
        """Test successful OTP verification."""
        # Create OTP
        otp = OTP.objects.create(
            email='unverified@warungio.com',
            purpose='registration',
            otp_code='123456',
        )

        response = self.client.post(self.otp_verify_url, {
            'email': 'unverified@warungio.com',
            'otp_code': '123456',
            'purpose': 'registration',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['verified'])

        # Check user is now verified
        user = User.objects.get(email='unverified@warungio.com')
        self.assertTrue(user.is_verified)

    def test_verify_otp_failed(self):
        """Test OTP verification with wrong code."""
        response = self.client.post(self.otp_verify_url, {
            'email': 'unverified@warungio.com',
            'otp_code': '999999',
            'purpose': 'registration',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_otp_expired(self):
        """Test OTP verification with expired code."""
        from django.utils import timezone
        from datetime import timedelta

        otp = OTP.objects.create(
            email='unverified@warungio.com',
            purpose='registration',
            otp_code='654321',
        )
        otp.expires_at = timezone.now() - timedelta(hours=1)
        otp.save()

        response = self.client.post(self.otp_verify_url, {
            'email': 'unverified@warungio.com',
            'otp_code': '654321',
            'purpose': 'registration',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_forgot_password_success(self):
        """Test forgot password request."""
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            response = self.client.post(self.forgot_password_url, {
                'email': 'verified@warungio.com',
            }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Kode OTP Reset Password Warungio', mail.outbox[0].subject)

    def test_forgot_password_nonexistent(self):
        """Test forgot password with unregistered email — returns 200 to prevent user enumeration."""
        response = self.client.post(self.forgot_password_url, {
            'email': 'nonexistent@test.com',
        }, format='json')
        # Returns 200 with same message as registered email to prevent user enumeration
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_reset_password_success(self):
        """Test complete password reset flow."""
        # Create OTP
        otp = OTP.objects.create(
            email='verified@warungio.com',
            purpose='password_reset',
            otp_code='111222',
        )

        response = self.client.post(self.reset_password_url, {
            'email': 'verified@warungio.com',
            'otp_code': '111222',
            'new_password': 'NewResetPass123!',
            'new_password2': 'NewResetPass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify can login with new password
        login_response = self.client.post(self.login_url, {
            'email': 'verified@warungio.com',
            'password': 'NewResetPass123!',
        }, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
