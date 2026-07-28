"""
Products views for Warungio Marketplace.
"""

import os
import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import status, generics, permissions, views, filters
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.core.cache import cache

from .models import Category, Product, ProductGallery, Review, Favorite, Promo, RecentlyViewed, Voucher, QualityCheck
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
from notifications.services import notify_flash_sale_started
from drf_spectacular.utils import extend_schema, extend_schema_view


# =============================================================================
# HELPER: Broadcast product changes via WebSocket to relevant store followers
# =============================================================================

def notify_product_update(store_id, product_id, product_name, action, store_user_id=None):
    """Broadcast product change via WebSocket to:
    1. Store followers (via store_{store_id} group)
    2. Store owner/seller (via notifications_{user_id} group)
    
    Action is one of: 'product_created', 'product_updated', 'product_deleted', 'product_status_changed'
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            event = {
                'type': action,
                'product_id': product_id,
                'product_name': product_name,
                'store_id': store_id,
            }
            # Broadcast to store followers
            async_to_sync(channel_layer.group_send)(
                f'store_{store_id}',
                event
            )
            # Also notify the store owner/seller directly
            if store_user_id:
                async_to_sync(channel_layer.group_send)(
                    f'notifications_{store_user_id}',
                    event
                )
    except Exception as e:
        _log = logging.getLogger('django_backend.products')
        _log.warning('WebSocket broadcast error (product update): %s', str(e))


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


@extend_schema_view(
    get=extend_schema(operation_id='retrieve_product_by_pk'),
)
class ProductDetailView(generics.RetrieveAPIView):
    """Get product detail."""
    queryset = Product.objects.filter(is_active=True).select_related(
        'store', 'category'
    )
    serializer_class = ProductDetailSerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = 'pk'


class ProductBySlugView(generics.RetrieveAPIView):
    """Get product by slug."""
    queryset = Product.objects.filter(is_active=True).select_related(
        'store', 'category'
    )
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
        product = serializer.save(store=store)
        # Handle gallery images (additional photos)
        gallery_files = self.request.FILES.getlist('gallery_images')
        if gallery_files:
            gallery_objs = []
            for idx, f in enumerate(gallery_files):
                ext = os.path.splitext(f.name)[1] if f.name else '.jpg'
                f.name = f"gallery_{product.id}_{idx+1}{ext}"
                gallery_objs.append(ProductGallery(product=product, image=f, order=idx+1))
            ProductGallery.objects.bulk_create(gallery_objs)
        store.product_count = store.products.count()
        store.save(update_fields=['product_count'])
        # Broadcast to store followers and seller
        notify_product_update(store.id, product.id, product.product_name, 'product_created', store.user_id)


class ProductManageView(generics.RetrieveUpdateDestroyAPIView):
    """Update or delete a product (seller only)."""
    serializer_class = ProductUpdateSerializer
    permission_classes = (permissions.IsAuthenticated, IsStoreOwner)

    def get_queryset(self):
        return Product.objects.filter(store__user=self.request.user).select_related(
            'store', 'category'
        )

    @transaction.atomic
    def perform_destroy(self, instance):
        store = instance.store
        product_id = instance.id
        product_name = instance.product_name
        super().perform_destroy(instance)
        store.product_count = store.products.filter(is_active=True).count()
        store.save(update_fields=['product_count'])
        # Broadcast deletion
        notify_product_update(store.id, product_id, product_name, 'product_deleted', store.user_id)

    @transaction.atomic
    def perform_update(self, serializer):
        old_stock = self.get_object().stock  # capture before save
        product = serializer.save()
        # Handle gallery images (additional photos) on update
        gallery_files = self.request.FILES.getlist('gallery_images')
        if gallery_files:
            import os
            # Remove old gallery images
            product.gallery.all().delete()
            gallery_objs = []
            for idx, f in enumerate(gallery_files):
                ext = os.path.splitext(f.name)[1] if f.name else '.jpg'
                f.name = f"gallery_{product.id}_{idx+1}{ext}"
                gallery_objs.append(ProductGallery(product=product, image=f, order=idx+1))
            ProductGallery.objects.bulk_create(gallery_objs)
        store = product.store
        # Detect if stock changed
        if 'stock' in serializer.validated_data:
            stock_change = product.stock - old_stock
            if stock_change != 0:
                from orders.views import notify_stock_update
                notify_stock_update(
                    store_id=store.id,
                    product_id=product.id,
                    product_name=product.product_name,
                    stock_change=stock_change,
                    action='stock_adjusted',
                    store_user_id=store.user_id,
                )
        # Detect if is_active status changed
        if 'is_active' in serializer.validated_data:
            action = 'product_status_changed'
        else:
            action = 'product_updated'
        notify_product_update(store.id, product.id, product.product_name, action, store.user_id)


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
        if getattr(self, "swagger_fake_view", False):
            return Product.objects.none()

        return Product.objects.filter(
            store__user=self.request.user
        ).select_related('store', 'category')


class ReviewListView(generics.ListCreateAPIView):
    """List and create reviews for a product."""
    serializer_class = ReviewSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Review.objects.none()
        return Review.objects.filter(
            product_id=self.kwargs['product_id']
        ).select_related('user', 'product')

    def perform_create(self, serializer):
        product = Product.objects.get(id=self.kwargs['product_id'])
        serializer.save(user=self.request.user, product=product)

        # Broadcast review update via WebSocket to store followers + seller
        notify_product_update(
            store_id=product.store_id,
            product_id=product.id,
            product_name=product.product_name,
            action='product_updated',
            store_user_id=product.store.user_id if product.store else None,
        )


@extend_schema(exclude=True)
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


@extend_schema(exclude=True)
class MyFavoritesView(generics.ListAPIView):
    """List user's favorite products."""
    serializer_class = FavoriteSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).select_related('product')


@extend_schema(exclude=True)
class MyReviewsView(generics.ListAPIView):
    """List reviews written by the authenticated user."""
    serializer_class = ReviewSerializer
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = None

    def get_queryset(self):
        return Review.objects.filter(
            user=self.request.user
        ).select_related('user', 'product').order_by('-created_at')


class ReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a review."""
    serializer_class = ReviewSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        # Users can only manage their own reviews
        return Review.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        review = serializer.save()
        product = review.product
        # Broadcast review update via WebSocket
        if product:
            notify_product_update(
                store_id=product.store_id,
                product_id=product.id,
                product_name=product.product_name,
                action='product_updated',
                store_user_id=product.store.user_id if product.store else None,
            )

    def perform_destroy(self, instance):
        product = instance.product
        super().perform_destroy(instance)
        # Rating cascade handled by Review.delete() → product.update_rating() → store.update_rating_avg()

        # Broadcast review deletion via WebSocket
        notify_product_update(
            store_id=product.store_id,
            product_id=product.id,
            product_name=product.product_name,
            action='product_updated',
            store_user_id=product.store.user_id if product.store else None,
        )


@extend_schema(exclude=True)
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
    serializer_class = PromoSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return Promo.objects.filter(is_active=True).select_related('store')


@extend_schema(exclude=True)
class SellerPromoListCreateView(generics.ListCreateAPIView):
    """List and create promos for the seller's store."""
    serializer_class = PromoSerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_queryset(self):
        return Promo.objects.filter(store__user=self.request.user).select_related(
            'store'
        ).order_by('-created_at')

    def perform_create(self, serializer):
        store = self.request.user.store
        promo = serializer.save(store=store)
        # Send notification for flash sale promos
        try:
            if promo.promo_type == 'flash_sale' or (getattr(promo, 'discount_percentage', 0) or 0) >= 50:
                discount_desc = f"Diskon {promo.discount_percentage}%" if hasattr(promo, 'discount_percentage') and promo.discount_percentage else promo.description or 'Promo Spesial'
                notify_flash_sale_started(
                    store.user_id, promo.promo_name or promo.title or 'Promo',
                    discount_desc, store.store_name
                )
        except Exception as exc:
            _log = logging.getLogger('django_backend.products')
            _log.warning('notify_flash_sale_started failed: %s', exc)


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


@extend_schema(exclude=True)
class ProductQualityCheckView(generics.ListAPIView):
    """List quality checks for a specific product."""
    serializer_class = QualityCheckSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        return QualityCheck.objects.filter(
            product_id=self.kwargs['product_id']
        ).select_related('product__store').order_by('-checked_at')


@extend_schema(exclude=True)
class SmartScanView(views.APIView):
    """
    Process a Smart Scan AI product analysis.
    Synchronous for interactive UX — seller waits ~3-10s for AI result.
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

        # Process scan via service layer (sync — interactive flow)
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


@extend_schema(exclude=True)
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


@extend_schema(exclude=True)
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


@extend_schema(exclude=True)
class StockPredictionView(views.APIView):
    """Get stock prediction for a specific product (cached 15 min + sync fallback).

    Returns AI-powered demand forecast, reorder recommendations,
    safety stock levels, and days-until-stockout analysis.

    Flutter-ready JSON response with full prediction data.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        product_id = request.query_params.get('product_id')
        days_ahead = int(request.query_params.get('days_ahead', 30))
        history_days = int(request.query_params.get('history_days', 90))

        store = request.user.store

        # Check cache first
        if product_id:
            cache_key = f'stock_prediction_{store.id}_{product_id}_{days_ahead}'
        else:
            cache_key = f'stock_prediction_all_{store.id}_{days_ahead}'

        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        # Cache miss — compute sync, then cache for next time
        predictor = StockPredictor(store=store)

        if product_id:
            product = Product.objects.filter(
                id=product_id, store__user=request.user
            ).first()
            if not product:
                return Response({'error': 'Produk tidak ditemukan.'},
                              status=status.HTTP_404_NOT_FOUND)
            result = predictor.predict_demand(product, days_ahead, history_days)
        else:
            result = predictor.predict_store_stock(store, days_ahead)

        cache.set(cache_key, result, 60 * 15)  # 15 min cache
        return Response(result)


@extend_schema(exclude=True)
class ReorderSuggestionView(views.APIView):
    """Get reorder suggestions for seller's store (cached 10 min + sync fallback).

    Uses EOQ (Economic Order Quantity) to optimize order quantities.
    Returns prioritized list of products needing restock.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        store = request.user.store
        cache_key = f'reorder_suggestions_{store.id}'

        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        # Cache miss — compute sync
        optimizer = ReorderOptimizer(store)
        suggestions = optimizer.get_reorder_suggestions()

        cache.set(cache_key, suggestions, 60 * 10)  # 10 min cache
        return Response(suggestions)


@extend_schema(exclude=True)
class StoreStockForecastView(views.APIView):
    """Get comprehensive stock forecast for the entire store (cached 15 min + sync fallback).

    Returns:
    - Summary metrics (total products, low stock count, etc.)
    - Urgent reorder suggestions
    - Demand predictions per product
    - Trend analysis
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        store = request.user.store
        days_ahead = int(request.query_params.get('days_ahead', 30))
        cache_key = f'stock_forecast_{store.id}_{days_ahead}'

        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        # Cache miss — compute sync
        predictor = StockPredictor(store=store)
        result = predictor.predict_store_stock(store, days_ahead)

        cache.set(cache_key, result, 60 * 15)  # 15 min cache
        return Response({
            **result,
            'recommendations': {
                'message': 'Gunakan endpoint /api/products/reorder-suggestions/ untuk rekomendasi pemesanan detail.',
                'endpoint': '/api/products/reorder-suggestions/',
            },
        })





@extend_schema(exclude=True)
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

        # Auto-create notifications for seller — use bulk_create for efficiency
        combined = low_stock + out_of_stock
        existing_titles = set(Notification.objects.filter(
            user=request.user,
            notification_type__in=['stok_habis', 'stok_rendah'],
            title__in=[f"{item['product_name']} — {'Stok Habis' if item['stock'] <= 0 else 'Stok Rendah'}" for item in combined]
        ).values_list('title', flat=True))
        
        new_notifications = []
        for item in combined:
            title = f"{item['product_name']} — {'Stok Habis' if item['stock'] <= 0 else 'Stok Rendah'}"
            if title in existing_titles:
                continue
            ntype = 'stok_habis' if item['stock'] <= 0 else 'stok_rendah'
            desc = f"Stok {item['product_name']}: {item['stock']} {item.get('unit', 'pcs')}. "
            desc += "Segera lakukan restock!" if item['stock'] <= 0 else "Segera tambah stok."
            new_notifications.append(Notification(
                user=request.user,
                notification_type=ntype,
                title=title,
                description=desc,
                action_url=f"/seller/products/?highlight={item['id']}",
                action_text='Lihat Produk',
                priority='high' if item['stock'] <= 0 else 'medium',
            ))
        
        if new_notifications:
            Notification.objects.bulk_create(new_notifications, ignore_conflicts=False)

        return Response({
            'count': len(combined),
            'low_stock': low_stock,
            'out_of_stock': out_of_stock,
            'total_low_stock': len(low_stock),
            'total_out_of_stock': len(out_of_stock),
        })


@extend_schema(exclude=True)
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
