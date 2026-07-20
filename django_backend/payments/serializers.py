"""
Payments serializers for Warungio Marketplace.
Midtrans Snap payment integration.
"""

from rest_framework import serializers
from .models import Payment, PaymentMethod, MidtransTransaction, BankAccount
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.openapi import OpenApiTypes


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = '__all__'


class PaymentSerializer(serializers.ModelSerializer):
    """Payment transaction serializer."""
    order_number = serializers.SerializerMethodField()
    store_name = serializers.SerializerMethodField()
    payment_details = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ('id', 'order', 'order_number', 'store_name', 'payment_type',
                  'payment_status', 'amount', 'fee', 'net_amount',
                  'transaction_code', 'midtrans_transaction_id',
                  'bank_name', 'va_number', 'payment_details',
                  'paid_at', 'expired_at', 'created_at')
        read_only_fields = ('transaction_code', 'payment_status', 'paid_at',
                           'created_at', 'payment_details')

    @extend_schema_field(OpenApiTypes.STR)


    def get_order_number(self, obj):
        return obj.order.order_number if obj.order else None

    def get_store_name(self, obj):
        return obj.order.store.store_name if (obj.order and obj.order.store) else None

    def get_payment_details(self, obj):
        try:
            mt = obj.midtrans
            return {
                'payment_type': mt.payment_type,
                'bank': mt.bank,
                'va_number': mt.va_number,
                'transaction_status': mt.transaction_status,
                'transaction_time': mt.transaction_time,
            }
        except MidtransTransaction.DoesNotExist:
            return None


class MidtransSnapRequest(serializers.Serializer):
    """Midtrans Snap transaction request serializer."""
    order_id = serializers.IntegerField(required=True)
    payment_method = serializers.ChoiceField(
        choices=[
            ('credit_card', 'credit_card'),
            ('bank_transfer', 'bank_transfer'),
            ('gopay', 'gopay'),
            ('shopeepay', 'shopeepay'),
            ('ovo', 'ovo'),
            ('dana', 'dana'),
            ('qris', 'qris'),
        ],
        default='bank_transfer'
    )
    bank = serializers.ChoiceField(
        choices=['bca', 'bni', 'bri', 'mandiri', 'cimb', 'permata'],
        required=False
    )


class MidtransNotificationSerializer(serializers.Serializer):
    """Midtrans payment notification callback serializer."""
    transaction_time = serializers.DateTimeField(required=False)
    transaction_status = serializers.CharField(required=True)
    transaction_id = serializers.CharField(required=False)
    status_code = serializers.CharField(required=False)
    status_message = serializers.CharField(required=False)
    order_id = serializers.CharField(required=True)
    payment_type = serializers.CharField(required=False)
    gross_amount = serializers.CharField(required=False)
    fraud_status = serializers.CharField(required=False)
    bank = serializers.CharField(required=False, allow_null=True)
    va_number = serializers.CharField(required=False, allow_null=True)
    bill_key = serializers.CharField(required=False, allow_null=True)
    biller_code = serializers.CharField(required=False, allow_null=True)
    signature_key = serializers.CharField(required=False)


class PaymentHistorySerializer(serializers.ModelSerializer):
    """Payment history for user dashboard."""
    order_number = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = ('id', 'order_number', 'payment_type', 'payment_status',
                  'amount', 'transaction_code', 'paid_at', 'created_at')

    def get_order_number(self, obj):
        return obj.order.order_number if obj.order else None


class BankAccountSerializer(serializers.ModelSerializer):
    """Serializer for store bank accounts."""
    class Meta:
        model = BankAccount
        fields = ('id', 'store', 'bank_name', 'account_number', 'account_holder', 'is_primary', 'created_at')
        read_only_fields = ('store', 'created_at')
