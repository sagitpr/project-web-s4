"""
Supplier URL configuration for Warungio Marketplace.
Flutter-ready API endpoints.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Categories
    path('categories/', views.SupplierCategoryListView.as_view(), name='supplier-categories'),
    path('categories/<int:pk>/', views.SupplierCategoryDetailView.as_view(), name='supplier-category-detail'),

    # Suppliers
    path('', views.SupplierListView.as_view(), name='supplier-list'),
    path('featured/', views.SupplierFeaturedView.as_view(), name='supplier-featured'),
    path('top-rated/', views.SupplierTopRatedView.as_view(), name='supplier-top-rated'),
    path('<int:pk>/', views.SupplierDetailView.as_view(), name='supplier-detail'),
    path('<slug:slug>/', views.SupplierBySlugView.as_view(), name='supplier-detail-slug'),
    path('<int:pk>/products/', views.SupplierProductsView.as_view(), name='supplier-products'),
    path('<int:pk>/reviews/', views.SupplierReviewsView.as_view(), name='supplier-reviews'),
    path('<int:pk>/contracts/', views.SupplierContractsView.as_view(), name='supplier-contracts'),

    # Supplier Products (direct)
    path('products/', views.SupplierProductListView.as_view(), name='supplier-product-list'),
    path('products/<int:pk>/', views.SupplierProductDetailView.as_view(), name='supplier-product-detail'),

    # Purchase Orders (for stores)
    path('orders/', views.SupplierOrderListCreateView.as_view(), name='supplier-order-list'),
    path('orders/<int:pk>/', views.SupplierOrderDetailView.as_view(), name='supplier-order-detail'),
    path('orders/<int:pk>/update-status/', views.SupplierOrderStatusView.as_view(), name='supplier-order-status'),

    # Supplier Management (for sellers)
    path('my-suppliers/', views.MySupplierListView.as_view(), name='my-suppliers'),
    path('register/', views.SupplierRegisterView.as_view(), name='supplier-register'),

    # Mock endpoints removed for production

    # Search
    path('search/', views.SupplierSearchView.as_view(), name='supplier-search'),
]
