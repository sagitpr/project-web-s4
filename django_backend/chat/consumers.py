"""
WebSocket Chat Consumer for Warungio Marketplace.
Real-time messaging between buyers and sellers.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Conversation, Message

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """Real-time chat WebSocket consumer."""

    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return

        self.conversation_id = self.scope['url_route']['kwargs'].get('conversation_id')
        self.room_group_name = f'chat_{self.conversation_id}' if self.conversation_id else f'user_{self.user.id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Receive message from WebSocket."""
        data = json.loads(text_data)
        message_type = data.get('type', 'message')

        if message_type == 'message':
            await self.handle_message(data)
        elif message_type == 'mark_read':
            await self.handle_mark_read(data)
        elif message_type == 'typing':
            await self.handle_typing(data)

    async def handle_message(self, data):
        """Handle incoming chat message."""
        content = data.get('content', '')
        conversation_id = data.get('conversation_id')
        receiver_id = data.get('receiver_id')

        if not content or not conversation_id:
            return

        # Save message to database
        message = await self.save_message(
            conversation_id=conversation_id,
            receiver_id=receiver_id,
            content=content
        )

        if message:
            # Send to conversation group
            await self.channel_layer.group_send(
                f'chat_{conversation_id}',
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender_id': self.user.id,
                    'sender_name': self.user.full_name,
                    'conversation_id': conversation_id,
                }
            )

            # Send notification to receiver
            await self.channel_layer.group_send(
                f'user_{receiver_id}',
                {
                    'type': 'notification',
                    'notification_type': 'chat',
                    'title': f'Pesan dari {self.user.full_name}',
                    'description': content[:100],
                    'conversation_id': conversation_id,
                }
            )

    async def handle_mark_read(self, data):
        """Mark messages as read."""
        conversation_id = data.get('conversation_id')
        if conversation_id:
            await self.mark_messages_read(conversation_id)

    async def handle_typing(self, data):
        """Handle typing indicator."""
        conversation_id = data.get('conversation_id')
        is_typing = data.get('is_typing', False)

        await self.channel_layer.group_send(
            f'chat_{conversation_id}',
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'user_name': self.user.full_name,
                'is_typing': is_typing,
            }
        )

    async def chat_message(self, event):
        """Send chat message to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'conversation_id': event['conversation_id'],
        }))

    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'user_name': event['user_name'],
            'is_typing': event['is_typing'],
        }))

    async def notification(self, event):
        """Send notification to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification_type': event['notification_type'],
            'title': event['title'],
            'description': event['description'],
            'conversation_id': event.get('conversation_id'),
        }))

    @database_sync_to_async
    def save_message(self, conversation_id, receiver_id, content):
        """Save message to database."""
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            message = Message.objects.create(
                conversation=conversation,
                sender=self.user,
                receiver_id=receiver_id,
                content=content,
            )
            return {
                'id': message.id,
                'content': message.content,
                'created_at': message.created_at.isoformat(),
            }
        except Conversation.DoesNotExist:
            return None

    @database_sync_to_async
    def mark_messages_read(self, conversation_id):
        """Mark all messages in conversation as read."""
        Message.objects.filter(
            conversation_id=conversation_id,
            receiver=self.user,
            is_read=False
        ).update(is_read=True)


class UserNotificationConsumer(AsyncWebsocketConsumer):
    """Real-time notification consumer for user."""
    
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return

        self.group_name = f'user_{self.user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        # Handle pings or other client messages
        if data.get('type') == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))

    async def notification(self, event):
        """Send notification to user."""
        await self.send(text_data=json.dumps(event))
