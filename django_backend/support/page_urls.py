"""
HTML page URL configuration for Bantuan & Chat pages.
"""

from django.urls import path
from . import page_views

urlpatterns = [
    path('', page_views.bantuan_page, name='bantuan-page'),
    path('artikel/<slug:slug>/', page_views.bantuan_article, name='bantuan-article'),
]
