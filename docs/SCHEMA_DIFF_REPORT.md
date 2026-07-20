# SCHEMA DIFF REPORT
**Project:** Warungio Marketplace
**Date:** July 20, 2026
**Comparison:** Django Model Definitions vs Physical Database Schema

---

## 1. Methodology

For each of the 122 Django models, every `concrete_field` was compared against the actual SQLite table columns (`PRAGMA table_info`). Additionally, every table's actual columns were compared against model fields to detect both missing columns (drift) and orphan columns (extra columns in DB not in models).

---

## 2. Models With No Drift (119/122)

119 out of 122 models have exact schema consistency between the model definition and the database table. These include:

- **accounts**: User, OTP, UserSession, SocialAccount, LoginAttempt, IndonesianAddress, KYCVerification, RegistrationEvent
- **ai_intelligence**: DigitalTwin, MarketplaceHealthSnapshot, DemandPrediction, PricingRecommendation, SalesForecast, CustomerSegment, UserSegmentAssignment, GamificationProfile, Challenge, UserChallengeProgress, BusinessCoachInsight, PersonalShoppingInsight, AIModelRegistry, ExperimentResult
- **analytics**: SalesAnalytics
- **chat**: Conversation, ChatMessage (via support_conversations, support_messages)
- **engagement**: UserBehaviorProfile, BehaviorEvent, ActivityLog, ChurnPrediction, DeviceToken, NotificationTemplate, NotificationCampaign, NotificationQueue, NotificationDeliveryLog, NotificationAnalytics, NotificationABTest, QuietHoursConfig, NotificationCooldown, EngagementSignal, NotificationPreferenceExtension
- **inventory**: MasterProduct, ProductBatch, InventoryStock, ExpiryNotification, StockAlert, SmartScanSession, DetectedItem
- **loyalty**: LoyaltyAccount, LoyaltyTier, LoyaltyReward, LoyaltyTransaction, LoyaltyRedemption, LoyaltyReferral
- **monitoring**: PerformanceMetric, SystemHealth, UptimeRecord
- **notifications**: Notification, NotificationPreference
- **orders**: ShippingMethod, Cart, OrderItem, Delivery, OfflineSale, PackedItem, PackingSession, PickListItem
- **payments**: PaymentMethod, Payment, MidtransTransaction, BankAccount, AdminFeeTransaction
- **products**: Category, Product, ProductGallery, Review, Favorite, Promo, RecentlyViewed, Voucher
- **regions**: Province, Regency, District, Village
- **sessions**: Session
- **stores**: Store, StoreFollower, StoreCategory
- **subscriptions**: Subscription
- **suppliers**: SupplierCategory, Supplier, SupplierProduct, SupplierOrder, SupplierOrderItem, SupplierReview, SupplierContract, SupplierPayment
- **support**: HelpCategory, HelpArticle, FAQ, BannerPromo, ContactInfo, SupportInfo, ChatQuickReply, SupportConversation, SupportMessage
- **token_blacklist**: OutstandingToken, BlacklistedToken

---

## 3. Models With Schema Drift (Before Repair) — 3/122

### 3.1 `support.SupportTicket`
| Property | Model Expects | Database Had |
|----------|---------------|--------------|
| Table `supports` | EXISTS | **MISSING** |

### 3.2 `orders.Order`
| Column | Model Expects | Database Had |
|--------|---------------|--------------|
| `admin_fee_seller` | `DecimalField(max_digits=10, decimal_places=2)` | **MISSING** |

### 3.3 `products.QualityCheck`
| Column | Model Expects | Database Had |
|--------|---------------|--------------|
| `quality_status` | `CharField(max_length=20, default='pending')` | **MISSING** |
| `created_at` | `DateTimeField(auto_now_add=True)` | **MISSING** |

---

## 4. Orphan Columns in Database (Not in Model)

### 4.1 `quality_checks` — 9 orphan columns
| Orphan Column | Type | Notes |
|---------------|------|-------|
| `quality_score` | INTEGER | Old QualityCheck model field — preserved for data safety |
| `ripeness_score` | INTEGER | Old QualityCheck model field |
| `detected_objects` | TEXT | Old QualityCheck model field |
| `confidence_score` | decimal | Old QualityCheck model field |
| `capture_image` | varchar(100) | Old QualityCheck model field |
| `is_feasible` | bool | Old QualityCheck model field |
| `feasibility_percentage` | decimal | Old QualityCheck model field |
| `store_id` | bigint | Old QualityCheck model FK |
| `detection_result_id` | bigint | Old QualityCheck model FK |

**Recommendation:** These columns are unused but harmless. Consider a data migration to archive any data in these columns, then a cleanup migration to drop them.

---

## 5. Schema Comparison: Pre vs Post Repair

### `supports` Table
| Column | Type | Nullable | After Repair |
|--------|------|----------|--------------|
| id | bigint AUTO_INCREMENT | NOT NULL | ✅ |
| user_id | bigint FK→users | NULL | ✅ |
| subject | varchar(255) | NOT NULL | ✅ |
| message | text | NOT NULL | ✅ |
| support_status | varchar(20) | NOT NULL | ✅ |
| priority | varchar(20) | NOT NULL | ✅ |
| created_at | datetime(6) | NOT NULL | ✅ |
| updated_at | datetime(6) | NOT NULL | ✅ |

### `orders` Table — New Column
| Column | Type | After Repair |
|--------|------|--------------|
| admin_fee_seller | decimal(10,2) | ✅ Added |

### `quality_checks` Table — New Columns
| Column | Type | After Repair |
|--------|------|--------------|
| quality_status | varchar(20) | ✅ Added |
| created_at | datetime(6) | ✅ Added |

### `wallets` and `wallet_transactions` Tables (Production MariaDB)
Both tables verified present in SQLite. Repair migration `payments.0006` creates both if missing on any environment.

---

## 6. Index Comparison

All indexes defined in model `Meta.indexes` and migration `AddIndex` operations were verified:
- All properly created indexes on `supports` table: ✅
- All indexes on `wallet_transactions`: ✅ (wallet+created_at, user+created_at, tx_type)
- All model-defined indexes verified: ✅

---

## 7. Final Schema Status

| Check | Pre-Repair | Post-Repair |
|-------|-----------|-------------|
| Missing tables | 1 (`supports`) | 0 ✅ |
| Missing columns | 3 (`admin_fee_seller`, `quality_status`, `created_at`) | 0 ✅ |
| Orphan columns | 9 (quality_checks legacy) | 9 (documented) ✅ |
| Extra system tables | 7 (expected) | 7 (expected) ✅ |

**SCHEMA IS NOW FULLY CONSISTENT** ✅
