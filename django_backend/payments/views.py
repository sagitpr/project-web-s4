"""
Payments views for Warungio Marketplace.
Midtrans Snap payment gateway integration.
"""

import json
import hashlib
import hmac
import logging
import requests
from asgiref.sync import async_to_sync
from datetime import timedelta

logger = logging.getLogger(__name__)
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from channels.layers import get_channel_layer
from rest_framework import status, generics, permissions, views
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from accounts.permissions import IsSeller

from .models import Payment, PaymentMethod, MidtransTransaction, BankAccount
from .serializers import (
    PaymentMethodSerializer, PaymentSerializer, MidtransSnapRequest,
    MidtransNotificationSerializer, PaymentHistorySerializer, BankAccountSerializer
)
from orders.models import Order


def notify_payment_update(user_id, order_id, order_number, payment_status, message=''):
    """Broadcast payment update via WebSocket to buyer."""
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'notifications_{user_id}',
                {
                    'type': 'payment_update',
                    'order_id': order_id,
                    'order_number': order_number,
                    'status': payment_status,
                    'message': message,
                }
            )
    except Exception as e:
        logger.error('WebSocket broadcast error (payment update): %s', str(e))


class PaymentMethodListView(generics.ListAPIView):
    """List available payment methods."""
    queryset = PaymentMethod.objects.filter(is_active=True)
    serializer_class = PaymentMethodSerializer
    permission_classes = (permissions.AllowAny,)


class CreateSnapTransactionView(views.APIView):
    """Create Midtrans Snap transaction."""
    permission_classes = (permissions.IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = MidtransSnapRequest(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data['order_id']
        payment_method = serializer.validated_data['payment_method']

        order = Order.objects.filter(id=order_id, user=request.user).first()
        if not order:
            return Response({'error': 'Pesanan tidak ditemukan.'},
                          status=status.HTTP_404_NOT_FOUND)

        if order.order_status not in ['pending', 'paid']:
            return Response({'error': 'Pesanan sudah diproses.'},
                          status=status.HTTP_400_BAD_REQUEST)

        # Prepare Midtrans transaction parameters
        transaction_details = {
            'order_id': f"WRG-{order.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
            'gross_amount': int(float(order.total_price)),
        }

        customer_details = {
            'first_name': order.user.full_name or order.user.email,
            'email': order.user.email,
            'phone': str(order.user.phone) if order.user.phone else '',
        }

        item_details = []
        for item in order.items.all():
            item_details.append({
                'id': str(item.product_id or 0),
                'price': int(float(item.price)),
                'quantity': item.qty,
                'name': item.product_name[:50],
            })

        # Add shipping as item
        if float(order.shipping_cost) > 0:
            item_details.append({
                'id': 'SHIPPING',
                'price': int(float(order.shipping_cost)),
                'quantity': 1,
                'name': 'Biaya Pengiriman',
            })

        # Build request payload — credit_card config available for all Snap methods
        payload = {
            'transaction_details': transaction_details,
            'customer_details': customer_details,
            'item_details': item_details,
            'credit_card': {'secure': True},
        }

        # Payment method specific settings
        # NOTE: Only set payment_type for specific methods.
        # When payment_method is 'credit_card' (generic Snap default) or unknown,
        # omit payment_type so Snap auto-presents ALL available payment methods
        # (QRIS, bank transfer, e-wallet, kartu kredit, etc.)
        if payment_method == 'bank_transfer':
            bank = serializer.validated_data.get('bank', 'bca')
            payload['payment_type'] = 'bank_transfer'
            payload['bank_transfer'] = {'bank': bank}
        elif payment_method in ['gopay', 'shopeepay', 'ovo', 'dana']:
            payload['payment_type'] = payment_method
        elif payment_method == 'qris':
            payload['payment_type'] = 'qris'
            payload['qris'] = {'acquirer': 'gopay'}
        else:
            # Generic Snap — don't set payment_type, let Snap auto-present all methods
            pass

        # Call Midtrans Snap API
        try:
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Basic {self._encode_auth(settings.MIDTRANS_SERVER_KEY)}',
            }
            
            response = requests.post(
                settings.MIDTRANS_SNAP_URL,
                json=payload,
                headers=headers,
                timeout=30,
            )
            
            if response.status_code not in [200, 201]:
                return Response({
                    'error': 'Gagal membuat transaksi pembayaran.',
                    'details': response.json() if response.text else '',
                }, status=status.HTTP_502_BAD_GATEWAY)

            snap_response = response.json()

            # Create or update payment record (inside transaction)
            payment, created = Payment.objects.get_or_create(
                order=order,
                defaults={
                    'user': request.user,
                    'amount': order.total_price,
                    'payment_type': payment_method,
                    'midtrans_order_id': transaction_details['order_id'],
                }
            )
            if not created:
                payment.midtrans_order_id = transaction_details['order_id']
                payment.amount = order.total_price
                payment.save()

            # Store Midtrans transaction
            MidtransTransaction.objects.update_or_create(
                payment=payment,
                defaults={
                    'order_id': transaction_details['order_id'],
                    'transaction_id': snap_response.get('transaction_id', ''),
                    'transaction_status': 'pending',
                    'payment_type': payment_method,
                    'raw_response': snap_response,
                }
            )

            return Response({
                'token': snap_response.get('token', ''),
                'redirect_url': snap_response.get('redirect_url', ''),
                'transaction_id': transaction_details['order_id'],
                'payment': PaymentSerializer(payment).data,
            })

        except requests.RequestException as e:
            return Response({
                'error': 'Gagal terhubung ke server pembayaran.',
                'details': str(e),
            }, status=status.HTTP_502_BAD_GATEWAY)

    def _encode_auth(self, key):
        import base64
        return base64.b64encode(f'{key}:'.encode()).decode()


class MidtransNotificationView(views.APIView):
    """Handle Midtrans payment notification callback."""
    permission_classes = (permissions.AllowAny,)

    @transaction.atomic
    def post(self, request):
        serializer = MidtransNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        order_id = data['order_id']
        transaction_status = data['transaction_status']
        transaction_id = data.get('transaction_id', '')
        payment_type = data.get('payment_type', '')
        gross_amount = data.get('gross_amount', '0')
        fraud_status = data.get('fraud_status', 'accept')

        # Verify signature
        if not self._verify_signature(data):
            return Response({'error': 'Invalid signature.'},
                          status=status.HTTP_400_BAD_REQUEST)

        # Find the Midtrans transaction
        midtrans_tx = MidtransTransaction.objects.filter(
            order_id=order_id
        ).first()

        if not midtrans_tx:
            return Response({'error': 'Transaction not found.'},
                          status=status.HTTP_404_NOT_FOUND)

        payment = midtrans_tx.payment
        order = payment.order

        # Update Midtrans transaction
        midtrans_tx.transaction_id = transaction_id
        midtrans_tx.transaction_status = transaction_status
        midtrans_tx.payment_type = payment_type
        midtrans_tx.transaction_time = data.get('transaction_time')
        midtrans_tx.status_code = data.get('status_code', '')
        midtrans_tx.status_message = data.get('status_message', '')
        midtrans_tx.fraud_status = fraud_status

        if data.get('va_number'):
            midtrans_tx.va_number = data['va_number']
            payment.va_number = data['va_number']
            payment.bank_name = data.get('bank', '')

        if data.get('settlement_time'):
            midtrans_tx.settlement_time = data['settlement_time']

        midtrans_tx.raw_response = data
        midtrans_tx.save()

        # Idempotency guard: skip if already paid/refunded
        if payment.payment_status in ('paid', 'refunded') and transaction_status in ('deny', 'cancel', 'expire'):
            logger.warning('Ignoring %s webhook for payment %s — already in %s',
                          transaction_status, payment.id, payment.payment_status)
            return Response({'status': 'ignored', 'message': 'Already processed'})

        # Handle transaction status
        if transaction_status == 'settlement' or transaction_status == 'capture':
            if fraud_status == 'accept':
                payment.mark_as_paid()

                is_topup = order_id.startswith('TOP-') or (order and order.notes == 'TOPUP')
                if is_topup:
                    user = payment.user
                    if user:
                        if not user.device_info:
                            user.device_info = {}
                        current_balance = float(user.device_info.get('wallet_balance', 2350000.0))
                        amount_to_add = float(gross_amount)
                        user.device_info['wallet_balance'] = current_balance + amount_to_add
                        user.save(update_fields=['device_info'])

                    notify_payment_update(
                        user_id=payment.user_id,
                        order_id=order.id if order else 0,
                        order_number=order.order_number if order else 'TOPUP',
                        payment_status='paid',
                        message=f'Top Up saldo Warungio sebesar Rp {float(gross_amount):,} berhasil! Saldo Anda telah diperbarui.',
                    )
                else:
                    # Create persistent notification record
                    from notifications.models import Notification as Notif
                    Notif.objects.create(
                        user_id=order.user_id,
                        notification_type='payment',
                        priority='high',
                        title='Pembayaran Berhasil',
                        description=f'Pembayaran untuk pesanan {order.order_number} berhasil! Pesanan akan segera diproses.',
                        action_url=f'/buyer/order-detail/?id={order.id}',
                        action_text='Lihat Pesanan',
                    )

                    # Notify buyer via WebSocket
                    notify_payment_update(
                        user_id=order.user_id,
                        order_id=order.id,
                        order_number=order.order_number,
                        payment_status='paid',
                        message=f'Pembayaran untuk pesanan {order.order_number} berhasil! Pesanan akan segera diproses.',
                    )

                # Update Midtrans settlement
                midtrans_tx.settlement_time = timezone.now()
                midtrans_tx.save(update_fields=['settlement_time'])

        elif transaction_status in ['deny', 'cancel', 'expire']:
            payment.payment_status = 'failed' if transaction_status == 'deny' else transaction_status
            payment.save()
            order.order_status = 'cancelled'
            order.save()

            # Notify buyer about failed payment
            notify_payment_update(
                user_id=order.user_id,
                order_id=order.id,
                order_number=order.order_number,
                payment_status='failed',
                message=f'Pembayaran untuk pesanan {order.order_number} gagal. Silakan coba lagi.',
            )

        elif transaction_status == 'refund':
            payment.payment_status = 'refunded'
            payment.save()
            order.order_status = 'refunded'
            order.save()

            notify_payment_update(
                user_id=order.user_id,
                order_id=order.id,
                order_number=order.order_number,
                payment_status='refunded',
                message=f'Pembayaran pesanan {order.order_number} telah direfund.',
            )

        return Response({'status': 'OK'})

    def _verify_signature(self, data):
        """Verify Midtrans notification signature using hmac.compare_digest."""
        order_id = data.get('order_id', '')
        status_code = data.get('status_code', '')
        gross_amount = str(data.get('gross_amount', '0'))
        server_key = settings.MIDTRANS_SERVER_KEY

        payload = f'{order_id}{status_code}{gross_amount}{server_key}'
        expected = hashlib.sha512(payload.encode()).hexdigest()

        # Use hmac.compare_digest for timing-attack-safe comparison
        return hmac.compare_digest(expected, data.get('signature_key', ''))


class PaymentStatusView(views.APIView):
    """Check payment status for an order."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, order_id):
        payment = Payment.objects.filter(
            order_id=order_id,
            order__user=request.user
        ).first()

        if not payment:
            return Response({'status': 'no_payment'})

        return Response({
            'payment_status': payment.payment_status,
            'payment_type': payment.payment_type,
            'transaction_code': payment.transaction_code,
            'amount': float(payment.amount),
            'paid_at': payment.paid_at,
        })


class PaymentConfigView(views.APIView):
    """Return Midtrans payment configuration (client key, snap URL)."""
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        from .services.midtrans import get_snap_js_url
        return Response({
            'client_key': settings.MIDTRANS_CLIENT_KEY,
            'snap_url': settings.MIDTRANS_SNAP_URL,
            'snap_js_url': get_snap_js_url(),
            'is_production': settings.MIDTRANS_IS_PRODUCTION,
            'merchant_id': settings.MIDTRANS_MERCHANT_ID,
        })


class PaymentHistoryView(generics.ListAPIView):
    """User payment history."""
    serializer_class = PaymentHistorySerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Payment.objects.filter(
            user=self.request.user
        ).select_related('order').order_by('-created_at')[:20]


class WalletTopUpView(views.APIView):
    """Initiate a Midtrans Snap transaction for wallet top-up."""
    permission_classes = (permissions.IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        amount = request.data.get('amount')
        if not amount:
            return Response({'error': 'Nominal top-up wajib diisi.'},
                          status=status.HTTP_400_BAD_REQUEST)
        try:
            amount = int(amount)
            if amount < 10000:
                return Response({'error': 'Minimal top-up adalah Rp 10.000.'},
                              status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({'error': 'Nominal top-up harus berupa angka.'},
                          status=status.HTTP_400_BAD_REQUEST)

        # Create a virtual order for this top-up
        order = Order.objects.create(
            user=request.user,
            store=None,
            subtotal=amount,
            total_price=amount,
            payment_method='midtrans',
            payment_status='pending',
            order_status='pending',
            delivery_address='Virtual Wallet Top-up',
            recipient_name=request.user.full_name or request.user.email,
            recipient_phone=str(request.user.phone) if request.user.phone else '',
            notes='TOPUP',
        )

        tx_order_id = f"TOP-{order.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"

        # Call Midtrans Snap API
        payload = {
            'transaction_details': {
                'order_id': tx_order_id,
                'gross_amount': amount,
            },
            'customer_details': {
                'first_name': request.user.full_name or request.user.email,
                'email': request.user.email,
                'phone': str(request.user.phone) if request.user.phone else '',
            },
            'item_details': [{
                'id': 'TOPUP',
                'price': amount,
                'quantity': 1,
                'name': f'Top Up Saldo Warungio Rp {amount:,}',
            }],
            'credit_card': {'secure': True},
        }

        try:
            import base64
            auth_str = base64.b64encode(f'{settings.MIDTRANS_SERVER_KEY}:'.encode()).decode()
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Basic {auth_str}',
            }
            
            response = requests.post(
                settings.MIDTRANS_SNAP_URL,
                json=payload,
                headers=headers,
                timeout=30,
            )
            
            if response.status_code not in [200, 201]:
                return Response({
                    'error': 'Gagal membuat transaksi pembayaran Midtrans.',
                    'details': response.json() if response.text else '',
                }, status=status.HTTP_502_BAD_GATEWAY)

            snap_response = response.json()

            # Create payment record
            payment = Payment.objects.create(
                order=order,
                user=request.user,
                amount=amount,
                payment_type='midtrans',
                midtrans_order_id=tx_order_id,
            )

            # Store Midtrans transaction
            MidtransTransaction.objects.create(
                payment=payment,
                order_id=tx_order_id,
                transaction_id=snap_response.get('transaction_id', ''),
                transaction_status='pending',
                payment_type='midtrans',
                raw_response=snap_response,
            )

            return Response({
                'token': snap_response.get('token', ''),
                'redirect_url': snap_response.get('redirect_url', ''),
                'transaction_id': tx_order_id,
            })

        except requests.RequestException as e:
            return Response({
                'error': 'Gagal terhubung ke server pembayaran.',
                'details': str(e),
            }, status=status.HTTP_502_BAD_GATEWAY)


# =============================================================================
# FINANCE & REPORTS WORKFLOW ENDPOINTS (SELLER WORKSPACE)
# =============================================================================

class BankAccountListView(generics.ListCreateAPIView):
    """List and create bank accounts for the seller's store."""
    serializer_class = BankAccountSerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_queryset(self):
        return BankAccount.objects.filter(store=self.request.user.store)

    def perform_create(self, serializer):
        # Auto-associate with the user's store
        store = self.request.user.store
        # If this is the first bank account, set it as primary automatically
        is_first = not BankAccount.objects.filter(store=store).exists()
        serializer.save(store=store, is_primary=is_first)


class BankAccountDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete bank account."""
    serializer_class = BankAccountSerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_queryset(self):
        return BankAccount.objects.filter(store=self.request.user.store)


class BankAccountSetPrimaryView(views.APIView):
    """Set a specific bank account as primary/default."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request, pk):
        store = request.user.store
        account = generics.get_object_or_404(BankAccount, pk=pk, store=store)
        account.is_primary = True
        account.save()
        return Response({'message': 'Rekening bank utama berhasil diperbarui.', 'account': BankAccountSerializer(account).data})


class FinanceSummaryView(views.APIView):
    """Get dynamic finance summary calculations based on live order database."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        store = request.user.store

        # 1. Total Pemasukan / Revenue (Completed orders)
        completed_orders = Order.objects.filter(
            store=store,
            order_status='completed'
        )
        total_income = completed_orders.aggregate(total=Sum('total_price'))['total'] or 0

        # 2. Total Penarikan / Withdrawals (Successful or pending withdrawals)
        withdrawals_qs = Payment.objects.filter(
            user=request.user,
            payment_type='withdrawal',
            payment_status__in=['paid', 'pending']
        )
        total_withdrawals = withdrawals_qs.filter(payment_status='paid').aggregate(total=Sum('amount'))['total'] or 0
        total_pending_withdrawals = withdrawals_qs.filter(payment_status='pending').aggregate(total=Sum('amount'))['total'] or 0

        # 3. Saldo Tertahan (Paid, Processed, Shipped orders)
        held_orders = Order.objects.filter(
            store=store,
            order_status__in=['paid', 'processed', 'shipped']
        )
        held_balance = held_orders.aggregate(total=Sum('total_price'))['total'] or 0

        # 4. Available Balance (Saldo Tersedia = Total Income - All Withdrawals)
        # Note: We subtract both pending and paid withdrawals to avoid double-withdrawal race conditions
        available_balance = max(0, total_income - (total_withdrawals + total_pending_withdrawals))

        # 5. Total Transactions count in past 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        total_transactions = Order.objects.filter(
            store=store,
            created_at__gte=thirty_days_ago
        ).count() + withdrawals_qs.filter(created_at__gte=thirty_days_ago).count()

        # 6. Graph trend data (Pemasukan vs Penarikan) in past 30 days
        labels = []
        income_trend = []
        withdrawal_trend = []
        
        today = timezone.now().date()
        for i in range(29, -1, -1):
            d = today - timedelta(days=i)
            labels.append(d.strftime('%d %b'))

            # Daily Income
            daily_inc = Order.objects.filter(
                store=store,
                order_status='completed',
                completed_at__date=d
            ).aggregate(total=Sum('total_price'))['total'] or 0
            income_trend.append(float(daily_inc))

            # Daily Withdrawals
            daily_wdr = Payment.objects.filter(
                user=request.user,
                payment_type='withdrawal',
                payment_status='paid',
                created_at__date=d
            ).aggregate(total=Sum('amount'))['total'] or 0
            withdrawal_trend.append(float(daily_wdr))

        return Response({
            'total_balance': float(available_balance + held_balance),
            'available_balance': float(available_balance),
            'held_balance': float(held_balance),
            'total_income': float(total_income),
            'total_withdrawals': float(total_withdrawals),
            'total_pending_withdrawals': float(total_pending_withdrawals),
            'total_transactions': total_transactions,
            'chart_data': {
                'labels': labels,
                'income': income_trend,
                'withdrawal': withdrawal_trend
            }
        })


class FinanceTransactionListView(views.APIView):
    """List financial history merged from order income, held balances, and withdrawals."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        store = request.user.store
        tx_type = request.query_params.get('type', 'all')  # all, income, withdrawal, held
        search_query = request.query_params.get('search', '')
        
        # We query the actual Order and Payment models dynamically
        transactions = []

        # 1. Add Order Incomes (Completed)
        if tx_type in ['all', 'income']:
            orders = Order.objects.filter(
                store=store,
                order_status='completed'
            ).select_related('user')
            if search_query:
                orders = orders.filter(
                    Q(order_number__icontains=search_query) |
                    Q(recipient_name__icontains=search_query)
                )
            for o in orders:
                transactions.append({
                    'id': f'inc-{o.id}',
                    'created_at': o.completed_at or o.created_at,
                    'type': 'income',
                    'type_label': 'Pemasukan',
                    'description': f'Penjualan Order #{o.order_number}',
                    'category': 'Penjualan Produk',
                    'method': 'Saldo Warungio',
                    'amount': float(o.total_price),
                    'status': 'success',
                    'status_label': 'Berhasil'
                })

        # 2. Add Held Balances (Paid, Processed, Shipped)
        if tx_type in ['all', 'held']:
            held_orders = Order.objects.filter(
                store=store,
                order_status__in=['paid', 'processed', 'shipped']
            ).select_related('user')
            if search_query:
                held_orders = held_orders.filter(
                    Q(order_number__icontains=search_query) |
                    Q(recipient_name__icontains=search_query)
                )
            for o in held_orders:
                transactions.append({
                    'id': f'held-{o.id}',
                    'created_at': o.created_at,
                    'type': 'held',
                    'type_label': 'Saldo Tertahan',
                    'description': f'Penjualan Order #{o.order_number} (Proses)',
                    'category': 'Penjualan Produk',
                    'method': 'Saldo Warungio',
                    'amount': float(o.total_price),
                    'status': 'pending',
                    'status_label': 'Proses'
                })

        # 3. Add Withdrawals (Payment type='withdrawal')
        if tx_type in ['all', 'withdrawal']:
            withdrawals = Payment.objects.filter(
                user=request.user,
                payment_type='withdrawal'
            ).order_by('-created_at')
            if search_query:
                withdrawals = withdrawals.filter(
                    Q(transaction_code__icontains=search_query) |
                    Q(bank_name__icontains=search_query)
                )
            for w in withdrawals:
                status_map = {
                    'pending': ('pending', 'Proses'),
                    'paid': ('success', 'Berhasil'),
                    'failed': ('failed', 'Gagal'),
                    'expired': ('failed', 'Gagal')
                }
                st_code, st_label = status_map.get(w.payment_status, ('pending', 'Proses'))
                transactions.append({
                    'id': f'wdr-{w.id}',
                    'created_at': w.created_at,
                    'type': 'withdrawal',
                    'type_label': 'Penarikan',
                    'description': f'Penarikan ke {w.bank_name or "Bank"} •••• {w.va_number[-4:] if w.va_number else "5678"}',
                    'category': 'Penarikan Dana',
                    'method': 'Transfer Bank',
                    'amount': -float(w.amount),
                    'status': st_code,
                    'status_label': st_label
                })

        # Sort combined list by date descending
        transactions.sort(key=lambda x: x['created_at'], reverse=True)

        # Simple manual pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 5))
        start = (page - 1) * page_size
        end = start + page_size
        paginated_tx = transactions[start:end]

        return Response({
            'count': len(transactions),
            'results': paginated_tx,
            'page': page,
            'page_size': page_size
        })


class WithdrawBalanceView(views.APIView):
    """Initiate withdrawal process for the seller."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    @transaction.atomic
    def post(self, request):
        store = request.user.store
        amount_val = request.data.get('amount')
        
        if not amount_val:
            return Response({'error': 'Nominal penarikan wajib diisi.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            amount = float(amount_val)
            if amount < 10000:
                return Response({'error': 'Minimal penarikan adalah Rp 10.000.'}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({'error': 'Nominal penarikan harus berupa angka.'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Require a primary bank account
        primary_bank = BankAccount.objects.filter(store=store, is_primary=True).first()
        if not primary_bank:
            return Response({'error': 'Anda harus menambahkan rekening bank utama terlebih dahulu.'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Available balance validation
        # Compute available balance: completed_orders total - total withdrawals (paid/pending)
        total_income = Order.objects.filter(
            store=store,
            order_status='completed'
        ).aggregate(total=Sum('total_price'))['total'] or 0

        withdrawals_total = Payment.objects.filter(
            user=request.user,
            payment_type='withdrawal',
            payment_status__in=['paid', 'pending']
        ).aggregate(total=Sum('amount'))['total'] or 0

        available_balance = max(0, total_income - withdrawals_total)

        if amount > available_balance:
            return Response({'error': 'Saldo tidak mencukupi untuk melakukan penarikan.'}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Create a Payment withdrawal record (inside transaction)
        withdrawal_tx = Payment.objects.create(
            order=None,
            user=request.user,
            amount=amount,
            fee=0,
            payment_type='withdrawal',
            payment_status='pending', # 'pending' = proses, can be approved by admin later
            bank_name=primary_bank.bank_name,
            va_number=primary_bank.account_number
        )

        return Response({
            'message': 'Permintaan penarikan dana berhasil diajukan dan sedang diproses.',
            'transaction': PaymentSerializer(withdrawal_tx).data
        })
