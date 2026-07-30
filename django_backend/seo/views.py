"""
SEO views for Warungio Marketplace.
Provides robots.txt and sitemap.xml endpoints.
"""

from django.http import HttpResponse
from django.urls import reverse
from django.conf import settings
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET
from django.template.loader import render_to_string
from django.utils.text import slugify


SITE_URL = "https://warungio.web.id"


@require_GET
@cache_page(86400)  # Cache for 24 hours
def robots_txt(request):
    """
    Generate robots.txt.
    - Allows all major crawlers
    - Blocks sensitive/admin directories
    - Points to sitemap.xml
    """
    lines = [
        "# Warungio - robots.txt",
        "# Last updated: 2026-07-22",
        "",
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /admin-panel/",
        "Disallow: /api/",
        "Disallow: /auth/",
        "Disallow: /buyer/",
        "Disallow: /seller/",
        "Disallow: /static/",
        "Disallow: /media/",
        "Disallow: /accounts/",
        "Disallow: /social-callback/",
        "Disallow: /*?next=",
        "Disallow: /*?page=",
        "Disallow: /*/edit/",
        "Disallow: /*/delete/",
        "Disallow: /assets/pwa/",
        "",
        "Crawl-delay: 10",
        "",
        "Allow: /$",
        "Allow: /info/",
        "Allow: /bantuan/",
        "Allow: /download/",
        "Allow: /health/",
        "Allow: /kategori/",
        "Allow: /kota/",
        "Allow: /toko/",
        "Allow: /produk/",
        "Allow: /promo/",
        "Allow: /store/",
        "Allow: /order/",
        "",
        "User-agent: Googlebot",
        "Allow: /",
        "Allow: /*?page=",
        "Disallow: /admin/",
        "Disallow: /admin-panel/",
        "Disallow: /api/",
        "",
        "User-agent: Googlebot-Image",
        "Allow: /static/images/",
        "Allow: /media/",
        "",
        "User-agent: Bingbot",
        "Allow: /*?page=",
        "Disallow: /admin/",
        "Disallow: /admin-panel/",
        "Disallow: /api/",
        "",
        f"Sitemap: {SITE_URL}/sitemap.xml",
        "",
        "# Warungio - Ekosistem Marketplace & Manajemen Bisnis UMKM Indonesia",
        "# Marketplace hyperlocal terpercaya + aplikasi stok barang gratis, POS kasir digital,",
        "# manajemen inventaris, laporan keuangan, dan analisis bisnis berbasis AI",
        "# Total pages indexed: 800+",
    ]

    return HttpResponse(
        "\n".join(lines),
        content_type="text/plain; charset=utf-8",
        headers={
            "X-Robots-Tag": "all",
            "Cache-Control": "public, max-age=86400",
        },
    )


@require_GET
@cache_page(3600)  # Cache for 1 hour
def sitemap_xml(request):
    """
    Generate comprehensive sitemap.xml with all public pages.
    Includes image sitemap for media-rich pages.
    """
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d")

    pages = [
        # ── Landing / Core Pages ──
        {"loc": "/", "priority": "1.0", "changefreq": "daily", "lastmod": now},
        {"loc": "/info/tentang-kami/", "priority": "0.9", "changefreq": "monthly", "lastmod": now},
        {"loc": "/info/cara-belanja/", "priority": "0.8", "changefreq": "monthly", "lastmod": now},
        {"loc": "/info/metode-pembayaran/", "priority": "0.8", "changefreq": "monthly", "lastmod": now},
        {"loc": "/info/kontak-kami/", "priority": "0.7", "changefreq": "monthly", "lastmod": now},
        {"loc": "/info/kebijakan/", "priority": "0.7", "changefreq": "monthly", "lastmod": now},
        {"loc": "/info/blog/", "priority": "0.8", "changefreq": "weekly", "lastmod": now},
        {"loc": "/info/panduan-seller/", "priority": "0.8", "changefreq": "monthly", "lastmod": now},
        {"loc": "/info/komunitas/", "priority": "0.7", "changefreq": "monthly", "lastmod": now},
        {"loc": "/info/tips-sukses/", "priority": "0.8", "changefreq": "monthly", "lastmod": now},
        {"loc": "/info/bantuan/", "priority": "0.7", "changefreq": "monthly", "lastmod": now},
        {"loc": "/bantuan/", "priority": "0.8", "changefreq": "weekly", "lastmod": now},
        {"loc": "/download/", "priority": "0.9", "changefreq": "monthly", "lastmod": now},
    ]

    # ── Category & City index pages ──
    pages.append({"loc": "/kategori/", "priority": "0.8", "changefreq": "daily", "lastmod": now})
    pages.append({"loc": "/kota/", "priority": "0.8", "changefreq": "daily", "lastmod": now})

    # ── Dynamically add categories from database ──
    try:
        from products.models import Category
        categories = Category.objects.filter(is_active=True)
        for cat in categories:
            slug = slugify(cat.category_name)
            pages.append({
                "loc": f"/kategori/{slug}/",
                "priority": "0.8",
                "changefreq": "daily",
                "lastmod": now,
            })
    except Exception:
        pass  # Graceful fallback if categories table doesn't exist yet

    # ── Dynamically add help articles from database ──
    try:
        from support.models import HelpArticle
        articles = HelpArticle.objects.filter(is_published=True)
        for article in articles:
            pages.append({
                "loc": f"/bantuan/artikel/{article.slug}/",
                "priority": "0.6",
                "changefreq": "weekly",
                "lastmod": article.updated_at.strftime("%Y-%m-%d") if article.updated_at else now,
            })
    except Exception:
        pass

    # ── Dynamically add active stores (up to 1000) ──
    try:
        from stores.models import Store
        stores = Store.objects.filter(status='active').order_by('-total_sales')[:1000]
        for store in stores:
            pages.append({
                "loc": f"/toko/{store.slug}/",
                "priority": "0.8",
                "changefreq": "daily",
                "lastmod": store.updated_at.strftime("%Y-%m-%d") if store.updated_at else now,
            })
    except Exception:
        pass

    # ── Dynamically add cities with active stores (up to 200) ──
    try:
        from stores.models import Store
        cities = Store.objects.filter(status='active').exclude(city__isnull=True).exclude(city__exact='').values_list('city', flat=True).distinct()[:200]
        for city in cities:
            if city:
                city_slug = slugify(city)
                pages.append({
                    "loc": f"/kota/{city_slug}/",
                    "priority": "0.7",
                    "changefreq": "weekly",
                    "lastmod": now,
                })
    except Exception:
        pass

    # ── Dynamically add districts with active stores ──
    try:
        from stores.models import Store
        districts = Store.objects.filter(status='active').exclude(district__isnull=True).exclude(district__exact='').values_list('district', flat=True).distinct()[:500]
        for dist in districts:
            if dist:
                dist_slug = slugify(dist)
                pages.append({
                    "loc": f"/kota/{dist_slug}/",
                    "priority": "0.6",
                    "changefreq": "weekly",
                    "lastmod": now,
                })
    except Exception:
        pass

    # ── Dynamically add provinces with active stores ──
    try:
        from stores.models import Store
        provinces = Store.objects.filter(status='active').exclude(province__isnull=True).exclude(province__exact='').values_list('province', flat=True).distinct()[:34]
        for prov in provinces:
            if prov:
                prov_slug = slugify(prov)
                pages.append({
                    "loc": f"/kota/{prov_slug}/",
                    "priority": "0.6",
                    "changefreq": "monthly",
                    "lastmod": now,
                })
    except Exception:
        pass

    # ── Dynamically add active products (top 2000) ──
    try:
        from products.models import Product
        products = Product.objects.filter(is_active=True).order_by('-sold_count').select_related('store')[:2000]
        for product in products:
            if product.slug:
                pages.append({
                    "loc": f"/produk/{product.slug}/",
                    "priority": "0.7",
                    "changefreq": "weekly",
                    "lastmod": product.updated_at.strftime("%Y-%m-%d") if hasattr(product, 'updated_at') and product.updated_at else now,
                })
    except Exception:
        pass

    # ── Dynamically add store product pages ──
    try:
        from stores.models import Store
        from products.models import Product
        store_list = Store.objects.filter(status='active').order_by('-total_sales')[:200]
        for store in store_list:
            pages.append({
                "loc": f"/toko/{store.slug}/products/",
                "priority": "0.6",
                "changefreq": "daily",
                "lastmod": now,
            })
    except Exception:
        pass

    # ── Dynamically add active promos ──
    try:
        from products.models import Promo
        promos = Promo.objects.filter(is_active=True).order_by('-created_at')[:20]
        from django.utils import timezone
        for promo in promos:
            promo_slug = slugify(promo.promo_name)
            pages.append({
                "loc": f"/promo/{promo_slug}/",
                "priority": "0.5",
                "changefreq": "daily" if promo.start_date <= timezone.now().date() <= promo.end_date else "weekly",
                "lastmod": now,
            })
    except Exception:
        pass

    # Build XML
    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"',
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]

    # ── Static images for image sitemap ──
    static_images = [
        "/static/images/Warungio L.png",
        "/static/images/Tentang-kami.png",
        "/static/images/paket-sayur.png",
        "/static/images/sembako.png",
        "/static/images/vegetable.png",
        "/static/images/fruit.png",
    ]

    for page in pages:
        xml_parts.append("  <url>")
        xml_parts.append(f"    <loc>{SITE_URL}{page['loc']}</loc>")
        xml_parts.append(f"    <lastmod>{page['lastmod']}</lastmod>")
        xml_parts.append(f"    <changefreq>{page['changefreq']}</changefreq>")
        xml_parts.append(f"    <priority>{page['priority']}</priority>")

        # Add xhtml:link for hreflang
        xml_parts.append(
            '    <xhtml:link rel="alternate" hreflang="id" '
            f'href="{SITE_URL}{page["loc"]}"/>'
        )

        # Add image references for key pages
        if page["loc"] in ("/", "/info/tentang-kami/", "/download/"):
            for img in static_images:
                xml_parts.append(f"    <image:image><image:loc>{SITE_URL}{img}</image:loc></image:image>")

        xml_parts.append("  </url>")

    xml_parts.append("</urlset>")

    return HttpResponse(
        "\n".join(xml_parts),
        content_type="application/xml; charset=utf-8",
        headers={
            "X-Robots-Tag": "all",
            "Cache-Control": "public, max-age=3600",
        },
    )
