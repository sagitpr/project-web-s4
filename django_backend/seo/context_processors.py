"""
SEO context processor for Warungio Marketplace.
Provides dynamic SEO metadata (title, description, OG, Twitter, JSON-LD, canonical, etc.)
to all templates based on the current request path.

Usage:
    In templates: {{ seo.meta_title }}, {{ seo.meta_description }}
    Include: {% include 'seo/seo_meta.html' %}

This processor is registered in settings.TEMPLATES[].OPTIONS.context_processors.
"""

from django.conf import settings
from django.urls import reverse

# Import JSON for breadcrumb parsing
import json

# Try to import the SeoMetadata model if it exists
# (graceful fallback if migrations haven't been run yet)
try:
    from .models import SeoMetadata
    _HAS_SEO_MODEL = True
except Exception:
    SeoMetadata = None
    _HAS_SEO_MODEL = False

# ── Site-wide constants ──
SITE_NAME = "Warungio"
SITE_URL = "https://warungio.web.id"
SITE_DESCRIPTION = (
    "Warungio adalah marketplace hyperlocal Indonesia yang menghubungkan "
    "pembeli dengan warung dan UMKM lokal terdekat. Belanja kebutuhan harian, "
    "sembako, sayur segar, buah segar, daging, dan produk kebutuhan rumah "
    "tangga lainnya dengan pengiriman cepat dan pembayaran aman."
)
SITE_KEYWORDS = (
    "warungio, marketplace hyperlocal, belanja online sembako, warung online, "
    "UMKM Indonesia, toko kelontong digital, belanja kebutuhan harian, "
    "sayur segar online, buah segar online, sembako murah, "
    "grocery delivery Indonesia, distributor sembako, supplier bahan pokok, "
    "belanja dari warung terdekat, aplikasi belanja harian"
)
DEFAULT_OG_IMAGE = f"{SITE_URL}/static/images/Warungio L.png"
DEFAULT_LOCALE = "id_ID"
ALTERNATE_LOCALES = {
    "en_US": "/en/",
}
CONTACT_EMAIL = "info@warungio.id"
CONTACT_PHONE = "+6281234567890"
SOCIAL_LINKS = {
    "facebook": "https://facebook.com/warungio",
    "instagram": "https://instagram.com/warungio",
    "twitter": "https://twitter.com/warungio",
    "youtube": "https://youtube.com/@warungio",
}


# ═══════════════════════════════════════════════════════════════════════
#  PAGE-SPECIFIC SEO METADATA
# ═══════════════════════════════════════════════════════════════════════
# Each entry can specify:
#   meta_title        — HTML <title>
#   meta_description  — <meta name="description"> (aim for 155-160 chars)
#   og_title          — Open Graph title (defaults to meta_title)
#   og_description    — Open Graph description (defaults to meta_description)
#   og_image          — Open Graph image URL
#   canonical         — Canonical URL path (defaults to request.path)
#   schema_type       — JSON-LD @type for WebPage schema
#   keywords          — Page-specific keywords
#   breadcrumbs       — List of (label, url) tuples
#   noindex           — If True, set meta robots noindex
#   hreflang          — Dict of language_code: URL for alternate pages
#   body_class        — CSS class for <body>
#
_PAGE_SEO = {
    # ── Landing / Home ──
    "/": {
        "meta_title": f"{SITE_NAME} - Marketplace Hyperlocal Indonesia untuk Kebutuhan Harian",
        "meta_description": (
            "Warungio adalah marketplace hyperlocal terbaik di Indonesia untuk "
            "belanja kebutuhan harian, sembako, sayur segar, buah segar, daging, "
            "dan produk rumah tangga langsung dari warung dan UMKM terdekat. "
            "Nikmati pengiriman cepat, pembayaran aman via Midtrans (QRIS, GoPay, "
            "OVO, transfer bank, COD), dan harga terjangkau. Download aplikasi "
            "Warungio sekarang dan rasakan kemudahan belanja dari rumah!"
        ),
        "schema_type": "WebPage",
        "breadcrumbs": [("Beranda", "/")],
    },
    # ── Auth Pages ──
    "/auth/login/": {
        "meta_title": f"Masuk - {SITE_NAME}",
        "meta_description": (
            "Masuk ke akun Warungio Anda untuk mulai belanja kebutuhan harian, "
            "sembako, sayur segar, dan produk rumah tangga dari warung terdekat. "
            "Nikmati kemudahan belanja online dengan pengiriman cepat dan "
            "pembayaran aman via QRIS, GoPay, OVO, atau COD."
        ),
        "schema_type": "WebPage",
        "noindex": True,
        "breadcrumbs": [("Beranda", "/"), ("Masuk", "/auth/login/")],
    },
    "/auth/login-seller/": {
        "meta_title": f"Login Mitra Seller - {SITE_NAME}",
        "meta_description": (
            "Login ke dashboard seller Warungio untuk mengelola toko, produk, "
            "pesanan, dan keuangan Anda. Pantau performa bisnis UMKM Anda secara "
            "real-time dan jangkau lebih banyak pelanggan."
        ),
        "schema_type": "WebPage",
        "noindex": True,
        "breadcrumbs": [("Beranda", "/"), ("Login Seller", "/auth/login-seller/")],
    },
    "/auth/register/": {
        "meta_title": f"Daftar Akun Baru - {SITE_NAME}",
        "meta_description": (
            "Daftar akun Warungio sekarang dan nikmati kemudahan belanja kebutuhan "
            "harian online. Temukan sembako murah, sayur segar, buah segar, daging "
            "berkualitas, dan kebutuhan rumah tangga lengkap dari warung terdekat. "
            "Gratis pendaftaran!"
        ),
        "schema_type": "WebPage",
        "noindex": True,
        "breadcrumbs": [("Beranda", "/"), ("Daftar", "/auth/register/")],
    },
    "/auth/register-mitra/": {
        "meta_title": f"Daftar Menjadi Mitra Seller - {SITE_NAME}",
        "meta_description": (
            "Gabung menjadi mitra seller Warungio dan kembangkan usaha warung atau "
            "UMKM Anda. Jangkau lebih banyak pelanggan, kelola pesanan dengan mudah, "
            "dan tingkatkan penjualan melalui platform marketplace hyperlocal terpercaya. "
            "Daftar gratis sekarang!"
        ),
        "schema_type": "WebPage",
        "noindex": True,
        "breadcrumbs": [("Beranda", "/"), ("Daftar Mitra", "/auth/register-mitra/")],
    },
    "/auth/otp/": {
        "meta_title": f"Verifikasi OTP - {SITE_NAME}",
        "meta_description": "Verifikasi akun Warungio Anda dengan kode OTP yang telah dikirim ke email atau WhatsApp Anda.",
        "schema_type": "WebPage",
        "noindex": True,
    },
    "/auth/reset-password/": {
        "meta_title": f"Reset Password - {SITE_NAME}",
        "meta_description": "Reset password akun Warungio Anda. Masukkan email terdaftar untuk menerima kode OTP reset password.",
        "schema_type": "WebPage",
        "noindex": True,
    },
    # ── Info / Public Pages ──
    "/info/tentang-kami/": {
        "meta_title": f"Tentang Kami | {SITE_NAME} Hyperlocal Marketplace",
        "meta_description": (
            "Pelajari lebih lanjut tentang Warungio, marketplace hyperlocal Indonesia "
            "yang memberdayakan warung lokal dan UMKM. Kami menghubungkan pembeli "
            "dengan warung terdekat untuk belanja kebutuhan harian, sembako, sayur "
            "segar, dan buah segar dengan pengiriman cepat dan pembayaran aman. "
            "Visi kami adalah mendigitalisasi jutaan warung tradisional Indonesia."
        ),
        "schema_type": "AboutPage",
        "breadcrumbs": [("Beranda", "/"), ("Tentang Kami", "/info/tentang-kami/")],
    },
    "/info/cara-belanja/": {
        "meta_title": f"Cara Belanja di {SITE_NAME} - Panduan Lengkap",
        "meta_description": (
            "Panduan lengkap cara belanja di Warungio. Mulai dari mendaftar akun, "
            "mencari produk sembako dan sayur segar, menambahkan ke keranjang, "
            "checkout dengan berbagai metode pembayaran (QRIS, GoPay, OVO, transfer "
            "bank, COD), hingga melacak pengiriman. Belanja kebutuhan harian jadi "
            "lebih mudah dan cepat bersama Warungio."
        ),
        "schema_type": "WebPage",
        "breadcrumbs": [("Beranda", "/"), ("Cara Belanja", "/info/cara-belanja/")],
    },
    "/info/metode-pembayaran/": {
        "meta_title": f"Metode Pembayaran - {SITE_NAME}",
        "meta_description": (
            "Warungio mendukung berbagai metode pembayaran aman dan praktis: "
            "transfer bank (BCA, Mandiri, BRI, BNI), e-wallet (GoPay, OVO, DANA, "
            "ShopeePay), QRIS, kartu kredit/debit (Visa, Mastercard, JCB), dan "
            "COD (Cash on Delivery). Semua pembayaran online diproses melalui "
            "Midtrans dengan enkripsi keamanan tinggi."
        ),
        "schema_type": "WebPage",
        "breadcrumbs": [("Beranda", "/"), ("Metode Pembayaran", "/info/metode-pembayaran/")],
    },
    "/info/kontak-kami/": {
        "meta_title": f"Hubungi Kami - {SITE_NAME}",
        "meta_description": (
            "Hubungi tim customer service Warungio melalui email, telepon, WhatsApp, "
            "atau kunjungi kantor pusat kami. Kami siap membantu Anda 24/7 untuk "
            "pertanyaan tentang pesanan, pembayaran, pengiriman, atau pendaftaran "
            "mitra seller. Warungio - belanja kebutuhan harian lebih mudah."
        ),
        "schema_type": "ContactPage",
        "breadcrumbs": [("Beranda", "/"), ("Hubungi Kami", "/info/kontak-kami/")],
    },
    "/info/kebijakan/": {
        "meta_title": f"Kebijakan & Ketentuan - {SITE_NAME}",
        "meta_description": (
            "Syarat dan ketentuan penggunaan platform marketplace hyperlocal Warungio. "
            "Pelajari hak dan kewajiban pengguna, kebijakan privasi, ketentuan "
            "pembayaran dan refund, serta perubahan kebijakan. Dengan menggunakan "
            "Warungio, Anda menyetujui seluruh ketentuan yang berlaku."
        ),
        "schema_type": "WebPage",
        "breadcrumbs": [("Beranda", "/"), ("Kebijakan", "/info/kebijakan/")],
    },
    "/info/blog/": {
        "meta_title": f"Blog - {SITE_NAME}",
        "meta_description": (
            "Baca artikel tips belanja, resep masak, panduan bisnis UMKM, dan "
            "informasi terbaru seputar Warungio. Dapatkan inspirasi belanja "
            "kebutuhan harian, sembako, sayur segar, dan buah segar dengan "
            "tips hemat dari Warungio."
        ),
        "schema_type": "Blog",
        "breadcrumbs": [("Beranda", "/"), ("Blog", "/info/blog/")],
    },
    "/info/panduan-seller/": {
        "meta_title": f"Panduan Seller - {SITE_NAME}",
        "meta_description": (
            "Panduan lengkap untuk mitra seller Warungio. Pelajari cara mendaftar "
            "sebagai mitra, mengelola produk, memproses pesanan, melakukan pencairan "
            "dana, dan tips sukses berjualan di platform marketplace hyperlocal. "
            "Kembangkan bisnis UMKM Anda bersama Warungio."
        ),
        "schema_type": "WebPage",
        "breadcrumbs": [("Beranda", "/"), ("Panduan Seller", "/info/panduan-seller/")],
    },
    "/info/komunitas/": {
        "meta_title": f"Komunitas Seller - Warungio",
        "meta_description": (
            "Bergabung dengan komunitas seller Warungio di seluruh Indonesia. "
            "Diskusikan strategi bisnis, dapatkan tips sukses, dan ikuti webinar "
            "eksklusif untuk mengembangkan usaha UMKM Anda. Warungio - memberdayakan "
            "warung lokal Indonesia."
        ),
        "schema_type": "WebPage",
        "breadcrumbs": [("Beranda", "/"), ("Komunitas Seller", "/info/komunitas/")],
    },
    "/info/tips-sukses/": {
        "meta_title": f"Tips Sukses untuk Seller - {SITE_NAME}",
        "meta_description": (
            "Kumpulan tips sukses untuk mitra seller Warungio. Pelajari strategi "
            "foto produk berkualitas, respons cepat, manajemen stok, pemanfaatan "
            "promo, dan analisis data bisnis untuk mengembangkan toko Anda di "
            "marketplace hyperlocal terbesar di Indonesia."
        ),
        "schema_type": "WebPage",
        "breadcrumbs": [("Beranda", "/"), ("Tips Sukses", "/info/tips-sukses/")],
    },
    # ── Bantuan / Help Center ──
    "/bantuan/": {
        "meta_title": f"Pusat Bantuan - {SITE_NAME}",
        "meta_description": (
            "Pusat bantuan Warungio. Temukan jawaban atas pertanyaan seputar "
            "pesanan, pembayaran, pengiriman, refund, dan cara menggunakan platform. "
            "Cari artikel panduan, FAQ, atau hubungi tim customer service kami "
            "yang siap membantu 24 jam sehari, 7 hari seminggu."
        ),
        "schema_type": "FAQPage",
        "breadcrumbs": [("Beranda", "/"), ("Bantuan", "/bantuan/")],
    },
    # ── Download Page ──
    "/download/": {
        "meta_title": f"Download Aplikasi {SITE_NAME} - Belanja Lebih Mudah",
        "meta_description": (
            "Download aplikasi Warungio untuk pengalaman belanja kebutuhan harian "
            "yang lebih mudah, cepat, dan hemat. Tersedia untuk Android (APK) dan "
            "iOS (segera hadir). Belanja sembako, sayur segar, buah, daging, dan "
            "kebutuhan rumah tangga langsung dari warung terdekat."
        ),
        "schema_type": "WebPage",
        "breadcrumbs": [("Beranda", "/"), ("Download", "/download/")],
    },
    # ── Buyer Dashboard ──
    "/buyer/dashboard/": {
        "meta_title": f"Dashboard Pembeli - {SITE_NAME}",
        "meta_description": "Dashboard pembeli Warungio. Kelola profil, pantau pesanan, dan temukan rekomendasi warung terdekat.",
        "schema_type": "WebPage",
        "noindex": True,
    },
    "/buyer/home/": {
        "meta_title": f"Marketplace - {SITE_NAME}",
        "meta_description": "Temukan warung terdekat, produk segar pilihan, dan promo terbaik hari ini di marketplace Warungio.",
        "schema_type": "WebPage",
        "noindex": True,
    },
    # ── Products ──
    "/buyer/products/": {
        "meta_title": f"Semua Produk | {SITE_NAME} Marketplace",
        "meta_description": "Jelajahi semua produk segar, sembako, dan kebutuhan harian dari warung dan UMKM terdekat di Warungio.",
        "schema_type": "CollectionPage",
        "noindex": True,
    },
    # ── Seller Pages ──
    "/seller/dashboard/": {
        "meta_title": f"Dashboard Seller - {SITE_NAME}",
        "meta_description": "Dashboard seller Warungio. Pantau penjualan, pesanan, dan performa toko Anda secara real-time.",
        "schema_type": "WebPage",
        "noindex": True,
    },
    "/seller/products/": {
        "meta_title": f"Produk Saya - {SITE_NAME} Seller",
        "meta_description": "Kelola, tambah, dan edit produk toko Anda di dashboard seller Warungio.",
        "schema_type": "WebPage",
        "noindex": True,
    },
    "/seller/orders/": {
        "meta_title": f"Pesanan Masuk - {SITE_NAME} Seller",
        "meta_description": "Kelola dan proses pesanan pelanggan di dashboard seller Warungio.",
        "schema_type": "WebPage",
        "noindex": True,
    },
}

# ── Default SEO (for unlisted paths) ──
_DEFAULT_SEO = {
    "meta_title": SITE_NAME,
    "meta_description": SITE_DESCRIPTION[:160],
    "og_title": SITE_NAME,
    "og_description": SITE_DESCRIPTION[:200],
    "og_image": DEFAULT_OG_IMAGE,
    "canonical": None,
    "schema_type": "WebPage",
    "keywords": SITE_KEYWORDS,
    "breadcrumbs": [],
    "noindex": False,
    "hreflang": None,
    "body_class": "",
}


def _build_absolute_url(path):
    """Convert a relative path to absolute URL."""
    if path.startswith("http"):
        return path
    return f"{SITE_URL}{path}"


def _get_seo_for_path(path):
    """Get SEO metadata dict for the given request path, with intelligent fallback.
    
    Priority:
    1. SeoMetadata model record (if exists and active)
    2. Hardcoded _PAGE_SEO dictionary
    3. Dynamic prefix matching
    4. Default SEO
    """
    # Normalize path
    path = path.split("?")[0].split("#")[0]
    if path != "/":
        path = path.rstrip("/") + "/"

    # 1. Check SeoMetadata model first (admin-editable)
    if _HAS_SEO_MODEL and SeoMetadata is not None:
        try:
            from_db = SeoMetadata.get_for_path(path)
            if from_db:
                seo = {
                    "meta_title": from_db.meta_title or None,
                    "meta_description": from_db.meta_description or None,
                    "og_title": from_db.og_title or None,
                    "og_description": from_db.og_description or None,
                    "og_image": from_db.og_image or None,
                    "canonical": from_db.canonical_url or None,
                    "schema_type": from_db.schema_type if from_db.schema_type != 'WebPage' else None,
                    "keywords": from_db.meta_keywords or None,
                    "noindex": from_db.noindex,
                    "breadcrumbs": None,  # parsed from breadcrumb_json
                    "hreflang": None,  # parsed from hreflang_json
                }
                # Parse breadcrumb JSON if provided
                # Format expected: [{"label":"Home","url":"/"}, ...]
                # Converted to tuples for _build_json_ld compatibility
                if from_db.breadcrumb_json:
                    try:
                        parsed = json.loads(from_db.breadcrumb_json)
                        if isinstance(parsed, list) and len(parsed) > 0:
                            # Convert dicts to tuples (label, url) for _build_json_ld
                            seo["breadcrumbs"] = [
                                (item.get("label", ""), item.get("url", ""))
                                for item in parsed
                                if isinstance(item, dict) and "label" in item
                            ]
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                # Parse hreflang JSON if provided
                if from_db.hreflang_json:
                    try:
                        parsed = json.loads(from_db.hreflang_json)
                        if isinstance(parsed, dict) and len(parsed) > 0:
                            seo["hreflang"] = parsed
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                # Remove None values so they fall through to hardcoded defaults
                seo = {k: v for k, v in seo.items() if v is not None}
                return seo
        except Exception:
            pass  # Fall through to hardcoded

    # 2. Check hardcoded _PAGE_SEO
    seo = _PAGE_SEO.get(path)

    # 3. Dynamic prefix matching
    if seo is None:
        if path.startswith("/bantuan/artikel/"):
            seo = {
                "meta_title": f"Artikel Bantuan - {SITE_NAME}",
                "meta_description": "Baca artikel panduan dan informasi bantuan Warungio.",
                "schema_type": "Article",
                "noindex": False,
            }
        elif path.startswith("/products/"):
            seo = {
                "meta_title": f"Detail Produk - {SITE_NAME}",
                "meta_description": "Lihat detail produk, harga, dan ulasan di Warungio.",
                "schema_type": "Product",
                "noindex": True,
            }
        elif path.startswith("/buyer/"):
            seo = {
                "meta_title": f"Akun Saya - {SITE_NAME}",
                "meta_description": "Halaman akun pembeli Warungio.",
                "schema_type": "WebPage",
                "noindex": True,
            }
        elif path.startswith("/seller/"):
            seo = {
                "meta_title": f"Seller - {SITE_NAME}",
                "meta_description": "Dashboard dan manajemen toko seller Warungio.",
                "schema_type": "WebPage",
                "noindex": True,
            }
        elif path.startswith("/admin-panel/"):
            seo = {
                "meta_title": f"Admin - {SITE_NAME}",
                "meta_description": "Panel admin Warungio.",
                "schema_type": "WebPage",
                "noindex": True,
            }
        elif path.startswith("/auth/"):
            seo = {
                "meta_title": f"Autentikasi - {SITE_NAME}",
                "meta_description": "Halaman autentikasi Warungio.",
                "schema_type": "WebPage",
                "noindex": True,
            }

    return seo or _DEFAULT_SEO


def seo_metadata(request):
    """
    Context processor that injects comprehensive SEO metadata into all templates.

    Usage in templates:
        {{ seo.meta_title }}
        {{ seo.meta_description }}
        {{ seo.canonical_url }}

    Or simply include the pre-built template:
        {% include 'seo/seo_meta.html' %}
    """
    path = request.path_info or "/"
    page_seo = _get_seo_for_path(path)

    # Build SEO context
    meta_title = page_seo.get("meta_title", _DEFAULT_SEO["meta_title"])
    meta_description = page_seo.get("meta_description", _DEFAULT_SEO["meta_description"])
    og_title = page_seo.get("og_title", meta_title)
    og_description = page_seo.get("og_description", meta_description)
    og_image = page_seo.get("og_image", DEFAULT_OG_IMAGE)
    og_image_url = _build_absolute_url(og_image) if og_image else DEFAULT_OG_IMAGE
    schema_type = page_seo.get("schema_type", "WebPage")
    keywords = page_seo.get("keywords", SITE_KEYWORDS)
    breadcrumbs = page_seo.get("breadcrumbs", [])
    noindex = page_seo.get("noindex", False)
    hreflang = page_seo.get("hreflang", None)

    # Canonical URL
    canonical_path = page_seo.get("canonical", path)
    if canonical_path and not canonical_path.startswith("http"):
        canonical_url = _build_absolute_url(canonical_path)
    else:
        canonical_url = canonical_path or _build_absolute_url(path)

    # Body class
    body_class = page_seo.get("body_class", "")
    if noindex:
        body_class += " noindex-page"
    body_class = body_class.strip()

    # Build JSON-LD structured data
    json_ld = _build_json_ld(schema_type, meta_title, meta_description, canonical_url, breadcrumbs)

    # Build hreflang tags
    hreflang_tags = []
    if hreflang:
        for lang_code, lang_url in hreflang.items():
            hreflang_tags.append({
                "lang": lang_code,
                "url": _build_absolute_url(lang_url),
            })
    # Always add default
    hreflang_tags.append({
        "lang": "id",
        "url": canonical_url,
    })

    seo = {
        "meta_title": meta_title,
        "meta_description": meta_description,
        "og_title": og_title,
        "og_description": og_description,
        "og_image": og_image_url,
        "og_type": page_seo.get("og_type", "website"),
        "og_url": canonical_url,
        "og_locale": DEFAULT_LOCALE,
        "og_site_name": SITE_NAME,
        "twitter_card": page_seo.get("twitter_card", "summary_large_image"),
        "twitter_title": og_title,
        "twitter_description": og_description,
        "twitter_image": og_image_url,
        "twitter_site": "@warungio",
        "twitter_creator": "@warungio",
        "canonical_url": canonical_url,
        "keywords": keywords,
        "schema_type": schema_type,
        "json_ld": json_ld,
        "noindex": noindex,
        "robots": "noindex, nofollow" if noindex else "index, follow, max-image-preview:large, max-snippet:-1",
        "hreflang_tags": hreflang_tags,
        "breadcrumbs": breadcrumbs,
        "page_name": meta_title.split(" | ")[0] if " | " in meta_title else meta_title.split(" - ")[0],
        "body_class": body_class,
        # Site-wide constants
        "site_name": SITE_NAME,
        "site_url": SITE_URL,
        "site_description": SITE_DESCRIPTION,
        "site_keywords": SITE_KEYWORDS,
        "contact_email": CONTACT_EMAIL,
        "contact_phone": CONTACT_PHONE,
        "social_links": SOCIAL_LINKS,
        "current_year": 2026,
    }

    return {"seo": seo}


def _build_json_ld(schema_type, name, description, url, breadcrumbs):
    """
    Build comprehensive JSON-LD structured data.

    Returns a list of schema objects that should be rendered as
    separate <script type="application/ld+json"> blocks.
    """
    schemas = []

    # 1. Organization (always included)
    schemas.append({
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": SITE_NAME,
        "url": SITE_URL,
        "logo": f"{SITE_URL}/static/images/Warungio L.png",
        "description": SITE_DESCRIPTION[:200],
        "email": CONTACT_EMAIL,
        "telephone": CONTACT_PHONE,
        "foundingDate": "2023",
        "foundingLocation": "Tasikmalaya, Indonesia",
        "areaServed": "ID",
        "contactPoint": {
            "@type": "ContactPoint",
            "telephone": CONTACT_PHONE,
            "contactType": "customer service",
            "areaServed": "ID",
            "availableLanguage": ["Indonesian", "English"],
        },
        "sameAs": [
            SOCIAL_LINKS["facebook"],
            SOCIAL_LINKS["instagram"],
            SOCIAL_LINKS["twitter"],
            SOCIAL_LINKS["youtube"],
        ],
    })

    # 2. WebSite (always included, with SearchAction)
    schemas.append({
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": SITE_NAME,
        "url": SITE_URL,
        "description": SITE_DESCRIPTION[:200],
        "inLanguage": "id-ID",
        "potentialAction": {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": f"{SITE_URL}/buyer/products/?search={{search_term_string}}",
            },
            "query-input": "required name=search_term_string",
        },
    })

    # 3. WebPage or specific subtype
    page_schema = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": name,
        "description": description[:200] if description else "",
        "url": url,
        "inLanguage": "id-ID",
        "isPartOf": {
            "@id": f"{SITE_URL}/#website",
        },
    }

    # Add breadcrumb reference
    if breadcrumbs:
        page_schema["breadcrumb"] = {
            "@id": f"{url}#breadcrumb",
        }

    schemas.append(page_schema)

    # 4. BreadcrumbList (if breadcrumbs exist)
    if breadcrumbs:
        item_list = []
        for i, (label, crumb_url) in enumerate(breadcrumbs, start=1):
            item_list.append({
                "@type": "ListItem",
                "position": i,
                "name": label,
                "item": _build_absolute_url(crumb_url),
            })
        schemas.append({
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "@id": f"{url}#breadcrumb",
            "itemListElement": item_list,
        })

    # 5. LocalBusiness (for contact page or landing page)
    if schema_type in ("ContactPage", "AboutPage", "WebPage"):
        schemas.append({
            "@context": "https://schema.org",
            "@type": "LocalBusiness",
            "name": SITE_NAME,
            "url": SITE_URL,
            "logo": f"{SITE_URL}/static/images/Warungio L.png",
            "image": f"{SITE_URL}/static/images/Warungio L.png",
            "description": SITE_DESCRIPTION[:200],
            "email": CONTACT_EMAIL,
            "telephone": CONTACT_PHONE,
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "Tasikmalaya",
                "addressRegion": "Jawa Barat",
                "addressCountry": "ID",
            },
            "areaServed": "ID",
            "priceRange": "Rp",
            "currenciesAccepted": "IDR",
            "paymentAccepted": ["Cash", "Credit Card", "QRIS", "GoPay", "OVO", "Bank Transfer"],
        })

    # 6. MobileApplication (always included since Warungio has a mobile app)
    schemas.append({
        "@context": "https://schema.org",
        "@type": "MobileApplication",
        "name": f"{SITE_NAME} Marketplace",
        "operatingSystem": "Android, iOS",
        "applicationCategory": "ShoppingApplication",
        "description": SITE_DESCRIPTION[:200],
        "url": f"{SITE_URL}/download/",
        "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "IDR",
        },
    })

    return schemas
