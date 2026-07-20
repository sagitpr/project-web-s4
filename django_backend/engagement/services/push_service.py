"""
Push Notification Service for Engagement Engine.
Supports Firebase Cloud Messaging (FCM) for Android,
Web Push for PWA/browsers, and future APNs for iOS.

Uses the existing notification infrastructure for WebSocket delivery
and extends with FCM HTTP v1 API for mobile push.
"""

import json
import logging
from typing import Optional, Dict, List, Any
from django.utils import timezone
from django.conf import settings

from engagement.models import DeviceToken

logger = logging.getLogger(__name__)


class PushNotificationService:
    """
    Multi-platform push notification delivery service.
    Supports FCM, Web Push, and in-app WebSocket delivery.
    """

    def __init__(self):
        self.fcm_enabled = bool(getattr(settings, 'FCM_SERVER_KEY', '') or 
                                 getattr(settings, 'FCM_CREDENTIALS', None))
        self.web_push_enabled = bool(getattr(settings, 'VAPID_PUBLIC_KEY', '') and
                                      getattr(settings, 'VAPID_PRIVATE_KEY', ''))

    def send_push(
        self,
        user,
        title: str,
        body: str,
        action_url: str = '',
        data: Dict = None,
        icon: str = '',
        image_url: str = '',
        badge_count: int = None,
        ttl_seconds: int = 86400,
    ) -> bool:
        """
        Send push notification to all active devices of a user.
        Returns True if at least one device received the notification.
        """
        data = data or {}
        active_tokens = DeviceToken.objects.filter(user=user, is_active=True)
        
        if not active_tokens.exists():
            # Fall back to in-app notification
            return self._send_in_app_fallback(user, title, body, action_url)

        success_count = 0
        for token in active_tokens:
            try:
                if token.platform == 'fcm_android':
                    success = self._send_fcm(token.token, title, body, data, icon, image_url, ttl_seconds)
                elif token.platform == 'web_push':
                    success = self._send_web_push(token.token, title, body, data, icon)
                elif token.platform == 'fcm_ios':
                    success = self._send_fcm(token.token, title, body, data, icon, image_url, ttl_seconds, is_ios=True)
                else:
                    # Fallback to FCM
                    success = self._send_fcm(token.token, title, body, data, icon, image_url, ttl_seconds)

                if success:
                    success_count += 1
                    token.last_used_at = timezone.now()
                    token.save(update_fields=['last_used_at'])
                else:
                    # Mark token as potentially inactive
                    token.is_active = False
                    token.save(update_fields=['is_active'])

            except Exception as e:
                logger.warning('Failed to send push to token %s...: %s', token.token[:20], e)

        also_sent_in_app = self._send_in_app_fallback(user, title, body, action_url)

        return success_count > 0 or also_sent_in_app

    def register_device_token(
        self,
        user,
        token: str,
        platform: str,
        device_name: str = '',
        device_id: str = '',
        app_version: str = '',
    ) -> DeviceToken:
        """Register or update a device token for push notifications."""
        device_token, created = DeviceToken.objects.update_or_create(
            token=token,
            platform=platform,
            defaults={
                'user': user,
                'device_name': device_name or '',
                'device_id': device_id or '',
                'app_version': app_version or '',
                'is_active': True,
                'last_used_at': timezone.now(),
            }
        )
        return device_token

    def unregister_device_token(self, token: str, platform: str = None):
        """Mark a device token as inactive."""
        filters = {'token': token}
        if platform:
            filters['platform'] = platform

        DeviceToken.objects.filter(**filters).update(is_active=False)

    def broadcast_to_all(self, title: str, body: str, data: Dict = None,
                          platform: str = None):
        """Broadcast notification to all active devices (admin use)."""
        tokens = DeviceToken.objects.filter(is_active=True)
        if platform:
            tokens = tokens.filter(platform=platform)

        for token in tokens.iterator():
            try:
                self.send_push(
                    user=token.user,
                    title=title,
                    body=body,
                    data=data,
                )
            except Exception as e:
                logger.warning('Broadcast failed for token %s: %s', token.id, e)

    def _send_fcm(self, token: str, title: str, body: str, data: Dict,
                   icon: str = '', image_url: str = '', ttl_seconds: int = 86400,
                   is_ios: bool = False) -> bool:
        """Send notification via Firebase Cloud Messaging HTTP v1 API."""
        fcm_server_key = getattr(settings, 'FCM_SERVER_KEY', '')
        if not fcm_server_key:
            logger.debug('FCM not configured, skipping push delivery')
            return False

        import requests

        # Build FCM message
        message = {
            'to': token,
            'notification': {
                'title': title,
                'body': body,
            },
            'data': {
                'click_action': 'FLUTTER_NOTIFICATION_CLICK',
                **{str(k): str(v) for k, v in data.items()},
            },
            'android': {
                'priority': 'high',
                'ttl': f'{ttl_seconds}s',
                'notification': {
                    'channel_id': 'warungio_engagement',
                    'priority': 'high',
                    'default_sound': True,
                    'default_vibrate_timings': True,
                },
            },
            'apns': {
                'headers': {
                    'apns-priority': '10',
                },
                'payload': {
                    'aps': {
                        'alert': {
                            'title': title,
                            'body': body,
                        },
                        'sound': 'default',
                        'badge': data.get('badge', 1),
                        'content-available': 1,
                    },
                },
            },
        }

        if icon:
            message['notification']['icon'] = icon
            message['android']['notification']['icon'] = icon

        if image_url:
            message['notification']['image'] = image_url
            message['android']['notification']['image'] = image_url

        # URL in data payload
        if data.get('action_url'):
            message['data']['url'] = data['action_url']

        try:
            resp = requests.post(
                'https://fcm.googleapis.com/fcm/send',
                json=message,
                headers={
                    'Authorization': f'key={fcm_server_key}',
                    'Content-Type': 'application/json',
                },
                timeout=10,
            )

            if resp.status_code == 200:
                result = resp.json()
                if result.get('success', 0) >= 1:
                    return True
                elif result.get('failure', 0) >= 1:
                    error = result.get('results', [{}])[0].get('error', 'unknown')
                    if error in ('NotRegistered', 'InvalidRegistration'):
                        logger.info('FCM token invalid, will deactivate')
                    return False
                return False
            else:
                logger.warning('FCM API error %s: %s', resp.status_code, resp.text[:200])
                return False

        except Exception as e:
            logger.warning('FCM request failed: %s', e)
            return False

    def _send_web_push(self, endpoint: str, title: str, body: str,
                        data: Dict, icon: str = '') -> bool:
        """Send Web Push notification (PWA/browser)."""
        vapid_public = getattr(settings, 'VAPID_PUBLIC_KEY', '')
        vapid_private = getattr(settings, 'VAPID_PRIVATE_KEY', '')

        if not vapid_public or not vapid_private:
            logger.debug('Web Push not configured (VAPID keys missing)')
            return False

        try:
            from pywebpush import webpush, WebPushException

            payload = json.dumps({
                'title': title,
                'body': body,
                'icon': icon or '/static/img/warungio-icon.png',
                'badge': '/static/img/warungio-badge.png',
                'data': data,
                'requireInteraction': True,
                'vibrate': [200, 100, 200],
            })

            webpush(
                subscription_info=json.loads(endpoint),
                data=payload,
                vapid_private_key=vapid_private,
                vapid_claims={
                    'sub': 'mailto:admin@warungio.com',
                    'aud': endpoint.split('/')[2] if '://' in endpoint else 'https://warungio.com',
                },
                ttl=86400,
            )
            return True

        except WebPushException as e:
            if e.response and e.response.status_code in (404, 410):
                logger.info('Web Push endpoint expired')
                return False
            logger.warning('Web Push failed: %s', e)
            return False
        except ImportError:
            logger.debug('pywebpush not installed')
            return False
        except Exception as e:
            logger.warning('Web Push error: %s', e)
            return False

    def _send_in_app_fallback(self, user, title: str, body: str,
                                action_url: str = '',
                                data: dict = None) -> bool:
        """Send in-app notification as fallback when push is unavailable."""
        data = data or {}
        try:
            from notifications.services import create_notification

            create_notification(
                user_id=user.id,
                notification_type='engagement',
                priority='medium' if not action_url else 'high',
                title=title,
                description=body,
                action_url=action_url,
                action_text='Lihat Detail',
                metadata={
                    'source': 'engagement_engine',
                    'psychological_trigger': data.get('psychological_trigger', ''),
                    'ai_generated': data.get('ai_generated', False),
                },
                send_ws=True,
            )
            return True
        except Exception as e:
            logger.warning('In-app fallback failed: %s', e)
            return False


# Singleton
_push_service = None


def get_push_service() -> PushNotificationService:
    global _push_service
    if _push_service is None:
        _push_service = PushNotificationService()
    return _push_service
