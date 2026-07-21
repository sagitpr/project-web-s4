"""
E2E Email Pipeline Tests for Warungio.

Tests the complete email delivery pipeline end-to-end:
1. Registration flow → OTP email → email content verification
2. NotificationService → email delivery pipeline
3. Template rendering pipeline (HTML + plain text)
4. Email dispatch through all channels
5. Celery async dispatch fallback

These tests use the locmem EmailBackend to capture sent emails
without requiring a real SMTP server.
"""

import uuid
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.conf import settings
from django.core import mail
from django.utils import timezone
from rest_framework import status

from accounts.models import User, OTP
from accounts.services.email_service import send_otp_email
from accounts.services.notification_service import notification_service
from accounts.tasks import send_otp_task

# =============================================================================
# E2E: REGISTRATION → OTP EMAIL PIPELINE
# =============================================================================

@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST_USER='noreply@warungio.com',
    EMAIL_HOST_PASSWORD='secret',
    DEFAULT_FROM_EMAIL='noreply@warungio.com',
    DEBUG=True,
)
class RegistrationToEmailE2ETests(TestCase):
    """E2E tests: Register a user → OTP generated → Email sent → Email verified."""

    def setUp(self):
        """Create a test user."""
        self.email = 'seller-e2e@warungio.com'
        self.user = User.objects.create_user(
            username='seller-e2e',
            email=self.email,
            full_name='Seller E2E',
            phone='081234567891',
            password='TestPass123!',
            role='seller',
            is_active=False,
            is_verified=False,
        )

    def test_e2e_registration_otp_email_sent(self):
        """E2E: Registration → OTP email sent successfully."""
        # 1. Create OTP for registration
        otp = OTP.objects.create(
            user=self.user,
            email=self.email,
            purpose='registration',
            ip_address='127.0.0.1',
        )

        # 2. Send OTP email (this is what the registration flow does)
        result = send_otp_email(
            email=self.email,
            otp_code=otp.otp_code,
            purpose='registration',
            user_full_name=self.user.full_name,
        )

        # 3. Verify email was sent
        self.assertTrue(result['success'], 'OTP email should be sent successfully')
        self.assertEqual(len(mail.outbox), 1, 'Exactly one email should be sent')
        email_msg = mail.outbox[0]

        # 4. Verify email structure
        self.assertEqual(email_msg.to, [self.email])
        self.assertEqual(email_msg.from_email, 'noreply@warungio.com')
        self.assertIn('Verifikasi Akun', email_msg.subject)
        self.assertIn(otp.otp_code, email_msg.subject)

        # 5. Verify multipart content (HTML + plain text)
        self.assertTrue(len(email_msg.body) > 0, 'Plain text body should exist')
        self.assertTrue(len(email_msg.alternatives) > 0, 'HTML alternatives should exist')

        # 6. Verify HTML content
        html_content = None
        for content, mime_type in email_msg.alternatives:
            if mime_type == 'text/html':
                html_content = content
                break
        self.assertIsNotNone(html_content, 'HTML content should exist')
        self.assertIn('Warungio', html_content)
        self.assertIn(otp.otp_code, html_content)
        self.assertIn(self.user.full_name, html_content)
        self.assertIn('</html>', html_content)

    def test_e2e_registration_otp_email_without_name(self):
        """E2E: Registration OTP email falls back to email prefix when no name."""
        otp = OTP.objects.create(
            user=self.user,
            email=self.email,
            purpose='registration',
            ip_address='127.0.0.1',
        )

        result = send_otp_email(
            email=self.email,
            otp_code=otp.otp_code,
            purpose='registration',
            # No user_full_name provided
        )

        self.assertTrue(result['success'])
        html_content = None
        for content, mime_type in mail.outbox[0].alternatives:
            if mime_type == 'text/html':
                html_content = content
                break
        # Should use email prefix as fallback
        self.assertIn('seller-e2e', html_content)

    def test_e2e_multiple_otps_only_latest_email_sent(self):
        """E2E: When multiple OTPs exist, only latest is used for email."""
        # Create first OTP
        OTP.objects.create(
            user=self.user,
            email=self.email,
            purpose='registration',
            ip_address='127.0.0.1',
        )

        # Create second OTP (simulating resend)
        otp2 = OTP.objects.create(
            user=self.user,
            email=self.email,
            purpose='registration',
            ip_address='127.0.0.1',
        )

        # Send email with the latest OTP
        result = send_otp_email(
            email=self.email,
            otp_code=otp2.otp_code,
            purpose='registration',
            user_full_name=self.user.full_name,
        )

        self.assertTrue(result['success'])
        self.assertIn(otp2.otp_code, mail.outbox[0].subject)


# =============================================================================
# E2E: NOTIFICATION SERVICE → EMAIL PIPELINE
# =============================================================================

@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST_USER='noreply@warungio.com',
    EMAIL_HOST_PASSWORD='secret',
    DEFAULT_FROM_EMAIL='noreply@warungio.com',
    DEBUG=False,
)
class NotificationServiceEmailE2ETests(TestCase):
    """E2E tests: NotificationService → Email dispatch → Email received."""

    def test_e2e_notification_service_sends_otp_email(self):
        """E2E: NotificationService.send_otp delivers email via SMTP pipeline."""
        result = notification_service.send_otp(
            identifier='buyer-e2e@warungio.com',
            otp_code='123456',
            purpose='registration',
            user_full_name='Buyer E2E',
        )

        self.assertTrue(result['success'], 'NotificationService should send OTP email')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['buyer-e2e@warungio.com'])
        self.assertIn('123456', mail.outbox[0].subject)

    def test_e2e_notification_service_multiple_recipients_independent(self):
        """E2E: Each notification_service.send_otp call is independent."""
        # Send to first recipient
        result1 = notification_service.send_otp(
            identifier='buyer1@warungio.com',
            otp_code='111111',
            purpose='registration',
        )
        self.assertTrue(result1['success'])

        # Send to second recipient
        result2 = notification_service.send_otp(
            identifier='buyer2@warungio.com',
            otp_code='222222',
            purpose='login',
        )
        self.assertTrue(result2['success'])

        # Verify both emails were sent independently
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to, ['buyer1@warungio.com'])
        self.assertIn('111111', mail.outbox[0].subject)
        self.assertEqual(mail.outbox[1].to, ['buyer2@warungio.com'])
        self.assertIn('222222', mail.outbox[1].subject)

    def test_e2e_notification_service_returns_structured_response(self):
        """E2E: NotificationService returns structured success response."""
        result = notification_service.send_otp(
            identifier='test@warungio.com',
            otp_code='999999',
            purpose='password_reset',
        )

        # Verify the structured response contains all required fields
        self.assertIn('success', result, 'Response should contain success field')
        self.assertIn('message', result, 'Response should contain message field')
        self.assertTrue(result['success'], 'OTP delivery should succeed')
        self.assertTrue(len(result.get('message', '')) > 0, 'Message should not be empty')
        # 'channel' is returned when available; 'error' is returned on failure
        self.assertTrue(
            'channel' in result or 'error' in result,
            'Response should contain channel (on success) or error (on failure)',
        )


# =============================================================================
# E2E: CELERY TASK → EMAIL DELIVERY PIPELINE
# =============================================================================

@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST_USER='noreply@warungio.com',
    EMAIL_HOST_PASSWORD='secret',
    DEFAULT_FROM_EMAIL='noreply@warungio.com',
    CELERY_TASK_ALWAYS_EAGER=True,
)
class CeleryEmailTaskE2ETests(TestCase):
    """E2E tests: Celery task dispatches email via the same pipeline."""

    def test_e2e_celery_task_sends_otp_email(self):
        """E2E: Celery send_otp_task delivers email correctly."""
        send_otp_task(
            identifier='celery-test@warungio.com',
            otp_code='777777',
            purpose='registration',
            user_full_name='Celery User',
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['celery-test@warungio.com'])
        self.assertIn('777777', mail.outbox[0].subject)
        self.assertIn('Verifikasi Akun', mail.outbox[0].subject)

    def test_e2e_celery_task_password_reset_email(self):
        """E2E: Celery task sends password reset email with correct subject."""
        send_otp_task(
            identifier='reset-test@warungio.com',
            otp_code='555555',
            purpose='password_reset',
            user_full_name='Reset User',
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Reset Password', mail.outbox[0].subject)
        self.assertIn('555555', mail.outbox[0].subject)
        html_content = mail.outbox[0].alternatives[0][0]
        self.assertIn('Reset User', html_content)

    def test_e2e_celery_task_login_email(self):
        """E2E: Celery task sends login OTP with correct subject."""
        send_otp_task(
            identifier='login-test@warungio.com',
            otp_code='444444',
            purpose='login',
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Masuk', mail.outbox[0].subject)


# =============================================================================
# E2E: HTML EMAIL RENDERING PIPELINE
# =============================================================================

@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST_USER='noreply@warungio.com',
    EMAIL_HOST_PASSWORD='secret',
    DEFAULT_FROM_EMAIL='noreply@warungio.com',
)
class EmailRenderingPipelineE2ETests(TestCase):
    """E2E tests: Full email rendering pipeline — context → template → HTML."""

    def test_e2e_email_contains_all_required_elements(self):
        """E2E: Rendered email has all required elements for all purposes."""
        purposes = {
            'registration': ('Verifikasi Akun', 'verifikasi'),
            'login': ('Masuk', 'masuk'),
            'password_reset': ('Reset Password', 'reset'),
        }

        for purpose, (subject_keyword, _) in purposes.items():
            mail.outbox.clear()
            result = send_otp_email(
                email=f'test-{purpose}@warungio.com',
                otp_code='000000',
                purpose=purpose,
                user_full_name='Test User',
            )
            self.assertTrue(result['success'])
            email_msg = mail.outbox[0]

            # Subject
            self.assertIn(subject_keyword, email_msg.subject)

            # HTML content
            html_content = email_msg.alternatives[0][0]
            self.assertIn('Warungio', html_content)
            self.assertIn('Test User', html_content)
            self.assertIn('000000', html_content)
            self.assertIn('</html>', html_content)
            self.assertIn('viewport', html_content)  # responsive
            self.assertIn('style=', html_content)     # inline styles

            # Plain text
            self.assertTrue(len(email_msg.body) > 0)

    def test_e2e_email_sender_name_displayed(self):
        """E2E: Email sender name is properly displayed."""
        result = send_otp_email(
            email='display-test@warungio.com',
            otp_code='333333',
            purpose='registration',
        )
        self.assertTrue(result['success'])
        # DEFAULT_FROM_EMAIL should be used
        self.assertIn('noreply@warungio.com', str(mail.outbox[0].from_email))


# =============================================================================
# E2E: EMAIL PIPELINE ERROR RECOVERY
# =============================================================================

class EmailPipelineErrorRecoveryE2ETests(TestCase):
    """E2E tests: Email pipeline recovers from failures gracefully."""

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        EMAIL_HOST_USER='noreply@warungio.com',
        EMAIL_HOST_PASSWORD='secret',
        DEFAULT_FROM_EMAIL='noreply@warungio.com',
    )
    def test_e2e_pipeline_subsequent_emails_after_failure(self):
        """E2E: Pipeline continues working after a transient failure."""
        # 1. Simulate a failure
        import accounts.services.email_service as email_service
        with patch.object(email_service, 'send_mail',
                         side_effect=Exception('Transient failure')):
            result = send_otp_email(
                email='fail-test@warungio.com',
                otp_code='111111',
                purpose='registration',
            )
            self.assertFalse(result['success'])

        # 2. Clear outbox
        mail.outbox.clear()

        # 3. Next send should work fine
        result = send_otp_email(
            email='recovery-test@warungio.com',
            otp_code='222222',
            purpose='login',
        )
        self.assertTrue(result['success'])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['recovery-test@warungio.com'])
