"""
Management command to seed initial help center data.
Run: python manage.py seed_help_data
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from support.models import (
    HelpCategory, HelpArticle, FAQ, BannerPromo,
    ContactInfo, SupportInfo, ChatQuickReply
)


class Command(BaseCommand):
    help = 'Seed initial data for Bantuan & Chat Customer Service'

    def handle(self, *args, **options):
        self.stdout.write('Seeding help center data...')

        # === Support Info Cards ===
        infos = [
            {'key': 'fast_response', 'title': 'Respon Cepat', 'description': 'Tim kami merespon dalam hitungan menit', 'sort_order': 1},
            {'key': 'right_solution', 'title': 'Solusi Tepat', 'description': 'Setiap masalah pasti ada solusinya', 'sort_order': 2},
            {'key': 'available_24_7', 'title': '24/7 Siap Membantu', 'description': 'Layanan pelanggan non-stop setiap hari', 'sort_order': 3},
            {'key': 'data_safe', 'title': 'Data Aman', 'description': 'Data pribadi Anda terlindungi dengan aman', 'sort_order': 4},
        ]
        for info in infos:
            SupportInfo.objects.update_or_create(key=info['key'], defaults=info)
        self.stdout.write(f'  [OK] {len(infos)} support info cards created')

        # === Help Categories ===
        categories = [
            {'name': 'Pesanan', 'slug': 'pesanan', 'icon': 'package', 'description': 'Info seputar pesanan dan pengiriman', 'sort_order': 1},
            {'name': 'Pembayaran', 'slug': 'pembayaran', 'icon': 'payment', 'description': 'Metode dan masalah pembayaran', 'sort_order': 2},
            {'name': 'Akun', 'slug': 'akun', 'icon': 'user', 'description': 'Pengelolaan akun dan profil', 'sort_order': 3},
            {'name': 'Promo', 'slug': 'promo', 'icon': 'tag', 'description': 'Promo, voucher, dan diskon', 'sort_order': 4},
            {'name': 'Pengiriman', 'slug': 'pengiriman', 'icon': 'truck', 'description': 'Informasi pengiriman dan tracking', 'sort_order': 5},
            {'name': 'Pengembalian', 'slug': 'pengembalian', 'icon': 'refresh', 'description': 'Pengembalian barang dan refund', 'sort_order': 6},
        ]
        created_cats = []
        for cat in categories:
            obj, _ = HelpCategory.objects.update_or_create(slug=cat['slug'], defaults=cat)
            created_cats.append(obj)
        self.stdout.write(f'  [OK] {len(categories)} help categories created')

        # === Help Articles ===
        articles = [
            {
                'category_slug': 'pesanan',
                'title': 'Cara Melacak Pesanan',
                'slug': 'cara-melacak-pesanan',
                'content': '<p>Untuk melacak pesanan Anda di Warungio, ikuti langkah-langkah berikut:</p>\n<ol>\n<li>Buka aplikasi Warungio dan masuk ke akun Anda</li>\n<li>Tap menu "Pesanan Saya" di halaman utama</li>\n<li>Pilih pesanan yang ingin dilacak</li>\n<li>Lihat status terbaru pesanan Anda</li>\n</ol>\n<p>Status pesanan akan diperbarui secara realtime. Anda juga akan mendapatkan notifikasi setiap ada perubahan status.</p>\n<h3>Status Pesanan:</h3>\n<ul>\n<li><strong>Menunggu Pembayaran</strong> - Pesanan belum dibayar</li>\n<li><strong>Diproses</strong> - Penjual sedang menyiapkan pesanan</li>\n<li><strong>Dikirim</strong> - Pesanan sudah dalam perjalanan</li>\n<li><strong>Selesai</strong> - Pesanan sudah diterima</li>\n</ul>',
                'excerpt': 'Panduan lengkap cara melacak status pesanan Anda di Warungio secara realtime.',
                'is_featured': True,
                'views_count': 1250,
            },
            {
                'category_slug': 'pembayaran',
                'title': 'Metode Pembayaran',
                'slug': 'metode-pembayaran',
                'content': '<p>Warungio mendukung berbagai metode pembayaran untuk memudahkan Anda berbelanja:</p>\n<h3>Pembayaran Tunai (COD)</h3>\n<p>Bayar langsung saat pesanan diterima. Tersedia di wilayah tertentu.</p>\n<h3>Transfer Bank</h3>\n<ul>\n<li>BNI</li>\n<li>BRI</li>\n<li>Mandiri</li>\n<li>BCA</li>\n</ul>\n<h3>E-Wallet</h3>\n<ul>\n<li>GoPay</li>\n<li>OVO</li>\n<li>Dana</li>\n<li>LinkAja</li>\n</ul>\n<h3>QRIS</h3>\n<p>Bayar menggunakan QRIS dari aplikasi pembayaran favorit Anda.</p>',
                'excerpt': 'Berbagai metode pembayaran yang bisa Anda gunakan di Warungio.',
                'is_featured': True,
                'views_count': 980,
            },
            {
                'category_slug': 'pengembalian',
                'title': 'Pengembalian Barang',
                'slug': 'pengembalian-barang',
                'content': '<p>Jika Anda menerima barang yang tidak sesuai, Anda dapat mengajukan pengembalian dengan ketentuan berikut:</p>\n<h3>Syarat Pengembalian:</h3>\n<ul>\n<li>Pengajuan maksimal 3 hari setelah barang diterima</li>\n<li>Barang dalam kondisi masih baik dan belum digunakan</li>\n<li>Menyertakan bukti foto atau video</li>\n</ul>\n<h3>Cara Mengajukan:</h3>\n<ol>\n<li>Buka halaman detail pesanan</li>\n<li>Pilih "Ajukan Pengembalian"</li>\n<li>Lengkapi formulir dan upload bukti</li>\n<li>Tunggu konfirmasi dari tim kami (maksimal 2x24 jam)</li>\n</ol>',
                'excerpt': 'Syarat, ketentuan, dan cara mengajukan pengembalian barang di Warungio.',
                'is_featured': True,
                'views_count': 750,
            },
            {
                'category_slug': 'promo',
                'title': 'Promo & Voucher',
                'slug': 'promo-dan-voucher',
                'content': '<p>Dapatkan berbagai promo dan voucher menarik di Warungio!</p>\n<h3>Jenis Promo:</h3>\n<ul>\n<li><strong>Diskon Produk</strong> - Potongan harga langsung untuk produk tertentu</li>\n<li><strong>Voucher Gratis Ongkir</strong> - Bebas biaya pengiriman</li>\n<li><strong>Cashback</strong> - Dapatkan kembali sebagian dari pembayaran</li>\n<li><strong>Promo Spesial</strong> - Promo waktu terbatas di hari-hari tertentu</li>\n</ul>\n<p>Pantau selalu halaman Promo di aplikasi Warungio untuk informasi promo terbaru!</p>',
                'excerpt': 'Info lengkap tentang promo, voucher, dan cashback yang tersedia di Warungio.',
                'views_count': 620,
            },
            {
                'category_slug': 'akun',
                'title': 'Cara Mendaftar Akun Warungio',
                'slug': 'cara-mendaftar-akun',
                'content': '<p>Bergabung dengan Warungio sangat mudah! Ikuti langkah-langkah berikut:</p>\n<ol>\n<li>Buka aplikasi atau website Warungio</li>\n<li>Klik "Daftar" di halaman utama</li>\n<li>Masukkan nama lengkap, email, dan nomor HP</li>\n<li>Buat kata sandi yang kuat</li>\n<li>Verifikasi akun melalui kode OTP yang dikirim ke email/HP</li>\n<li>Akun Anda siap digunakan!</li>\n</ol>\n<p>Setelah mendaftar, Anda bisa langsung berbelanja atau mendaftar sebagai mitra penjual.</p>',
                'excerpt': 'Panduan langkah demi langkah untuk mendaftar akun Warungio.',
                'views_count': 540,
            },
            {
                'category_slug': 'pengiriman',
                'title': 'Biaya dan Waktu Pengiriman',
                'slug': 'biaya-waktu-pengiriman',
                'content': '<p>Warungio bekerja sama dengan berbagai mitra pengiriman untuk memastikan pesanan Anda sampai dengan aman dan tepat waktu.</p>\n<h3>Mitra Pengiriman:</h3>\n<ul>\n<li>Indrive</li>\n<li>Maxxim</li>\n<li>Grab</li>\n<li>GoSend</li>\n</ul>\n<h3>Estimasi Waktu:</h3>\n<ul>\n<li><strong>Same Day</strong> - Sampai di hari yang sama (1-6 jam)</li>\n<li><strong>Next Day</strong> - Sampai keesokan harinya</li>\n<li><strong>Reguler</strong> - 2-3 hari kerja</li>\n</ul>\n<p>Biaya pengiriman dihitung berdasarkan jarak dan berat pesanan.</p>',
                'excerpt': 'Informasi biaya pengiriman, estimasi waktu, dan mitra pengiriman Warungio.',
                'views_count': 430,
            },
        ]
        for art in articles:
            cat = HelpCategory.objects.filter(slug=art['category_slug']).first()
            if cat:
                HelpArticle.objects.update_or_create(
                    slug=art['slug'],
                    defaults={
                        'category': cat,
                        'title': art['title'],
                        'content': art['content'],
                        'excerpt': art['excerpt'],
                        'is_featured': art.get('is_featured', False),
                        'views_count': art.get('views_count', 0),
                        'is_published': True,
                        'published_at': timezone.now(),
                    }
                )
        self.stdout.write(f'  [OK] {len(articles)} articles created')

        # === FAQs ===
        faqs = [
            {'question': 'Apakah Warungio melayani pengiriman ke seluruh Indonesia?', 'answer': 'Saat ini Warungio melayani pengiriman di kota-kota besar di Indonesia. Kami terus memperluas jangkauan pengiriman ke lebih banyak wilayah.', 'category_slug': 'pengiriman', 'sort_order': 1},
            {'question': 'Bagaimana cara membatalkan pesanan?', 'answer': 'Anda dapat membatalkan pesanan sebelum pesanan diproses oleh penjual.', 'category_slug': 'pesanan', 'sort_order': 2},
            {'question': 'Berapa lama proses refund?', 'answer': 'Proses refund biasanya memakan waktu 3-7 hari kerja tergantung metode pembayaran yang digunakan.', 'category_slug': 'pengembalian', 'sort_order': 3},
            {'question': 'Bagaimana cara menjadi mitra penjual di Warungio?', 'answer': 'Untuk menjadi mitra penjual, daftar melalui halaman "Daftar Mitra" di aplikasi atau website.', 'category_slug': 'akun', 'sort_order': 4},
            {'question': 'Apa itu kode OTP dan bagaimana cara mendapatkannya?', 'answer': 'Kode OTP adalah kode verifikasi 6 digit yang dikirim ke email atau nomor HP Anda.', 'category_slug': 'akun', 'sort_order': 5},
            {'question': 'Apakah ada biaya tambahan untuk layanan COD?', 'answer': 'Tidak ada biaya tambahan untuk pembayaran COD. Anda hanya membayar sesuai total belanja yang tertera.', 'category_slug': 'pembayaran', 'sort_order': 6},
        ]
        for faq in faqs:
            cat = HelpCategory.objects.filter(slug=faq['category_slug']).first()
            FAQ.objects.update_or_create(
                question=faq['question'],
                defaults={
                    'answer': faq['answer'],
                    'category': cat,
                    'sort_order': faq['sort_order'],
                    'is_published': True,
                }
            )
        self.stdout.write(f'  [OK] {len(faqs)} FAQs created')

        # === Contact Info ===
        contacts = [
            {'contact_type': 'whatsapp', 'label': 'Chat WhatsApp', 'value': '+6281234567890', 'operating_hours': '24 jam, 7 hari seminggu', 'sort_order': 1},
            {'contact_type': 'email', 'label': 'Email Support', 'value': 'support@warungio.com', 'operating_hours': 'Senin - Jumat, 08:00 - 20:00', 'sort_order': 2},
            {'contact_type': 'phone', 'label': 'Telepon', 'value': '+62211234567', 'operating_hours': 'Senin - Sabtu, 08:00 - 18:00', 'sort_order': 3},
            {'contact_type': 'instagram', 'label': 'Instagram', 'value': 'warungio', 'operating_hours': 'Media sosial', 'sort_order': 4},
        ]
        for contact in contacts:
            ContactInfo.objects.update_or_create(
                contact_type=contact['contact_type'],
                defaults=contact
            )
        self.stdout.write(f'  [OK] {len(contacts)} contacts created')

        # === Banner Promo ===
        banner, _ = BannerPromo.objects.update_or_create(
            title='Belanja Hemat di Warungio',
            defaults={
                'subtitle': 'Dapatkan promo spesial setiap hari untuk kebutuhan dapur Anda!',
                'link_url': '/products/',
                'link_text': 'Belanja Sekarang',
                'position': 'help_bottom',
                'is_active': True,
            }
        )
        self.stdout.write(f'  [OK] Banner promo created: {banner.title}')

        # === Chat Quick Replies ===
        replies = [
            {'category': 'order', 'label': 'Status Pesanan', 'message_template': 'Halo admin, saya ingin menanyakan status pesanan saya. Nomor pesanan: [No. Pesanan]', 'sort_order': 1},
            {'category': 'payment', 'label': 'Pembayaran', 'message_template': 'Halo admin, saya ingin bertanya tentang pembayaran.', 'sort_order': 2},
            {'category': 'return', 'label': 'Pengembalian Barang', 'message_template': 'Halo admin, saya ingin mengajukan pengembalian barang.', 'sort_order': 3},
            {'category': 'other', 'label': 'Lainnya', 'message_template': 'Halo admin, saya ingin bertanya tentang Warungio.', 'sort_order': 4},
        ]
        for reply in replies:
            ChatQuickReply.objects.update_or_create(
                category=reply['category'],
                label=reply['label'],
                defaults=reply
            )
        self.stdout.write(f'  [OK] {len(replies)} quick replies created')

        self.stdout.write('\nSeed data berhasil dibuat!')
        self.stdout.write('Login admin: http://localhost:8000/admin/')
        self.stdout.write('Halaman bantuan: http://localhost:8000/bantuan/')
