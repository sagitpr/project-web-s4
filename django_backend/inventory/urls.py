"""
Inventory management URL routes.
All endpoints under /api/inventory/ prefix.
Flutter-ready API design.
"""

from django.urls import path, include
from . import views

urlpatterns = [
    # Root — list available endpoints
    path('', views.InventoryRootView.as_view(), name='inventory-root'),

    # Master Product Database
    path('master-products/', views.MasterProductSearchView.as_view(), name='master-product-search'),
    path('master-products/create/', views.MasterProductCreateView.as_view(), name='master-product-create'),
    path('master-products/<int:pk>/', views.MasterProductDetailView.as_view(), name='master-product-detail'),

    # Barcode Lookup
    path('barcode-lookup/', views.BarcodeLookupView.as_view(), name='barcode-lookup'),

    # Batch Management
    path('batches/create/', views.BatchCreateView.as_view(), name='batch-create'),
    path('batches/', views.BatchListView.as_view(), name='batch-list'),
    path('batches/<int:pk>/', views.BatchDetailView.as_view(), name='batch-detail'),
    path('batches/<int:pk>/update/', views.BatchUpdateView.as_view(), name='batch-update'),
    path('batches/<int:pk>/dispose/', views.BatchDisposeView.as_view(), name='batch-dispose'),
    path('batches/summary/', views.BatchSummaryView.as_view(), name='batch-summary'),

    # FEFO Stock Outbound
    path('stock-out/', views.StockOutView.as_view(), name='stock-out'),
    path('fefo-check/', views.FEFOCheckView.as_view(), name='fefo-check'),

    # Inventory Transactions
    path('transactions/', views.InventoryTransactionListView.as_view(), name='transaction-list'),

    # Expiry Dashboard
    path('expiry/summary/', views.ExpirySummaryView.as_view(), name='expiry-summary'),
    path('expiry/check/', views.ExpiryCheckTriggerView.as_view(), name='expiry-check'),
    path('expiry/notifications/', views.ExpiryNotificationListView.as_view(), name='expiry-notifications'),

    # Stock Alerts
    path('alerts/', views.StockAlertListCreateView.as_view(), name='alert-list-create'),
    path('alerts/<int:pk>/', views.StockAlertDetailView.as_view(), name='alert-detail'),
    path('low-stock-report/', views.LowStockReportView.as_view(), name='low-stock-report'),

    # AI Smart Inventory Scanning
    path('ai-scan/', include('inventory.ai_scan.urls')),

    # AI Auto-Register Draft Product
    path('ai-auto-register/', views.AIAutoRegisterDraftView.as_view(), name='ai-auto-register'),

    # AI Product Recognition (Hybrid Pipeline)
    path('ai-recognize/', views.AIProductRecognizeView.as_view(), name='ai-product-recognize'),
    path('ai-multi-detect/', views.AIMultiDetectView.as_view(), name='ai-multi-detect'),
    path('ai-freshness/', views.AIFreshnessView.as_view(), name='ai-freshness'),
    path('ai-learn-product/', views.AILearnProductView.as_view(), name='ai-learn-product'),

    # AI Expired Reminder & Discount Recommendations
    path('expired-reminder/dashboard/', views.ExpiredReminderDashboardView.as_view(), name='expired-reminder-dashboard'),
    path('expired-reminder/flash-sale/', views.FlashSaleCandidatesView.as_view(), name='expired-reminder-flash-sale'),
    path('expired-reminder/discounts/', views.DiscountRecommendationsView.as_view(), name='expired-reminder-discounts'),
    path('expired-reminder/check/', views.TriggerExpiryCheckView.as_view(), name='expired-reminder-check'),
]
