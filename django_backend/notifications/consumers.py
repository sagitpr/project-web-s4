"""
WebSocket Notification Consumer for Warungio Marketplace.
Real-time push notifications for users.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Notification


class NotificationConsumer(AsyncWebsocketConsumer):
    """Real-time notification WebSocket consumer."""

    async def connect(self):
        self.user = self.scope['user']
        self.store_groups = []  # Initialize before any early return
        if not self.user.is_authenticated:
            await self.close()
            return

        self.group_name = f'notifications_{self.user.id}'

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # Also join store groups for stores the user follows (for product updates)
        self.store_groups = await self.get_followed_store_groups()
        for group in self.store_groups:
            await self.channel_layer.group_add(group, self.channel_name)

        await self.accept()

        # Send unread count on connect
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count,
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        # Leave followed store groups
        for group in self.store_groups:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type', '')

        if msg_type == 'mark_read':
            await self.mark_notification_read(data.get('notification_id'))
        elif msg_type == 'mark_all_read':
            await self.mark_all_read()
        elif msg_type == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))

    async def send_notification(self, event):
        """Send notification to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'id': event.get('id'),
            'notification_type': event.get('notification_type'),
            'title': event.get('title'),
            'description': event.get('description'),
            'priority': event.get('priority', 'medium'),
            'action_url': event.get('action_url'),
            'created_at': event.get('created_at'),
        }))

        # Send updated unread count
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count,
        }))

    async def order_update(self, event):
        """Send order update notification."""
        await self.send(text_data=json.dumps({
            'type': 'order_update',
            'order_id': event.get('order_id'),
            'order_number': event.get('order_number'),
            'status': event.get('status'),
            'message': event.get('message', ''),
        }))

    async def payment_update(self, event):
        """Send payment update notification."""
        await self.send(text_data=json.dumps({
            'type': 'payment_update',
            'order_id': event.get('order_id'),
            'status': event.get('status'),
            'message': event.get('message', ''),
        }))

    async def delivery_update(self, event):
        """Send delivery/tracking update notification."""
        await self.send(text_data=json.dumps({
            'type': 'delivery_update',
            'order_id': event.get('order_id'),
            'order_number': event.get('order_number'),
            'delivery_status': event.get('delivery_status'),
            'tracking_number': event.get('tracking_number'),
            'courier': event.get('courier'),
            'message': event.get('message', ''),
        }))

    @database_sync_to_async
    def get_followed_store_groups(self):
        """Return list of store group names the user follows."""
        from stores.models import StoreFollower
        store_ids = StoreFollower.objects.filter(
            user=self.user
        ).values_list('store_id', flat=True)
        return [f'store_{sid}' for sid in store_ids]

    async def product_created(self, event):
        """Send product created notification."""
        await self.send(text_data=json.dumps({
            'type': 'product_created',
            'product_id': event.get('product_id'),
            'product_name': event.get('product_name'),
            'store_id': event.get('store_id'),
            'action': 'created',
        }))

    async def product_updated(self, event):
        """Send product updated notification."""
        await self.send(text_data=json.dumps({
            'type': 'product_updated',
            'product_id': event.get('product_id'),
            'product_name': event.get('product_name'),
            'store_id': event.get('store_id'),
            'action': 'updated',
        }))

    async def product_status_changed(self, event):
        """Send product status changed (publish/unpublish) notification."""
        await self.send(text_data=json.dumps({
            'type': 'product_status_changed',
            'product_id': event.get('product_id'),
            'product_name': event.get('product_name'),
            'store_id': event.get('store_id'),
            'action': 'status_changed',
        }))

    async def product_deleted(self, event):
        """Send product deleted notification."""
        await self.send(text_data=json.dumps({
            'type': 'product_deleted',
            'product_id': event.get('product_id'),
            'product_name': event.get('product_name'),
            'store_id': event.get('store_id'),
            'action': 'deleted',
        }))

    async def stock_update(self, event):
        """Send real-time stock change notification."""
        await self.send(text_data=json.dumps({
            'type': 'stock_update',
            'product_id': event.get('product_id'),
            'product_name': event.get('product_name'),
            'store_id': event.get('store_id'),
            'stock_change': event.get('stock_change'),
            'action': event.get('action', 'stock_updated'),
        }))

    @database_sync_to_async
    def get_unread_count(self):
        return Notification.objects.filter(
            user=self.user, is_read=False
        ).count()

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        Notification.objects.filter(
            id=notification_id, user=self.user
        ).update(is_read=True)

    @database_sync_to_async
    def mark_all_read(self):
        Notification.objects.filter(
            user=self.user, is_read=False
        ).update(is_read=True)
