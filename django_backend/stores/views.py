"""
Stores views for Warungio Marketplace.
"""

from django.db import transaction
from rest_framework import status, generics, permissions, views, filters
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Store, StoreFollower, StoreCategory
from .serializers import (
    StoreListSerializer, StoreDetailSerializer, StoreCreateSerializer,
    StoreUpdateSerializer, StoreFollowerSerializer, StoreCategorySerializer
)
from accounts.permissions import IsSeller, IsStoreOwner
from drf_spectacular.utils import extend_schema


class StoreCategoryListView(generics.ListAPIView):
    """List all store categories."""
    queryset = StoreCategory.objects.filter(is_active=True)
    serializer_class = StoreCategorySerializer
    permission_classes = (permissions.AllowAny,)


class StoreListView(generics.ListAPIView):
    """List all active stores with search and filter."""
    queryset = Store.objects.filter(status='active')
    serializer_class = StoreListSerializer
    permission_classes = (permissions.AllowAny,)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['city', 'province', 'category']
    search_fields = ['store_name', 'description', 'city']
    ordering_fields = ['rating_avg', 'follower_count', 'total_sales', 'created_at']


class StoreDetailView(generics.RetrieveAPIView):
    """Get store detail by ID or slug."""
    queryset = Store.objects.all()
    serializer_class = StoreDetailSerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = 'pk'

    def get_object(self):
        pk = self.kwargs.get('pk')
        slug = self.kwargs.get('slug')
        if slug:
            return Store.objects.get(slug=slug, status='active')
        return super().get_object()


class MyStoreView(generics.RetrieveUpdateAPIView):
    """Get/update current user's store."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return StoreUpdateSerializer
        return StoreDetailSerializer

    def get_object(self):
        store, created = Store.objects.get_or_create(
            user=self.request.user,
            defaults={'store_name': f"Toko {self.request.user.full_name}"}
        )
        return store


class StoreCreateView(generics.CreateAPIView):
    """Create a new store."""
    queryset = Store.objects.all()
    serializer_class = StoreCreateSerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    @transaction.atomic
    def perform_create(self, serializer):
        user = self.request.user
        user.role = 'seller'
        user.save(update_fields=['role'])
        serializer.save(user=user)


@extend_schema(exclude=True)
class StoreFollowView(views.APIView):
    """Follow/unfollow a store."""
    permission_classes = (permissions.IsAuthenticated,)

    @transaction.atomic
    def post(self, request, store_id):
        store = Store.objects.filter(id=store_id, status='active').first()
        if not store:
            return Response({'error': 'Toko tidak ditemukan.'},
                          status=status.HTTP_404_NOT_FOUND)
        
        if store.user == request.user:
            return Response({'error': 'Tidak bisa mengikuti toko sendiri.'},
                          status=status.HTTP_400_BAD_REQUEST)

        follow, created = StoreFollower.objects.get_or_create(
            user=request.user, store=store
        )
        
        if created:
            return Response({'message': 'Berhasil mengikuti toko.', 'is_following': True})
        else:
            follow.delete()
            return Response({'message': 'Berhenti mengikuti toko.', 'is_following': False})

    def get(self, request, store_id):
        store = Store.objects.filter(id=store_id).first()
        if not store:
            return Response({'error': 'Toko tidak ditemukan.'},
                          status=status.HTTP_404_NOT_FOUND)
        
        is_following = StoreFollower.objects.filter(
            user=request.user, store=store
        ).exists()
        
        return Response({
            'is_following': is_following,
            'count': store.follower_count,
        })


class StoreFollowersView(generics.ListAPIView):
    """List store followers."""
    serializer_class = StoreFollowerSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return StoreFollower.objects.none()

        return StoreFollower.objects.filter(store_id=self.kwargs['store_id'])


@extend_schema(exclude=True)
class RemoveStoreImageView(views.APIView):
    """Remove store logo or banner image (set to null, delete file)."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    @transaction.atomic
    def post(self, request):
        image_type = request.data.get('image_type')  # 'logo' or 'banner'
        if image_type not in ('logo', 'banner'):
            return Response({'error': 'Field image_type harus "logo" atau "banner".'},
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            store = Store.objects.get(user=request.user)
        except Store.DoesNotExist:
            return Response({'error': 'Toko tidak ditemukan.'},
                          status=status.HTTP_404_NOT_FOUND)
        
        if image_type == 'logo':
            if store.store_logo:
                try:
                    storage = store.store_logo.storage
                    if storage.exists(store.store_logo.name):
                        storage.delete(store.store_logo.name)
                except Exception:
                    pass
                store.store_logo = None
                store.save(update_fields=['store_logo'])
            return Response({'message': 'Logo toko berhasil dihapus.'})
        
        elif image_type == 'banner':
            if store.store_banner:
                try:
                    storage = store.store_banner.storage
                    if storage.exists(store.store_banner.name):
                        storage.delete(store.store_banner.name)
                except Exception:
                    pass
                store.store_banner = None
                store.save(update_fields=['store_banner'])
            return Response({'message': 'Banner toko berhasil dihapus.'})


@extend_schema(exclude=True)
class MyFollowedStoresView(generics.ListAPIView):
    """List stores the current user follows."""
    serializer_class = StoreListSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Store.objects.filter(
            followers__user=self.request.user,
            status='active'
        ).select_related('user').order_by('store_name')
