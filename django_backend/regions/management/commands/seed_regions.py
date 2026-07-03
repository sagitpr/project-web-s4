"""
Management command to seed Indonesian province & regency data.
Uses bulk_create for ~10x speedup over get_or_create loop.
Validates all FK relationships before inserting.

Usage:
    python manage.py seed_regions                # Seed provinces + regencies
    python manage.py seed_regions --flush        # Clear and reseed all
    python manage.py seed_regions --dry-run      # Validate data without inserting
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from regions.models import Province, Regency
from regions.data.provinces import PROVINCES
from regions.data.regencies import REGENCIES

logger = logging.getLogger('django_backend')


class Command(BaseCommand):
    help = 'Seed Indonesian administrative region data (Provinces + Regencies)'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true',
                            help='Delete ALL existing region data before seeding')
        parser.add_argument('--dry-run', action='store_true',
                            help='Validate data and report what would be created without inserting')

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        if options['flush']:
            self.stdout.write(self.style.WARNING('Flushing existing region data...'))
            Regency.objects.all().delete()
            Province.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('  Done.'))

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no data will be inserted'))
            self._validate_provinces()
            self._validate_regencies()
            return

        with transaction.atomic():
            prov_created, prov_skipped = self._seed_provinces()
            reg_created, reg_skipped, reg_errors = self._seed_regencies()

        # Summary
        p_total = Province.objects.count()
        r_total = Regency.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'\n[OK] Seeded: {p_total} provinces (+{prov_created}), '
            f'{r_total} regencies/cities (+{reg_created})'
        ))
        if reg_errors:
            self.stdout.write(self.style.WARNING(f'  Errors: {reg_errors} (FK lookup failures)'))

    # ── Validation (dry-run) ──

    def _validate_provinces(self):
        """Check all province codes for uniqueness and consistency."""
        codes = set()
        duplicates = []
        for prov in PROVINCES:
            code = prov['code']
            if code in codes:
                duplicates.append(code)
            codes.add(code)
        if duplicates:
            self.stdout.write(self.style.ERROR(f'  Duplicate province codes: {duplicates}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'  Provinces: {len(PROVINCES)} unique codes OK'))

    def _validate_regencies(self):
        """Check all regency FK references are valid."""
        prov_codes = {p['code'] for p in PROVINCES}
        valid = 0
        orphan = 0
        orphan_details = []
        for code, prov_code, name, *_ in REGENCIES:
            if prov_code in prov_codes:
                valid += 1
            else:
                orphan += 1
                orphan_details.append(f'{code} {name} → province {prov_code} NOT FOUND')
        self.stdout.write(self.style.SUCCESS(f'  Regencies: {valid} valid FK, {orphan} orphan'))
        for detail in orphan_details[:10]:
            self.stdout.write(self.style.WARNING(f'    {detail}'))

    # ── Seed provinces (bulk_create) ──

    def _seed_provinces(self):
        """Seed all 38 provinces via bulk_create (~2x faster than get_or_create)."""
        existing = {p.code for p in Province.objects.all()}
        to_create = []
        for prov in PROVINCES:
            if prov['code'] in existing:
                continue
            to_create.append(Province(
                code=prov['code'],
                name=prov['name'],
                name_upper=prov['name'].upper(),
                latitude=prov.get('latitude'),
                longitude=prov.get('longitude'),
                is_active=True,
            ))
        created = len(to_create)
        skipped = sum(1 for p in PROVINCES if p['code'] in existing)
        if to_create:
            Province.objects.bulk_create(to_create, batch_size=500, ignore_conflicts=True)
            self.stdout.write(f'  Provinces: {created} created, {skipped} skipped')
        return created, skipped

    # ── Seed regencies (bulk_create) ──

    def _seed_regencies(self):
        """Seed all regencies via bulk_create with FK prefetch."""
        province_map = {p.code: p for p in Province.objects.all()}
        existing = {r.code for r in Regency.objects.all()}
        to_create = []
        errors = 0
        skipped = 0

        for code, prov_code, name, reg_type, lat, lng in REGENCIES:
            if code in existing:
                skipped += 1
                continue
            province = province_map.get(prov_code)
            if not province:
                self.stderr.write(self.style.ERROR(f'  Province {prov_code} not found for regency {code} {name}'))
                errors += 1
                continue
            to_create.append(Regency(
                code=code,
                province=province,
                name=name,
                name_upper=name.upper(),
                type=reg_type,
                latitude=lat,
                longitude=lng,
                is_active=True,
            ))

        created = len(to_create)
        if to_create:
            Regency.objects.bulk_create(to_create, batch_size=500, ignore_conflicts=True)

        self.stdout.write(f'  Regencies: {created} created, {skipped} skipped, {errors} errors')
        return created, skipped, errors
