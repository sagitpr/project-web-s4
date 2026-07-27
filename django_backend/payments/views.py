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
from django.utils.dateparse import parse_datetime
from channels.layers import get_channel_layer
from rest_framework import status, generics, permissions, views
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from django.core.cache import cache
from accounts.permissions import IsSeller
from accounts.response_utils import success_response, error_response

from .models import (
    Payment, PaymentMethod, MidtransTransaction, BankAccount, 
    BankAccountChangeRequest,
)
from .serializers import (
    PaymentMethodSerializer, PaymentSerializer, MidtransSnapRequest,
    MidtransNotificationSerializer, PaymentHistorySerializer, BankAccountSerializer
)
from .services.midtrans import create_snap_token, get_snap_js_url, process_webhook_notification, is_configured
from .services.wallet import get_wallet, debit_wallet, get_transactions_paginated
from notifications.models import Notification
from orders.models import Order
from drf_spectacular.utils import extend_schema


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


@extend_schema(exclude=True)
class CreateSnapTransactionView(views.APIView):
    """Create Midtrans Snap transaction (async via Celery)."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = MidtransSnapRequest(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data['order_id']
        payment_method = serializer.validated_data['payment_method']
        bank = serializer.validated_data.get('bank')

        order = Order.objects.filter(id=order_id, user=request.user).first()
        if not order:
            return Response({'error': 'Pesanan tidak ditemukan.'},
                          status=status.HTTP_404_NOT_FOUND)

        if order.order_status not in ['pending', 'paid']:
            return Response({'error': 'Pesanan sudah diproses.'},
                          status=status.HTTP_400_BAD_REQUEST)

        # Create Snap token synchronously -- frontend expects immediate token
        result = create_snap_token(order)

        if not result.get('success'):
            return Response({
                'error': result.get('error', 'Gagal membuat transaksi pembayaran.'),
            }, status=status.HTTP_400_BAD_REQUEST)

        # Save payment & Midtrans transaction records
        payment, _ = Payment.objects.get_or_create(
            order=order,
            defaults={
                'user': order.user,
                'amount': order.total_price,
                'payment_type': payment_method,
                'midtrans_order_id': result['transaction_id'],
            }
        )
        if not _:
            payment.midtrans_order_id = result['transaction_id']
            payment.amount = order.total_price
            payment.save()

        MidtransTransaction.objects.update_or_create(
            payment=payment,
            defaults={
                'order_id': result['transaction_id'],
                'transaction_status': 'pending',
                'payment_type': payment_method,
                'raw_response': result.get('raw_response', {}),
            }
        )

        return Response({
            'token': result['token'],
            'redirect_url': result.get('redirect_url', ''),
            'transaction_id': result.get('transaction_id', ''),
            'order_id': order.id,
            'snap_url': settings.MIDTRANS_SNAP_URL,
        })


@extend_schema(exclude=True)
class MidtransNotificationView(views.APIView):
    """
    Handle Midtrans payment notification callback.

    Production-grade webhook handler with:
    - SHA512 signature verification (timing-attack safe via hmac.compare_digest)
    - Replay attack prevention via transaction_time recency check (120s window)
    - Cache-based idempotent dedup (2-minute sliding window)
    - Monotonic state machine: late pending/cancel never overwrites paid/refunded
    - Fraud/challenge handling with challenge_review state
    - Chargeback detection and auto-status update
    - Sensitive data masking in stored logs
    - Orphan webhook logging for reconciliation
    """
    permission_classes = (permissions.AllowAny,)

    @transaction.atomic
    def post(self, request):
        serializer = MidtransNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        order_id = data.get('order_id', '')
        signature_key = data.get('signature_key', '')

        # Signature verification
        if not self._verify_signature(data):
            logger.error('INVALID SIGNATURE order=%s, sig=%s',
                         order_id, signature_key[:20] if signature_key else 'MISSING')
            return Response({'error': 'Invalid signature.'},
                          status=status.HTTP_400_BAD_REQUEST)

        # Delegate all processing to the shared service function.
        # This handles: replay prevention, dedup, orphan webhooks,
        # monotonic state machine, fraud/chargeback/refund, settlement,
        # top-up detection, wallet credit, notifications.
        result = process_webhook_notification(data)

        if result['status'] == 'OK':
            return Response({'status': 'OK'})
        else:
            return Response(result)

    def _verify_signature(self, data):
        """Verify Midtrans notification signature using hmac.compare_digest.
        
        Classic Snap/Core API signature:
            SHA512(order_id + status_code + gross_amount + serverKey)
        
        Uses hmac.compare_digest for timing-attack-safe comparison.
        """
        order_id = data.get('order_id', '')
        status_code = data.get('status_code', '')
        gross_amount = str(data.get('gross_amount', '0'))
        server_key = settings.MIDTRANS_SERVER_KEY

        payload = f'{order_id}{status_code}{gross_amount}{server_key}'
        expected = hashlib.sha512(payload.encode()).hexdigest()

        # Use hmac.compare_digest for timing-attack-safe comparison
        return hmac.compare_digest(expected, data.get('signature_key', ''))


@extend_schema(exclude=True)
class PaymentStatusView(views.APIView):
    """Check payment status for an order."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, order_id):
        payment = Payment.objects.filter(
            order_id=order_id,
            order__user=request.user
        ).select_related('order').first()

        if not payment:
            return Response({'status': 'no_payment'})

        return Response({
            'payment_status': payment.payment_status,
            'payment_type': payment.payment_type,
            'transaction_code': payment.transaction_code,
            'amount': float(payment.amount),
            'paid_at': payment.paid_at,
        })


@extend_schema(exclude=True)
class PaymentConfigView(views.APIView):
    """Return Midtrans payment configuration (client key, snap URL)."""
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        return Response({
            'client_key': settings.MIDTRANS_CLIENT_KEY,
            'snap_url': settings.MIDTRANS_SNAP_URL,
            'snap_js_url': get_snap_js_url(),
            'is_production': settings.MIDTRANS_IS_PRODUCTION,
            'merchant_id': settings.MIDTRANS_MERCHANT_ID,
        })


@extend_schema(exclude=True)
class PublicApiConfigView(views.APIView):
    """
    Public API configuration endpoint.
    Returns safe-to-expose frontend keys (no secrets).
    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        # Only expose client-safe keys (no server-side secrets)
        return Response({
            'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
            'midtrans_client_key': settings.MIDTRANS_CLIENT_KEY,
            'midtrans_snap_url': settings.MIDTRANS_SNAP_URL,
            'midtrans_is_production': settings.MIDTRANS_IS_PRODUCTION,
        })


class PaymentHistoryView(generics.ListAPIView):
    """User payment history."""
    serializer_class = PaymentHistorySerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Payment.objects.none()

        return Payment.objects.filter(
            user=self.request.user
        ).select_related('order').order_by('-created_at')[:20]


@extend_schema(exclude=True)
class WalletTopUpView(views.APIView):
    """Initiate a Midtrans Snap transaction for wallet top-up (async via Celery)."""
    permission_classes = (permissions.IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        # Ensure wallet exists before proceeding
        get_wallet(request.user, lock=False)
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

        # Create Snap token synchronously -- frontend expects immediate token
        result = create_snap_token(order)

        if not result.get('success'):
            return Response({
                'error': result.get('error', 'Gagal memproses top-up.'),
            }, status=status.HTTP_400_BAD_REQUEST)

        # Save payment & Midtrans transaction records
        payment, _ = Payment.objects.get_or_create(
            order=order,
            defaults={
                'user': order.user,
                'amount': order.total_price,
                'payment_type': 'midtrans',
                'midtrans_order_id': result['transaction_id'],
            }
        )
        if not _:
            payment.midtrans_order_id = result['transaction_id']
            payment.amount = order.total_price
            payment.save()

        MidtransTransaction.objects.update_or_create(
            payment=payment,
            defaults={
                'order_id': result['transaction_id'],
                'transaction_status': 'pending',
                'payment_type': 'midtrans',
                'raw_response': result.get('raw_response', {}),
            }
        )

        return Response({
            'token': result['token'],
            'redirect_url': result.get('redirect_url', ''),
            'status': 'success',
            'order_id': order.id,
            'message': 'Top-up siap diproses.',
        })


# =============================================================================
# FINANCE & REPORTS WORKFLOW ENDPOINTS (SELLER WORKSPACE)
# =============================================================================

@extend_schema(exclude=True)
class BankAccountListView(generics.ListCreateAPIView):
    """List and create bank accounts for the seller's store."""
    serializer_class = BankAccountSerializer
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get_queryset(self):
        return BankAccount.objects.filter(store=self.request.user.store).select_related('store')

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
        return BankAccount.objects.filter(store=self.request.user.store).select_related('store')


@extend_schema(exclude=True)
class BankAccountSetPrimaryView(views.APIView):
    """Set a specific bank account as primary/default.
    
    NOTE: Once an account is verified (is_verified=True), it is READ-ONLY.
    Use the 'Request Account Change' flow to change it.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request, pk):
        store = request.user.store
        account = generics.get_object_or_404(BankAccount, pk=pk, store=store)
        
        # Prevent changing an already-verified primary account
        if account.is_primary and account.is_verified:
            return error_response(
                message='Rekening utama yang telah terverifikasi tidak dapat diubah langsung. '
                        'Gunakan fitur "Ajukan Perubahan Rekening" di Pengaturan Akun.',
                status_code=status.HTTP_400_BAD_REQUEST,
                code='primary_account_locked',
            )
        
        account.is_primary = True
        account.save()
        return Response({'message': 'Rekening bank utama berhasil diperbarui.', 'account': BankAccountSerializer(account).data})


@extend_schema(exclude=True)
class BankAccountRequestChangeView(views.APIView):
    """
    Request a change to the primary withdrawal account.
    
    Step 1: Submit new account details → triggers OTP verification.
    Step 2: Verify OTP → triggers password confirmation.
    Step 3: Confirm password → enters waiting period.
    Step 4: Waiting period ends → new account becomes active.
    
    During the process, the OLD account remains active for withdrawals.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request):
        from .serializers import BankAccountChangeRequestSerializer
        
        store = request.user.store
        user = request.user
        
        # Get current primary account
        current_primary = BankAccount.objects.filter(store=store, is_primary=True).first()
        if not current_primary:
            return error_response(
                message='Belum ada rekening utama yang terdaftar.',
                status_code=status.HTTP_400_BAD_REQUEST,
                code='no_primary_account',
            )
        
        new_bank_name = request.data.get('bank_name', '').strip()
        new_account_number = request.data.get('account_number', '').strip()
        new_account_holder = request.data.get('account_holder', '').strip()
        
        if not new_bank_name or not new_account_number or not new_account_holder:
            return error_response(
                message='Nama bank, nomor rekening, dan nama pemilik rekening wajib diisi.',
                status_code=status.HTTP_400_BAD_REQUEST,
                code='missing_fields',
            )
        
        # Check for existing pending request
        existing_pending = BankAccountChangeRequest.objects.filter(
            store=store,
            status__in=['pending_otp', 'pending_password', 'pending_waiting_period']
        ).first()
        if existing_pending:
            return error_response(
                message=f'Masih ada permintaan perubahan rekening yang sedang diproses '
                        f'(Status: {existing_pending.get_status_display()}). '
                        f'Selesaikan atau batalkan permintaan tersebut terlebih dahulu.',
                status_code=status.HTTP_400_BAD_REQUEST,
                code='pending_request_exists',
                existing_request_id=existing_pending.id,
                existing_request_status=existing_pending.status,
            )
        
        # Create change request
        ip_address = request.META.get('REMOTE_ADDR', 'unknown')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:200]
        
        change_req = BankAccountChangeRequest.objects.create(
            store=store,
            user=user,
            old_bank_name=current_primary.bank_name,
            old_account_number=current_primary.account_number,
            old_account_holder=current_primary.account_holder,
            new_bank_name=new_bank_name,
            new_account_number=new_account_number,
            new_account_holder=new_account_holder,
            status='pending_otp',
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        logger.info(
            'BANK ACCOUNT CHANGE REQUEST CREATED — User: %s | Store: %s | '
            'Old: %s ••••%s → New: %s ••••%s | IP: %s | Request ID: %d',
            user.email, store.id,
            current_primary.bank_name, current_primary.account_number[-4:],
            new_bank_name, new_account_number[-4:],
            ip_address, change_req.id,
        )
        
        # Send notification to user about the change request
        try:
            Notification.objects.create(
                user=user,
                notification_type='system',
                priority='high',
                title='Permintaan Perubahan Rekening Diajukan',
                description=f'Perubahan rekening penarikan dari '
                            f'{current_primary.bank_name} ••••{current_primary.account_number[-4:]} '
                            f'ke {new_bank_name} ••••{new_account_number[-4:]} sedang diproses. '
                            f'Selesaikan verifikasi OTP dan password untuk melanjutkan.',
                action_url='/seller/pengaturan/',
                action_text='Lihat Status',
            )
        except Exception as exc:
            logger.warning('Bank change request notification failed: %s', exc)
        
        # Generate and send OTP
        from accounts.models import OTP
        otp = OTP.objects.create(
            user=user,
            email=user.email,
            phone=str(user.phone) if user.phone else None,
            purpose='payment',
            ip_address=ip_address,
            user_agent=user_agent,
        )
        # Store OTP hash on the change request for verification
        change_req.otp_code_hash = otp.otp_code_hash
        change_req.save(update_fields=['otp_code_hash'])
        
        # Send OTP via Celery async or sync fallback
        from accounts.views import _dispatch_otp_async
        channels = _dispatch_otp_async(
            email=user.email,
            phone=str(user.phone) if user.phone else None,
            otp_code=otp.otp_code,
            purpose='payment',
            user_full_name=user.full_name,
        )
        if not channels:
            from accounts.services.email_service import send_otp_email
            send_otp_email(
                email=user.email,
                otp_code=otp.otp_code,
                purpose='payment',
                user_full_name=user.full_name,
            )
        
        return success_response(
            message='Permintaan perubahan rekening telah dibuat. '
                    'Silakan verifikasi OTP yang dikirim ke email Anda.',
            status_code=status.HTTP_201_CREATED,
            change_request_id=change_req.id,
            masked_current_account=current_primary.masked_account,
            masked_new_account=f'{new_bank_name} ••••{new_account_number[-4:]}',
            next_step='verify_otp',
        )


@extend_schema(exclude=True)
class BankAccountVerifyChangeOTPView(views.APIView):
    """
    Step 2: Verify OTP for the bank account change request.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request):
        from accounts.models import OTP
        from django.utils import timezone
        
        store = request.user.store
        user = request.user
        
        change_request_id = request.data.get('change_request_id')
        otp_code = request.data.get('otp_code', '').strip()
        
        if not change_request_id or not otp_code:
            return error_response(
                message='ID permintaan dan kode OTP wajib diisi.',
                status_code=status.HTTP_400_BAD_REQUEST,
                code='missing_fields',
            )
        
        change_req = generics.get_object_or_404(
            BankAccountChangeRequest,
            id=change_request_id, store=store, user=user
        )
        
        if change_req.status != 'pending_otp':
            return error_response(
                message=f'Status permintaan tidak valid (saat ini: {change_req.get_status_display()}).',
                status_code=status.HTTP_400_BAD_REQUEST,
                code='invalid_status',
            )
        
        # Verify OTP hash
        otp_code_hash = OTP.hash_otp(otp_code)
        if change_req.otp_code_hash != otp_code_hash:
            logger.warning(
                'BANK ACCOUNT CHANGE OTP FAILED — User: %s | Request: %d',
                user.email, change_request_id,
            )
            return error_response(
                message='Kode OTP tidak valid.',
                status_code=status.HTTP_400_BAD_REQUEST,
                code='invalid_otp',
            )
        
        # Mark OTP as verified
        change_req.otp_verified = True
        change_req.otp_verified_at = timezone.now()
        change_req.status = 'pending_password'
        change_req.save(update_fields=['otp_verified', 'otp_verified_at', 'status'])
        
        logger.info(
            'BANK ACCOUNT CHANGE OTP VERIFIED — User: %s | Request: %d',
            user.email, change_request_id,
        )
        
        return success_response(
            message='OTP berhasil diverifikasi. Silakan konfirmasi password Anda.',
            status_code=status.HTTP_200_OK,
            change_request_id=change_req.id,
            next_step='confirm_password',
        )


@extend_schema(exclude=True)
class BankAccountConfirmPasswordView(views.APIView):
    """
    Step 3: Confirm password for the bank account change request.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request):
        from django.utils import timezone
        
        store = request.user.store
        user = request.user
        
        change_request_id = request.data.get('change_request_id')
        password = request.data.get('password', '')
        
        if not change_request_id or not password:
            return error_response(
                message='ID permintaan dan password wajib diisi.',
                status_code=status.HTTP_400_BAD_REQUEST,
                code='missing_fields',
            )
        
        change_req = generics.get_object_or_404(
            BankAccountChangeRequest,
            id=change_request_id, store=store, user=user
        )
        
        if change_req.status != 'pending_password':
            return error_response(
                message=f'Status permintaan tidak valid (saat ini: {change_req.get_status_display()}).',
                status_code=status.HTTP_400_BAD_REQUEST,
                code='invalid_status',
            )
        
        if not user.check_password(password):
            logger.warning(
                'BANK ACCOUNT CHANGE PASSWORD FAILED — User: %s | Request: %d',
                user.email, change_request_id,
            )
            return error_response(
                message='Password tidak valid.',
                status_code=status.HTTP_400_BAD_REQUEST,
                code='invalid_password',
            )
        
        # Mark password as verified, enter waiting period
        change_req.password_verified = True
        change_req.password_verified_at = timezone.now()
        change_req.status = 'pending_waiting_period'
        change_req.waiting_started_at = timezone.now()
        change_req.waiting_ends_at = timezone.now() + timezone.timedelta(
            hours=change_req.waiting_period_hours
        )
        change_req.save(update_fields=[
            'password_verified', 'password_verified_at', 'status',
            'waiting_started_at', 'waiting_ends_at',
        ])
        
        logger.info(
            'BANK ACCOUNT CHANGE PASSWORD VERIFIED — User: %s | Request: %d | '
            'Waiting until: %s',
            user.email, change_request_id, change_req.waiting_ends_at,
        )
        
        return success_response(
            message=f'Password berhasil dikonfirmasi. Perubahan rekening akan aktif '
                    f'setelah masa tunggu {change_req.waiting_period_hours} jam '
                    f'(hingga {change_req.waiting_ends_at.strftime("%d %b %H:%M")}). '
                    f'Rekening lama tetap aktif selama proses ini.',
            status_code=status.HTTP_200_OK,
            change_request_id=change_req.id,
            waiting_ends_at=change_req.waiting_ends_at.isoformat(),
            next_step='waiting_period',
        )


@extend_schema(exclude=True)
class BankAccountCancelChangeView(views.APIView):
    """
    Cancel a pending bank account change request.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request):
        store = request.user.store
        user = request.user
        
        change_request_id = request.data.get('change_request_id')
        if not change_request_id:
            return error_response(
                message='ID permintaan wajib diisi.',
                status_code=status.HTTP_400_BAD_REQUEST,
                code='missing_fields',
            )
        
        change_req = generics.get_object_or_404(
            BankAccountChangeRequest,
            id=change_request_id, store=store, user=user
        )
        
        if change_req.status in ['completed', 'approved', 'rejected', 'expired']:
            return error_response(
                message=f'Permintaan dengan status {change_req.get_status_display()} tidak dapat dibatalkan.',
                status_code=status.HTTP_400_BAD_REQUEST,
                code='cannot_cancel',
            )
        
        change_req.status = 'cancelled'
        change_req.save(update_fields=['status'])
        
        logger.info(
            'BANK ACCOUNT CHANGE CANCELLED — User: %s | Request: %d',
            user.email, change_request_id,
        )
        
        return success_response(
            message='Permintaan perubahan rekening berhasil dibatalkan.',
            status_code=status.HTTP_200_OK,
        )


@extend_schema(exclude=True)
class BankAccountChangeRequestListView(views.APIView):
    """
    List all bank account change requests for the seller.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        from .serializers import BankAccountChangeRequestSerializer
        
        store = request.user.store
        requests_qs = BankAccountChangeRequest.objects.filter(
            store=store
        ).order_by('-created_at')[:20]
        
        return Response({
            'count': requests_qs.count(),
            'results': BankAccountChangeRequestSerializer(requests_qs, many=True).data,
        })


@extend_schema(exclude=True)
class BankAccountCheckActivationView(views.APIView):
    """
    Check and activate bank account changes whose waiting period has expired.
    
    The frontend should call this periodically (e.g., on visiting the settings page)
    to check if a pending change request's waiting period has ended.
    If so, the request is activated and the new account becomes primary.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        store = request.user.store
        now = timezone.now()
        activated = []
        
        # Find all change requests whose waiting period has expired
        pending_requests = BankAccountChangeRequest.objects.filter(
            store=store,
            status='pending_waiting_period',
            waiting_ends_at__lte=now,
            otp_verified=True,
            password_verified=True,
        )
        
        for change_req in pending_requests:
            try:
                new_account = change_req.activate()
                activated.append({
                    'id': change_req.id,
                    'new_account_id': new_account.id,
                    'new_account_masked': new_account.masked_account,
                    'completed_at': change_req.completed_at.isoformat() if change_req.completed_at else None,
                })
                
                # Notify user
                try:
                    Notification.objects.create(
                        user=request.user,
                        notification_type='system',
                        priority='high',
                        title='Rekening Utama Berhasil Diperbarui',
                        description=f'Rekening penarikan utama telah berubah menjadi '
                                    f'{new_account.bank_name} ••••{new_account.account_number[-4:]} '
                                    f'a.n. {new_account.account_holder}.',
                        action_url='/seller/pengaturan/',
                        action_text='Lihat Rekening',
                    )
                except Exception as exc:
                    logger.warning('Activation notification failed: %s', exc)
                    
                logger.info(
                    'BANK ACCOUNT CHANGE ACTIVATED — Request: %d | '
                    'Old: %s ••••%s → New: %s ••••%s',
                    change_req.id,
                    change_req.old_bank_name, change_req.old_account_number[-4:],
                    new_account.bank_name, new_account.account_number[-4:],
                )
            except Exception as exc:
                logger.error('Bank account activation failed for request %d: %s', change_req.id, exc)
        
        # Also return pending requests that are still in waiting period
        still_pending = BankAccountChangeRequest.objects.filter(
            store=store,
            status='pending_waiting_period',
            waiting_ends_at__gt=now,
        ).first()
        
        return success_response(
            message=f'{len(activated)} perubahan rekening telah diaktifkan.' if activated else 'Tidak ada perubahan rekening yang perlu diaktifkan.',
            activated_count=len(activated),
            activated=activated,
            has_pending=still_pending is not None,
            pending_ends_at=still_pending.waiting_ends_at.isoformat() if still_pending else None,
        )


@extend_schema(exclude=True)
class FinanceSummaryView(views.APIView):
    """Get dynamic finance summary calculations based on live order database.
    
    Cached for 2 minutes to reduce DB load.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        store = request.user.store
        cache_key = f'finance_summary_{store.id}'
        
        # Check cache first
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        
        # 1. Total Pemasukan KOTOR / Revenue (Completed orders, includes admin_fee)
        completed_orders = Order.objects.filter(
            store=store,
            order_status='completed'
        )
        total_income_gross = completed_orders.aggregate(total=Sum('total_price'))['total'] or 0

        # 1b. Total Admin Fee Seller yang dipotong dari seller (Rp 1.000)
        total_admin_fees = completed_orders.aggregate(total=Sum('admin_fee'))['total'] or 0

        # 1c. Pemasukan BERSIH seller (setelah dipotong admin_fee)
        total_income_net = total_income_gross - total_admin_fees

        # 2. Total Penarikan / Withdrawals (Successful or pending withdrawals)
        withdrawals_qs = Payment.objects.filter(
            user=request.user,
            payment_type='withdrawal',
            payment_status__in=['paid', 'pending']
        )
        total_withdrawals = withdrawals_qs.filter(payment_status='paid').aggregate(total=Sum('amount'))['total'] or 0
        total_pending_withdrawals = withdrawals_qs.filter(payment_status='pending').aggregate(total=Sum('amount'))['total'] or 0

        # 3. Saldo Tertahan (Paid, Processed, Shipped orders) — total termasuk admin_fee
        held_orders = Order.objects.filter(
            store=store,
            order_status__in=['paid', 'processed', 'shipped']
        )
        held_balance = held_orders.aggregate(total=Sum('total_price'))['total'] or 0

        # 4. Available Balance (Saldo Tersedia = Net Income - All Withdrawals)
        available_balance = max(0, total_income_net - (total_withdrawals + total_pending_withdrawals))

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

            # Daily Income NET (setelah admin_fee)
            daily_orders = Order.objects.filter(
                store=store,
                order_status='completed',
                completed_at__date=d
            )
            daily_gross = daily_orders.aggregate(total=Sum('total_price'))['total'] or 0
            daily_admin = daily_orders.aggregate(total=Sum('admin_fee'))['total'] or 0
            daily_net = daily_gross - daily_admin
            income_trend.append(float(daily_net))

            # Daily Withdrawals
            daily_wdr = Payment.objects.filter(
                user=request.user,
                payment_type='withdrawal',
                payment_status='paid',
                created_at__date=d
            ).aggregate(total=Sum('amount'))['total'] or 0
            withdrawal_trend.append(float(daily_wdr))

        data = {
            'total_balance': float(available_balance + held_balance),
            'available_balance': float(available_balance),
            'held_balance': float(held_balance),
            'total_income_gross': float(total_income_gross),
            'total_income_net': float(total_income_net),
            'total_admin_fees': float(total_admin_fees),
            'total_withdrawals': float(total_withdrawals),
            'total_pending_withdrawals': float(total_pending_withdrawals),
            'total_transactions': total_transactions,
            'chart_data': {
                'labels': labels,
                'income': income_trend,
                'withdrawal': withdrawal_trend
            }
        }
        # Cache briefly for spike protection — finance cards always show near-live data
        cache.set(cache_key, data, 15)
        return Response(data)


@extend_schema(exclude=True)
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


@extend_schema(exclude=True)
class WithdrawBalanceView(views.APIView):
    """Initiate withdrawal process for the seller.
    
    Uses data from FinanceSummaryView logic for consistent balance calculation.
    Idempotent: prevents duplicate withdrawals within a 30-second window.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    @transaction.atomic
    def post(self, request):
        store = request.user.store
        user = request.user
        amount_val = request.data.get('amount')

        if not amount_val:
            return Response({'error': 'Nominal penarikan wajib diisi.'},
                          status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = float(amount_val)
            if amount < 10000:
                return Response({'error': 'Minimal penarikan adalah Rp 10.000.'},
                              status=status.HTTP_400_BAD_REQUEST)
            if amount > 1000000000:
                return Response({'error': 'Maksimal penarikan adalah Rp 1.000.000.000.'},
                              status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({'error': 'Nominal penarikan harus berupa angka.'},
                          status=status.HTTP_400_BAD_REQUEST)

        # 1. Idempotency check — prevent duplicate within 30 seconds
        recent_withdrawal = Payment.objects.filter(
            user=user,
            payment_type='withdrawal',
            payment_status='pending',
            amount=amount,
            created_at__gte=timezone.now() - timedelta(seconds=30),
        ).first()
        if recent_withdrawal:
            return Response({
                'message': 'Permintaan penarikan sudah diajukan.',
                'transaction': PaymentSerializer(recent_withdrawal).data,
            })

        # 2. Require a primary bank account
        primary_bank = BankAccount.objects.filter(store=store, is_primary=True).first()
        if not primary_bank:
            return Response({
                'error': 'Anda harus menambahkan rekening bank utama terlebih dahulu.',
                'action_required': 'add_bank_account',
            }, status=status.HTTP_400_BAD_REQUEST)

        # 3. Available balance validation (consistent with FinanceSummaryView)
        completed_orders = Order.objects.filter(store=store, order_status='completed')
        total_income_gross = completed_orders.aggregate(total=Sum('total_price'))['total'] or 0
        total_admin_fees = completed_orders.aggregate(total=Sum('admin_fee'))['total'] or 0
        total_income_net = total_income_gross - total_admin_fees

        total_withdrawals = Payment.objects.filter(
            user=user,
            payment_type='withdrawal',
            payment_status__in=['paid', 'pending']
        ).aggregate(total=Sum('amount'))['total'] or 0

        available_balance = max(0, total_income_net - total_withdrawals)

        if amount > available_balance:
            return Response({
                'error': 'Saldo tidak mencukupi untuk melakukan penarikan.',
                'available_balance': float(available_balance),
                'requested_amount': amount,
            }, status=status.HTTP_400_BAD_REQUEST)

        # 4. Create a Payment withdrawal record
        withdrawal_tx = Payment.objects.create(
            order=None,
            user=user,
            amount=amount,
            fee=0,
            payment_type='withdrawal',
            payment_status='pending',
            bank_name=primary_bank.bank_name,
            va_number=primary_bank.account_number,
        )

        # 5. Debit seller wallet atomically
        try:
            result = debit_wallet(
                user=user,
                amount=amount,
                tx_type='withdrawal',
                description=f'Penarikan dana ke {primary_bank.bank_name} - {primary_bank.account_number}',
                reference_type='withdrawal',
                reference_id=str(withdrawal_tx.id),
            )
            logger.info('Seller wallet debited for withdrawal %s: Rp %s \u2192 Rp %s',
                       withdrawal_tx.id, result['balance_before'], result['balance_after'])
        except Exception as e:
            logger.error('Failed to debit seller wallet for withdrawal %s: %s', withdrawal_tx.id, e)

        # 6. Notify seller via notification
        try:
            Notification.objects.create(
                user=user,
                notification_type='withdrawal',
                priority='high',
                title='Penarikan Dana Berhasil Diajukan',
                description=f'Penarikan dana sebesar Rp {amount:,.0f} ke {primary_bank.bank_name} sedang diproses.',
                action_url='/seller/dashboard/finance/',
                action_text='Lihat Status',
            )
        except Exception as exc:
            logger.warning('Withdrawal notification creation failed: %s', str(exc))

        return Response({
            'message': 'Permintaan penarikan dana berhasil diajukan dan sedang diproses.',
            'transaction': PaymentSerializer(withdrawal_tx).data,
        })



# =============================================================================
# MIDTRANS MERCHANT STATUS (Dynamic seller activation)
# =============================================================================

@extend_schema(exclude=True)
class MidtransMerchantStatusView(views.APIView):
    """
    Return the merchant's Midtrans onboarding status dynamically.

    This replaces the old hardcoded "Registration under review" page.
    Status is determined from environment variables:
      - not_configured: No MIDTRANS_SERVER_KEY set
      - pending_activation: MIDTRANS_IS_PRODUCTION=False (sandbox mode)
      - active: MIDTRANS_IS_PRODUCTION=True and keys configured
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        configured = is_configured()
        is_production = settings.MIDTRANS_IS_PRODUCTION
        merchant_id = getattr(settings, 'MIDTRANS_MERCHANT_ID', '')

        if not configured:
            status = 'not_configured'
            label = 'Belum Dikonfigurasi'
            message = 'Pembayaran online belum dikonfigurasi. Silakan hubungi admin.'
        elif not is_production:
            status = 'pending_activation'
            label = 'Menunggu Aktivasi'
            message = 'Akun merchant sedang dalam proses aktivasi. Estimasi 1-2 hari kerja.'
        else:
            status = 'active'
            label = 'Aktif'
            message = 'Pembayaran online aktif dan siap digunakan.'

        if merchant_id and is_production and configured:
            status = 'active'
            label = 'Aktif'
            message = 'Pembayaran online aktif dan siap digunakan.'

        return Response({
            'status': status,
            'label': label,
            'message': message,
            'is_production': is_production,
            'merchant_id': merchant_id if merchant_id else None,
            'onboarding_progress': {
                'configured': configured,
                'production': is_production,
                'merchant_registered': bool(merchant_id),
            }
        })


# =============================================================================
# WALLET ENDPOINTS (Database-driven, not device_info)
# =============================================================================

@extend_schema(exclude=True)
class WalletBalanceView(views.APIView):
    """
    Get real-time wallet balance for the authenticated user.
    
    GET /api/payments/wallet/balance/
    
    Returns balance directly from the Wallet table (database-driven).
    Saldo TIDAK pernah disimpan di frontend atau localStorage.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        wallet = get_wallet(request.user, lock=False)
        return Response({
            'balance': float(wallet.balance),
            'balance_formatted': f'Rp {wallet.balance:,.0f}',
            'last_updated': wallet.updated_at.isoformat() if wallet.updated_at else None,
        })


@extend_schema(exclude=True)
class WalletTransactionListView(views.APIView):
    """
    Get paginated wallet transaction history.
    
    GET /api/payments/wallet/transactions/?page=1&page_size=10&type=all
    
    Returns history langsung dari WalletTransaction table.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        tx_type = request.query_params.get('type', 'all')
        
        result = get_transactions_paginated(
            user=request.user,
            page=page,
            page_size=page_size,
            tx_type=tx_type,
        )
        
        return Response(result)
