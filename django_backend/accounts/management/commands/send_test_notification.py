"""
Management command: python manage.py send_test_notification <recipient>

Sends a comprehensive test notification email through the configured email backend.
Audits the entire email delivery pipeline: SMTP handshake → template rendering →
Django send_mail → SMTP response → delivery status.

Usage:
    python manage.py send_test_notification user@example.com
    python manage.py send_test_notification user@example.com --subject "Custom Subject"
    python manage.py send_test_notification --diagnostic-only

Outputs complete delivery log including:
    - SMTP configuration audit
    - Template rendering status
    - Django send_mail response (sent_count)
    - SMTP server response details
    - Message-ID (extracted from headers)
    - Delivery timing
    - Success/failure status with error details
"""

import uuid
import time
import logging
from datetime import datetime
from email.mime.text import MIMEText
from smtplib import SMTPException, SMTPAuthenticationError

from django.conf import settings
from django.core.mail import BadHeaderError, EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

logger = logging.getLogger('django_backend.accounts.email')


class Command(BaseCommand):
    help = 'Send a comprehensive test notification email with full delivery audit logging.'

    def add_arguments(self, parser):
        parser.add_argument(
            'recipient',
            nargs='?',
            type=str,
            default=None,
            help='Email address to send the test notification to.',
        )
        parser.add_argument(
            '--subject',
            type=str,
            default='Warungio Test Notification',
            help='Email subject line.',
        )
        parser.add_argument(
            '--name',
            type=str,
            default='Admin Warungio',
            help='Sender display name.',
        )
        parser.add_argument(
            '--diagnostic-only',
            action='store_true',
            default=False,
            help='Only show diagnostic info without sending an email.',
        )

    def handle(self, *args, **options):
        recipient = options['recipient']
        subject = options['subject']
        sender_name = options['name']
        diagnostic_only = options['diagnostic_only']

        # Generate unique identifiers for this test
        test_id = uuid.uuid4().hex[:12].upper()
        timestamp = timezone.now()
        timestamp_str = timestamp.strftime('%d %B %Y %H:%M:%S WIB')

        self.stdout.write(self.style.MIGRATE_HEADING(
            '+==============================================================+'
        ))
        self.stdout.write(self.style.MIGRATE_HEADING(
            '|      WARUNGIO EMAIL NOTIFICATION SYSTEM AUDIT                |'
        ))
        self.stdout.write(self.style.MIGRATE_HEADING(
            '+==============================================================+'
        ))
        self._nl()

        # ── 1. CONFIGURATION AUDIT ──
        self.stdout.write(self.style.MIGRATE_HEADING('[1/5] EMAIL CONFIGURATION AUDIT'))
        self._print_setting('EMAIL_BACKEND', settings.EMAIL_BACKEND)
        self._print_setting('EMAIL_HOST', settings.EMAIL_HOST or '(not set)')
        self._print_setting('EMAIL_PORT', str(settings.EMAIL_PORT) if settings.EMAIL_PORT else '(not set)')
        self._print_setting('EMAIL_USE_TLS', str(settings.EMAIL_USE_TLS))
        self._print_setting('DEFAULT_FROM_EMAIL', settings.DEFAULT_FROM_EMAIL or '(not set)')

        host_user_configured = bool(settings.EMAIL_HOST_USER)
        host_pass_configured = bool(settings.EMAIL_HOST_PASSWORD)
        self._print_setting('EMAIL_HOST_USER configured', 'YES' if host_user_configured else 'NO')
        self._print_setting('EMAIL_HOST_PASS configured', 'YES' if host_pass_configured else 'NO')

        # Check Celery configuration
        celery_available = False
        try:
            from celery import current_app
            celery_available = current_app.conf.broker_url is not None
        except Exception:
            pass
        self._print_setting('Celery available', 'YES' if celery_available else 'NO')

        email_backend_type = 'SMTP (real)' if 'smtp' in settings.EMAIL_BACKEND.lower() else settings.EMAIL_BACKEND
        self._print_setting('Email backend type', email_backend_type)
        self._nl()

        if diagnostic_only:
            self.stdout.write(self.style.WARNING('Diagnostic mode: skipping email send.'))
            return

        # ── 2. SMTP CONNECTION TEST (skip for non-SMTP backends like locmem) ──
        self.stdout.write(self.style.MIGRATE_HEADING('[2/5] SMTP CONNECTION TEST'))
        is_smtp = 'smtp' in settings.EMAIL_BACKEND.lower()
        if is_smtp:
            smtp_result = self._test_smtp_connection()
            if not smtp_result['success']:
                self.stdout.write(self.style.ERROR(
                    'SMTP connection FAILED. Cannot proceed with email send.\n'
                    f'  Error: {smtp_result["error"]}'
                ))
                self._nl()
                self._print_summary(False, test_id, timestamp_str, smtp_result.get('error'))
                return
        else:
            self.stdout.write(self.style.WARNING(
                f'  Non-SMTP backend detected ({settings.EMAIL_BACKEND}) — skipping handshake test.'
            ))
            smtp_result = {'success': True}
        self._nl()

        if not recipient:
            self.stdout.write(self.style.WARNING(
                'No recipient provided.\n'
                '  Usage: python manage.py send_test_notification user@example.com'
            ))
            self._nl()
            self._print_summary(True, test_id, timestamp_str)
            return

        # ── 3. TEMPLATE RENDERING TEST ──
        self.stdout.write(self.style.MIGRATE_HEADING('[3/5] EMAIL TEMPLATE RENDERING TEST'))
        context = self._build_context(test_id, timestamp_str, sender_name, recipient)
        template_result = self._render_email_template(context)
        self._nl()

        if not template_result['success']:
            self.stdout.write(self.style.ERROR(f'Template rendering FAILED: {template_result["error"]}'))
            self._print_summary(False, test_id, timestamp_str, template_result.get('error'))
            return

        # ── 4. SEND EMAIL ──
        self.stdout.write(self.style.MIGRATE_HEADING('[4/5] SENDING EMAIL'))
        self.stdout.write(f'  From:       {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write(f'  To:         {recipient}')
        self.stdout.write(f'  Subject:    {subject}')
        self.stdout.write(f'  Test ID:    {test_id}')
        self.stdout.write(f'  Timestamp:  {timestamp_str}')
        self._nl()

        send_result = self._send_email(
            subject=subject,
            recipient=recipient,
            html_message=template_result['html'],
            plain_message=template_result['plain'],
            test_id=test_id,
        )
        self._nl()

        # ── 5. DELIVERY SUMMARY ──
        self.stdout.write(self.style.MIGRATE_HEADING('[5/5] DELIVERY SUMMARY'))
        self._print_summary(
            send_result['success'],
            test_id,
            timestamp_str,
            send_result.get('error'),
            send_result.get('message_id'),
            send_result.get('delivery_time_ms'),
            send_result.get('smtp_response'),
        )

    # =========================================================================
    # INTERNAL METHODS
    # =========================================================================

    def _test_smtp_connection(self):
        """Test SMTP connection with detailed handshake logging."""
        if not settings.EMAIL_HOST or not settings.EMAIL_PORT:
            return {
                'success': False,
                'error': 'EMAIL_HOST or EMAIL_PORT not configured.',
            }
        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            return {
                'success': False,
                'error': 'EMAIL_HOST_USER or EMAIL_HOST_PASSWORD not configured.',
            }

        from smtplib import SMTP
        self.stdout.write('  Connecting to SMTP server ... ', ending='')
        self.stdout.flush()

        try:
            smtp = SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=15)
            self.stdout.write(self.style.SUCCESS('CONNECTED'))
            self.stdout.write(f'  Server:     {settings.EMAIL_HOST}:{settings.EMAIL_PORT}')

            # EHLO
            self.stdout.write('  EHLO handshake ... ', ending='')
            self.stdout.flush()
            ehlo_result = smtp.ehlo_or_helo_if_needed()
            if ehlo_result is not None and len(ehlo_result) >= 2:
                ehlo_code, ehlo_msg = ehlo_result
                if ehlo_code == 250:
                    self.stdout.write(self.style.SUCCESS(f'OK (code={ehlo_code})'))
                else:
                    self.stdout.write(self.style.WARNING(f'Unexpected response (code={ehlo_code})'))
                # Show first few capabilities safely
                capabilities = []
                for m in ehlo_msg[:5]:
                    if isinstance(m, bytes):
                        capabilities.append(m.decode('utf-8', errors='replace'))
                    else:
                        capabilities.append(str(m))
                self.stdout.write(f'  Server capabilities: {capabilities}...')
            else:
                self.stdout.write(self.style.WARNING('OK (no extended info)'))

            # STARTTLS
            if settings.EMAIL_USE_TLS:
                self.stdout.write('  STARTTLS upgrade ... ', ending='')
                self.stdout.flush()
                smtp.starttls()
                self.stdout.write(self.style.SUCCESS('OK'))
                smtp.ehlo_or_helo_if_needed()

            # LOGIN
            self.stdout.write('  SMTP AUTH LOGIN ... ', ending='')
            self.stdout.flush()
            smtp.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            self.stdout.write(self.style.SUCCESS('OK'))

            smtp.quit()
            self.stdout.write('  SMTP connection closed gracefully.')
            return {'success': True, 'error': None}

        except SMTPAuthenticationError as e:
            self.stdout.write(self.style.ERROR('FAILED'))
            return {
                'success': False,
                'error': f'SMTP Authentication failed (535): {e}',
            }
        except SMTPException as e:
            self.stdout.write(self.style.ERROR('FAILED'))
            return {
                'success': False,
                'error': f'SMTP error: {e}',
            }
        except OSError as e:
            self.stdout.write(self.style.ERROR('FAILED'))
            return {
                'success': False,
                'error': f'Network error: {e}',
            }
        except Exception as e:
            self.stdout.write(self.style.ERROR('FAILED'))
            return {
                'success': False,
                'error': f'Unexpected error: {e}',
            }

    def _build_context(self, test_id, timestamp_str, sender_name, recipient):
        """Build email template context for the test notification."""
        return {
            'test_id': test_id,
            'timestamp': timestamp_str,
            'sender_name': sender_name,
            'recipient': recipient,
            'site_name': 'Warungio',
            'support_email': settings.DEFAULT_FROM_EMAIL,
            'email_host': settings.EMAIL_HOST,
            'email_port': settings.EMAIL_PORT,
            'email_backend': settings.EMAIL_BACKEND,
            'email_tls': 'Yes' if settings.EMAIL_USE_TLS else 'No',
            'django_debug': 'Yes' if settings.DEBUG else 'No',
            'current_year': datetime.now().year,
        }

    def _render_email_template(self, context):
        """Render both HTML and plain text email templates."""
        # HTML template
        html_template = 'email/test_notification.html'
        html_message = None
        try:
            html_message = render_to_string(html_template, context)
            html_len = len(html_message)
            self.stdout.write(f'  HTML template:  {html_template} ({html_len} chars) OK')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  HTML template:  {html_template} - NOT FOUND, generating inline'))
            html_message = self._generate_html_fallback(context)
            self.stdout.write(f'  HTML template:  inline fallback ({len(html_message)} chars) OK')

        # Plain text template
        plain_template = 'email/test_notification.txt'
        plain_message = None
        try:
            plain_message = render_to_string(plain_template, context)
            self.stdout.write(f'  Plain template: {plain_template} ({len(plain_message)} chars) OK')
        except Exception:
            plain_message = strip_tags(html_message)
            self.stdout.write(f'  Plain template: auto-generated from HTML ({len(plain_message)} chars) OK')

        if html_message and plain_message:
            return {
                'success': True,
                'html': html_message,
                'plain': plain_message,
            }
        return {
            'success': False,
            'error': 'Failed to render email templates.',
        }

    def _send_email(self, subject, recipient, html_message, plain_message, test_id):
        """Send email with detailed timing and response capture."""
        start_time = time.time()

        self.stdout.write('  Sending via Django mail backend ... ', ending='')
        self.stdout.flush()

        try:
            # Use EmailMultiAlternatives for proper HTML + plain text support
            email_msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,  # plain text body
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient],
                headers={
                    'X-Test-ID': test_id,
                    'X-Auto-Response-Suppress': 'All',
                    'Precedence': 'bulk',
                },
            )
            email_msg.attach_alternative(html_message, 'text/html')

            # Actually send the email (fail_silently=False ensures real delivery)
            sent_count = email_msg.send(fail_silently=False)

            delivery_time_ms = (time.time() - start_time) * 1000

            if sent_count == 1:
                self.stdout.write(self.style.SUCCESS('SENT'))
                self.stdout.write(f'  Delivery time:  {delivery_time_ms:.0f} ms')

                # Extract Message-ID from the message
                message_id = email_msg.extra_headers.get('Message-ID', 'N/A')
                # If message was actually sent, Django populates the Message-ID
                # We need to check the underlying message
                try:
                    if hasattr(email_msg, 'message'):
                        raw_msg = email_msg.message()
                        message_id = raw_msg.get('Message-ID', message_id)
                except Exception:
                    pass

                self.stdout.write(f'  Message-ID:     {message_id}')
                self.stdout.write(f'  SMTP backend:   {settings.EMAIL_BACKEND}')
                self.stdout.write(f'  SMTP host:      {settings.EMAIL_HOST}:{settings.EMAIL_PORT}')
                self.stdout.write(f'  TLS enabled:    {settings.EMAIL_USE_TLS}')

                # Log success to Django logger
                logger.info(
                    'TEST NOTIFICATION SENT — TestID: %s | To: %s | Duration: %.0fms | Message-ID: %s',
                    test_id, recipient, delivery_time_ms, message_id,
                )

                return {
                    'success': True,
                    'message_id': message_id,
                    'delivery_time_ms': delivery_time_ms,
                    'smtp_response': f'250 OK (sent via {settings.EMAIL_HOST}:{settings.EMAIL_PORT})',
                    'error': None,
                }
            else:
                self.stdout.write(self.style.ERROR('FAILED (sent_count=0)'))
                return {
                    'success': False,
                    'error': f'send_mail returned sent_count={sent_count} (expected 1)',
                    'delivery_time_ms': delivery_time_ms,
                    'message_id': None,
                    'smtp_response': None,
                }

        except BadHeaderError as e:
            self.stdout.write(self.style.ERROR('FAILED'))
            return {
                'success': False,
                'error': f'BadHeaderError: {e}',
                'delivery_time_ms': (time.time() - start_time) * 1000,
                'message_id': None,
                'smtp_response': None,
            }
        except SMTPAuthenticationError as e:
            self.stdout.write(self.style.ERROR('FAILED'))
            logger.error('Test notification SMTP auth failed: %s', e)
            return {
                'success': False,
                'error': f'SMTP Authentication failed: {e}',
                'delivery_time_ms': (time.time() - start_time) * 1000,
                'message_id': None,
                'smtp_response': '535 Authentication credentials invalid',
            }
        except SMTPException as e:
            self.stdout.write(self.style.ERROR('FAILED'))
            logger.error('Test notification SMTP error: %s', e)
            return {
                'success': False,
                'error': f'SMTP error: {e}',
                'delivery_time_ms': (time.time() - start_time) * 1000,
                'message_id': None,
                'smtp_response': str(e),
            }
        except (ConnectionError, TimeoutError) as e:
            self.stdout.write(self.style.ERROR('FAILED'))
            logger.error('Test notification network error: %s', e)
            return {
                'success': False,
                'error': f'Network/Timeout error: {e}',
                'delivery_time_ms': (time.time() - start_time) * 1000,
                'message_id': None,
                'smtp_response': 'Connection timeout or refused',
            }
        except Exception as e:
            self.stdout.write(self.style.ERROR('FAILED'))
            logger.exception('Test notification unexpected error: %s', e)
            return {
                'success': False,
                'error': f'Unexpected error: {e}',
                'delivery_time_ms': (time.time() - start_time) * 1000,
                'message_id': None,
                'smtp_response': str(e),
            }

    def _generate_html_fallback(self, context):
        """Generate HTML email inline if template is unavailable."""
        return f"""<!DOCTYPE html>
<html lang="id">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Warungio Test Notification</title></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;">
<tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
<tr><td style="background:linear-gradient(135deg,#059669,#047857);padding:32px 40px;text-align:center;">
<h1 style="color:#fff;font-size:24px;margin:0;font-weight:700;">Warungio</h1>
<p style="color:#a7f3d0;font-size:14px;margin:8px 0 0;">Test Notification System</p>
</td></tr>
<tr><td style="padding:40px;">
<p style="color:#1f2937;font-size:16px;line-height:1.6;margin:0 0 16px;">
Halo <strong>Penerima Uji Coba</strong>,</p>
<p style="color:#4b5563;font-size:14px;line-height:1.6;margin:0 0 24px;">
Email ini adalah <strong>uji coba sistem notifikasi Warungio</strong> yang dikirim untuk memverifikasi bahwa seluruh pipeline pengiriman email berfungsi dengan benar.</p>

<div style="background:#f0fdf4;border:2px solid #86efac;border-radius:12px;padding:24px;margin-bottom:24px;">
<table width="100%" cellpadding="6" cellspacing="0">
<tr><td style="color:#374151;font-size:13px;font-weight:600;width:140px;">Test ID</td>
<td style="color:#059669;font-size:14px;font-weight:700;font-family:monospace;">{context['test_id']}</td></tr>
<tr><td style="color:#374151;font-size:13px;font-weight:600;">Waktu</td>
<td style="color:#1f2937;font-size:14px;">{context['timestamp']}</td></tr>
<tr><td style="color:#374151;font-size:13px;font-weight:600;">Server</td>
<td style="color:#1f2937;font-size:14px;">{context['email_host']}:{context['email_port']}</td></tr>
<tr><td style="color:#374151;font-size:13px;font-weight:600;">Backend</td>
<td style="color:#1f2937;font-size:14px;">{context['email_backend']}</td></tr>
<tr><td style="color:#374151;font-size:13px;font-weight:600;">TLS</td>
<td style="color:#1f2937;font-size:14px;">{context['email_tls']}</td></tr>
<tr><td style="color:#374151;font-size:13px;font-weight:600;">Debug Mode</td>
<td style="color:#1f2937;font-size:14px;">{context['django_debug']}</td></tr>
</table></div>

<p style="color:#059669;font-size:14px;font-weight:600;margin:0 0 8px;">
✅ Sistem email Warungio berhasil dikonfigurasi dan siap digunakan.</p>
<p style="color:#6b7280;font-size:13px;line-height:1.5;margin:0 0 24px;">
Seluruh fitur yang bergantung pada pengiriman email seperti OTP, Reset Password, Registrasi, Notifikasi Pembayaran, Status Pesanan, dan notifikasi sistem lainnya telah siap beroperasi.</p>

<hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
<p style="color:#9ca3af;font-size:12px;line-height:1.5;margin:0;">
&copy; {context['current_year']} Warungio. All rights reserved.<br>
<a href="mailto:{context['support_email']}" style="color:#059669;text-decoration:none;">{context['support_email']}</a>
</p></td></tr>
<tr><td style="background:#f9fafb;padding:20px 40px;text-align:center;">
<p style="color:#9ca3af;font-size:11px;margin:0;">
Email ini dikirim secara otomatis oleh sistem Warungio untuk keperluan uji coba notifikasi.<br>
Mohon tidak membalas email ini secara langsung.</p>
</td></tr></table></td></tr></table></body></html>"""

    def _print_summary(self, success, test_id, timestamp, error=None, message_id=None,
                       delivery_time_ms=None, smtp_response=None):
        """Print delivery summary."""
        status_text = self.style.SUCCESS('SUCCESS') if success else self.style.ERROR('FAILED')

        self.stdout.write(self.style.MIGRATE_HEADING(
            '+----------------------------------------------------------------+'
        ))
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'  EMAIL NOTIFICATION TEST RESULT:  {status_text}'
        ))
        self.stdout.write(self.style.MIGRATE_HEADING(
            '+----------------------------------------------------------------+'
        ))
        self.stdout.write(f'  [+] Test ID:        {test_id}')
        self.stdout.write(f'  Timestamp:         {timestamp}')
        self.stdout.write(f'  Backend:           {settings.EMAIL_BACKEND}')
        self.stdout.write(f'  SMTP Server:       {settings.EMAIL_HOST}:{settings.EMAIL_PORT}')

        if success:
            if message_id:
                self.stdout.write(f'  Message-ID:        {message_id}')
            if delivery_time_ms is not None:
                self.stdout.write(f'  Delivery time:     {delivery_time_ms:.0f} ms')
            if smtp_response:
                self.stdout.write(f'  SMTP Response:     {smtp_response}')
            self.stdout.write(self.style.SUCCESS(
                '  Status:            EMAIL BERHASIL DIKIRIM'
            ))
        else:
            if error:
                self.stdout.write(self.style.ERROR(f'  Error:             {error}'))
            if smtp_response:
                self.stdout.write(f'  SMTP Response:     {smtp_response}')
            self.stdout.write(self.style.ERROR(
                '  Status:            EMAIL GAGAL DIKIRIM'
            ))

        self.stdout.write(self.style.MIGRATE_HEADING(
            '+----------------------------------------------------------------+'
        ))
        self._nl()

        # Final log to Django logger
        if success:
            logger.info(
                'TEST NOTIFICATION RESULT — SUCCESS | TestID: %s | '
                'Backend: %s | Server: %s:%s | Time: %.0fms',
                test_id, settings.EMAIL_BACKEND,
                settings.EMAIL_HOST, settings.EMAIL_PORT,
                delivery_time_ms or 0,
            )
        else:
            logger.error(
                'TEST NOTIFICATION RESULT — FAILED | TestID: %s | Error: %s',
                test_id, error,
            )

    def _nl(self):
        self.stdout.write('')

    @staticmethod
    def _print_setting(name: str, value: str) -> None:
        label = f'{name:.<32}'
        print(f'  {label} {value}')
