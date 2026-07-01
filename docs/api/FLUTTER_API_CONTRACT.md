# Warungio API Contract v2.0 — Flutter Integration Guide

## Base URL
```
Development: http://localhost:8000/api/
Production:  https://api.warungio.com/api/
```

## Authentication
All API endpoints require JWT Bearer token except public endpoints:
```http
Authorization: Bearer <access_token>
```

### Get Token
```http
POST /api/token/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

### Refresh Token
```http
POST /api/token/refresh/
Content-Type: application/json

{
  "refresh": "<refresh_token>"
}
```

---

## 1. 🏪 Supplier Management (`/api/suppliers/`)

### 1.1 List Suppliers
```http
GET /api/suppliers/
GET /api/suppliers/?category=1&city=Bandung&verification_level=verified
```

**Response:**
```json
{
  "count": 2,
  "results": [
    {
      "id": 1,
      "supplier_name": "PT Segar Makmur Abadi",
      "slug": "pt-segar-makmur-abadi",
      "category_name": "Sayuran",
      "city": "Bandung",
      "status": "active",
      "verification_level": "premium",
      "rating_avg": 4.80,
      "rating_count": 127,
      "total_products_supplied": 45,
      "on_time_delivery_rate": 97.50,
      "quality_score": 95,
      "lead_time_days": 1,
      "logo_url": "https://...",
      "is_featured": true
    }
  ]
}
```

### 1.2 Supplier Detail
```http
GET /api/suppliers/{id}/
GET /api/suppliers/{slug}/
```

### 1.3 Supplier Products
```http
GET /api/suppliers/{id}/products/
```

### 1.4 Supplier Products (all)
```http
GET /api/suppliers/products/?supplier=1&category=Sayuran
```

### 1.5 Mock Data for Development
```http
GET /api/suppliers/mock/suppliers/
GET /api/suppliers/mock/products/
```

---

## 2. ⭐ Loyalty Points (`/api/loyalty/`)

### 2.1 My Loyalty Account
```http
GET /api/loyalty/account/
```

**Response:**
```json
{
  "id": 1,
  "points_balance": 12500,
  "total_points_earned": 25000,
  "total_points_redeemed": 12500,
  "lifetime_points": 37500,
  "tier_name": "Gold",
  "tier_display_name": "Gold",
  "tier_badge_color": "#FFD700",
  "tier_multiplier": 2.00,
  "next_tier": {
    "name": "platinum",
    "display_name": "Platinum",
    "min_points": 50000,
    "icon": null
  },
  "points_to_next_tier": 37500
}
```

### 2.2 Calculate Points
```http
POST /api/loyalty/account/calculate/
{
  "order_total": 150000
}
```

### 2.3 List Rewards
```http
GET /api/loyalty/rewards/
```

### 2.4 Redeem Reward
```http
POST /api/loyalty/rewards/{id}/redeem/
```

**Response:**
```json
{
  "message": "Reward berhasil ditukarkan!",
  "redemption_id": 1,
  "reward_name": "Voucher Diskon 50%",
  "points_spent": 5000,
  "points_balance_after": 7500,
  "voucher_code": "LY-A1B2C3D4",
  "valid_until": "2026-07-28T00:00:00Z",
  "status": "approved"
}
```

### 2.5 Transaction History
```http
GET /api/loyalty/transactions/?type=earn&period=30
```

### 2.6 Full Dashboard
```http
GET /api/loyalty/dashboard/
```

### 2.7 Referral
```http
GET /api/loyalty/referral/
POST /api/loyalty/referral/claim/  {"referral_code": "WRG000001"}
```

---

## 3. 📊 Smart Stock Prediction (`/api/products/`)

### 3.1 Product Stock Prediction
```http
GET /api/products/stock-prediction/?product_id=1&days_ahead=30&history_days=90
```

**Response:**
```json
{
  "product_id": 1,
  "product_name": "Beras Premium 5kg",
  "current_stock": 12,
  "unit": "karung",
  "predicted_daily_demand": 3.5,
  "predicted_monthly_demand": 105.0,
  "confidence_score": 0.85,
  "safety_stock": 8,
  "reorder_point": 15,
  "recommended_reorder_qty": 50,
  "days_until_stockout": 3.4,
  "trend_direction": "up",
  "trend_factor": 0.12,
  "avg_daily_sales": 3.2,
  "lead_time_days": 3
}
```

### 3.2 Store Stock Forecast
```http
GET /api/products/store-forecast/?days_ahead=30
```

### 3.3 Reorder Suggestions
```http
GET /api/products/reorder-suggestions/
```

### 3.4 Mock Data
```http
GET /api/products/mock/stock-prediction/
```

---

## 4. 🤖 AI Business Insights (`/api/analytics/`)

### 4.1 Comprehensive Insights
```http
GET /api/analytics/ai/insights/?days=30
```

**Response:**
```json
{
  "store_id": 1,
  "store_name": "Warung Makmur",
  "sales_insights": { ... },
  "product_insights": { ... },
  "customer_insights": { ... },
  "inventory_insights": { ... },
  "growth_insights": { ... },
  "recommendations": [
    {
      "type": "inventory",
      "priority": "high",
      "title": "Stok Menipis",
      "description": "12 produk stok rendah",
      "action": "Restock sekarang",
      "action_url": "/seller/products/"
    }
  ]
}
```

### 4.2 Quick Insights
```http
GET /api/analytics/ai/quick/
```

### 4.3 Growth Tips
```http
GET /api/analytics/ai/growth-tips/
```

### 4.4 Mock Data
```http
GET /api/analytics/ai/mock/
```

---

## 5. 🖥️ Server Monitoring (`/api/monitoring/`)

### 5.1 Full Status
```http
GET /api/monitoring/status/
```

### 5.2 Health Check
```http
GET /api/monitoring/health/
```

### 5.3 Performance Metrics
```http
GET /api/monitoring/metrics/summary/
GET /api/monitoring/metrics/cpu/?hours=24
```

### 5.4 Error Logs
```http
GET /api/monitoring/errors/?hours=24&severity=error
```

### 5.5 Uptime
```http
GET /api/monitoring/uptime/?days=30
```

### 5.6 Mock Data
```http
GET /api/monitoring/mock/dashboard/
```

---

## 6. 📱 PWA Support

### Service Worker
```javascript
// Register in your Flutter WebView or main HTML
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/assets/pwa/service-worker.js');
}
```

### Manifest
```html
<link rel="manifest" href="/assets/pwa/manifest.json" />
<meta name="theme-color" content="#059669" />
```

---

## Error Response Format

All endpoints return consistent error format:
```json
{
  "error": "Deskripsi error dalam Bahasa Indonesia",
  "status_code": 400
}
```

## Pagination

List endpoints support pagination:
```http
GET /api/suppliers/?page=1&page_size=20
```

```json
{
  "count": 45,
  "next": "/api/suppliers/?page=2",
  "previous": null,
  "results": [...]
}
```

## Rate Limiting
- Anonymous: 100 requests/hour
- Authenticated: 1000 requests/hour
- OTP: 5 requests/minute
- Login: 10 requests/minute

## WebSocket Events
- `ws://host/ws/notifications/{user_id}/` — Real-time notifications
- `ws://host/ws/chat/{conversation_id}/` — Real-time chat
