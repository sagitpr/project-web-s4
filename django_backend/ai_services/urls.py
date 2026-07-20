"""
AI Services API URL Configuration.
All endpoints under /api/ai/ prefix.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Health / Connection Verification
    path('health/', views.AIHealthView.as_view(), name='ai-health'),
    
    # Product Recommendations
    path('recommendations/', views.AIRecommendationsView.as_view(), name='ai-recommendations'),
    path('recommendations/similar/<int:product_id>/', views.AISimilarProductsView.as_view(), name='ai-similar-products'),
    
    # Smart Search
    path('search/', views.AISmartSearchView.as_view(), name='ai-search'),
    path('search/suggestions/', views.AISearchSuggestionsView.as_view(), name='ai-search-suggestions'),
    
    # Vision Analysis
    path('vision/', views.AIProductVisionView.as_view(), name='ai-vision'),
    path('vision/freshness/', views.AIFreshnessDetectionView.as_view(), name='ai-freshness'),
    path('vision/task/<uuid:task_id>/', views.AIVisionTaskStatusView.as_view(), name='ai-vision-task-status'),
    
    # Product Description
    path('describe/', views.AIProductDescriptionView.as_view(), name='ai-describe'),
    
    # Review Analysis
    path('reviews/analyze/', views.AIReviewAnalysisView.as_view(), name='ai-review-analysis'),
    
    # Seller Assistant
    path('seller/insights/', views.AISellerAssistantView.as_view(), name='ai-seller-insights'),
    path('seller/recommendations/', views.AISellerStockView.as_view(), name='ai-seller-recommendations'),
    
    # Category Classification
    path('classify/', views.AICategoryClassifierView.as_view(), name='ai-classify'),
    
    # Fraud Detection
    path('fraud/order/<int:order_id>/', views.AIFraudOrderView.as_view(), name='ai-fraud-order'),
    path('fraud/user/<int:user_id>/', views.AIFraudUserView.as_view(), name='ai-fraud-user'),
    
    # Notification Generator
    path('notifications/generate/', views.AINotificationGenerateView.as_view(), name='ai-notification-generate'),
    
    # Dashboard Insights
    path('dashboard/seller/', views.AIDashboardSellerView.as_view(), name='ai-dashboard-seller'),
    path('dashboard/admin/', views.AIDashboardAdminView.as_view(), name='ai-dashboard-admin'),
]
