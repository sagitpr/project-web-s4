#  Warungio - Hyperlocal Fresh Marketplace

## Tentang Project

Warungio adalah platform marketplace hyperlocal yang menghubungkan pembeli, mitra warung, dan admin dalam satu ekosistem digital untuk jual beli kebutuhan harian, sembako, sayuran segar, buah, bumbu dapur, dan berbagai produk kebutuhan rumah tangga.

Tidak hanya marketplace biasa, Warungio berfokus pada digitalisasi warung lokal dengan sistem stok real-time, pemetaan warung terdekat, pengiriman berbasis area, serta dashboard manajemen toko yang modern.

---

## Vision

Menjadi platform marketplace hyperlocal terpercaya yang memberdayakan warung lokal, mempercepat distribusi kebutuhan harian, dan menghadirkan pengalaman belanja yang cepat, segar, aman, serta terjangkau bagi masyarakat Indonesia.

---

## Mission

* Mendigitalisasi warung tradisional.
* Menghubungkan pembeli dengan warung terdekat.
* Mengurangi rantai distribusi produk segar.
* Memberikan sistem pengelolaan toko yang modern.
* Membantu UMKM berkembang melalui teknologi.
* Menyediakan pengalaman belanja kebutuhan dapur yang mudah dan cepat.

---

## Problem Statement

Permasalahan yang ingin diselesaikan Warungio:

1. Sulit menemukan warung terdekat yang memiliki stok tersedia.
2. Informasi stok sering tidak akurat.
3. Pembeli harus berpindah-pindah toko untuk mencari kebutuhan.
4. Warung tradisional belum memiliki sistem digital yang terintegrasi.
5. Belum ada marketplace yang fokus pada jaringan warung lokal dan kebutuhan dapur harian.

---

## Solution

Warungio menyediakan:

* Marketplace Hyperlocal
* Real-Time Stock Management
* Live Tracking Delivery
* Verified Store System
* Smart Recommendation
* AI Quality Check
* Seller Analytics Dashboard
* Pickup di Warung
* Flash Sale dan Voucher

---

## Unique Selling Point (USP)

### Hyperlocal Marketplace

Menampilkan warung terdekat berdasarkan lokasi pengguna.

### Real-Time Stock

Stok selalu diperbarui secara langsung oleh mitra warung.

### Fresh Indicator

Menampilkan kualitas dan kesegaran produk.

### Pickup di Warung

Pembeli dapat mengambil barang langsung tanpa ongkir.

### AI Quality Check

Sistem analisis kualitas produk menggunakan teknologi AI.

### Verified Store

Mitra toko yang telah diverifikasi untuk meningkatkan kepercayaan pembeli.

---

# Sistem Alur Warungio

<img width="3498" height="2629" alt="sistem alur flow warungio" src="https://github.com/user-attachments/assets/81fe20c9-c4a4-4d5b-b1b3-ac6ff1ab8d78" />

---

# Role Pengguna

## Buyer (Pembeli)

Pengguna yang melakukan pembelian produk.

### Fitur Utama

* Cari dan beli produk
* Repeat Order
* Wishlist
* Flash Sale
* Live Tracking
* Chat Penjual
* Pickup di Warung
* Pembayaran
* Komplain
* Review Produk
* Voucher & Promo

---

## Seller / Mitra Warung

Pengguna yang menjual produk.

### Fitur Utama

* Kelola Produk
* Tambah/Edit Stok
* Real-Time Stock Update
* Kelola Pesanan Masuk
* Proses Pengiriman
* Chat Pembeli
* Laporan Penjualan
* Dashboard Analitik
* Promo dan Diskon
* Verified Store

---

## Admin System

Mengelola seluruh sistem marketplace.

### Fitur Utama

* Kelola User
* Verifikasi Mitra Warung
* Monitoring Transaksi
* Kelola Produk
* Kelola Kategori
* Kelola Promo
* Kelola Komplain
* Monitoring Radius Coverage
* Dashboard Analitik
* Monitoring Sistem

---

# Fitur Utama

## Discovery & Shopping

* Barcode Scan
* Repeat Order
* Wishlist
* Bundle / Paket Hemat
* Flash Sale
* Subscription
* Compare Produk
* Recently Viewed
* Voice Search
* Filter & Sorting

---

## Pengiriman & Tracking

* Live Tracking
* ETA Countdown
* Chat Kurir
* Schedule Delivery
* Drop Point
* Delivery Proof
* Pickup di Warung

---

## Payment & Trust

* COD
* E-Wallet
* Bank Transfer
* Split Payment
* Invoice
* Verified Store
* Garansi
* Return / Komplain

---

## Hyperlocal Signature

* Warung Terdekat
* Real-Time Stok
* Fresh Indicator
* Mitra Warung
* Belanja Titip
* Ambil di Warung
* Warung Buka Sekarang
* Radius Coverage

---

## Engagement

* Chat Penjual
* Rating & Ulasan
* Voucher
* Loyalty Points
* Referral
* Promo Notification
* Daily Check-In

---

## AI Features

### Product Quality Check

Analisis:

* Freshness Detection
* Product Categorization
* Quality Scoring
* Stock Recommendation

Output:

* Fresh
* Good
* Warning
* Rejected

---

# Core Features

Fitur inti yang menjadi identitas Warungio:

* Real-Time Stock
* Warung Terdekat
* Repeat Order
* Flash Sale
* Live Tracking
* Verified Store
* Chat Penjual
* Pickup di Warung
* AI Quality Check

---

# Tech Stack

## Frontend

* HTML5
* CSS3 (vanilla, flexbox/grid)
* JavaScript (ES6+, vanilla)
* Plus Jakarta Sans (Google Fonts)

## Backend

* **Django** (Python) — REST API, auth, orders, payments, chat, analytics
* **PHP** — Legacy backend endpoints
* **MySQL** / **MariaDB** — Primary database
* **SQLite** — Development database (Django default)
* **Redis** — Caching, Channels, Celery broker

## AI & Data Processing

* Python
* Pandas
* Scikit-learn
* AR Detection (image analysis)
* Celery — Async task queue

## API & Services

* Django REST Framework
* SimpleJWT Authentication
* WebSocket via Django Channels
* Midtrans Snap (payment gateway)
* Social Auth (Google, Facebook, Apple)
* REST API + JSON

## Infrastructure

* Docker & Docker Compose
* Nginx (reverse proxy)
* Gunicorn + Uvicorn (Django ASGI)
* GitHub Actions (CI/CD)

## Development Tools

* Git / GitHub
* Postman
* VS Code
* pytest (Django tests)

---

# Database Overview

Database:

warungio_db

Main Tables:

* users
* stores
* products
* categories
* cart
* orders
* order_items
* payments
* deliveries
* reviews
* chats
* notifications
* quality_checks

---

# API Overview

Modules:

* Authentication
* Products
* Categories
* Stores
* Cart
* Checkout
* Orders
* Payments
* Deliveries
* Reviews
* Promotions
* Notifications
* Chat
* Analytics
* AI Quality Check

---

# Security Features

* Password Hashing
* OTP Verification
* JWT Authentication
* Role Based Access Control
* CSRF Protection
* Input Validation
* Secure Session Management
* File Validation

---

# Struktur Project

```
warungio/
│
├── auth/                    # Auth pages (login, register, OTP, reset password)
│   ├── callback/            #   Apple Social login callback
│   ├── login/
│   ├── otp/
│   ├── register/
│   ├── register-mitra/
│   └── reset-password/
│
├── buyer/                   # Buyer frontend pages
│   ├── cart/                #   Keranjang belanja
│   ├── checkout/            #   Checkout flow
│   ├── dashboard/           #   Beranda buyer (landing page)
│   ├── orders/              #   Daftar pesanan
│   ├── order-success/       #   Konfirmasi pesanan berhasil
│   └── profile/             #   Profil & pengaturan akun
│
├── seller/                  # Seller frontend pages
│   ├── dashboard/
│   ├── partner-guide/
│   └── products/
│
├── backend/                 # PHP backend services
│   ├── config/              #   DB config, helpers
│   └── *.php                #   API endpoints, controllers
│
├── django_backend/          # Django REST API backend
│   ├── accounts/            #   Auth, users, profiles, social auth
│   ├── analytics/           #   Sales analytics & reports
│   ├── chat/                #   WebSocket chat
│   ├── notifications/       #   Push notifications
│   ├── orders/              #   Cart, orders, deliveries
│   ├── payments/            #   Midtrans payment gateway
│   ├── products/            #   Products, categories, reviews
│   ├── stores/              #   Stores, followers
│   ├── support/             #   Help center & ticket system
│   ├── config/              #   Django settings, ASGI/WSGI
│   ├── templates/           #   Django templates (help center)
│   └── manage.py
│
├── src/                     # Shared frontend source
│   ├── services/api.js      #   API client (WarungioAPI)
│   └── utils/auth.js        #   Auth utilities (WarungioAuth)
│
├── assets/images/           # Media assets (77 images)
├── database/                # SQL schemas & migrations
│   ├── schema/
│   └── seeds/
│
├── home/                    # Landing page (index.html + PHP)
├── reports/                 # Reports page
├── nginx/                   # Nginx configuration
│
├── scripts/                 # Utility scripts
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

# Cara Kerja Sistem

1. Buyer memilih produk.
2. Frontend mengirim request ke backend.
3. Backend memproses transaksi.
4. Database menyimpan data pesanan.
5. Seller menerima pesanan.
6. Seller memproses dan mengirim pesanan.
7. Buyer melakukan tracking pesanan.
8. Admin memonitor seluruh aktivitas sistem.

---

# Deployment Environment

## Development

* XAMPP
* PHP 8+
* MySQL

## Production

* Linux Server
* Apache / Nginx
* MySQL / MariaDB
* HTTPS SSL

---

# Current Status

Project Phase:

MVP Development

Progress:

✅ UI/UX Design

✅ System Architecture

✅ Database Design

✅ API Specification (Django REST)

✅ Authentication (JWT + OTP + Social)

✅ Buyer Dashboard

✅ Seller Dashboard

✅ Cart & Checkout Flow

✅ Order Management

✅ Midtrans Payment Integration

✅ Profile Management

⬜ AI Integration

⬜ Production Deployment

⬜ Mobile Application

---

# Roadmap

## Phase 1

* Marketplace Core
* Authentication
* Seller Dashboard
* Checkout
* Tracking

## Phase 2

* AI Recommendation Engine
* Smart Restock Prediction
* Multi-Warung Split Order
* Realtime Chat
* Push Notification

## Phase 3

* Mobile Application
* Driver Application
* Warehouse Integration
* IoT Freshness Monitoring

---

# Contributors

Project Lead

Sagit Faturrakhman

Program Studi Sistem Informasi

---

# Acknowledgement

Terima kasih kepada seluruh pihak yang mendukung pengembangan Warungio sebagai platform marketplace hyperlocal yang membantu digitalisasi warung lokal di Indonesia.

---

# License

Project ini dibuat untuk pembelajaran, penelitian, pengembangan akademik, dan pengembangan produk startup.
