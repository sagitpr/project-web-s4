"""
URL Configuration for AI Intelligence Platform API.
"""
from django.urls import path
from ai_intelligence import views

urlpatterns = [
    # Digital Twin
    path('twin/', views.DigitalTwinView.as_view(), name='ai-twin'),
    path('twin/refresh/', views.RefreshDigitalTwinView.as_view(), name='ai-twin-refresh'),

    # Marketplace Health
    path('marketplace/health/', views.MarketplaceHealthView.as_view(), name='ai-marketplace-health'),
    path('marketplace/health/refresh/', views.MarketplaceHealthRefreshView.as_view(), name='ai-marketplace-health-refresh'),

    # Business Coach
    path('coach/insights/', views.CoachInsightsView.as_view(), name='ai-coach-insights'),
    path('coach/insights/<int:pk>/read/', views.CoachInsightReadView.as_view(), name='ai-coach-insight-read'),
    path('coach/insights/<int:pk>/dismiss/', views.CoachInsightDismissView.as_view(), name='ai-coach-insight-dismiss'),

    # Personal Shopping Assistant
    path('shopping/insights/', views.ShoppingInsightsView.as_view(), name='ai-shopping-insights'),
    path('shopping/insights/<int:pk>/read/', views.ShoppingInsightReadView.as_view(), name='ai-shopping-insight-read'),

    # Predictions
    path('predictions/demand/<int:product_id>/', views.DemandPredictionView.as_view(), name='ai-demand-prediction'),
    path('predictions/price/<int:product_id>/', views.PriceRecommendationView.as_view(), name='ai-price-recommendation'),
    path('predictions/<int:store_id>/forecast/', views.SalesForecastView.as_view(), name='ai-sales-forecast'),

    # Customer Segmentation
    path('segmentation/my/', views.MySegmentsView.as_view(), name='ai-my-segments'),
    path('segmentation/', views.SegmentListView.as_view(), name='ai-segments'),

    # Gamification
    path('gamification/', views.GamificationProfileView.as_view(), name='ai-gamification'),
    path('gamification/challenges/', views.UserChallengesView.as_view(), name='ai-challenges'),

    # Business Coach (seller)
    path('coach/generate/', views.GenerateCoachInsightsView.as_view(), name='ai-coach-generate'),

    # Learning Engine
    path('models/', views.AIModelRegistryView.as_view(), name='ai-models'),
    path('experiments/', views.ExperimentResultView.as_view(), name='ai-experiments'),

    # Dashboards
    path('dashboard/executive/', views.ExecutiveDashboardView.as_view(), name='ai-executive-dashboard'),
    path('dashboard/seller/', views.SellerDashboardView.as_view(), name='ai-seller-dashboard'),
    path('dashboard/buyer/', views.BuyerDashboardView.as_view(), name='ai-buyer-dashboard'),
]
