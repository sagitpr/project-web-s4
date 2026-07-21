"""
SEO template tags for Warungio Marketplace.
Provides reusable tags for rendering SEO metadata.

Usage:
    {% load seo_tags %}
    {% seo_meta %}              — Render all meta tags (OG, Twitter, JSON-LD, etc.)
    {% json_ld_block %}         — Render JSON-LD structured data
    {% breadcrumb_json_ld %}    — Render BreadcrumbList schema
    {% canonical_url %}         — Render canonical URL
    {% hreflang_tags %}         — Render hreflang alternate links
    {% meta_robots %}           — Render meta robots tag
"""

import html as html_module
from django import template
from django.utils.safestring import mark_safe
from django.conf import settings
from django.template.defaultfilters import escape as django_escape

register = template.Library()


def _escape_attr(value):
    """Escape a string for use in an HTML attribute."""
    if value is None:
        return ""
    return html_module.escape(str(value)).replace('"', '&quot;').replace("'", "&#39;")


@register.simple_tag(takes_context=True)
def seo_meta(context):
    """Render complete SEO meta tags including OG, Twitter, and JSON-LD."""
    seo = context.get("seo", {})
    if not seo:
        return ""

    site_url = seo.get("site_url", "https://warungio.web.id")
    meta_title = seo.get("meta_title", "")
    meta_description = seo.get("meta_description", "")
    canonical_url = seo.get("canonical_url", "")
    keywords = seo.get("keywords", "")
    robots = seo.get("robots", "index, follow")
    noindex = seo.get("noindex", False)
    og_title = seo.get("og_title", meta_title)
    og_description = seo.get("og_description", meta_description)
    og_image = seo.get("og_image", "")
    og_url = seo.get("og_url", canonical_url)
    og_type = seo.get("og_type", "website")
    og_locale = seo.get("og_locale", "id_ID")
    og_site_name = seo.get("og_site_name", "Warungio")
    twitter_title = seo.get("twitter_title", og_title)
    twitter_description = seo.get("twitter_description", og_description)
    twitter_image = seo.get("twitter_image", og_image)
    twitter_card = seo.get("twitter_card", "summary_large_image")
    twitter_site = seo.get("twitter_site", "@warungio")
    twitter_creator = seo.get("twitter_creator", "@warungio")

    # Theme color
    theme_color = getattr(settings, "SEO_THEME_COLOR", "#059669")

    html = []

    # ── Standard Meta Tags (with proper escaping) ──
    if meta_title:
        html.append(f'<meta name="title" content="{_escape_attr(meta_title)}">')
    if meta_description:
        html.append(f'<meta name="description" content="{_escape_attr(meta_description)}">')
    if keywords:
        html.append(f'<meta name="keywords" content="{_escape_attr(keywords)}">')
    html.append(f'<meta name="robots" content="{_escape_attr(robots)}">')
    html.append(f'<meta name="googlebot" content="{_escape_attr(robots)}">')
    html.append('<meta name="google" content="notranslate">')

    # ── Language & Locale ──
    html.append(f'<meta http-equiv="content-language" content="id">')
    html.append(f'<meta name="language" content="Indonesian">')
    html.append(f'<meta name="geo.country" content="ID">')

    # ── Canonical ──
    if canonical_url:
        html.append(f'<link rel="canonical" href="{canonical_url}">')

    # ── Theme Color ──
    html.append(f'<meta name="theme-color" content="{theme_color}">')
    html.append(f'<meta name="msapplication-TileColor" content="{theme_color}">')
    html.append(f'<meta name="msapplication-navbutton-color" content="{theme_color}">')
    html.append(f'<meta name="apple-mobile-web-app-capable" content="yes">')
    html.append(f'<meta name="apple-mobile-web-app-status-bar-style" content="default">')
    html.append(f'<meta name="apple-mobile-web-app-title" content="Warungio">')
    html.append(f'<meta name="format-detection" content="telephone=no">')
    html.append(f'<meta name="mobile-web-app-capable" content="yes">')

    # ── Application Name ──
    html.append(f'<meta name="application-name" content="Warungio">')

    # ── Open Graph ──
    html.append(f'<meta property="og:type" content="{_escape_attr(og_type)}">')
    if og_title:
        html.append(f'<meta property="og:title" content="{_escape_attr(og_title)}">')
    if og_description:
        html.append(f'<meta property="og:description" content="{_escape_attr(og_description)}">')
    html.append(f'<meta property="og:url" content="{_escape_attr(og_url)}">')
    if og_image:
        html.append(f'<meta property="og:image" content="{_escape_attr(og_image)}">')
        html.append(f'<meta property="og:image:width" content="1200">')
        html.append(f'<meta property="og:image:height" content="630">')
        html.append(f'<meta property="og:image:type" content="image/png">')
        html.append(f'<meta property="og:image:alt" content="{_escape_attr(meta_title)}">')
    html.append(f'<meta property="og:locale" content="{_escape_attr(og_locale)}">')
    html.append(f'<meta property="og:site_name" content="{_escape_attr(og_site_name)}">')
    html.append('<meta property="og:country-name" content="Indonesia">')

    # ── Twitter Card ──
    html.append(f'<meta name="twitter:card" content="{_escape_attr(twitter_card)}">')
    html.append(f'<meta name="twitter:site" content="{_escape_attr(twitter_site)}">')
    html.append(f'<meta name="twitter:creator" content="{_escape_attr(twitter_creator)}">')
    if twitter_title:
        html.append(f'<meta name="twitter:title" content="{_escape_attr(twitter_title)}">')
    if twitter_description:
        html.append(f'<meta name="twitter:description" content="{_escape_attr(twitter_description)}">')
    if twitter_image:
        html.append(f'<meta name="twitter:image" content="{_escape_attr(twitter_image)}">')
        html.append(f'<meta name="twitter:image:alt" content="{_escape_attr(meta_title)}">')

    # ── PWA / Web App Manifest ──
    html.append(f'<link rel="manifest" href="{site_url}/assets/pwa/manifest.json">')

    # ── Preconnect / DNS-Prefetch ──
    preconnects = [
        "https://fonts.googleapis.com",
        "https://fonts.gstatic.com",
        "https://cdn.tailwindcss.com",
        "https://cdnjs.cloudflare.com",
        "https://unpkg.com",
    ]
    for url in preconnects:
        html.append(f'<link rel="preconnect" href="{url}" crossorigin>')
        html.append(f'<link rel="dns-prefetch" href="{url}">')

    # ── Hreflang ──
    hreflang_tags = seo.get("hreflang_tags", [])
    for hl in hreflang_tags:
        html.append(f'<link rel="alternate" hreflang="{hl["lang"]}" href="{hl["url"]}">')

    return mark_safe("\n    ".join(html))


@register.simple_tag(takes_context=True)
def json_ld_block(context):
    """Render JSON-LD structured data as <script> blocks."""
    seo = context.get("seo", {})
    schemas = seo.get("json_ld", [])
    if not schemas:
        return ""

    import json

    html = []
    for schema in schemas:
        json_str = json.dumps(schema, ensure_ascii=False, indent=2)
        html.append(f'<script type="application/ld+json">\n{json_str}\n</script>')

    return mark_safe("\n".join(html))


@register.simple_tag(takes_context=True)
def canonical_url(context):
    """Render canonical URL link tag."""
    seo = context.get("seo", {})
    url = seo.get("canonical_url", "")
    if url:
        return mark_safe(f'<link rel="canonical" href="{url}">')
    return ""


@register.simple_tag(takes_context=True)
def hreflang_tags(context):
    """Render hreflang alternate link tags."""
    seo = context.get("seo", {})
    tags = seo.get("hreflang_tags", [])
    if not tags:
        return ""
    html = []
    for hl in tags:
        html.append(f'<link rel="alternate" hreflang="{hl["lang"]}" href="{hl["url"]}">')
    return mark_safe("\n".join(html))


@register.simple_tag(takes_context=True)
def meta_robots(context):
    """Render meta robots tag."""
    seo = context.get("seo", {})
    robots = seo.get("robots", "index, follow")
    return mark_safe(f'<meta name="robots" content="{robots}">')
