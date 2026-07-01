"""
Management command to seed Indonesian administrative region data.
Loads provinces and regencies from data modules.
Districts and villages can be loaded from CSV or API in production.

Usage:
    python manage.py seed_regions              # Seed all region data
    python manage.py seed_regions --flush      # Clear and reseed
"""

from django.core.management.base import BaseCommand

from regions.models import Province, Regency
from regions.data.provinces import PROVINCES
from regions.data.regencies import REGENCIES


class Command(BaseCommand):
    help = 'Seed Indonesian administrative region data (Provinces + Regencies)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Clear all existing region data before seeding',
        )

    def handle(self, *args, **options):
        if options['flush']:
            self.stdout.write(self.style.WARNING('Flushing existing region data...'))
            Province.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('  Done.'))

        self._seed_provinces()
        self._seed_regencies()

        # Summary
        province_count = Province.objects.count()
        regency_count = Regency.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'\n[OK] Seeded: {province_count} provinces, {regency_count} regencies/cities'
        ))

    def _seed_provinces(self):
        """Seed all 38 provinces."""
        created = 0
        skipped = 0
        for prov in PROVINCES:
            _, is_new = Province.objects.get_or_create(
                code=prov['code'],
                defaults={
                    'name': prov['name'],
                    'latitude': prov.get('latitude'),
                    'longitude': prov.get('longitude'),
                }
            )
            if is_new:
                created += 1
            else:
                skipped += 1
        self.stdout.write(f'  Provinces: {created} created, {skipped} skipped')

    def _seed_regencies(self):
        """Seed all regencies/cities."""
        created = 0
        skipped = 0
        errors = 0

        for code, prov_code, name, reg_type, lat, lng in REGENCIES:
            try:
                province = Province.objects.get(code=prov_code)
                _, is_new = Regency.objects.get_or_create(
                    code=code,
                    defaults={
                        'province': province,
                        'name': name,
                        'type': reg_type,
                        'latitude': lat,
                        'longitude': lng,
                    }
                )
                if is_new:
                    created += 1
                else:
                    skipped += 1
            except Province.DoesNotExist:
                self.stderr.write(
                    self.style.ERROR(f'  Province {prov_code} not found for regency {code} {name}')
                )
                errors += 1

        self.stdout.write(f'  Regencies: {created} created, {skipped} skipped, {errors} errors')
