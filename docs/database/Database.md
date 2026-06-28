# WARUNGIO MARKETPLACE - DATABASE GUIDE

Version: 1.0

Database Engine:
MySQL / MariaDB

Database Name:
warungio_db

Character Set:
utf8mb4

Collation:
utf8mb4_unicode_ci

---

# 1. DATABASE OVERVIEW

Warungio menggunakan database relasional untuk mengelola:

* Authentication
* Buyer System
* Seller System
* Product Management
* Cart & Checkout
* Payment
* Delivery
* Reviews
* Chat
* Notifications
* AI Quality Check

---

# 2. DATABASE ARCHITECTURE

users
│
├── stores
│
├── orders
│
├── reviews
│
├── chats
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
├── product_gallery
│
├── cart
│
├── order_items
│
├── reviews
│
└── quality_checks

orders
│
├── order_items
│
├── payments
│
└── deliveries

---

# 3. CORE TABLES

## users

Purpose:
Menyimpan data seluruh pengguna.

Columns:

id
fullname
email
phone
password
role
otp
is_verified
profile_photo
created_at

Roles:

buyer
seller
admin

---

## stores

Purpose:
Menyimpan informasi toko seller.

Columns:

id
user_id
store_name
category
description
address
city
province
postal_code
latitude
longitude
open_time
close_time
bank_name
bank_account
bank_owner
store_logo
status
created_at

---

## categories

Purpose:
Kategori produk marketplace.

Examples:

Sayuran
Buah
Sembako
Protein
Bumbu Dapur
Minuman
Frozen Food

Columns:

id
category_name
category_icon

---

## products

Purpose:
Data seluruh produk.

Columns:

id
store_id
category_id
product_name
description
product_photo
price
stock
unit
quality_score
product_status
created_at

Product Status:

fresh
normal
warning
rejected

---

## product_gallery

Purpose:
Galeri foto produk.

Columns:

id
product_id
image
created_at

---

# 4. MARKETPLACE TABLES

## cart

Purpose:
Keranjang belanja user.

Columns:

id
user_id
product_id
qty
created_at

---

## favorites

Purpose:
Wishlist produk.

Columns:

id
user_id
product_id
created_at

---

# 5. ORDER MANAGEMENT

## orders

Purpose:
Data transaksi utama.

Columns:

id
user_id
store_id
total_price
shipping_cost
payment_method
order_status
delivery_address
created_at

Order Status:

pending
paid
processed
shipped
completed
cancelled

---

## order_items

Purpose:
Detail produk dalam pesanan.

Columns:

id
order_id
product_id
qty
price
subtotal

---

# 6. PAYMENT SYSTEM

## payments

Purpose:
Menyimpan data pembayaran.

Columns:

id
order_id
payment_type
payment_status
transaction_code
paid_at
created_at

Payment Type:

COD
BANK_TRANSFER
E_WALLET

Payment Status:

pending
paid
failed

---

# 7. DELIVERY SYSTEM

## deliveries

Purpose:
Tracking pengiriman.

Columns:

id
order_id
courier_name
tracking_number
delivery_status
estimated_time
created_at

Delivery Status:

waiting
picked_up
on_delivery
delivered

---

# 8. PROMOTION SYSTEM

## promotions

Purpose:
Promosi seller.

Columns:

id
store_id
promotion_name
description
discount_percent
start_date
end_date
banner
created_at

---

## vouchers

Purpose:
Voucher marketplace.

Columns:

id
voucher_code
discount_amount
min_purchase
expired_date
created_at

---

# 9. REVIEW SYSTEM

## reviews

Purpose:
Ulasan produk.

Columns:

id
user_id
product_id
rating
comment
created_at

Rating:

1
2
3
4
5

---

# 10. CHAT SYSTEM

## chats

Purpose:
Komunikasi buyer dan seller.

Columns:

id
sender_id
receiver_id
message
is_read
created_at

---

# 11. NOTIFICATION SYSTEM

## notifications

Purpose:
Notifikasi sistem.

Columns:

id
user_id
title
description
is_read
created_at

Events:

Order Created
Order Paid
Order Shipped
Order Delivered
Promotion Created

---

# 12. CUSTOMER SUPPORT

## supports

Purpose:
Ticket bantuan pengguna.

Columns:

id
user_id
subject
message
support_status
created_at

Support Status:

open
closed

---

# 13. AI QUALITY CHECK

## quality_checks

Purpose:
Hasil analisis kualitas produk.

Columns:

id
product_id
freshness_score
stock_status
ai_result
checked_at

Output:

Fresh
Good
Warning
Rejected

---

# 14. ANALYTICS TABLES

## reports

Purpose:
Ringkasan laporan toko.

Columns:

id
store_id
report_date
total_sales
total_orders
total_customers
created_at

---

# 15. DATABASE RELATIONSHIP

users
│
├── stores
│
├── cart
│
├── orders
│
├── reviews
│
├── chats
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
├── product_gallery
│
├── cart
│
├── reviews
│
├── quality_checks
│
└── order_items

orders
│
├── order_items
│
├── payments
│
└── deliveries

---

# 16. INDEXING STRATEGY

Indexed Columns:

users.email

users.phone

products.store_id

products.category_id

orders.user_id

orders.store_id

deliveries.order_id

notifications.user_id

Purpose:

Fast Search
Fast Checkout
Fast Dashboard Queries

---

# 17. SECURITY RULES

Passwords:

Hashed

OTP:

Temporary

Roles:

buyer
seller
admin

Database Rules:

Foreign Key Enabled

Unique Email

Unique Phone

Soft Delete Recommended

---

# 18. FUTURE TABLES

future_wallets

future_transactions

future_loyalty_points

future_ai_predictions

future_delivery_tracking

future_push_notifications

---

# 19. DATABASE BACKUP

Daily Backup

Weekly Full Backup

Retention:

30 Days

Backup Format:

SQL Dump

Storage:

Cloud Backup
Local Backup

---

# 20. DATABASE STATUS

Authentication Tables ✅

Marketplace Tables ✅

Seller Tables ✅

Checkout Tables ✅

Payment Tables ✅

Delivery Tables ✅

Review Tables ✅

Notification Tables ✅

AI Tables ✅

Production Ready ✅
