"""
Orders views for Warungio Marketplace.
Cart management, order placement, order tracking.
"""

import logging

logger = logging.getLogger(__name__)
from asgiref.sync import async_to_sync
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone
from channels.layers import get_channel_layer
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample, OpenApiResponse
from rest_framework import serializers as drf_serializers, status, generics, permissions, views, filters
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend

from django.db.models import Prefetch

from .models import Cart, Order, OrderItem, Delivery, ShippingMethod, OfflineSale, PackingSession, PackedItem, MitraDriver, MitraDeliveryTariff
from .serializers import (
    CartSerializer, OrderListSerializer, OrderDetailSerializer,
    OrderCreateSerializer, OrderStatusSerializer, DeliverySerializer,
    ShippingMethodSerializer, CancelOrderSerializer,
    OfflineSaleSerializer, OfflineSaleListSerializer,
    MitraDriverSerializer, MitraTariffSerializer
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

# =============================================================================
# HELPER: Broadcast stock changes via WebSocket
# =============================================================================

def notify_stock_update(store_id, product_id, product_name, stock_change, action='stock_updated', store_user_id=None):
    """Broadcast stock change via WebSocket to store followers and seller.
    
    Args:
        store_id: The store whose product stock changed
        product_id: The product that changed
        product_name: Display name
        stock_change: Positive for stock increase, negative for decrease
        action: 'stock_reserved', 'stock_released', 'stock_deducted', 'stock_adjusted'
        store_user_id: Optional — if provided, also notifies the store owner directly
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            event = {
                'type': 'stock_update',
                'product_id': product_id,
                'product_name': product_name,
                'store_id': store_id,
                'stock_change': stock_change,
                'action': action,
            }
            # Broadcast to store followers
            async_to_sync(channel_layer.group_send)(
                f'store_{store_id}',
                event,
            )
            # Also notify the store owner/seller directly
            if store_user_id:
                async_to_sync(channel_layer.group_send)(
                    f'notifications_{store_user_id}',
                    event,
                )
    except Exception as e:
        _log = logging.getLogger('django_backend.orders')
        _log.warning('WebSocket broadcast error (stock update): %s', str(e))


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
        if getattr(self, "swagger_fake_view", False):
            return Cart.objects.none()

        return Cart.objects.filter(user=self.request.user).select_related(
            'product', 'product__store'
        )

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Add item to cart with select_for_update locking on product row.
        
        Locks the product row before reading available_stock to prevent
        race conditions when concurrent requests hit the same product.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Lock product row — guarantees stock snapshot is race-condition free
        # DRF PrimaryKeyRelatedField deserializes FK to the model instance
        product = serializer.validated_data.get('product')
        if product and isinstance(product, Product):
            # Re-fetch with lock for race-condition-free stock check
            product = Product.objects.select_for_update().get(id=product.id)
            requested_qty = serializer.validated_data.get('qty', 0)
            if requested_qty > product.available_stock:
                raise ValidationError({
                    'qty': [f'Stok tidak mencukupi. Tersedia: {product.available_stock}']
                })

        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CartDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Update or remove cart item."""
    serializer_class = CartSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user).select_related(
            'product', 'product__store'
        )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """
        Update cart item qty with select_for_update locking on product row.
        
        Locks the product row before re-validating available_stock to prevent
        race conditions when concurrent requests modify the same item.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # Lock product row — guarantees stock snapshot is race-condition free
        product_id = instance.product_id
        if product_id:
            product = Product.objects.select_for_update().get(id=product_id)
            requested_qty = serializer.validated_data.get('qty', instance.qty)
            if requested_qty > product.available_stock:
                raise ValidationError({
                    'qty': [f'Stok tidak mencukupi. Tersedia: {product.available_stock}']
                })

        self.perform_update(serializer)
        return Response(serializer.data)


@extend_schema(exclude=True)
class CartClearView(views.APIView):
    """Clear all cart items."""
    permission_classes = (permissions.IsAuthenticated,)

    def delete(self, request):
        Cart.objects.filter(user=request.user).delete()
        return Response({'message': 'Keranjang berhasil dikosongkan.'})


@extend_schema(exclude=True)
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
            201: OpenApiResponse(
                description='Pesanan berhasil dibuat',
                examples=[
                    OpenApiExample(
                        'Order Created',
                        value={'message': 'Pesanan berhasil dibuat.', 'orders': []},
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(
                description='Validation Error',
                examples=[
                    OpenApiExample('Validation Error', value={'error': 'Keranjang kosong.'}, response_only=True),
                ],
            ),
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
            # Use the store already prefetched via cart_items.select_related('product__store') — no extra query
            store = items[0].product.store if items else Store.objects.filter(id=store_id).first()
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

            # ── LOCK all product rows BEFORE checking stock ──
            # This prevents race conditions where two concurrent buyers
            # both pass the available_stock check for the last item.
            # select_for_update() acquires a row-level lock that blocks
            # concurrent transactions until this transaction completes.
            product_ids = list(set(item.product_id for item in items))
            if product_ids:
                locked_products = {
                    p.id: p
                    for p in Product.objects.select_for_update().filter(id__in=product_ids).order_by('id')
                }
            else:
                locked_products = {}

            # Create order items
            for cart_item in items:
                # Use the locked product object for race-condition-free stock check
                locked_product = locked_products.get(cart_item.product_id)
                if locked_product:
                    product = locked_product
                else:
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
                # Broadcast stock reservation to store followers + seller
                notify_stock_update(
                    store_id=store_id,
                    product_id=product.id,
                    product_name=product.product_name,
                    stock_change=-cart_item.qty,
                    action='stock_reserved',
                    store_user_id=store.user_id if store else None,
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
@extend_schema(exclude=True)
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


@extend_schema(exclude=True)
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
            200: OpenApiResponse(
                description='Order updated successfully',
                response=OrderDetailSerializer,
            ),
            400: OpenApiResponse(
                description='Bad Request',
                examples=[
                    OpenApiExample('Bad Request', value={'error': 'Pesan error'}, response_only=True),
                ],
            ),
            404: OpenApiResponse(
                description='Not Found',
                examples=[
                    OpenApiExample('Not Found', value={'error': 'Pesanan tidak ditemukan.'}, response_only=True),
                ],
            ),
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

        status_value = serializer.validated_data['status']            # ── Validation: Cancellation only for pending/paid/processed ──
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
                for item in order.items.prefetch_related('product').all():
                    if item.product:
                        # Release reserved_stock (stock tidak pernah berkurang saat order)
                        Product.objects.filter(id=item.product.id).update(
                            reserved_stock=F('reserved_stock') - item.qty,
                        )
                        # Broadcast stock release to store followers + seller
                        notify_stock_update(
                            store_id=order.store_id,
                            product_id=item.product.id,
                            product_name=item.product_name or item.product.product_name,
                            stock_change=item.qty,
                            action='stock_released',
                            store_user_id=order.store.user_id if order.store else None,
                        )
                Store.objects.filter(id=order.store_id).update(
                    total_sales=F('total_sales') - order.total_price
                )
                order.order_status = 'cancelled'
                order.save()
        else:
            order.save()

        # ── Credit seller wallet on order completion ──
        if status_value == 'completed' and order.store and order.store.user_id:
            try:
                from payments.services.wallet import credit_wallet
                result = credit_wallet(
                    user=order.store.user,
                    amount=float(order.total_price),
                    tx_type='payment',
                    description=f'Pendapatan dari pesanan #{order.order_number}',
                    reference_type='order',
                    reference_id=str(order.id),
                )
                logger.info('Seller wallet credited for completed order %s: Rp %s \u2192 Rp %s',
                           order.id, result['balance_before'], result['balance_after'])
            except Exception as e:
                logger.error('Failed to credit seller wallet for completed order %s: %s', order.id, e)

        # ── Broadcast delivery_update via WebSocket + DB for real-time tracking ──
        if delivery_status and order.user_id:
            notify_delivery_update(
                user_id=order.user_id,
                order_id=order.id,
                order_number=order.order_number,
                delivery_status=delivery_status,
                tracking_number=serializer.validated_data.get('tracking_number', order.tracking_number or ''),
                courier=serializer.validated_data.get('courier', order.courier or ''),
            )
            try:
                from notifications.services import notify_delivery_status
                notify_delivery_status(
                    user_id=order.user_id,
                    order_number=order.order_number,
                    order_id=order.id,
                    delivery_status=delivery_status,
                    courier=serializer.validated_data.get('courier', order.courier or ''),
                )
            except Exception as exc:
                logger.warning('Delivery status notify failed: %s', exc)

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
            200: OpenApiResponse(
                description='Tracking Data',
                examples=[
                    OpenApiExample(
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
                ],
            ),
            404: OpenApiResponse(
                description='Not Found',
                examples=[
                    OpenApiExample('Not Found', value={'error': 'Pesanan tidak ditemukan.'}, response_only=True),
                ],
            ),
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
                    # Credit seller wallet on auto-completion (tracking)
                    if order.store and order.store.user_id:
                        try:
                            from payments.services.wallet import credit_wallet
                            cr = credit_wallet(
                                user=order.store.user,
                                amount=float(order.total_price),
                                tx_type='payment',
                                description=f'Pendapatan dari pesanan #{order.order_number}',
                                reference_type='order',
                                reference_id=str(order.id),
                            )
                            logger.info('Seller wallet credited via tracking for order %s: Rp %s \u2192 Rp %s',
                                       order.id, cr['balance_before'], cr['balance_after'])
                        except Exception as exc:
                            logger.error('Failed to credit seller wallet for auto-completed order %s: %s', order.id, exc)
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
            try:
                from notifications.services import notify_delivery_status
                notify_delivery_status(
                    user_id=order.user_id,
                    order_number=order.order_number,
                    order_id=order.id,
                    delivery_status=new_status,
                    courier=delivery.courier_name or '',
                )
            except Exception as exc:
                logger.warning('Delivery status notify failed: %s', exc)

        return Response(result)


@extend_schema_view(
    post=extend_schema(
        summary='Batalkan Pesanan (Buyer)',
        description='Membatalkan pesanan oleh pembeli. '
                    'Hanya dapat dibatalkan jika status pesanan masih `pending` atau `paid`.',
        tags=['Orders'],
        request=CancelOrderSerializer,
        responses={
            200: OpenApiResponse(
                description='Order cancelled successfully',
                response=OrderDetailSerializer,
            ),
            400: OpenApiResponse(
                description='Bad Request',
                examples=[
                    OpenApiExample('Bad Request', value={'error': 'Pesanan tidak dapat dibatalkan pada status saat ini.'}, response_only=True),
                ],
            ),
        },
    ),
)
class BuyerCancelOrderView(views.APIView):
    """
    Cancel order by buyer (order owner).
    Only cancellable if status is 'pending' or 'paid'.
    """
    permission_classes = (permissions.IsAuthenticated,)

    @transaction.atomic
    def post(self, request, order_id):
        order = Order.objects.filter(
            id=order_id, user=request.user
        ).prefetch_related('items__product').first()

        if not order:
            return Response({'error': 'Pesanan tidak ditemukan.'},
                          status=status.HTTP_404_NOT_FOUND)

        if order.order_status not in ('pending', 'paid'):
            return Response({'error': 'Pesanan tidak dapat dibatalkan pada status saat ini.'},
                          status=status.HTTP_400_BAD_REQUEST)

        serializer = CancelOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data.get('reason', '')

        # Release reserved_stock atomically
        for item in order.items.all():
            if item.product:
                Product.objects.filter(id=item.product.id).update(
                    reserved_stock=F('reserved_stock') - item.qty,
                )
                # Broadcast stock update — reserved_stock released → available increases
                notify_stock_update(
                    store_id=order.store_id,
                    product_id=item.product.id,
                    product_name=item.product_name or item.product.product_name,
                    stock_change=item.qty,
                    action='stock_released',
                    store_user_id=order.store.user_id if order.store else None,
                )

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
            'message': 'Pesanan berhasil dibatalkan. Stok produk sudah dikembalikan.',
            'order': OrderDetailSerializer(order).data,
        })


@extend_schema(exclude=True)
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

@extend_schema(exclude=True)
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

        # Broadcast stock deduction to store followers + seller
        notify_stock_update(
            store_id=product.store_id,
            product_id=product.id,
            product_name=product.product_name,
            stock_change=-quantity,
            action='stock_deducted',
            store_user_id=product.store.user_id,
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

@extend_schema(exclude=True)
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
        ).prefetch_related('items').first()

        if not order:
            return Response(
                {'error': 'Pesanan tidak ditemukan atau status bukan "paid".'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Tutup sesi packing sebelumnya yang masih aktif
        PackingSession.objects.filter(
            order=order, status='packing'
        ).update(status='cancelled')

        # Items already prefetched — no N+1
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


@extend_schema(exclude=True)
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

        # Broadcast stock deduction to store followers + seller
        notify_stock_update(
            store_id=request.user.store.id,
            product_id=product.id,
            product_name=product.product_name,
            stock_change=-quantity,
            action='stock_deducted',
            store_user_id=request.user.store.user_id,
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


@extend_schema(exclude=True)
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


@extend_schema(exclude=True)
class PackingStatusView(views.APIView):
    """
    Cek status packing terkini.

    GET /api/orders/{order_id}/packing/status/
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request, order_id):
        session = PackingSession.objects.filter(
            order_id=order_id, store=request.user.store
        ).order_by('-started_at').prefetch_related(
            Prefetch('packed_items', queryset=PackedItem.objects.select_related('product', 'batch'))
        ).first()

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

@extend_schema(exclude=True)
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

            # Broadcast POS stock deduction to store followers + seller
            notify_stock_update(
                store_id=request.user.store.id,
                product_id=product.id,
                product_name=product.product_name,
                stock_change=-quantity,
                action='stock_deducted',
                store_user_id=request.user.store.user_id,
            )

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


@extend_schema(exclude=True)
class OfflineSaleListView(generics.ListAPIView):
    """Daftar penjualan offline untuk seller."""
    serializer_class = OfflineSaleListSerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_queryset(self):
        return OfflineSale.objects.filter(
            store__user=self.request.user
        ).select_related('product').order_by('-created_at')

# =============================================================================
# GRABEXPRESS / GOSEND WEBHOOK HANDLERS
# =============================================================================

# =============================================================================
# BASE DELIVERY WEBHOOK (shared by GrabExpress, GoSend, Mitra)
# =============================================================================

DELIVERY_WEBHOOK_STATUS_MAP = {
    'grabexpress': {
        'delivery.assigned': 'menunggu_penjemputan',
        'delivery.picked_up': 'kurir_menjemput',
        'delivery.in_transit': 'dalam_perjalanan',
        'delivery.arrived': 'dalam_perjalanan',
        'delivery.delivered': 'pesanan_diterima',
        'delivery.cancelled': 'dibatalkan',
    },
    'gosend': {
        'order.assigned': 'menunggu_penjemputan',
        'order.picked_up': 'kurir_menjemput',
        'order.in_transit': 'dalam_perjalanan',
        'order.arrived': 'dalam_perjalanan',
        'order.delivered': 'pesanan_diterima',
        'order.cancelled': 'dibatalkan',
    },
    'mitra_pengiriman': {
        'driver_assigned': 'menunggu_penjemputan',
        'picked_up': 'kurir_menjemput',
        'in_transit': 'dalam_perjalanan',
        'arrived': 'dalam_perjalanan',
        'delivered': 'pesanan_diterima',
        'cancelled': 'dibatalkan',
    },
}

DELIVERY_SIGNATURE_HEADERS = {
    'grabexpress': ['X-Grab-Signature', 'Authorization'],
    'gosend': ['X-Gojek-Signature', 'X-Signature'],
    'mitra_pengiriman': ['X-Mitra-Signature', 'X-Signature'],
}


def _process_delivery_webhook(request, provider):
    from django.db import transaction
    from django.utils import timezone
    from .services.delivery_client import get_grab_client, get_gosend_client

    if provider == 'grabexpress':
        client = get_grab_client()
    elif provider == 'gosend':
        client = get_gosend_client()
    else:
        client = None

    if client and client.is_available():
        headers = DELIVERY_SIGNATURE_HEADERS.get(provider, [])
        signature = ''
        for h in headers:
            sig = request.headers.get(h, '')
            if sig:
                signature = sig
                break
        if not signature:
            logger.warning(f'{provider} webhook missing signature header')
            return Response({'status': 'invalid_signature'}, status=status.HTTP_400_BAD_REQUEST)
        if not client.verify_webhook_signature(request.body, signature):
            logger.warning(f'{provider} webhook signature verification failed')
            return Response({'status': 'invalid_signature'}, status=status.HTTP_400_BAD_REQUEST)

    data = request.data
    event = data.get('event', data.get('type', ''))

    delivery_id = (
        data.get('deliveryId') or data.get('delivery_id')
        or data.get('orderId') or data.get('order_id')
        or data.get('id') or ''
    )
    if not delivery_id:
        return Response({'status': 'missing_delivery_id'}, status=status.HTTP_400_BAD_REQUEST)

    status_map = DELIVERY_WEBHOOK_STATUS_MAP.get(provider, {})
    internal_status = status_map.get(event, '')
    if not internal_status:
        logger.warning(f'{provider} unknown event: {event}')
        return Response({'status': 'unknown_event'})

    try:
        if provider == 'grabexpress':
            delivery = Delivery.objects.select_related('order').get(grab_delivery_id=delivery_id)
        elif provider == 'gosend':
            delivery = Delivery.objects.select_related('order').get(gojek_order_id=delivery_id)
        elif provider == 'mitra_pengiriman':
            delivery = Delivery.objects.select_related('order').get(mitra_delivery_id=delivery_id)
        else:
            delivery = Delivery.objects.select_related('order').get(tracking_number=delivery_id)
    except (Delivery.DoesNotExist, Delivery.MultipleObjectsReturned):
        try:
            delivery = Delivery.objects.select_related('order').get(tracking_number=delivery_id)
        except Delivery.DoesNotExist:
            logger.warning(f'{provider} webhook: delivery {delivery_id} not found')
            return Response({'status': 'delivery_not_found'}, status=status.HTTP_404_NOT_FOUND)

    with transaction.atomic():
        delivery.delivery_status = internal_status
        delivery.courier_provider = provider

        driver_info = data.get('driver', data.get('rider', data.get('driver_info', {})))
        if driver_info and isinstance(driver_info, dict):
            delivery.driver_name = driver_info.get('name', driver_info.get('driverName', delivery.driver_name or ''))
            delivery.driver_phone = driver_info.get('phone', driver_info.get('driverPhone', delivery.driver_phone or ''))

        if internal_status == 'kurir_menjemput':
            delivery.picked_up_at = timezone.now()
        elif internal_status == 'pesanan_diterima':
            delivery.delivered_at = timezone.now()
            delivery.order.completed_at = timezone.now()
            delivery.order.order_status = 'completed'
            delivery.order.save(update_fields=['completed_at', 'order_status'])
        elif internal_status == 'dibatalkan':
            delivery.cancelled_at = timezone.now()

        delivery.save()

    if delivery.order.user_id:
        notify_delivery_update(
            user_id=delivery.order.user_id,
            order_id=delivery.order.id,
            order_number=delivery.order.order_number,
            delivery_status=internal_status,
            tracking_number=delivery_id,
            courier=provider.capitalize(),
        )
        try:
            from notifications.services import notify_delivery_status
            notify_delivery_status(
                user_id=delivery.order.user_id,
                order_number=delivery.order.order_number,
                order_id=delivery.order.id,
                delivery_status=internal_status,
                courier=provider.capitalize(),
            )
        except Exception as exc:
            logger.warning('Delivery status notify failed: %s', exc)

    logger.info(f'{provider} webhook: order #{delivery.order.id} status={internal_status}')
    return None


@extend_schema(exclude=True)
class DeliveryWebhookView(views.APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, provider=''):
        provider = provider or request.data.get('provider', '').lower()
        if not provider:
            path = request.path.lower()
            if 'grab' in path:
                provider = 'grabexpress'
            elif 'gojek' in path or 'gosend' in path:
                provider = 'gosend'
            elif 'mitra' in path:
                provider = 'mitra_pengiriman'
        if provider not in DELIVERY_WEBHOOK_STATUS_MAP:
            return Response({'status': 'unknown_provider'}, status=status.HTTP_400_BAD_REQUEST)
        result = _process_delivery_webhook(request, provider)
        if result is not None:
            return result
        return Response({'status': 'ok'})


# =============================================================================
# DELIVERY COURIER RATE CALCULATION
# =============================================================================

@extend_schema(exclude=True)
class DeliveryRateView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        from .services.delivery_client import get_grab_client, get_gosend_client
        from .services.distance import calculate_haversine_distance, estimate_shipping_fee

        courier = request.data.get('courier', '').lower()
        service_type = request.data.get('service_type', 'Instant')
        origin = {
            'latitude': request.data.get('origin_lat'),
            'longitude': request.data.get('origin_lng'),
            'address': request.data.get('origin_address', ''),
        }
        destination = {
            'latitude': request.data.get('destination_lat'),
            'longitude': request.data.get('destination_lng'),
            'address': request.data.get('destination_address', ''),
        }
        items = request.data.get('items', [])
        if not items:
            items = [{'name': 'Pesanan', 'quantity': 1, 'weight_kg': 0.5}]

        if courier == 'grabexpress':
            client = get_grab_client()
            result = client.calculate_rate(origin, destination, items, service_type)
        elif courier == 'gosend':
            client = get_gosend_client()
            result = client.calculate_rate(origin, destination, items, service_type)
        else:
            d = calculate_haversine_distance(
                origin.get('latitude'), origin.get('longitude'),
                destination.get('latitude'), destination.get('longitude'),
            )
            distance = d if d is not None and d > 0 else 3.0
            result = {
                'total_fee': float(estimate_shipping_fee(5000, distance)),
                'currency': 'IDR',
                'estimated_time': 'Estimasi sesuai kurir',
                'distance_km': round(distance, 2),
                'provider': 'generic',
                '_fallback': True,
            }
        if not result:
            return Response({'error': 'Gagal menghitung ongkos kirim.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


@extend_schema(exclude=True)
class DeliveryAutoBookView(views.APIView):
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    @transaction.atomic
    def post(self, request):
        from .services.delivery_client import auto_book_courier
        order_id = request.data.get('order_id')
        courier = request.data.get('courier', 'grabexpress').lower()
        service_type = request.data.get('service_type', 'Instant')
        if not order_id:
            return Response({'error': 'order_id wajib diisi.'}, status=status.HTTP_400_BAD_REQUEST)
        order = Order.objects.filter(
            id=order_id, store__user=request.user
        ).select_related('store').prefetch_related('items').first()
        if not order:
            return Response({'error': 'Pesanan tidak ditemukan.'}, status=status.HTTP_404_NOT_FOUND)
        if order.order_status not in ('paid', 'processed'):
            return Response({'error': 'Pesanan harus berstatus Lunas atau Diproses.'}, status=status.HTTP_400_BAD_REQUEST)
        result = auto_book_courier(order, courier, service_type)
        if not result:
            return Response({'error': f'Gagal membooking {courier}. Silakan coba manual.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'success': True,
            'message': f'{courier} berhasil dibooking. Kurir akan segera menjemput.',
            'delivery_id': result.get('delivery_id'),
            'tracking_url': result.get('tracking_url'),
            'estimated_time': result.get('estimated_time'),
            'status': result.get('status'),
        })


@extend_schema(exclude=True)
class DeliveryLivePositionView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, order_id):
        from .services.distance import calculate_haversine_distance
        order = Order.objects.filter(id=order_id, user=request.user).select_related('delivery').first()
        if not order:
            return Response({'error': 'Pesanan tidak ditemukan.'}, status=status.HTTP_404_NOT_FOUND)
        try:
            delivery = order.delivery
        except Delivery.DoesNotExist:
            return Response({'error': 'Belum ada informasi pengiriman.'}, status=status.HTTP_404_NOT_FOUND)
        if delivery.delivery_status in ('pesanan_diterima', 'dibatalkan'):
            return Response({'active': False, 'message': 'Pengiriman selesai.'})

        store = delivery.order.store
        delivery_status_val = delivery.delivery_status or 'menunggu_konfirmasi'
        origin_lat = float(store.latitude) if store and store.latitude else -6.2
        origin_lng = float(store.longitude) if store and store.longitude else 106.8
        dest_lat = float(delivery.buyer_latitude) if delivery.buyer_latitude else -6.3
        dest_lng = float(delivery.buyer_longitude) if delivery.buyer_longitude else 106.9

        progress_map = {
            'menunggu_konfirmasi': -0.1, 'diproses_penjual': -0.05,
            'menunggu_penjemputan': 0.0, 'kurir_menjemput': 0.2,
            'dalam_perjalanan': 0.6, 'pesanan_diterima': 1.0,
        }
        progress = progress_map.get(delivery_status_val, 0.0)
        lat = origin_lat + (dest_lat - origin_lat) * progress
        lng = origin_lng + (dest_lng - origin_lng) * progress
        total_dist = calculate_haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng) or 3.0
        remaining_dist = total_dist * (1 - progress)
        eta_minutes = max(1, int(remaining_dist * 2))

        return Response({
            'active': True,
            'position': {'latitude': round(lat, 7), 'longitude': round(lng, 7)},
            'origin': {'latitude': origin_lat, 'longitude': origin_lng},
            'destination': {'latitude': dest_lat, 'longitude': dest_lng},
            'progress': progress,
            'eta_minutes': eta_minutes,
            'estimated_time': f'{eta_minutes} menit lagi' if eta_minutes > 0 else 'Hampir sampai',
            'source': 'interpolated',
        })


# =============================================================================
# MITRA PENGIRIMAN — Internal fleet management
# =============================================================================

@extend_schema(exclude=True)
class MitraDriverListCreateView(generics.ListCreateAPIView):
    serializer_class = MitraDriverSerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_queryset(self):
        return MitraDriver.objects.filter(store=self.request.user.store).order_by('-total_deliveries')

    def perform_create(self, serializer):
        serializer.save(store=self.request.user.store)


@extend_schema(exclude=True)
class MitraDriverDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MitraDriverSerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_queryset(self):
        return MitraDriver.objects.filter(store=self.request.user.store)


@extend_schema(exclude=True)
class MitraTariffListCreateView(generics.ListCreateAPIView):
    serializer_class = MitraTariffSerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_queryset(self):
        return MitraDeliveryTariff.objects.filter(store=self.request.user.store, is_active=True)

    def perform_create(self, serializer):
        serializer.save(store=self.request.user.store)


@extend_schema(exclude=True)
class MitraAssignDriverView(views.APIView):
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    @transaction.atomic
    def post(self, request):
        delivery_id = request.data.get('delivery_id')
        driver_id = request.data.get('driver_id')
        if not delivery_id or not driver_id:
            return Response({'error': 'delivery_id dan driver_id wajib diisi.'}, status=status.HTTP_400_BAD_REQUEST)
        delivery = Delivery.objects.filter(
            id=delivery_id, order__store__user=request.user
        ).select_related('order').first()
        if not delivery:
            return Response({'error': 'Pengiriman tidak ditemukan.'}, status=status.HTTP_404_NOT_FOUND)
        driver = MitraDriver.objects.filter(
            id=driver_id, store=request.user.store, is_active=True
        ).first()
        if not driver:
            return Response({'error': 'Driver tidak ditemukan atau tidak aktif.'}, status=status.HTTP_404_NOT_FOUND)
        delivery.assigned_driver = driver
        delivery.driver_name = driver.name
        delivery.driver_phone = driver.phone
        delivery.delivery_status = 'menunggu_penjemputan'
        delivery.courier_provider = 'mitra_pengiriman'
        delivery.save(update_fields=[
            'assigned_driver', 'driver_name', 'driver_phone',
            'delivery_status', 'courier_provider'
        ])
        driver.total_deliveries += 1
        driver.save(update_fields=['total_deliveries'])
        if delivery.order.user_id:
            notify_delivery_update(
                user_id=delivery.order.user_id,
                order_id=delivery.order.id,
                order_number=delivery.order.order_number,
                delivery_status='menunggu_penjemputan',
                courier='Mitra Pengiriman',
            )
            try:
                from notifications.services import notify_delivery_status
                notify_delivery_status(
                    user_id=delivery.order.user_id,
                    order_number=delivery.order.order_number,
                    order_id=delivery.order.id,
                    delivery_status='menunggu_penjemputan',
                    courier='Mitra Pengiriman',
                )
            except Exception as exc:
                logger.warning('Delivery status notify failed: %s', exc)
        return Response({
            'success': True,
            'message': f'Driver {driver.name} berhasil ditugaskan.',
            'driver_name': driver.name,
            'driver_phone': driver.phone,
        })


# =============================================================================
# QR CODE GENERATION & VERIFICATION + POD
# =============================================================================

@extend_schema(exclude=True)
class GenerateDeliveryQRView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, order_id):
        delivery = Delivery.objects.filter(order_id=order_id).select_related('order').first()
        if not delivery:
            return Response({'error': 'Pengiriman tidak ditemukan.'}, status=status.HTTP_404_NOT_FOUND)

        order = delivery.order
        is_owner = order.user_id == request.user.id
        is_seller = order.store and order.store.user_id == request.user.id
        is_admin = request.user.is_staff or request.user.is_superuser or getattr(request.user, 'role', '') == 'admin'

        if not (is_owner or is_seller or is_admin):
            return Response({'error': 'Tidak memiliki akses.'}, status=status.HTTP_403_FORBIDDEN)

        code_type = request.data.get('code_type', 'pickup')
        if code_type not in ('pickup', 'delivery'):
            return Response({'error': 'code_type harus "pickup" atau "delivery".'}, status=status.HTTP_400_BAD_REQUEST)

        qr_code = generate_qr_code(delivery, code_type)
        if code_type == 'delivery':
            delivery.qr_delivery_code = qr_code
        else:
            delivery.qr_pickup_code = qr_code
        delivery.save(update_fields=['qr_delivery_code', 'qr_pickup_code'])

        return Response({
            'success': True,
            'qr_code': qr_code,
            'code_type': code_type,
            'message': f'QR {code_type} berhasil dibuat.',
        })


@extend_schema(exclude=True)
class VerifyDeliveryQRView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, order_id):
        delivery = Delivery.objects.filter(order_id=order_id).select_related('order').first()
        if not delivery:
            return Response({'error': 'Pengiriman tidak ditemukan.'}, status=status.HTTP_404_NOT_FOUND)

        order = delivery.order
        is_seller = order.store and order.store.user_id == request.user.id
        is_admin = request.user.is_staff or request.user.is_superuser or getattr(request.user, 'role', '') == 'admin'
        is_driver = delivery.assigned_driver and delivery.assigned_driver.id == request.user.id

        if not (is_seller or is_admin or is_driver):
            return Response({'error': 'Tidak memiliki akses.'}, status=status.HTTP_403_FORBIDDEN)

        qr_code = request.data.get('qr_code', '')
        code_type = request.data.get('code_type', 'pickup')

        if not qr_code:
            return Response({'error': 'qr_code wajib diisi.'}, status=status.HTTP_400_BAD_REQUEST)
        if code_type not in ('pickup', 'delivery'):
            return Response({'error': 'code_type harus "pickup" atau "delivery".'}, status=status.HTTP_400_BAD_REQUEST)

        result = verify_qr_code(delivery, qr_code, code_type)
        if not result['valid']:
            return Response({'success': False, 'error': result.get('error', 'QR Code tidak valid.')}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if code_type == 'pickup':
                delivery.delivery_status = 'kurir_menjemput' if delivery.courier_provider in ('grabexpress', 'gosend') else 'dalam_perjalanan'
                delivery.picked_up_at = timezone.now()
            else:
                delivery.delivery_status = 'pesanan_diterima'
                delivery.delivered_at = timezone.now()
            delivery.save(update_fields=['delivery_status', 'picked_up_at', 'delivered_at'])
            if code_type == 'delivery':
                order.order_status = 'completed'
                order.completed_at = timezone.now()
                order.save(update_fields=['order_status', 'completed_at'])

        if order.user_id:
            notify_delivery_update(
                user_id=order.user_id,
                order_id=order.id,
                order_number=order.order_number,
                delivery_status=delivery.delivery_status,
                courier=delivery.courier_provider or delivery.courier_name or 'Mitra Pengiriman',
            )
            try:
                from notifications.services import notify_delivery_status
                notify_delivery_status(
                    user_id=order.user_id,
                    order_number=order.order_number,
                    order_id=order.id,
                    delivery_status=delivery.delivery_status,
                    courier=delivery.courier_provider or delivery.courier_name or 'Mitra Pengiriman',
                )
            except Exception as exc:
                logger.warning('Delivery status notify failed: %s', exc)

        return Response({
            'success': True,
            'message': f'QR {code_type} berhasil diverifikasi.',
            'delivery_status': delivery.delivery_status,
            'delivery_id': delivery.id,
        })


@extend_schema(exclude=True)
class DeliveryPODUploadView(views.APIView):
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request, order_id):
        delivery = Delivery.objects.filter(
            order_id=order_id, order__store__user=request.user
        ).first()
        if not delivery:
            return Response({'error': 'Pengiriman tidak ditemukan.'}, status=status.HTTP_404_NOT_FOUND)

        pod_photo = request.FILES.get('pod_photo')
        if pod_photo:
            delivery.pod_photo = pod_photo

        pod_signature = request.data.get('pod_signature', '')
        if pod_signature:
            delivery.pod_signature = pod_signature

        pod_notes = request.data.get('pod_notes', '')
        if pod_notes:
            delivery.pod_notes = pod_notes

        delivery.pod_signed_at = timezone.now()
        delivery.save()

        return Response({
            'success': True,
            'message': 'Bukti pengiriman (POD) berhasil diupload.',
            'pod_photo_url': delivery.pod_photo.url if delivery.pod_photo else '',
            'pod_signed_at': delivery.pod_signed_at.isoformat() if delivery.pod_signed_at else '',
        })


class GuestReviewCreateView(views.APIView):
    """
    Public endpoint for guests to submit product reviews after order completion.
    Validates via order_number + phone number.
    POST /api/orders/guest-review/
    {
        "order_number": "WRG-ABC123",
        "phone": "081234567890",
        "product_id": 5,
        "rating": 4,
        "comment": "Produk bagus, recommended!"
    }
    """
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        order_number = request.data.get('order_number', '').strip()
        phone = request.data.get('phone', '').strip()
        product_id = request.data.get('product_id')
        rating = request.data.get('rating')
        comment = request.data.get('comment', '').strip()

        # Validation
        if not order_number or not phone:
            return Response({'error': 'Order number dan nomor HP wajib diisi.'}, status=status.HTTP_400_BAD_REQUEST)
        if not product_id:
            return Response({'error': 'Produk wajib dipilih.'}, status=status.HTTP_400_BAD_REQUEST)
        if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
            return Response({'error': 'Rating harus antara 1-5.'}, status=status.HTTP_400_BAD_REQUEST)

        # Find order and verify phone matches
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return Response({'error': 'Pesanan tidak ditemukan.'}, status=status.HTTP_404_NOT_FOUND)

        # Verify phone number matches the order's recipient phone
        recipient_phone = getattr(order, 'recipient_phone', '')
        # Normalize both phones for comparison
        if recipient_phone and phone:
            norm_phone = phone.replace(' ', '').replace('-', '').replace('+', '').lstrip('0')
            norm_recipient = recipient_phone.replace(' ', '').replace('-', '').replace('+', '').lstrip('0')
            is_phone_match = norm_phone == norm_recipient
        else:
            is_phone_match = False

        if not is_phone_match:
            return Response({'error': 'Nomor HP tidak sesuai dengan pesanan ini.'}, status=status.HTTP_403_FORBIDDEN)

        # Check order is completed or delivered
        delivery = getattr(order, 'delivery', None)
        is_delivered = delivery and delivery.delivery_status == 'pesanan_diterima'
        if order.order_status != 'completed' and not is_delivered:
            return Response({'error': 'Ulasan hanya dapat diberikan setelah pesanan selesai.'}, status=status.HTTP_400_BAD_REQUEST)

        # Verify product belongs to this order's store
        try:
            product = Product.objects.get(id=product_id, store=order.store)
        except Product.DoesNotExist:
            return Response({'error': 'Produk tidak ditemukan di toko ini.'}, status=status.HTTP_404_NOT_FOUND)

        # Check duplicate review for this order_number + product
        from products.models import GuestReview
        existing = GuestReview.objects.filter(order_number=order_number, product=product).first()
        if existing:
            return Response({'error': 'Anda sudah memberikan ulasan untuk produk ini.'}, status=status.HTTP_409_CONFLICT)

        # Create review
        review = GuestReview.objects.create(
            order_number=order_number,
            phone=phone,
            product=product,
            rating=rating,
            comment=comment,
            is_verified=True,
        )

        logger.info('GUEST REVIEW — Order: %s | Phone: %s | Product: %s | Rating: %d',
                    order_number, phone, product.product_name, rating)

        return Response({
            'success': True,
            'message': 'Terima kasih! Ulasan Anda telah dikirim.',
            'review_id': review.id,
        }, status=status.HTTP_201_CREATED)
