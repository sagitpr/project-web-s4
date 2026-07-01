"""
Notification service abstraction for Warungio.
Decouples authentication from delivery channels (WhatsApp, Email, Console).
Supports fallback logic: WhatsApp (Primary) -> Email (Fallback) -> Console (Debug).
"""

import logging
from django.conf import settings
from .whatsapp_service import send_whatsapp_otp, _whatsapp_configured
from .email_service import send_otp_email, _email_configured

logger = logging.getLogger('django_backend.accounts.notifications')


class BaseNotificationProvider:
    """Interface for notification delivery channels."""
    def send_otp(self, recipient: str, otp_code: str, purpose: str, user_full_name: str = None) -> dict:
        """
        Send an OTP code to a recipient.
        
        Returns:
            dict: {'success': bool, 'message': str, 'error': str | None}
        """
        raise NotImplementedError("Subclasses must implement send_otp method.")


class WhatsAppNotificationProvider(BaseNotificationProvider):
    """WhatsApp OTP delivery provider."""
    def send_otp(self, recipient: str, otp_code: str, purpose: str, user_full_name: str = None) -> dict:
        logger.info(f"Attempting to send OTP via WhatsApp to {recipient}...")
        return send_whatsapp_otp(
            phone=recipient,
            otp_code=otp_code,
            purpose=purpose,
            user_full_name=user_full_name
        )


class EmailNotificationProvider(BaseNotificationProvider):
    """Email OTP delivery provider."""
    def send_otp(self, recipient: str, otp_code: str, purpose: str, user_full_name: str = None) -> dict:
        logger.info(f"Attempting to send OTP via Email to {recipient}...")
        return send_otp_email(
            email=recipient,
            otp_code=otp_code,
            purpose=purpose,
            user_full_name=user_full_name
        )


class ConsoleNotificationProvider(BaseNotificationProvider):
    """Console/Debug OTP delivery provider for local testing."""
    def send_otp(self, recipient: str, otp_code: str, purpose: str, user_full_name: str = None) -> dict:
        message = (
            f"\n=== [DEV] WARUNGIO OTP CODE ===\n"
            f"Recipient: {recipient}\n"
            f"OTP Code: {otp_code}\n"
            f"Purpose: {purpose}\n"
            f"Greeting Name: {user_full_name or 'N/A'}\n"
            f"================================\n"
        )
        logger.info(message)
        print(message)
        return {
            'success': True,
            'message': 'OTP printed to console.',
            'error': None
        }


class NotificationService:
    """Factory and dispatch manager for Warungio OTP notifications."""
    
    def __init__(self):
        self.whatsapp_provider = WhatsAppNotificationProvider()
        self.email_provider = EmailNotificationProvider()
        self.console_provider = ConsoleNotificationProvider()

    def send_otp(self, identifier: str, otp_code: str, purpose: str = 'registration', user_full_name: str = None) -> dict:
        """
        Dispatch OTP via the configured delivery path:
        1. If identifier is a phone number and WhatsApp is configured, send via WhatsApp.
        2. If identifier is an email and Email is configured, send via Email.
        3. If DEBUG is enabled or provider is unconfigured, fall back to Console.
        4. If primary channel fails, execute fallback to other available channels.
        """
        # Determine if identifier is email or phone number
        is_email = '@' in identifier
        
        # Scenario A: Email routing
        if is_email:
            if _email_configured():
                res = self.email_provider.send_otp(identifier, otp_code, purpose, user_full_name)
                if res.get('success'):
                    return res
                logger.warning(f"Email delivery failed. Fallback to console if DEBUG enabled.")
            
            if settings.DEBUG:
                return self.console_provider.send_otp(identifier, otp_code, purpose, user_full_name)
            
            return {
                'success': False,
                'message': 'Gagal mengirim email OTP. Saluran email tidak siap.',
                'error': 'Email not configured or SMTP failed.'
            }

        # Scenario B: Phone routing
        else:
            if _whatsapp_configured():
                res = self.whatsapp_provider.send_otp(identifier, otp_code, purpose, user_full_name)
                if res.get('success'):
                    logger.info(
                        'WhatsApp OTP sent successfully to %s via %s',
                        identifier, res.get('provider', 'unknown'),
                    )
                    return res
                logger.warning(
                    "WhatsApp delivery via %s failed: %s. Fallback to Email if user email exists.",
                    res.get('provider', 'unknown'),
                    res.get('error'),
                )
                
            # If WhatsApp failed or is not configured, check if we can fall back to Email
            # Note: For views that only pass phone number, we don't have the email address.
            # In those cases, we fall back to Console if DEBUG is True.
            if settings.DEBUG:
                return self.console_provider.send_otp(identifier, otp_code, purpose, user_full_name)

            return {
                'success': False,
                'message': 'Gagal mengirim OTP via WhatsApp. Saluran WhatsApp tidak siap.',
                'error': 'WhatsApp not configured or API call failed.'
            }

# Singleton instance
notification_service = NotificationService()
