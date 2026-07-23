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
from django.views.generic import TemplateView, RedirectView
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView, TokenBlacklistView
)
from drf_spectacular.views import (
    SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
)
from accounts import views as accounts_views
from accounts.decorators import buyer_required, seller_required, admin_required
from seo import page_views as seo_views


@require_GET
def health_check(request):
    """
    Liveness check untuk Docker HEALTHCHECK & Cloud Run startup probe.
    SELALU return HTTP 200 agar container tidak jadi unhealthy.
    """
    result = {"status": "ok", "service": "warungio"}

    # Report DB status di body (bukan HTTP status) — liveness probe harus
    # selalu 200 agar container tidak restart akibat DB blip sesaat.
    if getattr(settings, 'DATABASE_IS_REQUIRED', False):
        from django.db import connections
        try:
            c = connections['default'].cursor()
            c.close()
            result['database'] = 'connected'
        except Exception as e:
            result['database'] = f'unavailable: {e}'
            result['status'] = 'degraded'
            # Tetap return 200 — jangan pernah set status 503 di liveness probe.
            # Docker HEALTHCHECK akan mark container unhealthy jika HTTP != 200.

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
    # NEW API (v2.0.0)
    path(f'{api_prefix}suppliers/', include('suppliers.urls')),
    path(f'{api_prefix}loyalty/', include('loyalty.urls')),
    path(f'{api_prefix}monitoring/', include('monitoring.urls')),
    path(f'{api_prefix}regions/', include('regions.urls')),
    path(f'{api_prefix}inventory/', include('inventory.urls')),

    # AI Services
    path(f'{api_prefix}ai/', include('ai_services.urls')),

    # Engagement & Retention Engine
    path(f'{api_prefix}engagement/', include('engagement.urls')),

    # AI Intelligence Platform
    path(f'{api_prefix}intelligence/', include('ai_intelligence.urls')),

    # Download App (direct APK/IPA serving)
    path('download/', include('core.download_urls')),

    # SEO (robots.txt, sitemap.xml)
    path('', include('seo.urls')),

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
    path('auth/login-seller/', TemplateView.as_view(template_name='auth/login/index.html', extra_context={'entry': 'seller'}), name='page-login-seller'),
    path('auth/register/', TemplateView.as_view(template_name='auth/register/index.html'), name='page-register'),
    path('auth/otp/', TemplateView.as_view(template_name='auth/otp/index.html'), name='page-otp'),
    path('auth/reset-password/', TemplateView.as_view(template_name='auth/reset-password/index.html'), name='page-reset-password'),
    path('auth/register-mitra/', TemplateView.as_view(template_name='auth/register-mitra/index.html'), name='page-register-mitra'),
    path('social-callback/apple.html', TemplateView.as_view(template_name='auth/social-callback/apple.html'), name='page-apple-callback'),
    # Buyer pages (protected with buyer_required decorator + login_required fallback)
    path('buyer/home/', login_required(buyer_required(TemplateView.as_view(template_name='home/index.html'))), name='page-buyer-home'),
    path('buyer/products/', login_required(buyer_required(TemplateView.as_view(template_name='buyer/products/index.html'))), name='page-buyer-products'),
    path('buyer/favorites/', login_required(buyer_required(TemplateView.as_view(template_name='buyer/favorites/index.html'))), name='page-buyer-favorites'),
    path('buyer/promo/', login_required(buyer_required(TemplateView.as_view(template_name='buyer/promo/index.html'))), name='page-buyer-promo'),
    path('buyer/settings/', login_required(buyer_required(TemplateView.as_view(template_name='buyer/settings/index.html'))), name='page-buyer-settings'),
    path('buyer/loyalty/', login_required(buyer_required(TemplateView.as_view(template_name='buyer/loyalty/index.html'))), name='page-buyer-loyalty'),
    path('buyer/wallet/', login_required(buyer_required(TemplateView.as_view(template_name='buyer/wallet/index.html'))), name='page-buyer-wallet'),
    path('buyer/reviews/', login_required(buyer_required(TemplateView.as_view(template_name='buyer/reviews/index.html'))), name='page-buyer-reviews'),
    path('buyer/dashboard/', login_required(buyer_required(TemplateView.as_view(template_name='buyer/dashboard/index.html'))), name='page-buyer-dashboard'),
    path('buyer/orders/', login_required(buyer_required(TemplateView.as_view(template_name='buyer/orders/index.html'))), name='page-buyer-orders'),
    path('buyer/cart/', login_required(buyer_required(TemplateView.as_view(template_name='buyer/cart/index.html'))), name='page-buyer-cart'),
    path('buyer/checkout/', login_required(buyer_required(TemplateView.as_view(template_name='buyer/checkout/index.html'))), name='page-buyer-checkout'),
    path('buyer/order-detail/', login_required(buyer_required(TemplateView.as_view(template_name='buyer/order-detail/index.html'))), name='page-buyer-order-detail'),
    path('buyer/order-success/', login_required(buyer_required(TemplateView.as_view(template_name='buyer/order-success/index.html'))), name='page-buyer-order-success'),
    path('buyer/profile/', login_required(buyer_required(TemplateView.as_view(template_name='buyer/profile/index.html'))), name='page-buyer-profile'),
    path('products/<int:pk>/', login_required(buyer_required(TemplateView.as_view(template_name='buyer/product-detail/index.html'))), name='page-product-detail'),
    # Seller pages (protected with seller_required decorator + login_required fallback)
    path('seller/dashboard/', login_required(seller_required(TemplateView.as_view(template_name='seller/dashboard/index.html'))), name='page-seller-dashboard'),
    path('seller/pengiriman/', login_required(seller_required(TemplateView.as_view(template_name='seller/pengiriman/index.html'))), name='page-seller-pengiriman'),
    path('seller/products/', login_required(seller_required(TemplateView.as_view(template_name='seller/products/index.html'))), name='page-seller-products'),
    path('seller/orders/', login_required(seller_required(TemplateView.as_view(template_name='seller/orders/index.html'))), name='page-seller-orders'),
    path('seller/order-detail/', login_required(seller_required(TemplateView.as_view(template_name='seller/order-detail/index.html'))), name='page-seller-order-detail'),
    path('seller/partner-guide/', login_required(seller_required(TemplateView.as_view(template_name='seller/partner-guide/index.html'))), name='page-seller-partner-guide'),
    path('seller/laporan/', login_required(seller_required(TemplateView.as_view(template_name='seller/laporan/index.html'))), name='page-seller-laporan'),
    path('seller/keuangan/', login_required(seller_required(TemplateView.as_view(template_name='seller/keuangan/index.html'))), name='page-seller-keuangan'),
    path('seller/pelanggan/', login_required(seller_required(TemplateView.as_view(template_name='seller/pelanggan/index.html'))), name='page-seller-pelanggan'),
    path('seller/pengaturan/', login_required(seller_required(TemplateView.as_view(template_name='seller/pengaturan/index.html'))), name='page-seller-pengaturan'),
    path('seller/promo-diskon/', login_required(seller_required(TemplateView.as_view(template_name='seller/promo-diskon/index.html'))), name='page-seller-promo-diskon'),
    path('seller/ulasan/', login_required(seller_required(TemplateView.as_view(template_name='seller/ulasan/index.html'))), name='page-seller-ulasan'),
    path('seller/supplier/', login_required(seller_required(TemplateView.as_view(template_name='seller/supplier/index.html'))), name='page-seller-supplier'),
    path('seller/stock-prediction/', login_required(seller_required(TemplateView.as_view(template_name='seller/stock-prediction/index.html'))), name='page-seller-stock-prediction'),
    # ── DUPLICATE SHORTHAND ROUTES → CANONICAL PERMANENT REDIRECTS ──
    # These shorthand paths (without /buyer/ prefix) duplicate the canonical /buyer/* routes.
    # Keeping them as direct routes creates multiple entry points and inconsistent redirects.
    # Converting to permanent (301) redirects preserves existing bookmarks while funneling
    # all traffic through canonical paths.
    #
    # The template engine {% url 'page-products' %} will still generate '/products/',
    # which then 301-redirects to '/buyer/products/'. This is transparent to the user.
    path('home/', RedirectView.as_view(url='/buyer/home/', permanent=True), name='page-landing'),
    path('products/', RedirectView.as_view(url='/buyer/products/', permanent=True), name='page-products'),
    path('orders/', RedirectView.as_view(url='/buyer/orders/', permanent=True), name='page-orders'),
    path('promo/', RedirectView.as_view(url='/buyer/promo/', permanent=True), name='page-promo'),
    path('favorites/', RedirectView.as_view(url='/buyer/favorites/', permanent=True), name='page-favorites'),
    path('wallet/', RedirectView.as_view(url='/buyer/wallet/', permanent=True), name='page-wallet'),
    path('settings/', RedirectView.as_view(url='/buyer/settings/', permanent=True), name='page-settings'),
    path('buyer/chat/', login_required(buyer_required(TemplateView.as_view(template_name='buyer/chat/index.html'))), name='page-buyer-chat'),
    # Buyer Refund pages
    path('buyer/refunds/', login_required(TemplateView.as_view(template_name='buyer/refunds/index.html')), name='page-buyer-refunds'),
    path('buyer/refunds/create/', login_required(TemplateView.as_view(template_name='buyer/refunds/create.html')), name='page-buyer-refund-create'),
    path('buyer/refunds/<int:pk>/', login_required(TemplateView.as_view(template_name='buyer/refunds/detail.html')), name='page-buyer-refund-detail'),
    # Seller Refund pages
    path('seller/refunds/', login_required(TemplateView.as_view(template_name='seller/refunds/index.html')), name='page-seller-refunds'),
    path('seller/refunds/<int:pk>/', login_required(TemplateView.as_view(template_name='seller/refunds/detail.html')), name='page-seller-refund-detail'),
]

# ── Admin Panel Pages (staff-only, with dedicated admin login) ──
# Unauthenticated users are redirected to the dedicated admin login page.
# Admins never see the public landing page.
staff = staff_member_required(login_url='/admin-panel/login/')

urlpatterns += [
    # Dedicated admin login page (separated from public /auth/login/)
    path('admin-panel/login/', TemplateView.as_view(template_name='admin/login/index.html'), name='admin-login-page'),
    path('admin-panel/', staff(TemplateView.as_view(template_name='admin/dashboard/index.html')), name='admin-dashboard'),
    path('admin-panel/users/', staff(TemplateView.as_view(template_name='admin/users/index.html')), name='admin-users'),
    path('admin-panel/marketplace/', staff(TemplateView.as_view(template_name='admin/marketplace/index.html')), name='admin-marketplace'),
    path('admin-panel/orders/', staff(TemplateView.as_view(template_name='admin/orders/index.html')), name='admin-orders'),
    path('admin-panel/payments/', staff(TemplateView.as_view(template_name='admin/payments/index.html')), name='admin-payments'),
    path('admin-panel/notifications/', staff(TemplateView.as_view(template_name='admin/notifications/index.html')), name='admin-notifications'),
    path('admin-panel/suppliers/', staff(TemplateView.as_view(template_name='admin/suppliers/index.html')), name='admin-suppliers'),
    path('admin-panel/loyalty/', staff(TemplateView.as_view(template_name='admin/loyalty/index.html')), name='admin-loyalty'),
    path('admin-panel/monitoring/', staff(TemplateView.as_view(template_name='admin/monitoring/index.html')), name='admin-monitoring'),
    path('admin-panel/ai/', staff(TemplateView.as_view(template_name='admin/ai/index.html')), name='admin-ai'),
    path('admin-panel/analytics/', staff(TemplateView.as_view(template_name='admin/analytics/index.html')), name='admin-analytics'),
    path('admin-panel/reports/', staff(TemplateView.as_view(template_name='admin/reports/index.html')), name='admin-reports'),
    path('admin-panel/security/', staff(TemplateView.as_view(template_name='admin/security/index.html')), name='admin-security'),
    path('admin-panel/audit/', staff(TemplateView.as_view(template_name='admin/audit/index.html')), name='admin-audit'),
    path('admin-panel/engagement/', staff(TemplateView.as_view(template_name='admin/engagement/index.html')), name='admin-engagement'),
    path('admin-panel/settings/', staff(TemplateView.as_view(template_name='admin/settings/index.html')), name='admin-settings'),
    path('admin-panel/refunds/', staff(TemplateView.as_view(template_name='admin/refunds/index.html')), name='admin-refunds'),
    path('admin-panel/refunds/<int:pk>/', staff(TemplateView.as_view(template_name='admin/refunds/detail.html')), name='admin-refund-detail'),
]


# Info Pages (public)
urlpatterns += [
    path('info/tentang-kami/', TemplateView.as_view(template_name='pages/tentang-kami/index.html'), name='page-tentang-kami'),
    path('info/cara-belanja/', TemplateView.as_view(template_name='pages/cara-belanja/index.html'), name='page-cara-belanja'),
    path('info/metode-pembayaran/', TemplateView.as_view(template_name='pages/metode-pembayaran/index.html'), name='page-metode-pembayaran'),
    path('info/kontak-kami/', TemplateView.as_view(template_name='pages/kontak-kami/index.html'), name='page-kontak-kami'),
    path('info/kebijakan/', TemplateView.as_view(template_name='pages/kebijakan/index.html'), name='page-kebijakan'),
    path('info/blog/', TemplateView.as_view(template_name='pages/blog/index.html'), name='page-blog'),
    path('info/panduan-seller/', TemplateView.as_view(template_name='pages/panduan-seller/index.html'), name='page-panduan-seller'),
    path('info/komunitas/', TemplateView.as_view(template_name='pages/komunitas/index.html'), name='page-komunitas'),
    path('info/tips-sukses/', TemplateView.as_view(template_name='pages/tips-sukses/index.html'), name='page-tips-sukses'),
]

# Bantuan / Help Center (via support app page_urls)
urlpatterns += [path('bantuan/', include('support.page_urls'))]

# Alias: page-bantuan → redirect to the actual bantuan page
urlpatterns += [
    path('info/bantuan/', RedirectView.as_view(url='/bantuan/', permanent=True), name='page-bantuan'),
]

# ── SEO Landing Pages (indexable, public) ──
urlpatterns += [
    path('kategori/', seo_views.category_index, name='seo-category-index'),
    path('kategori/<slug:slug>/', seo_views.category_landing, name='seo-category'),
    path('kota/', seo_views.city_index, name='seo-city-index'),
    path('kota/<slug:slug>/', seo_views.city_landing, name='seo-city'),
    path('toko/<slug:slug>/', seo_views.store_landing, name='seo-store'),
    path('produk/<slug:slug>/', seo_views.product_detail, name='seo-product'),
    path('promo/<slug:slug>/', seo_views.promo_landing, name='seo-promo'),
]

# Extra routes for feature pages
urlpatterns += [
    path('buyer/followed-stores/', login_required(TemplateView.as_view(template_name='buyer/favorites/index.html')), name='page-buyer-followed-stores'),
    path('buyer/recently-viewed/', login_required(TemplateView.as_view(template_name='buyer/products/index.html')), name='page-buyer-recently-viewed'),
    path('seller/stock-alerts/', login_required(TemplateView.as_view(template_name='seller/products/index.html')), name='page-seller-stock-alerts'),
]

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
