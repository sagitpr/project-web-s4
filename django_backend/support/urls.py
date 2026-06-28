"""
Support / Help Center URL configuration for Warungio Marketplace.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'categories', views.HelpCategoryViewSet, basename='help-category')
router.register(r'articles', views.HelpArticleViewSet, basename='help-article')
router.register(r'faqs', views.FAQViewSet, basename='faq')
router.register(r'banners', views.BannerPromoViewSet, basename='banner')
router.register(r'contacts', views.ContactInfoViewSet, basename='contact')
router.register(r'support-info', views.SupportInfoViewSet, basename='support-info')
router.register(r'quick-replies', views.ChatQuickReplyViewSet, basename='quick-reply')

urlpatterns = [
    path('', include(router.urls)),
    path('search/', views.HelpSearchView.as_view(), name='help-search'),
    
    # AI Chat
    path('ai-chat/', views.AIChatView.as_view(), name='ai-chat'),

    # Support Tickets
    path('tickets/', views.SupportTicketUserView.as_view(), name='support-ticket-list'),
    path('tickets/all/', views.SupportTicketAdminView.as_view(), name='support-ticket-admin'),
    path('tickets/<int:pk>/', views.SupportTicketDetailView.as_view(), name='support-ticket-detail'),
]
