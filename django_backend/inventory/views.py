"""
API views for inventory management.
Barcode lookup, batch entry, FEFO picking, expiry alerts, master product CRUD.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.core.cache import cache
from rest_framework import permissions, status, generics
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsSeller, IsStoreOwner

logger = logging.getLogger(__name__)
from .models import MasterProduct, ProductBatch, InventoryStock, ExpiryNotification, StockAlert
from notifications.services import (
    notify_inventory_low, notify_expired_product,
    notify_ai_scan_complete, notify_stock_prediction, notify_discount_recommendation,
)
from .serializers import (
    MasterProductSerializer,
    MasterProductCreateSerializer,
    BarcodeLookupSerializer,
    BarcodeLookupResultSerializer,
    ProductBatchSerializer,
    BatchCreateSerializer,
    InventoryStockSerializer,
    StockOutSerializer,
    StockOutResultSerializer,
    ExpirySummarySerializer,
    ExpiryNotificationSerializer,
    StockAlertSerializer,
    BatchSummarySerializer,
)
from .services.barcode_lookup import lookup_barcode, validate_barcode_checksum
from .services.fefo_engine import stock_in, stock_out, get_batch_summary, get_expiry_summary
from .services.ai_product_recognition import get_ai_product_recognition_pipeline
from .services.expired_reminder import get_expired_reminder
from drf_spectacular.utils import extend_schema

# ── Cache TTLs ──
LOW_STOCK_CACHE_TTL = 60 * 3  # 3 minutes
EXPIRY_CACHE_TTL = 60 * 5     # 5 minutes


# =============================================================================
# ROOT - API Overview
# =============================================================================


@extend_schema(exclude=True)
class InventoryRootView(APIView):
    """List available inventory API endpoints."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return Response({
            'service': 'Warungio Inventory Management API',
            'version': '2.0.0',
            'endpoints': {
                'master_products': '/api/inventory/master-products/',
                'master_product_detail': '/api/inventory/master-products/<id>/',
                'barcode_lookup': '/api/inventory/barcode-lookup/?barcode=<code>',
                'batches': '/api/inventory/batches/',
                'batch_create': '/api/inventory/batches/create/',
                'expiry_summary': '/api/inventory/expiry/summary/',
                'low_stock_report': '/api/inventory/low-stock-report/',
                'stock_alerts': '/api/inventory/alerts/',
                'stock_out': '/api/inventory/stock-out/',
            },
        })


# =============================================================================
# MASTER PRODUCT
# =============================================================================


class MasterProductSearchView(generics.ListAPIView):
    """Search master product database by name, barcode, or brand."""
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = MasterProductSerializer
    pagination_class = None

    def get_queryset(self):
        q = self.request.query_params.get('q', '').strip()
        if not q:
            return MasterProduct.objects.filter(is_active=True)[:50]
        return MasterProduct.objects.filter(
            Q(product_name__icontains=q) |
            Q(barcode__startswith=q) |
            Q(brand__icontains=q) |
            Q(category__icontains=q),
            is_active=True,
        )[:50]


class MasterProductDetailView(generics.RetrieveAPIView):
    """Get master product details by ID."""
    permission_classes = (permissions.IsAuthenticated,)
    queryset = MasterProduct.objects.filter(is_active=True)
    serializer_class = MasterProductSerializer


class MasterProductCreateView(generics.CreateAPIView):
    """Create a new master product entry."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)
    queryset = MasterProduct.objects.all()
    serializer_class = MasterProductCreateSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = MasterProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        barcode = data.get('barcode', '').strip()

        # Check if barcode already exists
        existing = MasterProduct.objects.filter(barcode=barcode).first()
        if existing:
            return Response({
                'found': True,
                'master_product': {
                    'id': existing.id,
                    'barcode': existing.barcode,
                    'product_name': existing.product_name,
                    'brand': existing.brand,
                    'category': existing.category,
                    'unit': existing.unit,
                },
                'message': 'Produk dengan barcode ini sudah ada.',
            }, status=status.HTTP_200_OK)

        # Validate barcode format
        if not validate_barcode_checksum(barcode):
            return Response({
                'error': 'Format barcode tidak valid.',
                'detail': 'EAN-13 harus 13 digit dengan checksum valid.',
            }, status=status.HTTP_400_BAD_REQUEST)

        master = MasterProduct.objects.create(
            barcode=barcode,
            product_name=data.get('product_name', ''),
            brand=data.get('brand', ''),
            category=data.get('category', 'Umum'),
            subcategory=data.get('subcategory', ''),
            unit=data.get('unit', 'pcs'),
            weight_value=data.get('weight_value'),
            weight_unit=data.get('weight_unit', ''),
            image_url=data.get('image_url', ''),
            manufacturer=data.get('manufacturer', ''),
            bpom_number=data.get('bpom_number', ''),
        )

        return Response({
            'found': True,
            'master_product': {
                'id': master.id,
                'barcode': master.barcode,
                'product_name': master.product_name,
                'brand': master.brand,
                'category': master.category,
                'unit': master.unit,
            },
            'message': 'Master produk berhasil dibuat.',
        }, status=status.HTTP_201_CREATED)


# =============================================================================
# BARCODE LOOKUP
# =============================================================================


@extend_schema(exclude=True)
class BarcodeLookupView(APIView):
    """Look up a product by barcode.

    Checks local MasterProduct DB first, then falls back to
    Open Food Facts API. Auto-creates MasterProduct on first external find.

    Query params:
        barcode (required): 13-digit EAN-13, 8-digit EAN-8, or 12-digit UPC-A
        store_id (optional): For context

    Flutter-ready JSON.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        barcode = request.query_params.get('barcode', '').strip()
        if not barcode:
            return Response(
                {'error': 'Parameter barcode wajib diisi.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        store = None
        store_id = request.query_params.get('store_id')
        if store_id:
            from stores.models import Store
            try:
                store = Store.objects.get(id=int(store_id))
            except (ValueError, Store.DoesNotExist):
                pass

        result = lookup_barcode(barcode, store=store)

        if result.get('found'):
            return Response({
                'found': True,
                'master_product': result.get('master_product'),
                'source': result.get('source', 'local'),
                'is_new': result.get('is_new', False),
            })

        return Response({
            'found': False,
            'error': result.get('error', 'Barcode tidak ditemukan.'),
            'source': result.get('source', 'error'),
        }, status=status.HTTP_404_NOT_FOUND)


# =============================================================================
# BATCH ENTRY
# =============================================================================


@extend_schema(exclude=True)
class BatchCreateView(APIView):
    """Create a new batch with stock-in entry.

    Accepts batch number, production/expiry dates, and quantity.
    Auto-calculates shelf life and status.

    Flutter-ready JSON.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request):
        serializer = BatchCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        store = request.user.store

        master_product = MasterProduct.objects.filter(
            id=data['master_product_id'], is_active=True
        ).first()
        if not master_product:
            return Response(
                {'error': 'Master produk tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Validate expiry > production
        if data['expiry_date'] <= data['production_date']:
            return Response(
                {'error': 'Tanggal kadaluwarsa harus setelah tanggal produksi.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = stock_in(
            store=store,
            master_product=master_product,
            batch_number=data['batch_number'],
            production_date=data['production_date'],
            expiry_date=data['expiry_date'],
            quantity=data['quantity'],
            unit=data.get('unit', 'pcs'),
            purchase_price=data.get('purchase_price'),
            product=None,
            notes=data.get('notes', ''),
            created_by=request.user,
        )

        if result['success']:
            batch = result['batch']
            # Broadcast stock change to followers and seller
            if batch.product:
                try:
                    from orders.views import notify_stock_update
                    notify_stock_update(
                        store_id=store.id,
                        product_id=batch.product.id,
                        product_name=batch.product.product_name,
                        stock_change=float(data['quantity']),
                        action='stock_added',
                        store_user_id=store.user_id,
                    )
                except Exception as exc:
                    logger.warning('Stock broadcast failed for batch create: %s', exc)
            return Response({
                'success': True,
                'batch': {
                    'id': batch.id,
                    'master_product_id': master_product.id,
                    'product_name': master_product.product_name,
                    'batch_number': batch.batch_number,
                    'production_date': batch.production_date.isoformat(),
                    'expiry_date': batch.expiry_date.isoformat(),
                    'initial_quantity': float(batch.initial_quantity),
                    'current_quantity': float(batch.current_quantity),
                    'unit': batch.unit,
                    'shelf_life_days': batch.shelf_life_days,
                    'shelf_life_remaining_pct': float(batch.shelf_life_remaining_pct),
                    'status': batch.status,
                    'days_until_expiry': batch.days_until_expiry,
                },
                'is_new_batch': result['is_new_batch'],
                'message': 'Batch berhasil ditambahkan.',
            }, status=status.HTTP_201_CREATED)

        return Response(
            {'error': 'Gagal membuat batch.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class BatchUpdateView(generics.UpdateAPIView):
    """Update batch details (quantity adjustment, notes)."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)
    queryset = ProductBatch.objects.all()
    serializer_class = ProductBatchSerializer

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        batch = self.get_object()

        # Verify ownership
        if batch.store != request.user.store:
            return Response(
                {'error': 'Batch ini bukan milik toko Anda.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        current_qty = request.data.get('current_quantity')
        qty_changed = False
        if current_qty is not None:
            new_qty = Decimal(str(current_qty))
            if new_qty < 0:
                return Response(
                    {'error': 'Jumlah tidak boleh negatif.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            qty_changed = new_qty != batch.current_quantity
            old_qty = float(batch.current_quantity)
            batch.current_quantity = new_qty

        notes = request.data.get('notes')
        if notes is not None:
            batch.notes = notes

        batch.save()
        batch.refresh_status()

        # Sync Product.stock + broadcast if quantity changed
        if qty_changed and batch.product:
            from .services.fefo_engine import _sync_product_stock
            _sync_product_stock(batch.product)
            try:
                from orders.views import notify_stock_update
                stock_change = float(new_qty) - old_qty
                notify_stock_update(
                    store_id=batch.store.id,
                    product_id=batch.product.id,
                    product_name=batch.product.product_name,
                    stock_change=stock_change,
                    action='stock_adjusted',
                    store_user_id=batch.store.user_id,
                )
            except Exception as exc:
                logger.warning('Stock broadcast failed for batch update: %s', exc)

        serializer = ProductBatchSerializer(batch)
        return Response(serializer.data)


class BatchDetailView(generics.RetrieveAPIView):
    """Get batch details by ID."""
    permission_classes = (permissions.IsAuthenticated,)
    queryset = ProductBatch.objects.all()
    serializer_class = ProductBatchSerializer


@extend_schema(exclude=True)
class BatchDisposeView(APIView):
    """Dispose of a batch (mark as disposed, remove from inventory)."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    @transaction.atomic
    def post(self, request, pk):
        try:
            batch = ProductBatch.objects.get(id=pk, store=request.user.store)
        except ProductBatch.DoesNotExist:
            return Response(
                {'error': 'Batch tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        qty_before = float(batch.current_quantity)
        batch.current_quantity = 0
        batch.is_active = False
        batch.save()

        # Log disposal transaction
        InventoryStock.objects.create(
            store=request.user.store,
            master_product=batch.master_product,
            product=batch.product,
            batch=batch,
            transaction_type='disposal',
            quantity=qty_before,
            quantity_before=qty_before,
            quantity_after=0,
            notes='Manual disposal oleh seller.',
            created_by=request.user,
        )

        ExpiryNotification.objects.create(
            batch=batch,
            store=request.user.store,
            notification_type='disposal',
            days_until_expiry=-1,
        )

        # Sync Product.stock from remaining batches + broadcast
        if batch.product:
            from .services.fefo_engine import _sync_product_stock
            _sync_product_stock(batch.product)
            try:
                from orders.views import notify_stock_update
                notify_stock_update(
                    store_id=batch.store.id,
                    product_id=batch.product.id,
                    product_name=batch.product.product_name,
                    stock_change=-qty_before,
                    action='stock_disposed',
                    store_user_id=batch.store.user_id,
                )
            except Exception as exc:
                logger.warning('Stock broadcast failed for batch dispose: %s', exc)
            # Send low stock notification if applicable
            try:
                store_user_id = batch.store.user_id
                product_name = batch.product.product_name
                remaining = float(sum(
                    ProductBatch.objects.filter(
                        store=batch.store,
                        master_product=batch.master_product,
                        is_active=True,
                        status__in=['fresh', 'expiring_soon'],
                    ).values_list('current_quantity', flat=True)
                ))
                if remaining <= 5:
                    notify_inventory_low(store_user_id, product_name, remaining, batch.store.store_name)
            except Exception as exc:
                logger.warning('Low stock notification failed for batch dispose: %s', exc)

        return Response({
            'success': True,
            'message': f'Batch {batch.batch_number} telah di-dispose.',
            'disposed_quantity': qty_before,
        })


# =============================================================================
# FEFO STOCK OUTBOUND
# =============================================================================


@extend_schema(exclude=True)
class StockOutView(APIView):
    """Process stock outbound using FEFO.

    Automatically picks the nearest-expiring batch(es) first.
    If quantity exceeds available stock, returns error with shortage info.

    Flutter-ready JSON.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request):
        serializer = StockOutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        store = request.user.store

        master_product = MasterProduct.objects.filter(
            id=data['master_product_id'], is_active=True
        ).first()
        if not master_product:
            return Response(
                {'error': 'Master produk tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        result = stock_out(
            store=store,
            master_product=master_product,
            quantity=data['quantity'],
            notes=data.get('notes', ''),
            created_by=request.user,
            reference_type=data.get('reference_type', ''),
            reference_id=data.get('reference_id', ''),
        )

        if result['success']:
            # Broadcast stock deduction — find Product listing from first affected batch
            try:
                product_obj = None
                if result.get('transactions'):
                    first_batch_id = result['transactions'][0].get('batch_id')
                    if first_batch_id:
                        from .models import ProductBatch
                        batch_obj = ProductBatch.objects.filter(id=first_batch_id).select_related('product').first()
                        if batch_obj and batch_obj.product:
                            product_obj = batch_obj.product
                if product_obj:
                    from orders.views import notify_stock_update
                    notify_stock_update(
                        store_id=store.id,
                        product_id=product_obj.id,
                        product_name=product_obj.product_name,
                        stock_change=-float(data['quantity']),
                        action='stock_deducted',
                        store_user_id=store.user_id,
                    )
            except Exception as exc:
                logger.warning('Stock broadcast failed for stock_out: %s', exc)

            return Response({
                'success': True,
                'total_quantity': result['total_quantity'],
                'batches_used': result['batches_used'],
                'transactions': result['transactions'],
                'note': result['note'],
            })

        # Convert FEFO picks to serializable dicts before returning
        picks_data = []
        for pick in result.get('picks', []):
            batch = pick.get('batch')
            if hasattr(batch, 'id'):  # ProductBatch instance
                picks_data.append({
                    'batch_id': batch.id,
                    'batch_number': batch.batch_number,
                    'expiry_date': batch.expiry_date.isoformat(),
                    'current_quantity': float(batch.current_quantity),
                    'pick_qty': float(pick.get('pick_qty', 0)),
                })
            else:
                picks_data.append(pick)

        return Response({
            'success': False,
            'error': result.get('error', 'Stok tidak mencukupi.'),
            'picks': picks_data,
            'shortage': result.get('shortage', 0),
            'message': 'Stok tidak mencukupi untuk quantity yang diminta.',
        }, status=status.HTTP_409_CONFLICT)


@extend_schema(exclude=True)
class FEFOCheckView(APIView):
    """Check what batch(es) would be picked by FEFO for a given quantity.

    Preview only — does not deduct stock.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request):
        master_product_id = request.data.get('master_product_id')
        quantity = request.data.get('quantity')

        if not master_product_id or not quantity:
            return Response(
                {'error': 'master_product_id dan quantity wajib diisi.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .services.fefo_engine import get_fefo_batch
        from stores.models import Store

        try:
            master_product = MasterProduct.objects.get(id=master_product_id, is_active=True)
        except MasterProduct.DoesNotExist:
            return Response(
                {'error': 'Master produk tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        result = get_fefo_batch(request.user.store, master_product, Decimal(str(quantity)))

        if result['success']:
            return Response({
                'success': True,
                'total_quantity': float(quantity),
                'batches_used': len(result['picks']),
                'picks': [
                    {
                        'batch_id': p['batch'].id,
                        'batch_number': p['batch'].batch_number,
                        'expiry_date': p['batch'].expiry_date.isoformat(),
                        'current_quantity': float(p['batch'].current_quantity),
                        'pick_qty': float(p['pick_qty']),
                        'days_until_expiry': (p['batch'].expiry_date - timezone.now().date()).days,
                    }
                    for p in result['picks']
                ],
            })

        return Response({
            'success': False,
            'error': result.get('error', 'Stok tidak mencukupi.'),
            'shortage': result.get('shortage', 0),
        }, status=status.HTTP_409_CONFLICT)


# =============================================================================
# INVENTORY TRANSACTIONS
# =============================================================================


@extend_schema(exclude=True)
class InventoryTransactionListView(generics.ListAPIView):
    """List stock transactions for the seller's store.

    Filterable by:
    - transaction_type: stock_in, stock_out, adjustment, disposal
    - master_product_id: filter by product
    - date_from, date_to: date range
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)
    serializer_class = InventoryStockSerializer
    pagination_class = None

    def get_queryset(self):
        qs = InventoryStock.objects.filter(
            store=self.request.user.store
        ).select_related(
            'master_product', 'batch', 'created_by'
        ).order_by('-created_at')

        transaction_type = self.request.query_params.get('transaction_type')
        if transaction_type:
            qs = qs.filter(transaction_type=transaction_type)

        master_product_id = self.request.query_params.get('master_product_id')
        if master_product_id:
            qs = qs.filter(master_product_id=master_product_id)

        date_from = self.request.query_params.get('date_from')
        if date_from:
            qs = qs.filter(created_at__gte=date_from)

        date_to = self.request.query_params.get('date_to')
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        return qs


# =============================================================================
# BATCH & STOCK SUMMARY
# =============================================================================


@extend_schema(exclude=True)
class BatchSummaryView(APIView):
    """Get batch summary for the seller's store.

    Groups by status: fresh, expiring_soon, expired, disposed.
    Optionally filter by master_product_id.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        master_product_id = request.query_params.get('master_product_id')
        master_product = None
        if master_product_id:
            try:
                master_product = MasterProduct.objects.get(id=int(master_product_id))
            except (ValueError, MasterProduct.DoesNotExist):
                pass

        summary = get_batch_summary(request.user.store, master_product)
        serializer = BatchSummarySerializer(data=summary)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class BatchListView(generics.ListAPIView):
    """List all active batches for the seller's store.

    Filterable by:
    - status: fresh, expiring_soon, expired, disposed
    - master_product_id: filter by product
    - expires_soon: true (within 30 days)
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)
    serializer_class = ProductBatchSerializer
    pagination_class = None

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ProductBatch.objects.none()

        qs = ProductBatch.objects.filter(
            store=self.request.user.store,
            is_active=True,
        ).select_related('master_product').order_by('expiry_date')

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        master_product_id = self.request.query_params.get('master_product_id')
        if master_product_id:
            qs = qs.filter(master_product_id=master_product_id)

        expires_soon = self.request.query_params.get('expires_soon')
        if expires_soon and expires_soon.lower() in ('true', '1'):
            today = timezone.now().date()
            from datetime import timedelta
            qs = qs.filter(
                expiry_date__range=[today, today + timedelta(days=30)],
                status__in=['fresh', 'expiring_soon'],
            )

        return qs


# =============================================================================
# EXPIRY DASHBOARD
# =============================================================================


@extend_schema(exclude=True)
class ExpirySummaryView(APIView):
    """Get expiry dashboard for the seller's store (cached 5 min).

    Returns:
    - expiring_this_week_count
    - expiring_this_month_count
    - already_expired_count
    - Full list of expiring batches (this week) with product details
    - Full list of already expired batches
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        store = request.user.store
        cache_key = f'expiry_summary_{store.id}'

        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        data = get_expiry_summary(store)
        serializer = ExpirySummarySerializer(data={
            'store_id': store.id,
            'today': timezone.now().date(),
            'expiring_this_week_count': data['expiring_this_week_count'],
            'expiring_this_month_count': data['expiring_this_month_count'],
            'already_expired_count': data['already_expired_count'],
        })
        serializer.is_valid(raise_exception=True)
        result = {
            **serializer.validated_data,
            'expiring_this_week': data.get('expiring_this_week', []),
            'already_expired': data.get('already_expired', []),
        }
        cache.set(cache_key, result, EXPIRY_CACHE_TTL)
        
        return Response(result)


@extend_schema(exclude=True)
class ExpiryCheckTriggerView(APIView):
    """Manually trigger expiry check and notification for this store (async via Celery).

    POST to this endpoint to run expiry checks immediately.
    Returns task ID for status tracking.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request):
        from .tasks import run_expiry_check_task
        try:
            task = run_expiry_check_task.delay(store_id=request.user.store.id)
            task_id = task.id
        except Exception as exc:
            logger.warning('Celery unavailable — expiry check skipped: %s', exc)
            task_id = None
        return Response({
            'success': True,
            'task_id': task_id,
            'message': 'Pemeriksaan kadaluwarsa sedang diproses.',
        })


@extend_schema(exclude=True)
class ExpiryNotificationListView(generics.ListAPIView):
    """List expiry notifications for the seller's store."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)
    serializer_class = ExpiryNotificationSerializer

    def get_queryset(self):
        return ExpiryNotification.objects.filter(
            store=self.request.user.store
        ).select_related('batch__master_product').order_by('-sent_at')


# =============================================================================
# STOCK ALERTS
# =============================================================================


@extend_schema(exclude=True)
class StockAlertListCreateView(generics.ListCreateAPIView):
    """List and create stock threshold alerts."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)
    serializer_class = StockAlertSerializer

    def get_queryset(self):
        return StockAlert.objects.filter(
            store=self.request.user.store
        ).select_related('master_product').order_by('master_product__product_name')

    def perform_create(self, serializer):
        serializer.save(store=self.request.user.store)


class StockAlertDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete a stock alert."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)
    serializer_class = StockAlertSerializer

    def get_queryset(self):
        return StockAlert.objects.filter(store=self.request.user.store)


@extend_schema(exclude=True)
class LowStockReportView(APIView):
    """Get low stock report for the seller's store (cached 3 min).

    Compares current stock against alert thresholds.
    Returns products where current stock is below minimum.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        store = request.user.store
        cache_key = f'low_stock_report_{store.id}'

        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        alerts = StockAlert.objects.filter(
            store=store, is_active=True
        ).select_related('master_product')

        today = timezone.now().date()

        low_stock_items = []
        for alert in alerts:
            # Sum all batch quantities for this product
            total_qty = ProductBatch.objects.filter(
                store=store,
                master_product=alert.master_product,
                is_active=True,
                status__in=['fresh', 'expiring_soon'],
            ).aggregate(total=Sum('current_quantity'))['total'] or 0

            if total_qty < alert.min_stock:
                # Get nearest expiry batch info
                nearest_batch = ProductBatch.objects.filter(
                    store=store,
                    master_product=alert.master_product,
                    is_active=True,
                    status__in=['fresh', 'expiring_soon'],
                ).order_by('expiry_date').first()

                low_stock_items.append({
                    'alert_id': alert.id,
                    'master_product_id': alert.master_product.id,
                    'product_name': alert.master_product.product_name,
                    'barcode': alert.master_product.barcode,
                    'current_stock': float(total_qty),
                    'min_stock': float(alert.min_stock),
                    'shortage': float(alert.min_stock - total_qty),
                    'nearest_expiry': nearest_batch.expiry_date.isoformat() if nearest_batch else None,
                    'days_until_expiry': (nearest_batch.expiry_date - today).days if nearest_batch else None,
                })

        result = {
            'store_id': store.id,
            'store_name': store.store_name,
            'total_low_stock': len(low_stock_items),
            'items': sorted(low_stock_items, key=lambda x: x['shortage'], reverse=True),
        }
        cache.set(cache_key, result, LOW_STOCK_CACHE_TTL)
        return Response(result)


# =============================================================================
# AI AUTO-REGISTER — Create Draft Product from Scan
# =============================================================================


@extend_schema(exclude=True)
class AIAutoRegisterDraftView(APIView):
    """
    Auto-create a draft Product from AI recognition results.
    
    POST /api/inventory/ai-auto-register/
    {
        "product_name": "Nama Produk",
        "brand": "Merek",
        "category": "Kategori",
        "subcategory": "Subkategori",
        "packaging_type": "botol|plastik|kaleng|kardus|sachet|dll",
        "unit": "pcs|kg|ml|gr",
        "weight_value": 250,
        "weight_unit": "ml",
        "estimated_price": 10000,
        "description": "Deskripsi produk",
        "composition": "Komposisi",
        "expiry_date": "2027-12-31",
        "barcode": "optional_barcode",
        "confidence": 0.85,
        "images": ["base64_img1", "base64_img2"],
        "freshness_score": null,
        "freshness_status": null
    }
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    @transaction.atomic
    def post(self, request):
        from products.models import Product, Category

        product_name = request.data.get('product_name', '').strip()
        if not product_name:
            return Response({'error': 'Nama produk wajib diisi.'},
                          status=status.HTTP_400_BAD_REQUEST)

        store = request.user.store
        if not store:
            return Response({'error': 'Anda belum memiliki toko.'},
                          status=status.HTTP_400_BAD_REQUEST)

        # Find or create category
        category_name = request.data.get('category', '').strip() or 'Umum'
        category, _ = Category.objects.get_or_create(
            category_name__iexact=category_name,
            defaults={'category_name': category_name, 'is_active': True}
        )

        # Build description from AI data
        ai_parts = []
        packaging = request.data.get('packaging_type', '')
        if packaging:
            ai_parts.append(f"Jenis kemasan: {packaging}")
        composition = request.data.get('composition', '')
        if composition:
            ai_parts.append(f"Komposisi: {composition}")
        freshness = request.data.get('freshness_status', '')
        if freshness:
            ai_parts.append(f"Tingkat kesegaran: {freshness}")

        description = request.data.get('description', '').strip()
        if ai_parts:
            ai_note = '\n'.join(ai_parts)
            description = (description + '\n\n' + ai_note) if description else ai_note

        confidence = float(request.data.get('confidence', 0))
        ai_scan_notes = f"Produk dibuat dari AI Auto-Register (confidence: {confidence*100:.0f}%)"

        product = Product.objects.create(
            store=store,
            category=category,
            product_name=product_name,
            brand=request.data.get('brand', ''),
            description=description,
            price=Decimal(str(request.data.get('estimated_price', 0))),
            stock=0,
            unit=request.data.get('unit', 'pcs'),
            weight_value=request.data.get('weight_value'),
            weight_unit=request.data.get('weight_unit', ''),
            is_active=False,
            product_status='draft',
            notes=ai_scan_notes,
        )

        # Save first image as product photo
        images = request.data.get('images', [])
        if images:
            try:
                import base64
                img_str = images[0]
                if ',' in img_str:
                    img_str = img_str.split(',')[1]
                img_bytes = base64.b64decode(img_str)
                from django.core.files.basefile import ContentFile
                content = ContentFile(img_bytes)
                ext = 'jpg'
                fname = f"ai_draft_{product.id}_{int(timezone.now().timestamp())}.{ext}"
                product.product_photo.save(fname, content, save=True)
            except Exception as exc:
                logger.warning(f"Failed to save AI draft image for product {product.id}: {exc}")

        # Update store product count
        store.product_count = Product.objects.filter(store=store).count()
        store.save(update_fields=['product_count'])

        # Log & broadcast
        logger.info(f"AI Auto-Register: '{product_name}' (ID: {product.id}) created as draft")
        try:
            from products.views import notify_product_update
            notify_product_update(store.id, product.id, product.product_name, 'product_created', store.user_id)
        except Exception as exc:
            logger.warning(f"WebSocket broadcast failed: {exc}")

        return Response({
            'success': True,
            'product_id': product.id,
            'product_slug': getattr(product, 'slug', ''),
            'is_draft': True,
            'message': f'Produk "{product_name}" berhasil dibuat sebagai draft.',
        }, status=status.HTTP_201_CREATED)


# =============================================================================
# AI PRODUCT RECOGNITION — Hybrid Pipeline
# =============================================================================


@extend_schema(exclude=True)
class AIProductRecognizeView(APIView):
    """
    AI Product Recognition — Hybrid Pipeline.
    
    End-to-end product recognition from a single image.
    Combines Gemini Vision + OCR + Barcode + Freshness detection.
    
    POST /api/inventory/ai-recognize/
    {
        "image": "base64_encoded_image",
        "barcode_hint": "optional_barcode",
        "ocr_text_hint": "optional_ocr_text",
        "scan_mode": "auto|freshness|multi"
    }
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request):
        image = request.data.get('image', '')
        if not image:
            return Response({'error': 'Image (base64) wajib diisi.'},
                          status=status.HTTP_400_BAD_REQUEST)

        pipeline = get_ai_product_recognition_pipeline()
        result = pipeline.recognize_product(
            image_data=image,
            store=request.user.store,
            barcode_hint=request.data.get('barcode_hint', ''),
            ocr_text_hint=request.data.get('ocr_text_hint', ''),
            scan_mode=request.data.get('scan_mode', 'auto'),
        )
        
        # Send notification for scan results
        try:
            product_name = result.get('product_name', '') or result.get('recognized_product', {}).get('product_name', '')
            confidence = float(result.get('confidence', 0) or result.get('recognized_product', {}).get('confidence', 0))
            if product_name:
                notify_ai_scan_complete(request.user.id, product_name, result, confidence)
        except Exception as exc:
            logger.warning('AI scan notification failed: %s', exc)
        
        return Response(result)


@extend_schema(exclude=True)
class AIMultiDetectView(APIView):
    """
    Multi-Object Detection — detect multiple products in one image.
    
    POST /api/inventory/ai-multi-detect/
    {
        "image": "base64_encoded_image"
    }
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request):
        image = request.data.get('image', '')
        if not image:
            return Response({'error': 'Image (base64) wajib diisi.'},
                          status=status.HTTP_400_BAD_REQUEST)

        pipeline = get_ai_product_recognition_pipeline()
        result = pipeline.detect_multi_object(
            image_data=image,
            store=request.user.store,
        )

        return Response(result)


@extend_schema(exclude=True)
class AIFreshnessView(APIView):
    """
    Freshness Classification — analyze freshness of produce.
    
    POST /api/inventory/ai-freshness/
    {
        "image": "base64_encoded_image",
        "product_name": "optional_product_name"
    }
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request):
        image = request.data.get('image', '')
        if not image:
            return Response({'error': 'Image (base64) wajib diisi.'},
                          status=status.HTTP_400_BAD_REQUEST)

        pipeline = get_ai_product_recognition_pipeline()
        result = pipeline.classify_freshness(
            image_data=image,
            product_name=request.data.get('product_name', ''),
        )

        return Response(result)


@extend_schema(exclude=True)
class AILearnProductView(APIView):
    """
    Smart UMKM Learning — register a new product from multiple images.
    
    POST /api/inventory/ai-learn-product/
    {
        "images": ["base64_img_1", "base64_img_2"],
        "product_name": "Nama Produk",
        "brand": "Merek",
        "category": "Kategori",
        "price": 10000,
        "unit": "pcs",
        "stock": 24,
        "expiry_date": "2027-12-31"
    }
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request):
        images = request.data.get('images', [])
        if not images:
            return Response({'error': 'Minimal 1 foto diperlukan.'},
                          status=status.HTTP_400_BAD_REQUEST)

        pipeline = get_ai_product_recognition_pipeline()
        result = pipeline.learn_new_product(
            images=images,
            seller_input={
                'product_name': request.data.get('product_name', ''),
                'brand': request.data.get('brand', ''),
                'category': request.data.get('category', 'UMKM'),
                'price': request.data.get('price', 0),
                'unit': request.data.get('unit', 'pcs'),
                'stock': request.data.get('stock', 0),
                'expiry_date': request.data.get('expiry_date', ''),
                'barcode': request.data.get('barcode', ''),
                'subcategory': request.data.get('subcategory', ''),
                'weight_value': request.data.get('weight_value'),
                'weight_unit': request.data.get('weight_unit', ''),
                'manufacturer': request.data.get('manufacturer', ''),
                'bpom_number': request.data.get('bpom_number', ''),
            },
            store=request.user.store,
            user=request.user,
        )

        return Response(result, status=status.HTTP_201_CREATED if result.get('is_new') else status.HTTP_200_OK)


# =============================================================================
# AI EXPIRED REMINDER & DISCOUNT RECOMMENDATIONS
# =============================================================================


@extend_schema(exclude=True)
class ExpiredReminderDashboardView(APIView):
    """
    Get AI Expired Reminder dashboard widget data.
    
    GET /api/inventory/expired-reminder/dashboard/
    Returns summary of expiring batches, discount recs, and bundling suggestions.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        reminder = get_expired_reminder()
        data = reminder.get_seller_discount_recommendations(
            store_id=request.user.store.id
        )
        return Response(data)


@extend_schema(exclude=True)
class FlashSaleCandidatesView(APIView):
    """
    Get products needing urgent flash sale (<=3 days to expiry).
    
    GET /api/inventory/expired-reminder/flash-sale/
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        reminder = get_expired_reminder()
        candidates = reminder.get_flash_sale_candidates(
            store_id=request.user.store.id
        )
        return Response({
            'count': len(candidates),
            'candidates': candidates,
        })


@extend_schema(exclude=True)
class DiscountRecommendationsView(APIView):
    """
    Get discount recommendations for expiring products.
    
    GET /api/inventory/expired-reminder/discounts/
    Returns tiered discount suggestions with bundling.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        reminder = get_expired_reminder()
        data = reminder.get_seller_discount_recommendations(
            store_id=request.user.store.id
        )
        return Response({
            'recommendations': data.get('recommendations', []),
            'bundling_suggestions': data.get('bundling_suggestions', []),
            'financial_impact': data.get('financial_impact', {}),
        })


@extend_schema(exclude=True)
class TriggerExpiryCheckView(APIView):
    """
    Manually trigger full expiry check for this store.
    
    POST /api/inventory/expired-reminder/check/
    Updates batch statuses and sends notifications.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request):
        reminder = get_expired_reminder()
        result = reminder.check_store_expiry(
            store_id=request.user.store.id
        )
        
        # Send notifications for expired products found during check
        try:
            store = request.user.store
            store_user_id = store.user_id
            expired_count = result.get('expired_count', 0) or len(result.get('expired', []))
            expiring_count = result.get('expiring_count', 0) or len(result.get('expiring', []))
            
            if expired_count > 0:
                for item in result.get('expired', []):
                    pname = item.get('product_name', item.get('batch', {}).get('master_product', {}).get('product_name', 'Produk'))
                    notify_expired_product(store_user_id, pname, 0, store.store_name)
            
            if expiring_count > 0:
                for item in result.get('expiring', []):
                    pname = item.get('product_name', item.get('batch', {}).get('master_product', {}).get('product_name', 'Produk'))
                    days = item.get('days_until_expiry', 7)
                    notify_expired_product(store_user_id, pname, days, store.store_name)
                    if days <= 3:
                        notify_discount_recommendation(store_user_id, pname, 0, days)
        except Exception as exc:
            logger.warning('Expiry notification failed: %s', exc)
        
        return Response(result)
