"""
Payments URL configuration for Warungio Marketplace.
"""

from django.urls import path
from . import views
from . import pos_views

urlpatterns = [
    path('methods/', views.PaymentMethodListView.as_view(), name='payment-methods'),
    path('config/', views.PaymentConfigView.as_view(), name='payment-config'),
    path('create-snap/', views.CreateSnapTransactionView.as_view(), name='create-snap'),
    path('notification/', views.MidtransNotificationView.as_view(), name='midtrans-notification'),
    path('status/<int:order_id>/', views.PaymentStatusView.as_view(), name='payment-status'),
    path('history/', views.PaymentHistoryView.as_view(), name='payment-history'),
    path('wallet/topup/', views.WalletTopUpView.as_view(), name='wallet-topup'),
    
    # Seller Finance & Bank Accounts
    path('finance/summary/', views.FinanceSummaryView.as_view(), name='finance-summary'),
    path('finance/transactions/', views.FinanceTransactionListView.as_view(), name='finance-transactions'),
    path('finance/bank-accounts/', views.BankAccountListView.as_view(), name='finance-bank-accounts'),
    path('finance/bank-accounts/<int:pk>/', views.BankAccountDetailView.as_view(), name='finance-bank-account-detail'),
    path('finance/bank-accounts/<int:pk>/set-primary/', views.BankAccountSetPrimaryView.as_view(), name='finance-bank-account-set-primary'),
    path('finance/withdraw/', views.WithdrawBalanceView.as_view(), name='finance-withdraw'),
    # Public API Configuration (safe frontend keys)
    path('config/public/', views.PublicApiConfigView.as_view(), name='public-api-config'),

    # Merchant Status (dynamic seller activation)
    path('merchant-status/', views.MidtransMerchantStatusView.as_view(), name='midtrans-merchant-status'),

    # Wallet Endpoints (database-driven, not device_info)
    path('wallet/balance/', views.WalletBalanceView.as_view(), name='wallet-balance'),
    path('wallet/transactions/', views.WalletTransactionListView.as_view(), name='wallet-transactions'),

    # POS Offline Transaction
    path('pos/complete/', pos_views.POSCompleteSaleView.as_view(), name='pos-complete-sale'),
]
