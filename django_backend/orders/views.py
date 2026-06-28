"""
Orders views for Warungio Marketplace.
Cart management, order placement, order tracking.
"""

from asgiref.sync import async_to_sync
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from channels.layers import get_channel_layer
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from rest_framework import serializers as drf_serializers, status, generics, permissions, views, filters
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend

from .models import Cart, Order, OrderItem, Delivery, ShippingMethod
from .serializers import (
    CartSerializer, OrderListSerializer, OrderDetailSerializer,
    OrderCreateSerializer, OrderStatusSerializer, DeliverySerializer,
    ShippingMethodSerializer, CancelOrderSerializer
)
from stores.models import Store
from products.models import Product
from accounts.permissions import IsSeller, IsOrderOwner
from notifications.models import Notification
from .services.courier_tracking import get_tracking_status


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
    except Exception:
        pass  # WebSocket layer unavailable silently


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
    except Exception:
        pass


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

            order = Order.objects.create(
                user=user,
                store_id=store_id,
                shipping_method=shipping_method,
                subtotal=0,
                total_price=0,
                shipping_cost=float(shipping_method.base_fee) if shipping_method else 0,
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
                
                if product.stock < cart_item.qty:
                    raise ValidationError(
                        f"Stok {product.product_name} tidak mencukupi."
                    )

                # Reduce stock atomically
                Product.objects.filter(id=product.id).update(
                    stock=F('stock') - cart_item.qty,
                    sold_count=F('sold_count') + cart_item.qty
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
                        Product.objects.filter(id=item.product.id).update(
                            stock=F('stock') + item.qty,
                            sold_count=F('sold_count') - item.qty
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
            except Exception:
                pass

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
