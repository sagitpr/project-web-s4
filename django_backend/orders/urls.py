"""
Orders URL configuration for Warungio Marketplace.
"""

from django.urls import path
from . import views
from . import views_guest_checkout

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

    # Delivery Webhook (unified: GrabExpress, GoSend, Mitra)
    path('webhooks/<str:provider>/', views.DeliveryWebhookView.as_view(), name='delivery-webhook'),
    path('webhooks/grabexpress/', views.DeliveryWebhookView.as_view(), {'provider': 'grabexpress'}, name='webhook-grabexpress'),
    path('webhooks/gosend/', views.DeliveryWebhookView.as_view(), {'provider': 'gosend'}, name='webhook-gosend'),
    path('webhooks/mitra/', views.DeliveryWebhookView.as_view(), {'provider': 'mitra_pengiriman'}, name='webhook-mitra'),
    path('webhooks/delivery/', views.DeliveryWebhookView.as_view(), name='delivery-webhook-infer'),

    path('delivery/rate/', views.DeliveryRateView.as_view(), name='delivery-rate'),
    path('delivery/auto-book/', views.DeliveryAutoBookView.as_view(), name='delivery-auto-book'),
    path('<int:order_id>/delivery/position/', views.DeliveryLivePositionView.as_view(), name='delivery-position'),

    # Mitra Pengiriman (Internal Fleet)
    path('mitra/drivers/', views.MitraDriverListCreateView.as_view(), name='mitra-drivers'),
    path('mitra/drivers/<int:pk>/', views.MitraDriverDetailView.as_view(), name='mitra-driver-detail'),
    path('mitra/tariffs/', views.MitraTariffListCreateView.as_view(), name='mitra-tariffs'),
    path('mitra/assign/', views.MitraAssignDriverView.as_view(), name='mitra-assign'),

    # QR Code generation & verification (Pickup & Delivery)
    path('<int:order_id>/delivery/qr/generate/', views.GenerateDeliveryQRView.as_view(), name='delivery-qr-generate'),
    path('<int:order_id>/delivery/qr/verify/', views.VerifyDeliveryQRView.as_view(), name='delivery-qr-verify'),

    # Proof of Delivery (POD) Upload
    path('<int:order_id>/delivery/pod/', views.DeliveryPODUploadView.as_view(), name='delivery-pod-upload'),

    # Guest Checkout (public — no auth required)
    path('guest-checkout/', views_guest_checkout.GuestCheckoutView.as_view(), name='guest-checkout'),

    # Public Tracking (no auth required)
    path('track-public/', views_guest_checkout.TrackOrderPublicView.as_view(), name='track-public'),
]
