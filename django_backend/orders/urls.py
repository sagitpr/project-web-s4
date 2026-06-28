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
]
