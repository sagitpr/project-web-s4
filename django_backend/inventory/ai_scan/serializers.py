"""
Serializers for AI Smart Inventory Scanning.
Flutter-ready JSON for scan sessions, detected items, confirmation.
"""

from rest_framework import serializers
from inventory.models import SmartScanSession, DetectedItem, MasterProduct


class SmartScanSessionSerializer(serializers.ModelSerializer):
    """Scan session serializer."""
    duration_seconds = serializers.IntegerField(read_only=True)
    completion_rate = serializers.FloatField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    scan_mode_display = serializers.CharField(source='get_scan_mode_display', read_only=True)

    class Meta:
        model = SmartScanSession
        fields = [
            'id', 'store', 'user', 'scan_mode', 'scan_mode_display',
            'status', 'status_display',
            'frame_count', 'total_items_detected', 'total_items_confirmed',
            'total_batches_created',
            'duration_seconds', 'completion_rate',
            'started_at', 'completed_at', 'updated_at',
        ]
        read_only_fields = [
            'user', 'frame_count', 'total_items_detected',
            'total_items_confirmed', 'total_batches_created',
            'started_at', 'completed_at', 'updated_at',
        ]


class StartScanSerializer(serializers.Serializer):
    """Start a new AI scan session."""
    scan_mode = serializers.ChoiceField(
        choices=SmartScanSession.SCAN_MODE_CHOICES,
        default='multi',
    )


class FrameDetectionSerializer(serializers.Serializer):
    """Submit frame detections from camera."""
    frame_number = serializers.IntegerField(default=0)
    detections = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )
    barcodes = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )
    ocr_text = serializers.CharField(required=False, allow_blank=True, default='')
    ocr_confidence = serializers.FloatField(required=False, default=0.5)


class BulkBarcodeSerializer(serializers.Serializer):
    """Bulk barcode scan submission."""
    barcodes = serializers.ListField(
        child=serializers.DictField(),
        required=True,
    )
    """
    Each barcode entry:
    {
        'barcode': '8991234567890',
        'count': 12,
        'batch_number': 'BATCH001',
        'expiry_date': '2027-12-31',
    }
    """


class DetectedItemSerializer(serializers.ModelSerializer):
    """Detected item serializer."""
    master_product_name = serializers.CharField(
        source='master_product.product_name', read_only=True, allow_null=True
    )
    master_product_barcode = serializers.CharField(
        source='master_product.barcode', read_only=True, allow_null=True
    )
    status_display = serializers.CharField(
        source='get_confirmation_status_display', read_only=True
    )
    method_display = serializers.CharField(
        source='get_detection_method_display', read_only=True
    )

    class Meta:
        model = DetectedItem
        fields = [
            'id', 'session', 'store',
            'detection_method', 'method_display',
            'confidence_score',
            'master_product', 'master_product_name', 'master_product_barcode',
            'detected_count', 'confirmed_count', 'unit',
            'detected_barcode', 'barcode_confidence',
            'detected_batch_number', 'detected_expiry_date',
            'detected_product_name', 'detected_brand',
            'ocr_confidence',
            'bounding_box', 'detection_features',
            'frame_number',
            'confirmation_status', 'status_display',
            'user_notes',
            'created_batch',
            'detected_at', 'confirmed_at',
        ]
        read_only_fields = [
            'session', 'store', 'detected_at', 'confirmed_at',
        ]


class ConfirmItemsSerializer(serializers.Serializer):
    """Confirm and save detected items as inventory batches."""
    items = serializers.ListField(
        child=serializers.DictField(),
        required=True,
    )
    """
    Each item:
    {
        'item_id': 1,
        'confirmed_count': 10,
        'batch_number': 'BATCH001',
        'expiry_date': '2027-12-31',
        'unit': 'pcs',
        'notes': 'Optional notes',
    }
    """


class UpdateDetectedItemSerializer(serializers.Serializer):
    """Update a single detected item before confirmation."""
    confirmed_count = serializers.IntegerField(required=False)
    batch_number = serializers.CharField(required=False, allow_blank=True)
    expiry_date = serializers.DateField(required=False, allow_null=True)
    unit = serializers.CharField(required=False, allow_blank=True)
    master_product_id = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    confirmation_status = serializers.ChoiceField(
        choices=[
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('corrected', 'Corrected'),
            ('rejected', 'Rejected'),
        ],
        required=False,
    )


class RegisterNewProductSerializer(serializers.Serializer):
    """Register a new MasterProduct from scan data."""
    barcode = serializers.CharField(max_length=13, required=True)
    product_name = serializers.CharField(max_length=200, required=True)
    brand = serializers.CharField(max_length=100, required=False, allow_blank=True)
    category = serializers.CharField(max_length=100, required=False, default='Umum')
    subcategory = serializers.CharField(max_length=100, required=False, allow_blank=True)
    unit = serializers.ChoiceField(
        choices=MasterProduct.UNIT_CHOICES, default='pcs'
    )
    weight_value = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    weight_unit = serializers.CharField(max_length=10, required=False, allow_blank=True)
    image_url = serializers.URLField(required=False, allow_blank=True)
    manufacturer = serializers.CharField(max_length=200, required=False, allow_blank=True)
    bpom_number = serializers.CharField(max_length=30, required=False, allow_blank=True)


class AggregatedScanResultSerializer(serializers.Serializer):
    """Aggregated scan result for review UI."""
    item_ids = serializers.ListField(child=serializers.IntegerField())
    master_product_id = serializers.IntegerField(allow_null=True)
    master_product_name = serializers.CharField(allow_blank=True)
    barcode = serializers.CharField(allow_blank=True)
    brand = serializers.CharField(allow_blank=True)
    unit = serializers.CharField()
    total_count = serializers.IntegerField()
    confirmed_count = serializers.IntegerField()
    confidence = serializers.FloatField()
    batch_number = serializers.CharField(allow_blank=True)
    expiry_date = serializers.DateField(allow_null=True)
    detection_methods = serializers.ListField(child=serializers.CharField())
    status = serializers.CharField()


class ScanSummarySerializer(serializers.Serializer):
    """AI scan dashboard summary."""
    store_id = serializers.IntegerField()
    period_days = serializers.IntegerField()
    sessions = serializers.DictField()
    items = serializers.DictField()
    batches_created = serializers.IntegerField()
    avg_items_per_session = serializers.FloatField()
