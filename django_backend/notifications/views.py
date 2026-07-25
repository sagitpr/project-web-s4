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
    NotificationPreferenceSerializer, NotificationCountSerializer
)


class NotificationListView(generics.ListAPIView):
    """List user notifications."""
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
        
        # Filter read/unread
        unread = self.request.query_params.get('unread')
        if unread == 'true':
            qs = qs.filter(is_read=False)
        elif unread == 'false':
            qs = qs.filter(is_read=True)
        
        return qs.order_by('-created_at')[:50]


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
    """Get unread notification count."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        # Single annotated query — replaces 6 separate COUNT queries
        qs = Notification.objects.filter(
            user=request.user, is_read=False
        )
        
        # Get total + per-type counts in one query using aggregation
        counts = qs.aggregate(
            total_unread=Count('id'),
            order_unread=Count('id', filter=Q(notification_type='order')),
            payment_unread=Count('id', filter=Q(notification_type='payment')),
            chat_unread=Count('id', filter=Q(notification_type='chat')),
            promo_unread=Count('id', filter=Q(notification_type='promo')),
            system_unread=Count('id', filter=Q(notification_type='system')),
        )
        
        return Response({
            'total_unread': counts['total_unread'],
            'order_unread': counts['order_unread'],
            'payment_unread': counts['payment_unread'],
            'chat_unread': counts['chat_unread'],
            'promo_unread': counts['promo_unread'],
            'system_unread': counts['system_unread'],
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
