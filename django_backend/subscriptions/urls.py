"""Subscription URL configuration for Warungio Marketplace."""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.SubscriptionListView.as_view(), name='subscription-list'),
    path('my/', views.MySubscriptionView.as_view(), name='subscription-my'),
    path('<int:pk>/', views.SubscriptionDetailView.as_view(), name='subscription-detail'),
    path('store/<int:store_id>/', views.StoreSubscriptionView.as_view(), name='subscription-store'),
    path('check/<int:store_id>/', views.CheckSubscriptionStatusView.as_view(), name='subscription-check'),
]
