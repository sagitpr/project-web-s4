# Migration Repair Plan

> **Date**: July 20, 2026
> **Scope**: Fix all inconsistencies identified in DATABASE_CONSISTENCY_REPORT.md and MIGRATION_AUDIT_REPORT.md
> **Principle**: **Never modify already applied migrations. Never fake migrations unless absolutely required and justified.**
> **Strategy**: Forward-only repairs with minimal intervention.

---

## Inconsistency Summary

| # | Issue | App | Severity | Requires Repair? |
|---|-------|-----|----------|-----------------|
| 1 | Ghost migration entry | orders | Medium | ✅ Yes |
| 2 | Pending migrations | ai_intelligence | Low | ✅ Yes (normal) |
| 3 | Pending migrations | engagement | Low | ✅ Yes (normal) |

**Note**: All other apps (18/21) have zero issues. All 99 physical tables match their models perfectly.

---

## Repair 1: Clean Ghost Migration Entry

### Problem
Migration `orders.0010_alter_admin_fee_seller` exists in `django_migrations` table but the migration file was removed/renamed. The actual migration history on disk uses `0010_remove_order_admin_fee_seller_packingsession_and_more` instead.

### Evidence
```sql
-- Currently in django_migrations:
('orders', '0010_alter_admin_fee_seller')
('orders', '0010_remove_order_admin_fee_seller_packingsession_and_more')

-- Files on disk:
orders/migrations/0010_remove_order_admin_fee_seller_packingsession_and_more.py
orders/migrations/0011_fix_missing_tables.py
orders/migrations/0012_alter_order_admin_fee_seller.py
```

### Why This Happened
The migration `0010_alter_admin_fee_seller` was likely:
1. Created and applied to add the `admin_fee_seller` field to `Order`
2. Later, the migration was **renamed** (not recreated) to `0010_remove_order_admin_fee_seller_packingsession_and_more` when additional schema changes were merged into it
3. The old name was never removed from `django_migrations`

### Repair Steps

**Step 1: Verify the ghost entry is safe to delete**
```sql
-- Check that the ghost migration's operations are covered by the existing migration
SELECT name, applied FROM django_migrations 
WHERE app = 'orders' AND name LIKE '0010%';
```

**Step 2: Remove the ghost entry from django_migrations**
```sql
-- Run directly on the database
DELETE FROM django_migrations 
WHERE app = 'orders' AND name = '0010_alter_admin_fee_seller';
```

**Step 3: Verify the fix**
```bash
python manage.py showmigrations orders
```
Expected output — clean migration chain:
```
orders
 [X] 0001_initial
 [X] 0002_...
 [X] 0009_add_admin_fee_back
 [X] 0010_remove_order_admin_fee_seller_packingsession_and_more   ← only one 0010
 [X] 0011_fix_missing_tables
 [X] 0012_alter_order_admin_fee_seller
```

### Why Not Fake?
- **Faking is not needed** because the database state is already correct
- The ghost migration is a **stale record**, not a missing migration
- All physical tables already have the correct schema
- `makemigrations --check --dry-run` confirms "No changes detected"

---

## Repair 2: Apply Pending ai_intelligence Migration

### Problem
`ai_intelligence` app has `0001_initial` migration that hasn't been applied. 14 models and ~30 indexes need to be created.

### Why This Happened
The `ai_intelligence` app was added to `INSTALLED_APPS` (in `config/settings.py`) and its migration was generated (`makemigrations`) but never applied (`migrate`).

### Repair Steps

**Step 1: Preview SQL**
```bash
python manage.py sqlmigrate ai_intelligence 0001_initial
```

**Step 2: Apply migration**
```bash
python manage.py migrate ai_intelligence 0001_initial
```

**Step 3: Verify**
```bash
python manage.py showmigrations ai_intelligence
```
Expected output:
```
ai_intelligence
 [X] 0001_initial
```

**Tables created** (14):
- `ai_digital_twins`
- `ai_marketplace_health`
- `ai_demand_predictions`
- `ai_pricing_recommendations`
- `ai_sales_forecasts`
- `ai_customer_segments`
- `ai_user_segments`
- `ai_gamification_profiles`
- `ai_challenges`
- `ai_challenge_progress`
- `ai_coach_insights`
- `ai_shopping_insights`
- `ai_model_registry`
- `ai_experiments`

### Data Loss Risk
**None**. These are new tables with no existing data.

---

## Repair 3: Apply Pending engagement Migration

### Problem
`engagement` app has `0001_initial` migration that hasn't been applied. 16 models and ~40 indexes need to be created.

### Why This Happened
Same as ai_intelligence — the `engagement` app was recently added.

### Repair Steps

**Step 1: Preview SQL**
```bash
python manage.py sqlmigrate engagement 0001_initial
```

**Step 2: Apply migration**
```bash
python manage.py migrate engagement 0001_initial
```

**Step 3: Verify**
```bash
python manage.py showmigrations engagement
```
Expected output:
```
engagement
 [X] 0001_initial
```

**Tables created** (16):
- `engagement_user_profiles`
- `engagement_behavior_events`
- `engagement_activity_logs`
- `engagement_churn_predictions`
- `engagement_device_tokens`
- `engagement_notification_templates`
- `engagement_campaigns`
- `engagement_notification_queue`
- `engagement_delivery_logs`
- `engagement_notification_analytics`
- `engagement_ab_tests`
- `engagement_quiet_hours`
- `engagement_notification_cooldowns`
- `engagement_signals`
- `engagement_preference_extensions`

### Data Loss Risk
**None**. These are new tables with no existing data.

---

## Repair 4: Apply All Pending Migrations (Combined)

The simplest approach is to apply all pending migrations at once:

```bash
python manage.py migrate
```

This will:
1. ✅ Apply `ai_intelligence.0001_initial` (14 tables)
2. ✅ Apply `engagement.0001_initial` (16 tables)
3. Leave all other apps unchanged

---

## Validation Checklist (Post-Repair)

- [ ] `python manage.py showmigrations` — all apps show `[X]` (applied)
- [ ] `python manage.py makemigrations --check` — "No changes detected"
- [ ] `python manage.py migrate --plan` — empty plan
- [ ] All 30 new tables exist in database:
  - 14 `ai_*` tables
  - 16 `engagement_*` tables
- [ ] Ghost migration entry removed from `django_migrations`
- [ ] Total migrations: 77 - 1 (ghost) + 2 (new) = **78 applied** (or using ghost cleanup: original 77 entries, after deletion 76, plus 2 new = **78**)

---

## Rollback Plan

If any repair step causes problems:

| Repair | Rollback Command | Data Loss? |
|--------|-----------------|------------|
| 1 (ghost cleanup) | `INSERT INTO django_migrations (app, name, applied) VALUES ('orders', '0010_alter_admin_fee_seller', NOW())` | None |
| 2 (ai_intelligence) | `python manage.py migrate ai_intelligence zero` | Yes — all 14 tables dropped |
| 3 (engagement) | `python manage.py migrate engagement zero` | Yes — all 16 tables dropped |

---

## Execution Order

```
Step 1: Clean ghost migration (requires direct DB access)
Step 2: python manage.py migrate
Step 3: python manage.py makemigrations --check
Step 4: python manage.py showmigrations
Step 5: Verify all tables present
```

**Total downtime required**: Near zero (new tables only, no data migrations)
**Risk level**: Low
**Can be rolled back**: Yes
