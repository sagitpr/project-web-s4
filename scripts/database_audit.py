"""
Warungio Database Audit Script
Generates comprehensive report of all models, tables, relationships, and indexes.
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['DJANGO_ALLOW_HOSTS'] = '*'

# Must set PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'django_backend'))

import django
django.setup()

from django.apps import apps
from django.db import connection
from collections import defaultdict

def get_table_columns(table_name):
    """Get column info from actual database."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            return {row[1]: {'type': row[2], 'nullable': not row[3], 'default': row[4], 'pk': bool(row[5])} for row in cursor.fetchall()}
    except:
        return None

def get_indexes(table_name):
    """Get index info from actual database."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"PRAGMA index_list('{table_name}')")
            indexes = []
            for row in cursor.fetchall():
                cursor.execute(f"PRAGMA index_info('{row[1]}')")
                cols = [r[2] for r in cursor.fetchall()]
                indexes.append({'name': row[1], 'unique': bool(row[2]), 'columns': cols})
            return indexes
    except:
        return []

def get_foreign_keys(table_name):
    """Get foreign key info from actual database."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"PRAGMA foreign_key_list('{table_name}')")
            return [{'column': r[3], 'references_table': r[2], 'references_column': r[4]} for r in cursor.fetchall()]
    except:
        return []

print("=" * 100)
print("  WARUNGIO DATABASE AUDIT REPORT")
print("=" * 100)

# Phase 1: Database Configuration
print("\n\n--- PHASE 1: DATABASE CONFIGURATION ---")
db = connection.settings_dict
print(f"  Engine:     {db['ENGINE']}")
print(f"  Name:       {db['NAME']}")
print(f"  Host:       {db.get('HOST', 'N/A')}")
print(f"  Port:       {db.get('PORT', 'N/A')}")
print(f"  User:       {db.get('USER', 'N/A')}")
print(f"  Tables:     {len(connection.introspection.table_names())}")

# Phase 2 & 3: Model Audit + Migration Audit
print("\n\n--- PHASE 2 & 3: MODEL + MIGRATION AUDIT ---")
print(f"{'App':<20} {'Model':<25} {'Table':<25} {'Fields':<8} {'Has Table':<12} {'Has Migration':<14} {'Rows':<8}")
print("-" * 120)

all_models = apps.get_models()
table_names = connection.introspection.table_names()
total_models = 0
total_tables = 0
missing_tables = []
missing_migrations = []

for model in sorted(all_models, key=lambda m: (m._meta.app_label, m._meta.model_name)):
    app_label = model._meta.app_label
    model_name = model.__name__
    table_name = model._meta.db_table
    field_count = len(model._meta.fields)
    has_table = table_name in table_names
    
    # Check if app has migrations
    from django.db.migrations.recorder import MigrationRecorder
    applied = MigrationRecorder.Migration.objects.filter(app__exact=app_label).count()
    
    rows = 0
    if has_table:
        try:
            rows = model.objects.count()
        except:
            pass
    
    status = "[OK]" if has_table else "[MISS]"
    mig_status = "[OK]" if applied > 0 else "[MISS]"
    
    print(f"{app_label:<20} {model_name:<25} {table_name:<25} {field_count:<8} {status:<12} {mig_status:<14} {rows:<8}")
    
    total_models += 1
    if has_table:
        total_tables += 1
    else:
        missing_tables.append((app_label, model_name, table_name))

print(f"\n  Total Models: {total_models}")
print(f"  Tables Created: {total_tables}")
print(f"  Missing Tables: {len(missing_tables)}")

if missing_tables:
    print("\n  ❌ Missing Tables:")
    for app, model, table in missing_tables:
        print(f"    - {app}.{model} -> {table}")

# Phase 4: Database Structure Comparison
print("\n\n--- PHASE 4: DATABASE STRUCTURE COMPARISON ---")
issues = []

for model in all_models:
    table_name = model._meta.db_table
    if table_name not in table_names:
        continue
    
    actual_columns = get_table_columns(table_name)
    if not actual_columns:
        continue
    
    # Expected columns from Django model
    expected_fields = {}
    for field in model._meta.fields:
        col_name = field.column
        db_type = field.db_type(connection)
        expected_fields[col_name] = db_type
    
    # Check for missing columns
    for col_name in expected_fields:
        if col_name not in actual_columns:
            issues.append(f"MISSING COLUMN: {table_name}.{col_name} ({expected_fields[col_name]})")
    
    # Check for extra columns
    for col_name in actual_columns:
        if col_name not in expected_fields and col_name not in ('id',):
            issues.append(f"EXTRA COLUMN: {table_name}.{col_name} ({actual_columns[col_name]['type']})")

if issues:
    print(f"  Found {len(issues)} structure issues:")
    for issue in issues:
        print(f"    ⚠ {issue}")
else:
    print("  ✅ No structure issues found - all columns match.")

# Phase 5: Relationship Audit
print("\n\n--- PHASE 5: RELATIONSHIP AUDIT ---")
print(f"{'Source Model':<25} {'Field':<20} {'Type':<12} {'Target Model':<25} {'on_delete':<20}")
print("-" * 110)

relation_issues = []

for model in all_models:
    for field in model._meta.fields:
        if field.is_relation:
            rel_name = field.name
            rel_type = field.many_to_many and 'M2M' or field.one_to_many and 'FK' or field.one_to_one and 'O2O' or 'REL'
            target = field.related_model.__name__ if field.related_model else 'DELETED'
            on_delete = field.remote_field.on_delete.__name__ if hasattr(field.remote_field, 'on_delete') else 'N/A'
            
            print(f"{model.__name__:<25} {rel_name:<20} {rel_type:<12} {target:<25} {on_delete:<20}")
            
            if field.related_model is None:
                relation_issues.append(f"BROKEN FK: {model.__name__}.{rel_name} -> DELETED MODEL")

    # M2M fields
    if hasattr(model._meta, 'many_to_many'):
        for field in model._meta.many_to_many:
            rel_name = field.name
            rel_type = 'M2M'
            target = field.related_model.__name__ if field.related_model else 'DELETED'
            through = field.remote_field.through.__name__ if hasattr(field.remote_field, 'through') and field.remote_field.through else 'auto'
            
            print(f"{model.__name__:<25} {rel_name:<20} {rel_type:<12} {target:<25} through={through}")

if relation_issues:
    print(f"\n  ❌ Relationship Issues:")
    for issue in relation_issues:
        print(f"    {issue}")
else:
    print("\n  ✅ All relationships are valid.")

# Phase 6: Index Audit
print("\n\n--- PHASE 6: INDEX AUDIT ---")
print(f"{'Table':<25} {'Index Name':<30} {'Columns':<25} {'Unique':<8}")
print("-" * 90)

for model in all_models:
    table_name = model._meta.db_table
    if table_name not in table_names:
        continue
    
    actual_indexes = get_indexes(table_name)
    for idx in actual_indexes:
        print(f"{table_name:<25} {idx['name']:<30} {','.join(idx['columns']):<25} {'✅' if idx['unique'] else '❌':<8}")

# Phase 7: Foreign Key Audit
print("\n\n--- PHASE 7: FOREIGN KEY AUDIT ---")
for model in all_models:
    table_name = model._meta.db_table
    if table_name not in table_names:
        continue
    
    fks = get_foreign_keys(table_name)
    if fks:
        print(f"\n  {table_name}:")
        for fk in fks:
            print(f"    {fk['column']} -> {fk['references_table']}.{fk['references_column']}")

# Phase 8: Model Coverage Summary
print("\n\n--- PHASE 8: APP COVERAGE SUMMARY ---")
print(f"{'App':<20} {'Models':<8} {'Tables':<8} {'Relationships':<14} {'Status':<12}")
print("-" * 65)

app_stats = defaultdict(lambda: {'models': 0, 'tables': 0, 'relations': 0})
for model in all_models:
    app_label = model._meta.app_label
    app_stats[app_label]['models'] += 1
    table_name = model._meta.db_table
    if table_name in table_names:
        app_stats[app_label]['tables'] += 1
    for field in model._meta.fields:
        if field.is_relation:
            app_stats[app_label]['relations'] += 1

for app, stats in sorted(app_stats.items()):
    ok = stats['models'] == stats['tables']
    status = "[OK] COMPLETE" if ok else "[MISS] INCOMPLETE"
    print(f"{app:<20} {stats['models']:<8} {stats['tables']:<8} {stats['relations']:<14} {status:<12}")

print("\n\n--- AUDIT COMPLETE ---")
print(f"Database: {db['ENGINE'].split('.')[-1]} -> {db['NAME']}")
