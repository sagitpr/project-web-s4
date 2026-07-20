"""
API views for AI Smart Inventory Scanning.
Real-time camera scanning, bulk barcode scan, item review, batch creation.
"""

from datetime import date

from django.utils import timezone
from rest_framework import permissions, status, generics
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsSeller
from inventory.models import (
    SmartScanSession, DetectedItem, MasterProduct
)
from .serializers import (
    SmartScanSessionSerializer,
    StartScanSerializer,
    FrameDetectionSerializer,
    BulkBarcodeSerializer,
    DetectedItemSerializer,
    ConfirmItemsSerializer,
    UpdateDetectedItemSerializer,
    RegisterNewProductSerializer,
    AggregatedScanResultSerializer,
    ScanSummarySerializer,
)
from .services.detection_service import (
    process_frame_detections,
    aggregate_session_detections,
    deduplicate_session,
)
from .services.barcode_service import (
    process_barcode_detections,
    process_bulk_barcodes,
)
from .services.ocr_service import (
    process_ocr_text,
    process_detected_item_ocr,
)
from drf_spectacular.utils import extend_schema
from .services.aggregator_service import (
    aggregate_scan_results,
    confirm_and_save_items,
    register_new_product,
    update_detected_item,
    get_scan_summary,
    match_unmatched_items,
)


# =============================================================================
# SCAN SESSION
# =============================================================================


@extend_schema(exclude=True)
class StartScanSessionView(APIView):
    """Start a new AI Smart Scan session.

    POST /api/inventory/ai-scan/start/
    {
        "scan_mode": "single" | "multi" | "bulk"
    }
    Returns the created session.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request):
        serializer = StartScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Close any open sessions for this store
        SmartScanSession.objects.filter(
            store=request.user.store,
            status='scanning',
        ).update(status='cancelled')

        session = SmartScanSession.objects.create(
            store=request.user.store,
            user=request.user,
            scan_mode=serializer.validated_data['scan_mode'],
            status='scanning',
        )

        return Response({
            'session': SmartScanSessionSerializer(session).data,
            'message': 'Sesi scan dimulai.',
        }, status=status.HTTP_201_CREATED)


@extend_schema(exclude=True)
class SessionDetailView(APIView):
    """Get scan session details with aggregate items."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request, session_id):
        try:
            session = SmartScanSession.objects.get(
                id=session_id,
                store=request.user.store,
            )
        except SmartScanSession.DoesNotExist:
            return Response(
                {'error': 'Sesi tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = aggregate_scan_results(session)
        return Response(data)


class SessionListView(generics.ListAPIView):
    """List recent scan sessions for the seller's store."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)
    serializer_class = SmartScanSessionSerializer
    pagination_class = None

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return SmartScanSession.objects.none()

        return SmartScanSession.objects.filter(
            store=self.request.user.store
        ).order_by('-started_at')[:50]


@extend_schema(exclude=True)
class CancelSessionView(APIView):
    """Cancel an active scan session."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request, session_id):
        try:
            session = SmartScanSession.objects.get(
                id=session_id,
                store=request.user.store,
                status='scanning',
            )
        except SmartScanSession.DoesNotExist:
            return Response(
                {'error': 'Sesi scan aktif tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        session.status = 'cancelled'
        session.completed_at = timezone.now()
        session.save(update_fields=['status', 'completed_at', 'updated_at'])

        return Response({
            'success': True,
            'message': 'Sesi scan dibatalkan.',
        })


# =============================================================================
# REAL-TIME FRAME PROCESSING
# =============================================================================


@extend_schema(exclude=True)
class SubmitFrameView(APIView):
    """Submit camera frame detections to an active scan session.

    POST /api/inventory/ai-scan/{session_id}/frame/
    {
        "frame_number": 1,
        "detections": [
            {"label": "Beras Premium", "confidence": 0.92, "bbox": {...}, "features": {...}}
        ],
        "barcodes": [
            {"value": "8991234567890", "confidence": 0.98, "format": "ean13"}
        ],
        "ocr_text": "Beras Premium 5kg\nEXP: 12/2027\nLot: BATCH001",
        "ocr_confidence": 0.75
    }
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request, session_id):
        try:
            session = SmartScanSession.objects.get(
                id=session_id,
                store=request.user.store,
                status='scanning',
            )
        except SmartScanSession.DoesNotExist:
            return Response(
                {'error': 'Sesi scan aktif tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = FrameDetectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        frame_number = data.get('frame_number', 0)
        results = {}

        # Process object detections
        detections = data.get('detections', [])
        if detections:
            detection_result = process_frame_detections(
                session, detections, frame_number
            )
            results['detections'] = detection_result

        # Process barcodes
        barcodes = data.get('barcodes', [])
        if barcodes:
            barcode_result = process_barcode_detections(
                session, barcodes, frame_number
            )
            results['barcodes'] = barcode_result

        # Process OCR text
        ocr_text = data.get('ocr_text', '')
        if ocr_text:
            ocr_result = process_ocr_text(
                ocr_text,
                confidence=data.get('ocr_confidence', 0.5)
            )
            results['ocr'] = ocr_result

            # Apply OCR data to recent unmatched barcode items
            if ocr_result.get('success'):
                recent_items = DetectedItem.objects.filter(
                    session=session,
                    confirmation_status='pending',
                ).order_by('-detected_at')[:5]
                for item in recent_items:
                    process_detected_item_ocr(item, ocr_result)

        # Run deduplication
        dedup_result = deduplicate_session(session)
        results['dedup'] = dedup_result

        # Try to match unmatched items
        match_result = match_unmatched_items(session)
        results['auto_matched'] = match_result

        return Response({
            'success': True,
            'frame_number': frame_number,
            'session_id': session.id,
            'results': results,
        })


# =============================================================================
# BULK BARCODE SCAN
# =============================================================================


@extend_schema(exclude=True)
class BulkBarcodeScanView(APIView):
    """Submit bulk barcode scan for a session.

    Useful for scanning an entire shelf/stockroom at once.
    Each barcode entry can include count, batch number, and expiry date.

    POST /api/inventory/ai-scan/{session_id}/bulk/
    {
        "barcodes": [
            {"barcode": "8991234567890", "count": 12, "batch_number": "B001", "expiry_date": "2027-12-31"},
            {"barcode": "8991234567891", "count": 6}
        ]
    }
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request, session_id):
        try:
            session = SmartScanSession.objects.get(
                id=session_id,
                store=request.user.store,
                status='scanning',
            )
        except SmartScanSession.DoesNotExist:
            return Response(
                {'error': 'Sesi scan aktif tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = BulkBarcodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = process_bulk_barcodes(
            session, serializer.validated_data['barcodes']
        )

        # Update session status to review
        session.status = 'review'
        session.save(update_fields=['status', 'updated_at'])

        return Response({
            'success': True,
            'result': result,
            'message': 'Scan massal selesai. Silakan review hasil scan.',
        })


# =============================================================================
# ITEM REVIEW & CONFIRMATION
# =============================================================================


@extend_schema(exclude=True)
class SessionAggregatedView(APIView):
    """Get aggregated scan results ready for review.

    GET /api/inventory/ai-scan/{session_id}/review/
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request, session_id):
        try:
            session = SmartScanSession.objects.get(
                id=session_id,
                store=request.user.store,
            )
        except SmartScanSession.DoesNotExist:
            return Response(
                {'error': 'Sesi tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Auto-transition to review status if still scanning
        if session.status == 'scanning':
            session.status = 'review'
            session.save(update_fields=['status', 'updated_at'])

        data = aggregate_scan_results(session)
        return Response(data)


@extend_schema(exclude=True)
class UpdateDetectedItemView(APIView):
    """Update a detected item before confirming.

    Allows user to correct quantity, batch number, expiry date,
    product linkage, or notes before saving.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def patch(self, request, session_id, item_id):
        try:
            session = SmartScanSession.objects.get(
                id=session_id,
                store=request.user.store,
            )
        except SmartScanSession.DoesNotExist:
            return Response(
                {'error': 'Sesi tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UpdateDetectedItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = update_detected_item(item_id, serializer.validated_data)

        if result['success']:
            return Response(result)
        return Response(
            {'error': result.get('error', 'Gagal memperbarui item.')},
            status=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema(exclude=True)
class ConfirmAndSaveView(APIView):
    """Confirm detected items and save as inventory batches.

    POST /api/inventory/ai-scan/{session_id}/confirm/
    {
        "items": [
            {
                "item_id": 1,
                "confirmed_count": 10,
                "batch_number": "BATCH001",
                "expiry_date": "2027-12-31",
                "unit": "pcs",
                "notes": "From shelf scan"
            }
        ]
    }
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request, session_id):
        try:
            session = SmartScanSession.objects.get(
                id=session_id,
                store=request.user.store,
            )
        except SmartScanSession.DoesNotExist:
            return Response(
                {'error': 'Sesi tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ConfirmItemsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = confirm_and_save_items(
            session,
            serializer.validated_data['items'],
            request.user,
        )

        if result['success']:
            return Response({
                'success': True,
                'batches_created': result['batches_created'],
                'total_batches': result['total_batches'],
                'total_items_confirmed': result['total_items_confirmed'],
                'message': (
                    f"{result['total_batches']} batch berhasil dibuat dari "
                    f"{result['total_items_confirmed']} item."
                ),
            })

        return Response({
            'success': False,
            'batches_created': result.get('batches_created', []),
            'errors': result.get('errors', []),
            'message': 'Beberapa item gagal diproses.',
        }, status=status.HTTP_207_MULTI_STATUS)


@extend_schema(exclude=True)
class RejectAllPendingView(APIView):
    """Reject all pending items in a session."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request, session_id):
        try:
            session = SmartScanSession.objects.get(
                id=session_id,
                store=request.user.store,
            )
        except SmartScanSession.DoesNotExist:
            return Response(
                {'error': 'Sesi tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        updated = DetectedItem.objects.filter(
            session=session,
            confirmation_status='pending',
        ).update(
            confirmation_status='rejected',
        )

        session.status = 'cancelled'
        session.completed_at = timezone.now()
        session.save(update_fields=['status', 'completed_at', 'updated_at'])

        return Response({
            'success': True,
            'items_rejected': updated,
            'message': f'{updated} item ditolak.',
        })


# =============================================================================
# MASTER PRODUCT REGISTRATION
# =============================================================================


@extend_schema(exclude=True)
class RegisterNewProductFromScanView(APIView):
    """Register a new MasterProduct from scan data.

    Called when a scanned barcode is not found in the database.
    Auto-links any pending DetectedItems matching this barcode.
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def post(self, request, session_id):
        try:
            session = SmartScanSession.objects.get(
                id=session_id,
                store=request.user.store,
            )
        except SmartScanSession.DoesNotExist:
            return Response(
                {'error': 'Sesi tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = RegisterNewProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = register_new_product(
            session,
            serializer.validated_data,
            request.user,
        )

        if result['success']:
            # Link pending items with this barcode to the new master product
            master = MasterProduct.objects.get(id=result['master_product']['id'])
            linked = DetectedItem.objects.filter(
                session=session,
                detected_barcode=master.barcode,
                master_product__isnull=True,
            ).update(master_product=master)

            return Response({
                'success': True,
                'master_product': result['master_product'],
                'items_linked': linked,
                'message': (
                    f'Produk {master.product_name} berhasil didaftarkan. '
                    f'{linked} item terdeteksi telah ditautkan.'
                ),
            }, status=status.HTTP_201_CREATED)

        return Response(
            {'error': result.get('error', 'Gagal mendaftarkan produk.')},
            status=status.HTTP_400_BAD_REQUEST,
        )


# =============================================================================
# DETECTED ITEM LIST
# =============================================================================


class DetectedItemListView(generics.ListAPIView):
    """List all detected items for a session."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)
    serializer_class = DetectedItemSerializer
    pagination_class = None

    def get_queryset(self):
        session_id = self.kwargs.get('session_id')
        return DetectedItem.objects.filter(
            session_id=session_id,
            session__store=self.request.user.store,
        ).select_related('master_product').order_by('-confidence_score')


# =============================================================================
# SCAN SUMMARY / DASHBOARD
# =============================================================================


@extend_schema(exclude=True)
class ScanSummaryView(APIView):
    """Get AI scan summary for the seller's dashboard.

    GET /api/inventory/ai-scan/summary/?days=7
    """
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        days = int(request.query_params.get('days', 7))
        data = get_scan_summary(
            store=request.user.store,
            user=request.user,
            days=days,
        )
        return Response(data)


@extend_schema(exclude=True)
class ActiveSessionView(APIView):
    """Get the current active scanning session if any."""
    permission_classes = (permissions.IsAuthenticated, IsSeller)

    def get(self, request):
        session = SmartScanSession.objects.filter(
            store=request.user.store,
            status='scanning',
        ).order_by('-started_at').first()

        if session:
            data = aggregate_scan_results(session)
            data['session'] = SmartScanSessionSerializer(session).data
            return Response(data)

        return Response({
            'active': False,
            'message': 'Tidak ada sesi scan aktif.',
        })
