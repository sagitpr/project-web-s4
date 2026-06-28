"""Subscription views for Warungio Marketplace."""

from rest_framework import generics, permissions, views
from rest_framework.response import Response

from .models import Subscription
from .serializers import SubscriptionSerializer
from accounts.permissions import IsSeller


class SubscriptionListView(generics.ListAPIView):
    """List all subscriptions (admin only)."""
    serializer_class = SubscriptionSerializer
    permission_classes = (permissions.IsAdminUser,)

    def get_queryset(self):
        qs = Subscription.objects.select_related('user', 'store').all()
        status = self.request.query_params.get('status')
        package = self.request.query_params.get('package')
        if status:
            qs = qs.filter(status=status)
        if package:
            qs = qs.filter(package_name=package)
        return qs


class MySubscriptionView(generics.ListAPIView):
    """Get current seller's subscriptions."""
    serializer_class = SubscriptionSerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_queryset(self):
        return Subscription.objects.filter(
            user=self.request.user
        ).select_related('store')


class StoreSubscriptionView(generics.ListAPIView):
    """Get subscriptions for a specific store."""
    serializer_class = SubscriptionSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        store_id = self.kwargs.get('store_id')
        return Subscription.objects.filter(
            store_id=store_id
        ).select_related('user', 'store')


class SubscriptionDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve or update a subscription."""
    serializer_class = SubscriptionSerializer
    permission_classes = (permissions.IsAdminUser,)

    def get_queryset(self):
        return Subscription.objects.select_related('user', 'store').all()


class CheckSubscriptionStatusView(views.APIView):
    """Check if a store has an active subscription."""
    permission_classes = (permissions.AllowAny,)

    def get(self, request, store_id):
        active = Subscription.objects.filter(
            store_id=store_id, status='active'
        ).first()
        if active:
            return Response({
                'has_active_subscription': True,
                'package': active.package_name,
                'end_date': active.end_date,
            })
        return Response({
            'has_active_subscription': False,
        })
