"""
Products views for Warungio Marketplace.
"""

from rest_framework import status, generics, permissions, views, filters
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Category, Product, Review, Favorite, Promo, RecentlyViewed, Voucher, QualityCheck
from stores.models import Store
from .serializers import (
    CategorySerializer, ProductListSerializer, ProductDetailSerializer,
    ProductCreateSerializer, ProductUpdateSerializer,
    ReviewSerializer, FavoriteSerializer, PromoSerializer, VoucherSerializer,
    QualityCheckSerializer, RecentlyViewedSerializer,
)
from accounts.permissions import IsSeller, IsStoreOwner
from .services.smart_scan import process_scan
from .services.stock_prediction import StockPredictor, ReorderOptimizer
from notifications.models import Notification


class CategoryListView(generics.ListAPIView):

    """List all product categories."""
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = (permissions.AllowAny,)


class ProductListView(generics.ListAPIView):
    """List products with search, filter, and pagination."""
    serializer_class = ProductListSerializer
    permission_classes = (permissions.AllowAny,)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'category': ['exact'],
        'store': ['exact'],
        'price': ['gte', 'lte', 'exact'],
        'product_status': ['exact'],
        'is_featured': ['exact'],
        'created_at': ['gte', 'lte'],
    }
    search_fields = ['product_name', 'description', 'store__store_name']
    ordering_fields = ['price', 'sold_count', 'rating_avg', 'created_at', 'quality_score']

    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related(
            'store', 'category'
        )


class ProductFeaturedView(generics.ListAPIView):
    """List featured products."""
    serializer_class = ProductListSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return Product.objects.filter(
            is_active=True, is_featured=True
        ).select_related('store', 'category')[:20]


class ProductDetailView(generics.RetrieveAPIView):
    """Get product detail."""
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductDetailSerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = 'pk'


class ProductBySlugView(generics.RetrieveAPIView):
    """Get product by slug."""
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductDetailSerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = 'slug'


class ProductCreateView(generics.CreateAPIView):
    """Create a new product for seller's store."""
    serializer_class = ProductCreateSerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    @transaction.atomic
    def perform_create(self, serializer):
        store = self.request.user.store
        serializer.save(store=store)
        store.product_count = store.products.count()
        store.save(update_fields=['product_count'])


class ProductManageView(generics.RetrieveUpdateDestroyAPIView):
    """Update or delete a product (seller only)."""
    serializer_class = ProductUpdateSerializer
    permission_classes = (permissions.IsAuthenticated, IsStoreOwner)

    def get_queryset(self):
        return Product.objects.filter(store__user=self.request.user)

    @transaction.atomic
    def perform_destroy(self, instance):
        store = instance.store
        super().perform_destroy(instance)
        store.product_count = store.products.filter(is_active=True).count()
        store.save(update_fields=['product_count'])


class StoreProductsView(generics.ListAPIView):
    """List products for a specific store."""
    serializer_class = ProductListSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        store_id = self.kwargs.get('store_id')
        return Product.objects.filter(
            store_id=store_id, is_active=True
        ).select_related('store', 'category')


class MyProductsView(generics.ListAPIView):
    """List current seller's products (manage view)."""
    serializer_class = ProductListSerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_queryset(self):
        return Product.objects.filter(
            store__user=self.request.user
        ).select_related('store', 'category')


class ReviewListView(generics.ListCreateAPIView):
    """List and create reviews for a product."""
    serializer_class = ReviewSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_queryset(self):
        return Review.objects.filter(
            product_id=self.kwargs['product_id']
        ).select_related('user', 'product')

    def perform_create(self, serializer):
        product = Product.objects.get(id=self.kwargs['product_id'])
        serializer.save(user=self.request.user, product=product)


class FavoriteView(views.APIView):
    """Toggle favorite/wishlist for a product."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, product_id):
        product = Product.objects.filter(id=product_id, is_active=True).first()
        if not product:
            return Response({'error': 'Produk tidak ditemukan.'},
                          status=status.HTTP_404_NOT_FOUND)

        favorite, created = Favorite.objects.get_or_create(
            user=request.user, product=product
        )
        
        if created:
            return Response({'message': 'Produk ditambahkan ke favorit.', 'is_favorite': True})
        else:
            favorite.delete()
            return Response({'message': 'Produk dihapus dari favorit.', 'is_favorite': False})

    def get(self, request, product_id):
        is_favorite = Favorite.objects.filter(
            user=request.user, product_id=product_id
        ).exists()
        return Response({'is_favorite': is_favorite})


class MyFavoritesView(generics.ListAPIView):
    """List user's favorite products."""
    serializer_class = FavoriteSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).select_related('product')


class SellerStoreReviewListView(generics.ListAPIView):
    """List all reviews for the seller's store products."""
    serializer_class = ReviewSerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_queryset(self):
        return Review.objects.filter(
            product__store__user=self.request.user
        ).select_related('user', 'product').order_by('-created_at')


class PromoListView(generics.ListAPIView):
    """List active promos."""
    queryset = Promo.objects.filter(is_active=True)
    serializer_class = PromoSerializer
    permission_classes = (permissions.AllowAny,)


class SellerPromoListCreateView(generics.ListCreateAPIView):
    """List and create promos for the seller's store."""
    serializer_class = PromoSerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_queryset(self):
        return Promo.objects.filter(store__user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        store = self.request.user.store
        serializer.save(store=store)


class SellerPromoManageView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a seller promo."""
    serializer_class = PromoSerializer
    permission_classes = (permissions.IsAuthenticated, IsStoreOwner)

    def get_queryset(self):
        return Promo.objects.filter(store__user=self.request.user)


class QualityCheckListView(generics.ListCreateAPIView):
    """List and create quality check results (create restricted to sellers/admins)."""
    serializer_class = QualityCheckSerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_queryset(self):
        qs = QualityCheck.objects.select_related('product__store').all()
        product_id = self.request.query_params.get('product')
        status = self.request.query_params.get('status')
        if product_id:
            qs = qs.filter(product_id=product_id)
        if status:
            qs = qs.filter(quality_status=status)
        return qs


class ProductQualityCheckView(generics.ListAPIView):
    """List quality checks for a specific product."""
    serializer_class = QualityCheckSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return QualityCheck.objects.filter(
            product_id=self.kwargs['product_id']
        ).select_related('product__store').order_by('-checked_at')


class SmartScanView(views.APIView):
    """
    Process a Smart Scan AI product analysis.
    Accepts product ID, scan type, and optional parameters.
    Returns analyzed quality data and persists to QualityCheck.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request):
        product_id = request.data.get('product_id') or request.data.get('product')
        scan_type = request.data.get('scan_type', 'computer_vision')
        options = request.data.get('options', {})

        if not product_id:
            return Response({'error': 'ID produk wajib diisi.'},
                          status=status.HTTP_400_BAD_REQUEST)

        product = Product.objects.filter(id=product_id).first()
        if not product:
            return Response({'error': 'Produk tidak ditemukan.'},
                          status=status.HTTP_404_NOT_FOUND)

        # Process scan via service layer
        result = process_scan(product, scan_type, options)

        # Create QualityCheck record if result is actionable
        quality_status = result.get('quality_status', 'pending')
        freshness_score = result.get('freshness_score', 0)
        ai_result = result.get('ai_result', '')

        # Only persist if not pending (e.g., uncertain OCR needs manual confirmation first)
        if quality_status != 'pending' or scan_type in ('barcode', 'manual'):
            qc = QualityCheck.objects.create(
                product=product,
                freshness_score=freshness_score,
                quality_status=quality_status,
                stock_status='sufficient',
                ai_result=ai_result,
            )

            # Update product quality score if fresh/warning/rejected
            if quality_status in ('fresh', 'normal', 'warning', 'rejected'):
                product.quality_score = freshness_score
                product.save(update_fields=['quality_score'])

            result['quality_check_id'] = qc.id

        result['product'] = {
            'id': product.id,
            'product_name': product.product_name,
            'product_photo': product.product_photo.url if product.product_photo else None,
        }
        result['eligible_for_sale'] = quality_status not in ('rejected', 'pending')

        return Response(result)


class RecentlyViewedView(views.APIView):
    """Record and list recently viewed products.
    
    POST: Record a product view
    GET: List user's recently viewed products (max 20)
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        product_id = request.data.get('product_id')
        if not product_id:
            return Response({'error': 'ID produk wajib diisi.'},
                          status=status.HTTP_400_BAD_REQUEST)

        product = Product.objects.filter(id=product_id, is_active=True).first()
        if not product:
            return Response({'error': 'Produk tidak ditemukan.'},
                          status=status.HTTP_404_NOT_FOUND)

        # Upsert — create or update viewed_at
        recently, created = RecentlyViewed.objects.update_or_create(
            user=request.user,
            product=product,
            defaults={'viewed_at': timezone.now()}
        )
        # Prune old entries beyond 50
        total = RecentlyViewed.objects.filter(user=request.user).count()
        if total > 50:
            old_ids = RecentlyViewed.objects.filter(
                user=request.user
            ).values_list('id', flat=True).order_by('-viewed_at')[50:]
            RecentlyViewed.objects.filter(id__in=list(old_ids)).delete()

        return Response({'message': 'Produk dicatat.', 'viewed_at': recently.viewed_at})

    def get(self, request):
        qs = RecentlyViewed.objects.filter(
            user=request.user
        ).select_related('product__store', 'product__category')[:20]
        serializer = RecentlyViewedSerializer(qs, many=True)
        return Response({'count': len(qs), 'results': serializer.data})


class SearchSuggestionsView(views.APIView):
    """Return autocomplete suggestions for the search bar.
    
    GET ?q=bayam  →  returns product names, store names, category names
    Limited to 5 suggestions per type (15 total).
    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        if len(q) < 1:
            return Response({'suggestions': [], 'products': [], 'stores': [], 'categories': []})

        # Product suggestions
        products = Product.objects.filter(
            is_active=True, product_name__icontains=q
        ).values('id', 'product_name', 'price', 'slug')[:5]

        # Store suggestions
        stores = Store.objects.filter(
            status='active', store_name__icontains=q
        ).values('id', 'store_name', 'slug', 'city')[:5]

        # Category suggestions
        categories = Category.objects.filter(
            is_active=True, category_name__icontains=q
        ).values('id', 'category_name')[:5]

        # Combined flat suggestions list for dropdown
        suggestions = []
        for p in products:
            suggestions.append({
                'type': 'product',
                'label': p['product_name'],
                'value': p['slug'],
                'id': p['id'],
                'subtitle': 'Rp ' + '{:,.0f}'.format(p['price']).replace(',', '.'),
            })
        for s in stores:
            suggestions.append({
                'type': 'store',
                'label': s['store_name'],
                'value': s['slug'],
                'id': s['id'],
                'subtitle': s.get('city', ''),
            })
        for c in categories:
            suggestions.append({
                'type': 'category',
                'label': c['category_name'],
                'value': c['category_name'].lower(),
                'id': c['id'],
            })

        return Response({
            'suggestions': suggestions,
            'products': list(products),
            'stores': list(stores),
            'categories': list(categories),
        })


# =============================================================================
# SMART STOCK PREDICTION
# =============================================================================


class StockPredictionView(views.APIView):
    """Get stock prediction for a specific product.

    Returns AI-powered demand forecast, reorder recommendations,
    safety stock levels, and days-until-stockout analysis.

    Flutter-ready JSON response with full prediction data.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        product_id = request.query_params.get('product_id')
        days_ahead = int(request.query_params.get('days_ahead', 30))
        history_days = int(request.query_params.get('history_days', 90))

        if product_id:
            product = Product.objects.filter(
                id=product_id, store__user=request.user
            ).first()
            if not product:
                return Response({'error': 'Produk tidak ditemukan.'},
                              status=status.HTTP_404_NOT_FOUND)
            predictor = StockPredictor()
            result = predictor.predict_demand(product, days_ahead, history_days)
            return Response(result)

        # Predict for all products
        predictor = StockPredictor(store=request.user.store)
        result = predictor.predict_store_stock(request.user.store, days_ahead)
        return Response(result)


class ReorderSuggestionView(views.APIView):
    """Get reorder suggestions for seller's store.

    Uses EOQ (Economic Order Quantity) to optimize order quantities.
    Returns prioritized list of products needing restock.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        optimizer = ReorderOptimizer(request.user.store)
        suggestions = optimizer.get_reorder_suggestions()
        return Response(suggestions)


class StoreStockForecastView(views.APIView):
    """Get comprehensive stock forecast for the entire store.

    Returns:
    - Summary metrics (total products, low stock count, etc.)
    - Urgent reorder suggestions
    - Demand predictions per product
    - Trend analysis
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        days_ahead = int(request.query_params.get('days_ahead', 30))
        predictor = StockPredictor(store=request.user.store)
        result = predictor.predict_store_stock(request.user.store, days_ahead)
        return Response({
            **result,
            'recommendations': {
                'message': 'Gunakan endpoint /api/products/reorder-suggestions/ untuk rekomendasi pemesanan detail.',
                'endpoint': '/api/products/reorder-suggestions/',
            },
            'meta': {
                'api_version': '1.0.0',
                'note': 'Data dummy untuk pengembangan Flutter. Gunakan produk dengan data penjualan untuk hasil akurat.',
            },
        })


class MockStockPredictionView(views.APIView):
    """Mock stock prediction data for Flutter development."""
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        from datetime import datetime, timedelta
        today = timezone.now().date()
        return Response({
            'store_id': 1,
            'store_name': 'Warung Makmur',
            'total_products': 45,
            'low_stock_count': 12,
            'out_of_stock_count': 3,
            'predictions': [
                {
                    'product_id': 1,
                    'product_name': 'Beras Premium 5kg',
                    'current_stock': 12,
                    'unit': 'karung',
                    'status': 'sufficient_data',
                    'predicted_daily_demand': 3.5,
                    'predicted_monthly_demand': 105.0,
                    'confidence_score': 0.85,
                    'safety_stock': 8,
                    'reorder_point': 15,
                    'recommended_reorder_qty': 50,
                    'days_until_stockout': 3.4,
                    'trend_direction': 'up',
                    'trend_factor': 0.12,
                    'avg_daily_sales': 3.2,
                    'lead_time_days': 3,
                },
                {
                    'product_id': 2,
                    'product_name': 'Minyak Goreng 1L',
                    'current_stock': 5,
                    'unit': 'dus',
                    'status': 'sufficient_data',
                    'predicted_daily_demand': 8.2,
                    'predicted_monthly_demand': 246.0,
                    'confidence_score': 0.92,
                    'safety_stock': 15,
                    'reorder_point': 25,
                    'recommended_reorder_qty': 100,
                    'days_until_stockout': 0.6,
                    'trend_direction': 'up',
                    'trend_factor': 0.25,
                    'avg_daily_sales': 7.8,
                    'lead_time_days': 2,
                },
            ],
            'generated_at': timezone.now().isoformat(),
            'meta': {
                'api_version': '1.0.0',
                'source': 'mock',
            },
        })


class LowStockProductsView(views.APIView):
    """List low stock and out-of-stock products for the seller.
    
    Returns products where stock ≤ 5 (low) or stock = 0 (out).
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        threshold = int(request.query_params.get('threshold', 5))
        qs = Product.objects.filter(
            store__user=request.user,
            stock__lte=threshold,
            is_active=True,
        ).select_related('category').order_by('stock')

        low_stock = []
        out_of_stock = []
        for p in qs:
            item = {
                'id': p.id,
                'product_name': p.product_name,
                'stock': p.stock,
                'unit': p.unit,
                'price': float(p.price),
                'category': p.category.category_name if p.category else None,
                'product_photo': p.product_photo.url if p.product_photo else None,
                'slug': p.slug,
            }
            if p.stock <= 0:
                out_of_stock.append(item)
            else:
                low_stock.append(item)

        # Auto-create notifications for seller
        combined = low_stock + out_of_stock
        for item in combined:
            ntype = 'stok_habis' if item['stock'] <= 0 else 'stok_rendah'
            title = f"{item['product_name']} — {'Stok Habis' if item['stock'] <= 0 else 'Stok Rendah'}"
            desc = f"Stok {item['product_name']}: {item['stock']} {item.get('unit', 'pcs')}. "
            desc += "Segera lakukan restock!" if item['stock'] <= 0 else "Segera tambah stok."
            Notification.objects.get_or_create(
                user=request.user,
                notification_type=ntype,
                title=title,
                defaults={
                    'description': desc,
                    'action_url': f"/seller/products/?highlight={item['id']}",
                    'action_text': 'Lihat Produk',
                    'priority': 'high' if item['stock'] <= 0 else 'medium',
                }
            )

        return Response({
            'count': len(combined),
            'low_stock': low_stock,
            'out_of_stock': out_of_stock,
            'total_low_stock': len(low_stock),
            'total_out_of_stock': len(out_of_stock),
        })


class VoucherCheckView(views.APIView):
    """Check if a voucher code is valid."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        code = request.data.get('code', '')
        total = float(request.data.get('total', 0))
        
        voucher = Voucher.objects.filter(
            voucher_code__iexact=code, is_active=True
        ).first()
        
        if not voucher:
            return Response({'valid': False, 'error': 'Kode voucher tidak valid.'})
        
        from django.utils import timezone
        if voucher.expired_date < timezone.now().date():
            return Response({'valid': False, 'error': 'Kode voucher sudah kadaluwarsa.'})
        
        if total < float(voucher.min_purchase):
            return Response({
                'valid': False,
                'error': f'Minimal pembelian Rp {voucher.min_purchase:,.0f}'
            })
        
        return Response({
            'valid': True,
            'discount': float(voucher.discount_amount),
            'code': voucher.voucher_code,
        })
