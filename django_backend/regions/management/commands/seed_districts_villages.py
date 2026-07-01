"""
Management command to seed Indonesian administrative region data (Districts & Villages).
Downloads data from edwardsamuel/Wilayah-Administratif-Indonesia repository on GitHub.
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


class Command(BaseCommand):
    help = 'Seed Indonesian districts (Kecamatan) and villages (Desa/Kelurahan)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit the number of records seeded for testing purposes (0 means seed all)',
        )
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Delete all districts and villages before seeding',
        )

    def handle(self, *args, **options):
        limit = options['limit']
        if options['flush']:
            self.stdout.write(self.style.WARNING("Flushing existing districts and villages..."))
            Village.objects.all().delete()
            District.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("  Done."))

        self.stdout.write("Starting seeder for Districts and Villages...")
        
        # 1. Seed Districts
        self._seed_districts(limit)
        
        # 2. Seed Villages
        self._seed_villages(limit)

        self.stdout.write(self.style.SUCCESS(
            f"\n[OK] Seeding complete: {District.objects.count()} districts, {Village.objects.count()} villages."
        ))

    def _seed_districts(self, limit):
        self.stdout.write(f"Downloading districts from {KECAMATAN_URL}...")
        try:
            resp = requests.get(KECAMATAN_URL, timeout=30)
            resp.raise_for_status()
            decoded_content = resp.content.decode('utf-8')
            csv_reader = csv.reader(decoded_content.splitlines(), delimiter=',')
            
            # Skip header
            header = next(csv_reader)
            
            districts_to_create = []
            existing_codes = set(District.objects.values_list('code', flat=True))
            
            regencies_cache = {r.code: r for r in Regency.objects.all()}
            provinces_cache = {p.code: p for p in Province.objects.all()}
            
            count = 0
            for row in csv_reader:
                if len(row) < 3:
                    continue
                code, regency_code, name = row[0].strip(), row[1].strip(), row[2].strip()
                
                if code in existing_codes:
                    continue
                
                regency = regencies_cache.get(regency_code)
                if not regency:
                    continue
                
                prov_code = regency_code[:2]
                province = provinces_cache.get(prov_code)
                if not province:
                    continue
                
                dist = District(
                    code=code,
                    regency=regency,
                    province=province,
                    name=name,
                    name_upper=name.upper(),
                    is_active=True
                )
                districts_to_create.append(dist)
                
                count += 1
                if limit > 0 and count >= limit:
                    break

            if districts_to_create:
                self.stdout.write(f"Bulk creating {len(districts_to_create)} districts...")
                District.objects.bulk_create(districts_to_create, batch_size=2000, ignore_conflicts=True)
                self.stdout.write(f"Successfully seeded districts.")
            else:
                self.stdout.write("No new districts to seed.")

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error seeding districts: {str(e)}"))

    def _seed_villages(self, limit):
        self.stdout.write(f"Downloading villages from {KELURAHAN_URL}...")
        try:
            resp = requests.get(KELURAHAN_URL, timeout=60)
            resp.raise_for_status()
            decoded_content = resp.content.decode('utf-8')
            csv_reader = csv.reader(decoded_content.splitlines(), delimiter=',')
            
            # Skip header
            header = next(csv_reader)
            
            villages_to_create = []
            existing_codes = set(Village.objects.values_list('code', flat=True))
            
            districts_cache = {d.code: d for d in District.objects.all()}
            regencies_cache = {r.code: r for r in Regency.objects.all()}
            provinces_cache = {p.code: p for p in Province.objects.all()}
            
            count = 0
            for row in csv_reader:
                if len(row) < 3:
                    continue
                code, district_code, name = row[0].strip(), row[1].strip(), row[2].strip()
                
                if code in existing_codes:
                    continue
                
                district = districts_cache.get(district_code)
                if not district:
                    continue
                
                reg_code = district_code[:4]
                regency = regencies_cache.get(reg_code)
                if not regency:
                    continue
                
                prov_code = district_code[:2]
                province = provinces_cache.get(prov_code)
                if not province:
                    continue
                
                # Determine type (Kelurahan / Desa)
                vtype = 'desa'
                if name.upper().startswith('KEL.') or 'KELURAHAN' in name.upper():
                    vtype = 'kelurahan'
                
                village = Village(
                    code=code,
                    district=district,
                    regency=regency,
                    province=province,
                    name=name,
                    name_upper=name.upper(),
                    type=vtype,
                    postal_code='',
                    is_active=True
                )
                villages_to_create.append(village)
                
                count += 1
                if limit > 0 and count >= limit:
                    break

            if villages_to_create:
                self.stdout.write(f"Bulk creating {len(villages_to_create)} villages...")
                Village.objects.bulk_create(villages_to_create, batch_size=2000, ignore_conflicts=True)
                self.stdout.write(f"Successfully seeded villages.")
            else:
                self.stdout.write("No new villages to seed.")

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error seeding villages: {str(e)}"))
