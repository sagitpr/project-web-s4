"""
Management command: python manage.py check_inbox [--email <email>]

Checks a Gmail/IMAP mailbox to verify if a specific test email arrived
and whether it landed in Inbox or Spam folder.

This provides the "Inbox vs Spam" audit that cannot be determined
from the sending side alone.

Usage:
    python manage.py check_inbox --email recipient@gmail.com
    python manage.py check_inbox --email recipient@gmail.com --test-id ABC123
    python manage.py check_inbox --email recipient@gmail.com --imap-server imap.gmail.com --imap-user user@gmail.com
    python manage.py check_inbox --diagnostic-only

Requires IMAP credentials (app password for Gmail) configured in .env:
    IMAP_HOST=imap.gmail.com
    IMAP_PORT=993
    IMAP_USER=your-email@gmail.com
    IMAP_PASSWORD=your-app-password

Note: For security, use Gmail App Passwords (not your regular password).
      Generate at: https://myaccount.google.com/apppasswords
"""

import uuid
import logging
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger('django_backend.accounts.email')


class Command(BaseCommand):
    help = 'Check if a test email landed in Inbox or Spam via IMAP.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default=None,
            help='Email address of the recipient to check (search for recent messages).',
        )
        parser.add_argument(
            '--test-id',
            type=str,
            default=None,
            help='Test ID from send_test_notification command (searches email body for this ID).',
        )
        parser.add_argument(
            '--imap-server',
            type=str,
            default=None,
            help='IMAP server hostname (overrides settings.IMAP_HOST).',
        )
        parser.add_argument(
            '--imap-user',
            type=str,
            default=None,
            help='IMAP username (overrides settings.IMAP_USER).',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Maximum number of recent messages to search (default: 20).',
        )
        parser.add_argument(
            '--diagnostic-only',
            action='store_true',
            default=False,
            help='Only show configuration info without connecting to IMAP.',
        )

    def handle(self, *args, **options):
        email = options['email']
        test_id = options['test_id']
        imap_server = options['imap_server'] or getattr(settings, 'IMAP_HOST', None)
        imap_user = options['imap_user'] or getattr(settings, 'IMAP_USER', None)
        search_limit = options['limit']
        diagnostic_only = options['diagnostic_only']

        self.stdout.write(self.style.MIGRATE_HEADING(
            '+================================================================+'
        ))
        self.stdout.write(self.style.MIGRATE_HEADING(
            '|      WARUNGIO EMAIL INBOX AUDIT                                |'
        ))
        self.stdout.write(self.style.MIGRATE_HEADING(
            '+================================================================+'
        ))
        self._nl()

        # ── 1. Check configuration ──
        self.stdout.write(self.style.MIGRATE_HEADING('[1/4] IMAP CONFIGURATION'))
        imap_password = getattr(settings, 'IMAP_PASSWORD', None)
        imap_port = getattr(settings, 'IMAP_PORT', 993)

        self._print_setting('IMAP_HOST', imap_server or '(not configured)')
        self._print_setting('IMAP_PORT', str(imap_port) if imap_port else '993')
        self._print_setting('IMAP_USER', imap_user or '(not configured)')
        self._print_setting('IMAP_PASS configured', 'YES' if imap_password else 'NO')
        self._print_setting('Recipient email', email or '(not provided)')
        self._print_setting('Test ID search', test_id or '(searching recent)')
        self._nl()

        if diagnostic_only:
            self.stdout.write(self.style.WARNING('Diagnostic mode: skipping IMAP connection.'))
            self._print_instructions()
            return

        if not imap_server:
            self.stdout.write(self.style.ERROR(
                'IMAP server not configured.\n'
                '  Set IMAP_HOST in your .env file or use --imap-server.\n'
                '  Example: IMAP_HOST=imap.gmail.com'
            ))
            self._print_instructions()
            return

        if not imap_user or not imap_password:
            self.stdout.write(self.style.ERROR(
                'IMAP credentials not configured.\n'
                '  Set IMAP_USER and IMAP_PASSWORD in your .env file or use --imap-user.\n'
                '  For Gmail: use an App Password (not your regular password).\n'
                '  Generate at: https://myaccount.google.com/apppasswords'
            ))
            return

        # ── 2. Connect to IMAP ──
        self.stdout.write(self.style.MIGRATE_HEADING('[2/4] IMAP CONNECTION'))
        connect_result = self._connect_imap(imap_server, imap_port, imap_user, imap_password)
        self._nl()

        if not connect_result['success']:
            self.stdout.write(self.style.ERROR(f'IMAP connection FAILED: {connect_result["error"]}'))
            return

        mail_conn = connect_result['connection']

        try:
            # ── 3. Search Inbox ──
            self.stdout.write(self.style.MIGRATE_HEADING('[3/4] SEARCHING INBOX'))
            inbox_result = self._search_folder(mail_conn, 'INBOX', email, test_id, search_limit)
            self._nl()

            # ── 4. Search Spam ──
            self.stdout.write(self.style.MIGRATE_HEADING('[4/4] SEARCHING SPAM'))
            spam_result = self._search_folder(mail_conn, '[Gmail]/Spam', email, test_id, search_limit)
            self._nl()

            # ── Summary ──
            self._print_audit_summary(inbox_result, spam_result, email, test_id)
        finally:
            try:
                mail_conn.logout()
            except Exception:
                pass

        self._nl()
        self._print_instructions()

    # =========================================================================
    # INTERNAL METHODS
    # =========================================================================

    def _connect_imap(self, server, port, user, password):
        """Connect to IMAP server and login."""
        import imaplib

        self.stdout.write(f'  Connecting to {server}:{port} ... ', ending='')
        self.stdout.flush()

        try:
            mail_conn = imaplib.IMAP4_SSL(server, port, timeout=15)
            self.stdout.write(self.style.SUCCESS('CONNECTED'))

            self.stdout.write('  IMAP LOGIN ... ', ending='')
            self.stdout.flush()
            mail_conn.login(user, password)
            self.stdout.write(self.style.SUCCESS('OK'))

            return {'success': True, 'connection': mail_conn}

        except imaplib.IMAP4.abort as e:
            self.stdout.write(self.style.ERROR('FAILED'))
            return {'success': False, 'error': f'IMAP connection aborted: {e}'}
        except Exception as e:
            self.stdout.write(self.style.ERROR('FAILED'))
            return {'success': False, 'error': str(e)}

    def _search_folder(self, mail_conn, folder_name, email, test_id, limit):
        """Search a specific IMAP folder for matching emails."""
        import imaplib

        self.stdout.write(f'  Opening folder "{folder_name}" ... ', ending='')
        self.stdout.flush()

        try:
            status, _ = mail_conn.select(folder_name, readonly=True)
            if status != 'OK':
                self.stdout.write(self.style.WARNING('NOT FOUND'))
                return {
                    'found': False,
                    'count': 0,
                    'messages': [],
                    'note': f'Folder "{folder_name}" does not exist on this server.',
                }
            self.stdout.write(self.style.SUCCESS('OK'))

            # Search strategy
            search_criteria = []
            if email:
                search_criteria.append(f'(TO "{email}")')
            if test_id:
                search_criteria.append(f'(BODY "{test_id}")')

            # If no specific criteria, get recent messages
            if not search_criteria:
                search_criteria.append('(SINCE 01-Jan-2026)')

            search_query = ' '.join(search_criteria) if search_criteria else 'ALL'
            self.stdout.write(f'  Searching: {search_query}'[:80] + ' ... ', ending='')
            self.stdout.flush()

            status, message_ids = mail_conn.search(None, search_query)

            if status != 'OK' or not message_ids[0]:
                self.stdout.write(self.style.WARNING('NONE FOUND'))
                return {'found': False, 'count': 0, 'messages': []}

            ids = message_ids[0].split()
            total = len(ids)
            self.stdout.write(self.style.SUCCESS(f'{total} message(s) found'))

            # Fetch details for recent messages
            messages = []
            fetch_ids = ids[-min(limit, total):]  # Get most recent ones

            for msg_id in fetch_ids:
                try:
                    status, data = mail_conn.fetch(msg_id, '(FLAGS BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID X-TEST-ID)])')
                    if status != 'OK':
                        continue

                    headers = data[0][1].decode('utf-8', errors='replace')
                    flags = data[0][0] if isinstance(data[0][0], bytes) else b''

                    # Parse headers
                    msg_info = self._parse_headers(headers, flags)
                    msg_info['id'] = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
                    messages.append(msg_info)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  Error reading message {msg_id}: {e}'))

            return {
                'found': len(messages) > 0,
                'count': len(messages),
                'total': total,
                'messages': messages,
            }

        except imaplib.IMAP4.abort as e:
            self.stdout.write(self.style.ERROR('FAILED'))
            return {'found': False, 'count': 0, 'messages': [], 'error': str(e)}
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'ERROR: {e}'))
            return {'found': False, 'count': 0, 'messages': [], 'error': str(e)}

    def _parse_headers(self, header_text, flags):
        """Parse email headers from IMAP FETCH response."""
        import email as email_parser
        from email import policy

        msg = email_parser.message_from_string(header_text, policy=policy.default)

        subject = str(msg.get('Subject', 'N/A'))
        sender = str(msg.get('From', 'N/A'))
        date = str(msg.get('Date', 'N/A'))
        message_id = str(msg.get('Message-ID', 'N/A'))
        x_test_id = str(msg.get('X-Test-ID', 'N/A'))

        # Determine if seen/unseen
        seen = b'\\Seen' in flags

        return {
            'subject': subject[:100],
            'from': sender[:100],
            'date': date[:40],
            'message_id': message_id[:80],
            'x_test_id': x_test_id[:30],
            'seen': seen,
        }

    def _print_audit_summary(self, inbox_result, spam_result, email, test_id):
        """Print final inbox audit summary."""
        self.stdout.write(self.style.MIGRATE_HEADING(
            '+----------------------------------------------------------------+'
        ))
        self.stdout.write(self.style.MIGRATE_HEADING(
            '  EMAIL INBOX AUDIT RESULT'
        ))
        self.stdout.write(self.style.MIGRATE_HEADING(
            '+----------------------------------------------------------------+'
        ))

        # Check Inbox
        inbox_found = inbox_result.get('found', False)
        inbox_count = inbox_result.get('count', 0)
        inbox_messages = inbox_result.get('messages', [])

        # Check Spam
        spam_found = spam_result.get('found', False)
        spam_count = spam_result.get('count', 0)
        spam_messages = spam_result.get('messages', [])

        if email:
            self.stdout.write(f'  Recipient:       {email}')
        if test_id:
            self.stdout.write(f'  Test ID search:  {test_id}')

        self._nl()

        # Inbox status
        if inbox_found:
            self.stdout.write(self.style.SUCCESS(
                f'  [+] INBOX:  {inbox_count} matching message(s) found'
            ))
            for m in inbox_messages:
                self.stdout.write(f'       Subject: {m["subject"]}')
                self.stdout.write(f'       From:    {m["from"]}')
                self.stdout.write(f'       Date:    {m["date"]}')
                if m['x_test_id'] != 'N/A':
                    self.stdout.write(f'       Test ID: {m["x_test_id"]}')
                self._nl()
        else:
            self.stdout.write(self.style.WARNING(
                f'  [!] INBOX:  No matching messages found'
            ))

        # Spam status
        if spam_found:
            self.stdout.write(self.style.WARNING(
                f'  [!] SPAM:   {spam_count} matching message(s) found in Spam!'
            ))
            for m in spam_messages:
                self.stdout.write(f'       Subject: {m["subject"]}')
                self.stdout.write(f'       From:    {m["from"]}')
                self.stdout.write(f'       Date:    {m["date"]}')
                if m['x_test_id'] != 'N/A':
                    self.stdout.write(f'       Test ID: {m["x_test_id"]}')
                self._nl()
        else:
            self.stdout.write(self.style.SUCCESS(
                f'  [+] SPAM:   No messages found in Spam'
            ))

        # Overall verdict
        self._nl()
        if inbox_found and not spam_found:
            self.stdout.write(self.style.SUCCESS(
                '  [+] VERDICT: Email terkirim ke INBOX (delivered to inbox)'
            ))
        elif inbox_found and spam_found:
            self.stdout.write(self.style.WARNING(
                '  [!] VERDICT: Email ditemukan di INBOX dan SPAM (check manually)'
            ))
        elif not inbox_found and spam_found:
            self.stdout.write(self.style.ERROR(
                '  [-] VERDICT: Email MASUK SPAM! Periksa pengaturan pengirim (SPF, DKIM, DMARC)'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                '  [?] VERDICT: Email tidak ditemukan. Mungkin belum terkirim atau berbeda folder.'
            ))

        self.stdout.write(self.style.MIGRATE_HEADING(
            '+----------------------------------------------------------------+'
        ))

    def _print_instructions(self):
        """Print instructions for setting up IMAP audit."""
        self._nl()
        self.stdout.write(self.style.MIGRATE_HEADING('IMAP CONFIGURATION GUIDE'))
        self.stdout.write('')
        self.stdout.write('  To check Gmail Inbox vs Spam, add to your .env file:')
        self.stdout.write('')
        self.stdout.write('    IMAP_HOST=imap.gmail.com')
        self.stdout.write('    IMAP_PORT=993')
        self.stdout.write('    IMAP_USER=your-email@gmail.com')
        self.stdout.write('    IMAP_PASSWORD=your-app-password')
        self.stdout.write('')
        self.stdout.write('  Generate Gmail App Password at:')
        self.stdout.write('    https://myaccount.google.com/apppasswords')
        self.stdout.write('')
        self.stdout.write('  Then run:')
        self.stdout.write('    python manage.py check_inbox --email recipient@gmail.com')
        self.stdout.write('')
        self.stdout.write('  To search for a specific test:')
        self.stdout.write('    python manage.py check_inbox --test-id ABC123')

    def _nl(self):
        self.stdout.write('')

    @staticmethod
    def _print_setting(name: str, value: str) -> None:
        label = f'{name:.<32}'
        print(f'  {label} {value}')
