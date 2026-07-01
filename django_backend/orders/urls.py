"""
Orders URL configuration for Warungio Marketplace.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Cart
    path('cart/', views.CartListView.as_view(), name='cart-list'),
    path('cart/count/', views.CartCountView.as_view(), name='cart-count'),
    path('cart/clear/', views.CartClearView.as_view(), name='cart-clear'),
    path('cart/<int:pk>/', views.CartDetailView.as_view(), name='cart-detail'),
    
    # Shipping Methods
    path('shipping-methods/', views.ShippingMethodListView.as_view(), name='shipping-methods'),
    
    # Orders
    path('create/', views.OrderCreateView.as_view(), name='order-create'),
    path('my-orders/', views.MyOrdersView.as_view(), name='my-orders'),
    path('history/', views.OrderHistoryView.as_view(), name='order-history'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    
    # Seller Orders
    path('seller/', views.SellerOrdersView.as_view(), name='seller-orders'),
    path('<int:order_id>/status/', views.OrderStatusUpdateView.as_view(), name='order-status-update'),

    # Buyer Cancel
    path('<int:order_id>/cancel/', views.BuyerCancelOrderView.as_view(), name='order-cancel'),

    # Delivery Tracking
    path('<int:order_id>/tracking/', views.DeliveryTrackingView.as_view(), name='delivery-tracking'),

    # Offline Sales (pembelian langsung di toko)
    path('offline-sale/', views.OfflineSaleCreateView.as_view(), name='offline-sale-create'),
    path('offline-sales/', views.OfflineSaleListView.as_view(), name='offline-sale-list'),

    # Packing Flow (Scan at Packing)
    path('<int:order_id>/packing/start/', views.PackingStartView.as_view(), name='packing-start'),
    path('<int:order_id>/packing/<int:session_id>/scan/', views.PackingScanItemView.as_view(), name='packing-scan'),
    path('<int:order_id>/packing/<int:session_id>/complete/', views.PackingCompleteView.as_view(), name='packing-complete'),
    path('<int:order_id>/packing/status/', views.PackingStatusView.as_view(), name='packing-status'),

    # POS Offline (Multi-item Scan & Pay)
    path('pos/checkout/', views.POSOfflineCreateView.as_view(), name='pos-checkout'),
]
