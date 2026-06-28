"""
WebSocket consumer for Bantuan & Chat support.
Real-time chat between users and customer service admins.
"""

import json
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import SupportConversation, SupportMessage

User = get_user_model()


class SupportChatConsumer(AsyncWebsocketConsumer):
    """Real-time support chat WebSocket consumer."""

    async def connect(self):
        self.user = self.scope['user']
        self.room_group_name = 'support_chat'

        # Allow anonymous users to connect (guest support chat)
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Send welcome message
        await self.send(text_data=json.dumps({
            'type': 'system',
            'content': 'Terhubung ke layanan chat Warungio. Silakan kirim pesan Anda.',
            'timestamp': datetime.now().isoformat(),
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type', 'message')

        if msg_type == 'message':
            await self.handle_message(data)
        elif msg_type == 'typing':
            await self.handle_typing(data)

    async def handle_message(self, data):
        content = data.get('content', '').strip()
        if not content:
            return

        sender_name = 'Anda'
        if self.user.is_authenticated:
            sender_name = self.user.full_name or self.user.email

        # Save message to database (create conversation if needed)
        message_data = await self.save_message(content)

        # Broadcast to support chat group
        if message_data:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'support_message',
                    'message': message_data,
                    'sender_id': self.user.id if self.user.is_authenticated else None,
                    'sender_name': sender_name,
                }
            )

    async def handle_typing(self, data):
        is_typing = data.get('is_typing', False)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'is_typing': is_typing,
                'user_id': self.user.id if self.user.is_authenticated else None,
            }
        )

    async def support_message(self, event):
        """Send chat message to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
        }))

    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'is_typing': event['is_typing'],
        }))

    @database_sync_to_async
    def save_message(self, content):
        """Save support message to database."""
        try:
            conversation, _ = SupportConversation.objects.get_or_create(
                is_active=True,
                defaults={'subject': 'Chat Bantuan'}
            )
            message = SupportMessage.objects.create(
                conversation=conversation,
                sender=self.user if self.user.is_authenticated else None,
                content=content,
                is_from_user=not self.user.is_staff,
            )
            return {
                'id': message.id,
                'content': message.content,
                'created_at': message.created_at.isoformat(),
                'is_from_user': message.is_from_user,
            }
        except Exception:
            return None
