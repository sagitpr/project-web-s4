"""
Refunds serializers for Warungio Marketplace.
"""
from rest_framework import serializers
from .models import Refund, RefundTimelineEvent
from orders.models import Order


class RefundTimelineEventSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = RefundTimelineEvent
        fields = ('id', 'refund', 'event_type', 'description',
                  'created_by', 'created_by_name', 'created_by_role',
                  'metadata', 'created_at')

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.full_name or obj.created_by.email
        return 'Sistem'


class RefundCreateSerializer(serializers.ModelSerializer):
    """Buyer creates a refund request."""

    class Meta:
        model = Refund
        fields = ('order', 'reason', 'reason_text', 'amount_requested',
                  'evidence_images', 'evidence_description', 'buyer_notes', 'refund_items')
        read_only_fields = ('refund_number', 'refund_status')

    def validate_order(self, value):
        user = self.context['request'].user
        if value.user != user:
            raise serializers.ValidationError("Pesanan bukan milik Anda.")
        if value.order_status not in ('completed', 'paid', 'on_delivery'):
            raise serializers.ValidationError(
                "Hanya pesanan dengan status Selesai, Dibayar, atau Dalam Perjalanan yang bisa direfund."
            )
        # Check if already has a pending/under_review refund
        existing = Refund.objects.filter(
            order=value,
            refund_status__in=('pending', 'under_review', 'waiting_buyer', 'waiting_seller')
        ).exists()
        if existing:
            raise serializers.ValidationError("Refund untuk pesanan ini sudah diajukan.")
        return value

    def validate_amount_requested(self, value):
        if value <= 0:
            raise serializers.ValidationError("Jumlah refund harus lebih dari 0.")
        return value


class RefundListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for refund lists."""
    store_name = serializers.CharField(source='store.store_name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    status_display = serializers.CharField(source='get_refund_status_display', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    buyer_name = serializers.SerializerMethodField()

    class Meta:
        model = Refund
        fields = ('id', 'refund_number', 'order', 'order_number',
                  'store_name', 'reason', 'reason_display', 'amount_requested',
                  'amount_approved', 'refund_status', 'status_display',
                  'is_escalated', 'created_at', 'resolved_at', 'buyer_name')

    def get_buyer_name(self, obj):
        if obj.user:
            return obj.user.full_name or obj.user.email
        return 'Pembeli'


class RefundDetailSerializer(serializers.ModelSerializer):
    """Detailed refund serializer with timeline and order info."""
    store_name = serializers.CharField(source='store.store_name', read_only=True)
    store_logo = serializers.SerializerMethodField()
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    order_status = serializers.CharField(source='order.order_status', read_only=True)
    order_created_at = serializers.DateTimeField(source='order.created_at', read_only=True)
    status_display = serializers.CharField(source='get_refund_status_display', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    resolution_display = serializers.CharField(source='get_resolution_display', read_only=True)
    timeline = RefundTimelineEventSerializer(many=True, read_only=True)
    buyer_name = serializers.SerializerMethodField()
    order_items = serializers.SerializerMethodField()

    class Meta:
        model = Refund
        fields = '__all__'

    def get_store_logo(self, obj):
        if obj.store and obj.store.store_logo:
            return obj.store.store_logo.url
        return None

    def get_buyer_name(self, obj):
        if obj.user:
            return obj.user.full_name or obj.user.email
        return 'Pembeli'

    def get_order_items(self, obj):
        items = obj.order.items.all()
        return [{
            'id': item.id,
            'product_name': item.product_name,
            'product_photo': item.product_photo,
            'qty': item.qty,
            'price': float(item.price),
            'subtotal': float(item.subtotal),
        } for item in items]


class SellerRefundActionSerializer(serializers.Serializer):
    """Seller reviews and takes action on a refund request."""
    action = serializers.ChoiceField(choices=[
        'approve', 'reject', 'negotiate', 'request_info'
    ])
    amount_approved = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        required=False, allow_null=True
    )
    resolution = serializers.ChoiceField(
        choices=Refund.RESOLUTION_CHOICES,
        required=False, allow_null=True
    )
    seller_notes = serializers.CharField(required=False, allow_blank=True)
    admin_notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        action = data.get('action')
        if action == 'approve' and not data.get('amount_approved'):
            data['amount_approved'] = None  # Will be set to amount_requested
        if action == 'negotiate' and not data.get('amount_approved'):
            raise serializers.ValidationError(
                {"amount_approved": "Jumlah negosiasi harus diisi."}
            )
        return data


class AdminRefundActionSerializer(serializers.Serializer):
    """Admin intervenes or resolves a refund dispute."""
    action = serializers.ChoiceField(choices=[
        'resolve', 'escalate', 'assign', 'close'
    ])
    resolution = serializers.ChoiceField(
        choices=Refund.RESOLUTION_CHOICES,
        required=False
    )
    amount_approved = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        required=False, allow_null=True
    )
    admin_notes = serializers.CharField(required=False, allow_blank=True)
