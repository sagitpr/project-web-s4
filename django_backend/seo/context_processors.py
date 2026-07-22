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
    "Warungio adalah ekosistem manajemen bisnis dan marketplace hyperlocal "
    "Indonesia terlengkap untuk UMKM dan warung tradisional. Sebagai platform "
    "all-in-one, Warungio menghubungkan pembeli dengan warung terdekat untuk "
    "belanja kebutuhan harian, sembako, sayur segar, buah segar, daging, dan "
    "produk rumah tangga. Untuk pemilik usaha, Warungio menyediakan sistem POS "
    "kasir digital, manajemen inventaris dan stok real-time, aplikasi stok barang "
    "gratis, laporan keuangan, analisis penjualan dengan AI, manajemen pemasok "
    "dan supplier, manajemen pelanggan, serta fitur promosi dan diskon. "
    "Digitalisasi warung Indonesia untuk bisnis yang lebih maju."
)
SITE_KEYWORDS = (
    "warungio, aplikasi stok barang gratis, aplikasi kasir gratis, "
    "manajemen inventaris UMKM, aplikasi bisnis UMKM, "
    "marketplace hyperlocal Indonesia, POS kasir digital, "
    "aplikasi toko kelontong, aplikasi warung sembako, "
    "manajemen stok barang, laporan keuangan bisnis, "
    "analisis penjualan UMKM, aplikasi supplier barang, "
    "manajemen pelanggan UMKM, belanja kebutuhan harian, "
    "sayur segar online, sembako online murah, "
    "belanja dari warung terdekat, aplikasi belanja harian, "
    "sistem informasi manajemen UMKM, digitalisasi warung, "
    "aplikasi pembukuan toko, aplikasi catat stok barang"
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
        "meta_title": f"{SITE_NAME} - Ekosistem Marketplace Hyperlocal & Manajemen Bisnis UMKM",
        "meta_description": (
            "Warungio adalah platform all-in-one yang menggabungkan marketplace "
            "hyperlocal dengan sistem manajemen bisnis UMKM terlengkap. Untuk "
            "pembeli: belanja kebutuhan harian, sembako, sayur segar, buah segar, "
            "daging, dan produk rumah tangga dari warung terdekat dengan pengiriman "
            "cepat. Untuk pemilik usaha: POS kasir digital gratis, aplikasi stok "
            "barang, manajemen inventaris real-time, laporan keuangan dan penjualan "
            "berbasis AI, manajemen supplier, manajemen pelanggan, serta fitur "
            "promosi. Digitalisasi warung Indonesia, tingkatkan omzet hingga 3x lipat!"
        ),
        "schema_type": "WebPage",
        "breadcrumbs": [("Beranda", "/")],
    },
    # ── Auth Pages ──
    "/auth/login/": {
        "meta_title": f"Masuk - {SITE_NAME} Marketplace & Bisnis UMKM",
        "meta_description": (
            "Masuk ke akun Warungio Anda. Pelanggan: belanja kebutuhan harian, "
            "sembako, dan sayur segar dari warung terdekat. Pemilik UMKM: kelola "
            "toko, pantau stok barang, akses laporan penjualan, dan proses pesanan "
            "dari dashboard bisnis lengkap Warungio."
        ),
        "schema_type": "WebPage",
        "noindex": True,
        "breadcrumbs": [("Beranda", "/"), ("Masuk", "/auth/login/")],
    },
    "/auth/login-seller/": {
        "meta_title": f"Login Mitra Seller - {SITE_NAME} Bisnis UMKM",
        "meta_description": (
            "Login ke dashboard seller Warungio untuk mengelola toko, produk, "
            "pesanan, stok barang, laporan keuangan, dan analisis penjualan. "
            "Akses sistem POS kasir digital, manajemen inventaris real-time, "
            "manajemen supplier, dan fitur manajemen pelanggan. Pantau performa "
            "bisnis UMKM Anda dan jangkau lebih banyak pelanggan."
        ),
        "schema_type": "WebPage",
        "noindex": True,
        "breadcrumbs": [("Beranda", "/"), ("Login Seller", "/auth/login-seller/")],
    },
    "/auth/register/": {
        "meta_title": f"Daftar Akun Baru - {SITE_NAME} Marketplace & Bisnis",
        "meta_description": (
            "Daftar akun Warungio gratis sekarang! Pembeli: nikmati kemudahan "
            "belanja kebutuhan harian, sembako, sayur segar, dan buah segar dari "
            "warung terdekat dengan pengiriman cepat. Pemilik UMKM: dapatkan akses "
            "aplikasi stok barang gratis, POS kasir digital, dan dashboard "
            "manajemen bisnis lengkap untuk mengembangkan usaha Anda."
        ),
        "schema_type": "WebPage",
        "noindex": True,
        "breadcrumbs": [("Beranda", "/"), ("Daftar", "/auth/register/")],
    },
    "/auth/register-mitra/": {
        "meta_title": f"Daftar Mitra Seller - {SITE_NAME} Digitalisasi UMKM",
        "meta_description": (
            "Gabung menjadi mitra seller Warungio dan digitalisasikan bisnis UMKM "
            "Anda. Dapatkan aplikasi stok barang gratis, sistem POS kasir digital, "
            "manajemen inventaris real-time, laporan keuangan dan penjualan berbasis "
            "AI, manajemen supplier, dan fitur manajemen pelanggan. Jangkau lebih "
            "banyak pelanggan, kelola pesanan dengan mudah, dan tingkatkan omzet "
            "hingga 3x lipat. Daftar gratis sekarang!"
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
        "meta_title": f"Tentang {SITE_NAME} - Ekosistem Marketplace & Manajemen Bisnis UMKM",
        "meta_description": (
            "Warungio adalah ekosistem all-in-one yang menggabungkan marketplace "
            "hyperlocal dengan sistem manajemen bisnis UMKM terlengkap. Kami "
            "memberdayakan jutaan warung tradisional Indonesia melalui aplikasi stok "
            "barang gratis, POS kasir digital, manajemen inventaris real-time, "
            "laporan keuangan dan analisis penjualan berbasis AI, manajemen supplier, "
            "serta manajemen pelanggan. Untuk pembeli, nikmati belanja kebutuhan "
            "harian, sembako, sayur segar, dan buah segar dari warung terdekat "
            "dengan pengiriman cepat. Visi kami: digitalisasi UMKM Indonesia."
        ),
        "schema_type": "AboutPage",
        "breadcrumbs": [("Beranda", "/"), ("Tentang Kami", "/info/tentang-kami/")],
    },
    "/info/cara-belanja/": {
        "meta_title": f"Cara Belanja di {SITE_NAME} & Cara Jadi Mitra Seller",
        "meta_description": (
            "Panduan lengkap menggunakan Warungio. Untuk pembeli: cara belanja "
            "kebutuhan harian, sembako, sayur segar, buah segar, dari warung "
            "terdekat dengan berbagai metode pembayaran (QRIS, GoPay, OVO, transfer "
            "bank, COD). Untuk pemilik UMKM: cara mendaftar sebagai mitra seller, "
            "menggunakan aplikasi stok barang gratis, POS kasir digital, manajemen "
            "inventaris, dan fitur manajemen bisnis lengkap Warungio."
        ),
        "schema_type": "WebPage",
        "breadcrumbs": [("Beranda", "/"), ("Cara Belanja", "/info/cara-belanja/")],
    },
    "/info/metode-pembayaran/": {
        "meta_title": f"Metode Pembayaran Marketplace & Bisnis - {SITE_NAME}",
        "meta_description": (
            "Warungio mendukung berbagai metode pembayaran aman dan praktis: "
            "transfer bank (BCA, Mandiri, BRI, BNI), e-wallet (GoPay, OVO, DANA, "
            "ShopeePay), QRIS, kartu kredit/debit (Visa, Mastercard, JCB), dan "
            "COD. Untuk mitra seller: nikmati pencairan dana otomatis, laporan "
            "transaksi real-time, dan rekonsiliasi pembayaran terintegrasi dengan "
            "sistem POS dan manajemen keuangan Warungio. Semua pembayaran diproses "
            "melalui Midtrans dengan enkripsi keamanan tinggi."
        ),
        "schema_type": "WebPage",
        "breadcrumbs": [("Beranda", "/"), ("Metode Pembayaran", "/info/metode-pembayaran/")],
    },
    "/info/kontak-kami/": {
        "meta_title": f"Hubungi Kami - {SITE_NAME} Marketplace & Bisnis UMKM",
        "meta_description": (
            "Hubungi tim customer service Warungio melalui email, telepon, WhatsApp, "
            "atau kunjungi kantor pusat. Kami siap membantu Anda 24/7 untuk "
            "pertanyaan tentang pesanan, pembayaran, pengiriman, pendaftaran mitra "
            "seller, penggunaan aplikasi stok barang, POS kasir digital, manajemen "
            "inventaris, laporan keuangan, dan fitur manajemen bisnis Warungio."
        ),
        "schema_type": "ContactPage",
        "breadcrumbs": [("Beranda", "/"), ("Hubungi Kami", "/info/kontak-kami/")],
    },
    "/info/kebijakan/": {
        "meta_title": f"Kebijakan & Ketentuan - {SITE_NAME} Marketplace & Bisnis",
        "meta_description": (
            "Syarat dan ketentuan penggunaan platform Warungio baik sebagai "
            "marketplace hyperlocal untuk belanja kebutuhan harian maupun sebagai "
            "sistem manajemen bisnis UMKM. Pelajari ketentuan penggunaan aplikasi "
            "stok barang, POS kasir digital, layanan marketplace, kebijakan privasi, "
            "pembayaran dan refund untuk pembeli dan mitra seller."
        ),
        "schema_type": "WebPage",
        "breadcrumbs": [("Beranda", "/"), ("Kebijakan", "/info/kebijakan/")],
    },
    "/info/blog/": {
        "meta_title": f"Blog {SITE_NAME} - Tips Belanja & Panduan Bisnis UMKM",
        "meta_description": (
            "Baca artikel tips belanja hemat, resep masak, panduan bisnis UMKM, "
            "cara menggunakan aplikasi stok barang gratis, tips manajemen inventaris, "
            "strategi pemasaran untuk warung, dan informasi terbaru seputar Warungio. "
            "Dapatkan inspirasi mengelola bisnis dan belanja kebutuhan harian dengan "
            "lebih cerdas bersama Warungio."
        ),
        "schema_type": "Blog",
        "breadcrumbs": [("Beranda", "/"), ("Blog", "/info/blog/")],
    },
    "/info/panduan-seller/": {
        "meta_title": f"Panduan Seller - {SITE_NAME} Manajemen Bisnis UMKM",
        "meta_description": (
            "Panduan lengkap untuk mitra seller Warungio. Pelajari cara menggunakan "
            "aplikasi stok barang gratis, sistem POS kasir digital, manajemen "
            "inventaris real-time, laporan keuangan dan penjualan berbasis AI, "
            "manajemen supplier, pencairan dana, serta tips sukses berjualan dan "
            "mengembangkan bisnis UMKM Anda di platform Warungio."
        ),
        "schema_type": "WebPage",
        "breadcrumbs": [("Beranda", "/"), ("Panduan Seller", "/info/panduan-seller/")],
    },
    "/info/komunitas/": {
        "meta_title": f"Komunitas Seller & UMKM - {SITE_NAME}",
        "meta_description": (
            "Bergabung dengan komunitas seller Warungio di seluruh Indonesia. "
            "Diskusikan strategi bisnis, tips menggunakan aplikasi stok barang, "
            "POS kasir digital, manajemen inventaris, dan pengelolaan keuangan "
            "UMKM. Dapatkan tips sukses, ikuti webinar eksklusif, dan kembangkan "
            "usaha Anda bersama ribuan mitra Warungio."
        ),
        "schema_type": "WebPage",
        "breadcrumbs": [("Beranda", "/"), ("Komunitas Seller", "/info/komunitas/")],
    },
    "/info/tips-sukses/": {
        "meta_title": f"Tips Sukses UMKM & Manajemen Toko - {SITE_NAME}",
        "meta_description": (
            "Kumpulan tips sukses untuk mitra seller Warungio. Pelajari strategi "
            "manajemen inventaris dan stok barang, penggunaan POS kasir digital, "
            "analisis laporan keuangan dan penjualan berbasis AI, manajemen "
            "supplier, foto produk berkualitas, pemanfaatan promo, dan cara "
            "mengembangkan toko UMKM Anda di platform Warungio."
        ),
        "schema_type": "WebPage",
        "breadcrumbs": [("Beranda", "/"), ("Tips Sukses", "/info/tips-sukses/")],
    },
    # ── Bantuan / Help Center ──
    "/bantuan/": {
        "meta_title": f"Pusat Bantuan - {SITE_NAME} Marketplace & Manajemen Bisnis",
        "meta_description": (
            "Pusat bantuan Warungio. Temukan jawaban seputar belanja kebutuhan "
            "harian, cara menggunakan aplikasi stok barang gratis, POS kasir "
            "digital, manajemen inventaris, laporan keuangan, pesanan, pembayaran, "
            "pengiriman, refund, dan fitur manajemen bisnis UMKM. Hubungi tim "
            "customer service kami yang siap membantu 24/7."
        ),
        "schema_type": "FAQPage",
        "breadcrumbs": [("Beranda", "/"), ("Bantuan", "/bantuan/")],
    },
    # ── Download Page ──
    "/download/": {
        "meta_title": f"Download Aplikasi {SITE_NAME} - Marketplace & Manajemen Bisnis",
        "meta_description": (
            "Download aplikasi Warungio gratis! Untuk pembeli: belanja kebutuhan "
            "harian, sembako, sayur segar, buah, daging dari warung terdekat. "
            "Untuk pemilik UMKM: aplikasi stok barang gratis, POS kasir digital, "
            "manajemen inventaris real-time, laporan keuangan berbasis AI, dan "
            "manajemen pelanggan. Tersedia untuk Android APK."
        ),
        "schema_type": "WebPage",
        "breadcrumbs": [("Beranda", "/"), ("Download", "/download/")],
    },
    # ── Buyer Dashboard ──
    "/buyer/dashboard/": {
        "meta_title": f"Dashboard Pembeli - {SITE_NAME} Marketplace",
        "meta_description": "Dashboard pembeli Warungio. Kelola profil, pantau pesanan, dan temukan rekomendasi warung dan UMKM terdekat.",
        "schema_type": "WebPage",
        "noindex": True,
    },
    "/buyer/home/": {
        "meta_title": f"Marketplace {SITE_NAME} - Belanja dari Warung & UMKM Terdekat",
        "meta_description": "Temukan warung terdekat, produk segar pilihan, sembako murah, dan promo terbaik hari ini di marketplace hyperlocal Warungio.",
        "schema_type": "WebPage",
        "noindex": True,
    },
    # ── Products ──
    "/buyer/products/": {
        "meta_title": f"Semua Produk Segar & Sembako | {SITE_NAME} Marketplace",
        "meta_description": "Jelajahi semua produk segar, sembako, sayuran, buah, daging, dan kebutuhan harian dari warung dan UMKM terdekat di marketplace hyperlocal Warungio.",
        "schema_type": "CollectionPage",
        "noindex": True,
    },
    # ── Seller Pages ──
    "/seller/dashboard/": {
        "meta_title": f"Dashboard Seller - {SITE_NAME} Manajemen Bisnis UMKM",
        "meta_description": "Dashboard seller Warungio. Kelola toko, pantau stok barang real-time, proses pesanan, akses laporan keuangan dan penjualan berbasis AI, manajemen supplier, dan fitur manajemen bisnis UMKM lengkap.",
        "schema_type": "WebPage",
        "noindex": True,
    },
    "/seller/products/": {
        "meta_title": f"Produk Saya - {SITE_NAME} Manajemen Inventaris",
        "meta_description": "Kelola stok barang, tambah produk baru, edit harga, dan atur kategori produk toko UMKM Anda dengan aplikasi manajemen inventaris Warungio.",
        "schema_type": "WebPage",
        "noindex": True,
    },
    "/seller/orders/": {
        "meta_title": f"Pesanan Masuk - {SITE_NAME} POS & Manajemen Pesanan",
        "meta_description": "Proses dan kelola pesanan pelanggan dengan sistem POS kasir digital Warungio. Pantau status pesanan real-time, cetak struk, dan atur pengiriman.",
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
        if path == "/kategori/":
            seo = {
                "meta_title": f"Semua Kategori Produk | {SITE_NAME} Marketplace & Manajemen Bisnis",
                "meta_description": f"Jelajahi semua kategori produk di {SITE_NAME}: sayuran segar, buah segar, \nsembako, daging, dan kebutuhan rumah tangga. Untuk pemilik UMKM: gunakan \naplikasi stok barang gratis dan POS kasir digital Warungio untuk mengelola \nusaha Anda. Belanja dan kelola bisnis dalam satu platform.",
                "schema_type": "CollectionPage",
                "noindex": False,
            }
        elif path == "/kota/":
            seo = {
                "meta_title": f"Belanja & Bisnis di Kota Anda | {SITE_NAME} Ekosistem UMKM",
                "meta_description": f"Temukan warung dan UMKM lokal di kota Anda melalui {SITE_NAME}. \nPembeli: belanja kebutuhan harian, sembako, sayur segar dari warung terdekat. \nPemilik usaha: kelola toko dengan aplikasi stok barang gratis, POS kasir digital, \ndan laporan keuangan berbasis AI.",
                "schema_type": "CollectionPage",
                "noindex": False,
            }
        elif path.startswith("/bantuan/artikel/"):
            seo = {
                "meta_title": f"Artikel Bantuan - {SITE_NAME} Marketplace & Manajemen Bisnis",
                "meta_description": "Baca artikel panduan Warungio: cara belanja kebutuhan harian, menggunakan aplikasi stok barang gratis, POS kasir digital, manajemen inventaris, laporan keuangan, dan fitur manajemen bisnis UMKM.",
                "schema_type": "Article",
                "noindex": False,
            }
        elif path.startswith("/products/"):
            seo = {
                "meta_title": f"Detail Produk - {SITE_NAME} Marketplace",
                "meta_description": "Lihat detail produk segar, sembako, dan kebutuhan harian dari warung terdekat. Untuk pemilik UMKM: gunakan aplikasi stok barang Warungio untuk mengelola inventaris dan penjualan Anda.",
                "schema_type": "Product",
                "noindex": True,
            }
        elif path.startswith("/buyer/"):
            seo = {
                "meta_title": f"Akun Pembeli - {SITE_NAME} Marketplace",
                "meta_description": "Kelola akun pembeli Warungio Anda: pantau pesanan, kelola alamat, lihat riwayat transaksi, dan temukan promo belanja kebutuhan harian dari warung terdekat.",
                "schema_type": "WebPage",
                "noindex": True,
            }
        elif path.startswith("/seller/"):
            seo = {
                "meta_title": f"Dashboard Seller - {SITE_NAME} Manajemen Bisnis UMKM",
                "meta_description": "Kelola bisnis UMKM Anda di dashboard seller Warungio: POS kasir digital, aplikasi stok barang gratis, manajemen inventaris real-time, laporan keuangan dan penjualan berbasis AI, manajemen supplier, dan manajemen pelanggan.",
                "schema_type": "WebPage",
                "noindex": True,
            }
        elif path.startswith("/admin-panel/"):
            seo = {
                "meta_title": f"Admin Panel - {SITE_NAME}",
                "meta_description": "Panel administrasi Warungio. Kelola pengguna, transaksi, dan pengaturan platform marketplace hyperlocal dan sistem manajemen bisnis UMKM.",
                "schema_type": "WebPage",
                "noindex": True,
            }
        elif path.startswith("/kategori/"):
            category_name = path.split('/')[-2].replace('-', ' ').title()
            seo = {
                "meta_title": f"Jual & Beli {category_name} Segar Online | {SITE_NAME}",
                "meta_description": f"Pembeli: beli {path.split('/')[-2].replace('-', ' ')} segar online dari warung dan UMKM \nterdekat dengan harga terjangkau. Pemilik UMKM: kelola stok dan penjualan \n{path.split('/')[-2].replace('-', ' ')} Anda dengan aplikasi stok barang gratis dan \nPOS kasir digital Warungio.",
                "schema_type": "CollectionPage",
                "noindex": False,
            }
        elif path.startswith("/kota/"):
            city_name = path.split('/')[-2].replace('-', ' ').title()
            seo = {
                "meta_title": f"Belanja & Bisnis UMKM di {city_name} | {SITE_NAME}",
                "meta_description": f"Nikmati {SITE_NAME} di {city_name}! Pembeli: belanja kebutuhan harian, \nsembako, sayur segar, buah segar dari warung terdekat. Pemilik usaha: digitalisasikan \ntoko Anda dengan aplikasi stok barang gratis, POS kasir digital, \ndan laporan keuangan berbasis AI dari {SITE_NAME}.",
                "schema_type": "CollectionPage",
                "noindex": False,
            }
        elif path.startswith("/toko/"):
            store_name = path.split('/')[-2].replace('-', ' ').title()
            seo = {
                "meta_title": f"{store_name} - Toko UMKM di {SITE_NAME}",
                "meta_description": f"Kunjungi {store_name} di {SITE_NAME} dan temukan produk segar, \nsembako, dan kebutuhan harian berkualitas. Pemilik toko: kelola stok barang, \npesanan, dan laporan penjualan dengan aplikasi stok barang gratis dan POS \nkasir digital dari {SITE_NAME}.",
                "schema_type": "Store",
                "noindex": False,
            }
        elif path.startswith("/produk/"):
            product_name = path.split('/')[-2].replace('-', ' ').title()
            seo = {
                "meta_title": f"{product_name} - Harga & Review | {SITE_NAME}",
                "meta_description": f"Beli {path.split('/')[-2].replace('-', ' ')} dengan harga terbaik di {SITE_NAME}. \nPembeli: dapatkan produk segar dari warung terdekat dengan pengiriman cepat. \nPemilik UMKM: gunakan aplikasi stok barang dan POS kasir digital Warungio \nuntuk mengelola penjualan produk Anda.",
                "schema_type": "Product",
                "noindex": False,
            }
        elif path.startswith("/promo/"):
            promo_name = path.split('/')[-2].replace('-', ' ').title()
            seo = {
                "meta_title": f"{promo_name} - Promo {SITE_NAME} Marketplace & Bisnis",
                "meta_description": f"Dapatkan promo dan diskon terbaik di {SITE_NAME}! Pembeli: \nnikmati diskon belanja kebutuhan harian, sembako, sayur segar, gratis ongkir, \ndan cashback. Pemilik UMKM: buat promo toko Anda sendiri dan pantau \nperforma dengan laporan penjualan dan analisis bisnis Warungio.",
                "schema_type": "WebPage",
                "noindex": False,
            }
        elif path.startswith("/auth/"):
            seo = {
                "meta_title": f"Autentikasi - {SITE_NAME} Marketplace & Bisnis UMKM",
                "meta_description": "Masuk atau daftar akun Warungio untuk mulai belanja kebutuhan harian dari warung terdekat atau mengelola bisnis UMKM Anda dengan aplikasi stok barang gratis dan POS kasir digital.",
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
        "google_site_verification": getattr(settings, 'GOOGLE_SITE_VERIFICATION', ''),
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

    # 5. LocalBusiness (only for Landing, About, Contact pages)
    if schema_type in ("ContactPage", "AboutPage", "WebPage") and url == _build_absolute_url("/"):
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

    # 6. MobileApplication (only on landing page and download page)
    if url in (_build_absolute_url("/"), _build_absolute_url("/download/")):
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
