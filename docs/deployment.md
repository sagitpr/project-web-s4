# WARUNGIO MARKETPLACE — DEPLOYMENT GUIDE

> **Version:** 2.0 — Migration-sync permanent solution  
> **Last updated:** July 2026

---

## 📋 Daftar Isi

1. [Deployment Overview](#1-deployment-overview)
2. [Quick Start (Pertama Kali)](#2-quick-start-pertama-kali)
3. [Deployment Biasa](#3-deployment-biasa)
4. [Migration Sync System](#4-migration-sync-system)
5. [Docker Entrypoint Flow](#5-docker-entrypoint-flow)
6. [Environment Variables](#6-environment-variables)
7. [Troubleshooting](#7-troubleshooting)
8. [FAQ](#8-faq)

---

## 1. Deployment Overview

Warungio menggunakan arsitektur **Django REST API** dengan **Docker Compose** sebagai
platform deployment utama. Setiap deploy menjalankan urutan berikut secara otomatis:

```
git pull
  → docker compose up -d --build
    → Container start
      → Wait for MariaDB
      → sync_migrations (backup → fake existing → migrate missing)
      → migrate (safety net)
      → collectstatic
      → Daphne ASGI server
```

### Architecture

```
Browser (HTML/CSS/JS)
       │
       ▼
   Nginx (reverse proxy, serve static/media)
       │
       ▼
   Daphne (Django ASGI)
       │
       ├── MariaDB (database)
       ├── Redis (cache, channels)
       └── Volumes (static, media, logs)
```

---

## 2. Quick Start (Pertama Kali)

Untuk deployment **pertama kali** di server baru:

```bash
# 1. Clone repository
git clone <repo-url> warungio
cd warungio

# 2. Setup environment
cp .env.example .env
# Edit .env — isi DB_PASS, DJANGO_SECRET_KEY, dll.

# 3. Build & start
docker compose up -d --build

# 4. Cek health
curl http://localhost:8000/health/

# 5. Cek log migration
docker compose logs django | grep -i "sync\|migrate\|error"
```

> **PENTING:** Pada deploy pertama, `sync_migrations` akan:
> - Mendeteksi semua tabel yang sudah ada di database
> - Membandingkannya dengan migration files
> - Melakukan **fake** untuk migration yang sudah tercermin di DB
> - Menjalankan **migrate** untuk yang benar-benar belum ada (misal: `token_blacklist`)

---

## 3. Deployment Biasa

Untuk deployment setelah perubahan kode:

### 3.1. Deploy Lengkap (Rekomendasi)

```bash
# Dari project root:
./scripts/deploy.sh
```

Script ini akan:
1. `git pull --ff-only` — mengambil kode terbaru
2. `docker compose build` — rebuild image
3. `docker compose up -d` — restart services
4. Health check — tunggu sampai HTTP 200

### 3.2. One-liner (Tanpa Script)

```bash
git pull && docker compose up -d --build
```

### 3.3. Force Rebuild (No Cache)

```bash
./scripts/deploy.sh --no-cache
```

### 3.4. Cek Health Saja

```bash
./scripts/deploy.sh --check
```

> **Semua metode di atas** akan menjalankan `sync_migrations → migrate → collectstatic`
> secara otomatis di dalam container. Database tidak perlu dihapus.

---

## 4. Migration Sync System

### 4.1. Masalah yang Diselesaikan

Database MariaDB sudah memiliki seluruh tabel bisnis (`users`, `orders`, `products`,
`stores`, dll.) tetapi tabel `django_migrations` tidak sinkron. Akibatnya:

- `python manage.py migrate` gagal karena tabel seperti `users` sudah ada
- `token_blacklist` belum pernah dimigrasi → login menghasilkan HTTP 500

### 4.2. Solusi: `sync_migrations`

Management command: `python manage.py sync_migrations`

Algoritma:

```
1. Backup django_migrations → django_migrations_backup_<timestamp>
2. Load migration graph dari semua apps
3. Inspect semua tabel di database
4. Untuk setiap migration yang belum di-applied:
   a. Parsing setiap operasi (CreateModel, AddField, AddIndex, dll.)
   b. Cek apakah struktur sudah ada di database:
      - CreateModel → cek tabel exists
      - AddField → cek kolom exists
      - AddIndex → cek index exists
      - AddConstraint → cek constraint exists
      - AlterField → cek tipe data cocok
      - dll.
   c. Jika semua operasi sudah reflected → fake migration
   d. Jika ada operasi yang belum reflected → tandai untuk di-run
5. Fake semua migration yang sudah reflected
6. Jalankan `python manage.py migrate` untuk yang benar-benar belum ada
```

### 4.3. Usage

```bash
# Standard — backup + sync + migrate
python manage.py sync_migrations

# Dry run — lihat apa yang akan dilakukan tanpa perubahan
python manage.py sync_migrations --dry-run

# Emergency — force-fake semua (hanya jika yakin struktur sudah benar)
python manage.py sync_migrations --fake-all

# Per-app — sync hanya satu app
python manage.py sync_migrations --app orders

# Skip backup
python manage.py sync_migrations --no-backup
```

### 4.4. Idempotent

Command ini **aman dijalankan berkali-kali**. Tidak akan:
- Menduplikasi data
- Menghapus tabel
- Merusak data existing

Setiap kali dijalankan:
- Migration yang sudah di-record akan di-skip
- Migration yang belum di-record akan dicek satu per satu
- Hanya migration yang benar-benar baru yang akan di-fake atau di-run

### 4.5. Output Example

```
═══════════════════════════════════════════
   Warungio Migration Sync
═══════════════════════════════════════════

📤 Backing up django_migrations → django_migrations_backup_20260701_120000...

📦 Loading migration graph...
   Applied in DB:   12 migrations

🔍 Inspecting database schema...
   Tables found:    45

   Total in graph:  36 migrations

────────────────────────────────────────────────────────
  SYNC RESULTS
    ✅ Already in DB (fake):  20
    ▶️  Missing (migrate):    4
────────────────────────────────────────────────────────

  ⏩ Will fake (already reflected in DB):
    accounts.0001_initial
    products.0001_initial
    orders.0001_initial
    ...

  ▶️  Will run (missing from DB):
    token_blacklist.0001_initial
    ...

⏩ Faking 20 migration(s) (already in DB)...
   Faking complete.

▶️  Running migrate for 4 missing migration(s)...
   Migrations for 'token_blacklist':
     token_blacklist.0001_initial
   ...

═══════════════════════════════════════════
   ✅ Migration sync complete.
═══════════════════════════════════════════
```

---

## 5. Docker Entrypoint Flow

File: `docker-entrypoint.sh`

Urutan startup di dalam container:

```
[1/6] Wait for MariaDB (real auth check)
  ↓
[2/6] Sync migrations with existing database
    → python manage.py sync_migrations --no-backup
    → Backup dilakukan otomatis (skip di container karena ephemeral)
    → Fake migration untuk tabel yang sudah ada
    → Run migration untuk yang belum ada (token_blacklist, dll.)
  ↓
[3/6] Apply any remaining migrations
    → python manage.py migrate --noinput (safety net)
  ↓
[4/6] Collect static files
    → python manage.py collectstatic --noinput
  ↓
[5/6] Create superuser (optional — via env vars)
  ↓
[6/6] Start Daphne ASGI server (foreground)
```

> **Kenapa `--no-backup` di container?**  
> Karena container bersifat ephemeral, backup di dalam container tidak berguna.
> Backup tetap dilakukan saat menjalankan `sync_migrations` secara manual di luar container.

---

## 6. Environment Variables

### 6.1. Database

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_MYSQL` | `false` | Set `true` untuk MariaDB/MySQL |
| `DB_HOST` | `127.0.0.1` | Database host |
| `DB_PORT` | `3306` | Database port |
| `DB_NAME` | `warungio_db` | Database name |
| `DB_USER` | `warungio` | Database user |
| `DB_PASS` | — | **WAJIB DIISI** |
| `DB_ROOT_PASS` | — | Root password untuk mysql container |

### 6.2. Django

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | — | Secret key untuk session/crypto |
| `DJANGO_DEBUG` | `True` | Set `False` di production |
| `DJANGO_ALLOWED_HOSTS` | — | Comma-separated hosts |
| `DJANGO_SUPERUSER_EMAIL` | — | Auto-create superuser |
| `DJANGO_SUPERUSER_PASSWORD` | — | Superuser password |

### 6.3. Redis / Celery

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `CELERY_ENABLED` | `false` | Set `true` untuk aktivasi Celery |

> **Catatan:** Celery **nonaktif default** untuk hemat RAM di VPS 1GB.
> Aktifkan hanya jika Redis terkonfigurasi dan RAM tersedia.

---

## 7. Troubleshooting

### 7.1. Login HTTP 500

**Penyebab:** Tabel `token_blacklist_outstandingtoken` atau `token_blacklist_blacklistedtoken` tidak ada.

**Solusi:** Jalankan `sync_migrations`:
```bash
docker compose exec django python manage.py sync_migrations
```

### 7.2. Migration Gagal Karena Tabel Sudah Ada

**Penyebab:** Tabel sudah ada di DB tapi belum tercatat di `django_migrations`.

**Jangan hapus database!** Jalankan saja:
```bash
docker compose exec django python manage.py sync_migrations
```

### 7.3. Ingin Reset Migration (Tanpa Hapus Data)

```bash
# 1. Backup database
docker compose exec mysql mysqldump -u root -p warungio_db > backup.sql

# 2. Sync migrations
docker compose exec django python manage.py sync_migrations
```

### 7.4. Ingin Lihat Status Migration Saat Ini

```bash
docker compose exec django python manage.py showmigrations
```

Atau langsung cek tabel:
```sql
SELECT * FROM django_migrations ORDER BY applied DESC;
```

### 7.5. Container Restart Loop

Cek log untuk melihat error:
```bash
docker compose logs django | tail -50
```

Jika error migration, jalankan:
```bash
docker compose exec django python manage.py sync_migrations --dry-run
```

### 7.6. Database Tidak Bisa Connect

Cek apakah MariaDB sudah siap:
```bash
docker compose logs mysql | tail -20
docker compose exec mysql mysqladmin ping -u root -p
```

---

## 8. FAQ

### Q: Apakah saya harus menghapus database setiap deploy?

**Tidak.** `sync_migrations` dirancang untuk menangani database yang sudah ada.
Tidak perlu menghapus atau mereset database.

### Q: Apakah data saya aman?

**Ya.** Command ini hanya membaca struktur tabel (schema), bukan data.
Tidak ada operasi DROP, DELETE, atau TRUNCATE.

### Q: Bagaimana dengan migration baru setelah deploy?

Setiap deploy akan menjalankan `sync_migrations` → `migrate`.
Migration baru akan otomatis terdeteksi dan dijalankan.

### Q: Apa yang terjadi jika saya menjalankan `sync_migrations` dua kali?

Aman. Idempotent. Migration yang sudah di-record akan di-skip.
Migration yang belum akan diproses seperti biasa.

### Q: Apakah `sync_migrations` menggantikan `migrate`?

Tidak. `sync_migrations` adalah **pre-processing** sebelum `migrate`.
Ia memastikan tabel yang sudah ada tidak menyebabkan error saat `migrate` dijalankan.

### Q: File `django_migrations_backup_*` apakah perlu dihapus?

Tidak perlu, tapi aman dihapus jika backup sudah tidak diperlukan.
Backup hanya dibuat saat `sync_migrations` dijalankan **tanpa** `--no-backup`.

---

## Deployment Cheat Sheet

```bash
# ─── First deployment ───
git clone <repo> && cd warungio
cp .env.example .env
# Edit .env
docker compose up -d --build

# ─── Daily deployment ───
git pull && docker compose up -d --build

# ─── Using deploy script ───
./scripts/deploy.sh

# ─── Emergency migration fix ───
docker compose exec django python manage.py sync_migrations

# ─── Check status ───
docker compose ps
docker compose logs --tail=20 django
curl http://localhost:8000/health/

# ─── Manual migration commands ───
docker compose exec django python manage.py sync_migrations --dry-run
docker compose exec django python manage.py sync_migrations
docker compose exec django python manage.py migrate --noinput
docker compose exec django python manage.py showmigrations
```
