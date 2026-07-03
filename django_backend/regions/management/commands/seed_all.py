"""
Unified management command to seed ALL Indonesian administrative region data.
Orchestrates provinces → regencies → districts → villages in the correct order.
Reports comprehensive statistics after completion.

Usage:
    python manage.py seed_all                        # Seed all region data
    python manage.py seed_all --flush                # Clear and reseed everything
    python manage.py seed_all --dry-run              # Validate only
    python manage.py seed_all --limit=1000           # Limit villages for testing
    python manage.py seed_all --skip-download        # Skip GitHub download
"""

import time
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import connection

from regions.models import Province, Regency, District, Village


class Command(BaseCommand):
    help = 'Seed ALL Indonesian administrative region data (4 levels)'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true',
                            help='Clear all region data before reseeding')
        parser.add_argument('--dry-run', action='store_true',
                            help='Validate data without inserting')
        parser.add_argument('--limit', type=int, default=0,
                            help='Limit districts/villages for testing (0 = seed all)')
        parser.add_argument('--skip-download', action='store_true',
                            help='Skip GitHub download, use existing data only')

    def handle(self, *args, **options):
        flush = options['flush']
        dry_run = options.get('dry_run', False)
        limit = options['limit']
        skip_download = options.get('skip_download', False)

        self.stdout.write(self.style.MIGRATE_HEADING(
            '╔══════════════════════════════════════════════╗\n'
            '║   SEEDER DATA WILAYAH INDONESIA             ║\n'
            '║   Source: Kemendagri + BPS (via GitHub)     ║\n'
            '╚══════════════════════════════════════════════╝'
        ))

        start = time.time()

        if flush and not dry_run:
            self.stdout.write(self.style.WARNING('\n[FLUSH] Menghapus semua data wilayah...'))
            Village.objects.all().delete()
            District.objects.all().delete()
            Regency.objects.all().delete()
            Province.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('  Semua data wilayah dihapus.\n'))

        # ── Step 1: Provinces + Regencies ──
        self.stdout.write(self.style.MIGRATE_HEADING('[1/2] Provinsi & Kabupaten/Kota'))
        call_command('seed_regions', dry_run=dry_run)

        # ── Step 2: Districts + Villages ──
        self.stdout.write(self.style.MIGRATE_HEADING('[2/2] Kecamatan & Desa/Kelurahan'))
        call_command('seed_districts_villages', dry_run=dry_run, limit=limit, skip_download=skip_download)

        elapsed = time.time() - start

        if not dry_run:
            p = Province.objects.count()
            r = Regency.objects.count()
            d = District.objects.count()
            v = Village.objects.count()
            self.stdout.write(self.style.SUCCESS(
                '\n' + '=' * 50 + '\n'
                '  HASIL SEEDING DATA WILAYAH\n'
                '=' * 50 + '\n'
                f'  Provinsi       : {p} / 38\n'
                f'  Kabupaten/Kota : {r} / 514\n'
                f'  Kecamatan      : {d} / ~7,277\n'
                f'  Desa/Kelurahan : {v} / ~83,731\n'
                '=' * 50 + '\n'
                f'  Waktu: {elapsed:.1f}s\n'
                '=' * 50
            ))
        else:
            self.stdout.write(self.style.SUCCESS('\n[DONE] Dry-run validasi selesai.'));
