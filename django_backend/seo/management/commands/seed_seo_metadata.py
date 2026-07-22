"""
Management command to seed initial SEO metadata records.
Populates the SeoMetadata model for all public SEO landing pages.

Usage:
    python manage.py seed_seo_metadata
    python manage.py seed_seo_metadata --force  # Overwrite existing records
"""

from django.core.management.base import BaseCommand

SITE_NAME = "Warungio"
SITE_URL = "https://warungio.web.id"


# ── SEO Metadata definitions ──
# Each entry: (path, title, description, schema_type, noindex, breadcrumb_json)
SEO_ENTRIES = [
    # ── Landing / Core ──
    ("/", (
        f"{SITE_NAME} - Ekosistem Marketplace Hyperlocal & Manajemen Bisnis UMKM",
        "Warungio adalah platform all-in-one yang menggabungkan marketplace "
        "hyperlocal dengan sistem manajemen bisnis UMKM terlengkap. Untuk "
        "pembeli: belanja kebutuhan harian, sembako, sayur segar, buah segar, "
        "daging dari warung terdekat. Untuk pemilik usaha: POS kasir digital "
        "gratis, aplikasi stok barang, manajemen inventaris real-time, laporan "
        "keuangan dan penjualan berbasis AI, manajemen supplier, dan manajemen "
        "pelanggan. Digitalisasi warung Indonesia.",
        "WebPage", False,
        '[{"label":"Beranda","url":"/"}]'
    )),
    ("/kategori/", (
        f"Semua Kategori Produk | {SITE_NAME} Marketplace & Manajemen Bisnis",
        "Jelajahi semua kategori produk di Warungio: sayuran segar, buah segar, "
        "sembako, daging, dan kebutuhan rumah tangga. Untuk pemilik UMKM: "
        "gunakan aplikasi stok barang gratis dan POS kasir digital Warungio "
        "untuk mengelola inventaris dan penjualan Anda.",
        "CollectionPage", False,
        '[{"label":"Beranda","url":"/"},{"label":"Kategori","url":"/kategori/"}]'
    )),
    ("/kota/", (
        f"Belanja & Bisnis UMKM di Kota Anda | {SITE_NAME} Ekosistem UMKM",
        "Temukan warung dan UMKM lokal di kota Anda melalui Warungio. "
        "Pembeli: belanja kebutuhan harian, sembako, sayur segar dari warung "
        "terdekat. Pemilik usaha: digitalisasikan toko Anda dengan aplikasi "
        "stok barang gratis, POS kasir digital, dan laporan keuangan berbasis AI.",
        "CollectionPage", False,
        '[{"label":"Beranda","url":"/"},{"label":"Kota","url":"/kota/"}]'
    )),
    # ── Info Pages ──
    ("/info/tentang-kami/", (
        f"Tentang {SITE_NAME} - Ekosistem Marketplace & Manajemen Bisnis UMKM",
        "Warungio adalah ekosistem all-in-one yang menggabungkan marketplace "
        "hyperlocal dengan sistem manajemen bisnis UMKM terlengkap. Kami "
        "memberdayakan jutaan warung tradisional Indonesia melalui aplikasi stok "
        "barang gratis, POS kasir digital, manajemen inventaris real-time, "
        "laporan keuangan dan analisis penjualan berbasis AI, manajemen supplier, "
        "serta manajemen pelanggan. Untuk pembeli: belanja kebutuhan harian dari "
        "warung terdekat dengan pengiriman cepat.",
        "AboutPage", False,
        '[{"label":"Beranda","url":"/"},{"label":"Tentang Kami","url":"/info/tentang-kami/"}]'
    )),
    ("/info/cara-belanja/", (
        f"Cara Belanja di {SITE_NAME} & Cara Jadi Mitra Seller",
        "Panduan lengkap menggunakan Warungio. Untuk pembeli: cara belanja "
        "kebutuhan harian, sembako, sayur segar dari warung terdekat dengan "
        "QRIS, GoPay, OVO, transfer bank, atau COD. Untuk pemilik UMKM: cara "
        "mendaftar mitra seller, menggunakan aplikasi stok barang gratis, "
        "POS kasir digital, dan fitur manajemen bisnis lengkap Warungio.",
        "WebPage", False,
        '[{"label":"Beranda","url":"/"},{"label":"Cara Belanja","url":"/info/cara-belanja/"}]'
    )),
    ("/info/metode-pembayaran/", (
        f"Metode Pembayaran Marketplace & Bisnis - {SITE_NAME}",
        "Warungio mendukung berbagai metode pembayaran aman: transfer bank "
        "(BCA, Mandiri, BRI, BNI), e-wallet (GoPay, OVO, DANA, ShopeePay), "
        "QRIS, kartu kredit, dan COD. Mitra seller nikmati pencairan dana "
        "otomatis dan laporan transaksi real-time terintegrasi dengan POS dan "
        "manajemen keuangan Warungio. Diproses via Midtrans.",
        "WebPage", False,
        '[{"label":"Beranda","url":"/"},{"label":"Pembayaran","url":"/info/metode-pembayaran/"}]'
    )),
    ("/info/kontak-kami/", (
        f"Hubungi Kami - {SITE_NAME} Marketplace & Bisnis UMKM",
        "Hubungi tim customer service Warungio melalui email, telepon, WhatsApp, "
        "atau kunjungi kantor pusat. Kami siap membantu 24/7 untuk pertanyaan "
        "tentang belanja, aplikasi stok barang, POS kasir digital, manajemen "
        "inventaris, laporan keuangan, dan fitur manajemen bisnis Warungio.",
        "ContactPage", False,
        '[{"label":"Beranda","url":"/"},{"label":"Kontak","url":"/info/kontak-kami/"}]'
    )),
    ("/info/kebijakan/", (
        f"Kebijakan & Ketentuan - {SITE_NAME} Marketplace & Bisnis",
        "Syarat dan ketentuan penggunaan platform Warungio baik sebagai "
        "marketplace hyperlocal untuk belanja kebutuhan harian maupun sebagai "
        "sistem manajemen bisnis UMKM. Pelajari ketentuan aplikasi stok barang, "
        "POS kasir digital, kebijakan privasi, pembayaran dan refund.",
        "WebPage", False,
        '[{"label":"Beranda","url":"/"},{"label":"Kebijakan","url":"/info/kebijakan/"}]'
    )),
    ("/info/blog/", (
        f"Blog {SITE_NAME} - Tips Belanja & Panduan Bisnis UMKM",
        "Baca artikel tips belanja hemat, resep masak, panduan bisnis UMKM, "
        "cara menggunakan aplikasi stok barang gratis, tips manajemen inventaris, "
        "strategi pemasaran warung, dan informasi terbaru seputar Warungio. "
        "Dapatkan inspirasi mengelola bisnis dan belanja lebih cerdas.",
        "Blog", False,
        '[{"label":"Beranda","url":"/"},{"label":"Blog","url":"/info/blog/"}]'
    )),
    ("/info/panduan-seller/", (
        f"Panduan Seller - {SITE_NAME} Manajemen Bisnis UMKM",
        "Panduan lengkap untuk mitra seller Warungio. Pelajari cara menggunakan "
        "aplikasi stok barang gratis, sistem POS kasir digital, manajemen "
        "inventaris real-time, laporan keuangan dan penjualan berbasis AI, "
        "manajemen supplier, pencairan dana, dan tips sukses berjualan "
        "di platform Warungio.",
        "WebPage", False,
        '[{"label":"Beranda","url":"/"},{"label":"Panduan Seller","url":"/info/panduan-seller/"}]'
    )),
    ("/info/komunitas/", (
        f"Komunitas Seller & UMKM - {SITE_NAME}",
        "Bergabung dengan komunitas seller Warungio di seluruh Indonesia. "
        "Diskusikan strategi bisnis, tips aplikasi stok barang, POS kasir "
        "digital, manajemen inventaris, dan pengelolaan keuangan UMKM. "
        "Ikuti webinar eksklusif dan kembangkan usaha bersama ribuan mitra.",
        "WebPage", False,
        '[{"label":"Beranda","url":"/"},{"label":"Komunitas","url":"/info/komunitas/"}]'
    )),
    ("/info/tips-sukses/", (
        f"Tips Sukses UMKM & Manajemen Toko - {SITE_NAME}",
        "Kumpulan tips sukses mitra seller Warungio: strategi manajemen "
        "inventaris dan stok barang, penggunaan POS kasir digital, analisis "
        "laporan keuangan dan penjualan berbasis AI, manajemen supplier, "
        "foto produk, pemanfaatan promo, dan cara mengembangkan UMKM.",
        "WebPage", False,
        '[{"label":"Beranda","url":"/"},{"label":"Tips Sukses","url":"/info/tips-sukses/"}]'
    )),
    # ── Bantuan ──
    ("/bantuan/", (
        f"Pusat Bantuan - {SITE_NAME} Marketplace & Manajemen Bisnis",
        "Pusat bantuan Warungio. Temukan jawaban seputar belanja kebutuhan "
        "harian, cara menggunakan aplikasi stok barang gratis, POS kasir "
        "digital, manajemen inventaris, laporan keuangan, pesanan, pembayaran, "
        "pengiriman, refund, dan fitur manajemen bisnis UMKM. Siap membantu 24/7.",
        "FAQPage", False,
        '[{"label":"Beranda","url":"/"},{"label":"Bantuan","url":"/bantuan/"}]'
    )),
    # ── Download ──
    ("/download/", (
        f"Download Aplikasi {SITE_NAME} - Marketplace & Manajemen Bisnis",
        "Download aplikasi Warungio gratis! Pembeli: belanja kebutuhan harian, "
        "sembako, sayur segar dari warung terdekat. Pemilik UMKM: aplikasi "
        "stok barang gratis, POS kasir digital, manajemen inventaris real-time, "
        "laporan keuangan berbasis AI, dan manajemen pelanggan. Tersedia Android.",
        "WebPage", False,
        '[{"label":"Beranda","url":"/"},{"label":"Download","url":"/download/"}]'
    )),
]


class Command(BaseCommand):
    help = "Seed initial SEO metadata records for all public pages"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing SEO metadata records',
        )

    def handle(self, *args, **options):
        from seo.models import SeoMetadata

        force = options['force']
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for path, (title, description, schema_type, noindex, breadcrumb_json) in SEO_ENTRIES:
            existing = SeoMetadata.objects.filter(path=path).first()

            if existing:
                if force:
                    existing.meta_title = title
                    existing.meta_description = description
                    existing.schema_type = schema_type
                    existing.noindex = noindex
                    existing.breadcrumb_json = breadcrumb_json
                    existing.is_active = True
                    existing.save()
                    updated_count += 1
                else:
                    skipped_count += 1
            else:
                SeoMetadata.objects.create(
                    path=path,
                    meta_title=title,
                    meta_description=description,
                    schema_type=schema_type,
                    noindex=noindex,
                    breadcrumb_json=breadcrumb_json,
                    is_active=True,
                )
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"SEO metadata seed complete: "
            f"{created_count} created, {updated_count} updated, {skipped_count} skipped"
        ))
