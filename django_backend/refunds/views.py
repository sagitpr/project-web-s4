"""
Refunds views for Warungio Marketplace.
Buyer, Seller, and Admin refund management.
"""

import logging
from django.db import transaction as db_transaction
from django.utils import timezone
from rest_framework import status, generics, permissions, views
from rest_framework.response import Response
from django.db.models import Q

from .models import Refund, RefundTimelineEvent

logger = logging.getLogger(__name__)
from .serializers import (
    RefundCreateSerializer, RefundListSerializer, RefundDetailSerializer,
    SellerRefundActionSerializer, AdminRefundActionSerializer,
    RefundTimelineEventSerializer,
)
from accounts.permissions import IsSeller
from orders.models import Order
from drf_spectacular.utils import extend_schema


def _add_timeline(refund, event_type, description, user=None, role=None, metadata=None):
    """Helper to create a timeline event."""
    RefundTimelineEvent.objects.create(
        refund=refund,
        event_type=event_type,
        description=description,
        created_by=user,
        created_by_role=role or (user.role if user else 'system'),
        metadata=metadata or {},
    )


# ─── Buyer Views ───────────────────────────────────────────────────────────


class CreateRefundView(generics.CreateAPIView):
    """Buyer submits a refund request."""
    serializer_class = RefundCreateSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        refund = serializer.save(
            user=self.request.user,
            store=serializer.validated_data['order'].store,
            refund_status='pending',
        )
        _add_timeline(
            refund, 'created',
            f"Refund diajukan dengan alasan: {refund.get_reason_display()}",
            self.request.user, 'buyer',
        )


class MyRefundListView(generics.ListAPIView):
    """Buyer lists their refund requests."""
    serializer_class = RefundListSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Refund.objects.none()

        qs = Refund.objects.filter(user=self.request.user).select_related('store', 'order')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(refund_status=status_filter)
        return qs


class RefundDetailView(generics.RetrieveAPIView):
    """Get refund detail with timeline and order info."""
    queryset = Refund.objects.all()
    serializer_class = RefundDetailSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        # Buyer can see own refunds, seller can see store refunds, admin can see all
        if user.is_staff:
            return Refund.objects.all()
        if hasattr(user, 'store'):
            return Refund.objects.filter(
                Q(user=user) | Q(store=user.store)
            )
        return Refund.objects.filter(user=user)


@extend_schema(exclude=True)
class BuyerCancelRefundView(views.APIView):
    """Buyer cancels a pending refund request."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, pk):
        try:
            refund = Refund.objects.get(pk=pk, user=request.user,
                                         refund_status__in=('pending', 'waiting_buyer'))
        except Refund.DoesNotExist:
            return Response({'error': 'Refund tidak ditemukan atau tidak dapat dibatalkan.'},
                          status=status.HTTP_400_BAD_REQUEST)

        refund.refund_status = 'cancelled'
        refund.save(update_fields=['refund_status'])

        _add_timeline(refund, 'cancelled', 'Refund dibatalkan oleh pembeli.', request.user, 'buyer')

        return Response({'message': 'Refund berhasil dibatalkan.'})


# ─── Seller Views ──────────────────────────────────────────────────────────


@extend_schema(exclude=True)
class StoreRefundListView(generics.ListAPIView):
    """Seller lists refund requests for their store."""
    serializer_class = RefundListSerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_queryset(self):
        qs = Refund.objects.filter(store__user=self.request.user).select_related('store', 'order', 'user')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(refund_status=status_filter)
        return qs


@extend_schema(exclude=True)
class SellerRefundActionView(views.APIView):
    """Seller takes action on a refund request."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request, pk):
        try:
            refund = Refund.objects.get(pk=pk, store__user=request.user)
        except Refund.DoesNotExist:
            return Response({'error': 'Refund tidak ditemukan.'},
                          status=status.HTTP_404_NOT_FOUND)

        if refund.refund_status not in ('pending', 'under_review', 'waiting_seller'):
            return Response({'error': 'Tidak dapat merespon refund dengan status saat ini.'},
                          status=status.HTTP_400_BAD_REQUEST)

        serializer = SellerRefundActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data['action']

        if action == 'approve':
            amount = serializer.validated_data.get('amount_approved') or refund.amount_requested
            refund.amount_approved = amount
            refund.resolution = serializer.validated_data.get('resolution', 'full_refund')
            refund.refund_status = 'approved'
            refund.seller_notes = serializer.validated_data.get('seller_notes', '')
            _add_timeline(
                refund, 'approved',
                f"Refund disetujui oleh penjual. Jumlah: Rp {amount:,.0f}.",
                request.user, 'seller',
            )

        elif action == 'reject':
            refund.refund_status = 'rejected'
            refund.seller_notes = serializer.validated_data.get('seller_notes', '')
            _add_timeline(
                refund, 'rejected',
                f"Refund ditolak oleh penjual. Alasan: {serializer.validated_data.get('seller_notes', 'Tidak ada alasan')}",
                request.user, 'seller',
            )

        elif action == 'negotiate':
            amount = serializer.validated_data['amount_approved']
            refund.amount_approved = amount
            refund.refund_status = 'waiting_buyer'
            refund.seller_notes = serializer.validated_data.get('seller_notes', '')
            _add_timeline(
                refund, 'negotiated',
                f"Penjual menawarkan refund sebesar Rp {amount:,.0f}. Menunggu konfirmasi pembeli.",
                request.user, 'seller',
                {'amount_offered': float(amount)},
            )

        elif action == 'request_info':
            refund.refund_status = 'waiting_buyer'
            refund.seller_notes = serializer.validated_data.get('seller_notes', '')
            _add_timeline(
                refund, 'note_added',
                f"Penjual meminta informasi tambahan: {serializer.validated_data.get('seller_notes', '')}",
                request.user, 'seller',
            )

        refund.save()
        return Response(RefundDetailSerializer(refund).data)


# ─── Admin Views ────────────────────────────────────────────────────────────


class RefundAdminPermission(permissions.BasePermission):
    """Custom permission for admin-only refund access."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)


class AdminRefundListView(generics.ListAPIView):
    """Admin lists all refund requests."""
    serializer_class = RefundListSerializer
    permission_classes = (permissions.IsAuthenticated, RefundAdminPermission)

    def get_queryset(self):
        qs = Refund.objects.all().select_related('store', 'order', 'user')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(refund_status=status_filter)
        escalated = self.request.query_params.get('escalated')
        if escalated == 'true':
            qs = qs.filter(is_escalated=True)
        return qs


@extend_schema(exclude=True)
class AdminRefundActionView(views.APIView):
    """Admin intervenes or resolves a refund dispute."""
    permission_classes = (permissions.IsAuthenticated, RefundAdminPermission)

    def post(self, request, pk):
        try:
            refund = Refund.objects.get(pk=pk)
        except Refund.DoesNotExist:
            return Response({'error': 'Refund tidak ditemukan.'},
                          status=status.HTTP_404_NOT_FOUND)

        serializer = AdminRefundActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data['action']

        if action == 'resolve':
            amount = serializer.validated_data.get('amount_approved') or refund.amount_requested
            refund.amount_approved = amount
            refund.resolution = serializer.validated_data.get('resolution', 'full_refund')
            refund.refund_status = 'refunded'
            refund.admin_notes = serializer.validated_data.get('admin_notes', '')
            refund.resolved_at = timezone.now()

            # ── Wallet updates + timeline (atomic: all or roll back) ──
            try:
                with db_transaction.atomic():
                    from payments.services.wallet import credit_wallet, debit_wallet
                    _add_timeline(
                        refund, 'resolved',
                        f"Admin menyelesaikan refund. Resolusi: {refund.get_resolution_display()}. Jumlah: Rp {amount:,.0f}.",
                        request.user, 'admin',
                    )
                    if refund.user:
                        credit_result = credit_wallet(
                            user=refund.user,
                            amount=float(amount),
                            tx_type='refund',
                            description=f'Refund untuk pesanan #{refund.order.order_number}',
                            reference_type='refund',
                            reference_id=str(refund.id),
                        )
                        logger.info('Buyer wallet credited for refund %s: Rp %s \u2192 Rp %s',
                                   refund.id, credit_result['balance_before'], credit_result['balance_after'])
                    if refund.store and refund.store.user_id:
                        debit_result = debit_wallet(
                            user=refund.store.user,
                            amount=float(amount),
                            tx_type='refund',
                            description=f'Refund pesanan #{refund.order.order_number}',
                            reference_type='refund',
                            reference_id=str(refund.id),
                        )
                        logger.info('Seller wallet debited for refund %s: Rp %s \u2192 Rp %s',
                                   refund.id, debit_result['balance_before'], debit_result['balance_after'])
                    # Persist refund status changes inside the same atomic block
                    refund.save(update_fields=['refund_status', 'amount_approved', 'resolution', 'admin_notes', 'resolved_at'])
            except Exception as e:
                logger.error('Failed to update wallets for refund %s (rolled back): %s', refund.id, e)
                raise

        elif action == 'escalate':
            refund.is_escalated = True
            refund.admin_notes = serializer.validated_data.get('admin_notes', '')
            refund.refund_status = 'under_review'
            _add_timeline(
                refund, 'admin_intervened',
                f"Admin mengambil alih review refund: {serializer.validated_data.get('admin_notes', '')}",
                request.user, 'admin',
            )

        elif action == 'close':
            refund.refund_status = 'cancelled'
            refund.admin_notes = serializer.validated_data.get('admin_notes', '')
            refund.resolved_at = timezone.now()
            _add_timeline(
                refund, 'resolved',
                f"Admin menutup refund: {serializer.validated_data.get('admin_notes', 'Tidak ada alasan')}",
                request.user, 'admin',
            )

        refund.save()
        return Response(RefundDetailSerializer(refund).data)


# ─── Refund Stats (for dashboard widgets) ─────────────────────────────


@extend_schema(exclude=True)
class RefundStatsView(views.APIView):
    """Get refund statistics for dashboard widgets."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        user = request.user
        if user.is_staff:
            queryset = Refund.objects.all()
        elif hasattr(user, 'store'):
            queryset = Refund.objects.filter(store=user.store)
        else:
            queryset = Refund.objects.filter(user=user)

        stats = {
            'total': queryset.count(),
            'pending': queryset.filter(refund_status='pending').count(),
            'under_review': queryset.filter(refund_status='under_review').count(),
            'approved': queryset.filter(refund_status='approved').count(),
            'rejected': queryset.filter(refund_status='rejected').count(),
            'refunded': queryset.filter(refund_status='refunded').count(),
            'cancelled': queryset.filter(refund_status='cancelled').count(),
            'escalated': queryset.filter(is_escalated=True).count(),
            'total_amount_requested': float(
                sum(q.amount_requested for q in queryset.filter(
                    refund_status__in=('pending', 'under_review', 'approved', 'refunded')
                ))
            ),
            'total_amount_refunded': float(
                sum(q.amount_approved or 0 for q in queryset.filter(
                    refund_status='refunded'
                ))
            ),
        }
        return Response(stats)
