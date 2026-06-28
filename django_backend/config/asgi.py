"""
ASGI config for Warungio Marketplace.
Supports Django Channels for WebSocket real-time features.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Initialize Django ASGI application first to avoid AppRegistryNotReady
# All Django model imports MUST go below this line
django_asgi_app = get_asgi_application()

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from channels.auth import AuthMiddlewareStack
from channels.middleware import BaseMiddleware
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.exceptions import DenyConnection
from chat import routing as chat_routing
from notifications import routing as notification_routing
from analytics import routing as analytics_routing
from support import routing as support_routing


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware that authenticates WebSocket connections
    via JWT token passed as a query parameter (?token=...).
    Falls back to AuthMiddlewareStack (session-based) if no token.
    """
    async def __call__(self, scope, receive, send):
        # Try JWT token from query string first
        query_string = scope.get('query_string', b'').decode()
        params = dict(p.split('=') for p in query_string.split('&') if '=' in p)
        token = params.get('token', None)

        if token:
            try:
                access = AccessToken(token)
                User = get_user_model()
                scope['user'] = await database_sync_to_async(User.objects.get)(id=access['user_id'])
                # Bypass AuthMiddlewareStack — JWT auth replaces session auth
                return await self.inner(scope, receive, send)
            except Exception:
                raise DenyConnection('Token tidak valid.')

        # Fallback to session-based auth (AuthMiddlewareStack)
        return await super().__call__(scope, receive, send)


application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': JWTAuthMiddleware(
        AuthMiddlewareStack(
            URLRouter(
                chat_routing.websocket_urlpatterns +
                notification_routing.websocket_urlpatterns +
                analytics_routing.websocket_urlpatterns +
                support_routing.websocket_urlpatterns
            )
        )
    ),
})
