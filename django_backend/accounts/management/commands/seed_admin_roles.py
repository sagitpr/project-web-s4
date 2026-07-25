"""
Management command to seed default admin roles.
Run after initial migration:
    python manage.py seed_admin_roles
"""

from django.core.management.base import BaseCommand
from accounts.models import AdminRole


class Command(BaseCommand):
    help = 'Seed default admin roles with appropriate permissions'

    ROLES = [
        {
            'name': 'Super Admin',
            'level': 100,
            'description': 'Akses penuh ke seluruh sistem, termasuk manajemen administrator',
            'permissions': [
                'view_dashboard', 'manage_products', 'manage_orders', 'manage_payments',
                'manage_users', 'manage_sellers', 'manage_buyers', 'manage_content',
                'manage_promotions', 'manage_reports', 'manage_ai', 'manage_system',
                'manage_administrators', 'view_audit_logs', 'export_data',
            ],
        },
        {
            'name': 'Admin',
            'level': 80,
            'description': 'Akses penuh ke sistem kecuali manajemen administrator',
            'permissions': [
                'view_dashboard', 'manage_products', 'manage_orders', 'manage_payments',
                'manage_users', 'manage_sellers', 'manage_buyers', 'manage_content',
                'manage_promotions', 'manage_reports', 'manage_ai', 'manage_system',
                'view_audit_logs', 'export_data',
            ],
        },
        {
            'name': 'Moderator',
            'level': 60,
            'description': 'Moderasi konten, produk, pengguna, dan pesanan',
            'permissions': [
                'view_dashboard', 'manage_products', 'manage_orders', 'manage_users',
                'manage_sellers', 'manage_buyers', 'manage_content', 'view_audit_logs',
            ],
        },
        {
            'name': 'Support',
            'level': 50,
            'description': 'Layanan pelanggan, bantuan pesanan dan pengguna',
            'permissions': [
                'view_dashboard', 'manage_orders', 'manage_users',
                'manage_buyers', 'manage_sellers',
            ],
        },
        {
            'name': 'Finance',
            'level': 40,
            'description': 'Manajemen pembayaran, refund, dan laporan keuangan',
            'permissions': [
                'view_dashboard', 'manage_payments', 'manage_reports',
                'manage_orders', 'export_data',
            ],
        },
        {
            'name': 'Content Manager',
            'level': 30,
            'description': 'Manajemen konten, promosi, dan produk',
            'permissions': [
                'view_dashboard', 'manage_content', 'manage_promotions',
                'manage_products', 'manage_sellers', 'export_data',
            ],
        },
        {
            'name': 'Viewer',
            'level': 10,
            'description': 'Akses baca untuk laporan dan dashboard',
            'permissions': [
                'view_dashboard', 'manage_reports', 'view_audit_logs', 'export_data',
            ],
        },
    ]

    def handle(self, *args, **options):
        created = 0
        updated = 0

        for role_data in self.ROLES:
            role, was_created = AdminRole.objects.update_or_create(
                level=role_data['level'],
                defaults={
                    'name': role_data['name'],
                    'description': role_data['description'],
                    'permissions': role_data['permissions'],
                    'is_active': True,
                },
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'  [OK] Created: {role.name} (Level {role.level})'))
            else:
                updated += 1
                self.stdout.write(f'  [OK] Updated: {role.name} (Level {role.level})')

        self.stdout.write(self.style.SUCCESS(f'Done! {created} roles created, {updated} roles updated.'))
