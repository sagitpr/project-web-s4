"""
Management command: python manage.py test_email [recipient]

Verifies SMTP configuration and sends a test email to confirm everything
works end-to-end.

Usage:
    python manage.py test_email user@example.com
    python manage.py test_email --purpose registration user@example.com

If no recipient is given, the command prints a diagnostic report and
exits without sending.
"""

import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.services.email_service import (
    send_otp_email,
    validate_email_settings,
)

logger = logging.getLogger('django_backend.accounts.email')


class Command(BaseCommand):
    help = 'Test SMTP / email configuration and optionally send a test OTP email.'

    PURPOSES = [
        'registration',
        'login',
        'password_reset',
        'email_change',
        'phone_change',
        'payment',
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            'recipient',
            nargs='?',
            type=str,
            default=None,
            help='Email address to send the test message to.',
        )
        parser.add_argument(
            '--purpose',
            type=str,
            default='registration',
            choices=self.PURPOSES,
            help=f"OTP purpose (default: registration). Choices: {', '.join(self.PURPOSES)}",
        )
        parser.add_argument(
            '--no-verify',
            action='store_true',
            default=False,
            help='Skip SMTP handshake verification (just send).',
        )

    def handle(self, *args, **options):
        recipient = options['recipient']
        purpose = options['purpose']
        skip_verify = options['no_verify']

        self.stdout.write(self.style.MIGRATE_HEADING('=== Warungio - Email Service Diagnostics ==='))
        self._nl()

        # -- 1. Environment info --------------------------------------------
        self._print_setting('EMAIL_BACKEND', settings.EMAIL_BACKEND)
        self._print_setting('EMAIL_HOST', settings.EMAIL_HOST)
        self._print_setting('EMAIL_PORT', str(settings.EMAIL_PORT))
        self._print_setting('EMAIL_USE_TLS', str(settings.EMAIL_USE_TLS))
        self._print_setting('DEFAULT_FROM_EMAIL', settings.DEFAULT_FROM_EMAIL)
        self._print_setting(
            'EMAIL_HOST_USER',
            settings.EMAIL_HOST_USER or '(empty - not configured)',
        )
        pw_hint = (
            '**** (set)'
            if settings.EMAIL_HOST_PASSWORD
            else '(empty - not configured)'
        )
        self._print_setting('EMAIL_HOST_PASSWORD', pw_hint)
        self.stdout.write(
            f'  OTP_EXPIRE_MINUTES ... {getattr(settings, "OTP_EXPIRE_MINUTES", 15)}'
        )
        self._nl()

        # -- 2. Validate settings structure ----------------------------------
        errors = []
        if not settings.EMAIL_HOST:
            errors.append('EMAIL_HOST is empty')
        if not settings.EMAIL_PORT:
            errors.append('EMAIL_PORT is empty')
        if not settings.EMAIL_HOST_USER:
            errors.append('EMAIL_HOST_USER is empty')
        if not settings.EMAIL_HOST_PASSWORD:
            errors.append('EMAIL_HOST_PASSWORD is empty')
        if not settings.DEFAULT_FROM_EMAIL:
            errors.append('DEFAULT_FROM_EMAIL is empty')

        if errors:
            for err in errors:
                self.stdout.write(self.style.WARNING(f'  !! {err}'))
            self._nl()
            self.stdout.write(
                self.style.WARNING(
                    'Set the missing values in your root .env or django_backend/.env file.'
                )
            )
            if not recipient:
                self.stdout.write(self.style.WARNING('\nNo recipient - exiting.'))
                return
            self._nl()

        # -- 3. SMTP handshake -----------------------------------------------
        if not skip_verify and settings.EMAIL_HOST and settings.EMAIL_HOST_USER:
            self.stdout.write('Testing SMTP connection ... ', ending='')
            result = validate_email_settings()
            if result['success']:
                self.stdout.write(self.style.SUCCESS('OK'))
                self.stdout.write(f'  {result["message"]}')
            else:
                self.stdout.write(self.style.ERROR('FAILED'))
                self.stdout.write(f'  {result["error"]}')
            self._nl()
        elif skip_verify:
            self.stdout.write('SMTP verification skipped (--no-verify).')
            self._nl()

        # -- 4. Send test email ----------------------------------------------
        if recipient:
            self.stdout.write(
                f'Sending test OTP email to {recipient} (purpose={purpose}) ... ',
                ending='',
            )

            result = send_otp_email(
                email=recipient,
                otp_code='123456',
                purpose=purpose,
                user_full_name='Warungio User',
            )

            if result['success']:
                self.stdout.write(self.style.SUCCESS('SENT'))
            else:
                self.stdout.write(self.style.ERROR('FAILED'))

            self._nl()
            self.stdout.write(f'  success .. {result["success"]}')
            self.stdout.write(f'  message .. {result["message"]}')
            if result.get('error'):
                self.stdout.write(self.style.ERROR(f'  error .... {result["error"]}'))
        else:
            self.stdout.write(
                self.style.WARNING(
                    'No recipient provided - skipping test send.\n'
                    '  Usage: python manage.py test_email user@example.com'
                )
            )

        # -- Summary ---------------------------------------------------------
        self._nl()
        all_ok = (
            settings.EMAIL_HOST
            and settings.EMAIL_PORT
            and settings.EMAIL_HOST_USER
            and settings.EMAIL_HOST_PASSWORD
            and settings.DEFAULT_FROM_EMAIL
        )
        if all_ok:
            self.stdout.write(self.style.SUCCESS('=== Configuration looks complete ==='))
        else:
            self.stdout.write(self.style.WARNING('=== Configuration INCOMPLETE ==='))

    # -----------------------------------------------------------------
    #  Helpers
    # -----------------------------------------------------------------

    def _nl(self):
        """Write a newline (ASCII-safe for Windows cp1252 console)."""
        self.stdout.write('')

    @staticmethod
    def _print_setting(name: str, value: str) -> None:
        """Pretty-print a setting name + value (ASCII-only)."""
        label = f'{name:.<26}'
        print(f'  {label} {value}')
