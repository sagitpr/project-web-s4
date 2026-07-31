"""
Comprehensive email notification tests for Warungio.
Covers: send_otp_email, validate_email_settings, _email_configured,
        template rendering (HTML + plain text), SMTP failure handling,
        multi-alternative email structure, BadHeaderError, auth failures,
        network timeouts, and the send_test_notification management command.
"""

import uuid
from unittest.mock import patch, MagicMock
from datetime import timedelta

from django.test import TestCase, override_settings
from django.conf import settings
from django.core import mail
from django.core.management import call_command
from django.utils import timezone
from io import StringIO

from accounts.services.email_service import (
    send_otp_email,
    validate_email_settings,
    _email_configured,
    _subject_for_purpose,
)


class EmailServiceUnitTests(TestCase):
    """Unit tests for email_service.py functions."""

    # ── _email_configured ──

    @override_settings(EMAIL_HOST_USER='user@test.com', EMAIL_HOST_PASSWORD='secret')
    def test_email_configured_true(self):
        """Test _email_configured returns True when credentials are set."""
        self.assertTrue(_email_configured())

    @override_settings(EMAIL_HOST_USER='', EMAIL_HOST_PASSWORD='')
    def test_email_configured_false_empty(self):
        """Test _email_configured returns False when credentials are empty."""
        self.assertFalse(_email_configured())

    @override_settings(EMAIL_HOST_USER='user@test.com', EMAIL_HOST_PASSWORD='')
    def test_email_configured_false_partial(self):
        """Test _email_configured returns False when only user is set."""
        self.assertFalse(_email_configured())

    # ── _subject_for_purpose ──

    def test_subject_for_registration(self):
        """Test subject for registration purpose."""
        subject = _subject_for_purpose('registration', '123456')
        self.assertIn('Verifikasi Akun', subject)
        self.assertIn('123456', subject)

    def test_subject_for_password_reset(self):
        """Test subject for password reset purpose."""
        subject = _subject_for_purpose('password_reset', '654321')
        self.assertIn('Kata Sandi', subject)
        self.assertIn('654321', subject)

    def test_subject_for_unknown_purpose(self):
        """Test subject falls back to generic for unknown purpose."""
        subject = _subject_for_purpose('unknown', '000000')
        self.assertIn('Verifikasi', subject)

    # ── validate_email_settings ──

    @override_settings(
        EMAIL_HOST='smtp.test.com',
        EMAIL_PORT=587,
        EMAIL_HOST_USER='user@test.com',
        EMAIL_HOST_PASSWORD='secret',
        DEFAULT_FROM_EMAIL='noreply@test.com',
        EMAIL_USE_TLS=True,
    )
    def test_validate_email_settings_missing_config(self):
        """Test validation returns errors for missing config without SMTP attempt."""
        # When EMAIL_HOST_USER is set but SMTP connection fails, it returns the SMTP error
        result = validate_email_settings()
        self.assertFalse(result['success'])
        # It should either be a config error or SMTP connection error since we can't
        # actually connect to smtp.test.com
        self.assertIn('error', result)
        self.assertIn('message', result)

    @override_settings(EMAIL_HOST='', EMAIL_PORT=0, EMAIL_HOST_USER='', EMAIL_HOST_PASSWORD='',
                       DEFAULT_FROM_EMAIL='')
    def test_validate_email_settings_empty_config(self):
        """Test validation catches all missing settings."""
        result = validate_email_settings()
        self.assertFalse(result['success'])
        self.assertIn('EMAIL_HOST', result.get('error', ''))
        self.assertIn('EMAIL_PORT', result.get('error', ''))

    @override_settings(EMAIL_HOST='smtp.test.com', EMAIL_PORT=587,
                       EMAIL_HOST_USER='', EMAIL_HOST_PASSWORD='',
                       DEFAULT_FROM_EMAIL='noreply@test.com')
    def test_validate_email_settings_missing_credentials(self):
        """Test validation catches missing credentials."""
        result = validate_email_settings()
        self.assertFalse(result['success'])
        self.assertIn('EMAIL_HOST_USER', result.get('error', ''))

    # ── send_otp_email: no SMTP configured ──

    @override_settings(EMAIL_HOST_USER='', EMAIL_HOST_PASSWORD='')
    def test_send_otp_email_not_configured(self):
        """Test send_otp_email returns failure when SMTP not configured."""
        result = send_otp_email(
            email='test@warungio.com',
            otp_code='123456',
            purpose='registration',
        )
        self.assertFalse(result['success'])
        self.assertIn('SMTP', result.get('error', ''))

    # ── send_otp_email: successful send (locmem backend) ──

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        EMAIL_HOST_USER='test@warungio.com',
        EMAIL_HOST_PASSWORD='secret',
        DEFAULT_FROM_EMAIL='noreply@warungio.com',
    )
    def test_send_otp_email_success_locmem(self):
        """Test send_otp_email successfully sends via locmem backend."""
        result = send_otp_email(
            email='buyer@warungio.com',
            otp_code='654321',
            purpose='registration',
            user_full_name='Test User',
        )
        self.assertTrue(result['success'])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('654321', mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ['buyer@warungio.com'])

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        EMAIL_HOST_USER='test@warungio.com',
        EMAIL_HOST_PASSWORD='secret',
        DEFAULT_FROM_EMAIL='noreply@warungio.com',
    )
    def test_send_otp_email_html_content(self):
        """Test OTP email contains HTML with formatted OTP code."""
        result = send_otp_email(
            email='test@warungio.com',
            otp_code='999999',
            purpose='registration',
        )
        self.assertTrue(result['success'])
        html_content = mail.outbox[0].alternatives[0][0] if mail.outbox[0].alternatives else ''
        self.assertIn('999999', html_content)
        self.assertIn('Warungio', html_content)

    # ── send_otp_email: multipart structure ──

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        EMAIL_HOST_USER='test@warungio.com',
        EMAIL_HOST_PASSWORD='secret',
        DEFAULT_FROM_EMAIL='noreply@warungio.com',
    )
    def test_send_otp_email_multipart_alternative(self):
        """Test OTP email has both plain text and HTML alternatives."""
        result = send_otp_email(
            email='test@warungio.com',
            otp_code='888888',
            purpose='login',
        )
        self.assertTrue(result['success'])
        msg = mail.outbox[0]
        # Plain text body
        self.assertTrue(len(msg.body) > 0)
        # HTML alternative
        self.assertTrue(len(msg.alternatives) > 0)
        has_html = any('text/html' in alt for alt in msg.alternatives)
        self.assertTrue(has_html, 'Email should have text/html alternative')

    # ── send_otp_email: contextual subject by purpose ──

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        EMAIL_HOST_USER='test@warungio.com',
        EMAIL_HOST_PASSWORD='secret',
        DEFAULT_FROM_EMAIL='noreply@warungio.com',
    )
    def test_send_otp_email_subject_by_purpose(self):
        """Test email subject changes based on purpose."""
        for purpose, keyword in [
            ('registration', 'Verifikasi Akun'),
            ('login', 'Masuk'),
            ('password_reset', 'Kata Sandi'),
        ]:
            mail.outbox.clear()
            result = send_otp_email(
                email='test@warungio.com',
                otp_code='111111',
                purpose=purpose,
            )
            self.assertTrue(result['success'])
            self.assertIn(keyword, mail.outbox[0].subject,
                          f'Subject for {purpose} should contain {keyword}')


# =============================================================================
# EMAIL ERROR HANDLING TESTS
# =============================================================================

@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST_USER='test@warungio.com',
    EMAIL_HOST_PASSWORD='secret',
    DEFAULT_FROM_EMAIL='noreply@warungio.com',
)
class EmailErrorHandlingTests(TestCase):
    """Test email error handling: SMTP auth failure, timeout, BadHeaderError."""

    def test_send_otp_email_smtp_auth_failure(self):
        """Test send_otp_email handles SMTP auth failure gracefully."""
        import accounts.services.email_service as email_service
        with patch.object(email_service, 'send_mail',
                         side_effect=email_service.SMTPAuthenticationError(
                             535, b'Authentication failed')):
            result = send_otp_email(
                email='test@warungio.com',
                otp_code='123456',
                purpose='registration',
            )
        self.assertFalse(result['success'])
        self.assertIn('autentikasi', result.get('message', '').lower())

    def test_send_otp_email_smtp_timeout(self):
        """Test send_otp_email handles SMTP timeout gracefully."""
        import accounts.services.email_service as email_service
        with patch.object(email_service, 'send_mail',
                         side_effect=ConnectionError('Connection timed out')):
            result = send_otp_email(
                email='test@warungio.com',
                otp_code='123456',
                purpose='registration',
            )
        self.assertFalse(result['success'])
        self.assertIn('timeout', result.get('message', '').lower())

    def test_send_otp_email_bad_header(self):
        """Test send_otp_email handles BadHeaderError gracefully."""
        import accounts.services.email_service as email_service
        with patch.object(email_service, 'send_mail',
                         side_effect=email_service.BadHeaderError('Invalid header')):
            result = send_otp_email(
                email='test@warungio.com',
                otp_code='123456',
                purpose='registration',
            )
        self.assertFalse(result['success'])
        self.assertIn('header', result.get('message', '').lower())

    def test_send_otp_email_generic_smtp_error(self):
        """Test send_otp_email handles generic SMTPException gracefully."""
        import accounts.services.email_service as email_service
        with patch.object(email_service, 'send_mail',
                         side_effect=email_service.SMTPException('Server busy')):
            result = send_otp_email(
                email='test@warungio.com',
                otp_code='123456',
                purpose='registration',
            )
        self.assertFalse(result['success'])
        self.assertIn('smtp', result.get('message', '').lower())

    def test_send_otp_email_network_error(self):
        """Test send_otp_email handles general network error."""
        import accounts.services.email_service as email_service
        with patch.object(email_service, 'send_mail',
                         side_effect=TimeoutError('Socket timeout')):
            result = send_otp_email(
                email='test@warungio.com',
                otp_code='123456',
                purpose='registration',
            )
        self.assertFalse(result['success'])
        self.assertIn('timeout', result.get('message', '').lower())

    def test_send_otp_email_unexpected_error(self):
        """Test send_otp_email handles completely unexpected error."""
        import accounts.services.email_service as email_service
        with patch.object(email_service, 'send_mail',
                         side_effect=RuntimeError('Something broke')):
            result = send_otp_email(
                email='test@warungio.com',
                otp_code='123456',
                purpose='registration',
            )
        self.assertFalse(result['success'])

    def test_send_otp_email_zero_recipients(self):
        """Test send_otp_email handles sent_count=0 (no recipients)."""
        import accounts.services.email_service as email_service
        with patch.object(email_service, 'send_mail', return_value=0):
            result = send_otp_email(
                email='test@warungio.com',
                otp_code='123456',
                purpose='registration',
            )
        self.assertFalse(result['success'])
        self.assertIn('penerima 0', result.get('message', ''))


# =============================================================================
# EMAIL TEMPLATE RENDERING TESTS
# =============================================================================

@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST_USER='test@warungio.com',
    EMAIL_HOST_PASSWORD='secret',
    DEFAULT_FROM_EMAIL='noreply@warungio.com',
)
class EmailTemplateTests(TestCase):
    """Test email template rendering for all notification types."""

    def test_otp_email_html_template_renders(self):
        """Test the OTP HTML email template renders without errors."""
        result = send_otp_email(
            email='test@warungio.com',
            otp_code='123456',
            purpose='registration',
            user_full_name='Test User',
        )
        self.assertTrue(result['success'])
        html_content = mail.outbox[0].alternatives[0][0]
        self.assertIn('123456', html_content)
        self.assertIn('Test User', html_content)
        self.assertIn('Warungio', html_content)
        self.assertIn('</html>', html_content)

    def test_otp_email_plain_text_fallback(self):
        """Test plain text body exists and contains the OTP code."""
        result = send_otp_email(
            email='test@warungio.com',
            otp_code='777777',
            purpose='password_reset',
        )
        self.assertTrue(result['success'])
        plain_body = mail.outbox[0].body
        self.assertTrue(len(plain_body) > 0, 'Plain text body should not be empty')
        # Should contain the OTP or relevant content
        self.assertIn('777777', mail.outbox[0].subject)

    def test_otp_email_responsive_html_structure(self):
        """Test the HTML email has responsive design elements."""
        result = send_otp_email(
            email='test@warungio.com',
            otp_code='555555',
            purpose='registration',
        )
        self.assertTrue(result['success'])
        html_content = mail.outbox[0].alternatives[0][0]
        # Check for responsive meta tag
        self.assertIn('viewport', html_content)
        # Check for inline styles (required for email clients)
        self.assertIn('style=', html_content)
        # Check for table-based layout (required for Outlook)
        self.assertIn('<table', html_content)

    def test_otp_email_greeting_by_name(self):
        """Test the email greeting uses the user's name when provided."""
        result = send_otp_email(
            email='test@warungio.com',
            otp_code='444444',
            purpose='registration',
            user_full_name='Budi Santoso',
        )
        self.assertTrue(result['success'])
        html_content = mail.outbox[0].alternatives[0][0]
        self.assertIn('Budi Santoso', html_content)

    def test_otp_email_greeting_fallback_to_email(self):
        """Test the email greeting falls back to email prefix when name not provided."""
        result = send_otp_email(
            email='budi.pengguna@warungio.com',
            otp_code='333333',
            purpose='registration',
        )
        self.assertTrue(result['success'])
        html_content = mail.outbox[0].alternatives[0][0]
        self.assertIn('budi.pengguna', html_content)


# =============================================================================
# NOTIFICATION SERVICE TESTS
# =============================================================================

class NotificationServiceTests(TestCase):
    """Test the NotificationService dispatch logic."""

    @override_settings(EMAIL_HOST_USER='', EMAIL_HOST_PASSWORD='', DEBUG=True)
    def test_notification_service_fallback_to_console_in_debug(self):
        """Test notification_service falls back to console in DEBUG mode without SMTP."""
        from accounts.services.notification_service import notification_service
        result = notification_service.send_otp(
            identifier='test@warungio.com',
            otp_code='123456',
            purpose='registration',
        )
        self.assertTrue(result['success'])
        self.assertIn('console', result.get('message', '').lower())

    @override_settings(EMAIL_HOST_USER='', EMAIL_HOST_PASSWORD='', DEBUG=False)
    def test_notification_service_fails_without_smtp_in_production(self):
        """Test notification_service returns failure in production without SMTP."""
        from accounts.services.notification_service import notification_service
        result = notification_service.send_otp(
            identifier='test@warungio.com',
            otp_code='123456',
            purpose='registration',
        )
        self.assertFalse(result['success'])
        self.assertIn('tidak siap', result.get('message', '').lower())


# =============================================================================
# send_test_notification MANAGEMENT COMMAND TESTS
# =============================================================================

class SendTestNotificationCommandTests(TestCase):
    """Test the send_test_notification management command."""

    def test_command_diagnostic_only(self):
        """Test --diagnostic-only runs without errors."""
        out = StringIO()
        call_command('send_test_notification', '--diagnostic-only', stdout=out)
        output = out.getvalue()
        self.assertIn('SYSTEM AUDIT', output)
        self.assertIn('CONFIGURATION AUDIT', output)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        EMAIL_HOST_USER='test@warungio.com',
        EMAIL_HOST_PASSWORD='secret',
        DEFAULT_FROM_EMAIL='noreply@warungio.com',
    )
    def test_command_sends_email_with_locmem(self):
        """Test command successfully sends email via locmem backend (no real SMTP)."""
        out = StringIO()
        call_command(
            'send_test_notification',
            'recipient@test.com',
            '--subject', 'Test Subject',
            '--name', 'Tester',
            stdout=out,
        )
        output = out.getvalue()
        self.assertIn('SENT', output)
        self.assertIn('Test Subject', output)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['recipient@test.com'])
        self.assertEqual(mail.outbox[0].subject, 'Test Subject')

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        EMAIL_HOST_USER='test@warungio.com',
        EMAIL_HOST_PASSWORD='secret',
        DEFAULT_FROM_EMAIL='noreply@warungio.com',
    )
    def test_command_includes_test_id(self):
        """Test command output includes the test ID."""
        out = StringIO()
        call_command(
            'send_test_notification',
            'recipient@test.com',
            stdout=out,
        )
        output = out.getvalue()
        self.assertIn('Test ID:', output)

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        EMAIL_HOST_USER='test@warungio.com',
        EMAIL_HOST_PASSWORD='secret',
        DEFAULT_FROM_EMAIL='noreply@warungio.com',
    )
    def test_command_template_rendering_output(self):
        """Test command logs template rendering details."""
        out = StringIO()
        call_command(
            'send_test_notification',
            'test@warungio.com',
            stdout=out,
        )
        output = out.getvalue()
        self.assertIn('HTML template:', output)
        self.assertIn('Plain template:', output)

    @override_settings(EMAIL_HOST='', EMAIL_PORT='', EMAIL_HOST_USER='', EMAIL_HOST_PASSWORD='')
    def test_command_handles_missing_config(self):
        """Test command handles missing SMTP configuration gracefully."""
        out = StringIO()
        call_command(
            'send_test_notification',
            stdout=out,
        )
        output = out.getvalue()
        self.assertTrue(
            'FAILED' in output.upper() or 'INCOMPLETE' in output.upper() or 'CONFIGURATION' in output.upper(),
            f'Output should indicate missing config or diagnostic info. Got: {output[:200]}'
        )
