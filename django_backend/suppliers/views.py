"""
Supplier views for Warungio Marketplace.
Complete CRUD with Flutter-ready JSON responses.
"""

from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone
from rest_framework import status, generics, permissions, views, filters
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Supplier, SupplierCategory, SupplierProduct, SupplierOrder,
    SupplierOrderItem, SupplierReview, SupplierContract, SupplierPayment
)
from .serializers import (
    SupplierCategorySerializer, SupplierListSerializer, SupplierDetailSerializer,
    SupplierProductSerializer, SupplierProductListSerializer,
    SupplierOrderListSerializer, SupplierOrderDetailSerializer,
    SupplierOrderItemSerializer, SupplierReviewSerializer,
    SupplierContractSerializer, SupplierPaymentSerializer,
    FlutterSupplierDTO, FlutterSupplierProductDTO, FlutterSupplierOrderDTO,
)
from accounts.permissions import IsSeller, IsAdmin
from drf_spectacular.utils import extend_schema, extend_schema_view


# =============================================================================
# CATEGORIES
# =============================================================================

class SupplierCategoryListView(generics.ListAPIView):
    """List all active supplier categories."""
    queryset = SupplierCategory.objects.filter(is_active=True)
    serializer_class = SupplierCategorySerializer
    permission_classes = (permissions.AllowAny,)
    filter_backends = [filters.OrderingFilter]
    ordering = ['sort_order']


class SupplierCategoryDetailView(generics.RetrieveAPIView):
    """Get supplier category detail."""
    queryset = SupplierCategory.objects.filter(is_active=True)
    serializer_class = SupplierCategorySerializer
    permission_classes = (permissions.AllowAny,)


# =============================================================================
# SUPPLIERS
# =============================================================================

class SupplierListView(generics.ListAPIView):
    """List active suppliers with search, filter, pagination."""
    serializer_class = SupplierListSerializer
    permission_classes = (permissions.AllowAny,)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'category': ['exact'],
        'city': ['exact', 'in'],
        'status': ['exact'],
        'verification_level': ['exact'],
        'is_featured': ['exact'],
        'rating_avg': ['gte', 'lte'],
    }
    search_fields = ['supplier_name', 'city', 'description', 'tags']
    ordering_fields = ['rating_avg', '-rating_avg', 'supplier_name', 'created_at', 'total_products_supplied']
    ordering = ['-rating_avg']

    def get_queryset(self):
        return Supplier.objects.filter(is_active=True, status='active').select_related('category')


class SupplierFeaturedView(generics.ListAPIView):
    """List featured/top suppliers."""
    serializer_class = SupplierListSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return Supplier.objects.filter(
            is_active=True, status='active', is_featured=True
        ).select_related('category')[:10]


class SupplierTopRatedView(generics.ListAPIView):
    """List top-rated suppliers."""
    serializer_class = SupplierListSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return Supplier.objects.filter(
            is_active=True, status='active'
        ).select_related('category').order_by('-rating_avg')[:20]


@extend_schema_view(
    get=extend_schema(operation_id='retrieve_supplier_by_pk'),
)
class SupplierDetailView(generics.RetrieveAPIView):
    """Get supplier detail with full info."""
    queryset = Supplier.objects.filter(is_active=True)
    serializer_class = SupplierDetailSerializer
    permission_classes = (permissions.AllowAny,)


class SupplierBySlugView(generics.RetrieveAPIView):
    """Get supplier by slug."""
    queryset = Supplier.objects.filter(is_active=True)
    serializer_class = SupplierDetailSerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = 'slug'


@extend_schema(exclude=True)
class SupplierProductsView(generics.ListAPIView):
    """List products for a specific supplier."""
    serializer_class = SupplierProductListSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Product.objects.none()

        return SupplierProduct.objects.filter(
            supplier_id=self.kwargs['pk'],
            is_active=True, is_available=True
        ).select_related('supplier')


@extend_schema(exclude=True)
class SupplierReviewsView(generics.ListCreateAPIView):
    """List and create reviews for a supplier."""
    serializer_class = SupplierReviewSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_queryset(self):
        return SupplierReview.objects.filter(
            supplier_id=self.kwargs['pk']
        ).select_related('user', 'supplier')

    def perform_create(self, serializer):
        supplier = Supplier.objects.get(id=self.kwargs['pk'])
        serializer.save(user=self.request.user, supplier=supplier)


@extend_schema(exclude=True)
class SupplierContractsView(generics.ListAPIView):
    """List active contracts for a supplier."""
    serializer_class = SupplierContractSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get_queryset(self):
        return SupplierContract.objects.filter(
            supplier_id=self.kwargs['pk']
        ).select_related('supplier')


# =============================================================================
# SUPPLIER PRODUCTS
# =============================================================================

class SupplierProductListView(generics.ListAPIView):
    """List all available supplier products."""
    serializer_class = SupplierProductListSerializer
    permission_classes = (permissions.AllowAny,)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'supplier': ['exact'],
        'category': ['exact'],
        'is_available': ['exact'],
        'unit_price': ['gte', 'lte'],
    }
    search_fields = ['product_name', 'sku', 'supplier__supplier_name']
    ordering_fields = ['unit_price', '-unit_price', 'product_name']

    def get_queryset(self):
        return SupplierProduct.objects.filter(
            is_active=True, supplier__is_active=True
        ).select_related('supplier')


class SupplierProductDetailView(generics.RetrieveAPIView):
    """Get supplier product detail."""
    queryset = SupplierProduct.objects.filter(is_active=True)
    serializer_class = SupplierProductSerializer
    permission_classes = (permissions.AllowAny,)


# =============================================================================
# PURCHASE ORDERS
# =============================================================================

@extend_schema(exclude=True)
class SupplierOrderListCreateView(generics.ListCreateAPIView):
    """List and create purchase orders."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SupplierOrderDetailSerializer
        return SupplierOrderListSerializer

    def get_queryset(self):
        return SupplierOrder.objects.filter(
            store__user=self.request.user
        ).select_related('supplier', 'store').prefetch_related('items')

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            store=self.request.user.store
        )


class SupplierOrderDetailView(generics.RetrieveAPIView):
    """Get purchase order detail."""
    serializer_class = SupplierOrderDetailSerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_queryset(self):
        return SupplierOrder.objects.filter(
            store__user=self.request.user
        ).select_related('supplier', 'store').prefetch_related('items')


@extend_schema(exclude=True)
class SupplierOrderStatusView(views.APIView):
    """Update purchase order status."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request, pk):
        order = SupplierOrder.objects.filter(
            pk=pk, store__user=request.user
        ).first()
        if not order:
            return Response({'error': 'Pesanan tidak ditemukan.'},
                          status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status')
        valid_statuses = ['sent', 'cancelled']
        if new_status not in valid_statuses:
            return Response({'error': 'Status tidak valid.'},
                          status=status.HTTP_400_BAD_REQUEST)

        order.status = new_status
        order.save(update_fields=['status'])
        return Response({
            'message': f'Status pesanan diubah ke {new_status}.',
            'order': SupplierOrderDetailSerializer(order).data,
        })


# =============================================================================
# SUPPLIER MANAGEMENT (for sellers)
# =============================================================================

@extend_schema(exclude=True)
class MySupplierListView(generics.ListAPIView):
    """List suppliers used by the current seller."""
    serializer_class = SupplierListSerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_queryset(self):
        store = self.request.user.store
        # Suppliers whose products have been ordered by this store
        supplier_ids = SupplierOrder.objects.filter(
            store=store
        ).values_list('supplier_id', flat=True).distinct()
        return Supplier.objects.filter(id__in=supplier_ids, is_active=True)


@extend_schema(exclude=True)
class SupplierRegisterView(views.APIView):
    """Register a new supplier (for sellers/admin)."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = SupplierDetailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        supplier = serializer.save()
        return Response({
            'message': 'Supplier berhasil didaftarkan.',
            'supplier': SupplierListSerializer(supplier).data,
        }, status=status.HTTP_201_CREATED)


# =============================================================================
# SEARCH
# =============================================================================

@extend_schema(exclude=True)
class SupplierSearchView(views.APIView):
    """Search suppliers by name, city, category."""
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        if len(q) < 2:
            return Response({'results': [], 'count': 0})

        suppliers = Supplier.objects.filter(
            is_active=True, status='active',
            supplier_name__icontains=q
        ).select_related('category')[:10]

        return Response({
            'count': suppliers.count(),
            'results': SupplierListSerializer(suppliers, many=True).data,
        })


