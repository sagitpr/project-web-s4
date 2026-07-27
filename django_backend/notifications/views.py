"""
Notifications views for Warungio Marketplace.
"""

from django.db.models import Count, Q
from rest_framework import status, generics, permissions, views
from rest_framework.response import Response

from .models import Notification, NotificationPreference
from drf_spectacular.utils import extend_schema
from .serializers import (
    NotificationSerializer, NotificationMarkReadSerializer,
    NotificationPreferenceSerializer, NotificationCountSerializer,
    NotificationArchiveSerializer, NotificationBroadcastSerializer,
)
from .services import create_notification, broadcast_notification


class NotificationListView(generics.ListAPIView):
    """List user notifications with search, filter, and pagination."""
    serializer_class = NotificationSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()

        qs = Notification.objects.filter(user=self.request.user).select_related('user')
        
        # Filter by type
        ntype = self.request.query_params.get('type')
        if ntype:
            qs = qs.filter(notification_type=ntype)
        
        # Filter by priority
        priority = self.request.query_params.get('priority')
        if priority:
            qs = qs.filter(priority=priority)
        
        # Filter read/unread
        unread = self.request.query_params.get('unread')
        if unread == 'true':
            qs = qs.filter(is_read=False)
        elif unread == 'false':
            qs = qs.filter(is_read=True)
        
        # Filter archived
        archived = self.request.query_params.get('archived')
        if archived == 'true':
            qs = qs.filter(is_archived=True)
        else:
            qs = qs.filter(is_archived=False)
        
        # Search in title + description
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Pagination
        page_size = int(self.request.query_params.get('pageSize', 50))
        page = int(self.request.query_params.get('page', 1))
        offset = (page - 1) * page_size
        
        return qs.order_by('-created_at')[offset:offset + page_size]


@extend_schema(exclude=True)
class NotificationMarkReadView(views.APIView):
    """Mark notifications as read."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = NotificationMarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if serializer.validated_data.get('mark_all'):
            Notification.objects.filter(
                user=request.user, is_read=False
            ).update(is_read=True)
            return Response({'message': 'Semua notifikasi ditandai sudah dibaca.'})
        
        notification_ids = serializer.validated_data.get('notification_ids', [])
        if notification_ids:
            Notification.objects.filter(
                id__in=notification_ids,
                user=request.user
            ).update(is_read=True)
        
        return Response({'message': f'{len(notification_ids)} notifikasi ditandai sudah dibaca.'})


@extend_schema(exclude=True)
class NotificationUnreadCountView(views.APIView):
    """Get unread notification count with per-type breakdown."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        qs = Notification.objects.filter(
            user=request.user, is_read=False, is_archived=False
        )
        
        # Get total + per-type counts in one query using aggregation
        counts = qs.aggregate(
            total_unread=Count('id'),
            order_unread=Count('id', filter=Q(notification_type='order')),
            payment_unread=Count('id', filter=Q(notification_type='payment')),
            chat_unread=Count('id', filter=Q(notification_type='chat')),
            promo_unread=Count('id', filter=Q(notification_type='promo')),
            system_unread=Count('id', filter=Q(notification_type='system')),
            inventory_unread=Count('id', filter=Q(notification_type='inventory')),
            security_unread=Count('id', filter=Q(notification_type='security')),
            delivery_unread=Count('id', filter=Q(notification_type='delivery')),
            wallet_unread=Count('id', filter=Q(notification_type='wallet')),
            loyalty_unread=Count('id', filter=Q(notification_type='loyalty')),
            ai_scan_unread=Count('id', filter=Q(notification_type='ai_scan')),
        )
        
        return Response({
            'total_unread': counts['total_unread'],
            'order_unread': counts['order_unread'],
            'payment_unread': counts['payment_unread'],
            'chat_unread': counts['chat_unread'],
            'promo_unread': counts['promo_unread'],
            'system_unread': counts['system_unread'],
            'inventory_unread': counts['inventory_unread'],
            'security_unread': counts['security_unread'],
            'delivery_unread': counts['delivery_unread'],
            'wallet_unread': counts['wallet_unread'],
            'loyalty_unread': counts['loyalty_unread'],
            'ai_scan_unread': counts['ai_scan_unread'],
        })


@extend_schema(exclude=True)
class NotificationDeleteView(views.APIView):
    """Delete a single notification."""
    permission_classes = (permissions.IsAuthenticated,)

    def delete(self, request, pk):
        try:
            notification = Notification.objects.get(id=pk, user=request.user)
            notification.delete()
            return Response({'message': 'Notifikasi berhasil dihapus.'}, status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response(
                {'error': 'Notifikasi tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND
            )


class NotificationPreferenceView(generics.RetrieveUpdateAPIView):
    """Get/update notification preferences."""
    serializer_class = NotificationPreferenceSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        obj, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return obj


@extend_schema(exclude=True)
class CreateNotificationView(views.APIView):
    """Create notification (system use)."""
    permission_classes = (permissions.IsAdminUser,)

    def post(self, request):
        user_id = request.data.get('user_id')
        title = request.data.get('title')
        description = request.data.get('description', '')
        notification_type = request.data.get('type', 'system')
        action_url = request.data.get('action_url', '')
        
        notification = Notification.objects.create(
            user_id=user_id,
            title=title,
            description=description,
            notification_type=notification_type,
            action_url=action_url,
        )
        
        return Response(
            NotificationSerializer(notification).data,
            status=status.HTTP_201_CREATED
        )


@extend_schema(exclude=True)
class NotificationArchiveView(views.APIView):
    """Archive or unarchive notifications."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = NotificationArchiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notification_ids = serializer.validated_data.get('notification_ids', [])
        archive = serializer.validated_data.get('archive', True)
        
        if notification_ids:
            Notification.objects.filter(
                id__in=notification_ids,
                user=request.user
            ).update(is_archived=archive)
            action = 'diarsipkan' if archive else 'dipulihkan'
            return Response({
                'message': f'{len(notification_ids)} notifikasi {action}.',
                'archived_count': len(notification_ids),
            })
        
        return Response({'message': 'Tidak ada notifikasi yang dipilih.'}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(exclude=True)
class NotificationDeleteBulkView(views.APIView):
    """Delete multiple notifications at once."""
    permission_classes = (permissions.IsAuthenticated,)

    def delete(self, request):
        notification_ids = request.data.get('notification_ids', [])
        if not notification_ids:
            # Delete all archived notifications
            deleted, _ = Notification.objects.filter(
                user=request.user, is_archived=True
            ).delete()
            return Response({'message': f'Semua notifikasi arsip telah dihapus.', 'deleted_count': deleted})
        
        deleted, _ = Notification.objects.filter(
            id__in=notification_ids,
            user=request.user
        ).delete()
        return Response({'message': f'{deleted} notifikasi dihapus.', 'deleted_count': deleted})


@extend_schema(exclude=True)
class NotificationBroadcastView(views.APIView):
    """Admin: Broadcast notification to users by role."""
    permission_classes = (permissions.IsAdminUser,)

    def post(self, request):
        serializer = NotificationBroadcastSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        title = serializer.validated_data['title']
        description = serializer.validated_data.get('description', '')
        target_role = serializer.validated_data.get('target_role', 'all')
        notification_type = serializer.validated_data.get('notification_type', 'system')
        action_url = serializer.validated_data.get('action_url', '')
        action_text = serializer.validated_data.get('action_text', 'Lihat')
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Build user query based on target
        if target_role == 'all':
            users = User.objects.filter(is_active=True)
        elif target_role in ('buyer', 'seller'):
            users = User.objects.filter(is_active=True, role=target_role)
        elif target_role == 'admin':
            users = User.objects.filter(is_active=True, is_staff=True)
        else:
            return Response({'error': f'Role tidak dikenal: {target_role}'}, status=status.HTTP_400_BAD_REQUEST)
        
        user_count = users.count()
        if user_count == 0:
            return Response({'error': 'Tidak ada pengguna yang sesuai.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create notifications with explicit timestamps for broadcast
        from django.utils import timezone as tz_now
        now = tz_now.now()
        notifications = []
        for user in users.iterator():
            n = Notification(
                user=user,
                title=title,
                description=description,
                notification_type=notification_type,
                priority='info',
                action_url=action_url,
                action_text=action_text,
                metadata={'is_broadcast': True},
                created_at=now,
            )
            notifications.append(n)
        
        # Bulk create (auto_now_add will be overridden by explicit created_at)
        Notification.objects.bulk_create(notifications, batch_size=1000)
        
        # Broadcast via WebSocket to first 100 users (refresh from DB for accurate timestamps)
        first_100_ids = [n.id for n in notifications[:100] if n.id]
        if first_100_ids:
            for n in Notification.objects.filter(id__in=first_100_ids).iterator():
                try:
                    broadcast_notification(n)
                except Exception:
                    pass
        
        return Response({
            'message': f'Notifikasi terkirim ke {user_count} pengguna ({target_role}).',
            'sent_count': user_count,
            'target_role': target_role,
        })
