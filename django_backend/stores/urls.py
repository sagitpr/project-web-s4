"""
Stores URL configuration for Warungio Marketplace.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.StoreListView.as_view(), name='store-list'),
    path('categories/', views.StoreCategoryListView.as_view(), name='store-categories'),
    path('my-store/', views.MyStoreView.as_view(), name='my-store'),
    path('create/', views.StoreCreateView.as_view(), name='store-create'),
    path('<int:pk>/', views.StoreDetailView.as_view(), name='store-detail'),
    path('slug/<slug:slug>/', views.StoreDetailView.as_view(), name='store-detail-slug'),
    path('my-followed/', views.MyFollowedStoresView.as_view(), name='my-followed-stores'),
    path('<int:store_id>/follow/', views.StoreFollowView.as_view(), name='store-follow'),
    path('<int:store_id>/followers/', views.StoreFollowersView.as_view(), name='store-followers'),
]
