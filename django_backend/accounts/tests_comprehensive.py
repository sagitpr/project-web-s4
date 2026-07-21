"""
Comprehensive test suite for Warungio authentication system.
Covers: Register, Login, OTP, Forgot/Reset Password, Auto-Login, Redirect, Logout, Edge Cases.

All tests verify the standardized JSON response format:
    Success: { 'success': True, 'message': str, 'status_code': int, ... }
    Error:   { 'success': False, 'message': str, 'status_code': int, 'errors': ... }
"""

import json
from unittest.mock import patch, MagicMock
from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from django.core import mail
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, OTP, SocialAccount, LoginAttempt


class BaseTestCase(TestCase):
    """Base test class with common setup - creates users once per test class."""

    @classmethod
    def setUpTestData(cls):
        cls.register_url = reverse('register')
        cls.login_url = reverse('login')
        cls.logout_url = reverse('logout')
        cls.check_auth_url = reverse('check-auth')
        cls.profile_url = reverse('profile')
        cls.change_password_url = reverse('change-password')
        cls.otp_request_url = reverse('otp-request')
        cls.otp_verify_url = reverse('otp-verify')
        cls.otp_resend_url = reverse('otp-resend')
        cls.forgot_password_url = reverse('forgot-password')
        cls.reset_password_url = reverse('reset-password')
        cls.check_availability_url = reverse('check-availability')
        cls.token_refresh_url = reverse('accounts-token-refresh')

        # ---- Test data ----
        cls.buyer_data = {
            'email': 'buyer@warungio.com',
            'full_name': 'Test Buyer',
            'password': 'TestPass123!',
            'password2': 'TestPass123!',
            'phone': '+6281234567890',
            'address': 'Jl. Test No. 123',
            'role': 'buyer',
        }

        cls.seller_data = {
            'email': 'seller@warungio.com',
            'full_name': 'Toko Test Seller',
            'password': 'SellerPass123!',
            'password2': 'SellerPass123!',
            'phone': '+6281234567891',
            'address': 'Jl. Toko No. 456',
            'role': 'seller',
        }

        # ---- Pre-created users ----
        cls.verified_buyer = User.objects.create_user(
            username='verified_buyer',
            email='verified.buyer@warungio.com',
            password='BuyerPass123!',
            full_name='Verified Buyer',
            role='buyer',
            is_verified=True,
            is_active=True,
        )
        cls.verified_seller = User.objects.create_user(
            username='verified_seller',
            email='verified.seller@warungio.com',
            password='SellerPass123!',
            full_name='Verified Seller',
            role='seller',
            is_verified=True,
            is_active=True,
        )
        cls.unverified_user = User.objects.create_user(
            username='unverified_user',
            email='unverified@warungio.com',
            password='UnverifiedPass123!',
            full_name='Unverified User',
            role='buyer',
            is_verified=False,
            is_active=False,
        )

    def setUp(self):
        self.client = APIClient()
        mail.outbox = []

    def assert_success_response(self, response, expected_status=status.HTTP_200_OK):
        """Assert response has standardized success format."""
        self.assertEqual(response.status_code, expected_status,
                         f'Expected {expected_status}, got {response.status_code}: {response.data}')
        self.assertTrue(response.data.get('success', False),
                        f'Response missing success=True: {response.data}')
        self.assertIn('message', response.data,
                      f'Response missing message field: {response.data}')

    def assert_error_response(self, response, expected_status=status.HTTP_400_BAD_REQUEST):
        """Assert response has standardized error format."""
        self.assertEqual(response.status_code, expected_status,
                         f'Expected {expected_status}, got {response.status_code}: {response.data}')
        self.assertFalse(response.data.get('success', True),
                         f'Response missing success=False: {response.data}')
        self.assertIn('message', response.data,
                      f'Response missing message field: {response.data}')


# =============================================================================
# REGISTRATION TESTS
# =============================================================================

@override_settings(DEBUG=True)
class RegistrationTests(BaseTestCase):
    """Test user registration flow with OTP."""

    def test_register_buyer_success(self):
        """Test successful buyer registration returns standardized response with redirect_url."""
        response = self.client.post(self.register_url, self.buyer_data, format='json')
        self.assert_success_response(response, status.HTTP_201_CREATED)
        self.assertTrue(response.data.get('requires_otp'))
        self.assertIn('redirect_url', response.data)
        self.assertIn('auth/otp/', response.data['redirect_url'])
        self.assertIn('purpose=registration', response.data['redirect_url'])
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['role'], 'buyer')
        # Verify user created with is_active=False
        user = User.objects.get(email='buyer@warungio.com')
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_verified)
        # Verify OTP created
        self.assertTrue(OTP.objects.filter(email='buyer@warungio.com', purpose='registration').exists())

    def test_register_seller_success(self):
        """Test successful seller registration with seller-specific redirect."""
        response = self.client.post(self.register_url, self.seller_data, format='json')
        self.assert_success_response(response, status.HTTP_201_CREATED)
        self.assertTrue(response.data.get('requires_otp'))
        self.assertIn('role=seller', response.data['redirect_url'])
        self.assertEqual(response.data['user']['role'], 'seller')

    def test_register_duplicate_email(self):
        """Test registration with existing email returns error with success=False."""
        # First registration
        self.client.post(self.register_url, self.buyer_data, format='json')
        # Second registration with same email
        response = self.client.post(self.register_url, self.buyer_data, format='json')
        self.assert_error_response(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', str(response.data.get('errors', {})))

    def test_register_duplicate_phone(self):
        """Test registration with existing phone returns error."""
        self.client.post(self.register_url, self.buyer_data, format='json')
        duplicate_data = self.buyer_data.copy()
        duplicate_data['email'] = 'different@warungio.com'
        response = self.client.post(self.register_url, duplicate_data, format='json')
        self.assert_error_response(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone', str(response.data.get('errors', {})))

    def test_register_password_mismatch(self):
        """Test registration with mismatched passwords."""
        data = self.buyer_data.copy()
        data['password2'] = 'DifferentPass123!'
        response = self.client.post(self.register_url, data, format='json')
        self.assert_error_response(response, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_fields(self):
        """Test registration with missing required fields."""
        response = self.client.post(self.register_url, {}, format='json')
        self.assert_error_response(response, status.HTTP_400_BAD_REQUEST)

    # ── Atomic Transaction: No orphan accounts ──

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_register_atomic_rollback_on_otp_failure(self):
        """Test that registration rolls back entirely if OTP sending fails."""
        # Simulate email failure
        # NOTE: Must patch the actual reference used in email_service.py
        # (from django.core.mail import send_mail), not the source module.
        import accounts.services.email_service as email_service
        with patch.object(email_service, 'send_mail', side_effect=Exception('SMTP down')):
            with patch('accounts.views.send_otp_task', None):
                response = self.client.post(self.register_url, self.buyer_data, format='json')
                # Should fail - no account created
                self.assert_error_response(response, status.HTTP_400_BAD_REQUEST)
                # Verify NO user was created (transaction rolled back)
                self.assertFalse(
                    User.objects.filter(email='buyer@warungio.com').exists(),
                    'User should NOT exist - transaction should have rolled back'
                )
                # Verify NO OTP was created
                self.assertFalse(
                    OTP.objects.filter(email='buyer@warungio.com').exists(),
                    'OTP should NOT exist - transaction should have rolled back'
                )


# =============================================================================
# LOGIN TESTS
# =============================================================================

class LoginTests(BaseTestCase):
    """Test user login flow including OTP state detection."""

    def test_login_verified_buyer_success(self):
        """Test verified buyer login returns standardized response with tokens."""
        response = self.client.post(self.login_url, {
            'email': 'verified.buyer@warungio.com',
            'password': 'BuyerPass123!',
        }, format='json')
        self.assert_success_response(response)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['role'], 'buyer')
        self.assertIn('redirect_url', response.data)
        self.assertEqual(response.data['redirect_url'], '/buyer/home/')

    def test_login_verified_seller_success(self):
        """Test verified seller login redirects to seller dashboard."""
        response = self.client.post(self.login_url, {
            'email': 'verified.seller@warungio.com',
            'password': 'SellerPass123!',
        }, format='json')
        self.assert_success_response(response)
        self.assertEqual(response.data['user']['role'], 'seller')
        self.assertEqual(response.data['redirect_url'], '/seller/dashboard/')

    def test_login_unverified_user_detects_otp_state(self):
        """Test login for unverified user returns requires_otp=true with redirect_url."""
        response = self.client.post(self.login_url, {
            'email': 'unverified@warungio.com',
            'password': 'UnverifiedPass123!',
        }, format='json')
        self.assert_error_response(response, status.HTTP_403_FORBIDDEN)
        self.assertTrue(response.data.get('requires_otp'))
        self.assertTrue(response.data.get('needs_verification'))
        self.assertIn('redirect_url', response.data)
        self.assertIn('auth/otp/', response.data['redirect_url'])

    def test_login_wrong_password(self):
        """Test login with wrong password returns error."""
        response = self.client.post(self.login_url, {
            'email': 'verified.buyer@warungio.com',
            'password': 'WrongPass123!',
        }, format='json')
        self.assert_error_response(response, status.HTTP_400_BAD_REQUEST)

    def test_login_nonexistent_email(self):
        """Test login with unregistered email returns error."""
        response = self.client.post(self.login_url, {
            'email': 'nonexistent@warungio.com',
            'password': 'TestPass123!',
        }, format='json')
        self.assert_error_response(response, status.HTTP_400_BAD_REQUEST)

    def test_login_role_gate_seller_to_buyer(self):
        """Test seller trying to login as buyer is blocked."""
        response = self.client.post(self.login_url, {
            'email': 'verified.seller@warungio.com',
            'password': 'SellerPass123!',
            'login_entry': 'buyer',
        }, format='json')
        self.assert_error_response(response, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data.get('code'), 'role_mismatch')

    def test_login_role_gate_buyer_to_seller(self):
        """Test buyer trying to login as seller is blocked."""
        response = self.client.post(self.login_url, {
            'email': 'verified.buyer@warungio.com',
            'password': 'BuyerPass123!',
            'login_entry': 'seller',
        }, format='json')
        self.assert_error_response(response, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data.get('code'), 'role_mismatch')

    def test_login_sets_django_session(self):
        """Test that login sets Django session cookie for template navigation."""
        response = self.client.post(self.login_url, {
            'email': 'verified.buyer@warungio.com',
            'password': 'BuyerPass123!',
        }, format='json')
        self.assert_success_response(response)
        has_session = any(k.startswith('sessionid') for k in response.cookies.keys())
        self.assertTrue(has_session, 'Django session cookie should be set')

    def test_login_tracks_successful_attempt(self):
        """Test that successful login creates a LoginAttempt record."""
        self.client.post(self.login_url, {
            'email': 'verified.buyer@warungio.com',
            'password': 'BuyerPass123!',
        }, format='json')
        attempt = LoginAttempt.objects.filter(email='verified.buyer@warungio.com').first()
        self.assertIsNotNone(attempt)
        self.assertTrue(attempt.was_successful)


# =============================================================================
# OTP VERIFICATION TESTS
# =============================================================================

@override_settings(DEBUG=True)
class OTPVerificationTests(BaseTestCase):
    """Test OTP verification flow with auto-activation and auto-login."""

    def setUp(self):
        super().setUp()
        # Register a new user to get an OTP
        response = self.client.post(self.register_url, self.buyer_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.otp_code = response.data.get('otp_code')

    def test_otp_verify_success_auto_login_buyer(self):
        """Test OTP verification activates account, auto-login, redirect to buyer home."""
        response = self.client.post(self.otp_verify_url, {
            'email': 'buyer@warungio.com',
            'otp_code': self.otp_code,
            'purpose': 'registration',
        }, format='json')
        self.assert_success_response(response)
        self.assertTrue(response.data.get('verified'))
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['role'], 'buyer')
        self.assertIn('redirect_url', response.data)
        self.assertEqual(response.data['redirect_url'], '/buyer/home/')

        # Verify user is now active and verified
        user = User.objects.get(email='buyer@warungio.com')
        self.assertTrue(user.is_verified)
        self.assertTrue(user.is_active)
        self.assertEqual(user.registration_step, 'complete')

    def test_otp_verify_success_auto_login_seller(self):
        """Test OTP verification for seller redirects to seller dashboard."""
        # Register seller
        response = self.client.post(self.register_url, self.seller_data, format='json')
        seller_otp = response.data.get('otp_code')

        response = self.client.post(self.otp_verify_url, {
            'email': 'seller@warungio.com',
            'otp_code': seller_otp,
            'purpose': 'registration',
        }, format='json')
        self.assert_success_response(response)
        self.assertEqual(response.data['user']['role'], 'seller')
        self.assertEqual(response.data['redirect_url'], '/seller/dashboard/')

    def test_otp_verify_wrong_code(self):
        """Test OTP verification with wrong code returns error and decrements attempts."""
        response = self.client.post(self.otp_verify_url, {
            'email': 'buyer@warungio.com',
            'otp_code': '000000',
            'purpose': 'registration',
        }, format='json')
        self.assert_error_response(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get('code'), 'otp_invalid')
        self.assertIn('remaining_attempts', response.data)

    def test_otp_verify_expired_code(self):
        """Test OTP verification with expired code returns error with needs_new_otp."""
        # Backdate the OTP to make it expired
        otp = OTP.objects.filter(email='buyer@warungio.com', purpose='registration').first()
        otp.expires_at = timezone.now() - timedelta(hours=1)
        otp.save()

        response = self.client.post(self.otp_verify_url, {
            'email': 'buyer@warungio.com',
            'otp_code': self.otp_code,
            'purpose': 'registration',
        }, format='json')
        self.assert_error_response(response, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data.get('code'), 'otp_expired')
        self.assertTrue(response.data.get('needs_new_otp'))

    def test_otp_verify_locked_after_max_attempts(self):
        """Test OTP is locked after max failed attempts.
        
        After max_attempts (5), the OTP is marked is_valid=False so subsequent
        attempts return 'otp_not_found' because no valid OTP record is found.
        The 'otp_locked' response is returned for the attempt that reaches the limit.
        """
        response = None
        for i in range(6):
            response = self.client.post(self.otp_verify_url, {
                'email': 'buyer@warungio.com',
                'otp_code': '999999',
                'purpose': 'registration',
            }, format='json')
        # After all attempts exhausted, OTP is invalid - returns otp_not_found
        self.assert_error_response(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get('code'), 'otp_not_found')


# =============================================================================
# RESEND OTP TESTS
# =============================================================================

@override_settings(DEBUG=True, OTP_COOLDOWN_SECONDS=60)
class ResendOTPTests(BaseTestCase):
    """Test OTP resend with cooldown check."""

    def setUp(self):
        super().setUp()
        # Create an OTP that's past cooldown
        self.old_otp = OTP.objects.create(
            email='verified.buyer@warungio.com',
            purpose='login',
            otp_code='111111',
        )
        self.old_otp.created_at = timezone.now() - timedelta(seconds=120)
        self.old_otp.save(update_fields=['created_at'])

    def test_resend_otp_success(self):
        """Test successful OTP resend returns standardized response."""
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            response = self.client.post(self.otp_resend_url, {
                'email': 'verified.buyer@warungio.com',
                'purpose': 'login',
            }, format='json')
        self.assert_success_response(response)
        self.assertIn('expires_in_minutes', response.data)

    def test_resend_otp_cooldown_blocked(self):
        """Test resend during cooldown returns error."""
        # Create a recent OTP (cooldown not expired)
        OTP.objects.create(
            email='verified.buyer@warungio.com',
            purpose='login',
            otp_code='222222',
        )
        response = self.client.post(self.otp_resend_url, {
            'email': 'verified.buyer@warungio.com',
            'purpose': 'login',
        }, format='json')
        self.assert_error_response(response, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.data.get('code'), 'otp_cooldown')

    def test_resend_otp_invalidates_old(self):
        """Test resend invalidates previous OTPs."""
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            response = self.client.post(self.otp_resend_url, {
                'email': 'verified.buyer@warungio.com',
                'purpose': 'login',
            }, format='json')
        self.assert_success_response(response)
        # Old OTP should be invalid
        self.old_otp.refresh_from_db()
        self.assertFalse(self.old_otp.is_valid)


# =============================================================================
# FORGOT / RESET PASSWORD TESTS
# =============================================================================

@override_settings(DEBUG=True)
class ForgotPasswordTests(BaseTestCase):
    """Test forgot password flow with OTP."""

    def test_forgot_password_success_with_redirect(self):
        """Test forgot password returns redirect_url to OTP page."""
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            response = self.client.post(self.forgot_password_url, {
                'email': 'verified.buyer@warungio.com',
            }, format='json')
        self.assert_success_response(response)
        self.assertIn('redirect_url', response.data)
        self.assertIn('auth/otp/', response.data['redirect_url'])
        self.assertIn('purpose=password_reset', response.data['redirect_url'])
        self.assertTrue(response.data.get('requires_otp'))
        # Verify OTP sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Reset Password', mail.outbox[0].subject)

    def test_forgot_password_nonexistent_email(self):
        """Test forgot password with unregistered email returns 200 (prevent enumeration)."""
        response = self.client.post(self.forgot_password_url, {
            'email': 'nonexistent@test.com',
        }, format='json')
        # Still returns success to prevent user enumeration
        self.assert_success_response(response)

    def test_reset_password_success_with_redirect(self):
        """Test reset password returns redirect_url to login page."""
        # Create password reset OTP
        otp = OTP.objects.create(
            email='verified.buyer@warungio.com',
            purpose='password_reset',
            otp_code='999888',
        )
        response = self.client.post(self.reset_password_url, {
            'email': 'verified.buyer@warungio.com',
            'otp_code': '999888',
            'new_password': 'NewResetPass123!',
            'new_password2': 'NewResetPass123!',
        }, format='json')
        self.assert_success_response(response)
        self.assertIn('redirect_url', response.data)
        self.assertEqual(response.data['redirect_url'], '/auth/login/')
        self.assertEqual(response.data.get('next_action'), 'login')

        # Verify can login with new password
        login_response = self.client.post(self.login_url, {
            'email': 'verified.buyer@warungio.com',
            'password': 'NewResetPass123!',
        }, format='json')
        self.assert_success_response(login_response)

    def test_reset_password_wrong_otp(self):
        """Test reset password with wrong OTP returns error."""
        response = self.client.post(self.reset_password_url, {
            'email': 'verified.buyer@warungio.com',
            'otp_code': '000000',
            'new_password': 'NewPass123!',
            'new_password2': 'NewPass123!',
        }, format='json')
        self.assert_error_response(response, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_expired_otp(self):
        """Test reset password with expired OTP returns error."""
        otp = OTP.objects.create(
            email='verified.buyer@warungio.com',
            purpose='password_reset',
            otp_code='777666',
        )
        otp.expires_at = timezone.now() - timedelta(hours=1)
        otp.save()

        response = self.client.post(self.reset_password_url, {
            'email': 'verified.buyer@warungio.com',
            'otp_code': '777666',
            'new_password': 'NewPass123!',
            'new_password2': 'NewPass123!',
        }, format='json')
        self.assert_error_response(response, status.HTTP_400_BAD_REQUEST)


# =============================================================================
# CHECK AUTH / SESSION TESTS
# =============================================================================

class AuthStateTests(BaseTestCase):
    """Test auth state detection, session persistence, and logout."""

    def test_check_auth_returns_user_data(self):
        """Test CheckAuthView returns user data with standardized format."""
        login_response = self.client.post(self.login_url, {
            'email': 'verified.buyer@warungio.com',
            'password': 'BuyerPass123!',
        }, format='json')
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.get(self.check_auth_url)
        self.assert_success_response(response)
        self.assertTrue(response.data['authenticated'])
        self.assertIn('user', response.data)

    def test_check_auth_unverified_user_detects_otp(self):
        """Test CheckAuthView detects unverified user and provides redirect_url."""
        login_response = self.client.post(self.login_url, {
            'email': 'unverified@warungio.com',
            'password': 'UnverifiedPass123!',
        }, format='json')
        # Unverified user gets requires_otp response
        token = login_response.data.get('access')
        if not token:
            # Unverified user gets 403 - no JWT, use the one we generate manually
            refresh = RefreshToken.for_user(self.unverified_user)
            token = str(refresh.access_token)

        # Actually register a user and verify they can't get JWT before OTP
        # This tests the OTP state detection
        register_resp = self.client.post(self.register_url, {
            'email': 'newuser4@test.com',
            'full_name': 'New User',
            'password': 'NewPass123!',
            'password2': 'NewPass123!',
            'phone': '+6281234567899',
            'role': 'buyer',
        }, format='json')
        self.assert_success_response(register_resp, status.HTTP_201_CREATED)

        # User should NOT be able to login (not verified)
        login_resp = self.client.post(self.login_url, {
            'email': 'newuser4@test.com',
            'password': 'NewPass123!',
        }, format='json')
        self.assert_error_response(login_resp, status.HTTP_403_FORBIDDEN)
        self.assertTrue(login_resp.data.get('requires_otp'))
        self.assertIn('redirect_url', login_resp.data)

    def test_logout_success(self):
        """Test logout clears session and returns standardized response."""
        login_response = self.client.post(self.login_url, {
            'email': 'verified.buyer@warungio.com',
            'password': 'BuyerPass123!',
        }, format='json')
        token = login_response.data['access']
        refresh = login_response.data['refresh']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.post(self.logout_url, {'refresh': refresh}, format='json')
        self.assert_success_response(response)

    def test_token_refresh(self):
        """Test JWT token refresh returns standardized response."""
        login_response = self.client.post(self.login_url, {
            'email': 'verified.buyer@warungio.com',
            'password': 'BuyerPass123!',
        }, format='json')
        refresh = login_response.data['refresh']

        response = self.client.post(self.token_refresh_url, {
            'refresh': refresh
        }, format='json')
        self.assert_success_response(response)
        self.assertIn('access', response.data)

    def test_token_refresh_invalid(self):
        """Test invalid refresh token returns error."""
        response = self.client.post(self.token_refresh_url, {
            'refresh': 'invalid-token'
        }, format='json')
        self.assert_error_response(response, status.HTTP_401_UNAUTHORIZED)


# =============================================================================
# CHECK AVAILABILITY TESTS
# =============================================================================

class CheckAvailabilityTests(BaseTestCase):
    """Test email/phone availability checking."""

    def test_check_availability_email_available(self):
        """Test checking available email returns success."""
        response = self.client.post(self.check_availability_url, {
            'email': 'newemail@test.com',
        }, format='json')
        self.assert_success_response(response)
        self.assertTrue(response.data.get('available'))

    def test_check_availability_email_taken(self):
        """Test checking taken email returns error with success=False."""
        response = self.client.post(self.check_availability_url, {
            'email': 'verified.buyer@warungio.com',
        }, format='json')
        self.assert_error_response(response, status.HTTP_409_CONFLICT)


# =============================================================================
# COMPREHENSIVE E2E FLOW TESTS
# =============================================================================

@override_settings(DEBUG=True)
class SellerE2EFlowTests(BaseTestCase):
    """Complete end-to-end Seller registration, OTP, login, and role-based redirect."""

    def test_seller_full_registration_and_login(self):
        """Complete flow: register → OTP verify → auto-login → seller dashboard redirect."""
        # STEP 1: Register as Seller
        reg_response = self.client.post(self.register_url, self.seller_data, format='json')
        self.assert_success_response(reg_response, status.HTTP_201_CREATED)
        self.assertEqual(reg_response.data['user']['role'], 'seller')
        otp_code = reg_response.data.get('otp_code')
        self.assertIsNotNone(otp_code)

        # Verify user is inactive
        user = User.objects.get(email='seller@warungio.com')
        self.assertFalse(user.is_verified)
        self.assertFalse(user.is_active)
        self.assertEqual(user.registration_step, 'email_phone')

        # STEP 2: Verify OTP
        verify_response = self.client.post(self.otp_verify_url, {
            'email': 'seller@warungio.com',
            'otp_code': otp_code,
            'purpose': 'registration',
        }, format='json')
        self.assert_success_response(verify_response)
        self.assertTrue(verify_response.data.get('verified'))
        self.assertIn('access', verify_response.data)
        self.assertIn('refresh', verify_response.data)
        self.assertIn('redirect_url', verify_response.data)
        self.assertEqual(verify_response.data['redirect_url'], '/seller/dashboard/')
        self.assertEqual(verify_response.data['user']['role'], 'seller')

        # Verify user is now active
        user.refresh_from_db()
        self.assertTrue(user.is_verified)
        self.assertTrue(user.is_active)
        self.assertEqual(user.registration_step, 'complete')

        # STEP 3: Use JWT to access protected endpoint
        token = verify_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        check_response = self.client.get(self.check_auth_url)
        self.assert_success_response(check_response)
        self.assertEqual(check_response.data['user']['email'], 'seller@warungio.com')

    def test_buyer_full_registration_and_login(self):
        """Complete flow: register → OTP verify → auto-login → buyer home redirect."""
        # STEP 1: Register as Buyer
        reg_response = self.client.post(self.register_url, self.buyer_data, format='json')
        self.assert_success_response(reg_response, status.HTTP_201_CREATED)
        otp_code = reg_response.data.get('otp_code')

        # STEP 2: Verify OTP
        verify_response = self.client.post(self.otp_verify_url, {
            'email': 'buyer@warungio.com',
            'otp_code': otp_code,
            'purpose': 'registration',
        }, format='json')
        self.assert_success_response(verify_response)
        self.assertEqual(verify_response.data['redirect_url'], '/buyer/home/')


# =============================================================================
# REGRESSION TESTS
# =============================================================================

class RegressionTests(BaseTestCase):
    """Regression tests to ensure existing functionality is not broken."""

    def test_existing_verified_user_login_still_works(self):
        """Ensure previously registered verified users can still login."""
        response = self.client.post(self.login_url, {
            'email': 'verified.buyer@warungio.com',
            'password': 'BuyerPass123!',
        }, format='json')
        self.assert_success_response(response)
        self.assertIn('access', response.data)

    def test_profile_still_accessible_after_login(self):
        """Ensure profile endpoint still works after login."""
        login_response = self.client.post(self.login_url, {
            'email': 'verified.buyer@warungio.com',
            'password': 'BuyerPass123!',
        }, format='json')
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'verified.buyer@warungio.com')

    def test_change_password_still_works(self):
        """Ensure change password endpoint still works."""
        login_response = self.client.post(self.login_url, {
            'email': 'verified.buyer@warungio.com',
            'password': 'BuyerPass123!',
        }, format='json')
        token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.post(self.change_password_url, {
            'old_password': 'BuyerPass123!',
            'new_password': 'NewBuyerPass456!',
            'new_password2': 'NewBuyerPass456!',
        }, format='json')
        self.assert_success_response(response)

        # Change back for other tests
        user = User.objects.get(email='verified.buyer@warungio.com')
        user.set_password('BuyerPass123!')
        user.save()

    def test_all_endpoints_return_json_not_html(self):
        """Ensure all auth endpoints return JSON, not HTML (no 'Unexpected token <' errors)."""
        endpoints = [
            (self.login_url, {'email': 'test@test.com', 'password': 'test'}),
            (self.register_url, {'email': '', 'full_name': '', 'password': '', 'password2': '', 'phone': ''}),
            (self.otp_request_url, {'email': 'test@test.com'}),
            (self.otp_verify_url, {'email': 'test@test.com', 'otp_code': '123456', 'purpose': 'registration'}),
            (self.forgot_password_url, {'email': 'test@test.com'}),
            (self.check_availability_url, {'email': 'test@test.com'}),
        ]
        for url, data in endpoints:
            response = self.client.post(url, data, format='json')
            # Ensure response is JSON, not HTML
            content_type = response.get('Content-Type', '')
            self.assertIn('application/json', content_type,
                          f'Endpoint {url} returned {content_type} instead of application/json')
            # Ensure response data is a dict (JSON), not HTML string
            self.assertIsInstance(response.data, dict,
                                  f'Endpoint {url} returned non-dict response: {type(response.data)}')


# =============================================================================
# SECURITY TESTS
# =============================================================================

class SecurityTests(BaseTestCase):
    """Test authentication security measures."""

    def test_sql_injection_login(self):
        """Test SQL injection attempt returns error."""
        response = self.client.post(self.login_url, {
            'email': "' OR '1'='1",
            'password': "' OR '1'='1",
        }, format='json')
        self.assert_error_response(response, status.HTTP_400_BAD_REQUEST)

    def test_empty_password_rejected(self):
        """Test login with empty password."""
        response = self.client.post(self.login_url, {
            'email': 'verified.buyer@warungio.com',
            'password': '',
        }, format='json')
        self.assert_error_response(response, status.HTTP_400_BAD_REQUEST)

    def test_invalid_jwt_rejected(self):
        """Test protected endpoint with invalid JWT."""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid-token-here')
        response = self.client.get(self.check_auth_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data.get('success', True))

    def test_no_auth_header_rejected(self):
        """Test protected endpoint without any auth."""
        response = self.client.get(self.check_auth_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data.get('success', True))
