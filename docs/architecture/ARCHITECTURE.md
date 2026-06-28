# WARUNGIO MARKETPLACE ARCHITECTURE

## 1. PROJECT OVERVIEW

Warungio adalah marketplace kebutuhan dapur yang menghubungkan pembeli dengan warung terdekat untuk membeli sayuran, sembako, buah, bumbu dapur, protein, dan kebutuhan rumah tangga lainnya.

Platform terdiri dari:

* Buyer System
* Seller System
* Admin System
* AI Quality Check System
* Delivery Management System
* Promotion System

---

# 2. TECHNOLOGY STACK

## Frontend

* HTML5
* CSS3 (vanilla, flexbox/grid, animations)
* JavaScript (ES6+, vanilla)
* Plus Jakarta Sans (font)

## Backend (Primary)

* **Django** (Python 3.11+) — REST API, auth, orders, payments, chat, analytics
* Django REST Framework
* SimpleJWT — Token authentication
* Django Channels — WebSocket
* Celery — Async task queue
* Redis — Cache, broker, channel layer

## Backend (Legacy)

* PHP — Some legacy endpoints

## Database

* MySQL / MariaDB (production)
* SQLite (development, default)

## Infrastructure

* Docker + Docker Compose
* Nginx — Reverse proxy, static/media serving
* Gunicorn + Uvicorn — Django ASGI/WSGI server
* GitHub Actions — CI/CD

## Payment Gateway

* Midtrans Snap (credit card, bank transfer, e-wallet, QRIS, COD)

## Social Authentication

* Google OAuth
* Facebook Login
* Apple Sign In

## AI (Future)

* Python (Pandas, Scikit-learn)
* AR-based product quality detection

---

# 3. USER ROLES

## Buyer

Fitur:

* Registrasi
* Login
* OTP
* Marketplace
* Cart
* Checkout
* Tracking
* Chat
* Wishlist
* Review

---

## Seller

Fitur:

* Daftar Mitra
* Dashboard
* Produk
* Pesanan
* Pengiriman
* Pelanggan
* Promo
* Laporan
* Keuangan
* Ulasan

---

## Admin

Fitur:

* Verifikasi Mitra
* Kelola User
* Kelola Produk
* Kelola Pesanan
* Kelola Promo
* Monitoring Sistem

---

# 4. BUSINESS FLOW

Buyer
↓
Cari Produk
↓
Tambah Keranjang
↓
Checkout
↓
Pilih Pembayaran
↓
Pesanan Masuk Seller
↓
Seller Memproses
↓
Pilih Pengiriman
↓
Kirim Pesanan
↓
Pesanan Diterima
↓
Review Produk

---

# 5. BUYER JOURNEY

Landing Page
↓
Register / Login
↓
OTP Verification
↓
Home Dashboard
↓
Cari Produk
↓
Detail Produk
↓
Keranjang
↓
Checkout
↓
Pembayaran
↓
Tracking
↓
Pesanan Selesai

---

# 6. SELLER JOURNEY

Daftar Mitra
↓
Verifikasi Data
↓
Aktivasi Toko
↓
Dashboard Seller
↓
Tambah Produk
↓
Kelola Stok
↓
Pesanan Masuk
↓
Pilih Metode Pengiriman
↓
Kirim Pesanan
↓
Dana Masuk
↓
Laporan Penjualan

---

# 7. SYSTEM FLOW

Visitor
↓
Landing Page
↓
Login / Register
↓
OTP
↓
Role Selection

├── Buyer
│   ├── Home
│   ├── Produk
│   ├── Cart
│   ├── Checkout
│   ├── Tracking
│   └── Review
│
└── Seller
├── Dashboard
├── Produk
├── Pesanan
├── Pengiriman
├── Laporan
└── Keuangan

---

# 8. ORDER STATE FLOW

Pending
↓
Dibayar
↓
Diproses
↓
Siap Dikirim
↓
Dalam Pengiriman
↓
Selesai

Atau

Pending
↓
Dibatalkan

---

# 9. AI QUALITY CHECK FLOW

Upload Foto Produk
↓
AI Scan
↓
Deteksi Kategori
↓
Analisis Kesegaran
↓
Analisis Warna
↓
Analisis Kelayakan
↓
Skor Produk

Output:

* Fresh
* Good
* Warning
* Rejected

---

# 10. DATABASE ARCHITECTURE

Database:
warungio_db

Tabel Utama:

users
stores
products
categories
cart
orders
order_items
payments
deliveries
promotions
reviews
favorites
chats
notifications
quality_checks

---

# 11. DATABASE RELATION

users
│
├── stores
│
├── orders
│
├── reviews
│
└── notifications

stores
│
├── products
│
├── promotions
│
└── reports

products
│
├── order_items
│
├── favorites
│
└── quality_checks

orders
│
├── payments
│
└── deliveries

---

# 12. FEATURE MATRIX

Buyer:
✓ Marketplace
✓ Cart
✓ Checkout
✓ Tracking
✓ Chat
✓ Review

Seller:
✓ Dashboard
✓ Product Management
✓ Order Management
✓ Shipping Management
✓ Promotion
✓ Reports

Admin:
✓ Verification
✓ User Management
✓ Product Monitoring
✓ Analytics

---

# 13. PAGE SITEMAP

## Public

```
/home/index.html          Landing page
/auth/login/              Login
/auth/register/           Register (buyer)
/auth/register-mitra/     Register (seller)
/auth/otp/                OTP verification
/auth/reset-password/     Forgot/reset password
/auth/callback/Apple.social/  Apple auth callback
```

## Buyer

```
/buyer/dashboard/         Home dashboard (marketplace)
/buyer/cart/              Keranjang belanja
/buyer/checkout/          Checkout flow
/buyer/orders/            Daftar pesanan
/buyer/order-success/     Konfirmasi pesanan
/buyer/profile/           Profil & pengaturan
```

## Seller

```
/seller/dashboard/        Seller dashboard
/seller/products/         Kelola produk
/seller/partner-guide/    Panduan mitra
```

## Other

```
/reports/                 Laporan & analitik
```

## Django (API Only)

```
/api/auth/                Auth, OTP, profile
/api/stores/              Stores CRUD
/api/products/            Products, categories, reviews
/api/orders/              Cart, orders
/api/payments/            Midtrans payment
/api/analytics/           Dashboard analytics
/api/chat/                WebSocket chat
/api/notifications/       Notifications
/api/support/             Help center
```

---

# 14. PROJECT STRUCTURE

```
warungio/
│
├── auth/                    # Auth pages
│   ├── callback/Apple.social/
│   ├── login/
│   ├── otp/
│   ├── register/
│   ├── register-mitra/
│   └── reset-password/
│
├── buyer/                   # Buyer frontend
│   ├── cart/
│   ├── checkout/
│   ├── dashboard/
│   ├── orders/
│   ├── order-success/
│   └── profile/
│
├── seller/                  # Seller frontend
│   ├── dashboard/
│   ├── partner-guide/
│   └── products/
│
├── backend/                 # PHP backend
│   ├── config/
│   └── *.php
│
├── django_backend/          # Django REST API
│   ├── accounts/
│   ├── analytics/
│   ├── chat/
│   ├── notifications/
│   ├── orders/
│   ├── payments/
│   ├── products/
│   ├── stores/
│   ├── support/
│   ├── config/
│   ├── templates/
│   └── manage.py
│
├── src/                     # Shared JS source
│   ├── services/api.js
│   └── utils/auth.js
│
├── assets/images/           # 77 media images
├── database/                # SQL schemas
├── home/                    # Landing page
├── nginx/                   # Nginx config
├── reports/                 # Reports page
├── scripts/                 # Utility scripts
│
├── docker-compose.yml
├── Dockerfile
├── package.json
├── README.md
├── ARCHITECTURE.md
├── API_specification.md
├── Database.md
├── DEPLOYMENT.md
└── Task_Roadmap.md
```

---

# 15. DEPLOYMENT ARCHITECTURE

Frontend
(HTML + Tailwind)
↓
PHP Backend
↓
MySQL Database
↓
Admin Dashboard

Future:
AI Service (Django)
↓
Quality Check Engine

---

# 16. SECURITY

* Password Hashing
* Session Authentication
* CSRF Protection
* Input Validation
* File Upload Validation
* OTP Verification

---

# 17. PROJECT GOALS

* Marketplace kebutuhan dapur modern
* Mendukung warung lokal
* Pengiriman cepat
* AI Quality Check
* Sistem seller profesional
* Dashboard analitik lengkap

---

# 18. DOCUMENTATION STATUS

| Document | Status |
|----------|--------|
| README.md | ✅ Updated (struktur, tech stack, roles, features) |
| ARCHITECTURE.md | ✅ Updated (architecture, flow, sitemap) |
| API_specification.md | ⬜ Not created — generate from DRF Spectacular |
| Database.md | ✅ Complete (full schema) |
| DEPLOYMENT.md | ✅ Updated (Django, Cloud Run, Docker) |
| Task_Roadmap.md | ✅ Updated (all phases completed) |
| docs/deployment/DEPLOYMENT.md | ✅ Updated (Cloud Run + Docker guide) |
