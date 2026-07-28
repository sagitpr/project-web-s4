"""
Guest Checkout View — Public order placement without buyer account.

Allows anyone to place an order at a store by providing:
- Name, phone, delivery address
- Selected products with quantities
- Shipping method (Grab, Gojek, Mitra Sendiri)
- Payment method (Tunai, QRIS, Midtrans, Transfer, E-Wallet)

The order is recorded as an Order + OrderItem linked to the store's seller,
and the seller receives a real-time notification via WebSocket.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order, OrderItem, Delivery, ShippingMethod
from products.models import Product
from stores.models import Store
from accounts.permissions import IsSeller
from orders.views import notify_order_update, notify_stock_update
from inventory.services.fefo_engine import stock_out
from inventory.models import MasterProduct

logger = logging.getLogger(__name__)


class GuestCheckoutView(APIView):
    """
    Public Guest Checkout — no authentication required.
    
    POST /api/orders/guest-checkout/
    {
        "store_slug": "toko-abc",
        "items": [
            {"product_id": 1, "quantity": 2},
            {"product_id": 5, "quantity": 1}
        ],
        "buyer_name": "Budi Santoso",
        "buyer_phone": "081234567890",
        "delivery_address": "Jl. Merdeka No. 123, Jakarta",
        "shipping_method": "antar_sendiri",
        "payment_method": "cash"
    }
    
    Fields:
    - buyer_name: required
    - buyer_phone: required
    - delivery_address: required
    - shipping_method: optional (default: antar_sendiri)
      Options: grabexpress, gosend, mitra_pengiriman, antar_sendiri
    - payment_method: optional (default: cash)
      Options: cash, qris, midtrans, transfer, gopay, ovo
    """
    permission_classes = (permissions.AllowAny,)  # Public endpoint

    @transaction.atomic
    def post(self, request):
        store_slug = request.data.get('store_slug', '').strip()
        items_data = request.data.get('items', [])
        buyer_name = request.data.get('buyer_name', '').strip()
        buyer_phone = request.data.get('buyer_phone', '').strip()
        delivery_address = request.data.get('delivery_address', '').strip()
        shipping_method = request.data.get('shipping_method', 'antar_sendiri')
        payment_method = request.data.get('payment_method', 'cash')

        # ── Validation ──
        if not store_slug:
            return Response({'error': 'store_slug wajib diisi.'},
                          status=status.HTTP_400_BAD_REQUEST)
        if not items_data:
            return Response({'error': 'Minimal 1 item.'},
                          status=status.HTTP_400_BAD_REQUEST)
        if not buyer_name or not buyer_phone:
            return Response({'error': 'Nama dan nomor HP pembeli wajib diisi.'},
                          status=status.HTTP_400_BAD_REQUEST)
        if not delivery_address:
            return Response({'error': 'Alamat pengiriman wajib diisi.'},
                          status=status.HTTP_400_BAD_REQUEST)

        # ── Find Store ──
        try:
            store = Store.objects.get(slug=store_slug, status='active')
        except Store.DoesNotExist:
            return Response({'error': 'Toko tidak ditemukan.'},
                          status=status.HTTP_404_NOT_FOUND)

        # ── Find Shipping Method ──
        sm = ShippingMethod.objects.filter(code=shipping_method, is_active=True).first()

        # ── Process Items ──
        created_items = []
        total_amount = Decimal('0')
        product_ids = [item.get('product_id') for item in items_data]

        # Lock all product rows for race-condition-free stock check
        locked_products = {
            p.id: p
            for p in Product.objects.select_for_update().filter(
                id__in=product_ids, store=store, is_active=True
            )
        }

        errors = []
        for entry in items_data:
            pid = entry.get('product_id')
            qty = int(entry.get('quantity', 1))

            product = locked_products.get(pid)
            if not product:
                errors.append({'product_id': pid, 'error': 'Produk tidak ditemukan.'})
                continue
            if product.available_stock < qty:
                errors.append({
                    'product_id': pid,
                    'product_name': product.product_name,
                    'error': f'Stok tidak mencukupi. Tersedia: {product.available_stock}',
                })
                continue

            # Reserve stock
            Product.objects.filter(id=product.id).update(
                reserved_stock=F('reserved_stock') + qty
            )

            created_items.append({
                'product': product,
                'qty': qty,
                'price': product.price,
            })
            total_amount += product.price * qty

        if not created_items:
            return Response({
                'error': 'Tidak ada item yang dapat diproses.',
                'errors': errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        # ── Create Order ──
        shipping_cost = Decimal(str(sm.base_fee)) if sm else Decimal('0')
        order = Order.objects.create(
            store=store,
            subtotal=total_amount,
            shipping_cost=shipping_cost,
            total_price=total_amount + shipping_cost + Decimal('1500'),  # admin fee
            delivery_address=delivery_address,
            recipient_name=buyer_name,
            recipient_phone=buyer_phone,
            payment_method=payment_method,
            order_status='pending',
            notes=f'Pesanan dari {buyer_name} ({buyer_phone}) — Guest Checkout',
        )

        # ── Create Order Items ──
        for item in created_items:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                product_name=item['product'].product_name,
                product_photo=str(item['product'].product_photo.url) if item['product'].product_photo else '',
                qty=item['qty'],
                price=float(item['price']),
                subtotal=float(item['price'] * item['qty']),
            )

        # ── Create Delivery Record ──
        Delivery.objects.create(
            order=order,
            shipping_method=sm,
            estimated_time=sm.estimated_time if sm else None,
            delivery_status='menunggu_konfirmasi',
        )

        # ── Update Store Stats ──
        Store.objects.filter(id=store.id).update(
            total_sales=F('total_sales') + order.total_price
        )

        # ── Notify Seller via WebSocket ──
        if store.user_id:
            notify_order_update(
                user_id=store.user_id,
                order_id=order.id,
                order_number=order.order_number,
                status='pending',
                message=f'Pesanan baru dari {buyer_name}! Total: Rp {order.total_price:,.0f}. Segera diproses.',
            )

        # ── Broadcast Stock Reservation ──
        for item in created_items:
            notify_stock_update(
                store_id=store.id,
                product_id=item['product'].id,
                product_name=item['product'].product_name,
                stock_change=-item['qty'],
                action='stock_reserved',
                store_user_id=store.user_id,
            )

        return Response({
            'success': True,
            'order': {
                'order_number': order.order_number,
                'order_id': order.id,
                'total_price': float(order.total_price),
                'subtotal': float(total_amount),
                'shipping_cost': float(shipping_cost),
                'status': 'pending',
            },
            'message': f'Pesanan berhasil dibuat! Nomor pesanan: {order.order_number}. Seller akan segera menghubungi Anda.',
            'errors': errors if errors else None,
        }, status=status.HTTP_201_CREATED)


class TrackOrderPublicView(APIView):
    """
    Public tracking endpoint — no authentication required.
    GET /api/orders/track-public/?order_number=WRG-XXXXX
    Returns order details, items, delivery, timeline, driver info.
    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        order_number = request.query_params.get('order_number', '').strip()
        if not order_number:
            return Response({'error': 'order_number wajib diisi.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.select_related(
                'store', 'store__user', 'shipping_method'
            ).prefetch_related('items').get(order_number=order_number)
        except Order.DoesNotExist:
            return Response({'error': 'Pesanan tidak ditemukan.'}, status=status.HTTP_404_NOT_FOUND)

        # Build delivery data
        delivery_data = None
        from orders.models import Delivery as DeliveryModel
        try:
            delivery = DeliveryModel.objects.get(order=order)
            delivery_data = {
                'delivery_status': delivery.delivery_status,
                'delivery_status_label': self._status_label(delivery.delivery_status),
                'driver_name': delivery.driver_name or '',
                'driver_phone': delivery.driver_phone or '',
                'vehicle_plate': delivery.vehicle_plate or '',
                'vehicle_type': delivery.vehicle_type or '',
                'courier_provider': delivery.courier_provider or '',
                'tracking_number': delivery.tracking_number or '',
                'tracking_url': delivery.tracking_url or '',
                'pickup_code': delivery.pickup_code or '',
                'pod_photo': delivery.pod_photo.url if delivery.pod_photo else '',
                'pod_signature': delivery.pod_signature or '',
                'pod_notes': delivery.pod_notes or '',
                'estimated_time': delivery.estimated_time or '',
                'estimated_arrival': delivery.estimated_arrival or '',
                'driver_latitude': float(delivery.last_latitude) if delivery.last_latitude else None,
                'driver_longitude': float(delivery.last_longitude) if delivery.last_longitude else None,
                'picked_up_at': delivery.picked_up_at.isoformat() if delivery.picked_up_at else None,
                'delivered_at': delivery.delivered_at.isoformat() if delivery.delivered_at else None,
            }
        except DeliveryModel.DoesNotExist:
            delivery_data = None

        # Build items data
        items_data = []
        for item in order.items.all():
            items_data.append({
                'product_id': item.product_id,
                'product_name': item.product_name,
                'qty': item.qty,
                'price': float(item.price),
                'subtotal': float(item.subtotal),
                'product_photo': item.product_photo or '',
            })

        # Build timelines/milestones
        milestones = self._build_milestones(order)

        return Response({
            'success': True,
            'order': {
                'order_number': order.order_number,
                'order_status': order.order_status,
                'order_status_label': self._order_status_label(order.order_status),
                'store_name': order.store.store_name if order.store else '',
                'store_phone': order.store.phone if order.store else '',
                'store_logo': order.store.store_logo.url if order.store and order.store.store_logo else '',
                'subtotal': float(order.subtotal),
                'shipping_cost': float(order.shipping_cost),
                'admin_fee': float(order.admin_fee_buyer),
                'discount': float(order.discount),
                'total_price': float(order.total_price),
                'payment_method': order.payment_method,
                'recipient_name': order.recipient_name,
                'recipient_phone': order.recipient_phone,
                'delivery_address': order.delivery_address,
                'notes': order.notes,
                'courier': order.courier,
                'created_at': order.created_at.isoformat() if order.created_at else '',
                'completed_at': order.completed_at.isoformat() if order.completed_at else '',
            },
            'delivery': delivery_data,
            'items': items_data,
            'milestones': milestones,
        })

    def _build_milestones(self, order):
        """Build timeline milestones from order status."""
        if order.order_status == 'cancelled':
            return [{'status': 'dibatalkan', 'label': 'Pesanan Dibatalkan', 'icon': 'fa-ban', 'is_current': True}]

        # Try delivery milestones first
        try:
            delivery = order.delivery
            ds = delivery.delivery_status or 'menunggu_konfirmasi'
            delivery_milestones = [
                ('menunggu_konfirmasi', 'Pesanan Dibuat', 'fa-file-invoice'),
                ('diproses_penjual', 'Diproses Penjual', 'fa-box'),
                ('menunggu_penjemputan', 'Siap Diambil Kurir', 'fa-box-open'),
                ('kurir_menjemput', 'Kurir Menjemput', 'fa-motorcycle'),
                ('dalam_perjalanan', 'Dalam Perjalanan', 'fa-truck'),
                ('pesanan_diterima', 'Pesanan Diterima', 'fa-circle-check'),
            ]
            idx = -1
            for i, (key, _, _) in enumerate(delivery_milestones):
                if key == ds:
                    idx = i
                    break
            result = []
            for i, (key, label, icon) in enumerate(delivery_milestones):
                result.append({
                    'status': key,
                    'label': label,
                    'icon': icon,
                    'is_current': i == idx,
                    'is_completed': i <= idx,
                })
            return result
        except Exception:
            pass

        # Fall back to order status milestones
        status_milestones = [
            ('pending', 'Pesanan Dibuat', 'fa-file-invoice'),
            ('paid', 'Pembayaran Diterima', 'fa-credit-card'),
            ('processed', 'Diproses Penjual', 'fa-box'),
            ('shipped', 'Dikirim', 'fa-truck'),
            ('completed', 'Pesanan Selesai', 'fa-circle-check'),
        ]
        current_status = order.order_status
        result = []
        found = False
        for key, label, icon in status_milestones:
            if key == current_status:
                found = True
            result.append({
                'status': key,
                'label': label,
                'icon': icon,
                'is_current': key == current_status,
                'is_completed': found or key == current_status,
            })
        return result

    def _status_label(self, status_val):
        labels = {
            'menunggu_konfirmasi': 'Menunggu Konfirmasi',
            'diproses_penjual': 'Diproses Penjual',
            'menunggu_penjemputan': 'Siap Diambil',
            'kurir_menjemput': 'Kurir Menjemput',
            'dalam_perjalanan': 'Dalam Perjalanan',
            'pesanan_diterima': 'Pesanan Diterima',
            'dibatalkan': 'Dibatalkan',
        }
        return labels.get(status_val, status_val)

    def _order_status_label(self, status_val):
        labels = {
            'pending': 'Menunggu Pembayaran',
            'paid': 'Lunas',
            'processed': 'Diproses',
            'shipped': 'Dikirim',
            'completed': 'Selesai',
            'cancelled': 'Dibatalkan',
            'refunded': 'Dikembalikan',
        }
        return labels.get(status_val, status_val)
