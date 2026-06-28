from django.contrib import admin
from .models import Payment, PaymentMethod, MidtransTransaction, BankAccount


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_name', 'is_active', 'fee_percent', 'order')
    list_filter = ('is_active',)
    list_editable = ('is_active', 'order', 'fee_percent')
    search_fields = ('name', 'display_name')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'transaction_code', 'user', 'amount', 'payment_status', 'payment_type', 'created_at')
    list_filter = ('payment_status', 'payment_type', 'created_at')
    search_fields = ('transaction_code', 'user__email', 'midtrans_order_id')
    readonly_fields = ('transaction_code', 'created_at', 'updated_at', 'paid_at')
    date_hierarchy = 'created_at'


@admin.register(MidtransTransaction)
class MidtransTransactionAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'transaction_id', 'transaction_status', 'payment_type', 'created_at')
    list_filter = ('transaction_status', 'payment_type')
    search_fields = ('order_id', 'transaction_id')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('bank_name', 'account_number', 'account_holder', 'store', 'is_primary')
    list_filter = ('bank_name', 'is_primary')
    search_fields = ('account_number', 'account_holder', 'store__store_name')
