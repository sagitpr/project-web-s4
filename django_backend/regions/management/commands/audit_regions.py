"""
Management command to audit Indonesian administrative region data.
Checks data completeness, FK consistency, orphan records, and more.

Usage:
    python manage.py audit_regions           # Full audit report
    python manage.py audit_regions --fix     # Fix minor issues found
    python manage.py audit_regions --verbose # Show all records with issues
"""

from collections import Counter
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from regions.models import Province, Regency, District, Village
from regions.data.provinces import PROVINCES
from regions.data.regencies import REGENCIES


class Command(BaseCommand):
    help = 'Audit Indonesian region data completeness and consistency'

    def add_arguments(self, parser):
        parser.add_argument('--fix', action='store_true',
                            help='Fix minor issues automatically')
        parser.add_argument('--verbose', action='store_true',
                            help='Show detailed records with issues')

    def handle(self, *args, **options):
        fix = options['fix']
        verbose = options['verbose']

        self.stdout.write(self.style.MIGRATE_HEADING(
            '╔════════════════════════════════════════╗\n'
            '║   AUDIT DATA WILAYAH INDONESIA         ║\n'
            '╚════════════════════════════════════════╝'
        ))

        issues_found = 0
        issues_fixed = 0

        # ── 1. Record Counts ──
        self.stdout.write('\n📊 JUMLAH RECORD')
        p_count = Province.objects.count()
        r_count = Regency.objects.count()
        d_count = District.objects.count()
        v_count = Village.objects.count()
        self.stdout.write(f'  Provinsi       : {p_count} / 38 target')
        self.stdout.write(f'  Kabupaten/Kota : {r_count} / 514 target')
        self.stdout.write(f'  Kecamatan      : {d_count} / ~7,277 target')
        self.stdout.write(f'  Desa/Kelurahan : {v_count} / ~83,731 target')

        if p_count == 0:
            self.stdout.write(self.style.ERROR('\n❌ KRITIS: Database kosong! Jalankan seed_regions dulu.'))

        # ── 2. FK Consistency ──
        self.stdout.write('\n🔗 KONSISTENSI RELASI')

        # Regencies → Province
        orphan_regencies = Regency.objects.filter(province__isnull=True)
        if orphan_regencies.exists():
            self.stdout.write(self.style.ERROR(
                f'  ❌ {orphan_regencies.count()} regencies tanpa province FK'
            ))
            issues_found += orphan_regencies.count()

        # Districts → Regency
        orphan_districts = District.objects.filter(regency__isnull=True)
        if orphan_districts.exists():
            self.stdout.write(self.style.ERROR(
                f'  ❌ {orphan_districts.count()} districts tanpa regency FK'
            ))
            issues_found += orphan_districts.count()

        # Districts → Province
        orphan_districts_p = District.objects.filter(province__isnull=True)
        if orphan_districts_p.exists():
            self.stdout.write(self.style.ERROR(
                f'  ❌ {orphan_districts_p.count()} districts tanpa province FK'
            ))
            issues_found += orphan_districts_p.count()

        # Villages → District
        orphan_villages = Village.objects.filter(district__isnull=True)
        if orphan_villages.exists():
            self.stdout.write(self.style.ERROR(
                f'  ❌ {orphan_villages.count()} villages tanpa district FK'
            ))
            issues_found += orphan_villages.count()

        if issues_found == 0:
            self.stdout.write(self.style.SUCCESS('  ✅ Semua FK konsisten — tidak ada orphan records'))

        # ── 3. Duplicate Names ──
        self.stdout.write('\n🔍 DUPLIKASI NAMA')

        def check_duplicates(model, level_name, fields):
            """Check for duplicate names within the same parent."""
            if model.objects.count() == 0:
                return 0
            dups = model.objects.values(*fields).annotate(
                count=Count('id')
            ).filter(count__gt=1)
            dup_count = sum(d['count'] - 1 for d in dups)
            if dup_count > 0:
                self.stdout.write(self.style.WARNING(
                    f'  ⚠️  {dup_count} potensi duplikasi nama {level_name}'
                ))
                return dup_count
            else:
                self.stdout.write(self.style.SUCCESS(f'  ✅ Nama {level_name} unik'))
                return 0

        from django.db.models import Count
        dup_total = 0
        dup_total += check_duplicates(Province, 'provinsi', ['name'])
        dup_total += check_duplicates(Regency, 'kabupaten', ['province', 'name'])
        dup_total += check_duplicates(District, 'kecamatan', ['regency', 'name'])
        dup_total += check_duplicates(Village, 'desa/kelurahan', ['district', 'name'])
        if dup_total > 0:
            self.stdout.write(self.style.WARNING(f'  Total duplikasi: {dup_total}'))

        # ── 4. Active vs Inactive ──
        self.stdout.write('\n⚡ STATUS AKTIF')
        for model, name in [(Province, 'Provinsi'), (Regency, 'Kabupaten'),
                             (District, 'Kecamatan'), (Village, 'Desa')]:
            total = model.objects.count()
            active = model.objects.filter(is_active=True).count()
            inactive = total - active
            if inactive > 0:
                self.stdout.write(self.style.WARNING(f'  ⚠️  {name}: {active} aktif, {inactive} non-aktif'))
            else:
                self.stdout.write(f'  ✅ {name}: {active} aktif')

        # ── 5. Province Coverage ──
        self.stdout.write('\n🌏 COVERAGE PROVINSI')
        if p_count > 0:
            all_provinces = {p['name'] for p in PROVINCES}
            seeded_provinces = set(Province.objects.values_list('name', flat=True))
            missing = all_provinces - seeded_provinces
            if missing:
                self.stdout.write(self.style.WARNING(f'  ⚠️  Provinsi belum masuk: {", ".join(sorted(missing))}'))
            else:
                self.stdout.write(self.style.SUCCESS('  ✅ Semua 38 provinsi terdata'))

        # ── 6. Regency Coverage per Province ──
        self.stdout.write('\n🗺️  COVERAGE KABUPATEN PER PROVINSI')
        if r_count > 0:
            expected = Counter(p[1] for p in REGENCIES)
            actual = Counter(Regency.objects.values_list('province__code', flat=True))
            under_count = 0
            for prov_code in expected:
                exp = expected[prov_code]
                act = actual.get(prov_code, 0)
                if act < exp:
                    self.stdout.write(self.style.WARNING(
                        f'  ⚠️  Provinsi {prov_code}: {act}/{exp} kabupaten'
                    ))
                    under_count += 1
            if under_count == 0:
                self.stdout.write(self.style.SUCCESS('  ✅ Semua kabupaten/kota terdata'))

        # ── 7. Summary Stats ──
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'  AUDIT SELESAI: {issues_found} issues ditemukan'
        ))
        if issues_found > 0 and fix:
            self.stdout.write(self.style.WARNING('  Gunakan --fix untuk perbaikan otomatis'))
        self.stdout.write('=' * 50)
