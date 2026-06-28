# Warungio Marketplace — Database Management Guide

> **Database**: MariaDB 10.11+ / MySQL 8.0+  
> **Database Name**: `warungio_db`  
> **Character Set**: `utf8mb4`  
> **Last Updated**: May 2026

---

## Table of Contents

1. [Database Overview](#1-database-overview)
2. [How to Access the Database](#2-how-to-access-the-database)
3. [Database Connection Architecture](#3-database-connection-architecture)
4. [Table Reference](#4-table-reference)
5. [Key Relationships & ERD](#5-key-relationships--erd)
6. [Important Tables by Feature](#6-important-tables-by-feature)
7. [How Data Flows Into the Database](#7-how-data-flows-into-the-database)
8. [Database Management Tasks](#8-database-management-tasks)
9. [Backup & Restore](#9-backup--restore)
10. [Migration Guide](#10-migration-guide)
11. [Performance Optimization](#11-performance-optimization)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Database Overview

Warungio uses MariaDB/MySQL as its primary database. The system has **two backend layers** that connect to the same database:

| Layer | Technology | Connection File | Purpose |
|-------|-----------|----------------|---------|
| **Django Backend** (primary) | Python/Django ORM | `django_backend/config/settings.py` | REST APIs, authentication, stores, products, orders, analytics, chat, AR camera |
| **PHP Backend** (legacy) | PHP/PDO | `backend/db.php`, `backend/config.php`, `backend/function.php` | Legacy API endpoints, session auth |
| **Express.js** (optional) | Node.js/mysql2 | `backend/server.js` | Partner registration API |

### Database Files Location

```
database/
├── schema/                    # SQL schema files (reference)
│   ├── create_users_table.sql
│   ├── create_users_table_full.sql
│   ├── create_products_table.sql
│   ├── create_partner_registrations_table.sql
│   ├── alter_users_table.sql
│   └── warungio_db.sql        # Full database dump (recommended for import)
│
├── migrations/                # Django auto-managed migrations
│   (Django creates migrations automatically)
│
└── seeds/                     # Sample/seed data (future use)
```

### Database Configuration Files

| File | Purpose | Key Variables |
|------|---------|--------------|
| `.env` (project root) | Central environment variables | `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS` |
| `backend/function.php` | .env loader + auth helpers | Reads from `.env` |
| `backend/db.php` | PHP PDO connection | `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS` |
| `backend/config.php` | PHP PDO connection (legacy) | Same variables |
| `django_backend/config/settings.py` | Django database config | `DATABASES` dict reading from env |
| `backend/server.js` | Express.js connection | Reads from `.env` via dotenv |

---

## 2. How to Access the Database

### 2.1 Using Command Line (MariaDB/MySQL Client)

```bash
# Connect to MariaDB (default port)
mysql -u root -p

# Connect with custom port (3307 if running side-by-side)
mysql -u root -p -P 3307

# Connect to specific database
mysql -u root -p -P 3307 warungio_db

# Execute a query directly
mysql -u root -p -P 3307 -e "SHOW DATABASES;"
mysql -u root -p -P 3307 warungio_db -e "SHOW TABLES;"
```

### 2.2 Using phpMyAdmin (Web GUI)

phpMyAdmin is a web-based database management tool. If installed:

1. Navigate to `http://localhost/phpmyadmin` (or your server's URL)
2. Login with: `root` and password (or your database user credentials)
3. Select `warungio_db` from the left sidebar

**Quick checks in phpMyAdmin:**
- **Structure tab**: View table columns, types, indexes
- **Browse tab**: View table data (equivalent to `SELECT *`)
- **SQL tab**: Run custom queries
- **Export tab**: Download database backup
- **Import tab**: Restore database from backup

### 2.3 Using MySQL Workbench (Desktop GUI)

1. Download and install MySQL Workbench from [mysql.com](https://www.mysql.com/products/workbench/)
2. Create a new connection:
   - Connection Name: `Warungio`
   - Hostname: `localhost`
   - Port: `3306` (or `3307`)
   - Username: `root`
3. Click "Test Connection" and enter password
4. Select `warungio_db` from the schema list

### 2.4 Using HeidiSQL (Windows, Free)

1. Download from [heidisql.com](https://www.heidisql.com/)
2. Create new session:
   - Network type: MySQL (TCP/IP)
   - Hostname / IP: `localhost`
   - User: `root`
   - Port: `3306` or `3307`
3. Open and navigate to `warungio_db`

### 2.5 Quick SQL Navigation Commands

```sql
-- Show all databases
SHOW DATABASES;

-- Select database
USE warungio_db;

-- Show all tables
SHOW TABLES;

-- Describe table structure
DESCRIBE users;
DESCRIBE stores;
DESCRIBE products;
DESCRIBE orders;

-- Show CREATE TABLE statement
SHOW CREATE TABLE users;

-- Count rows in important tables
SELECT 'users', COUNT(*) FROM users
UNION ALL SELECT 'stores', COUNT(*) FROM stores
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'orders', COUNT(*) FROM orders;

-- Show table sizes
SELECT 
    TABLE_NAME, 
    ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) AS 'Size (MB)',
    TABLE_ROWS
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'warungio_db'
ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC;
```

---

## 3. Database Connection Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        .env File                                │
│  DB_HOST=localhost  DB_PORT=3306  DB_NAME=warungio_db          │
│  DB_USER=root  DB_PASS=your_password                           │
└──────────┬──────────────┬──────────────┬──────────────────────┘
           │              │              │
           ▼              ▼              ▼
┌──────────────────┐ ┌────────────────┐ ┌──────────────────┐
│  Django (Python)  │ │  PHP (PDO)     │ │ Express.js (Node)│
│  settings.py      │ │  db.php        │ │ server.js        │
│  ORM + Raw SQL    │ │  Raw SQL only  │ │ Raw SQL only     │
└────────┬─────────┘ └───────┬────────┘ └────────┬─────────┘
         │                   │                    │
         └───────────────────┼────────────────────┘
                             ▼
                  ┌──────────────────┐
                  │   MariaDB/MySQL  │
                  │   warungio_db    │
                  └──────────────────┘
```

### Connection String Reference

**Django** (`django_backend/config/settings.py`):
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',   # or 'django.db.backends.sqlite3' for dev
        'NAME': os.environ.get('DB_NAME', 'warungio_db'),
        'USER': os.environ.get('DB_USER', 'root'),
        'PASSWORD': os.environ.get('DB_PASS', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '3306'),
    }
}
```

**PHP** (`backend/db.php`):
```php
$dsn = 'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4';
$pdo = new PDO($dsn, DB_USER, DB_PASS, [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
]);
```

**Express.js** (`backend/server.js`):
```javascript
const dbConfig = {
  host: process.env.DB_HOST || 'localhost',
  database: process.env.DB_NAME || 'warungio_db',
  user: process.env.DB_USER || 'root',
  password: process.env.DB_PASS || '',
  waitForConnections: true,
  connectionLimit: 10,
};
```

---

## 4. Table Reference

### Core Tables (Django-Managed)

| Table | Purpose | Auto-Created by |
|-------|---------|-----------------|
| `accounts_user` | All users (buyers, sellers, admins) | Django migration |
| `accounts_otp` | OTP verification codes | Django migration |
| `accounts_loginattempt` | Login audit trail | Django migration |
| `accounts_socialaccount` | Linked social auth accounts | Django migration |
| `stores_store` | Seller store profiles | Django migration |
| `stores_storefollower` | Store followers | Django migration |
| `stores_storecategory` | Store categories | Django migration |
| `products_product` | Product catalog | Django migration |
| `products_productimage` | Product images | Django migration |
| `products_productreview` | Product reviews/ratings | Django migration |
| `products_category` | Product categories | Django migration |
| `orders_cart` | Shopping cart | Django migration |
| `orders_cartitem` | Items in cart | Django migration |
| `orders_order` | Orders/transactions | Django migration |
| `orders_orderitem` | Items in an order | Django migration |
| `payments_payment` | Payment transactions | Django migration |
| `payments_paymentmethod` | Saved payment methods | Django migration |
| `analytics_dailysales` | Daily sales data | Django migration |
| `analytics_productview` | Product view tracking | Django migration |
| `analytics_usermetric` | User behavior metrics | Django migration |
| `quality_checks` | Smart Scan AI quality check results | Django migration |
| `chat_message` | Chat messages | Django migration |
| `chat_conversation` | Chat conversations | Django migration |
| `notifications_notification` | User notifications | Django migration |
| `django_migrations` | Migration tracking | Django (auto) |
| `django_content_type` | Content types | Django (auto) |
| `django_admin_log` | Admin action log | Django (auto) |
| `django_session` | Session storage | Django (auto) |
| `authtoken_token` | Auth tokens (if used) | Django (auto) |

### Core Tables (PHP-Managed)

| Table | Purpose | Created by |
|-------|---------|------------|
| `partner_registrations` | Partner/store registration requests | `database/schema/create_partner_registrations_table.sql` |

### Django vs PHP Table Naming

Django automatically prefixes table names with the app name:
- `accounts_user` (Django) — primary user table
- `stores_store` (Django) — primary store table
- `products_product` (Django) — primary product table

PHP uses direct table names:
- `partner_registrations` (PHP) — stored directly

---

## 5. Key Relationships & ERD

### Entity Relationship Diagram

```
users (accounts_user)
│
├──< store (stores_store)
│     │
│     ├──< product (products_product)
│     │     ├──< product_image (products_productimage)
│     │     ├──< product_review (products_productreview) ──>─ user
│     │     └──< cart_item (orders_cartitem) ──>─ cart (orders_cart) ──>─ user
│     │
│     ├──< order_item (orders_orderitem) ──>─ order (orders_order) ──>─ user
│     │     └──< payment (payments_payment)
│     │
│     ├──< conversation (chat_conversation) ──>─ user (buyer)
│     │     └──< message (chat_message)
│     │
│     └──< store_follower (stores_storefollower) ──>─ user
│
├──< social_account (accounts_socialaccount)
├──< notification (notifications_notification)
├──< login_attempt (accounts_loginattempt)
├──< quality_check (quality_checks)
└──< daily_sales (analytics_dailysales) ──>─ store
```

### Key Relationships Explained

```
User ──HasOne──> Store          (Each seller has one store)
User ──HasOne──> SocialAccount  (Each user can link Google/Facebook/Apple)
User ──HasMany──> Order          (One user has many orders)
Order ──HasMany──> OrderItem    (One order has many items)
OrderItem ──BelongsTo──> Product (Each item is one product)
Store ──HasMany──> Product      (One store sells many products)
Store ──HasMany──> DailySales   (Analytics per store per day)
Product ──HasMany──> Review     (Products have reviews from users)
User ──HasMany──> Conversation  (Buyer ↔ Seller conversations)
Conversation ──HasMany──> Message (Each conversation has messages)
User ──HasMany──> Notification  (Notifications are per user)
Product ──HasMany──> QualityCheck    (Smart Scan AI quality checks per product)
```

---

## 6. Important Tables by Feature

### 🔐 Authentication & Users

| Table | Fields | Connected To |
|-------|--------|-------------|
| `accounts_user` | `id`, `email`, `password`, `role`, `phone`, `name`, `is_active`, `is_verified`, `created_at` | Login, registration, all user operations |
| `accounts_socialaccount` | `id`, `user_id`, `provider`, `provider_id`, `extra_data`, `created_at` | Google/Facebook/Apple login |
| `accounts_otp` | `id`, `user_id`, `otp_code`, `purpose`, `expires_at`, `verified_at` | Phone/email verification |
| `accounts_loginattempt` | `id`, `user_id`, `ip_address`, `success`, `timestamp` | Security audit |

### 🏪 Stores & Sellers

| Table | Fields | Connected To |
|-------|--------|-------------|
| `stores_store` | `id`, `owner_id`, `name`, `slug`, `description`, `logo`, `banner`, `status`, `rating`, `created_at` | Seller dashboard, products |
| `partner_registrations` | `id`, `store_name`, `owner_name`, `owner_email`, `status`, `created_at` | Partner registration (PHP) |

### 📦 Products

| Table | Fields | Connected To |
|-------|--------|-------------|
| `products_product` | `id`, `store_id`, `name`, `description`, `price`, `stock`, `category`, `image`, `is_active`, `created_at` | Product management, orders, AR camera |
| `products_productimage` | `id`, `product_id`, `image`, `is_primary`, `created_at` | Product gallery |
| `products_productreview` | `id`, `product_id`, `user_id`, `rating`, `comment`, `created_at` | Reviews, analytics |
| `products_category` | `id`, `name`, `slug`, `parent_id` | Product categorization |

### 🛒 Orders & Checkout

| Table | Fields | Connected To |
|-------|--------|-------------|
| `orders_cart` | `id`, `user_id`, `created_at`, `updated_at` | Shopping cart |
| `orders_cartitem` | `id`, `cart_id`, `product_id`, `quantity`, `price` | Cart items |
| `orders_order` | `id`, `buyer_id`, `store_id`, `status`, `total_amount`, `shipping_address`, `created_at` | Orders, dashboard analytics |
| `orders_orderitem` | `id`, `order_id`, `product_id`, `quantity`, `price` | Order items |
| `payments_payment` | `id`, `order_id`, `amount`, `method`, `status`, `transaction_id`, `created_at` | Payment processing |

### 📊 Analytics (Dashboard Realtime)

| Table | Fields | Connected To |
|-------|--------|-------------|
| `analytics_dailysales` | `id`, `store_id`, `date`, `total_sales`, `total_orders`, `total_products_sold`, `created_at` | Seller dashboard (real-time charts) |
| `analytics_productview` | `id`, `product_id`, `user_id`, `viewed_at` | Product popularity |
| `analytics_usermetric` | `id`, `user_id`, `page_views`, `session_duration`, `date` | User behavior |

### 📷 Smart Scan AI & Product Quality

| Table | Fields | Connected To |
|-------|--------|-------------|
| `quality_checks` | `id`, `product_id`, `freshness_score`, `stock_status`, `ai_result`, `quality_status`, `checked_at` | Smart Scan AI product freshness and barcode check results |

### 💬 Chat & Notifications

| Table | Fields | Connected To |
|-------|--------|-------------|
| `chat_conversation` | `id`, `buyer_id`, `store_id`, `created_at`, `updated_at` | Buyer ↔ Seller chat |
| `chat_message` | `id`, `conversation_id`, `sender_id`, `content`, `read`, `created_at` | Individual messages |
| `notifications_notification` | `id`, `user_id`, `type`, `title`, `message`, `data`, `read`, `created_at` | Push/in-app notifications |

---

## 7. How Data Flows Into the Database

### User Registration
```
User fills form → POST /api/auth/register/ 
  → Django creates accounts_user record
  → Returns JWT tokens
  → (Optional) OTP verification → accounts_otp created
```

### Social Login
```
User clicks Google/Facebook/Apple
  → OAuth popup → ID token received
  → POST /api/auth/social/google/ (or facebook/apple)
  → Django verifies token with provider
  → Creates accounts_user if new (or finds existing)
  → Creates/linked accounts_socialaccount record
  → Returns JWT tokens
```

### Product Creation (Seller)
```
Seller creates product → POST /api/products/
  → Django creates products_product record
  → Creates products_productimage records (if images)
  → Updates seller dashboard analytics
```

### Order Flow
```
Buyer adds to cart → Cart items in orders_cartitem
  → Buyer checks out → Django creates orders_order
  → Creates orders_orderitem records
  → Processes payment → payments_payment created
  → Updates analytics_dailysales for seller
  → Creates notifications_notification for seller
```

### Smart Scan AI Pengecekan Kualitas
```
Seller scans product with camera feed or barcode
  → Quality check results POSTed to /api/products/quality-checks/
  → Django creates quality_checks record
  → Dashboard analytics updated in realtime
```

### Analytics Update
```
Order completed → Analytics signal fires
  → Updates analytics_dailysales (total_sales, total_orders)
  → Updates products_product review count/rating
  → Updates stores_store rating
  → Realtime WebSocket push to seller dashboard
```

---

## 8. Database Management Tasks

### 8.1 Django Migrations (Preferred Method)

```bash
# Enter Django directory
cd django_backend

# Create migration for model changes
python manage.py makemigrations

# Show pending migrations
python manage.py showmigrations

# Apply migrations
python manage.py migrate

# Check migration status
python manage.py migrate --list

# Rollback migration (if needed)
python manage.py migrate accounts 0001_initial
```

### 8.2 Manual SQL Schema (Legacy/PHP)

The schema files in `database/schema/` are for reference. They match the current database structure.

```bash
# Import a schema file
mysql -u root -p -P 3307 warungio_db < database/schema/create_users_table.sql

# Import all schema files
for f in database/schema/*.sql; do
    mysql -u root -p -P 3307 warungio_db < "$f"
done
```

### 8.3 Seed Sample Data

```bash
# Create seed SQL file
nano database/seeds/sample_data.sql
```

```sql
-- Sample users
INSERT INTO accounts_user (email, password, name, role, is_active, is_verified)
VALUES 
  ('buyer@warungio.com', 'pbkdf2_sha256$...', 'Budi Santoso', 'buyer', true, true),
  ('seller@warungio.com', 'pbkdf2_sha256$...', 'Siti Rahayu', 'seller', true, true);

-- Apply seed data
mysql -u root -p -P 3307 warungio_db < database/seeds/sample_data.sql
```

### 8.4 Creating Database Snapshots

```bash
# Create a full dump
mysqldump -u root -p -P 3307 warungio_db > database/schema/warungio_db_$(date +%Y%m%d).sql

# Dump specific tables
mysqldump -u root -p -P 3307 warungio_db accounts_user stores_store products_product > tables_backup.sql

# Dump structure only (no data)
mysqldump -u root -p -P 3307 --no-data warungio_db > structure_only.sql

# Dump data only (no structure)
mysqldump -u root -p -P 3307 --no-create-info warungio_db > data_only.sql
```

### 8.5 Monitoring & Health Checks

```sql
-- Check database size
SELECT 
    table_schema AS 'Database',
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)'
FROM information_schema.tables 
WHERE table_schema = 'warungio_db'
GROUP BY table_schema;

-- Slow queries (requires slow_query_log enabled)
SHOW GLOBAL STATUS LIKE 'Slow_queries';

-- Connection status
SHOW STATUS LIKE 'Threads_connected';
SHOW PROCESSLIST;

-- Database uptime
SHOW STATUS LIKE 'Uptime';
```

---

## 9. Backup & Restore

### 9.1 Automated Backup Script

Create `database/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/warungio"
DB_NAME="warungio_db"
DB_USER="root"
DB_PASS="your_password"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

# Dump database
mysqldump -u $DB_USER -p$DB_PASS --routines --triggers --events $DB_NAME \
  | gzip > $BACKUP_DIR/${DB_NAME}_$DATE.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "${DB_NAME}_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: ${DB_NAME}_$DATE.sql.gz"
```

Make it executable and add to crontab:
```bash
chmod +x database/backup.sh
crontab -e
# Add: 0 2 * * * /path/to/warungio/database/backup.sh
```

### 9.2 Manual Restore

```bash
# Restore from gzipped backup
gunzip -c database/backups/warungio_db_20260101_020000.sql.gz | mysql -u root -p -P 3307 warungio_db

# Restore from uncompressed SQL
mysql -u root -p -P 3307 warungio_db < database/schema/warungio_db.sql
```

### 9.3 Export Specific Data for Analysis

```bash
# Export orders as CSV
mysql -u root -p -P 3307 -e "
  SELECT id, buyer_id, status, total_amount, created_at 
  FROM orders_order 
  INTO OUTFILE '/tmp/orders_export.csv'
  FIELDS TERMINATED BY ','
  ENCLOSED BY '\"'
  LINES TERMINATED BY '\n';
"
```

---

## 10. Migration Guide

### Migrating from PHP to Django Backend

The project is in the process of migrating from PHP to Django. Here's the status:

| Feature | PHP (Old) | Django (New) |
|---------|-----------|--------------|
| User registration | `backend/daftar.php`, `backend/register.php` | ✅ `POST /api/auth/register/` |
| User login | `backend/login.php` | ✅ `POST /api/auth/login/` |
| Social login | ❌ Not available | ✅ `POST /api/auth/social/*/` |
| Product management | `backend/add_product.php`, etc. | ✅ `POST /api/products/` |
| Orders | `backend/orders.php`, `backend/chekout.php` | ✅ `POST /api/orders/` |
| Dashboard analytics | `backend/api_dashboard.php` | ✅ `GET /api/analytics/` |
| Partner registration | `backend/daftar_mitra.php` | ✅ `POST /api/stores/register/` |

### Migration Steps (Per Feature)

```bash
# 1. Ensure Django model matches PHP table
# 2. Create/update Django migration
python manage.py makemigrations
python manage.py migrate

# 3. Migrate data from PHP tables if needed
python manage.py shell
```

```python
# Example: Migrate PHP users to Django
from django_backend.accounts.models import User
# Manually create users that match PHP table structure
```

---

## 11. Performance Optimization

### Indexes

Ensure these indexes exist for query performance:

```sql
-- Already indexed by Django:
-- accounts_user.email (UNIQUE)
-- accounts_socialaccount.provider + provider_id (UNIQUE)
-- stores_store.owner_id (INDEX)
-- products_product.store_id (INDEX)
-- orders_order.buyer_id (INDEX)

-- Recommended additional indexes:
ALTER TABLE orders_order ADD INDEX idx_order_status (status);
ALTER TABLE products_product ADD INDEX idx_product_category (category_id);
ALTER TABLE analytics_dailysales ADD INDEX idx_daily_store_date (store_id, date);
```

### Query Optimization Tips

```python
# BAD: N+1 query problem
orders = Order.objects.all()
for order in orders:
    print(order.buyer.name)  # Triggers a query for each order

# GOOD: Use select_related
orders = Order.objects.select_related('buyer', 'store').all()
for order in orders:
    print(order.buyer.name)  # No extra query

# BAD: Loading all records
products = Product.objects.all()

# GOOD: Paginate
products = Product.objects.all()[:20]  # Limit
```

### Connection Pooling

Django and PHP PDO handle connection pooling automatically. For high-traffic:

```bash
# Increase MariaDB connection limit
sudo nano /etc/mysql/mariadb.conf.d/50-server.cnf
```

```ini
[mysqld]
max_connections = 200
innodb_buffer_pool_size = 256M
query_cache_size = 64M
tmp_table_size = 32M
max_heap_table_size = 32M
```

---

## 12. Troubleshooting

### Common Database Issues

| Problem | Likely Cause | Solution |
|---------|-------------|----------|
| `Can't connect to MySQL server` | MariaDB not running | `sudo systemctl start mariadb` |
| `Access denied for user` | Wrong password/user | Check `.env` credentials |
| `Table doesn't exist` | Migration not applied | Run `python manage.py migrate` |
| `Duplicate entry` | Unique constraint violation | Check for duplicate emails/IDs |
| `MySQL server has gone away` | Timeout or connection dropped | Increase `wait_timeout` in MariaDB config |
| `Lock wait timeout exceeded` | Deadlock or long-running query | Kill long-running process: `SHOW PROCESSLIST; KILL <id>;` |
| `Out of memory` | Buffer pool too large | Reduce `innodb_buffer_pool_size` |
| `Data too long for column` | Input exceeds VARCHAR limit | Check form validation or increase column size |

### Useful Diagnostic Queries

```sql
-- Find locked tables
SHOW OPEN TABLES WHERE In_use > 0;

-- Find running queries
SHOW FULL PROCESSLIST;

-- Check table status
CHECK TABLE accounts_user;

-- Optimize tables
OPTIMIZE TABLE orders_order;
OPTIMIZE TABLE analytics_dailysales;

-- Analyze query performance
EXPLAIN SELECT * FROM orders_order WHERE buyer_id = 1;
```

### Reset Password (Direct Database)

```sql
-- Generate Django-compatible password hash
-- In Django shell:
python manage.py shell
>>> from django.contrib.auth.hashers import make_password
>>> print(make_password('newpassword123'))
```

```sql
-- Then update in database:
UPDATE accounts_user 
SET password = 'pbkdf2_sha256$...'  -- The hash from above
WHERE email = 'user@example.com';
```

---

## Quick Reference Card

```bash
# === CONNECT ===
mysql -u root -p -P 3307 warungio_db

# === VIEW TABLES ===
SHOW TABLES;

# === VIEW DATA ===
SELECT * FROM accounts_user LIMIT 10;
SELECT * FROM accounts_socialaccount LIMIT 10;
SELECT * FROM orders_order LIMIT 10;

# === COUNT RECORDS ===
SELECT 'Users', COUNT(*) FROM accounts_user
UNION SELECT 'Stores', COUNT(*) FROM stores_store
UNION SELECT 'Products', COUNT(*) FROM products_product
UNION SELECT 'Orders', COUNT(*) FROM orders_order;

# === DJANGO MIGRATIONS ===
cd django_backend
python manage.py showmigrations
python manage.py migrate

# === BACKUP ===
mysqldump -u root -p -P 3307 warungio_db > backup.sql

# === RESTORE ===
mysql -u root -p -P 3307 warungio_db < backup.sql
```
