"""
Management command to audit migration project health.

Usage:
    python manage.py check_migrations                 # Full audit
    python manage.py check_migrations --quick          # Skip syntax & dependency checks
    python manage.py check_migrations --app accounts   # Check only specific app
    python manage.py check_migrations --fix-dangling   # Report suggestions for dangling deps
"""

import ast
import glob
import os
import re
import sys
from collections import defaultdict

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Audit migration health: syntax, circular deps, dangling deps, missing migrations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--quick',
            action='store_true',
            help='Skip syntax & deep dependency checks for a faster overview',
        )
        parser.add_argument(
            '--app',
            type=str,
            default='',
            help='Check only a specific app (e.g., --app accounts)',
        )
        parser.add_argument(
            '--fix-dangling',
            action='store_true',
            help='Report suggestions for fixing dangling dependencies',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed per-file breakdown',
        )

    def handle(self, *args, **options):
        self.quick = options['quick']
        self.target_app = options['app']
        self.fix_dangling = options['fix_dangling']
        self.verbose = options['verbose']

        self.base_dir = settings.BASE_DIR / 'django_backend'
        if not self.base_dir.exists():
            self.base_dir = settings.BASE_DIR

        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n╔══════════════════════════════════════════════════════════╗\n'
            '║         Warungio Migration Health Check                  ║\n'
            '╚══════════════════════════════════════════════════════════╝'
        ))

        # Find all migration files
        self.migrations = self._find_migrations()
        if not self.migrations:
            self.stdout.write(self.style.ERROR('\n❌ No migration files found!'))
            return

        self.stdout.write(f'\n📁 Found {len(self.migrations)} migration files across {len(self._app_list())} apps')
        self.stdout.write('─' * 54)

        # Track overall status
        self.issues = defaultdict(list)
        self.total_checks = 0
        self.passed_checks = 0
        self.failed_checks = 0

        # 1. Check migration directory structure
        self._check_directory_structure()

        # 2. Check Python syntax
        if not self.quick:
            self._check_syntax()

        # 3. Check initial flag consistency
        self._check_initial_flag()

        # 4. Build and analyze dependency graph
        if not self.quick:
            self._build_dependency_graph()

        # 5. Check for apps with models but no migrations
        self._check_missing_migrations()

        # Print report
        self._print_report()

    def _find_migrations(self):
        """Find all migration files."""
        pattern = str(self.base_dir / '*/migrations/0*.py')
        files = glob.glob(pattern)

        # Also check apps/ subdirectory
        pattern2 = str(self.base_dir / 'apps/*/migrations/0*.py')
        files.extend(glob.glob(pattern2))

        if self.target_app:
            files = [f for f in files if self.target_app in f]

        return sorted(files)

    def _app_list(self):
        """Get sorted list of unique app labels from migration files."""
        apps_set = set()
        for fpath in self.migrations:
            parts = fpath.replace('\\', '/').split('/')
            # Find the app name (the directory before 'migrations')
            for i, part in enumerate(parts):
                if part == 'migrations' and i > 0:
                    apps_set.add(parts[i - 1])
                    break
        return sorted(apps_set)

    def _check(self, check_name, passed, detail=''):
        """Record a check result."""
        self.total_checks += 1
        if passed:
            self.passed_checks += 1
        else:
            self.failed_checks += 1
            self.issues[check_name].append(detail)

    def _check_directory_structure(self):
        """Check that each app with migrations has proper __init__.py."""
        self.stdout.write('\n📂 Checking migration directory structure...')

        migration_dirs = set()
        for fpath in self.migrations:
            migration_dirs.add(os.path.dirname(fpath))

        for dirpath in sorted(migration_dirs):
            init_file = os.path.join(dirpath, '__init__.py')
            app_name = os.path.basename(os.path.dirname(dirpath))
            has_init = os.path.exists(init_file)

            if has_init:
                self._check(
                    f'dir_structure.{app_name}',
                    True,
                    f'{app_name}/migrations/__init__.py: ✅'
                )
            else:
                self._check(
                    f'dir_structure.{app_name}',
                    False,
                    f'{app_name}/migrations/: ⚠️  Missing __init__.py!'
                )

    def _check_syntax(self):
        """Check Python syntax of all migration files."""
        self.stdout.write('\n🔍 Checking Python syntax...')

        for fpath in self.migrations:
            filename = '/'.join(fpath.replace('\\', '/').split('/')[-3:])
            try:
                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                ast.parse(content)
                if self.verbose:
                    self.stdout.write(f'  ✅ {filename}')
                self._check(f'syntax.{filename}', True)
            except SyntaxError as e:
                self._check(
                    f'syntax.{filename}',
                    False,
                    f'  ❌ {filename}: SyntaxError at line {e.lineno}: {e.msg}'
                )
            except Exception as e:
                self._check(
                    f'syntax.{filename}',
                    False,
                    f'  ❌ {filename}: {type(e).__name__}: {e}'
                )

    def _check_initial_flag(self):
        """Check that initial = True is set consistently."""
        self.stdout.write('\n🏁 Checking initial flag consistency...')

        for fpath in self.migrations:
            filename = '/'.join(fpath.replace('\\', '/').split('/')[-3:])
            with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            is_initial = 'initial = True' in content
            has_deps = 'dependencies' in content

            # Migration 0001 should be initial=True
            base = os.path.basename(fpath)
            is_first = base == '0001_initial.py' or base.startswith('0001_')

            if is_first and not is_initial:
                self._check(
                    f'initial.{filename}',
                    False,
                    f'  ⚠️  {filename}: First migration but missing `initial = True`'
                )
            else:
                self._check(f'initial.{filename}', True)

    def _build_dependency_graph(self):
        """Build dependency graph and check for circular/dangling deps."""
        self.stdout.write('\n🕸️  Building dependency graph...')

        # Build graph
        graph = {}  # node -> list of dependencies
        node_info = {}  # node -> file path

        for fpath in self.migrations:
            with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            parts = fpath.replace('\\', '/').split('/')
            # Determine app_label
            app_label = None
            for i, part in enumerate(parts):
                if part == 'migrations' and i > 0:
                    app_label = parts[i - 1]
                    break

            if not app_label:
                continue

            fname = os.path.basename(fpath).replace('.py', '')
            node = (app_label, fname)
            node_info[node] = fpath

            # Extract dependencies
            match = re.search(
                r'dependencies\s*=\s*\[(.*?)\]',
                content, re.DOTALL
            )
            deps = []
            if match:
                deps_text = match.group(1)
                # Extract ('app', 'migration_name') tuples
                tuples = re.findall(
                    r"'([^']+)',\s*'([^']+)'",
                    deps_text
                )
                for app, mig_name in tuples:
                    deps.append((app, mig_name))

                # Also check for swappable_dependency
                if 'swappable_dependency' in deps_text:
                    # This references a model, not a migration.
                    # For graph purposes, we note it but don't add as edge
                    pass

            graph[node] = deps

        all_nodes = list(graph.keys())
        self.stdout.write(f'  Nodes in graph: {len(all_nodes)}')

        # Check for circular dependencies via DFS
        self.stdout.write('  Checking for circular dependencies...')
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n: WHITE for n in all_nodes}
        cycle_found = False

        def dfs(node, path=None):
            nonlocal cycle_found
            if path is None:
                path = []
            color[node] = GRAY
            path.append(node)

            for dep in graph.get(node, []):
                if dep in node_info:  # Only check local app deps
                    dep_node = dep
                    if color[dep_node] == GRAY:
                        cycle_found = True
                        cycle_path = ' -> '.join(
                            f'{n[0]}.{n[1]}' for n in path[path.index(dep_node):]
                        )
                        self._check(
                            'circular_dep',
                            False,
                            f'  🔴 CIRCULAR: {dep_node[0]}.{dep_node[1]} ({cycle_path})'
                        )
                        return
                    elif color[dep_node] == WHITE:
                        dfs(dep_node, path)

            color[node] = BLACK
            path.pop()

        for node in all_nodes:
            if color[node] == WHITE:
                dfs(node)

        if not cycle_found:
            self._check('circular_dep', True, '  ✅ No circular dependencies found')

        # Check for dangling dependencies
        self.stdout.write('  Checking for dangling dependencies...')
        dangling_found = False
        suggestions = []

        for node, deps in graph.items():
            for dep in deps:
                if dep not in node_info:
                    # Check if it's a Django internal app
                    django_apps = {
                        'auth', 'contenttypes', 'admin', 'sessions',
                        'messages', 'staticfiles'
                    }
                    if dep[0] in django_apps:
                        continue  # Django internal, OK
                    if dep[1] == '__first__':
                        suggestion = (
                            f'  ⚠️  DANGLING: {node[0]}.{node[1]} -> '
                            f'({dep[0]}, \'{dep[1]}\') — __first__ sentinel '
                            f'(resolves dynamically, prefer specific migration)'
                        )
                        self._check(f'dangling.{node[0]}.{node[1]}', False, suggestion)
                        dangling_found = True

                        if self.fix_dangling:
                            # Find the actual first migration
                            for n in all_nodes:
                                if n[0] == dep[0] and n[1].startswith('0001'):
                                    suggestions.append(
                                        f'  💡 Suggestion: Replace __first__ with '
                                        f'\'{n[1]}\' in {node[0]}.{node[1]}'
                                    )
                                    break
                    else:
                        suggestion = (
                            f'  ❌ DANGLING: {node[0]}.{node[1]} -> '
                            f'({dep[0]}, \'{dep[1]}\') — NOT FOUND in files!'
                        )
                        self._check(f'dangling.{node[0]}.{node[1]}', False, suggestion)
                        dangling_found = True

        if not dangling_found:
            self._check('dangling', True, '  ✅ No dangling dependencies')
        else:
            for s in suggestions:
                self.stdout.write(s)

    def _check_missing_migrations(self):
        """Check for apps that have models but no migrations."""
        self.stdout.write('\n🔎 Checking for apps with models but no migrations...')

        # Get all migration app labels
        mig_apps = set()
        for fpath in self.migrations:
            parts = fpath.replace('\\', '/').split('/')
            for i, part in enumerate(parts):
                if part == 'migrations' and i > 0:
                    label = parts[i - 1]
                    if label == 'apps':
                        label = f'apps.{parts[i - 2]}'
                    mig_apps.add(label)
                    break

        # Check all installed apps
        for app_config in apps.get_app_configs():
            app_label = app_config.label
            has_models = bool(app_config.get_models())
            has_migration = app_label in mig_apps

            if self.target_app and self.target_app != app_label:
                continue

            if has_models and not has_migration:
                self._check(
                    f'missing_migration.{app_label}',
                    False,
                    f'  ⚠️  {app_label}: Has models but NO migrations! '
                    f'Run `python manage.py makemigrations {app_label}`'
                )
            elif has_models and has_migration:
                if self.verbose:
                    self.stdout.write(f'  ✅ {app_label}: {len(app_config.get_models())} models, migrations OK')

        # Check for app migration folders with no models
        for app_label in mig_apps:
            clean_label = app_label.replace('apps.', '')
            try:
                app_config = apps.get_app_config(clean_label)
                if not app_config.get_models():
                    self._check(
                        f'orphan_migration.{app_label}',
                        False,
                        f'  ⚠️  {app_label}: Has migrations but NO models (orphaned?)'
                    )
            except LookupError:
                self._check(
                    f'orphan_migration.{app_label}',
                    False,
                    f'  ⚠️  {app_label}: Has migrations but app NOT in INSTALLED_APPS (zombie!)'
                )

    def _print_report(self):
        """Print final summary report."""
        self.stdout.write('\n' + '=' * 54)
        self.stdout.write(self.style.MIGRATE_HEADING(
            '                   AUDIT REPORT'
        ))
        self.stdout.write('=' * 54)

        total = self.passed_checks + self.failed_checks
        health_pct = (self.passed_checks / total * 100) if total > 0 else 0

        # Summary line
        if self.failed_checks == 0:
            status = self.style.SUCCESS('✅ PASSED')
        elif health_pct >= 80:
            status = self.style.WARNING('⚠️  WARNING')
        else:
            status = self.style.ERROR('❌ FAILED')

        self.stdout.write(f'  Status:     {status}')
        self.stdout.write(f'  Checks:     {total} total')
        self.stdout.write(f'  Passed:     {self.style.SUCCESS(str(self.passed_checks))}')
        self.stdout.write(f'  Failed:     {self.style.ERROR(str(self.failed_checks))}')
        self.stdout.write(f'  Health:     {health_pct:.0f}%')

        # Issues breakdown
        if self.issues:
            self.stdout.write('\n' + self.style.ERROR('── Issues Found ──'))
            for category, items in sorted(self.issues.items()):
                for item in items:
                    self.stdout.write(item)

        # Recommendations
        if self.failed_checks > 0:
            self.stdout.write('\n' + self.style.WARNING('── Recommendations ──'))
            if any('circular' in k for k in self.issues):
                self.stdout.write('  🔧 Fix circular deps by breaking the cycle with a new migration')
            if any('dangling' in k for k in self.issues):
                self.stdout.write(
                    '  🔧 Replace __first__ sentinel with explicit migration names'
                )
            if any('missing_migration' in k for k in self.issues):
                self.stdout.write(
                    '  🔧 Run: python manage.py makemigrations <app_name>'
                )
            if any('orphan' in k for k in self.issues):
                self.stdout.write(
                    '  🔧 Either register the app in INSTALLED_APPS or remove migration folder'
                )
            if any('syntax' in k for k in self.issues):
                self.stdout.write('  🔧 Fix Python syntax errors in migration files')

        self.stdout.write('\n' + '=' * 54)
        self.stdout.write()
