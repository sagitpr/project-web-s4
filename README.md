# Warungio - Hyperlocal Fresh Marketplace

## Tentang Project
Warungio adalah platform marketplace hyperlocal yang menghubungkan pembeli, mitra warung, dan admin dalam satu ekosistem digital untuk jual beli kebutuhan harian dan produk segar.

Tidak hanya marketplace biasa, Warungio fokus pada jaringan warung lokal, stok real-time, dan distribusi berbasis area terdekat.

---

<img width="3498" height="2629" alt="sistem alur flow warungio (1)" src="https://github.com/user-attachments/assets/81fe20c9-c4a4-4d5b-b1b3-ac6ff1ab8d78" />



# Role Pengguna

## Buyer (Pembeli)
Pengguna yang melakukan belanja produk.

Fitur utama:
- Cari dan beli produk
- Repeat Order
- Wishlist
- Flash Sale
- Live Tracking
- Chat Penjual
- Pickup di Warung
- Pembayaran dan komplain

---

## Seller / Mitra Warung
Pengguna yang menjual produk.

Fitur utama:
- Kelola Produk
- Tambah/Edit Stok
- Real-Time Stock Update
- Kelola Pesanan Masuk
- Proses Pengiriman
- Chat Pembeli
- Laporan Penjualan
- Verified Store

---

## Admin system agent AI
Mengelola seluruh sistem marketplace.

Fitur utama:
- Kelola User
- Verifikasi Mitra Warung
- Monitoring Transaksi
- Kelola Produk & Kategori
- Kelola Promo
- Kelola Komplain
- Monitoring Radius Coverage
- Dashboard Analitik

---

# Fitur Utama

## Discovery & Shopping
- Barcode Scan  
- Repeat Order  
- Wishlist  
- Bundle / Paket Hemat  
- Flash Sale  
- Subscription  
- Compare Produk  
- Recently Viewed  
- Voice Search  
- Filter & Sorting  

---

## Pengiriman & Tracking
- Live Tracking  
- ETA Countdown  
- Chat Kurir  
- Schedule Delivery  
- Drop Point  
- Delivery Proof  
- Pickup di Warung  

---

## Payment & Trust
- COD  
- E-Wallet  
- Split Payment  
- Invoice  
- Verified Store  
- Garansi  
- Return / Komplain  

---

## Hyperlocal Signature
- Warung Terdekat  
- Real-Time Stok  
- Fresh Indicator  
- Mitra Warung  
- Belanja Titip  
- Ambil di Warung  
- Warung Buka Sekarang  
- Radius Coverage  

---

## Engagement
- Chat Penjual  
- Rating & Ulasan  
- Voucher  
- Loyalty Points  
- Referral  
- Promo Notification  
- Daily Check-In  

---

## Core Features
Fitur inti yang jadi identitas Warungio:

- Real-Time Stok  
- Warung Terdekat  
- Repeat Order  
- Flash Sale  
- Live Tracking  
- Verified Store  
- Chat Penjual  
- Pickup di Warung  

---

# Tech Stack

## Frontend
- React  
- HTML5  
- CSS3  
- JavaScript  

## Backend
- Node.js  
- Express.js  
- PHP  

## Database
- MySQL  

## Data Processing / Intelligence
- Python  
- Pandas (Analitik Data)  
- Scikit-learn (Rekomendasi Produk - Opsional)

## API & Services
- REST API  
- JSON  

## Tools & Development
- Git  
- GitHub  
- Vite  
- Postman  

# Struktur Project
( masih plan setiap saat berubah )

```bash
warungio/
│
│   ├── public/
│   │
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   │   ├── buyer/
│   │   │   ├── seller/
│   │   │   └── admin/
│   │   │
│   │   ├── pages/
│   │   │   ├── buyer/
│   │   │   ├── seller/
│   │   │   └── admin/
│   │   │
│   │   ├── hooks/
│   │   ├── context/
│   │   ├── services/
│   │   └── utils/
│   │
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
│
|   ├──  node.modules/
│   ├── src/
│   │   ├── config/
│   │   ├── controllers/
│   │   │   ├── authController.js
│   │   │   ├── productController.js
│   │   │   ├── orderController.js
│   │   │   └── adminController.js
│   │   │
│   │   ├── models/
│   │   ├── routes/
│   │   ├── middleware/
│   │   ├── services/
│   │   └── utils/
│   │
│   ├── app.js
│   └── server.js
│
├── database/
│   ├── schema.sql
│   └── seed.sql
│
├── .env
├── .gitignore
├── package.json
└── README.md
```

---

##  Cara Kerja Sistem
Alur sederhana:

1. Buyer memilih produk  
2. Frontend kirim request ke backend  
3. Backend memproses order  
4. Database simpan data transaksi  
5. Seller menerima order  
6. Produk diproses dan dikirim  
7. Buyer tracking pesanan  
8. Admin memonitor seluruh proses

---

##  Roadmap
Pengembangan berikutnya:

- AI rekomendasi produk  
- Smart Restock Prediction  
- Multi-warung Order Split  
- Dashboard Supply Real-Time  
- IoT Monitoring Freshness  

---

##  Author
Sagit Faturrakhman  
Sistem Informasi

---

## License
Project ini dibuat untuk pembelajaran dan pengembangan akademik.
