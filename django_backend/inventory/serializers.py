"""
Serializers for inventory management.
Flutter-ready JSON for barcode scanning, batch entry, FEFO picking.
"""

from rest_framework import serializers
from .models import MasterProduct, ProductBatch, InventoryStock, ExpiryNotification, StockAlert
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.openapi import OpenApiTypes


class MasterProductSerializer(serializers.ModelSerializer):
    """Master product database serializer."""
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = MasterProduct
        fields = '__all__'

    @extend_schema_field(OpenApiTypes.STR)
    def get_display_name(self, obj):
        if obj.brand:
            return f"{obj.brand} - {obj.product_name}"
        return obj.product_name


class MasterProductCreateSerializer(serializers.Serializer):
    """Create a master product from barcode scan data."""
    barcode = serializers.CharField(max_length=13, required=True)
    product_name = serializers.CharField(max_length=200, required=True)
    brand = serializers.CharField(max_length=100, required=False, allow_blank=True)
    category = serializers.CharField(max_length=100, required=False, default='Umum')
    subcategory = serializers.CharField(max_length=100, required=False, allow_blank=True)
    unit = serializers.ChoiceField(choices=MasterProduct.UNIT_CHOICES, default='pcs')
    weight_value = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    weight_unit = serializers.CharField(max_length=10, required=False, allow_blank=True)
    image_url = serializers.URLField(required=False, allow_blank=True)
    manufacturer = serializers.CharField(max_length=200, required=False, allow_blank=True)
    bpom_number = serializers.CharField(max_length=30, required=False, allow_blank=True)


class BarcodeLookupSerializer(serializers.Serializer):
    """Barcode lookup request/response."""
    barcode = serializers.CharField(max_length=13, required=True)
    store_id = serializers.IntegerField(required=False)


class BarcodeLookupResultSerializer(serializers.Serializer):
    """Barcode lookup result."""
    found = serializers.BooleanField()
    master_product = MasterProductSerializer(required=False, allow_null=True)
    source = serializers.CharField()
    error = serializers.CharField(required=False, allow_blank=True)
    is_new = serializers.BooleanField(required=False, default=False)


class ProductBatchSerializer(serializers.ModelSerializer):
    """Batch entry serializer."""
    product_name = serializers.CharField(source='master_product.product_name', read_only=True)
    barcode = serializers.CharField(source='master_product.barcode', read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ProductBatch
        fields = [
            'id', 'store', 'master_product', 'product', 'product_name', 'barcode',
            'batch_number', 'production_date', 'expiry_date',
            'initial_quantity', 'current_quantity', 'unit',
            'purchase_price', 'shelf_life_days', 'shelf_life_remaining_pct',
            'status', 'status_display', 'days_until_expiry',
            'notes', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'shelf_life_days', 'shelf_life_remaining_pct',
            'status', 'days_until_expiry', 'created_at', 'updated_at',
        ]


class BatchCreateSerializer(serializers.Serializer):
    """Create/modify batch with stock_in."""
    master_product_id = serializers.IntegerField(required=True)
    product_id = serializers.IntegerField(required=False, allow_null=True)
    batch_number = serializers.CharField(max_length=100, required=True)
    production_date = serializers.DateField(required=True)
    expiry_date = serializers.DateField(required=True)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)
    unit = serializers.CharField(max_length=20, default='pcs')
    purchase_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class InventoryStockSerializer(serializers.ModelSerializer):
    """Stock transaction log serializer."""
    product_name = serializers.CharField(source='master_product.product_name', read_only=True)
    batch_number = serializers.CharField(source='batch.batch_number', read_only=True)
    expiry_date = serializers.DateField(source='batch.expiry_date', read_only=True)

    class Meta:
        model = InventoryStock
        fields = [
            'id', 'store', 'master_product', 'product', 'batch',
            'product_name', 'batch_number', 'expiry_date',
            'transaction_type', 'quantity', 'quantity_before', 'quantity_after',
            'reference_type', 'reference_id', 'notes', 'created_by', 'created_at',
        ]
        read_only_fields = ['created_at']


class StockOutSerializer(serializers.Serializer):
    """Stock outbound request (FEFO picking)."""
    master_product_id = serializers.IntegerField(required=True)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    reference_type = serializers.CharField(required=False, allow_blank=True)
    reference_id = serializers.CharField(required=False, allow_blank=True)


class FEFOPickResultSerializer(serializers.Serializer):
    """FEFO picking result."""
    transaction_id = serializers.IntegerField()
    batch_id = serializers.IntegerField()
    batch_number = serializers.CharField()
    expiry_date = serializers.DateField()
    quantity = serializers.FloatField()


class StockOutResultSerializer(serializers.Serializer):
    """Stock outbound result."""
    success = serializers.BooleanField()
    total_quantity = serializers.FloatField()
    batches_used = serializers.IntegerField()
    transactions = FEFOPickResultSerializer(many=True)
    note = serializers.CharField()


class ExpirySummarySerializer(serializers.Serializer):
    """Expiry dashboard summary."""
    store_id = serializers.IntegerField()
    today = serializers.DateField()
    expiring_this_week_count = serializers.IntegerField()
    expiring_this_month_count = serializers.IntegerField()
    already_expired_count = serializers.IntegerField()


class ExpiryNotificationSerializer(serializers.ModelSerializer):
    """Expiry notification record."""
    product_name = serializers.CharField(source='batch.master_product.product_name', read_only=True)

    class Meta:
        model = ExpiryNotification
        fields = '__all__'


class StockAlertSerializer(serializers.ModelSerializer):
    """Stock threshold alert serializer."""
    product_name = serializers.CharField(source='master_product.product_name', read_only=True)

    class Meta:
        model = StockAlert
        fields = '__all__'
        read_only_fields = ['store']


class BatchSummarySerializer(serializers.Serializer):
    """Aggregated batch summary."""
    total_batches = serializers.IntegerField()
    total_stock_qty = serializers.FloatField()
    fresh_count = serializers.IntegerField()
    fresh_qty = serializers.FloatField()
    expiring_soon_count = serializers.IntegerField()
    expiring_soon_qty = serializers.FloatField()
    expired_count = serializers.IntegerField()
    expired_qty = serializers.FloatField()
    disposed_count = serializers.IntegerField()
    disposed_qty = serializers.FloatField()
