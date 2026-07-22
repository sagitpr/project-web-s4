"""
SEO Page Validation Script for Warungio.
Tests that all SEO landing page types return HTTP 200 and have proper SEO tags.

Usage:
    python scripts/test_seo_pages.py                    # Test with local dev server
    python scripts/test_seo_pages.py --url https://warungio.web.id  # Test production
    python scripts/test_seo_pages.py --verbose          # Show full HTML head for debugging
"""

import os
import sys
import argparse
import urllib.request
import urllib.error
import re
import json
from urllib.parse import urljoin

BASE_URL = "http://localhost:8000"


# ── Expected SEO pages ──
# Each entry: (path, expected_title_substring, expected_schema_type, expect_noindex, expect_canonical)
SEO_PAGES = [
    # Core pages
    ("/", "Warungio", "WebPage", False),
    ("/robots.txt", None, None, None),  # Will test separately
    ("/sitemap.xml", None, None, None),  # Will test separately

    # Info pages
    ("/info/tentang-kami/", "Tentang Kami", "AboutPage", False),
    ("/info/cara-belanja/", "Cara Belanja", "WebPage", False),
    ("/info/metode-pembayaran/", "Metode Pembayaran", "WebPage", False),
    ("/info/kontak-kami/", "Hubungi Kami", "ContactPage", False),
    ("/info/kebijakan/", "Kebijakan", "WebPage", False),
    ("/info/blog/", "Blog", "Blog", False),
    ("/info/panduan-seller/", "Panduan Seller", "WebPage", False),
    ("/info/komunitas/", "Komunitas", "WebPage", False),
    ("/info/tips-sukses/", "Tips Sukses", "WebPage", False),

    # Help & Download
    ("/bantuan/", "Bantuan", "FAQPage", False),
    ("/download/", "Download", "WebPage", False),

    # SEO Landing Pages
    ("/kategori/", "Kategori", "CollectionPage", False),
    ("/kota/", "Kota", "CollectionPage", False),
]

# Auth pages (expected to return 200 but with noindex and not in sitemap)
AUTH_PAGES = [
    ("/auth/login/", "Masuk", True),
    ("/auth/register/", "Daftar", True),
    ("/auth/register-mitra/", "Mitra", True),
]


def fetch_url(url):
    """Fetch a URL and return (status_code, content, headers)."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8', errors='replace')
            return response.status, content, dict(response.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', errors='replace'), dict(e.headers)
    except Exception as e:
        return None, str(e), {}


def check_seo_tags(content, path, expected_title, expected_schema, expect_noindex):
    """Validate SEO meta tags in HTML content."""
    results = []
    content_lower = content.lower()

    # Check for <title>
    title_match = re.search(r'<title[^>]*>([^<]+)</title>', content)
    if title_match:
        title_text = title_match.group(1).strip()
        if expected_title.lower() in title_text.lower():
            results.append(("✅", f"<title> contains '{expected_title}'"))
        else:
            results.append(("❌", f"<title> = '{title_text}' — expected to contain '{expected_title}'"))
    else:
        results.append(("❌", "Missing <title> tag"))

    # Check for <meta description>
    desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']', content)
    if desc_match:
        desc = desc_match.group(1)
        if len(desc) >= 50:
            results.append(("✅", f"meta description present ({len(desc)} chars)"))
        else:
            results.append(("⚠️", f"meta description too short ({len(desc)} chars)"))
    else:
        results.append(("❌", "Missing meta description"))

    # Check for canonical URL
    canonical_match = re.search(r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)["\']', content)
    if canonical_match:
        canonical = canonical_match.group(1)
        results.append(("✅", f"Canonical URL: {canonical}"))
    else:
        results.append(("❌", "Missing canonical URL"))

    # Check for robots meta
    robots_match = re.search(r'<meta\s+name=["\']robots["\']\s+content=["\']([^"\']+)["\']', content)
    if robots_match:
        robots = robots_match.group(1)
        if expect_noindex:
            if 'noindex' in robots:
                results.append(("✅", f"robots: {robots} (noindex as expected)"))
            else:
                results.append(("❌", f"robots: {robots} — expected noindex"))
        else:
            if 'index' in robots:
                results.append(("✅", f"robots: {robots}"))
            else:
                results.append(("⚠️", f"robots: {robots} — expected index"))
    else:
        results.append(("⚠️", "Missing meta robots tag"))

    # Check for Open Graph
    og_title_match = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', content)
    if og_title_match:
        results.append(("✅", "og:title present"))
    else:
        results.append(("⚠️", "Missing og:title"))

    og_desc_match = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\']([^"\']+)["\']', content)
    if og_desc_match:
        results.append(("✅", "og:description present"))
    else:
        results.append(("⚠️", "Missing og:description"))

    og_image_match = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', content)
    if og_image_match:
        results.append(("✅", "og:image present"))
    else:
        results.append(("⚠️", "Missing og:image"))

    # Check for Twitter Card
    twitter_card = re.search(r'<meta\s+name=["\']twitter:card["\']\s+content=["\']([^"\']+)["\']', content)
    if twitter_card:
        results.append(("✅", "twitter:card present"))
    else:
        results.append(("⚠️", "Missing twitter:card"))

    # Check for JSON-LD
    jsonld_schemas = re.findall(r'<script\s+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', content, re.DOTALL)
    if jsonld_schemas:
        schema_types = []
        for js in jsonld_schemas:
            try:
                data = json.loads(js.strip())
                if isinstance(data, dict):
                    schema_types.append(data.get('@type', ''))
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            schema_types.append(item.get('@type', ''))
            except json.JSONDecodeError:
                pass

        if expected_schema and expected_schema in schema_types:
            results.append(("✅", f"JSON-LD @type '{expected_schema}' found"))
        elif expected_schema:
            results.append(("⚠️", f"JSON-LD @type '{expected_schema}' NOT found. Found: {schema_types[:5]}"))
        else:
            results.append(("✅", f"JSON-LD schemas: {', '.join(schema_types[:5])}"))
    else:
        results.append(("❌", "Missing JSON-LD structured data"))

    return results


def main():
    parser = argparse.ArgumentParser(description="Validate SEO pages for Warungio")
    parser.add_argument("--url", default=BASE_URL, help=f"Base URL (default: {BASE_URL})")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show full HTML head for debugging")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    verbose = args.verbose

    print(f"\n{'='*70}")
    print(f"  SEO PAGE VALIDATION — {base_url}")
    print(f"{'='*70}\n")

    # Test robots.txt
    print(f"  ├─ Testing /robots.txt...")
    status, content, headers = fetch_url(f"{base_url}/robots.txt")
    if status == 200:
        lines = content.strip().split('\n')
        sitemap_line = [l for l in lines if l.startswith('Sitemap:')]
        allow_lines = [l for l in lines if l.startswith('Allow:')]
        print(f"  │  ✅ HTTP 200 — {len(lines)} lines, {len(sitemap_line)} sitemap refs, {len(allow_lines)} Allow directives")
        if verbose:
            print(f"  │  ── Content ──")
            for line in lines[:20]:
                print(f"  │  {line}")
    else:
        print(f"  │  ❌ HTTP {status}")

    # Test sitemap.xml
    print(f"\n  ├─ Testing /sitemap.xml...")
    status, content, headers = fetch_url(f"{base_url}/sitemap.xml")
    if status == 200:
        url_count = content.count('<url>')
        loc_count = content.count('<loc>')
        print(f"  │  ✅ HTTP 200 — {url_count} URLs, {loc_count} <loc> entries")
        # Show sample entries
        locs = re.findall(r'<loc>([^<]+)</loc>', content)
        for loc in locs[:5]:
            print(f"  │     {loc}")
        if len(locs) > 5:
            print(f"  │     ... and {len(locs) - 5} more")
    else:
        print(f"  │  ❌ HTTP {status}")

    # Test each SEO page
    print(f"\n  ├─ Testing {len(SEO_PAGES) + len(AUTH_PAGES)} pages for HTTP 200 + SEO tags...")
    pages_passed = 0
    pages_failed = 0
    tags_total = 0
    tags_passed = 0

    all_pages = [(p, False) for p in SEO_PAGES] + [(p, True) for p in AUTH_PAGES]

    for page_info, is_auth in all_pages:
        if is_auth:
            path, expected_title, expect_noindex = page_info
            expected_schema = "WebPage"
        else:
            path, expected_title, expected_schema, expect_noindex = page_info

        url = f"{base_url}{path}"
        status, content, headers = fetch_url(url)

        if status == 200:
            page_ok = True
            if is_auth and expect_noindex:
                result_prefix = "🔒"
            else:
                result_prefix = "  "
            print(f"\n  {result_prefix} {path} — HTTP 200")
            pages_passed += 1

            # Skip SEO tag checks for non-HTML resources
            if path in ('/robots.txt', '/sitemap.xml'):
                continue

            # Check SEO tags
            tag_results = check_seo_tags(content, path, expected_title, expected_schema, expect_noindex)
            for status_icon, msg in tag_results:
                tag_ok = "✅" in status_icon or "⚠️" in status_icon
                tags_total += 1
                if tag_ok:
                    tags_passed += 1
                print(f"     {status_icon} {msg}")
        else:
            print(f"\n  ❌ {path} — HTTP {status}" + (f" ({content[:200]})" if content else ""))
            pages_failed += 1

    # Summary
    print(f"\n{'='*70}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f"  Pages tested:  {len(SEO_PAGES) + len(AUTH_PAGES)}")
    print(f"  Pages passed:  {pages_passed} (HTTP 200)")
    print(f"  Pages failed:  {pages_failed}")
    if tags_total > 0:
        tag_score = (tags_passed / tags_total) * 100
        print(f"  SEO tags:      {tags_passed}/{tags_total} ({tag_score:.0f}%)")
    print(f"{'='*70}\n")

    if pages_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
