"""
Management command to seed test orders with hyperlocal delivery data.
Creates 12 sample orders across all delivery statuses and shipping methods.

Run: python manage.py seed_orders
     python manage.py seed_orders --force  (re-seed)
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import timedelta
import random
import string

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed 12 test orders with various hyperlocal delivery statuses'

    SEED_PREFIX = 'WRG-SEED-'

    # ── Product groupings per store ──
    STORE_PRODUCTS = {
        'Warung Segar Makmur': [
            'Bayam Segar', 'Kangkung Hijau', 'Wortel Import',
            'Tomat Merah', 'Brokoli Fresh', 'Bawang Merah',
            'Cabe Merah Keriting', 'Terong Ungu',
        ],
        'Toko Buah Sehat': [
            'Apel Fuji', 'Pisang Cavendish', 'Jeruk Medan',
            'Anggur Hijau', 'Semangka Merah', 'Alpukat Mentega',
            'Mangga Harum Manis',
        ],
        'Sembako Hemat Jaya': [
            'Beras Premium 5kg', 'Minyak Goreng 2L',
            'Gula Pasir 1kg', 'Telur Ayam 1kg',
            'Tepung Terigu 1kg', 'Susu Kental Manis',
            'Kopi Bubuk 250g', 'Mie Instan Dus',
        ],
    }

    # ── 12 order scenarios ──
    ORDERS = [
        # ── GoSend ──
        {
            'store': 'Warung Segar Makmur',
            'buyer_idx': 0,
            'shipping_method': 'gosend',
            'items': ['Bayam Segar', 'Wortel Import', 'Tomat Merah'],
            'order_status': 'pending',
            'delivery_status': 'menunggu_konfirmasi',
            'hours_ago': 2,
            'driver_name': '',
            'driver_phone': '',
            'pickup_code': '',
        },
        {
            'store': 'Warung Segar Makmur',
            'buyer_idx': 1,
            'shipping_method': 'gosend',
            'items': ['Kangkung Hijau', 'Brokoli Fresh'],
            'order_status': 'processed',
            'delivery_status': 'diproses_penjual',
            'hours_ago': 6,
            'driver_name': '',
            'driver_phone': '',
            'pickup_code': '',
        },
        {
            'store': 'Toko Buah Sehat',
            'buyer_idx': 0,
            'shipping_method': 'gosend',
            'items': ['Apel Fuji', 'Anggur Hijau'],
            'order_status': 'shipped',
            'delivery_status': 'kurir_menjemput',
            'hours_ago': 4,
            'driver_name': 'Ahmad Rizki',
            'driver_phone': '081234567891',
            'pickup_code': '482910',
            'estimated_pickup': '10 menit lagi',
        },
        {
            'store': 'Sembako Hemat Jaya',
            'buyer_idx': 2,
            'shipping_method': 'gosend',
            'items': ['Beras Premium 5kg', 'Telur Ayam 1kg'],
            'order_status': 'completed',
            'delivery_status': 'pesanan_diterima',
            'hours_ago': 24,
            'driver_name': 'Doni Saputra',
            'driver_phone': '081234567892',
            'pickup_code': '371526',
            'estimated_time': 'Selesai',
            'completed': True,
        },
        # ── GrabExpress ──
        {
            'store': 'Warung Segar Makmur',
            'buyer_idx': 2,
            'shipping_method': 'grabexpress',
            'items': ['Bayam Segar', 'Kangkung Hijau', 'Tomat Merah'],
            'order_status': 'shipped',
            'delivery_status': 'dalam_perjalanan',
            'hours_ago': 3,
            'driver_name': 'Budi Hartono',
            'driver_phone': '081234567893',
            'pickup_code': '658201',
            'estimated_time': '15 menit lagi',
        },
        {
            'store': 'Toko Buah Sehat',
            'buyer_idx': 1,
            'shipping_method': 'grabexpress',
            'items': ['Pisang Cavendish', 'Jeruk Medan', 'Semangka Merah'],
            'order_status': 'completed',
            'delivery_status': 'pesanan_diterima',
            'hours_ago': 48,
            'driver_name': 'Citra Dewi',
            'driver_phone': '081234567894',
            'pickup_code': '123456',
            'estimated_time': 'Selesai',
            'completed': True,
        },
        {
            'store': 'Sembako Hemat Jaya',
            'buyer_idx': 0,
            'shipping_method': 'grabexpress',
            'items': ['Minyak Goreng 2L', 'Gula Pasir 1kg'],
            'order_status': 'paid',
            'delivery_status': 'menunggu_konfirmasi',
            'hours_ago': 1,
            'driver_name': '',
            'driver_phone': '',
            'pickup_code': '',
        },
        # ── Maxim Delivery ──
        {
            'store': 'Toko Buah Sehat',
            'buyer_idx': 2,
            'shipping_method': 'maxim',
            'items': ['Apel Fuji', 'Pisang Cavendish'],
            'order_status': 'processed',
            'delivery_status': 'diproses_penjual',
            'hours_ago': 5,
            'driver_name': '',
            'driver_phone': '',
            'pickup_code': '',
        },
        {
            'store': 'Sembako Hemat Jaya',
            'buyer_idx': 1,
            'shipping_method': 'maxim',
            'items': ['Beras Premium 5kg', 'Minyak Goreng 2L', 'Gula Pasir 1kg'],
            'order_status': 'shipped',
            'delivery_status': 'menunggu_penjemputan',
            'hours_ago': 3,
            'driver_name': '',
            'driver_phone': '',
            'pickup_code': '904732',
            'estimated_time': 'Segera dijemput',
        },
        # ── Antar Sendiri ──
        {
            'store': 'Warung Segar Makmur',
            'buyer_idx': 1,
            'shipping_method': 'antar_sendiri',
            'items': ['Brokoli Fresh', 'Wortel Import'],
            'order_status': 'shipped',
            'delivery_status': 'kurir_menjemput',
            'hours_ago': 2,
            'driver_name': 'Toko (Pak Rudi)',
            'driver_phone': '081234567895',
            'pickup_code': '285641',
            'estimated_pickup': 'Kurir toko sedang menuju',
        },
        {
            'store': 'Toko Buah Sehat',
            'buyer_idx': 0,
            'shipping_method': 'antar_sendiri',
            'items': ['Jeruk Medan', 'Anggur Hijau', 'Semangka Merah'],
            'order_status': 'shipped',
            'delivery_status': 'dalam_perjalanan',
            'hours_ago': 1,
            'driver_name': 'Toko (Pak Samsul)',
            'driver_phone': '081234567896',
            'pickup_code': '736214',
            'estimated_time': '20 menit lagi',
        },
        # ── Cancelled ──
        {
            'store': 'Sembako Hemat Jaya',
            'buyer_idx': 2,
            'shipping_method': 'maxim',
            'items': ['Telur Ayam 1kg', 'Gula Pasir 1kg'],
            'order_status': 'cancelled',
            'delivery_status': 'dibatalkan',
            'hours_ago': 12,
            'driver_name': '',
            'driver_phone': '',
            'pickup_code': '',
            'cancel_reason': 'Stok habis',
        },
    ]

    # ── Address pool ──
    ADDRESSES = [
        ('Jl. Merdeka No. 10, Jakarta Pusat', 'Bambang', '081298765401'),
        ('Jl. Sudirman Kav. 45, Jakarta Selatan', 'Siti Rahmawati', '081298765402'),
        ('Perumahan Griya Asri Blok C12, Bekasi', 'Hendra Gunawan', '081298765403'),
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force seed even if seed orders already exist',
        )

    def handle(self, *args, **options):
        from orders.models import Order, OrderItem, Delivery, ShippingMethod
        from stores.models import Store
        from products.models import Product

        force = options.get('force', False)

        # ── Idempotency guard ──
        existing_seed_count = Order.objects.filter(
            order_number__startswith=self.SEED_PREFIX
        ).count()
        if existing_seed_count > 0 and not force:
            self.stdout.write(self.style.WARNING(
                f'Seed orders already exist ({existing_seed_count} found). '
                f'Use --force to re-seed (will delete existing seed orders first).'
            ))
            return

        # ── Clean existing seed orders if --force ──
        if force and existing_seed_count > 0:
            self.stdout.write(f'Deleting {existing_seed_count} existing seed orders...')
            Delivery.objects.filter(
                order__order_number__startswith=self.SEED_PREFIX
            ).delete()
            Order.objects.filter(
                order_number__startswith=self.SEED_PREFIX
            ).delete()
            self.stdout.write('  Done.')

        # ── Load existing data ──
        users = list(User.objects.filter(role='buyer').order_by('id'))
        stores = list(Store.objects.filter(status='active').order_by('id'))
        shipping_methods = {sm.code: sm for sm in ShippingMethod.objects.all()}
        products = {p.product_name: p for p in Product.objects.all()}

        if len(users) < 3:
            self.stdout.write(self.style.WARNING('Need at least 3 buyer users. Creating extras...'))
            for i in range(3 - len(users)):
                u = User.objects.create_user(
                    f'buyer{len(users)+i+4}',
                    email=f'buyer{len(users)+i+4}@test.io',
                    password='Test123!',
                    full_name=f'Buyer {len(users)+i+4}',
                    is_verified=True,
                    role='buyer',
                )
                users.append(u)
                self.stdout.write(f'  + Created buyer: {u.email}')

        self.stdout.write(f'\nSeeding {len(self.ORDERS)} orders...\n')

        created_count = 0
        skipped_count = 0

        for idx, order_spec in enumerate(self.ORDERS):
            # Resolve store
            store = None
            for s in stores:
                if s.store_name == order_spec['store']:
                    store = s
                    break
            if not store:
                self.stdout.write(self.style.WARNING(
                    f'  ! Store "{order_spec["store"]}" not found, skipping order {idx+1}'
                ))
                skipped_count += 1
                continue

            # Resolve shipping method
            sm_code = order_spec['shipping_method']
            sm = shipping_methods.get(sm_code)
            if not sm:
                self.stdout.write(self.style.WARNING(
                    f'  ! Shipping method "{sm_code}" not found, skipping order {idx+1}'
                ))
                skipped_count += 1
                continue

            # Resolve buyer
            buyer = users[order_spec['buyer_idx'] % len(users)]

            # Resolve products
            order_products = []
            missing = []
            for pname in order_spec['items']:
                p = products.get(pname)
                if p:
                    order_products.append(p)
                else:
                    missing.append(pname)
            if missing:
                self.stdout.write(self.style.WARNING(
                    f'  ! Products not found for order {idx+1}: {", ".join(missing)}'
                ))
            if not order_products:
                skipped_count += 1
                continue

            # ── Calculate timestamps ──
            now = timezone.now()
            hours_ago = order_spec['hours_ago']
            created_at = now - timedelta(hours=hours_ago, minutes=random.randint(0, 59))

            # ── Resolve address ──
            addr = self.ADDRESSES[order_spec['buyer_idx'] % len(self.ADDRESSES)]

            # ── Create Order (subtotal=0, calculated by OrderItem.save()) ──
            order_number = f'{self.SEED_PREFIX}{idx+1:02d}-{random.randint(100,999)}'

            order = Order.objects.create(
                user=buyer,
                store=store,
                shipping_method=sm,
                order_number=order_number,
                subtotal=0,
                shipping_cost=Decimal(str(sm.base_fee)),
                total_price=0,
                order_status=order_spec['order_status'],
                payment_status='paid' if order_spec['order_status'] != 'pending' else 'pending',
                delivery_address=addr[0],
                recipient_name=addr[1],
                recipient_phone=addr[2],
                courier=sm.name,
                payment_method=random.choice(['midtrans', 'cod', 'transfer']),
                completed_at=created_at if order_spec.get('completed') else None,
            )

            # Backdate timestamps (auto_now_add/auto_now override create())
            Order.objects.filter(id=order.id).update(
                created_at=created_at,
                updated_at=created_at,
            )

            # ── Create Order Items ──
            for p in order_products:
                qty = random.randint(1, 3)
                OrderItem.objects.create(
                    order=order,
                    product=p,
                    product_name=p.product_name,
                    price=p.price,
                    qty=qty,
                    subtotal=p.price * qty,
                )

            # ── Create Delivery ──
            pickup_code = order_spec.get('pickup_code', '')
            if not pickup_code and order_spec['delivery_status'] in (
                'menunggu_penjemputan', 'kurir_menjemput', 'dalam_perjalanan', 'pesanan_diterima'
            ):
                pickup_code = ''.join(random.choices(string.digits, k=6))

            delivery = Delivery.objects.create(
                order=order,
                shipping_method=sm,
                courier_name=sm.name,
                driver_name=order_spec.get('driver_name', '') or None,
                driver_phone=order_spec.get('driver_phone', '') or None,
                pickup_code=pickup_code or None,
                delivery_status=order_spec['delivery_status'],
                estimated_time=order_spec.get('estimated_time', ''),
                estimated_pickup=order_spec.get('estimated_pickup', ''),
                tracking_number=f'TRK-{order.order_number}' if order_spec['delivery_status'] in (
                    'dalam_perjalanan', 'pesanan_diterima'
                ) else '',
                picked_up_at=created_at if order_spec['delivery_status'] in (
                    'kurir_menjemput', 'dalam_perjalanan', 'pesanan_diterima'
                ) else None,
                delivered_at=created_at if order_spec.get('completed') else None,
                notes=order_spec.get('cancel_reason', ''),
            )

            # Backdate delivery timestamps
            Delivery.objects.filter(id=delivery.id).update(
                created_at=created_at,
                updated_at=created_at,
            )

            created_count += 1

            # ── Print summary ──
            status_short = order_spec['delivery_status'].replace('_', ' ')
            self.stdout.write(
                f'  [{idx+1:2d}] #{order.order_number}: '
                f'{buyer.full_name} -> {store.store_name} '
                f'[{sm.name}] '
                f'Rp {order.total_price:,.0f} '
                f'({status_short})'
            )

        # ── Summary ──
        total = Order.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'\nDone. Created {created_count} orders, skipped {skipped_count}. '
            f'Total orders in database: {total}'
        ))

        # ── Breakdown by delivery status ──
        from django.db.models import Count
        breakdown = Delivery.objects.values('delivery_status').annotate(
            count=Count('id')
        ).order_by('delivery_status')
        self.stdout.write('\nDelivery Status Breakdown:')
        status_labels = dict(Delivery.HYPELOCAL_STATUS)
        for entry in breakdown:
            label = status_labels.get(entry['delivery_status'], entry['delivery_status'])
            self.stdout.write(f'  * {label}: {entry["count"]} order(s)')
