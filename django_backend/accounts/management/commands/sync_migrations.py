"""
Full Django management command: sync_migrations.

Kondisi project: Database MariaDB sudah memiliki seluruh tabel bisnis
(users, orders, products, stores, dll.) tetapi tabel django_migrations
tidak sinkron dengan schema. token_blacklist belum pernah dimigrasikan
sehingga login gagal karena tabel token_blacklist_outstandingtoken tidak ada.

Strategi:
  1. Backup tabel django_migrations sebelum perubahan
  2. Deteksi migration yang sudah tercermin di database:
     - CreateModel → cek apakah tabel exists
     - AddField → cek apakah kolom exists di tabel
     - AddIndex → cek apakah index exists
     - AddConstraint → cek apakah constraint exists
     - AlterField → cek tipe data match
     - dll.
  3. Tandai migration yang already reflected sebagai applied via MigrationRecorder
  4. Jalankan migration yang memang belum ada (termasuk token_blacklist)
  5. Idempotent: aman dijalankan berkali-kali

Usage:
    python manage.py sync_migrations              # Full sync
    python manage.py sync_migrations --dry-run     # Preview only
    python manage.py sync_migrations --fake-all    # Force-fake ALL remaining
    python manage.py sync_migrations --app orders  # Sync only one app
"""

import datetime
import sys
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder
from django.db.migrations.operations import (
    CreateModel, DeleteModel, RenameModel, AlterModelTable,
    AddField, RemoveField, AlterField, RenameField,
    AddIndex, RemoveIndex, AddConstraint, RemoveConstraint,
    AlterUniqueTogether, AlterIndexTogether
)
from django.apps import apps


_DJANGO_TYPE_GROUPS = {
    'IntegerGroup': ['ForeignKey', 'OneToOneField', 'AutoField', 'BigAutoField',
                     'SmallAutoField', 'IntegerField', 'BigIntegerField',
                     'SmallIntegerField', 'PositiveIntegerField',
                     'PositiveSmallIntegerField', 'PositiveBigIntegerField',
                     'BooleanField'],
    'CharGroup': ['CharField', 'SlugField', 'EmailField', 'URLField',
                  'UUIDField', 'FilePathField'],
    'TextGroup': ['TextField', 'JSONField'],
    'DateGroup': ['DateTimeField', 'DateField', 'TimeField'],
    'FloatGroup': ['DecimalField', 'FloatField'],
}

_DB_TYPE_GROUPS = {
    'IntegerGroup': ['int', 'integer', 'tinyint', 'smallint', 'mediumint',
                     'bigint', 'bool', 'boolean', 'serial'],
    'CharGroup': ['varchar', 'char', 'varbinary', 'binary'],
    'TextGroup': ['text', 'tinytext', 'mediumtext', 'longtext', 'json'],
    'DateGroup': ['datetime', 'date', 'time', 'timestamp', 'year'],
    'FloatGroup': ['decimal', 'dec', 'float', 'double', 'real', 'numeric'],
}


def _normalize_django_type(class_name):
    """Normalize Django field class name into a group."""
    for group, members in _DJANGO_TYPE_GROUPS.items():
        if class_name in members:
            return group
    return class_name


def _normalize_db_type(db_type_name):
    """Normalize database type name (e.g. 'varchar') into a group."""
    lower = db_type_name.lower()
    for group, members in _DB_TYPE_GROUPS.items():
        if lower in members or any(m in lower for m in members):
            return group
    return db_type_name


def _get_table_name(app_label, model_name):
    """Resolve actual db_table name from a model."""
    try:
        model = apps.get_model(app_label, model_name)
        return model._meta.db_table
    except LookupError:
        return f"{app_label}_{model_name.lower()}"


def _get_column_name(app_label, model_name, field_name):
    """Resolve actual column name from a model field."""
    try:
        model = apps.get_model(app_label, model_name)
        field = model._meta.get_field(field_name)
        return field.column
    except Exception:
        # Fallback pattern: ForeignKey -> field_name + '_id'
        return f"{field_name}_id" if field_name.endswith('_id') else field_name


class Command(BaseCommand):
    help = "Sync Django migrations with pre-existing database (backup + per-op detection + token_blacklist)"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Preview only — no DB changes')
        parser.add_argument('--fake-all', action='store_true',
                            help='Force-fake ALL remaining migrations')
        parser.add_argument('--app', type=str, default='',
                            help='Sync only a specific app (e.g., --app orders)')
        parser.add_argument('--no-backup', action='store_true',
                            help='Skip django_migrations backup')

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.fake_all = options['fake_all']
        self.target_app = options['app']
        self.no_backup = options['no_backup']

        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n═══ Warungio Migration Sync (Full) ═══'
        ))

        # 1. Backup
        if not self.dry_run and not self.no_backup:
            self._backup_migrations_table()

        # 2. Load migration graph
        self.stdout.write('Loading migration graph...')
        loader = MigrationLoader(connection)
        graph = loader.graph
        recorder = MigrationRecorder(connection)
        applied = loader.applied_migrations
        self.stdout.write(f'  Applied in DB: {len(applied)} migrations')

        # 3. Get DB schema
        self.stdout.write('Inspecting database schema...')
        existing_tables = set(connection.introspection.table_names())
        self.stdout.write(f'  Tables found: {len(existing_tables)}')

        # 4. Prepare schema cache (columns, constraints, descriptions)
        cursor = connection.cursor()
        table_columns = {}
        table_constraints = {}
        table_descriptions = {}
        for table in existing_tables:
            try:
                desc = connection.introspection.get_table_description(cursor, table)
                table_descriptions[table] = desc
                table_columns[table] = {col.name.lower() for col in desc}
            except Exception:
                table_descriptions[table] = []
                table_columns[table] = set()
            try:
                table_constraints[table] = connection.introspection.get_constraints(
                    cursor, table
                )
            except Exception:
                table_constraints[table] = {}

        # 5. Topo-sort all migrations
        all_migrations = self._topo_sort(graph)
        self.stdout.write(f'  Total in graph: {len(all_migrations)} migrations\n')

        # 6. Determine fate per migration
        to_fake = []
        to_run = []
        currently_applied = set(applied)

        for node in all_migrations:
            app_label, migration_name = node

            if self.target_app and app_label != self.target_app:
                continue
            if node in applied:
                continue

            # Check deps met
            deps_met = True
            try:
                mig = graph.nodes[node]
                for dep in mig.dependencies:
                    if dep in graph.nodes and dep not in currently_applied:
                        deps_met = False
                        break
            except KeyError:
                pass

            if not deps_met:
                to_run.append(node)
                continue

            if self.fake_all:
                to_fake.append(node)
                currently_applied.add(node)
                continue

            # Check if migration is already reflected in DB
            try:
                mig_obj = graph.nodes[node]
            except KeyError:
                to_run.append(node)
                continue

            is_reflected, details = self._check_operations_reflected(
                mig_obj, app_label, existing_tables,
                table_columns, table_constraints, table_descriptions
            )

            if is_reflected:
                to_fake.append(node)
                currently_applied.add(node)
            else:
                to_run.append(node)

        # 7. Report + Apply
        self._print_report(to_fake, to_run, self.dry_run)

        if to_fake and not self.dry_run:
            self.stdout.write(self.style.SUCCESS(f'\nFaking {len(to_fake)} migrations...'))
            for app_lbl, mig_name in to_fake:
                try:
                    recorder.record_applied(app_lbl, mig_name)
                    self.stdout.write(f'  ✅ {app_lbl}.{mig_name}')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'  ❌ {app_lbl}.{mig_name}: {e}'
                    ))
            self.stdout.write(self.style.SUCCESS('Faking complete.'))

        # 8. Always run migrate for truly missing migrations (incl. token_blacklist)
        if not self.dry_run:
            self.stdout.write(self.style.WARNING(
                '\nRunning migrate to apply any remaining migrations...'
            ))
            call_command('migrate', no_input=True)
            self.stdout.write(self.style.SUCCESS('Migration sync complete.'))

    # ------------------------------------------------------------------
    # BACKUP
    # ------------------------------------------------------------------
    def _backup_migrations_table(self):
        """Backup django_migrations table before making changes."""
        tables = connection.introspection.table_names()
        if 'django_migrations' not in tables:
            self.stdout.write('django_migrations table does not exist — no backup needed.')
            return

        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup = f'django_migrations_backup_{ts}'
        self.stdout.write(self.style.WARNING(f'Backing up django_migrations -> {backup}...'))
        with connection.cursor() as c:
            c.execute(f'CREATE TABLE `{backup}` SELECT * FROM django_migrations')
        self.stdout.write(self.style.SUCCESS(f'Backup saved as `{backup}`.'))

    # ------------------------------------------------------------------
    # GRAPH
    # ------------------------------------------------------------------
    def _topo_sort(self, graph):
        visited = set()
        result = []

        def visit(node):
            if node in visited:
                return
            if node in graph.nodes:
                for dep in graph.nodes[node].dependencies:
                    if dep in graph.nodes:
                        visit(dep)
            visited.add(node)
            result.append(node)

        for node in sorted(graph.nodes.keys()):
            visit(node)
        return result

    # ------------------------------------------------------------------
    # PER-OPERATION DETECTION
    # ------------------------------------------------------------------
    def _check_operations_reflected(
        self, migration, app_label, existing_tables,
        table_columns, table_constraints, table_descriptions
    ):
        """
        Periksa setiap operasi dalam migration.
        Returns (is_reflected, details).
        """
        total_ops = len(migration.operations)
        reflected_ops = 0

        for op in migration.operations:
            reflected = self._check_single_op(
                op, app_label, existing_tables,
                table_columns, table_constraints, table_descriptions
            )
            if reflected:
                reflected_ops += 1

        # If ALL operations are reflected -> whole migration is reflected
        if total_ops == 0:
            return (True, 'no ops')
        return (reflected_ops == total_ops, f'{reflected_ops}/{total_ops} ops reflected')

    def _check_single_op(self, op, app_label, existing_tables,
                          table_columns, table_constraints, table_descriptions):
        """Periksa satu operasi migration."""
        # ── helpers ──
        def tbl(mn):
            return _get_table_name(app_label, mn)

        def col(mn, fn):
            return _get_column_name(app_label, mn, fn).lower()

        def cols(s):
            return {c.lower() for c in s}

        # ── CreateModel ──
        if isinstance(op, CreateModel):
            db_table = tbl(op.name)
            if db_table not in existing_tables:
                return False
            # Cek kolom
            db_cols = table_columns.get(db_table, set())
            for fname, finst in op.fields:
                if finst.__class__.__name__ == 'GenericRelation':
                    continue
                if finst.__class__.__name__ == 'ManyToManyField':
                    # Cek join table
                    try:
                        model = apps.get_model(app_label, op.name)
                        join = model._meta.get_field(fname).m2m_db_table()
                    except Exception:
                        join = f'{db_table}_{fname}'
                    if join not in existing_tables:
                        return False
                    continue
                cname = col(op.name, fname)
                if cname not in db_cols:
                    return False
            return True

        # ── DeleteModel ──
        if isinstance(op, DeleteModel):
            return tbl(op.name) not in existing_tables

        # ── RenameModel ──
        if isinstance(op, RenameModel):
            return (tbl(op.old_name) not in existing_tables
                    and tbl(op.new_name) in existing_tables)

        # ── AlterModelTable ──
        if isinstance(op, AlterModelTable):
            return op.table in existing_tables

        # ── AddField ──
        if isinstance(op, AddField):
            db_table = tbl(op.model_name)
            if db_table not in existing_tables:
                return False
            if op.field.__class__.__name__ == 'ManyToManyField':
                try:
                    model = apps.get_model(app_label, op.model_name)
                    join = model._meta.get_field(op.name).m2m_db_table()
                except Exception:
                    join = f'{db_table}_{op.name}'
                return join in existing_tables
            if op.field.__class__.__name__ == 'GenericRelation':
                return True
            db_cols = table_columns.get(db_table, set())
            return col(op.model_name, op.name) in db_cols

        # ── RemoveField ──
        if isinstance(op, RemoveField):
            db_table = tbl(op.model_name)
            if db_table not in existing_tables:
                return True
            db_cols = table_columns.get(db_table, set())
            return col(op.model_name, op.name) not in db_cols

        # ── AlterField ──
        if isinstance(op, AlterField):
            db_table = tbl(op.model_name)
            if db_table not in existing_tables:
                return False
            cname = col(op.model_name, op.name)
            db_cols = table_columns.get(db_table, set())
            if cname not in db_cols:
                return False
            # Bandingkan tipe (gunakan cache table_descriptions jika ada)
            desc = table_descriptions.get(db_table, [])
            if not desc:
                return True  # skip type check if no cached description
            for col_desc in desc:
                if col_desc.name.lower() == cname:
                    db_type = connection.introspection.data_types_reverse.get(
                        col_desc.type_code
                    )
                    if db_type:
                        norm_db = _normalize_db_type(db_type)
                        norm_mig = _normalize_django_type(op.field.__class__.__name__)
                        if norm_db != norm_mig:
                            return False
                    return True
            return False

        # ── RenameField ──
        if isinstance(op, RenameField):
            db_table = tbl(op.model_name)
            if db_table not in existing_tables:
                return False
            db_cols = table_columns.get(db_table, set())
            old_c = col(op.model_name, op.old_name)
            new_c = col(op.model_name, op.new_name)
            return old_c not in db_cols and new_c in db_cols

        # ── AddIndex ──
        if isinstance(op, AddIndex):
            db_table = tbl(op.model_name)
            if db_table not in existing_tables:
                return False
            constraints = table_constraints.get(db_table, {})
            # Cek by name
            if op.index.name and op.index.name in constraints:
                idx = constraints[op.index.name]
                if idx.get('index'):
                    return True
            # Cek by columns
            idx_cols = [col(op.model_name, f) for f in op.index.fields]
            for c_name, c_val in constraints.items():
                if c_val.get('index'):
                    c_cols = [c.lower() for c in c_val.get('columns', [])]
                    if c_cols == idx_cols:
                        return True
            return False

        # ── RemoveIndex ──
        if isinstance(op, RemoveIndex):
            db_table = tbl(op.model_name)
            if db_table not in existing_tables:
                return True
            constraints = table_constraints.get(db_table, {})
            return op.name not in constraints

        # ── AddConstraint ──
        if isinstance(op, AddConstraint):
            db_table = tbl(op.model_name)
            if db_table not in existing_tables:
                return False
            constraints = table_constraints.get(db_table, {})
            # Cek by name
            if op.constraint.name and op.constraint.name in constraints:
                return True
            # UniqueConstraint by columns
            if op.constraint.__class__.__name__ == 'UniqueConstraint':
                uc_cols = [col(op.model_name, f) for f in op.constraint.fields]
                for c_val in constraints.values():
                    if c_val.get('unique'):
                        if [c.lower() for c in c_val.get('columns', [])] == uc_cols:
                            return True
            return False

        # ── RemoveConstraint ──
        if isinstance(op, RemoveConstraint):
            db_table = tbl(op.model_name)
            if db_table not in existing_tables:
                return True
            constraints = table_constraints.get(db_table, {})
            return op.name not in constraints

        # ── AlterUniqueTogether ──
        if isinstance(op, AlterUniqueTogether):
            db_table = tbl(op.name)
            if db_table not in existing_tables:
                return False
            if not op.unique_together:
                return True
            constraints = table_constraints.get(db_table, {})
            for ut in op.unique_together:
                ut_cols = [col(op.name, f) for f in ut]
                found = False
                for c_val in constraints.values():
                    if c_val.get('unique'):
                        if [c.lower() for c in c_val.get('columns', [])] == ut_cols:
                            found = True
                            break
                if not found:
                    return False
            return True

        # ── AlterIndexTogether ──
        if isinstance(op, AlterIndexTogether):
            db_table = tbl(op.name)
            if db_table not in existing_tables:
                return False
            if not op.index_together:
                return True
            constraints = table_constraints.get(db_table, {})
            for it in op.index_together:
                it_cols = [col(op.name, f) for f in it]
                found = False
                for c_val in constraints.values():
                    if c_val.get('index'):
                        if [c.lower() for c in c_val.get('columns', [])] == it_cols:
                            found = True
                            break
                if not found:
                    return False
            return True

        # ── Non-schema ops (AlterModelOptions, RunPython, RunSQL) ──
        return True

    # ------------------------------------------------------------------
    # REPORT
    # ------------------------------------------------------------------
    def _print_report(self, to_fake, to_run, dry_run):
        label = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(f'\n{"─" * 48}')
        self.stdout.write(f'{label}SYNC RESULTS')
        self.stdout.write(f'  To fake (already in DB): {len(to_fake)}')
        self.stdout.write(f'  To run  (missing):       {len(to_run)}')
        self.stdout.write(f'{"─" * 48}')

        if to_fake:
            self.stdout.write(self.style.SUCCESS('Fake:'))
            for app, name in to_fake[:15]:
                self.stdout.write(f'  ⏩ {app}.{name}')
            if len(to_fake) > 15:
                self.stdout.write(f'  ... and {len(to_fake) - 15} more')

        if to_run:
            self.stdout.write(self.style.WARNING('Run:'))
            for app, name in to_run[:15]:
                self.stdout.write(f'  ▶️  {app}.{name}')
            if len(to_run) > 15:
                self.stdout.write(f'  ... and {len(to_run) - 15} more')

        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\n⚠️  DRY RUN — no changes were made. Run without --dry-run to apply.'
            ))
