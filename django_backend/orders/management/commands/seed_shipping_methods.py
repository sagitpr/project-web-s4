"""
Management command to seed hyperlocal shipping methods for Warungio.
Inserts the 4 allowed methods: GoSend, GrabExpress, Maxim Delivery, Antar Sendiri.
"""
from django.core.management.base import BaseCommand
from orders.models import ShippingMethod


class Command(BaseCommand):
    help = 'Seed the 4 hyperlocal shipping methods (GoSend, GrabExpress, Maxim, Antar Sendiri)'

    METHODS = [
        {
            'code': 'gosend',
            'name': 'GoSend',
            'description': 'Pengiriman instan menggunakan layanan GoSend. Dilengkapi fitur tracking realtime, estimasi waktu, dan informasi driver.',
            'base_fee': 8000,
            'estimated_time': '30-60 menit',
            'sort_order': 1,
        },
        {
            'code': 'grabexpress',
            'name': 'GrabExpress',
            'description': 'Pengiriman instan menggunakan GrabExpress. Dengan tracking realtime, estimasi tiba, dan informasi driver lengkap.',
            'base_fee': 8000,
            'estimated_time': '30-60 menit',
            'sort_order': 2,
        },
        {
            'code': 'maxim',
            'name': 'Maxim Delivery',
            'description': 'Pengiriman menggunakan layanan Maxim Delivery. Dilengkapi tracking pesanan, informasi kurir, dan estimasi pengiriman.',
            'base_fee': 7000,
            'estimated_time': '45-90 menit',
            'sort_order': 3,
        },
        {
            'code': 'antar_sendiri',
            'name': 'Antar Sendiri',
            'description': 'Pesanan diantar langsung oleh pihak toko atau mitra warung. Tersedia nama kurir toko dan estimasi tiba.',
            'base_fee': 0,
            'estimated_time': '60-120 menit',
            'sort_order': 4,
        },
    ]

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for method_data in self.METHODS:
            obj, created = ShippingMethod.objects.update_or_create(
                code=method_data['code'],
                defaults=method_data,
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  + Created: {obj.name}'))
            else:
                updated_count += 1
                self.stdout.write(f'  ~ Updated: {obj.name}')

        total = ShippingMethod.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'\nDone. Created {created_count}, updated {updated_count}. Total methods: {total}'
        ))
