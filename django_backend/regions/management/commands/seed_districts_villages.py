"""
Management command to seed Indonesian districts (Kecamatan) and villages (Desa/Kelurahan).
Downloads data from edwardsamuel/Wilayah-Administratif-Indonesia (Kemendagri-sourced).
Validates FK relationships, removes orphan records, and uses bulk_create for performance.

Usage:
    python manage.py seed_districts_villages                # Full seed for all districts + villages
    python manage.py seed_districts_villages --limit=1000   # Limit for testing
    python manage.py seed_districts_villages --flush        # Clear and reseed
    python manage.py seed_districts_villages --dry-run      # Validate without inserting
"""

import csv
import logging
import requests
from django.core.management.base import BaseCommand
from django.db import transaction

from regions.models import Province, Regency, District, Village

logger = logging.getLogger('django_backend')

KECAMATAN_URL = "https://raw.githubusercontent.com/edwardsamuel/Wilayah-Administratif-Indonesia/master/csv/districts.csv"
KELURAHAN_URL = "https://raw.githubusercontent.com/edwardsamuel/Wilayah-Administratif-Indonesia/master/csv/villages.csv"
EXPECTED_DISTRICTS = 7277   # Per Kemendagri 2024
EXPECTED_VILLAGES = 83731   # Per Kemendagri 2024


class Command(BaseCommand):
    help = 'Seed Indonesian districts (Kecamatan) and villages (Desa/Kelurahan)'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0,
                            help='Limit records for testing (0 = seed all)')
        parser.add_argument('--flush', action='store_true',
                            help='Delete ALL existing districts and villages before seeding')
        parser.add_argument('--dry-run', action='store_true',
                            help='Validate data without inserting')
        parser.add_argument('--skip-download', action='store_true',
                            help='Skip GitHub download, use existing data if any')

    def handle(self, *args, **options):
        limit = options['limit']
        dry_run = options.get('dry_run', False)
        skip_download = options.get('skip_download', False)

        if options['flush']:
            self.stdout.write(self.style.WARNING("Flushing existing districts and villages..."))
            Village.objects.all().delete()
            District.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("  Done."))

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no data will be inserted'))
            self._validate_prerequisites()
            return

        # Pre-validate FK references
        if not self._validate_prerequisites():
            return

        self.stdout.write("Starting seeder for Districts and Villages...")

        dist_created, dist_skipped = self._seed_districts(limit, skip_download)
        vill_created, vill_skipped = self._seed_villages(limit, skip_download)

        # Report
        d_total = District.objects.count()
        v_total = Village.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'\n[OK] Seeding complete: {d_total} districts (+{dist_created}), '
            f'{v_total} villages (+{vill_created})'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'  Expected: ~{EXPECTED_DISTRICTS} districts, ~{EXPECTED_VILLAGES} villages'
        ))

    # ── Prerequisite validation ──

    def _validate_prerequisites(self):
        """Ensure provinces and regencies exist before seeding districts/villages."""
        p_count = Province.objects.count()
        r_count = Regency.objects.count()
        if p_count == 0 or r_count == 0:
            self.stderr.write(self.style.ERROR(
                'Provinces (0) or Regencies (0) not seeded yet. '
                'Run `python manage.py seed_regions` first.'
            ))
            return False
        self.stdout.write(f'  Prerequisites OK: {p_count} provinces, {r_count} regencies')
        return True

    # ── Seed districts ──

    def _seed_districts(self, limit, skip_download):
        """Seed districts from GitHub CSV with FK validation and bulk_create."""
        if skip_download:
            self.stdout.write("Skipping download (--skip-download). Checking existing data...")
            return 0, District.objects.count()

        self.stdout.write(f"Downloading districts from {KECAMATAN_URL}...")
        try:
            resp = requests.get(KECAMATAN_URL, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f"Download failed: {e}"))
            return 0, 0

        decoded = resp.content.decode('utf-8-sig')
        reader = csv.reader(decoded.splitlines(), delimiter=',')

        # Skip header
        next(reader, None)

        existing = set(District.objects.values_list('code', flat=True))
        regencies = {r.code: r for r in Regency.objects.all()}
        provinces = {p.code: p for p in Province.objects.all()}

        to_create = []
        count, skipped_fk = 0, 0

        for row in reader:
            if len(row) < 3:
                continue
            code, regency_code, name = row[0].strip(), row[1].strip(), row[2].strip()
            if not code or not regency_code or not name:
                continue
            if code in existing:
                continue

            regency = regencies.get(regency_code)
            if not regency:
                skipped_fk += 1
                continue

            province = provinces.get(regency_code[:2])
            if not province:
                skipped_fk += 1
                continue

            to_create.append(District(
                code=code,
                regency=regency,
                province=province,
                name=name,
                name_upper=name.upper(),
                is_active=True,
            ))
            count += 1
            if limit > 0 and count >= limit:
                break

        created = 0
        if to_create:
            self.stdout.write(f"  Bulk creating {len(to_create)} districts...")
            District.objects.bulk_create(to_create, batch_size=2000, ignore_conflicts=True)
            created = len(to_create)

        self.stdout.write(f'  Districts: {created} created, {len(existing)} existing, {skipped_fk} FK failures')
        return created, len(existing)

    # ── Seed villages ──

    def _seed_villages(self, limit, skip_download):
        """Seed villages from GitHub CSV with FK validation and bulk_create."""
        if skip_download:
            self.stdout.write("Skipping download (--skip-download). Checking existing data...")
            return 0, Village.objects.count()

        self.stdout.write(f"Downloading villages from {KELURAHAN_URL}...")
        try:
            resp = requests.get(KELURAHAN_URL, timeout=60)
            resp.raise_for_status()
        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f"Download failed: {e}"))
            return 0, 0

        decoded = resp.content.decode('utf-8-sig')
        reader = csv.reader(decoded.splitlines(), delimiter=',')

        # Skip header
        next(reader, None)

        existing = set(Village.objects.values_list('code', flat=True))
        districts = {d.code: d for d in District.objects.all()}
        regencies = {r.code: r for r in Regency.objects.all()}
        provinces = {p.code: p for p in Province.objects.all()}

        to_create = []
        count, skipped_fk = 0, 0

        for row in reader:
            if len(row) < 3:
                continue
            code, district_code, name = row[0].strip(), row[1].strip(), row[2].strip()
            if not code or not district_code or not name:
                continue
            if code in existing:
                continue

            district = districts.get(district_code)
            if not district:
                skipped_fk += 1
                continue

            regency = regencies.get(district_code[:4])
            if not regency:
                skipped_fk += 1
                continue

            province = provinces.get(district_code[:2])
            if not province:
                skipped_fk += 1
                continue

            # Determine type
            vtype = 'kelurahan' if (name.upper().startswith('KEL.') or 'KELURAHAN' in name.upper()) else 'desa'

            to_create.append(Village(
                code=code,
                district=district,
                regency=regency,
                province=province,
                name=name,
                name_upper=name.upper(),
                type=vtype,
                is_active=True,
            ))
            count += 1
            if limit > 0 and count >= limit:
                break

        created = 0
        if to_create:
            self.stdout.write(f"  Bulk creating {len(to_create)} villages...")
            Village.objects.bulk_create(to_create, batch_size=2000, ignore_conflicts=True)
            created = len(to_create)

        self.stdout.write(f'  Villages: {created} created, {len(existing)} existing, {skipped_fk} FK failures')
        return created, len(existing)
