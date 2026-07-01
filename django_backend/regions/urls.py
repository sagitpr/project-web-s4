"""
URL configuration for the Indonesian region API.
Flutter-ready endpoints for cascading region selector.
"""

from django.urls import path
from . import views

urlpatterns = [
    # List all provinces
    path('provinces/', views.ProvinceListView.as_view(), name='region-provinces'),
    
    # Province detail with regencies
    path('provinces/<str:code>/', views.ProvinceDetailView.as_view(), name='region-province-detail'),
    
    # List regencies (filter by ?province=31)
    path('regencies/', views.RegencyListView.as_view(), name='region-regencies'),
    
    # Regency detail with districts
    path('regencies/<str:code>/', views.RegencyDetailView.as_view(), name='region-regency-detail'),
    
    # List districts (filter by ?regency=3171)
    path('districts/', views.DistrictListView.as_view(), name='region-districts'),
    
    # District detail with villages
    path('districts/<str:code>/', views.DistrictDetailView.as_view(), name='region-district-detail'),
    
    # List villages (filter by ?district=317101)
    path('villages/', views.VillageListView.as_view(), name='region-villages'),
    
    # Search across all levels (?q=jakarta&type=regency&limit=10)
    path('search/', views.RegionSearchView.as_view(), name='region-search'),
    
    # Get full address path from village or district code
    path('path/', views.RegionPathView.as_view(), name='region-path'),
]
