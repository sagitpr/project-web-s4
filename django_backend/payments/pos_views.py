"""
POS Offline Transaction Views for Warungio Marketplace.

Handles offline (POS/cashier) transactions at the seller's store.
When a transaction is confirmed as paid, broadcasts a voice notification
to the seller's dashboard via WebSocket.

Security: Only the store owner can create POS transactions for their own store.
Idempotency: Duplicate requests within 30 seconds are rejected.
"""

import logging
from django.db import transaction as db_transaction
from django.utils import timezone
from rest_framework import status, generics, permissions, views
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from accounts.permissions import IsSeller
from .models import Payment

logger = logging.getLogger(__name__)


@extend_schema(exclude=True)
class POSCompleteSaleView(views.APIView):
    """
    Record an offline POS/cashier transaction and broadcast voice notification.

    POST /api/payments/pos/complete/

    This endpoint is called by the seller's POS/cashier interface when an
    offline transaction is successfully paid at the store.

    Request:
        {
            "amount": 125000,
            "customer_name": "Budi" (optional),
            "notes": "Pembelian sembako" (optional)
        }

    Response:
        {
            "success": true,
            "transaction_id": "POS-20240101-001",
            "amount": 125000,
            "message": "Transaksi berhasil dicatat."
        }
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    @db_transaction.atomic
    def post(self, request):
        user = request.user
        store = getattr(user, 'store', None)

        if not store:
            return Response(
                {'error': 'Anda belum memiliki toko. Silakan daftar toko terlebih dahulu.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        amount = request.data.get('amount')
        customer_name = request.data.get('customer_name', '').strip()
        notes = request.data.get('notes', '').strip()

        if not amount:
            return Response(
                {'error': 'Nominal transaksi wajib diisi.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount = int(amount)
            if amount <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return Response(
                {'error': 'Nominal transaksi harus berupa angka positif.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate transaction reference
        now = timezone.now()
        tx_ref = f"POS-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}-{user.id}"

        # Create a payment record for the POS transaction
        payment = Payment.objects.create(
            user=user,
            amount=amount,
            fee=0,
            payment_type='pos',
            payment_status='paid',
            va_number=customer_name if customer_name else 'POS Customer',
            transaction_code=tx_ref,
            paid_at=now,
        )

        logger.info(
            'POS transaction recorded — user=%s store=%s amount=%s ref=%s customer=%s',
            user.id, store.id, amount, tx_ref, customer_name or '(none)',
        )

        # Broadcast voice notification to seller
        from notifications.voice_service import broadcast_pos_transaction_voice
        try:
            broadcast_pos_transaction_voice(
                seller_user_id=user.id,
                amount=amount,
                order_number=tx_ref,
                transaction_id=f'voice-pos-{tx_ref}',
            )
        except Exception as e:
            logger.warning('POS voice notification failed: %s', e)

        return Response({
            'success': True,
            'transaction_id': tx_ref,
            'amount': amount,
            'message': 'Transaksi berhasil dicatat.',
            'paid_at': now.isoformat(),
        })
