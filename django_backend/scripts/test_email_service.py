#!/usr/bin/env python
"""Test email service to verify OTP delivery without running full test suite."""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ.setdefault('USE_MYSQL', 'False')
os.environ.setdefault('DJANGO_DEBUG', 'True')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

django.setup()

from django.conf import settings
from django.core import mail
from django.test.utils import override_settings
from accounts.services.email_service import send_otp_email
from accounts.models import User, OTP

def test_email_service():
    """Test OTP email service without DB dependency."""
    print("Testing OTP Email Service...")
    print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print(f"OTP_EXPIRE_MINUTES: {settings.OTP_EXPIRE_MINUTES}")

    # Configure to use in-memory email backend for testing
    with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
        print("\nTest 1: Send OTP email for registration")
        result = send_otp_email(
            email='test@warungio.com',
            otp_code='123456',
            purpose='registration',
            user_full_name='Test User',
        )
        print(f"Result: {result}")
        if mail.outbox:
            print(f"Email sent to: {mail.outbox[0].to}")
            print(f"Subject: {mail.outbox[0].subject}")
            print(f"Body preview: {mail.outbox[0].body[:200]}")
            mail.outbox.clear()
        else:
            print("No email in outbox (expected with default SMTP backend)")

        print("\nTest 2: Send OTP email for password reset")
        result = send_otp_email(
            email='user@example.com',
            otp_code='654321',
            purpose='password_reset',
            user_full_name='John Doe',
        )
        print(f"Result: {result}")
        if mail.outbox:
            print(f"Email sent to: {mail.outbox[0].to}")
            print(f"Subject: {mail.outbox[0].subject}")
            mail.outbox.clear()
        else:
            print("No email in outbox")

        print("\nTest 3: Invalid email")
        result = send_otp_email(
            email='invalid-email',
            otp_code='789012',
            purpose='login',
        )
        print(f"Result: {result}")
        if not result.get('success'):
            print(f"Error (expected): {result['error']}")

if __name__ == '__main__':
    test_email_service()
    print("\nEmail service tests completed!")
