"""
Products URL configuration for Warungio Marketplace.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    
    # Products
    path('', views.ProductListView.as_view(), name='product-list'),
    path('featured/', views.ProductFeaturedView.as_view(), name='product-featured'),
    path('create/', views.ProductCreateView.as_view(), name='product-create'),
    path('my-products/', views.MyProductsView.as_view(), name='my-products'),
    path('<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('<int:pk>/manage/', views.ProductManageView.as_view(), name='product-manage'),
    
    # Store Products
    path('store/<int:store_id>/', views.StoreProductsView.as_view(), name='store-products'),
    
    # Reviews
    path('<int:product_id>/reviews/', views.ReviewListView.as_view(), name='product-reviews'),
    path('reviews/mine/', views.MyReviewsView.as_view(), name='my-reviews'),
    path('reviews/<int:pk>/', views.ReviewDetailView.as_view(), name='review-detail'),
    path('store-reviews/', views.SellerStoreReviewListView.as_view(), name='seller-store-reviews'),
    
    # Favorites
    path('<int:product_id>/favorite/', views.FavoriteView.as_view(), name='product-favorite'),
    path('my-favorites/', views.MyFavoritesView.as_view(), name='my-favorites'),
    
    # Smart Scan AI
    path('smart-scan/', views.SmartScanView.as_view(), name='smart-scan'),

    # Quality Checks
    path('quality-checks/', views.QualityCheckListView.as_view(), name='quality-check-list'),
    path('<int:product_id>/quality-checks/', views.ProductQualityCheckView.as_view(), name='product-quality-checks'),

    # Promos & Vouchers
    path('promos/', views.PromoListView.as_view(), name='promo-list'),
    path('seller-promos/', views.SellerPromoListCreateView.as_view(), name='seller-promo-list-create'),
    path('seller-promos/<int:pk>/', views.SellerPromoManageView.as_view(), name='seller-promo-manage'),
    path('check-voucher/', views.VoucherCheckView.as_view(), name='check-voucher'),
    
    # Recently Viewed
    path('recently-viewed/', views.RecentlyViewedView.as_view(), name='recently-viewed'),
    
    # Search Suggestions (autocomplete)
    path('search-suggestions/', views.SearchSuggestionsView.as_view(), name='search-suggestions'),
    
    # Smart Stock Prediction (seller)
    path('stock-prediction/', views.StockPredictionView.as_view(), name='stock-prediction'),
    path('store-forecast/', views.StoreStockForecastView.as_view(), name='store-forecast'),
    path('reorder-suggestions/', views.ReorderSuggestionView.as_view(), name='reorder-suggestions'),
    path('mock/stock-prediction/', views.MockStockPredictionView.as_view(), name='mock-stock-prediction'),

    # Low Stock Alerts (seller)
    path('low-stock/', views.LowStockProductsView.as_view(), name='low-stock-products'),

    # Wildcard Slug (must be at the bottom to prevent intercepting other paths)
    path('<slug:slug>/', views.ProductBySlugView.as_view(), name='product-detail-slug'),
]
