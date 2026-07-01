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


class SupplierProductsView(generics.ListAPIView):
    """List products for a specific supplier."""
    serializer_class = SupplierProductListSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return SupplierProduct.objects.filter(
            supplier_id=self.kwargs['pk'],
            is_active=True, is_available=True
        ).select_related('supplier')


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


# =============================================================================
# MOCK DATA — For Flutter Development
# =============================================================================

class MockSupplierListView(views.APIView):
    """Return mock supplier data for Flutter development."""
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        mock_suppliers = [
            {
                'id': 1,
                'supplier_name': 'PT Segar Makmur Abadi',
                'slug': 'pt-segar-makmur-abadi',
                'category': {'id': 1, 'name': 'Sayuran', 'icon': '🥬'},
                'description': 'Supplier sayuran segar langsung dari petani lokal Jawa Barat.',
                'contact_person': 'Bambang Supriyadi',
                'phone': '081234567890',
                'whatsapp': '081234567890',
                'email': 'bambang@segarmakmur.id',
                'city': 'Bandung',
                'province': 'Jawa Barat',
                'rating_avg': 4.8,
                'rating_count': 127,
                'on_time_delivery_rate': 97.5,
                'quality_score': 95,
                'verification_level': 'premium',
                'logo_url': 'https://via.placeholder.com/200?text=Segar+Makmur',
                'banner_url': 'https://via.placeholder.com/1200x400?text=Segar+Makmur+Banner',
                'products_count': 45,
                'lead_time_days': 1,
                'delivery_coverage': ['Bandung', 'Jakarta', 'Bogor', 'Depok', 'Tangerang', 'Bekasi'],
                'payment_terms': '14days',
                'min_order': 500000.00,
                'is_featured': True,
            },
            {
                'id': 2,
                'supplier_name': 'UD Berkah Jaya',
                'slug': 'ud-berkah-jaya',
                'category': {'id': 2, 'name': 'Bahan Pokok', 'icon': '🍚'},
                'description': 'Distributor beras, minyak, gula dan sembako lainnya.',
                'contact_person': 'Siti Rahmawati',
                'phone': '087654321098',
                'whatsapp': '087654321098',
                'email': 'siti@berkahjaya.com',
                'city': 'Jakarta',
                'province': 'DKI Jakarta',
                'rating_avg': 4.5,
                'rating_count': 89,
                'on_time_delivery_rate': 92.0,
                'quality_score': 88,
                'verification_level': 'verified',
                'logo_url': 'https://via.placeholder.com/200?text=Berkah+Jaya',
                'banner_url': 'https://via.placeholder.com/1200x400?text=Berkah+Jaya+Banner',
                'products_count': 120,
                'lead_time_days': 2,
                'delivery_coverage': ['Jakarta', 'Bogor', 'Depok', 'Tangerang', 'Bekasi'],
                'payment_terms': '30days',
                'min_order': 1000000.00,
                'is_featured': True,
            },
            {
                'id': 3,
                'supplier_name': 'Tani Mandiri Group',
                'slug': 'tani-mandiri-group',
                'category': {'id': 3, 'name': 'Buah-buahan', 'icon': '🍎'},
                'description': 'Supplier buah-buahan impor dan lokal berkualitas premium.',
                'contact_person': 'Agus Wibowo',
                'phone': '085678901234',
                'whatsapp': '085678901234',
                'email': 'agus@tanimandiri.co.id',
                'city': 'Malang',
                'province': 'Jawa Timur',
                'rating_avg': 4.2,
                'rating_count': 56,
                'on_time_delivery_rate': 85.0,
                'quality_score': 90,
                'verification_level': 'verified',
                'logo_url': 'https://via.placeholder.com/200?text=Tani+Mandiri',
                'banner_url': 'https://via.placeholder.com/1200x400?text=Tani+Mandiri+Banner',
                'products_count': 78,
                'lead_time_days': 3,
                'delivery_coverage': ['Jawa Timur', 'Jawa Tengah', 'Jawa Barat', 'Jakarta'],
                'payment_terms': '7days',
                'min_order': 250000.00,
                'is_featured': False,
            },
        ]
        return Response({
            'count': len(mock_suppliers),
            'results': mock_suppliers,
            'meta': {
                'api_version': '1.0.0',
                'source': 'mock',
                'note': 'Data dummy untuk pengembangan Flutter. Gunakan endpoint /api/suppliers/ untuk data real.',
            },
        })


class MockSupplierProductListView(views.APIView):
    """Return mock supplier product data for Flutter development."""
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        mock_products = [
            {'id': 1, 'product_name': 'Beras Premium 5kg', 'sku': 'BR-PRM-001', 'category': 'Beras',
             'unit_price': 65000.00, 'unit': 'karung', 'min_order_qty': 10,
             'stock_available': 500, 'is_available': True, 'estimated_delivery_days': 2,
             'supplier_id': 2, 'supplier_name': 'UD Berkah Jaya'},
            {'id': 2, 'product_name': 'Minyak Goreng 1L', 'sku': 'MNY-001', 'category': 'Minyak',
             'unit_price': 18000.00, 'unit': 'dus', 'min_order_qty': 20,
             'stock_available': 1000, 'is_available': True, 'estimated_delivery_days': 1,
             'supplier_id': 2, 'supplier_name': 'UD Berkah Jaya'},
            {'id': 3, 'product_name': 'Bayam Hijau Segar', 'sku': 'SYR-BYM-001', 'category': 'Sayuran',
             'unit_price': 3500.00, 'unit': 'ikat', 'min_order_qty': 50,
             'stock_available': 200, 'is_available': True, 'estimated_delivery_days': 1,
             'supplier_id': 1, 'supplier_name': 'PT Segar Makmur Abadi'},
            {'id': 4, 'product_name': 'Apel Malang 1kg', 'sku': 'BUA-APL-001', 'category': 'Buah',
             'unit_price': 28000.00, 'unit': 'kg', 'min_order_qty': 10,
             'stock_available': 150, 'is_available': True, 'estimated_delivery_days': 3,
             'supplier_id': 3, 'supplier_name': 'Tani Mandiri Group'},
            {'id': 5, 'product_name': 'Gula Pasir 1kg', 'sku': 'GLP-001', 'category': 'Sembako',
             'unit_price': 15000.00, 'unit': 'karung', 'min_order_qty': 20,
             'stock_available': 800, 'is_available': True, 'estimated_delivery_days': 2,
             'supplier_id': 2, 'supplier_name': 'UD Berkah Jaya'},
        ]
        return Response({
            'count': len(mock_products),
            'results': mock_products,
            'meta': {
                'api_version': '1.0.0',
                'source': 'mock',
                'note': 'Data dummy untuk pengembangan Flutter.',
            },
        })
