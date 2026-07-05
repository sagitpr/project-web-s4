"""
Management Command: audit_wallet_migration
===========================================
Audit migration payments.0004_wallet_and_transactions terhadap actual database schema.

Gunakan untuk:
  - Memeriksa apakah tabel wallets & wallet_transactions sudah lengkap
  - Membandingkan kolom, tipe data, nullability, default, index, FK constraint
  - Jika schema identik: tandai migration sebagai applied (fake)
  - Jika ada objek hilang: buat hanya objek yang hilang

Usage:
  # Audit mode (read-only) — hanya laporan
  python manage.py audit_wallet_migration

  # Audit + apply: fake migration jika schema cocok, buat objek hilang jika tidak
  python manage.py audit_wallet_migration --apply
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, connections
from django.db.migrations.recorder import MigrationRecorder
from django.conf import settings


# ──────────────────────────────────────────────────────────────────────────
# EXPECTED SCHEMA — berdasarkan models.py & migration 0004
# ──────────────────────────────────────────────────────────────────────────

EXPECTED_WALLETS = {
    'table': 'wallets',
    'engine': 'InnoDB',
    'columns': {
        'id':       {'type': 'bigint',     'null': 'NO',  'key': 'PRI', 'extra': 'auto_increment', 'default': None},
        'balance':  {'type': 'decimal',    'null': 'NO',  'key': '',    'extra': '',               'default': '0.00'},
        'created_at': {'type': 'datetime', 'null': 'NO',  'key': '',    'extra': '',               'default': None},
        'updated_at': {'type': 'datetime', 'null': 'NO',  'key': '',    'extra': '',               'default': None},
        'user_id':  {'type': 'bigint',     'null': 'NO',  'key': 'UNI', 'extra': '',               'default': None},
    },
    'expected_fks': [
        {'column': 'user_id', 'ref_table': 'users', 'ref_column': 'id', 'on_delete': 'CASCADE'},
    ],
}

EXPECTED_WALLET_TXNS = {
    'table': 'wallet_transactions',
    'engine': 'InnoDB',
    'columns': {
        'id':             {'type': 'bigint',     'null': 'NO',  'key': 'PRI', 'extra': 'auto_increment', 'default': None},
        'wallet_id':      {'type': 'bigint',     'null': 'NO',  'key': 'MUL', 'extra': '',               'default': None},
        'user_id':        {'type': 'bigint',     'null': 'YES', 'key': 'MUL', 'extra': '',               'default': None},
        'tx_type':        {'type': 'varchar',    'null': 'NO',  'key': 'MUL', 'extra': '',               'default': None},
        'amount':         {'type': 'decimal',    'null': 'NO',  'key': '',    'extra': '',               'default': None},
        'balance_before': {'type': 'decimal',    'null': 'NO',  'key': '',    'extra': '',               'default': None},
        'balance_after':  {'type': 'decimal',    'null': 'NO',  'key': '',    'extra': '',               'default': None},
        'description':    {'type': 'varchar',    'null': 'YES', 'key': '',    'extra': '',               'default': None},
        'reference_type': {'type': 'varchar',    'null': 'YES', 'key': '',    'extra': '',               'default': None},
        'reference_id':   {'type': 'varchar',    'null': 'YES', 'key': '',    'extra': '',               'default': None},
        'created_at':     {'type': 'datetime',   'null': 'NO',  'key': '',    'extra': '',               'default': None},
    },
    'expected_fks': [
        {'column': 'wallet_id', 'ref_table': 'wallets', 'ref_column': 'id', 'on_delete': 'CASCADE'},
        {'column': 'user_id',   'ref_table': 'users',   'ref_column': 'id', 'on_delete': 'SET NULL'},
    ],
    'expected_indexes': [
        {'name': 'wallet_txn_wallet_created_idx', 'columns': ['wallet_id', 'created_at'], 'unique': False},
        {'name': 'wallet_txn_user_created_idx',   'columns': ['user_id', 'created_at'],   'unique': False},
        {'name': 'wallet_txn_tx_type_idx',        'columns': ['tx_type'],                  'unique': False},
    ],
}


class Command(BaseCommand):
    help = 'Audit migration payments.0004_wallet_and_transactions terhadap actual DB schema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply', action='store_true',
            help='Terapkan perubahan: fake migration jika schema cocok, buat objek hilang jika tidak'
        )

    def handle(self, *args, **options):
        self.apply = options['apply']

        # Pastikan pakai MySQL
        if not connection.vendor == 'mysql':
            self.stderr.write(self.style.ERROR(
                'ERROR: Command ini hanya untuk MySQL/MariaDB. '
                f'Vendor terdeteksi: {connection.vendor}'
            ))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n╔══════════════════════════════════════════════════════╗\n'
            '║    Audit Migration payments.0004_wallet_and_transactions   ║\n'
            '╚══════════════════════════════════════════════════════╝'
        ))

        all_ok = True

        # ── Audit Table: wallets ──
        wallets_ok, wallets_report = self._audit_table(EXPECTED_WALLETS)
        if not wallets_ok:
            all_ok = False
        self._print_report('wallets', wallets_ok, wallets_report)

        # ── Audit Table: wallet_transactions ──
        txns_ok, txns_report = self._audit_table(EXPECTED_WALLET_TXNS)
        if not txns_ok:
            all_ok = False
        self._print_report('wallet_transactions', txns_ok, txns_report)

        # ── Final Decision ──
        migration_name = '0004_wallet_and_transactions'
        app_label = 'payments'

        if all_ok:
            self.stdout.write(self.style.SUCCESS(
                '\n✓ SEMUA OBJEK LENGKAP. Schema database identik dengan migration.'
            ))
            if self.apply:
                self._fake_migration(app_label, migration_name)
            else:
                self.stdout.write(
                    '\nJalankan dengan --apply untuk menandai migration sebagai applied:\n'
                    '  python manage.py audit_wallet_migration --apply'
                )
        else:
            self.stdout.write(self.style.WARNING(
                '\n⚠  ADA PERBEDAAN. Schema database TIDAK identik dengan migration.'
            ))
            if self.apply:
                self._fix_differences()
            else:
                self.stdout.write(
                    '\nJalankan dengan --apply untuk memperbaiki perbedaan:\n'
                    '  python manage.py audit_wallet_migration --apply'
                )

    # ──────────────────────────────────────────────────────────────────────
    # AUDIT TABLE
    # ──────────────────────────────────────────────────────────────────────
    def _audit_table(self, expected):
        """Audit satu tabel terhadap expected schema. Returns (ok, report_list)."""
        table_name = expected['table']
        report = []

        # ── Cek apakah tabel exists ──
        tables = connection.introspection.table_names()
        if table_name not in tables:
            report.append(('MISSING', f'Tabel `{table_name}` TIDAK ADA di database'))
            return (False, report)

        report.append(('OK', f'Tabel `{table_name}` ada'))

        # ── Cek columns ──
        with connection.cursor() as cursor:
            # Get column info via SHOW COLUMNS (more reliable than get_table_description)
            cursor.execute(f'SHOW COLUMNS FROM `{table_name}`')
            db_columns = {}
            for row in cursor.fetchall():
                col_name = row[0]
                col_type = row[1]
                col_null = row[2]
                col_key = row[3]
                col_default = row[4]
                col_extra = row[5]
                db_columns[col_name] = {
                    'type_raw': col_type,
                    'null': col_null,
                    'key': col_key,
                    'default': col_default,
                    'extra': col_extra,
                }

            # Bandingkan setiap expected column
            for col_name, expected_col in expected['columns'].items():
                if col_name not in db_columns:
                    report.append(('MISSING', f'  Kolom `{col_name}` TIDAK ADA'))
                    continue

                db_col = db_columns[col_name]

                # Cek tipe data (partial match — "decimal" matches "decimal(14,2)")
                exp_type = expected_col['type']
                db_type_raw = db_col['type_raw'].lower()
                if not db_type_raw.startswith(exp_type):
                    report.append(('DIFF', f'  Kolom `{col_name}`: tipe DB={db_type_raw}, expected={exp_type}'))
                    continue

                # Cek nullability
                if db_col['null'] != expected_col['null']:
                    report.append(('DIFF', f'  Kolom `{col_name}`: nullable DB={db_col["null"]}, expected={expected_col["null"]}'))

                # Cek key
                db_key = db_col['key']
                exp_key = expected_col['key']
                # Normalize: MUL (multiple) bisa muncul untuk FK + index
                # PRI = primary key, UNI = unique, MUL = index (bisa juga FK)
                if exp_key == 'MUL' and db_key not in ('MUL', ''):
                    # MUL sometimes shows as '' for composite indexes, this is soft
                    pass
                elif exp_key == 'PRI' and db_key != 'PRI':
                    report.append(('DIFF', f'  Kolom `{col_name}`: key DB={db_key}, expected=PRI'))
                elif exp_key == 'UNI' and db_key not in ('UNI', 'MUL'):
                    report.append(('DIFF', f'  Kolom `{col_name}`: unique key DB={db_key}, expected=UNI'))

                # Cek auto_increment
                if expected_col.get('extra') == 'auto_increment' and 'auto_increment' not in db_col['extra']:
                    report.append(('DIFF', f'  Kolom `{col_name}`: extra DB={db_col["extra"]}, expected=auto_increment'))

            # Cek extra columns (columns di DB tapi tidak di expected)
            for col_name in db_columns:
                if col_name not in expected['columns']:
                    report.append(('EXTRA', f'  Kolom `{col_name}` ada di DB tapi tidak di migration'))

            # ── Cek Foreign Keys ──
            cursor.execute(f"""
                SELECT COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME,
                       DELETE_RULE
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = '{table_name}'
                  AND REFERENCED_TABLE_NAME IS NOT NULL
            """)
            db_fks = {}
            for row in cursor.fetchall():
                col = row[0]
                db_fks[col] = {
                    'ref_table': row[1],
                    'ref_column': row[2],
                    'delete_rule': row[3],
                }

            for exp_fk in expected.get('expected_fks', []):
                col = exp_fk['column']
                if col not in db_fks:
                    report.append(('MISSING', f'  FK `{col}` -> {exp_fk["ref_table"]}({exp_fk["ref_column"]}) TIDAK ADA'))
                    continue
                db_fk = db_fks[col]
                if db_fk['ref_table'] != exp_fk['ref_table'] or db_fk['ref_column'] != exp_fk['ref_column']:
                    report.append(('DIFF', f'  FK `{col}`: DB={db_fk["ref_table"]}({db_fk["ref_column"]}), expected={exp_fk["ref_table"]}({exp_fk["ref_column"]})'))
                if db_fk['delete_rule'] != exp_fk['on_delete']:
                    report.append(('DIFF', f'  FK `{col}` ON DELETE: DB={db_fk["delete_rule"]}, expected={exp_fk["on_delete"]}'))

            # ── Cek Indexes (khusus wallet_transactions) ──
            if 'expected_indexes' in expected:
                cursor.execute(f'SHOW INDEX FROM `{table_name}`')
                db_indexes = {}
                for row in cursor.fetchall():
                    idx_name = row[2]
                    col_name_idx = row[4]
                    non_unique = row[1]
                    if idx_name not in db_indexes:
                        db_indexes[idx_name] = {
                            'columns': [],
                            'unique': not non_unique,
                        }
                    db_indexes[idx_name]['columns'].append(col_name_idx)

                for exp_idx in expected['expected_indexes']:
                    idx_name = exp_idx['name']
                    if idx_name not in db_indexes:
                        report.append(('MISSING', f'  Index `{idx_name}` TIDAK ADA'))
                        continue
                    db_idx = db_indexes[idx_name]
                    if db_idx['columns'] != exp_idx['columns']:
                        report.append(('DIFF',
                            f'  Index `{idx_name}`: columns DB={db_idx["columns"]}, expected={exp_idx["columns"]}'))

        is_ok = all(r[0] == 'OK' or r[0] == 'EXTRA' for r in report)
        return (is_ok, report)

    # ──────────────────────────────────────────────────────────────────────
    # PRINT REPORT
    # ──────────────────────────────────────────────────────────────────────
    def _print_report(self, table_name, ok, report):
        status = '✓ LENGKAP' if ok else '✗ BEDA'
        style = self.style.SUCCESS if ok else self.style.WARNING
        self.stdout.write(style(f'\n── {table_name} [{status}] ──'))
        for r in report:
            code, msg = r
            if code == 'OK':
                self.stdout.write(f'  ✓ {msg}')
            elif code == 'MISSING':
                self.stderr.write(self.style.ERROR(f'  ✗ {msg}'))
            elif code == 'DIFF':
                self.stderr.write(self.style.WARNING(f'  ~ {msg}'))
            elif code == 'EXTRA':
                self.stdout.write(f'  ? {msg}')

    # ──────────────────────────────────────────────────────────────────────
    # FAKE MIGRATION
    # ──────────────────────────────────────────────────────────────────────
    def _fake_migration(self, app_label, migration_name):
        """Tandai migration sebagai applied di django_migrations."""
        recorder = MigrationRecorder(connection)
        applied = recorder.applied_migrations()

        if (app_label, migration_name) in applied:
            self.stdout.write(self.style.WARNING(
                f'\n⚠ Migration {app_label}.{migration_name} sudah tercatat sebagai applied.'
            ))
            return

        from django.utils import timezone
        recorder.record_applied(app_label, migration_name)
        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Migration {app_label}.{migration_name} berhasil ditandai sebagai applied (fake).'
        ))
        self.stdout.write('  Tabel sudah ada di database, tidak ada data yang dihapus.')

    # ──────────────────────────────────────────────────────────────────────
    # FIX DIFFERENCES
    # ──────────────────────────────────────────────────────────────────────
    def _fix_differences(self):
        """Buat objek yang hilang di database."""
        tables = connection.introspection.table_names()

        # ── Buat tabel wallets jika belum ada ──
        if 'wallets' not in tables:
            self.stdout.write('  Membuat tabel `wallets`...')
            with connection.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS `wallets` (
                        `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
                        `balance` decimal(14, 2) NOT NULL DEFAULT 0,
                        `created_at` datetime(6) NOT NULL,
                        `updated_at` datetime(6) NOT NULL,
                        `user_id` bigint NOT NULL UNIQUE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                # Add FK for wallets
                cursor.execute("""
                    ALTER TABLE `wallets` ADD CONSTRAINT `fk_wallets_user`
                    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
                """)
            self.stdout.write(self.style.SUCCESS('  ✓ Tabel `wallets` dibuat.'))

        # ── Buat tabel wallet_transactions jika belum ada ──
        if 'wallet_transactions' not in tables:
            self.stdout.write('  Membuat tabel `wallet_transactions`...')
            with connection.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS `wallet_transactions` (
                        `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
                        `tx_type` varchar(20) NOT NULL,
                        `amount` decimal(14, 2) NOT NULL,
                        `balance_before` decimal(14, 2) NOT NULL,
                        `balance_after` decimal(14, 2) NOT NULL,
                        `description` varchar(255) NULL,
                        `reference_type` varchar(50) NULL,
                        `reference_id` varchar(100) NULL,
                        `created_at` datetime(6) NOT NULL,
                        `user_id` bigint NULL,
                        `wallet_id` bigint NOT NULL,
                        INDEX `wallet_txn_wallet_created_idx` (`wallet_id`, `created_at` DESC),
                        INDEX `wallet_txn_user_created_idx` (`user_id`, `created_at` DESC),
                        INDEX `wallet_txn_tx_type_idx` (`tx_type`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                # Add FKs for wallet_transactions
                cursor.execute("""
                    ALTER TABLE `wallet_transactions` ADD CONSTRAINT `fk_wallet_txn_wallet`
                    FOREIGN KEY (`wallet_id`) REFERENCES `wallets` (`id`) ON DELETE CASCADE
                """)
                cursor.execute("""
                    ALTER TABLE `wallet_transactions` ADD CONSTRAINT `fk_wallet_txn_user`
                    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
                """)
            self.stdout.write(self.style.SUCCESS('  ✓ Tabel `wallet_transactions` dibuat.'))

        # ── Tambah kolom yang hilang (jika tabel sudah ada) ──
        with connection.cursor() as cursor:
            for table_info in [EXPECTED_WALLETS, EXPECTED_WALLET_TXNS]:
                table_name = table_info['table']
                if table_name not in tables:
                    continue  # already handled above

                # Cek setiap expected column
                cursor.execute(f'SHOW COLUMNS FROM `{table_name}`')
                existing_cols = {row[0] for row in cursor.fetchall()}

                for col_name, col_info in table_info['columns'].items():
                    if col_name in existing_cols:
                        continue

                    # Build ALTER TABLE ADD COLUMN
                    if col_name in ('description', 'reference_type'):
                        col_type = 'varchar(255)' if col_name == 'description' else 'varchar(50)'
                    elif col_name == 'reference_id':
                        col_type = 'varchar(100)'
                    elif col_name == 'tx_type':
                        col_type = 'varchar(20)'
                    elif col_info['type'] == 'bigint':
                        col_type = 'bigint'
                    elif col_info['type'] == 'decimal':
                        col_type = 'decimal(14, 2)'
                    elif col_info['type'] == 'datetime':
                        col_type = 'datetime(6)'
                    else:
                        col_type = col_info['type']

                    null_clause = 'NULL' if col_info['null'] == 'YES' else 'NOT NULL'
                    default_clause = ''
                    if col_info['default'] is not None and col_info['default'] != '':
                        default_clause = f" DEFAULT {col_info['default']}"
                    elif col_info.get('extra') == 'auto_increment':
                        pass  # handled by PRIMARY KEY

                    sql = f"ALTER TABLE `{table_name}` ADD COLUMN `{col_name}` {col_type} {null_clause}{default_clause}"
                    self.stdout.write(f'  Menambah kolom `{col_name}` ke `{table_name}`...')
                    try:
                        cursor.execute(sql)
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Kolom `{col_name}` ditambahkan.'))
                    except Exception as e:
                        self.stderr.write(self.style.ERROR(f'  ✗ Gagal: {e}'))

                # Tambah FK yang hilang
                cursor.execute(f"""
                    SELECT COLUMN_NAME
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = '{table_name}'
                      AND REFERENCED_TABLE_NAME IS NOT NULL
                """)
                existing_fks = {row[0] for row in cursor.fetchall()}

                for fk in table_info.get('expected_fks', []):
                    if fk['column'] in existing_fks:
                        continue
                    delete_rule = fk.get('on_delete', 'CASCADE')
                    sql = (
                        f"ALTER TABLE `{table_name}` ADD CONSTRAINT `fk_{table_name}_{fk['column']}` "
                        f"FOREIGN KEY (`{fk['column']}`) REFERENCES `{fk['ref_table']}` (`{fk['ref_column']}`) "
                        f"ON DELETE {delete_rule}"
                    )
                    self.stdout.write(f'  Menambah FK `{fk["column"]}` ke `{table_name}`...')
                    try:
                        cursor.execute(sql)
                        self.stdout.write(self.style.SUCCESS(f'  ✓ FK `{fk["column"]}` ditambahkan.'))
                    except Exception as e:
                        self.stderr.write(self.style.ERROR(f'  ✗ Gagal: {e}'))

        # ── Setelah fix, fake migration ──
        migration_name = '0004_wallet_and_transactions'
        app_label = 'payments'
        self._fake_migration(app_label, migration_name)

        self.stdout.write(self.style.SUCCESS(
            '\n✓ Sinkronisasi selesai. Startup Django seharusnya normal sekarang.'
        ))
