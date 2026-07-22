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

    def test_seller_login_full_flow(self):
        """Test dedicated seller login: JWT tokens, session, profile, cross-role guard."""
        # Login as seller
        response = self.client.post(self.login_url, {
            'email': 'seller@warungio.com',
            'password': 'TestPass123!',
            'login_entry': 'seller',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['role'], 'seller')
        self.assertEqual(response.data['user']['email'], 'seller@warungio.com')
        token = response.data['access']

        # Verify JWT token works for protected endpoints
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Check auth returns seller data
        check = self.client.get(self.check_auth_url)
        self.assertEqual(check.status_code, status.HTTP_200_OK)
        self.assertTrue(check.data['authenticated'])
        self.assertEqual(check.data['user']['role'], 'seller')
        
        # Profile returns seller role
        profile = self.client.get(self.profile_url)
        self.assertEqual(profile.status_code, status.HTTP_200_OK)
        self.assertEqual(profile.data['role'], 'seller')

        # Cross-role guard: buyer login_entry for seller account should fail
        buyer_login = self.client.post(self.login_url, {
            'email': 'seller@warungio.com',
            'password': 'TestPass123!',
            'login_entry': 'buyer',
        }, format='json')
        self.assertEqual(buyer_login.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(buyer_login.data.get('code'), 'role_mismatch')

        # Session cookie should be set
        session_cookie_set = any(
            k.startswith('sessionid') for k in response.cookies.keys()
        )
        self.assertTrue(session_cookie_set, 'Django session cookie should be set')

    def test_seller_login_rejects_wrong_password(self):
        """Test seller login with wrong password."""
        response = self.client.post(self.login_url, {
            'email': 'seller@warungio.com',
            'password': 'WrongPass999!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('access', response.data)

    def test_seller_login_rejects_buyer_role_mismatch(self):
        """Test that a buyer user cannot login as seller."""
        response = self.client.post(self.login_url, {
            'email': 'verified@warungio.com',
            'password': 'TestPass123!',
            'login_entry': 'seller',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data.get('code'), 'role_mismatch')
        self.assertEqual(response.data.get('user_role'), 'buyer')


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
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

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

    def test_resend_otp_success(self):
        """Test successful OTP resend after cooldown expires."""
        from django.utils import timezone
        from datetime import timedelta

        # Create an OTP that's old enough to be eligible for resend
        old_otp = OTP.objects.create(
            email='verified@warungio.com',
            purpose='login',
            otp_code='111111',
        )
        # Backdate it past the cooldown
        cooldown = getattr(settings, 'OTP_COOLDOWN_SECONDS', 60)
        old_otp.created_at = timezone.now() - timedelta(seconds=cooldown + 10)
        old_otp.save(update_fields=['created_at'])

        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            response = self.client.post(reverse('otp-resend'), {
                'email': 'verified@warungio.com',
                'purpose': 'login',
            }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('expires_in_minutes', response.data)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(OTP_COOLDOWN_SECONDS=60)
    def test_resend_otp_cooldown_blocked(self):
        """Test that resend is blocked during cooldown period."""
        from django.utils import timezone

        # Create a recent OTP (just created = cooldown not expired)
        OTP.objects.create(
            email='verified@warungio.com',
            purpose='login',
            otp_code='222222',
        )

        response = self.client.post(reverse('otp-resend'), {
            'email': 'verified@warungio.com',
            'purpose': 'login',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn('cooldown_seconds', response.data)
        self.assertIn('otp_cooldown', response.data.get('code', ''))

    @override_settings(OTP_COOLDOWN_SECONDS=60)
    def test_resend_otp_invalidates_old_otps(self):
        """Test that resend invalidates previous OTPs."""
        from django.utils import timezone
        from datetime import timedelta

        # Create old OTP past cooldown
        old_otp = OTP.objects.create(
            email='verified@warungio.com',
            purpose='login',
            otp_code='333333',
        )
        cooldown = getattr(settings, 'OTP_COOLDOWN_SECONDS', 60)
        old_otp.created_at = timezone.now() - timedelta(seconds=cooldown + 10)
        old_otp.save(update_fields=['created_at'])
        old_otp_id = old_otp.id

        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            response = self.client.post(reverse('otp-resend'), {
                'email': 'verified@warungio.com',
                'purpose': 'login',
            }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh from DB — old OTP should be invalid
        old_otp.refresh_from_db()
        self.assertFalse(old_otp.is_valid)

        # A new OTP should exist and be valid
        new_otps = OTP.objects.filter(
            email='verified@warungio.com', purpose='login', is_valid=True
        )
        self.assertEqual(new_otps.count(), 1)
        self.assertNotEqual(new_otps.first().id, old_otp_id)

    @override_settings(OTP_COOLDOWN_SECONDS=60, DEBUG=True)
    def test_resend_otp_new_code_expiry(self):
        """Test that resend generates a new code with correct expiration."""
        from django.utils import timezone
        from datetime import timedelta

        # Create old OTP past cooldown
        old_otp = OTP.objects.create(
            email='verified@warungio.com',
            purpose='login',
            otp_code='444444',
        )
        cooldown = getattr(settings, 'OTP_COOLDOWN_SECONDS', 60)
        old_otp.created_at = timezone.now() - timedelta(seconds=cooldown + 10)
        old_otp.save(update_fields=['created_at'])

        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            response = self.client.post(reverse('otp-resend'), {
                'email': 'verified@warungio.com',
                'purpose': 'login',
            }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # New OTP code should be returned in DEBUG mode
        self.assertIn('otp_code', response.data)
        new_code = response.data['otp_code']
        self.assertNotEqual(new_code, '444444')

        # Verify expiration is in the future (within expected window)
        new_otp = OTP.objects.get(
            email='verified@warungio.com', purpose='login', is_valid=True
        )
        expected_expiry = timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
        self.assertLess(
            new_otp.expires_at - timezone.now(),
            expected_expiry + timedelta(seconds=5)  # 5s tolerance
        )
        self.assertGreater(new_otp.expires_at, timezone.now())


@override_settings(DEBUG=True)
class SellerE2EFlowTests(TestCase):
    """
    Comprehensive end-to-end test for the complete Seller (Mitra) flow.
    
    Tests every step: register → OTP verify → login → JWT access →
    protected API endpoints → seller dashboard pages → token refresh.
    Verifies all database records and ensures no HTTP 4xx/5xx errors.
    """

    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.otp_verify_url = reverse('otp-verify')
        self.login_url = reverse('login')
        self.check_auth_url = reverse('check-auth')
        self.profile_url = reverse('profile')
        self.seller_email = 'mitra.seller@warungio.com'
        self.seller_password = 'MitraPass789!'
        self.seller_full_name = 'Toko Sembako Sejahtera'

    def _assert_no_client_error(self, response, step_name):
        """Assert no HTTP 4xx or 5xx errors at any step.
        
        Handles both DRF API responses (with .data) and template responses.
        """
        body = getattr(response, 'data', None) or getattr(response, 'content', b'')[:500]
        self.assertNotEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST,
            f'{step_name}: Got HTTP 400. Body: {body}'
        )
        self.assertNotEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED,
            f'{step_name}: Got HTTP 401. Body: {body}'
        )
        self.assertNotEqual(
            response.status_code, status.HTTP_403_FORBIDDEN,
            f'{step_name}: Got HTTP 403. Body: {body}'
        )
        self.assertNotEqual(
            response.status_code, status.HTTP_404_NOT_FOUND,
            f'{step_name}: Got HTTP 404. Body: {body}'
        )
        self.assertNotEqual(
            response.status_code, status.HTTP_429_TOO_MANY_REQUESTS,
            f'{step_name}: Got HTTP 429. Body: {body}'
        )
        self.assertNotEqual(
            response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR,
            f'{step_name}: Got HTTP 500. Body: {body}'
        )

    def test_seller_full_registration_and_login(self):
        """Test complete Seller flow: register → OTP verify → login → protected endpoints."""

        # =====================================================================
        # STEP 1: Register as Seller (Mitra)
        # =====================================================================
        register_response = self.client.post(self.register_url, {
            'email': self.seller_email,
            'full_name': self.seller_full_name,
            'password': self.seller_password,
            'password2': self.seller_password,
            'phone': '+6281234567890',
            'address': 'Jl. Merdeka No. 10, Jakarta',
            'role': 'seller',
        }, format='json')

        self.assertEqual(
            register_response.status_code, status.HTTP_201_CREATED,
            f'Step 1 - Seller registration failed: {register_response.data}'
        )
        self._assert_no_client_error(register_response, 'Step 1 - Register')
        self.assertEqual(register_response.data['user']['role'], 'seller')
        self.assertEqual(register_response.data['user']['email'], self.seller_email)
        self.assertIn('otp_code', register_response.data,
                      'OTP code should be returned in DEBUG mode')
        otp_code = register_response.data['otp_code']
        self.assertEqual(len(otp_code), 6, 'OTP code should be 6 digits')
        
        # Verify OTP record in DB
        otp_records = OTP.objects.filter(email=self.seller_email, purpose='registration')
        self.assertEqual(otp_records.count(), 1, 'Should be exactly 1 OTP record')
        otp_db = otp_records.first()
        self.assertTrue(otp_db.is_valid, 'OTP should be valid')
        self.assertFalse(otp_db.is_used, 'OTP should not be used yet')
        self.assertEqual(otp_db.attempts, 0, 'OTP should have 0 attempts')
        self.assertIsNotNone(otp_db.expires_at, 'OTP should have expiry')
        self.assertGreater(otp_db.expires_at, otp_db.created_at, 'Expiry should be in the future')

        # Verify User record in DB
        user = User.objects.get(email=self.seller_email)
        self.assertEqual(user.role, 'seller', 'User role should be seller')
        self.assertFalse(user.is_verified, 'User should NOT be verified before OTP')
        self.assertFalse(user.is_active, 'User should be INACTIVE until OTP verification')
        self.assertEqual(user.registration_step, 'email_phone')
        self.assertTrue(user.check_password(self.seller_password),
                        'Password should be correctly hashed')
        self.assertFalse(user.password.startswith(self.seller_password),
                         'Password should NOT be stored as plaintext')
        self.assertEqual(user.email, self.seller_email)
        self.assertEqual(user.full_name, self.seller_full_name)
        self.assertEqual(str(user.phone), '+6281234567890')
        self.assertEqual(user.address, 'Jl. Merdeka No. 10, Jakarta')
        self.assertIsNone(user.registration_completed_at,
                          'registration_completed_at should NOT be set before OTP')
        
        # Verify NO store exists yet (not auto-created before OTP verification)
        from stores.models import Store
        pre_store_count = Store.objects.filter(user=user).count()
        self.assertEqual(pre_store_count, 0,
                         'Store should NOT exist before OTP verification')
        
        # Verify LoginAttempt is NOT created during registration
        self.assertFalse(
            LoginAttempt.objects.filter(email=self.seller_email).exists(),
            'No LoginAttempt should exist after registration'
        )

        # =====================================================================
        # STEP 2: OTP Verification (Account Activation)
        # =====================================================================
        verify_response = self.client.post(self.otp_verify_url, {
            'email': self.seller_email,
            'otp_code': otp_code,
            'purpose': 'registration',
        }, format='json')

        self.assertEqual(
            verify_response.status_code, status.HTTP_200_OK,
            f'Step 2 - OTP verification failed: {verify_response.data}'
        )
        self._assert_no_client_error(verify_response, 'Step 2 - OTP Verify')
        self.assertTrue(verify_response.data['verified'])
        self.assertIn('next_step', verify_response.data)
        self.assertEqual(verify_response.data['next_step'], 'complete')
        self.assertIn('next_endpoint', verify_response.data)
        self.assertEqual(verify_response.data['next_endpoint'], '/seller/dashboard/')

        # Verify User record after activation
        user.refresh_from_db()
        self.assertTrue(user.is_verified, 'User should be verified after OTP')
        self.assertTrue(user.is_active, 'User should be active after OTP verification')
        self.assertEqual(user.registration_step, 'complete')
        self.assertIsNotNone(user.registration_completed_at,
                             'registration_completed_at should be set after OTP')
        self.assertGreater(user.registration_completed_at, user.registration_started_at or user.date_joined,
                          'completion time should be after start')
        
        # Verify OTP record after activation
        # OTP cleanup runs after successful verification to delete used + expired records.
        # Check that the OTP was either cleaned up or properly marked.
        otp_after = OTP.objects.filter(
            email=self.seller_email, purpose='registration'
        ).first()
        if otp_after is None:
            # OTP was cleaned up (deleted) — expected behavior
            pass
        else:
            # OTP still exists but must be marked as used/invalid
            self.assertFalse(otp_after.is_valid, 'OTP should be invalid after verification')
            self.assertTrue(otp_after.is_used, 'OTP should be marked as used')
            self.assertIsNotNone(otp_after.verified_at, 'OTP should have verified_at timestamp')

        # =====================================================================
        # STEP 3: Verify Store Auto-Creation
        # =====================================================================
        store = Store.objects.filter(user=user).first()
        self.assertIsNotNone(store, 'Step 3 - Store should be auto-created for seller after OTP')
        self.assertEqual(store.store_name, 'Toko Sembako Sejahtera',
                         'Store name should match full_name with Toko prefix deduplicated')
        self.assertEqual(store.status, 'pending', 'New store should be in pending status')
        self.assertIn('Mitra Warungio', store.description or '',
                      'Store description should mention Mitra Warungio')
        self.assertEqual(store.address, 'Jl. Merdeka No. 10, Jakarta',
                         'Store address should match user address')
        self.assertIsNotNone(store.slug, 'Store should have a slug generated')
        self.assertEqual(store.follower_count, 0, 'New store should have 0 followers')
        self.assertEqual(store.product_count, 0, 'New store should have 0 products')
        self.assertEqual(float(store.rating_avg), 0.0, 'New store should have 0 rating')
        self.assertEqual(float(store.total_sales), 0.0, 'New store should have 0 sales')
        
        # Verify only ONE store was created (no duplicates)
        store_count = Store.objects.filter(user=user).count()
        self.assertEqual(store_count, 1, 'Should be exactly 1 store per seller')

        # =====================================================================
        # STEP 4: Login (JWT Token Generation)
        # =====================================================================
        login_response = self.client.post(self.login_url, {
            'email': self.seller_email,
            'password': self.seller_password,
        }, format='json')

        self.assertEqual(
            login_response.status_code, status.HTTP_200_OK,
            f'Step 4 - Seller login failed. Response: {login_response.data}'
        )
        self._assert_no_client_error(login_response, 'Step 4 - Login')
        
        # Verify JWT tokens
        self.assertIn('access', login_response.data, 'Access token should be returned')
        self.assertIn('refresh', login_response.data, 'Refresh token should be returned')
        access_token = login_response.data['access']
        refresh_token = login_response.data['refresh']
        self.assertTrue(len(access_token) > 50, 'Access token should be a valid JWT')
        self.assertTrue(len(refresh_token) > 50, 'Refresh token should be a valid JWT')
        
        # Verify user data in response
        self.assertEqual(login_response.data['user']['role'], 'seller')
        self.assertEqual(login_response.data['user']['email'], self.seller_email)
        self.assertTrue(login_response.data['user']['is_verified'])
        self.assertIn('id', login_response.data['user'])
        self.assertEqual(login_response.data['user']['id'], user.id)
        
        # Verify LoginAttempt was tracked
        attempt = LoginAttempt.objects.filter(email=self.seller_email).first()
        self.assertIsNotNone(attempt, 'LoginAttempt should be created')
        self.assertTrue(attempt.was_successful)
        
        # Verify Django session was set (for template-based pages)
        # The session cookie should be present in the response
        session_cookie_set = any(
            k.startswith('sessionid') for k in login_response.cookies.keys()
        )
        self.assertTrue(session_cookie_set,
                        'Django session cookie should be set for template access')

        # =====================================================================
        # STEP 5: JWT-Protected API Endpoints
        # =====================================================================
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        # 5a. Check-Auth endpoint
        check_response = self.client.get(self.check_auth_url)
        self.assertEqual(
            check_response.status_code, status.HTTP_200_OK,
            f'Step 5a - Check-Auth failed: {check_response.data}'
        )
        self._assert_no_client_error(check_response, 'Step 5a - Check Auth')
        self.assertTrue(check_response.data['authenticated'])
        self.assertEqual(check_response.data['user']['role'], 'seller')
        self.assertEqual(check_response.data['user']['email'], self.seller_email)
        self.assertEqual(check_response.data['user']['id'], user.id)
        
        # 5b. Profile endpoint
        profile_response = self.client.get(self.profile_url)
        self.assertEqual(
            profile_response.status_code, status.HTTP_200_OK,
            f'Step 5b - Profile failed: {profile_response.data}'
        )
        self._assert_no_client_error(profile_response, 'Step 5b - Profile')
        self.assertEqual(profile_response.data['email'], self.seller_email)
        self.assertEqual(profile_response.data['role'], 'seller')
        self.assertTrue(profile_response.data['is_verified'])
        self.assertEqual(profile_response.data['full_name'], self.seller_full_name)
        
        # 5c. My Store endpoint
        my_store_response = self.client.get('/api/stores/my-store/')
        self.assertEqual(
            my_store_response.status_code, status.HTTP_200_OK,
            f'Step 5c - My Store failed: {my_store_response.data}'
        )
        self._assert_no_client_error(my_store_response, 'Step 5c - My Store')
        self.assertEqual(my_store_response.data['store_name'], 'Toko Sembako Sejahtera')
        self.assertEqual(my_store_response.data['status'], 'pending')
        # MyStore endpoint returns `user` as integer (user ID), not nested object
        if isinstance(my_store_response.data.get('user'), dict):
            self.assertEqual(my_store_response.data['user']['id'], user.id)
        else:
            self.assertEqual(my_store_response.data['user'], user.id)

        # =====================================================================
        # STEP 6: Seller Dashboard Pages (Session-Based Access)
        # =====================================================================
        # Since login() was called in LoginView, the session cookie is available.
        # We need to include the session cookie from the login response.
        
        # 6a. Seller Dashboard page
        dashboard_response = self.client.get('/seller/dashboard/',
            HTTP_COOKIE=f'sessionid={login_response.cookies.get("sessionid").value}')
        self.assertEqual(
            dashboard_response.status_code, status.HTTP_200_OK,
            f'Step 6a - Seller Dashboard returned {dashboard_response.status_code}'
        )
        self._assert_no_client_error(dashboard_response, 'Step 6a - Seller Dashboard')
        
        # 6b. Seller Products page
        products_page_response = self.client.get('/seller/products/',
            HTTP_COOKIE=f'sessionid={login_response.cookies.get("sessionid").value}')
        self.assertEqual(
            products_page_response.status_code, status.HTTP_200_OK,
            f'Step 6b - Seller Products page returned {products_page_response.status_code}'
        )
        self._assert_no_client_error(products_page_response, 'Step 6b - Seller Products')
        
        # 6c. Seller Orders page
        orders_page_response = self.client.get('/seller/orders/',
            HTTP_COOKIE=f'sessionid={login_response.cookies.get("sessionid").value}')
        self.assertEqual(
            orders_page_response.status_code, status.HTTP_200_OK,
            f'Step 6c - Seller Orders page returned {orders_page_response.status_code}'
        )
        self._assert_no_client_error(orders_page_response, 'Step 6c - Seller Orders')
        
        # 6d. Seller Partner Guide page
        partner_page_response = self.client.get('/seller/partner-guide/',
            HTTP_COOKIE=f'sessionid={login_response.cookies.get("sessionid").value}')
        self.assertEqual(
            partner_page_response.status_code, status.HTTP_200_OK,
            f'Step 6d - Seller Partner Guide returned {partner_page_response.status_code}'
        )
        self._assert_no_client_error(partner_page_response, 'Step 6d - Partner Guide')

        # =====================================================================
        # STEP 7: JWT Token Refresh
        # =====================================================================
        refresh_response = self.client.post(reverse('token-refresh'), {
            'refresh': refresh_token
        }, format='json')
        self.assertEqual(
            refresh_response.status_code, status.HTTP_200_OK,
            f'Step 7 - Token refresh failed: {refresh_response.data}'
        )
        self._assert_no_client_error(refresh_response, 'Step 7 - Token Refresh')
        self.assertIn('access', refresh_response.data,
                      'New access token should be returned')
        new_access_token = refresh_response.data['access']
        self.assertTrue(len(new_access_token) > 50, 'New access token should be a valid JWT')
        self.assertNotEqual(new_access_token, access_token,
                            'New access token should differ from original')

        # =====================================================================
        # STEP 8: Verify New JWT Token Works
        # =====================================================================
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_access_token}')
        reauth_response = self.client.get(self.check_auth_url)
        self.assertEqual(
            reauth_response.status_code, status.HTTP_200_OK,
            f'Step 8 - Re-auth with refreshed token failed: {reauth_response.data}'
        )
        self._assert_no_client_error(reauth_response, 'Step 8 - Re-auth')
        self.assertTrue(reauth_response.data['authenticated'])
        self.assertEqual(reauth_response.data['user']['role'], 'seller')
        self.assertEqual(reauth_response.data['user']['email'], self.seller_email)

        # =====================================================================
        # FINAL: Verify NO duplicate records in the entire flow
        # =====================================================================
        user_count = User.objects.filter(email=self.seller_email).count()
        self.assertEqual(user_count, 1, 'Should be exactly 1 user')
        
        store_count = Store.objects.filter(user=user).count()
        self.assertEqual(store_count, 1, 'Should be exactly 1 store')
        
        # OTP records are soft-invalidated after successful verification.
        # The OTP should be marked as used+invalid rather than deleted.
        remaining_otps = OTP.objects.filter(email=self.seller_email, purpose='registration')
        self.assertEqual(remaining_otps.count(), 1, 'OTP should remain in DB after soft-invalidate')
        otp_after = remaining_otps.first()
        self.assertFalse(otp_after.is_valid, 'OTP should be invalid after verification')
        self.assertTrue(otp_after.is_used, 'OTP should be marked as used')
        self.assertIsNotNone(otp_after.verified_at, 'OTP should have verified_at timestamp')

    def test_seller_flow_rejects_unverified_login(self):
        """Test that unverified seller cannot login (verification gate)."""
        # Register seller but DON'T verify OTP
        register_response = self.client.post(self.register_url, {
            'email': self.seller_email,
            'full_name': self.seller_full_name,
            'password': self.seller_password,
            'password2': self.seller_password,
            'phone': '+6281234567899',
            'address': 'Jl. Test No. 1',
            'role': 'seller',
        }, format='json')
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)

        # Try login without OTP verification — should be blocked
        login_response = self.client.post(self.login_url, {
            'email': self.seller_email,
            'password': self.seller_password,
        }, format='json')
        self.assertEqual(
            login_response.status_code, status.HTTP_403_FORBIDDEN,
            'Unverified seller should be blocked from login'
        )
        self.assertTrue(login_response.data.get('needs_verification', False),
                        'Response should indicate verification is needed')
        self.assertEqual(login_response.data.get('email'), self.seller_email,
                         'Response should include email for OTP redirect')
        
        # Verify no JWT tokens are returned
        self.assertNotIn('access', login_response.data,
                         'No JWT access token should be returned for unverified user')
        self.assertNotIn('refresh', login_response.data,
                         'No JWT refresh token should be returned for unverified user')
        
        # Verify no store was created (OTP not verified)
        from stores.models import Store
        user = User.objects.get(email=self.seller_email)
        store_count = Store.objects.filter(user=user).count()
        self.assertEqual(store_count, 0,
                         'Store should NOT be created if OTP is not verified')
        
        # LoginAttempt is only created AFTER the is_verified check in LoginView
        # (the view returns early for unverified users before LoginAttempt creation).
        # So no LoginAttempt is expected here.

    def test_seller_flow_wrong_password_rejected(self):
        """Test that wrong password is rejected at every stage."""
        # Register seller
        register_response = self.client.post(self.register_url, {
            'email': self.seller_email,
            'full_name': self.seller_full_name,
            'password': self.seller_password,
            'password2': self.seller_password,
            'phone': '+6281234567888',
            'address': 'Jl. Salah No. 1',
            'role': 'seller',
        }, format='json')
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        otp_code = register_response.data['otp_code']

        # Verify OTP
        verify_response = self.client.post(self.otp_verify_url, {
            'email': self.seller_email,
            'otp_code': otp_code,
            'purpose': 'registration',
        }, format='json')
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)

        # Try login with wrong password
        login_response = self.client.post(self.login_url, {
            'email': self.seller_email,
            'password': 'WrongPassword999!',
        }, format='json')
        self.assertEqual(
            login_response.status_code, status.HTTP_400_BAD_REQUEST,
            'Wrong password should return HTTP 400'
        )

    def test_seller_flow_protected_pages_reject_unauthenticated(self):
        """Test that unauthenticated users cannot access seller pages."""
        # Access seller dashboard without auth — should redirect to login
        dashboard_response = self.client.get('/seller/dashboard/')
        self.assertEqual(
            dashboard_response.status_code, status.HTTP_302_FOUND,
            'Unauthenticated access should redirect'
        )
        # Django login_required redirects to settings.LOGIN_URL which defaults to /accounts/login/
        # unless configured. The actual redirect uses ?next= parameter.
        self.assertIn('next=/seller/dashboard/', dashboard_response.url or '',
                      'Redirect should include next parameter for post-login redirect')
        
        # Access seller products without auth — should redirect to login
        products_response = self.client.get('/seller/products/')
        self.assertEqual(
            products_response.status_code, status.HTTP_302_FOUND,
            'Unauthenticated access should redirect'
        )
        self.assertIn('next=/seller/products/', products_response.url or '',
                      'Redirect should include next parameter for post-login redirect')
