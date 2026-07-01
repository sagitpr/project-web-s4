"""
Orders views for Warungio Marketplace.
Cart management, order placement, order tracking.
"""

import logging
from asgiref.sync import async_to_sync
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone
from channels.layers import get_channel_layer
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from rest_framework import serializers as drf_serializers, status, generics, permissions, views, filters
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend

from .models import Cart, Order, OrderItem, Delivery, ShippingMethod, OfflineSale, PackingSession, PackedItem
from .serializers import (
    CartSerializer, OrderListSerializer, OrderDetailSerializer,
    OrderCreateSerializer, OrderStatusSerializer, DeliverySerializer,
    ShippingMethodSerializer, CancelOrderSerializer,
    OfflineSaleSerializer, OfflineSaleListSerializer
)
from stores.models import Store
from products.models import Product
from inventory.models import MasterProduct, ProductBatch
from inventory.services.barcode_lookup import lookup_barcode
from inventory.services.fefo_engine import stock_out
from accounts.permissions import IsSeller, IsOrderOwner
from notifications.models import Notification
from .services.courier_tracking import get_tracking_status
from .services.distance import calculate_haversine_distance, estimate_shipping_fee


# =============================================================================
# HELPER: Send order notification via WebSocket + DB
# =============================================================================

def notify_order_update(user_id, order_id, order_number, status, message=''):
    """Create Notification record and broadcast via WebSocket channel layer."""
    # Save to DB
    Notification.objects.create(
        user_id=user_id,
        notification_type='order',
        priority='high' if status in ('paid', 'shipped', 'on_delivery', 'completed', 'cancelled') else 'medium',
        title=f'Pesanan {order_number}',
        description=message,
        action_url=f'/buyer/orders/index.html?id={order_id}',
        action_text='Lihat Pesanan',
        metadata={'order_id': order_id, 'order_number': order_number, 'status': status},
    )

    # Broadcast via WebSocket
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'notifications_{user_id}',
                {
                    'type': 'order_update',
                    'order_id': order_id,
                    'order_number': order_number,
                    'status': status,
                    'message': message,
                }
            )
    except Exception as e:
        _log = logging.getLogger('django_backend.orders')
        _log.error('WebSocket broadcast error (order update): %s', str(e))


# =============================================================================
# HELPER: Send delivery tracking update via WebSocket
# =============================================================================

def notify_delivery_update(user_id, order_id, order_number, delivery_status, tracking_number='', courier=''):
    """
    Broadcast delivery tracking update via WebSocket only.
    Intentionally does NOT create a Notification DB record — tracking updates are
    transient status polls and would flood the notification list.
    """
    status_messages = {
        'diproses_penjual': 'Pesanan sedang diproses oleh penjual.',
        'menunggu_penjemputan': 'Pesanan siap dijemput kurir!',
        'kurir_menjemput': 'Kurir sedang menuju ke toko untuk mengambil pesanan.',
        'dalam_perjalanan': 'Pesanan sedang dalam perjalanan menuju alamat kamu.',
        'pesanan_diterima': 'Pesanan telah sampai di alamat tujuan!',
        'dibatalkan': 'Pengiriman pesanan dibatalkan.',
    }
    message = status_messages.get(delivery_status, f'Status pengiriman: {delivery_status}')

    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'notifications_{user_id}',
                {
                    'type': 'delivery_update',
                    'order_id': order_id,
                    'order_number': order_number,
                    'delivery_status': delivery_status,
                    'tracking_number': tracking_number,
                    'courier': courier,
                    'message': message,
                }
            )
    except Exception as e:
        _log = logging.getLogger('django_backend.orders')
        _log.error('WebSocket broadcast error (delivery update): %s', str(e))


@extend_schema_view(
    get=extend_schema(
        summary='Daftar Metode Pengiriman',
        description='Mengembalikan daftar metode pengiriman hyperlocal yang aktif '
                    '(GoSend, GrabExpress, Maxim Delivery, Antar Sendiri).',
        tags=['Shipping'],
        responses={200: ShippingMethodSerializer(many=True)},
    ),
)
class ShippingMethodListView(generics.ListAPIView):
    """List active hyperlocal shipping methods."""
    queryset = ShippingMethod.objects.filter(is_active=True)
    serializer_class = ShippingMethodSerializer
    permission_classes = (permissions.AllowAny,)


class CartListView(generics.ListCreateAPIView):
    """List cart items and add to cart."""
    serializer_class = CartSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).select_related(
            'product', 'product__store'
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CartDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Update or remove cart item."""
    serializer_class = CartSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)


class CartClearView(views.APIView):
    """Clear all cart items."""
    permission_classes = (permissions.IsAuthenticated,)

    def delete(self, request):
        Cart.objects.filter(user=request.user).delete()
        return Response({'message': 'Keranjang berhasil dikosongkan.'})


class CartCountView(views.APIView):
    """Get cart item count."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        count = Cart.objects.filter(user=request.user).count()
        return Response({'count': count})


@extend_schema_view(
    post=extend_schema(
        summary='Buat Pesanan Baru',
        description='Membuat pesanan dari item keranjang yang dipilih. '
                    'Mendukung pemilihan metode pengiriman hyperlocal.',
        tags=['Orders'],
        request=OrderCreateSerializer,
        responses={
            201: OpenApiExample(
                'Order Created',
                value={'message': 'Pesanan berhasil dibuat.', 'orders': []},
                response_only=True,
            ),
            400: OpenApiExample('Validation Error', value={'error': 'Keranjang kosong.'}, response_only=True),
        },
    ),
)
class OrderCreateView(views.APIView):
    """Create order from cart items."""
    permission_classes = (permissions.IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = OrderCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        cart_items = Cart.objects.filter(
            id__in=serializer.validated_data['cart_items'],
            user=user
        ).select_related('product', 'product__store')

        if not cart_items.exists():
            return Response({'error': 'Keranjang kosong.'},
                          status=status.HTTP_400_BAD_REQUEST)

        # Group by store
        store_orders = {}
        for item in cart_items:
            store_id = item.product.store_id
            if store_id not in store_orders:
                store_orders[store_id] = []
            store_orders[store_id].append(item)

        buyer_lat = serializer.validated_data.get('latitude')
        buyer_lng = serializer.validated_data.get('longitude')

        orders = []
        for store_id, items in store_orders.items():
            # Create order
            sm_id = serializer.validated_data.get('shipping_method')
            shipping_method = None
            if sm_id:
                try:
                    shipping_method = ShippingMethod.objects.get(id=sm_id, is_active=True)
                except ShippingMethod.DoesNotExist:
                    pass

            # Calculate dynamic shipping cost based on distance
            store = Store.objects.filter(id=store_id).first()
            distance = None
            shipping_cost = 0.0
            if shipping_method:
                base_fee = shipping_method.base_fee
                if store and store.latitude is not None and store.longitude is not None and buyer_lat is not None and buyer_lng is not None:
                    distance = calculate_haversine_distance(
                        store.latitude, store.longitude, buyer_lat, buyer_lng
                    )
                    shipping_fee_decimal = estimate_shipping_fee(base_fee, distance)
                    shipping_cost = float(shipping_fee_decimal)
                else:
                    shipping_cost = float(base_fee)

            order = Order.objects.create(
                user=user,
                store_id=store_id,
                shipping_method=shipping_method,
                subtotal=0,
                total_price=0,
                shipping_cost=shipping_cost,
                delivery_address=serializer.validated_data['delivery_address'],
                recipient_name=serializer.validated_data['recipient_name'],
                recipient_phone=serializer.validated_data['recipient_phone'],
                notes=serializer.validated_data.get('notes', ''),
                payment_method=serializer.validated_data['payment_method'],
            )

            # Create order items
            for cart_item in items:
                product = cart_item.product
                price = float(product.price)
                
                if product.available_stock < cart_item.qty:
                    raise ValidationError(
                        f"Stok {product.product_name} tidak mencukupi. "
                        f"Tersedia: {product.available_stock}"
                    )

                # Reserve stock atomically (bukan kurangi langsung)
                # Stock akan benar-benar berkurang saat seller scan barang di packing
                Product.objects.filter(id=product.id).update(
                    reserved_stock=F('reserved_stock') + cart_item.qty
                )

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.product_name,
                    product_photo=str(product.product_photo.url) if product.product_photo else '',
                    qty=cart_item.qty,
                    price=price,
                    subtotal=price * cart_item.qty,
                )

            # Calculate totals
            order.calculate_totals()
            orders.append(order)

            # Create delivery record
            Delivery.objects.create(
                order=order,
                shipping_method=shipping_method,
                estimated_time=shipping_method.estimated_time if shipping_method else None,
                distance=distance,
                buyer_latitude=buyer_lat,
                buyer_longitude=buyer_lng,
            )

            # Update store stats atomically
            Store.objects.filter(id=order.store_id).update(
                total_sales=F('total_sales') + order.total_price
            )

        # Clear used cart items
        cart_ids = [item.id for items in store_orders.values() for item in items]
        Cart.objects.filter(id__in=cart_ids).delete()

        # Send real-time notifications for each order
        for order in orders:
            store_name = order.store.store_name if order.store else 'Warung'
            notify_order_update(
                user_id=user.id,
                order_id=order.id,
                order_number=order.order_number,
                status='pending',
                message=f'Pesanan dari {store_name} berhasil dibuat! Tunggu konfirmasi dari penjual.',
            )

        return Response({
            'message': 'Pesanan berhasil dibuat.',
            'orders': OrderListSerializer(orders, many=True).data,
        }, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        summary='Pesanan Saya',
        description='Mengembalikan daftar pesanan milik user yang terautentikasi.',
        tags=['Orders'],
        parameters=[
            OpenApiParameter('order_status', description='Filter status pesanan'),
            OpenApiParameter('payment_method', description='Filter metode pembayaran'),
        ],
    ),
)
class MyOrdersView(generics.ListAPIView):
    """List current user's orders."""
    serializer_class = OrderListSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['order_status', 'payment_method']
    ordering_fields = ['-created_at']

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).select_related(
            'store'
        ).prefetch_related('items')


class OrderDetailView(generics.RetrieveAPIView):
    """Get order detail."""
    serializer_class = OrderDetailSerializer
    permission_classes = (permissions.IsAuthenticated, IsOrderOwner)

    def get_queryset(self):
        return Order.objects.all().select_related(
            'store', 'user'
        ).prefetch_related('items')


class SellerOrdersView(generics.ListAPIView):
    """List orders for seller's store."""
    serializer_class = OrderListSerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_queryset(self):
        return Order.objects.filter(
            store__user=self.request.user
        ).select_related('store', 'user').prefetch_related('items')


@extend_schema_view(
    post=extend_schema(
        summary='Update Status Pesanan (Seller)',
        description='Memperbarui status pesanan oleh seller. '
                    'Mendukung alur pengiriman hyperlocal:\n'
                    '- `processed`: Konfirmasi pesanan\n'
                    '- `ready_pickup`: Siap dijemput kurir\n'
                    '- `courier_pickup`: Kurir menjemput (isi driver_name & driver_phone)\n'
                    '- `on_delivery`: Dalam perjalanan\n'
                    '- `completed`: Pesanan diterima\n'
                    '- `cancelled`: Batalkan pesanan',
        tags=['Orders'],
        request=OrderStatusSerializer,
        responses={
            200: OrderDetailSerializer,
            400: OpenApiExample('Bad Request', value={'error': 'Pesan error'}, response_only=True),
            404: OpenApiExample('Not Found', value={'error': 'Pesanan tidak ditemukan.'}, response_only=True),
        },
    ),
)
class OrderStatusUpdateView(views.APIView):
    """
    Update order status by seller.
    Supports hyperlocal delivery flow:
    - processed: seller confirms order (diproses_penjual)
    - ready_pickup: ready for courier pickup (menunggu_penjemputan)
    - courier_pickup: courier picks up (kurir_menjemput)
    - on_delivery: in transit (dalam_perjalanan)
    - completed: delivered (pesanan_diterima)
    - cancelled: order cancelled (dibatalkan)
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    # Map order_status -> delivery_status for hyperlocal flow
    STATUS_DELIVERY_MAP = {
        'processed': 'diproses_penjual',
        'ready_pickup': 'menunggu_penjemputan',
        'courier_pickup': 'kurir_menjemput',
        'on_delivery': 'dalam_perjalanan',
        'completed': 'pesanan_diterima',
        'cancelled': 'dibatalkan',
    }

    def post(self, request, order_id):
        order = Order.objects.filter(
            id=order_id, store__user=request.user
        ).prefetch_related('items__product').first()

        if not order:
            return Response({'error': 'Pesanan tidak ditemukan.'},
                          status=status.HTTP_404_NOT_FOUND)

        serializer = OrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        status_value = serializer.validated_data['status']

        # ── Validation: Cancellation only for pending/paid/processed ──
        if status_value == 'cancelled' and order.order_status not in ('pending', 'paid', 'processed'):
            return Response({
                'error': 'Pesanan tidak dapat dibatalkan pada status saat ini. '
                         'Hanya pesanan dengan status Menunggu, Lunas, atau Diproses yang dapat dibatalkan.'
            }, status=status.HTTP_400_BAD_REQUEST)

        order.order_status = status_value
        delivery_status = self.STATUS_DELIVERY_MAP.get(status_value, '')

        # ── Update delivery & order based on new status ──
        try:
            delivery = order.delivery
            if delivery_status:
                delivery.delivery_status = delivery_status

            if status_value == 'processed':
                delivery.estimated_pickup = serializer.validated_data.get('estimated_pickup', '')

            if status_value == 'ready_pickup':
                delivery.pickup_code = serializer.validated_data.get('pickup_code', '')
                delivery.estimated_time = serializer.validated_data.get('estimated_time', '')

            if status_value == 'courier_pickup':
                order.courier = serializer.validated_data.get('courier', order.courier or '')
                delivery.courier_name = serializer.validated_data.get('courier', '')
                delivery.driver_name = serializer.validated_data.get('driver_name', '')
                delivery.driver_phone = serializer.validated_data.get('driver_phone', '')
                delivery.picked_up_at = timezone.now()
                if not delivery.pickup_code:
                    import random, string
                    delivery.pickup_code = ''.join(random.choices(string.digits, k=6))

            if status_value == 'on_delivery':
                order.tracking_number = serializer.validated_data.get('tracking_number', '')
                delivery.tracking_number = serializer.validated_data.get('tracking_number', '')
                delivery.estimated_time = serializer.validated_data.get('estimated_time', delivery.estimated_time or '')

            if status_value == 'completed':
                order.completed_at = timezone.now()
                delivery.delivered_at = timezone.now()

            if status_value == 'cancelled':
                delivery.cancelled_at = timezone.now()

            delivery.save()
        except Delivery.DoesNotExist:
            pass

        if status_value == 'cancelled':
            with transaction.atomic():
                for item in order.items.all():
                    if item.product:
                        # Release reserved_stock (stock tidak pernah berkurang saat order)
                        Product.objects.filter(id=item.product.id).update(
                            reserved_stock=F('reserved_stock') - item.qty,
                        )
                Store.objects.filter(id=order.store_id).update(
                    total_sales=F('total_sales') - order.total_price
                )
                order.order_status = 'cancelled'
                order.save()
        else:
            order.save()

        # ── Build notification message ──
        cancel_reason = serializer.validated_data.get('cancel_reason', '')
        cancel_reason_text = serializer.validated_data.get('cancel_reason_text', '')

        REASON_LABELS = {
            'out_of_stock': 'Stok habis',
            'seller_unavailable': 'Penjual tidak bisa melayani',
            'wrong_price': 'Harga salah',
            'address_invalid': 'Alamat pengiriman tidak valid',
            'product_damaged': 'Produk rusak',
            'other': 'Lainnya',
        }

        status_messages = {
            'processed': 'Pesanan kamu sedang diproses oleh penjual.',
            'ready_pickup': 'Pesanan siap dijemput kurir.',
            'courier_pickup': 'Kurir sedang menjemput pesanan.',
            'on_delivery': 'Pesanan dalam perjalanan menuju alamat kamu!',
            'completed': 'Pesanan sudah diterima. Terima kasih sudah berbelanja!',
        }

        if status_value == 'cancelled':
            reason_label = REASON_LABELS.get(cancel_reason, '')
            msg = 'Pesanan dibatalkan oleh penjual.'
            if cancel_reason_text:
                msg += f' Alasan: {cancel_reason_text}'
            elif reason_label:
                msg += f' Alasan: {reason_label}'

            notify_order_update(
                user_id=order.store.user_id if order.store else request.user.id,
                order_id=order.id,
                order_number=order.order_number,
                status='cancelled',
                message=f'Pesanan {order.order_number} berhasil dibatalkan.' +
                    (f' Alasan: {cancel_reason_text or reason_label}' if (cancel_reason_text or reason_label) else ''),
            )
        else:
            msg = status_messages.get(status_value, f'Status pesanan berubah menjadi {status_value}.')

        notify_order_update(
            user_id=order.user_id,
            order_id=order.id,
            order_number=order.order_number,
            status=status_value,
            message=msg,
        )

        return Response({
            'message': f'Status pesanan berhasil diubah menjadi {status_value}.'
                       + (f' Stok produk sudah dikembalikan.' if status_value == 'cancelled' else ''),
            'order': OrderDetailSerializer(order).data,
        })


@extend_schema_view(
    get=extend_schema(
        summary='Tracking Pengiriman Hyperlocal',
        description='Mengembalikan status tracking terkini untuk pengiriman hyperlocal. '
                    'Termasuk milestones status, info driver, kode pickup, dan estimasi waktu.',
        tags=['Delivery'],
        responses={
            200: OpenApiExample(
                'Tracking Data',
                value={
                    'courier': 'GoSend',
                    'delivery_status': 'dalam_perjalanan',
                    'delivery_status_label': 'Dalam Perjalanan',
                    'status': 'on_delivery',
                    'milestones': [
                        {'status': 'Pesanan dikonfirmasi penjual', 'icon': 'package', 'time': '2026-01-01T10:00:00', 'is_current': False},
                        {'status': 'Pesanan dalam perjalanan', 'icon': 'truck', 'time': '2026-01-01T11:00:00', 'is_current': True},
                    ],
                    'driver_name': 'Budi',
                    'driver_phone': '08123456789',
                    'pickup_code': '123456',
                    'estimated_time': '15 menit lagi',
                    'source': 'hyperlocal',
                },
                response_only=True,
            ),
            404: OpenApiExample('Not Found', value={'error': 'Pesanan tidak ditemukan.'}, response_only=True),
        },
    ),
)
class DeliveryTrackingView(views.APIView):
    """
    Get hyperlocal delivery tracking status for an order.
    Returns status milestones, driver info, and estimated times
    based on the Delivery model's current status.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, order_id):
        order = Order.objects.filter(
            id=order_id, user=request.user
        ).select_related('delivery', 'delivery__shipping_method').first()

        if not order:
            return Response({'error': 'Pesanan tidak ditemukan.'},
                          status=status.HTTP_404_NOT_FOUND)

        try:
            delivery = order.delivery
        except Delivery.DoesNotExist:
            return Response({'error': 'Belum ada informasi pengiriman.'},
                          status=status.HTTP_404_NOT_FOUND)

        result = get_tracking_status(delivery)

        if not result:
            return Response({'error': 'Gagal mendapatkan status pengiriman.'},
                          status=status.HTTP_502_BAD_GATEWAY)

        # Broadcast WebSocket event if status changed
        new_status = result.get('delivery_status', '')
        old_status = delivery.delivery_status
        if new_status and new_status != old_status:
            try:
                delivery.delivery_status = new_status
                if new_status == 'pesanan_diterima':
                    delivery.delivered_at = timezone.now()
                    order.completed_at = timezone.now()
                    order.order_status = 'completed'
                    order.save(update_fields=['completed_at', 'order_status'])
                delivery.save(update_fields=['delivery_status', 'delivered_at'])
            except Exception as e:
                _log = logging.getLogger('django_backend.orders')
                _log.warning('Delivery tracking error: %s', str(e))

            notify_delivery_update(
                user_id=order.user_id,
                order_id=order.id,
                order_number=order.order_number,
                delivery_status=new_status,
                courier=delivery.courier_name or '',
            )

        return Response(result)


@extend_schema_view(
    post=extend_schema(
        summary='Batalkan Pesanan (Buyer)',
        description='Membatalkan pesanan oleh pembeli. '
                    'Hanya dapat dibatalkan jika status pesanan masih `pending` atau `paid`.',
        tags=['Orders'],
        request=CancelOrderSerializer,
        responses={
            200: OrderDetailSerializer,
            400: OpenApiExample('Bad Request', value={'error': 'Pesanan tidak dapat dibatalkan pada status saat ini.'}, response_only=True),
        },
    ),
)
class BuyerCancelOrderView(views.APIView):
    """
    Cancel order by buyer (order owner).
    Only cancellable if status is 'pending' or 'paid'.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, order_id):
        order = Order.objects.filter(
            id=order_id, user=request.user
        ).first()

        if not order:
            return Response({'error': 'Pesanan tidak ditemukan.'},
                          status=status.HTTP_404_NOT_FOUND)

        if order.order_status not in ('pending', 'paid'):
            return Response({'error': 'Pesanan tidak dapat dibatalkan pada status saat ini.'},
                          status=status.HTTP_400_BAD_REQUEST)

        serializer = CancelOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data.get('reason', '')

        order.order_status = 'cancelled'
        order.save(update_fields=['order_status'])

        # Send notification
        msg = 'Pesanan berhasil dibatalkan.'
        if reason:
            msg += f' Alasan: {reason}'

        notify_order_update(
            user_id=request.user.id,
            order_id=order.id,
            order_number=order.order_number,
            status='cancelled',
            message=msg,
        )

        # Notify seller too
        if order.store and order.store.user_id:
            notify_order_update(
                user_id=order.store.user_id,
                order_id=order.id,
                order_number=order.order_number,
                status='cancelled',
                message=f'Pesanan {order.order_number} dibatalkan oleh pembeli.' + (f' Alasan: {reason}' if reason else ''),
            )

        return Response({
            'message': 'Pesanan berhasil dibatalkan.',
            'order': OrderDetailSerializer(order).data,
        })


class OrderHistoryView(generics.ListAPIView):
    """Order history with status filter."""
    serializer_class = OrderListSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        status_filter = self.request.query_params.get('status', '')
        qs = Order.objects.filter(user=self.request.user)
        if status_filter:
            qs = qs.filter(order_status=status_filter)
        return qs.select_related('store').prefetch_related('items')[:50]


# =============================================================================
# OFFLINE SALE — Pembelian langsung di toko
# =============================================================================

class OfflineSaleCreateView(views.APIView):
    """
    [DEPRECATED] Gunakan POST /api/orders/pos/checkout/ untuk multi-item.
    
    Catat penjualan offline single-item (legacy).
    Stok berkurang via FEFO stock_out, konsisten dengan POS.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    @transaction.atomic
    def post(self, request):
        serializer = OfflineSaleSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']

        # Validasi kepemilikan produk
        if product.store.user != request.user:
            return Response(
                {'error': 'Produk bukan milik toko Anda.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validasi stok mencukupi (available_stock = stock - reserved_stock)
        available = product.available_stock
        if available < quantity:
            return Response(
                {'error': f'Stok tidak mencukupi. Tersedia: {available}, diminta: {quantity}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # FEFO: stock_out (konsisten dengan POS checkout)
        master = MasterProduct.objects.filter(
            product_name__icontains=product.product_name
        ).first()

        if master:
            stock_result = stock_out(
                store=request.user.store,
                master_product=master,
                quantity=quantity,
                notes=f'Offline Sale: {product.product_name}',
                created_by=request.user,
                reference_type='offline_sale',
            )
            if not stock_result['success']:
                return Response(
                    {'error': stock_result.get('error', 'Gagal kurangi stok via FEFO.')},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # Fallback: langsung kurangi stock jika tidak ada master product
            Product.objects.filter(id=product.id).update(
                stock=F('stock') - quantity
            )

        # Refresh product
        product.refresh_from_db()

        # Simpan record penjualan offline
        offline_sale = OfflineSale.objects.create(
            store=product.store,
            product=product,
            product_name=product.product_name,
            quantity=quantity,
            price=serializer.validated_data.get('price', product.price),
            buyer_name=serializer.validated_data.get('buyer_name', ''),
            buyer_phone=serializer.validated_data.get('buyer_phone', ''),
            notes=serializer.validated_data.get('notes', ''),
            payment_method=serializer.validated_data.get('payment_method', 'cash'),
            recorded_by=request.user,
        )

        # Update store total sales
        Store.objects.filter(id=product.store_id).update(
            total_sales=F('total_sales') + float(offline_sale.total)
        )

        return Response({
            'message': f'Penjualan offline berhasil dicatat. Stok {product.product_name}: {product.stock + quantity} → {product.stock}',
            'offline_sale': OfflineSaleSerializer(offline_sale).data,
            'new_stock': product.stock,
        }, status=status.HTTP_201_CREATED)


# =============================================================================
# PACKING SESSION — Scan barang untuk pesanan online
# =============================================================================

class PackingStartView(views.APIView):
    """
    Mulai sesi packing untuk pesanan online.
    Seller scan barang yang keluar → FEFO stock_out.

    POST /api/orders/{order_id}/packing/start/
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request, order_id):
        order = Order.objects.filter(
            id=order_id, store__user=request.user, order_status='paid'
        ).first()

        if not order:
            return Response(
                {'error': 'Pesanan tidak ditemukan atau status bukan "paid".'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Tutup sesi packing sebelumnya yang masih aktif
        PackingSession.objects.filter(
            order=order, status='packing'
        ).update(status='cancelled')

        total_items = sum(item.qty for item in order.items.all())

        session = PackingSession.objects.create(
            order=order,
            store=request.user.store,
            status='packing',
            total_items=total_items,
        )

        # Update order status ke 'processed'
        order.order_status = 'processed'
        order.save(update_fields=['order_status'])

        return Response({
            'session_id': session.id,
            'total_items': total_items,
            'message': f'Sesi packing dimulai. Scan {total_items} item.',
        }, status=status.HTTP_201_CREATED)


class PackingScanItemView(views.APIView):
    """
    Scan satu item saat packing.
    Barcode/OCR → lookup master product → FEFO stock_out → record.

    POST /api/orders/{order_id}/packing/{session_id}/scan/
    {
        "barcode": "8991234567890",
        "quantity": 2
    }
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    @transaction.atomic
    def post(self, request, order_id, session_id):
        session = PackingSession.objects.filter(
            id=session_id, order_id=order_id,
            store=request.user.store, status='packing'
        ).first()

        if not session:
            return Response(
                {'error': 'Sesi packing tidak ditemukan atau sudah selesai.'},
                status=status.HTTP_404_NOT_FOUND
            )

        barcode = request.data.get('barcode', '').strip()
        quantity = int(request.data.get('quantity', 1))

        if not barcode:
            return Response(
                {'error': 'Barcode wajib diisi.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cari master product via barcode
        lookup_result = lookup_barcode(barcode, store=request.user.store)

        if not lookup_result.get('found'):
            return Response(
                {'error': f'Produk dengan barcode {barcode} tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND
            )

        master = lookup_result['master_product']
        mp_id = master['id']

        # Cari Product listing yang cocok
        product = Product.objects.filter(
            store=request.user.store,
            product_name__icontains=master['product_name']
        ).first()

        if not product:
            # Cari product dari order items
            order_item = session.order.items.filter(
                product__product_name__icontains=master['product_name']
            ).first()
            product = order_item.product if order_item else None

        if not product:
            return Response(
                {'error': 'Produk tidak ditemukan di pesanan ini.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Cari OrderItem yang cocok dan belum ter-scan penuh
        master_model = MasterProduct.objects.get(id=mp_id)

        # FEFO: stock_out dengan batch terdekat expiry
        stock_result = stock_out(
            store=request.user.store,
            master_product=master_model,
            quantity=quantity,
            notes=f'Packing Order #{session.order.order_number}',
            created_by=request.user,
            reference_type='packing',
            reference_id=str(session.id),
        )

        if not stock_result['success']:
            return Response(
                {'error': stock_result.get('error', 'Stok tidak mencukupi.')},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Record packed item
        batch_model = stock_result['transactions'][0]['batch_id'] if stock_result.get('transactions') else None
        batch = None
        if batch_model:
            batch = ProductBatch.objects.get(id=batch_model)

        # Cari order_item yang cocok
        order_item = session.order.items.filter(product=product).first()

        PackedItem.objects.create(
            packing_session=session,
            order_item=order_item,
            product=product,
            batch=batch,
            quantity=quantity,
        )

        # Update scanned count
        session.scanned_items = PackedItem.objects.filter(
            packing_session=session
        ).aggregate(total=Sum('quantity'))['total'] or 0
        session.save(update_fields=['scanned_items', 'updated_at'])

        # Release reserved_stock
        Product.objects.filter(id=product.id).update(
            reserved_stock=F('reserved_stock') - quantity
        )

        return Response({
            'success': True,
            'product_name': master['product_name'],
            'quantity': quantity,
            'scanned': session.scanned_items,
            'total': session.total_items,
            'progress': session.progress_pct,
            'message': f'{master["product_name"]} x{quantity} di-scan. '
                      f'Progress: {session.scanned_items}/{session.total_items}',
        })


class PackingCompleteView(views.APIView):
    """
    Selesaikan sesi packing.
    Semua item harus sudah di-scan.

    POST /api/orders/{order_id}/packing/{session_id}/complete/
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    @transaction.atomic
    def post(self, request, order_id, session_id):
        session = PackingSession.objects.filter(
            id=session_id, order_id=order_id,
            store=request.user.store, status='packing'
        ).first()

        if not session:
            return Response(
                {'error': 'Sesi packing tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if session.scanned_items < session.total_items:
            return Response({
                'error': f'Belum semua item di-scan. '
                         f'{session.scanned_items}/{session.total_items} item.',
                'scanned': session.scanned_items,
                'total': session.total_items,
            }, status=status.HTTP_400_BAD_REQUEST)

        # Selesaikan sesi
        session.status = 'completed'
        session.completed_at = timezone.now()
        session.save(update_fields=['status', 'completed_at', 'updated_at'])

        # Update status order
        order = session.order
        order.order_status = 'shipped'
        order.save(update_fields=['order_status'])

        return Response({
            'success': True,
            'message': 'Packing selesai! Semua item sudah di-scan dan stok berkurang.',
            'total_items': session.total_items,
        })


class PackingStatusView(views.APIView):
    """
    Cek status packing terkini.

    GET /api/orders/{order_id}/packing/status/
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request, order_id):
        session = PackingSession.objects.filter(
            order_id=order_id, store=request.user.store
        ).order_by('-started_at').first()

        if not session:
            return Response({'active': False, 'message': 'Belum ada sesi packing.'})

        return Response({
            'active': session.status == 'packing',
            'session_id': session.id,
            'status': session.status,
            'total_items': session.total_items,
            'scanned_items': session.scanned_items,
            'progress_pct': session.progress_pct,
            'started_at': session.started_at,
            'completed_at': session.completed_at,
            'items': [
                {
                    'product_name': p.product.product_name if p.product else '?',
                    'quantity': p.quantity,
                    'batch_number': p.batch.batch_number if p.batch else '-',
                    'scanned_at': p.scanned_at,
                }
                for p in session.packed_items.all()
            ],
        })


# =============================================================================
# POS OFFLINE — Multi-item scan & pay
# =============================================================================

class POSOfflineCreateView(views.APIView):
    """
    Mencatat penjualan offline dengan scan barcode (multi-item).
    Stok otomatis berkurang via FEFO.

    POST /api/orders/pos/checkout/
    {
        "items": [
            {"barcode": "8991234567890", "quantity": 2},
            {"barcode": "8991234567891", "quantity": 1}
        ],
        "buyer_name": "Budi",
        "payment_method": "cash"
    }
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    @transaction.atomic
    def post(self, request):
        items_data = request.data.get('items', [])
        if not items_data:
            return Response(
                {'error': 'Minimal 1 item wajib diisi.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        buyer_name = request.data.get('buyer_name', '')
        payment_method = request.data.get('payment_method', 'cash')
        notes = request.data.get('notes', '')

        created_sales = []
        errors = []
        total_amount = 0

        for entry in items_data:
            barcode = entry.get('barcode', '').strip()
            quantity = int(entry.get('quantity', 1))

            if not barcode:
                errors.append({'error': 'Barcode kosong.', 'item': entry})
                continue

            # Cari via barcode
            lookup_result = lookup_barcode(barcode, store=request.user.store)
            if not lookup_result.get('found'):
                errors.append({
                    'barcode': barcode,
                    'error': 'Produk tidak ditemukan.',
                })
                continue

            master = lookup_result['master_product']
            master_model = MasterProduct.objects.get(id=master['id'])

            # Cari Product listing
            product = Product.objects.filter(
                store=request.user.store,
                product_name__icontains=master['product_name']
            ).first()

            if not product:
                errors.append({
                    'barcode': barcode,
                    'error': f'Produk {master["product_name"]} tidak ditemukan di toko Anda.',
                })
                continue

            # Validasi stok
            available = product.available_stock
            if available < quantity:
                errors.append({
                    'product': master['product_name'],
                    'error': f'Stok tidak mencukupi. Tersedia: {available}',
                })
                continue

            # FEFO: stock_out
            stock_result = stock_out(
                store=request.user.store,
                master_product=master_model,
                quantity=quantity,
                notes=f'POS Offline: {buyer_name or "Anonymous"}',
                created_by=request.user,
                reference_type='pos_offline',
            )

            if not stock_result['success']:
                errors.append({
                    'product': master['product_name'],
                    'error': stock_result.get('error', 'Gagal kurangi stok.'),
                })
                continue

            # Catat offline sale
            sale = OfflineSale.objects.create(
                store=request.user.store,
                product=product,
                product_name=product.product_name,
                quantity=quantity,
                price=product.price,
                buyer_name=buyer_name,
                notes=notes,
                payment_method=payment_method,
                recorded_by=request.user,
            )

            created_sales.append(OfflineSaleSerializer(sale).data)
            total_amount += float(sale.total)

            # Update store total sales
            Store.objects.filter(id=product.store_id).update(
                total_sales=F('total_sales') + float(sale.total)
            )

        return Response({
            'success': len(errors) == 0,
            'sales': created_sales,
            'total_amount': total_amount,
            'total_items': len(created_sales),
            'errors': errors if errors else None,
            'message': f'{len(created_sales)} item berhasil dicatat. Total: Rp {total_amount:,.0f}',
        })


class OfflineSaleListView(generics.ListAPIView):
    """Daftar penjualan offline untuk seller."""
    serializer_class = OfflineSaleListSerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_queryset(self):
        return OfflineSale.objects.filter(
            store__user=self.request.user
        ).select_related('product').order_by('-created_at')
