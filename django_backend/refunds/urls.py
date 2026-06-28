"""
Refunds URL configuration for Warungio Marketplace.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Buyer
    path('create/', views.CreateRefundView.as_view(), name='refund-create'),
    path('my-refunds/', views.MyRefundListView.as_view(), name='my-refunds'),
    path('<int:pk>/', views.RefundDetailView.as_view(), name='refund-detail'),
    path('<int:pk>/cancel/', views.BuyerCancelRefundView.as_view(), name='refund-cancel'),

    # Seller
    path('store-refunds/', views.StoreRefundListView.as_view(), name='store-refunds'),
    path('<int:pk>/seller-action/', views.SellerRefundActionView.as_view(), name='seller-refund-action'),

    # Admin
    path('admin/all/', views.AdminRefundListView.as_view(), name='admin-refunds'),
    path('<int:pk>/admin-action/', views.AdminRefundActionView.as_view(), name='admin-refund-action'),

    # Stats
    path('stats/', views.RefundStatsView.as_view(), name='refund-stats'),
]
