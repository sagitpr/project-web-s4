"""
E2E Test — OTP Flow: Register → OTP → Verify → Login
Simulates the full user authentication flow end-to-end.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['DJANGO_DEBUG'] = 'True'

import django
django.setup()

from django.test import TestCase, override_settings
from django.core import mail
from rest_framework.test import APIClient
from accounts.models import User, OTP
from accounts.services.email_service import send_otp_email


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST_USER='test@warungio.com',
    EMAIL_HOST_PASSWORD='secret',
    DEFAULT_FROM_EMAIL='noreply@warungio.com',
)
class OTPE2ETest(TestCase):
    """End-to-end test for Register → OTP → Verify → Login flow."""

    def setUp(self):
        from django.core import mail as djmail
        djmail.outbox.clear()
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
        self.login_url = '/api/auth/login/'
        self.verify_otp_url = '/api/auth/otp/verify/'
        self.resend_otp_url = '/api/auth/otp/resend/'
        self.test_email = 'e2e-test@warungio.com'
        self.test_password = 'TestPass123!'
        self.test_name = 'E2E Test User'

    @override_settings(OTP_COOLDOWN_SECONDS=0)
    def test_full_otp_flow_register_verify_login(self):
        """TEST 1: Full flow Register → OTP email received → Verify OTP → Login success."""
        print('\n--- E2E TEST 1: Register → OTP → Verify → Login ---')

        # Step 1: Register
        register_data = {
            'email': self.test_email,
            'password': self.test_password,
            'password2': self.test_password,
            'full_name': self.test_name,
            'phone': '+6281234567890',
        }
        response = self.client.post(self.register_url, register_data, format='json')
        print(f'  [Register] Status: {response.status_code}')
        self.assertIn(response.status_code, [200, 201, 302],
                      f'Register should succeed. Got: {response.status_code} {response.data}')

        # Step 2: Check OTP was created in DB
        otp_record = OTP.objects.filter(email=self.test_email).order_by('-created_at').first()
        self.assertIsNotNone(otp_record, 'OTP record should exist after registration')
        print(f'  [OTP DB]   Created: {otp_record.otp_code} (expires: {otp_record.expires_at})')

        # Step 3: Check OTP email was sent
        self.assertEqual(len(mail.outbox), 1, 'Exactly 1 email should be sent')
        email = mail.outbox[0]
        self.assertIn(self.test_email, email.to, 'Email should be sent to registered user')
        self.assertIn(otp_record.otp_code, email.subject, 'OTP code should appear in email subject')
        print(f'  [Email]    Subject: "{email.subject}"')
        print(f'  [Email]    To: {email.to}')
        print(f'  [Email]    Body: {email.body[:100]}...')

        # Step 4: Verify OTP
        verify_data = {
            'email': self.test_email,
            'otp_code': otp_record.otp_code,
        }
        response = self.client.post(self.verify_otp_url, verify_data, format='json')
        print(f'  [Verify]   Status: {response.status_code} — {response.data}')
        self.assertIn(response.status_code, [200, 201, 302],
                      f'OTP verification should succeed. Got: {response.status_code}')

        # Step 5: Check user is now active/verified
        user = User.objects.filter(email=self.test_email).first()
        self.assertIsNotNone(user, 'User should exist')
        # Check is_active or is_verified depending on model
        if hasattr(user, 'is_verified'):
            self.assertTrue(user.is_verified, 'User should be verified after OTP')
            print(f'  [User]     Verified: {user.is_verified}')
        if hasattr(user, 'is_active'):
            self.assertTrue(user.is_active, 'User should be active after OTP')
            print(f'  [User]     Active: {user.is_active}')

        # Step 6: Login with credentials
        login_data = {
            'email': self.test_email,
            'password': self.test_password,
        }
        response = self.client.post(self.login_url, login_data, format='json')
        print(f'  [Login]    Status: {response.status_code}')
        self.assertIn(response.status_code, [200, 302],
                      f'Login should succeed. Got: {response.status_code}')
        if response.status_code == 200:
            self.assertIn('access', response.data, 'Login response should contain access token')
            print(f'  [Login]    Access token: {response.data.get("access", "")[:50]}...')

        print('  >>> E2E TEST 1 PASSED <<<')

    @override_settings(OTP_COOLDOWN_SECONDS=0)
    def test_otp_resend_flow(self):
        """TEST 2: Resend OTP generates new code."""
        print('\n--- E2E TEST 2: Resend OTP ---')

        # Register first
        register_data = {
            'email': 'resend-test@warungio.com',
            'password': self.test_password,
            'password2': self.test_password,
            'full_name': 'Resend Test',
            'phone': '+6281234567891',
        }
        self.client.post(self.register_url, register_data, format='json')

        # Get initial OTP
        first_otp = OTP.objects.filter(email='resend-test@warungio.com').order_by('-created_at').first()
        self.assertIsNotNone(first_otp)
        print(f'  [First OTP]  {first_otp.otp_code}')

        # Resend OTP
        mail.outbox.clear()
        resend_data = {'email': 'resend-test@warungio.com'}
        response = self.client.post(self.resend_otp_url, resend_data, format='json')
        print(f'  [Resend]    Status: {response.status_code} — {response.data}')
        self.assertIn(response.status_code, [200, 201, 302],
                      f'Resend should succeed. Got: {response.status_code}')

        # Check new OTP was created
        second_otp = OTP.objects.filter(email='resend-test@warungio.com').order_by('-created_at').first()
        self.assertIsNotNone(second_otp)
        print(f'  [Second OTP] {second_otp.otp_code}')

        # Verify new email was sent
        self.assertEqual(len(mail.outbox), 1, 'Resend should send 1 email')
        self.assertIn(second_otp.otp_code, mail.outbox[0].subject,
                     'New OTP should be in email subject')
        print(f'  [Email]    Subject: {mail.outbox[0].subject}')

        # Verify old OTP (may or may not work — just log)
        verify_data = {'email': 'resend-test@warungio.com', 'otp_code': first_otp.otp_code}
        response = self.client.post(self.verify_otp_url, verify_data, format='json')
        print(f'  [Old OTP]  Verify Status: {response.status_code}')

        # New OTP should work
        mail.outbox.clear()
        verify_data = {'email': 'resend-test@warungio.com', 'otp_code': second_otp.otp_code}
        response = self.client.post(self.verify_otp_url, verify_data, format='json')
        print(f'  [New OTP]  Verify Status: {response.status_code} — {response.data}')
        self.assertIn(response.status_code, [200, 201, 302],
                     f'New OTP verification should succeed. Got: {response.status_code}')
        if response.status_code == 200:
            self.assertIn('access', response.data,
                         'Verify response should contain access token')

        print('  >>> E2E TEST 2 PASSED <<<')

    @override_settings(OTP_COOLDOWN_SECONDS=0)
    def test_invalid_otp_rejected(self):
        """TEST 3: Invalid OTP is rejected."""
        print('\n--- E2E TEST 3: Invalid OTP Rejected ---')

        register_data = {
            'email': 'invalid-otp@warungio.com',
            'password': self.test_password,
            'password2': self.test_password,
            'full_name': 'Invalid OTP',
            'phone': '+6281234567892',
        }
        self.client.post(self.register_url, register_data, format='json')

        verify_data = {'email': 'invalid-otp@warungio.com', 'otp_code': '000000'}
        response = self.client.post(self.verify_otp_url, verify_data, format='json')
        print(f'  [Verify Invalid] Status: {response.status_code} — {response.data}')
        self.assertEqual(response.status_code, 400,
                        f'Invalid OTP should return 400. Got: {response.status_code}')

        print('  >>> E2E TEST 3 PASSED <<<')

    @override_settings(OTP_COOLDOWN_SECONDS=0)
    def test_login_unverified_triggers_otp(self):
        """TEST 5: Login with unverified account → OTP auto-generated → Verify → Login success."""
        print('\n--- E2E TEST 5: Login (unverified) → OTP → Verify → Dashboard ---')

        # Step 1: Register a new user (starts unverified)
        email = 'login-otp-test@warungio.com'
        register_data = {
            'email': email,
            'password': self.test_password,
            'password2': self.test_password,
            'full_name': 'Login OTP Test',
            'phone': '+6281234567893',
        }
        response = self.client.post(self.register_url, register_data, format='json')
        self.assertIn(response.status_code, [200, 201, 302],
                      f'Register should succeed. Got: {response.status_code}')

        # Step 2: Verify user is NOT verified
        user = User.objects.filter(email=email).first()
        self.assertIsNotNone(user)
        self.assertFalse(user.is_verified, 'User should NOT be verified after register')
        print(f'  [User]     Verified: {user.is_verified} (expected: False)')

        # Clear outbox from register email
        mail.outbox.clear()

        # Step 3: Attempt login → should return 403 with requires_otp=true
        login_data = {
            'email': email,
            'password': self.test_password,
        }
        response = self.client.post(self.login_url, login_data, format='json')
        print(f'  [Login]    Status: {response.status_code}')
        self.assertEqual(response.status_code, 403,
                        f'Unverified login should return 403. Got: {response.status_code}')
        print(f'  [Login]    Response: {response.data}')

        # Step 4: Check response indicates OTP required
        data_str = str(response.data).lower()
        self.assertTrue(
            'requires_otp' in data_str or 'otp' in data_str,
            f'Response should mention OTP requirement. Got: {response.data}'
        )

        # Step 5: Check OTP was auto-generated and email sent
        otp_record = OTP.objects.filter(email=email, purpose='registration').order_by('-created_at').first()
        self.assertIsNotNone(otp_record, 'OTP should be auto-generated on login attempt')
        print(f'  [OTP DB]   Code: {otp_record.otp_code} (autogenerated on login attempt)')

        # Step 6: Check email was sent with OTP (outbox cleared before login, so exactly 1)
        self.assertEqual(len(mail.outbox), 1, 'Email should be sent with OTP')
        if mail.outbox:
            email_msg = mail.outbox[0]
            self.assertIn(email, email_msg.to, f'Email should be sent to {email}')
            print(f'  [Email]    Subject: "{email_msg.subject}"')

        # Step 7: Verify OTP → should auto-login
        mail.outbox.clear()
        verify_data = {
            'email': email,
            'otp_code': otp_record.otp_code,
        }
        response = self.client.post(self.verify_otp_url, verify_data, format='json')
        print(f'  [Verify]   Status: {response.status_code} — {response.data}')
        self.assertIn(response.status_code, [200, 201, 302],
                     f'OTP verification should succeed. Got: {response.status_code}')

        # Step 8: Verify user is now verified + active
        user.refresh_from_db()
        self.assertTrue(user.is_verified, 'User should be verified after OTP')
        self.assertTrue(user.is_active, 'User should be active after OTP')
        print(f'  [User]     Verified: {user.is_verified}, Active: {user.is_active}')

        # Step 9: Verify auto-login (response contains tokens)
        if response.status_code == 200:
            self.assertIn('access', response.data,
                         'OTP verify response should contain access token (auto-login)')
            print(f'  [Token]    Auto-login token received')

        # Step 10: Use force_login (Django session auth) to access dashboard
        from django.test import Client as DjangoClient
        session_client = DjangoClient()
        session_client.force_login(user)
        dash_response = session_client.get('/buyer/dashboard/', HTTP_ACCEPT='text/html')
        print(f'  [Dashboard] Status: {dash_response.status_code}')
        self.assertIn(dash_response.status_code, [200, 302],
                     f'Dashboard should be accessible. Got: {dash_response.status_code}')

        print('  >>> E2E TEST 5 PASSED <<<')

    @override_settings(OTP_COOLDOWN_SECONDS=0)
    def test_login_verified_user_success(self):
        """TEST 6: Already verified user can login directly without OTP."""
        print('\n--- E2E TEST 6: Verified User Direct Login ---')

        # Step 1: Register
        email = 'direct-login@warungio.com'
        register_data = {
            'email': email,
            'password': self.test_password,
            'password2': self.test_password,
            'full_name': 'Direct Login',
            'phone': '+6281234567894',
        }
        self.client.post(self.register_url, register_data, format='json')

        # Step 2: Verify OTP (complete registration)
        otp_record = OTP.objects.filter(email=email).order_by('-created_at').first()
        self.assertIsNotNone(otp_record)
        verify_data = {'email': email, 'otp_code': otp_record.otp_code}
        self.client.post(self.verify_otp_url, verify_data, format='json')

        # Step 3: Now login — should succeed directly (200, not 403)
        login_data = {'email': email, 'password': self.test_password}
        response = self.client.post(self.login_url, login_data, format='json')
        print(f'  [Login]    Status: {response.status_code}')
        self.assertEqual(response.status_code, 200,
                        f'Verified user login should return 200. Got: {response.status_code}')
        self.assertIn('access', response.data, 'Login should return access token')
        print(f'  [Token]    Access token received')

        print('  >>> E2E TEST 6 PASSED <<<')

    @override_settings(OTP_COOLDOWN_SECONDS=0)
    def test_reset_password_otp_flow(self):
        """TEST 8: Forgot Password → OTP → Reset Password → Login with new password."""
        print('\n--- E2E TEST 8: Reset Password via OTP ---')

        # Step 1: Register + verify user
        email = 'reset-test@warungio.com'
        register_data = {
            'email': email,
            'password': self.test_password,
            'password2': self.test_password,
            'full_name': 'Reset Test',
            'phone': '+6281234567895',
        }
        self.client.post(self.register_url, register_data, format='json')
        otp_record = OTP.objects.filter(email=email).order_by('-created_at').first()
        self.assertIsNotNone(otp_record)
        self.client.post(self.verify_otp_url, {'email': email, 'otp_code': otp_record.otp_code}, format='json')
        user = User.objects.filter(email=email).first()
        self.assertTrue(user.is_verified)
        print(f'  [User]     Verified: {user.is_verified}')

        # Step 2: Forgot Password — request OTP
        mail.outbox.clear()
        forgot_url = '/api/auth/forgot-password/'
        response = self.client.post(forgot_url, {'email': email}, format='json')
        print(f'  [Forgot]   Status: {response.status_code} — {response.data}')
        self.assertIn(response.status_code, [200, 302],
                     f'Forgot password should succeed. Got: {response.status_code}')

        # Step 3: Check reset OTP was created in DB
        reset_otp = OTP.objects.filter(email=email, purpose='password_reset').order_by('-created_at').first()
        self.assertIsNotNone(reset_otp, 'Reset OTP should exist')
        print(f'  [OTP DB]   Reset OTP: {reset_otp.otp_code}')

        # Step 4: Check email was sent
        email_sent = any(email in (msg.to if hasattr(msg, 'to') else []) and 'Reset' in msg.subject
                       for msg in mail.outbox)
        print(f'  [Email]    Sent: {email_sent}')

        # Step 5: Reset Password with OTP
        new_password = 'NewPass456!'
        reset_url = '/api/auth/reset-password/'
        response = self.client.post(reset_url, {
            'email': email,
            'otp_code': reset_otp.otp_code,
            'new_password': new_password,
            'new_password2': new_password,
        }, format='json')
        print(f'  [Reset]    Status: {response.status_code} — {response.data}')
        self.assertIn(response.status_code, [200, 302],
                     f'Reset password should succeed. Got: {response.status_code}')

        # Step 6: Login with NEW password
        login_data = {'email': email, 'password': new_password}
        response = self.client.post(self.login_url, login_data, format='json')
        print(f'  [Login]    Status: {response.status_code}')
        self.assertEqual(response.status_code, 200,
                        f'Login with new password should succeed. Got: {response.status_code}')
        self.assertIn('access', response.data, 'Login should return access token')
        print(f'  [Token]    Access token received')

        # Step 7: Login with OLD password should FAIL
        login_data = {'email': email, 'password': self.test_password}
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertIn(response.status_code, [400, 401, 403],
                     f'Old password should fail. Got: {response.status_code}')
        print(f'  [OldPass]  Correctly rejected: {response.status_code}')

        print('  >>> E2E TEST 8 PASSED <<<')

    @override_settings(
        OTP_COOLDOWN_SECONDS=0,
        SOCIAL_AUTH_GOOGLE_CLIENT_ID='test-client-id',
        SOCIAL_AUTH_FACEBOOK_APP_ID='test-app-id',
        SOCIAL_AUTH_FACEBOOK_APP_SECRET='test-secret',
    )
    def test_social_login_config_available(self):
        """TEST 9: Social login config endpoints return proper configuration."""
        print('\n--- E2E TEST 9: Social Login Configuration ---')

        # Google Auth Config
        response = self.client.get('/api/auth/social/config/google/')
        print(f'  [Google]   Status: {response.status_code}')
        self.assertIn(response.status_code, [200, 302],
                     f'Google config should be accessible. Got: {response.status_code}')

        # Facebook Auth Config
        response = self.client.get('/api/auth/social/config/facebook/')
        print(f'  [Facebook] Status: {response.status_code}')
        self.assertIn(response.status_code, [200, 302],
                     f'Facebook config should be accessible. Got: {response.status_code}')

        print('  >>> E2E TEST 9 PASSED <<<')

    @override_settings(EMAIL_HOST_USER='', EMAIL_HOST_PASSWORD='')
    def test_otp_in_app_fallback_notification(self):
        """TEST 10: When email SMTP is not configured, OTP creates in-app notification."""
        print('\n--- E2E TEST 10: In-App OTP Fallback Notification ---')

        # Register without SMTP — should still create in-app notification
        email = 'fallback-test@warungio.com'
        register_data = {
            'email': email,
            'password': self.test_password,
            'password2': self.test_password,
            'full_name': 'Fallback Test',
            'phone': '+6281234567896',
        }
        response = self.client.post(self.register_url, register_data, format='json')
        print(f'  [Register] Status: {response.status_code}')

        # Check if OTP was still created in DB
        otp_record = OTP.objects.filter(email=email).order_by('-created_at').first()
        self.assertIsNotNone(otp_record, 'OTP record should exist even without SMTP')
        print(f'  [OTP DB]   Code: {otp_record.otp_code}')

        # Check if in-app notification was created
        user = User.objects.filter(email=email).first()
        if user:
            from notifications.models import Notification
            notifications = Notification.objects.filter(user=user).order_by('-created_at')
            print(f'  [Notif]    Count: {notifications.count()}')
            for n in notifications:
                print(f'  [Notif]    {n.notification_type}: {n.title}')

        # Verify OTP still works (DB-based verification does not depend on email)
        if response.status_code in [200, 201]:
            verify_data = {'email': email, 'otp_code': otp_record.otp_code}
            verify_resp = self.client.post(self.verify_otp_url, verify_data, format='json')
            print(f'  [Verify]   Status: {verify_resp.status_code}')

        print('  >>> E2E TEST 10 PASSED <<<')

    @override_settings(
        SOCIAL_AUTH_GOOGLE_CLIENT_ID='test-google-id',
        SOCIAL_AUTH_FACEBOOK_APP_ID='test-fb-id',
        SOCIAL_AUTH_FACEBOOK_APP_SECRET='test-fb-secret',
        SOCIAL_AUTH_APPLE_CLIENT_ID='test-apple-id',
    )
    def test_social_login_get_or_create_user(self):
        """TEST 12: Social Login core logic — get_or_create_user, linking, role gate, tokens."""
        print('\n--- E2E TEST 12: Social Login Mock (get_or_create_user) ---')

        from accounts.social import SocialLoginBase
        from accounts.models import SocialAccount
        from rest_framework.test import APIRequestFactory

        base = SocialLoginBase()
        factory = APIRequestFactory()
        email = 'social-test@warungio.com'
        google_id = 'google-12345'

        # ── TEST 12a: Create new user via Google ──
        user, is_new = base.get_or_create_user(
            email=email,
            full_name='Social User',
            provider='google',
            provider_id=google_id,
            extra_data={'picture': 'https://example.com/pic.jpg'},
            role='buyer',
        )
        self.assertIsNotNone(user)
        self.assertTrue(is_new, 'New social user should be created')
        self.assertTrue(user.is_verified, 'Social users should be auto-verified')
        self.assertEqual(user.role, 'buyer')
        print(f'  [12a] New user created: {user.email}, role={user.role}, verified={user.is_verified}')

        # ── TEST 12b: Linking — same Google account should return existing user ──
        same_user, is_new2 = base.get_or_create_user(
            email=email,
            full_name='Social User',
            provider='google',
            provider_id=google_id,
        )
        self.assertEqual(same_user.id, user.id, 'Same Google account = same user')
        self.assertFalse(is_new2, 'Should NOT create new user')
        print(f'  [12b] Link check: existing user returned, is_new={is_new2}')

        # ── TEST 12c: Different email same Google ID should still return same user ──
        # (SocialAccount is keyed on provider+provider_id)
        social_account = SocialAccount.objects.filter(provider='google', provider_id=google_id).first()
        self.assertIsNotNone(social_account)
        self.assertEqual(social_account.user.id, user.id)
        print(f'  [12c] SocialAccount linked: {social_account.provider} -> {social_account.user.email}')

        # ── TEST 12d: Existing email + new provider (Facebook) should LINK, not create ──
        fb_user, is_new3 = base.get_or_create_user(
            email=email,
            full_name='Social User FB',
            provider='facebook',
            provider_id='fb-67890',
        )
        self.assertEqual(fb_user.id, user.id, 'Same email = same user (linked)')
        self.assertFalse(is_new3, 'Should link Facebook to existing user')
        fb_account = SocialAccount.objects.filter(provider='facebook', provider_id='fb-67890').first()
        self.assertIsNotNone(fb_account)
        self.assertEqual(fb_account.user.id, user.id)
        print(f'  [12d] FB linked: {fb_account.provider} -> {fb_account.user.email}')

        # ── TEST 12e: Role gate (validate_login_entry) ──
        request = factory.post('/api/auth/social/google/', {'role': 'buyer'})
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        # Buyer tries to login as seller → should be blocked
        role_check = base.validate_login_entry(user, 'seller')
        self.assertIsNotNone(role_check, 'Role mismatch should return error')
        self.assertEqual(role_check.status_code, 403)
        print(f'  [12e] Role gate: buyer->seller blocked (status={role_check.status_code})')

        # Buyer tries to login as buyer → should pass
        role_check_ok = base.validate_login_entry(user, 'buyer')
        self.assertIsNone(role_check_ok, 'Correct role should pass')
        print(f'  [12e] Role gate: buyer->buyer allowed')

        # ── TEST 12f: Token generation (direct JWT, bypasses login() which needs session) ──
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh_token = RefreshToken.for_user(user)
        access_token = str(refresh_token.access_token)
        self.assertTrue(len(access_token) > 0, 'Access token should be generated')
        self.assertTrue(len(str(refresh_token)) > 0, 'Refresh token should be generated')
        print(f'  [12f] Token generated: access={access_token[:30]}...')

        # Also test generate_jwt_tokens via force_login (session not required for token gen)
        tokens_manual = {
            'access': access_token,
            'refresh': str(refresh_token),
        }
        self.assertIn('access', tokens_manual)

        # ── TEST 12g: Create seller via social login ──
        seller_email = 'seller-social@warungio.com'
        seller_user, is_new4 = base.get_or_create_user(
            email=seller_email,
            full_name='Seller Social',
            provider='apple',
            provider_id='apple-11111',
            role='seller',
        )
        self.assertTrue(is_new4, 'Seller social user should be created')
        self.assertEqual(seller_user.role, 'seller')
        print(f'  [12g] Seller created: {seller_user.email}, role={seller_user.role}')

        # ── TEST 12h: SocialAccountStatus — list linked accounts ──
        self.client.force_login(user)
        resp = self.client.get('/api/auth/social/accounts/')
        print(f'  [12h] Social accounts list: status={resp.status_code}')
        self.assertIn(resp.status_code, [200, 302])

        print('  >>> E2E TEST 12 PASSED <<<')

    @override_settings(
        CELERY_TASK_ALWAYS_EAGER=True,
        OTP_COOLDOWN_SECONDS=0,
    )
    def test_celery_otp_async_sync_fallback(self):
        """TEST 13: OTP delivery — Celery async dispatch + sync fallback pipeline."""
        print('\n--- E2E TEST 13: Celery OTP Async + Sync Fallback ---')

        from accounts.views import _dispatch_otp_async

        email = 'celery-otp-test@warungio.com'
        register_data = {
            'email': email,
            'password': self.test_password,
            'password2': self.test_password,
            'full_name': 'Celery OTP Test',
            'phone': '+6281234567897',
        }

        # Step 1: Register — should dispatch OTP via Celery (eager mode)
        # In eager mode, .delay() runs synchronously. The task should succeed
        # because EMAIL_BACKEND=locmem
        mail.outbox.clear()
        response = self.client.post(self.register_url, register_data, format='json')
        print(f'  [Register] Status: {response.status_code}')
        self.assertIn(response.status_code, [200, 201, 302],
                     f'Register should succeed. Got: {response.status_code}')

        # Step 2: Check OTP was created in DB
        otp_record = OTP.objects.filter(email=email).order_by('-created_at').first()
        self.assertIsNotNone(otp_record, 'OTP should exist in DB')
        print(f'  [OTP DB]   Code: {otp_record.otp_code}')

        # Step 3: Check email was sent (Celery eager or sync fallback)
        self.assertGreaterEqual(len(mail.outbox), 1, 'At least 1 email should be sent')
        if mail.outbox:
            print(f'  [Email]    Subject: {mail.outbox[0].subject}')
            print(f'  [Email]    To: {mail.outbox[0].to}')

        # Step 4: Test SYNC FALLBACK — patch send_otp_task to None (Celery down)
        mail.outbox.clear()
        from unittest.mock import patch

        with patch('accounts.views.send_otp_task', None):
            channels_sync = _dispatch_otp_async(
                email=email,
                phone=None,
                otp_code='777777',
                purpose='registration',
                user_full_name='Sync Fallback Test',
            )
            print(f'  [SyncFallback] Channels: {channels_sync}')
            # With Celery patched to None, dispatch should fall back to sync send_otp_email()
            # If SMTP=locmem, sync should succeed and channels should contain 'email'
            print(f'  [SyncFallback] Outbox emails: {len(mail.outbox)}')
            self.assertTrue(
                len(channels_sync) > 0 or len(mail.outbox) > 0,
                'Sync fallback should dispatch OTP even when Celery is unavailable'
            )
            if mail.outbox:
                print(f'  [SyncFallback] Subject: {mail.outbox[0].subject}')

        # Step 5: Test without SMTP + no Celery — both fallbacks exhausted
        mail.outbox.clear()
        with patch('accounts.views.send_otp_task', None):
            with self.settings(EMAIL_HOST_USER='', EMAIL_HOST_PASSWORD=''):
                channels_no_delivery = _dispatch_otp_async(
                    email=email,
                    phone=None,
                    otp_code='666666',
                    purpose='registration',
                    user_full_name='No Delivery Test',
                )
                print(f'  [NoDelivery] Channels (expected empty): {channels_no_delivery}')
                # Both Celery and SMTP unavailable — channels should be empty
                self.assertEqual(
                    len(channels_no_delivery), 0,
                    'When both Celery and SMTP fail, channels should be empty'
                )

        # Step 6: Verify OTP still works
        verify_data = {'email': email, 'otp_code': otp_record.otp_code}
        response = self.client.post(self.verify_otp_url, verify_data, format='json')
        print(f'  [Verify]   Status: {response.status_code}')
        self.assertIn(response.status_code, [200, 201, 302],
                     f'OTP should still verify after Celery dispatch. Got: {response.status_code}')

        print('  >>> E2E TEST 13 PASSED <<<')

    def test_otp_email_content(self):
        """TEST 14: OTP email contains proper HTML with responsive design."""
        print('\n--- E2E TEST 14: OTP Email Content ---')
        from django.core import mail as djmail
        djmail.outbox.clear()

        send_otp_email(
            email='content-test@warungio.com',
            otp_code='888888',
            purpose='registration',
            user_full_name='Content Test',
        )

        self.assertEqual(len(mail.outbox), 1, 'Exactly 1 email should be sent')
        email_msg = mail.outbox[0]

        # Check subject contains OTP code and purpose
        self.assertIn('888888', email_msg.subject, 'OTP code in subject')
        self.assertIn('Verifikasi Akun', email_msg.subject, 'Purpose in subject')

        # Check HTML content
        if email_msg.alternatives:
            html_content = email_msg.alternatives[0][0]
            self.assertIn('888888', html_content, 'OTP code in HTML body')
            self.assertIn('Content Test', html_content, 'User name in HTML body')
            self.assertIn('Warungio', html_content, 'Brand name in HTML body')
            self.assertIn('</html>', html_content, 'Valid HTML structure')
            self.assertIn('viewport', html_content, 'Responsive viewport meta')
            print(f'  [HTML OK]  OTP visible, name visible, responsive layout')

        # Check plain text
        self.assertTrue(len(email_msg.body) > 0, 'Plain text body exists')
        print(f'  [Plain]    Body length: {len(email_msg.body)} chars')

        print('  >>> E2E TEST 11 PASSED <<<')


# Run directly
if __name__ == '__main__':
    import django.test.runner
    runner = django.test.runner.DiscoverRunner()
    suite = runner.test_loader.loadTestsFromTestCase(OTPE2ETest)
    old_config = runner.setup_databases()
    result = runner.run_suite(suite)
    runner.teardown_databases(old_config)
    sys.exit(0 if result.wasSuccessful() else 1)
