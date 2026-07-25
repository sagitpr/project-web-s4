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
    
    # Customer Support Center — Dashboard
    path('dashboard/', views.SupportDashboardView.as_view(), name='support-dashboard'),
    
    # Customer Support Center — Ticket Management
    path('tickets/<int:pk>/assign/', views.SupportTicketAssignView.as_view(), name='support-ticket-assign'),
    path('tickets/<int:pk>/resolve/', views.SupportTicketResolveView.as_view(), name='support-ticket-resolve'),
    
    # Customer Support Center — Complaints
    path('complaints/', views.ComplaintListView.as_view(), name='support-complaint-list'),
    path('complaints/<int:pk>/', views.ComplaintDetailView.as_view(), name='support-complaint-detail'),
    
    # Customer Support Center — Reports
    path('reports/products/', views.ReportProductListView.as_view(), name='support-report-product'),
    path('reports/products/<int:pk>/moderate/', views.ReportProductModerateView.as_view(), name='support-report-product-moderate'),
    path('reports/sellers/', views.ReportSellerListView.as_view(), name='support-report-seller'),
    path('reports/buyers/', views.ReportBuyerListView.as_view(), name='support-report-buyer'),
    
    # Customer Support Center — Disputes
    path('disputes/', views.DisputeListView.as_view(), name='support-dispute-list'),
    path('disputes/<int:pk>/', views.DisputeDetailView.as_view(), name='support-dispute-detail'),
    path('disputes/<int:pk>/resolve/', views.DisputeResolveView.as_view(), name='support-dispute-resolve'),
    
    # Customer Support Center — Internal Notes
    path('notes/', views.InternalNoteListView.as_view(), name='support-internal-notes'),
]
