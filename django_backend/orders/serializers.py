"""
Orders serializers for Warungio Marketplace.
"""

from rest_framework import serializers
from .models import Cart, Order, OrderItem, Delivery, ShippingMethod, OfflineSale
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.openapi import OpenApiTypes


class ShippingMethodSerializer(serializers.ModelSerializer):
    """Serializer for hyperlocal shipping methods."""
    class Meta:
        model = ShippingMethod
        fields = ('id', 'code', 'name', 'description', 'icon', 'is_active',
                  'estimated_time', 'base_fee', 'sort_order')


class CartSerializer(serializers.ModelSerializer):
    """Cart serializer with product details."""
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    product_photo = serializers.SerializerMethodField()
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    product_stock = serializers.IntegerField(source='product.stock', read_only=True)
    product_status = serializers.CharField(source='product.product_status', read_only=True)
    store_name = serializers.CharField(source='product.store.store_name', read_only=True)
    store_id = serializers.IntegerField(source='product.store.id', read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ('id', 'user', 'product', 'product_name', 'product_photo',
                  'product_price', 'product_stock', 'product_status',
                  'store_name', 'store_id', 'qty', 'subtotal', 'created_at')
        read_only_fields = ('user', 'created_at')

    @extend_schema_field(OpenApiTypes.STR)
    def get_product_photo(self, obj):
        if obj.product and obj.product.product_photo:
            return obj.product.product_photo.url
        return None

    def validate_qty(self, value):
        # For POST (create): get product ID from request data
        # For PATCH (update): get product from existing instance
        product_id = self.initial_data.get('product')
        product = None
        from products.models import Product
        if product_id:
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                pass
        elif self.instance and self.instance.product_id:
            try:
                product = Product.objects.get(id=self.instance.product_id)
            except Product.DoesNotExist:
                pass
        if product:
            available = product.available_stock
            if value > available:
                raise serializers.ValidationError(
                    f"Stok tidak mencukupi. Tersedia: {available}"
                )
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'product_name', 'product_photo',
                  'qty', 'price', 'subtotal')
        read_only_fields = ('product_name', 'product_photo', 'subtotal')


class OrderListSerializer(serializers.ModelSerializer):
    """Lightweight order serializer for lists."""
    store_name = serializers.CharField(source='store.store_name', read_only=True)
    store_logo = serializers.SerializerMethodField()
    item_count = serializers.IntegerField(source='items.count', read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'order_number', 'store_name', 'store_logo',
                  'subtotal', 'shipping_cost', 'discount',
                  'admin_fee', 'admin_fee_buyer',
                  'total_price', 'payment_method', 'order_status',
                  'item_count', 'created_at', 'completed_at')

    @extend_schema_field(OpenApiTypes.STR)
    def get_store_logo(self, obj):
        if obj.store and obj.store.store_logo:
            return obj.store.store_logo.url
        return None


class OrderDetailSerializer(serializers.ModelSerializer):
    """Detailed order serializer."""
    items = OrderItemSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    store_name = serializers.CharField(source='store.store_name', read_only=True)
    delivery = serializers.SerializerMethodField()
    shipping_method_name = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ('order_number', 'user', 'created_at', 'updated_at')

    @extend_schema_field(OpenApiTypes.STR)
    def get_shipping_method_name(self, obj):
        if obj.shipping_method:
            return obj.shipping_method.name
        return obj.courier or ''

    @extend_schema_field(OpenApiTypes.STR)
    def get_delivery(self, obj):
        try:
            delivery = obj.delivery
            sm = delivery.shipping_method
            return {
                'shipping_method_id': sm.id if sm else None,
                'shipping_method_name': sm.name if sm else (delivery.courier_name or ''),
                'courier_name': delivery.courier_name,
                'courier_phone': delivery.courier_phone,
                'driver_name': delivery.driver_name,
                'driver_phone': delivery.driver_phone,
                'tracking_number': delivery.tracking_number,
                'pickup_code': delivery.pickup_code,
                'delivery_status': delivery.delivery_status,
                'estimated_time': delivery.estimated_time,
                'estimated_pickup': delivery.estimated_pickup,
                'distance': float(delivery.distance) if delivery.distance else None,
                'buyer_latitude': float(delivery.buyer_latitude) if delivery.buyer_latitude else None,
                'buyer_longitude': float(delivery.buyer_longitude) if delivery.buyer_longitude else None,
            }
        except Delivery.DoesNotExist:
            return None


class OrderCreateSerializer(serializers.Serializer):
    """Order creation from cart serializer."""
    cart_items = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )
    shipping_method = serializers.IntegerField(required=False, allow_null=True)
    delivery_address = serializers.CharField(required=True)
    recipient_name = serializers.CharField(required=True)
    recipient_phone = serializers.CharField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(
        choices=['midtrans', 'cod', 'transfer'], default='midtrans'
    )
    vouchers = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)

    def validate_cart_items(self, value):
        from .models import Cart
        user = self.context['request'].user
        cart_ids = Cart.objects.filter(id__in=value, user=user)
        if cart_ids.count() != len(value):
            raise serializers.ValidationError(
                "Beberapa item keranjang tidak valid."
            )
        return value


class DeliverySerializer(serializers.ModelSerializer):
    shipping_method_name = serializers.CharField(source='shipping_method.name', read_only=True)

    class Meta:
        model = Delivery
        fields = '__all__'
        read_only_fields = ('order', 'created_at', 'updated_at')


class OrderStatusSerializer(serializers.Serializer):
    """Update order status serializer (seller actions).
    Supports hyperlocal delivery flow:
    - processed: confirm order
    - ready_pickup: ready for courier pickup
    - courier_pickup: courier picks up
    - on_delivery: in transit
    - completed: delivered
    - cancelled: cancel order
    """
    status = serializers.ChoiceField(choices=[
        'processed', 'ready_pickup', 'courier_pickup',
        'on_delivery', 'completed', 'cancelled'
    ])
    tracking_number = serializers.CharField(required=False, allow_blank=True)
    courier = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    # Hyperlocal delivery fields
    driver_name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    driver_phone = serializers.CharField(required=False, allow_blank=True, max_length=30)
    pickup_code = serializers.CharField(required=False, allow_blank=True, max_length=20)
    estimated_time = serializers.CharField(required=False, allow_blank=True, max_length=100)
    estimated_pickup = serializers.CharField(required=False, allow_blank=True, max_length=100)

    # Cancel-specific fields
    cancel_reason = serializers.ChoiceField(choices=[
        'out_of_stock', 'seller_unavailable', 'wrong_price',
        'address_invalid', 'product_damaged', 'other'
    ], required=False, allow_blank=True)
    cancel_reason_text = serializers.CharField(required=False, allow_blank=True, max_length=500)


class CancelOrderSerializer(serializers.Serializer):
    """Cancel order by buyer serializer."""
    reason = serializers.ChoiceField(choices=[
        'change_mind', 'found_cheaper', 'delivery_too_long',
        'wrong_address', 'duplicate_order', 'other'
    ], required=False, allow_blank=True)
    reason_text = serializers.CharField(required=False, allow_blank=True, max_length=500)


class OfflineSaleSerializer(serializers.ModelSerializer):
    """Serializer untuk mencatat penjualan offline & mengurangi stok."""
    product_name = serializers.CharField(read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    store_name = serializers.CharField(source='store.store_name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.full_name', read_only=True)
    price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        help_text='Harga satuan. Default: harga produk saat ini'
    )

    class Meta:
        model = OfflineSale
        fields = ('id', 'store', 'store_name', 'product', 'product_name',
                  'quantity', 'price', 'total', 'buyer_name', 'buyer_phone',
                  'notes', 'payment_method', 'recorded_by', 'recorded_by_name',
                  'created_at')
        read_only_fields = ('store', 'recorded_by', 'created_at')
        extra_kwargs = {
            'buyer_name': {'required': False, 'allow_blank': True},
            'buyer_phone': {'required': False, 'allow_blank': True},
            'notes': {'required': False, 'allow_blank': True},
            'payment_method': {'required': False},
        }

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Jumlah harus lebih dari 0.")
        return value

    def validate(self, data):
        product = data.get('product')
        quantity = data.get('quantity', 0)
        if product and product.stock < quantity:
            raise serializers.ValidationError(
                f"Stok tidak mencukupi. Tersedia: {product.stock}, diminta: {quantity}"
            )
        return data


class OfflineSaleListSerializer(serializers.ModelSerializer):
    """Serializer ringkas untuk daftar penjualan offline."""
    product_name = serializers.CharField(read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = OfflineSale
        fields = ('id', 'product', 'product_name', 'quantity', 'price',
                  'total', 'buyer_name', 'payment_method', 'created_at')
