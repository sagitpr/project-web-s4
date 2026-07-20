"""
Supplier serializers for Warungio Marketplace.
Flutter-ready JSON response contracts.
"""

from rest_framework import serializers
from .models import (
    Supplier, SupplierCategory, SupplierProduct, SupplierOrder,
    SupplierOrderItem, SupplierReview, SupplierContract, SupplierPayment
)
from stores.serializers import StoreListSerializer
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.openapi import OpenApiTypes


class SupplierCategorySerializer(serializers.ModelSerializer):
    """Supplier category serializer."""

    class Meta:
        model = SupplierCategory
        fields = ['id', 'name', 'description', 'icon', 'sort_order', 'supplier_count']
        read_only_fields = ['supplier_count']

    supplier_count = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)


    def get_supplier_count(self, obj):
        return obj.suppliers.filter(is_active=True).count()


class SupplierListSerializer(serializers.ModelSerializer):
    """Lightweight supplier serializer for list views."""

    class Meta:
        model = Supplier
        fields = [
            'id', 'supplier_name', 'slug', 'category_name', 'city',
            'status', 'verification_level', 'rating_avg', 'rating_count',
            'total_products_supplied', 'on_time_delivery_rate', 'quality_score',
            'lead_time_days', 'logo_url', 'is_featured', 'is_active',
        ]
        read_only_fields = fields

    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    logo_url = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)


    def get_logo_url(self, obj):
        if obj.logo:
            return obj.logo.url
        return None


class SupplierDetailSerializer(serializers.ModelSerializer):
    """Detailed supplier serializer with nested data."""
    category = SupplierCategorySerializer(read_only=True)

    class Meta:
        model = Supplier
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'slug']

    logo = serializers.SerializerMethodField()
    banner = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)


    def get_logo(self, obj):
        return obj.logo.url if obj.logo else None

    @extend_schema_field(OpenApiTypes.STR)


    def get_banner(self, obj):
        return obj.banner.url if obj.banner else None


class SupplierProductSerializer(serializers.ModelSerializer):
    """Supplier product serializer."""

    class Meta:
        model = SupplierProduct
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class SupplierProductListSerializer(serializers.ModelSerializer):
    """Lightweight supplier product for listings."""
    supplier_name = serializers.CharField(source='supplier.supplier_name', read_only=True)

    class Meta:
        model = SupplierProduct
        fields = [
            'id', 'supplier', 'supplier_name', 'product_name', 'sku',
            'category', 'unit_price', 'unit', 'min_order_qty',
            'stock_available', 'is_available', 'estimated_delivery_days',
        ]


class SupplierOrderItemSerializer(serializers.ModelSerializer):
    """Supplier order item serializer."""

    class Meta:
        model = SupplierOrderItem
        fields = '__all__'
        read_only_fields = ['subtotal']


class SupplierOrderListSerializer(serializers.ModelSerializer):
    """Lightweight supplier order for lists."""
    supplier_name = serializers.CharField(source='supplier.supplier_name', read_only=True)
    store_name = serializers.CharField(source='store.store_name', read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = SupplierOrder
        fields = [
            'id', 'order_number', 'supplier', 'supplier_name', 'store', 'store_name',
            'status', 'payment_status', 'total_amount', 'item_count',
            'ordered_at', 'estimated_delivery', 'delivered_at',
        ]
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.STR)


    def get_item_count(self, obj):
        return obj.items.count()


class SupplierOrderDetailSerializer(serializers.ModelSerializer):
    """Detailed supplier order with items."""
    items = SupplierOrderItemSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source='supplier.supplier_name', read_only=True)
    store_name = serializers.CharField(source='store.store_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True, allow_null=True)

    class Meta:
        model = SupplierOrder
        fields = '__all__'
        read_only_fields = ['ordered_at', 'updated_at', 'order_number']


class SupplierReviewSerializer(serializers.ModelSerializer):
    """Supplier review serializer."""
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.supplier_name', read_only=True)

    class Meta:
        model = SupplierReview
        fields = '__all__'
        read_only_fields = ['created_at']


class SupplierContractSerializer(serializers.ModelSerializer):
    """Supplier contract serializer."""
    supplier_name = serializers.CharField(source='supplier.supplier_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True, allow_null=True)
    days_remaining = serializers.SerializerMethodField()

    class Meta:
        model = SupplierContract
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

    @extend_schema_field(OpenApiTypes.STR)


    def get_days_remaining(self, obj):
        from django.utils import timezone
        if obj.end_date:
            delta = obj.end_date - timezone.now().date()
            return delta.days
        return None


class SupplierPaymentSerializer(serializers.ModelSerializer):
    """Supplier payment serializer."""
    supplier_name = serializers.CharField(source='supplier.supplier_name', read_only=True)
    paid_by_name = serializers.CharField(source='paid_by.full_name', read_only=True, allow_null=True)

    class Meta:
        model = SupplierPayment
        fields = '__all__'
        read_only_fields = ['created_at']


# =============================================================================
# FLUTTER DTO — API Response Contracts for Mobile
# =============================================================================

class FlutterSupplierDTO(serializers.Serializer):
    """DTO for Flutter: Complete supplier profile."""
    id = serializers.IntegerField()
    supplier_name = serializers.CharField()
    slug = serializers.CharField()
    category = SupplierCategorySerializer(allow_null=True)
    description = serializers.CharField(allow_null=True)
    contact_person = serializers.CharField()
    phone = serializers.CharField()
    whatsapp = serializers.CharField(allow_null=True)
    email = serializers.EmailField(allow_null=True)
    website = serializers.URLField(allow_null=True)
    address = serializers.CharField()
    city = serializers.CharField()
    province = serializers.CharField()
    rating_avg = serializers.DecimalField(max_digits=3, decimal_places=2)
    rating_count = serializers.IntegerField()
    on_time_delivery_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    quality_score = serializers.IntegerField()
    verification_level = serializers.CharField()
    logo_url = serializers.URLField(allow_null=True)
    banner_url = serializers.URLField(allow_null=True)
    products_count = serializers.IntegerField()
    lead_time_days = serializers.IntegerField()
    delivery_coverage = serializers.ListField(child=serializers.CharField())
    payment_terms = serializers.CharField()
    min_order = serializers.DecimalField(max_digits=12, decimal_places=2)
    is_featured = serializers.BooleanField()


class FlutterSupplierProductDTO(serializers.Serializer):
    """DTO for Flutter: Supplier product listing."""
    id = serializers.IntegerField()
    product_name = serializers.CharField()
    sku = serializers.CharField(allow_null=True)
    category = serializers.CharField(allow_null=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit = serializers.CharField()
    min_order_qty = serializers.IntegerField()
    stock_available = serializers.IntegerField()
    is_available = serializers.BooleanField()
    estimated_delivery_days = serializers.IntegerField()
    supplier_id = serializers.IntegerField()
    supplier_name = serializers.CharField()


class FlutterSupplierOrderDTO(serializers.Serializer):
    """DTO for Flutter: Purchase order detail."""
    id = serializers.IntegerField()
    order_number = serializers.CharField()
    status = serializers.CharField()
    supplier_id = serializers.IntegerField()
    supplier_name = serializers.CharField()
    store_id = serializers.IntegerField()
    store_name = serializers.CharField()
    items = SupplierOrderItemSerializer(many=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    shipping_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    tax = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_status = serializers.CharField()
    payment_terms = serializers.CharField()
    due_date = serializers.DateField(allow_null=True)
    shipping_address = serializers.CharField()
    courier = serializers.CharField(allow_null=True)
    tracking_number = serializers.CharField(allow_null=True)
    estimated_delivery = serializers.DateField(allow_null=True)
    notes = serializers.CharField(allow_null=True)
    ordered_at = serializers.DateTimeField()
