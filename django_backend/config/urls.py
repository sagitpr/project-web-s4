"""
Main URL Configuration for Warungio Marketplace API.
Connects all Django apps under /api/ prefix.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView, TokenBlacklistView
)
from drf_spectacular.views import (
    SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
)
from accounts import views as accounts_views


@require_GET
def health_check(request):
    """
    Liveness check for Cloud Run startup probe.
    Reports DB connectivity when DATABASE_IS_REQUIRED=True.
    """
    from django.db import connections

    result = {"status": "ok", "service": "warungio"}

    if getattr(settings, 'DATABASE_IS_REQUIRED', False):
        db_conn = connections['default']
        try:
            c = db_conn.cursor()
            c.close()
            result['database'] = 'connected'
        except Exception as e:
            result['status'] = 'degraded'
            result['database'] = f'unavailable: {e}'
            return JsonResponse(result, status=503)

    return JsonResponse(result)


api_prefix = 'api/'

urlpatterns = [
    # Home / Landing (root)
    path('', accounts_views.RootView.as_view(), name='home'),

    # Health check (Cloud Run startup probe)
    path('health/', health_check, name='health-check'),

    # Admin
    path('admin/', admin.site.urls),

    # API Root
    path(f'{api_prefix}auth/', include('accounts.urls')),
    path(f'{api_prefix}stores/', include('stores.urls')),
    path(f'{api_prefix}products/', include('products.urls')),
    path(f'{api_prefix}orders/', include('orders.urls')),
    path(f'{api_prefix}payments/', include('payments.urls')),
    path(f'{api_prefix}analytics/', include('analytics.urls')),
    path(f'{api_prefix}chat/', include('chat.urls')),
    path(f'{api_prefix}notifications/', include('notifications.urls')),
    path(f'{api_prefix}refunds/', include('refunds.urls')),
    path(f'{api_prefix}support/', include('support.urls')),

    # JWT Endpoints
    path(f'{api_prefix}token/', TokenObtainPairView.as_view(), name='token-obtain-pair'),
    path(f'{api_prefix}token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path(f'{api_prefix}token/blacklist/', TokenBlacklistView.as_view(), name='token-blacklist'),

    # OpenAPI / Swagger / ReDoc
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# ── Frontend Page Routes ──
# All routes include name= for {% url %} tag usage in Django templates
# Note: frontend route names use 'page-' prefix to avoid conflict with API route names
urlpatterns += [
    # Auth pages
    path('auth/login/', TemplateView.as_view(template_name='auth/login/index.html'), name='page-login'),
    path('auth/register/', TemplateView.as_view(template_name='auth/register/index.html'), name='page-register'),
    path('auth/otp/', TemplateView.as_view(template_name='auth/otp/index.html'), name='page-otp'),
    path('auth/reset-password/', TemplateView.as_view(template_name='auth/reset-password/index.html'), name='page-reset-password'),
    path('auth/register-mitra/', TemplateView.as_view(template_name='auth/register-mitra/index.html'), name='page-register-mitra'),
    # Buyer pages
    path('buyer/home/', login_required(TemplateView.as_view(template_name='home/index.html')), name='page-buyer-home'),
    path('buyer/dashboard/', login_required(TemplateView.as_view(template_name='buyer/dashboard/index.html')), name='page-buyer-dashboard'),
    path('buyer/orders/', login_required(TemplateView.as_view(template_name='buyer/orders/index.html')), name='page-buyer-orders'),
    path('buyer/cart/', login_required(TemplateView.as_view(template_name='buyer/cart/index.html')), name='page-buyer-cart'),
    path('buyer/checkout/', login_required(TemplateView.as_view(template_name='buyer/checkout/index.html')), name='page-buyer-checkout'),
    path('buyer/order-detail/', login_required(TemplateView.as_view(template_name='buyer/order-detail/index.html')), name='page-buyer-order-detail'),
    path('buyer/order-success/', login_required(TemplateView.as_view(template_name='buyer/order-success/index.html')), name='page-buyer-order-success'),
    path('buyer/profile/', login_required(TemplateView.as_view(template_name='buyer/profile/index.html')), name='page-buyer-profile'),
    path('products/<int:pk>/', login_required(TemplateView.as_view(template_name='buyer/product-detail/index.html')), name='page-product-detail'),
    # Seller pages (all protected with login_required)
    path('seller/dashboard/', login_required(TemplateView.as_view(template_name='seller/dashboard/index.html')), name='page-seller-dashboard'),
    path('seller/products/', login_required(TemplateView.as_view(template_name='seller/products/index.html')), name='page-seller-products'),
    path('seller/orders/', login_required(TemplateView.as_view(template_name='seller/orders/index.html')), name='page-seller-orders'),
    path('seller/order-detail/', login_required(TemplateView.as_view(template_name='seller/order-detail/index.html')), name='page-seller-order-detail'),
    path('seller/partner-guide/', login_required(TemplateView.as_view(template_name='seller/partner-guide/index.html')), name='page-seller-partner-guide'),
    path('seller/laporan/', login_required(TemplateView.as_view(template_name='seller/laporan/index.html')), name='page-seller-laporan'),
    path('seller/keuangan/', login_required(TemplateView.as_view(template_name='seller/keuangan/index.html')), name='page-seller-keuangan'),
    path('seller/pelanggan/', login_required(TemplateView.as_view(template_name='seller/pelanggan/index.html')), name='page-seller-pelanggan'),
    path('seller/pengaturan/', login_required(TemplateView.as_view(template_name='seller/pengaturan/index.html')), name='page-seller-pengaturan'),
    path('seller/promo-diskon/', login_required(TemplateView.as_view(template_name='seller/promo-diskon/index.html')), name='page-seller-promo-diskon'),
    path('seller/ulasan/', login_required(TemplateView.as_view(template_name='seller/ulasan/index.html')), name='page-seller-ulasan'),
    # Home / Landing
    path('home/', TemplateView.as_view(template_name='home/index.html'), name='page-landing'),
    path('products/', TemplateView.as_view(template_name='home/index.html'), name='page-products'),
    path('orders/', login_required(TemplateView.as_view(template_name='home/index.html')), name='page-orders'),
    path('promo/', TemplateView.as_view(template_name='home/index.html'), name='page-promo'),
    path('favorites/', login_required(TemplateView.as_view(template_name='home/index.html')), name='page-favorites'),
    path('wallet/', login_required(TemplateView.as_view(template_name='home/index.html')), name='page-wallet'),
    path('settings/', login_required(TemplateView.as_view(template_name='home/index.html')), name='page-settings'),
    path('buyer/chat/', login_required(TemplateView.as_view(template_name='buyer/chat/index.html')), name='page-buyer-chat'),
    # Buyer Refund pages
    path('buyer/refunds/', login_required(TemplateView.as_view(template_name='buyer/refunds/index.html')), name='page-buyer-refunds'),
    path('buyer/refunds/create/', login_required(TemplateView.as_view(template_name='buyer/refunds/create.html')), name='page-buyer-refund-create'),
    path('buyer/refunds/<int:pk>/', login_required(TemplateView.as_view(template_name='buyer/refunds/detail.html')), name='page-buyer-refund-detail'),
    # Seller Refund pages
    path('seller/refunds/', login_required(TemplateView.as_view(template_name='seller/refunds/index.html')), name='page-seller-refunds'),
    path('seller/refunds/<int:pk>/', login_required(TemplateView.as_view(template_name='seller/refunds/detail.html')), name='page-seller-refund-detail'),
]

# ── Admin Panel Pages (staff-only) ──
staff = staff_member_required(login_url='/auth/login/')

urlpatterns += [
    path('admin-panel/', staff(TemplateView.as_view(template_name='admin/dashboard/index.html')), name='admin-dashboard'),
    path('admin-panel/users/', staff(TemplateView.as_view(template_name='admin/users/index.html')), name='admin-users'),
    path('admin-panel/marketplace/', staff(TemplateView.as_view(template_name='admin/marketplace/index.html')), name='admin-marketplace'),
    path('admin-panel/orders/', staff(TemplateView.as_view(template_name='admin/orders/index.html')), name='admin-orders'),
    path('admin-panel/payments/', staff(TemplateView.as_view(template_name='admin/payments/index.html')), name='admin-payments'),
    path('admin-panel/notifications/', staff(TemplateView.as_view(template_name='admin/notifications/index.html')), name='admin-notifications'),
    path('admin-panel/ai/', staff(TemplateView.as_view(template_name='admin/ai/index.html')), name='admin-ai'),
    path('admin-panel/analytics/', staff(TemplateView.as_view(template_name='admin/analytics/index.html')), name='admin-analytics'),
    path('admin-panel/reports/', staff(TemplateView.as_view(template_name='admin/reports/index.html')), name='admin-reports'),
    path('admin-panel/security/', staff(TemplateView.as_view(template_name='admin/security/index.html')), name='admin-security'),
    path('admin-panel/audit/', staff(TemplateView.as_view(template_name='admin/audit/index.html')), name='admin-audit'),
    path('admin-panel/settings/', staff(TemplateView.as_view(template_name='admin/settings/index.html')), name='admin-settings'),
    path('admin-panel/refunds/', staff(TemplateView.as_view(template_name='admin/refunds/index.html')), name='admin-refunds'),
    path('admin-panel/refunds/<int:pk>/', staff(TemplateView.as_view(template_name='admin/refunds/detail.html')), name='admin-refund-detail'),
]


# Bantuan / Help Center (via support app page_urls)
urlpatterns += [path('bantuan/', include('support.page_urls'))]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Serve /assets/ directory (favicon, images, etc.)
    urlpatterns += static('/assets/', document_root=settings.BASE_DIR / 'assets')
    # Serve page-specific CSS/JS for standalone HTML pages
    urlpatterns += static('/auth/', document_root=settings.BASE_DIR)
    urlpatterns += static('/buyer/', document_root=settings.BASE_DIR)
    urlpatterns += static('/seller/', document_root=settings.BASE_DIR)
    urlpatterns += [path('api-auth/', include('rest_framework.urls'))]
