"""
AI Smart Inventory Scanning URL routes.
All endpoints under /api/inventory/ai-scan/ prefix.
Flutter-ready real-time scanning API.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Session Management
    path('start/', views.StartScanSessionView.as_view(), name='ai-scan-start'),
    path('sessions/', views.SessionListView.as_view(), name='ai-scan-sessions'),
    path('active/', views.ActiveSessionView.as_view(), name='ai-scan-active'),
    path('<int:session_id>/', views.SessionDetailView.as_view(), name='ai-scan-detail'),
    path('<int:session_id>/cancel/', views.CancelSessionView.as_view(), name='ai-scan-cancel'),

    # Real-time Frame Processing
    path('<int:session_id>/frame/', views.SubmitFrameView.as_view(), name='ai-scan-frame'),

    # Bulk Barcode Scan
    path('<int:session_id>/bulk/', views.BulkBarcodeScanView.as_view(), name='ai-scan-bulk'),

    # Review & Confirmation
    path('<int:session_id>/review/', views.SessionAggregatedView.as_view(), name='ai-scan-review'),
    path('<int:session_id>/items/', views.DetectedItemListView.as_view(), name='ai-scan-items'),
    path('<int:session_id>/items/<int:item_id>/', views.UpdateDetectedItemView.as_view(), name='ai-scan-item-update'),
    path('<int:session_id>/confirm/', views.ConfirmAndSaveView.as_view(), name='ai-scan-confirm'),
    path('<int:session_id>/reject-all/', views.RejectAllPendingView.as_view(), name='ai-scan-reject'),

    # Master Product Registration
    path('<int:session_id>/register-product/', views.RegisterNewProductFromScanView.as_view(), name='ai-scan-register'),

    # Dashboard Summary
    path('summary/', views.ScanSummaryView.as_view(), name='ai-scan-summary'),
]
