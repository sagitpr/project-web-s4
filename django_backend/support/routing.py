"""
WebSocket routing for support/help-center chat consumers.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/support/chat/$', consumers.SupportChatConsumer.as_asgi()),
]
