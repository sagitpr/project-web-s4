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
        "# Last updated: 2026-07-21",
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
        "Allow: /$",
        "Allow: /info/",
        "Allow: /bantuan/",
        "Allow: /download/",
        "Allow: /health/",
        "",
        "User-agent: Googlebot",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /admin-panel/",
        "Disallow: /api/",
        "",
        "User-agent: Googlebot-Image",
        "Allow: /static/images/",
        "Allow: /media/",
        "",
        "User-agent: Bingbot",
        "Disallow: /admin/",
        "Disallow: /admin-panel/",
        "Disallow: /api/",
        "",
        f"Sitemap: {SITE_URL}/sitemap.xml",
        "",
        "# Warungio - Hyperlocal Marketplace Indonesia",
        "# Last updated: 2026-07-21",
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
        # ── Auth Pages (low priority, noindex) ──
        {"loc": "/auth/login/", "priority": "0.3", "changefreq": "yearly", "lastmod": now},
        {"loc": "/auth/register/", "priority": "0.5", "changefreq": "yearly", "lastmod": now},
        {"loc": "/auth/register-mitra/", "priority": "0.5", "changefreq": "yearly", "lastmod": now},
        # ── Health ──
        {"loc": "/health/", "priority": "0.1", "changefreq": "yearly", "lastmod": now},
    ]

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
