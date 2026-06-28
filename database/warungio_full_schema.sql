-- =============================================================================
-- WARUNGIO MARKETPLACE — Complete MariaDB/MySQL Database Schema
-- Compatible with Django 4.2+, XAMPP phpMyAdmin, and Production Deployments
-- =============================================================================
-- How to import:
--   1. Open phpMyAdmin (http://localhost/phpmyadmin)
--   2. Click "New" → create database "warungio_db" (utf8mb4_general_ci)
--   3. Select the "warungio_db" database
--   4. Click "Import" tab → Choose this file → "Go"
--   5. Or: mysql -u root -p warungio_db < warungio_full_schema.sql
-- =============================================================================

CREATE DATABASE IF NOT EXISTS `warungio_db`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_general_ci;

USE `warungio_db`;

-- Django system tables (must be created BEFORE users join tables)
CREATE TABLE `django_content_type` (
  `id`        INT AUTO_INCREMENT PRIMARY KEY,
  `app_label` VARCHAR(100) NOT NULL,
  `model`     VARCHAR(100) NOT NULL,
  UNIQUE KEY `django_content_type_app_label_model_unique` (`app_label`, `model`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `auth_permission` (
  `id`              INT AUTO_INCREMENT PRIMARY KEY,
  `name`            VARCHAR(255) NOT NULL,
  `content_type_id` INT NOT NULL,
  `codename`        VARCHAR(100) NOT NULL,
  UNIQUE KEY `auth_permission_contenttype_codename_unique` (`content_type_id`, `codename`),
  CONSTRAINT `fk_auth_perm_content_type` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `auth_group` (
  `id`   INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(150) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Now create users (no FKs to auth tables, only join tables reference them)
CREATE TABLE `users` (
  `id`              BIGINT AUTO_INCREMENT PRIMARY KEY,
  `password`        VARCHAR(128) NOT NULL,
  `last_login`      DATETIME(6)  NULL,
  `is_superuser`    TINYINT(1)   NOT NULL DEFAULT 0,
  `username`        VARCHAR(150) NOT NULL UNIQUE,
  `first_name`      VARCHAR(150) NOT NULL DEFAULT '',
  `last_name`       VARCHAR(150) NOT NULL DEFAULT '',
  `is_staff`        TINYINT(1)   NOT NULL DEFAULT 0,
  `is_active`       TINYINT(1)   NOT NULL DEFAULT 1,
  `date_joined`     DATETIME(6)  NOT NULL,
  `email`           VARCHAR(254) NOT NULL UNIQUE,
  `phone`           VARCHAR(128) NULL UNIQUE,
  `full_name`       VARCHAR(100) NOT NULL,
  `role`            VARCHAR(20)  NOT NULL DEFAULT 'buyer',
  `is_verified`     TINYINT(1)   NOT NULL DEFAULT 0,
  `otp_secret`      VARCHAR(32)  NULL,
  `address`         TEXT         NULL,
  `profile_photo`   VARCHAR(100) NULL,
  `bio`             TEXT         NULL,
  `last_login_ip`   VARCHAR(39)  NULL,
  `device_info`     JSON         NULL,
  `created_at`      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at`      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  `is_mobile`       TINYINT(1)   NOT NULL DEFAULT 0,
  `is_tablet`       TINYINT(1)   NOT NULL DEFAULT 0,
  `is_desktop`      TINYINT(1)   NOT NULL DEFAULT 1,
  `browser_family`  VARCHAR(50)  NULL,
  `os_family`       VARCHAR(50)  NULL,

  INDEX `users_email_idx` (`email`),
  INDEX `users_phone_idx` (`phone`),
  INDEX `users_role_idx` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Users join tables (auth_group and auth_permission already exist)
CREATE TABLE `users_groups` (
  `id`       BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id`  BIGINT NOT NULL,
  `group_id` INT    NOT NULL,
  UNIQUE KEY `users_groups_unique` (`user_id`, `group_id`),
  CONSTRAINT `fk_users_groups_user`  FOREIGN KEY (`user_id`)  REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_users_groups_group` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `users_user_permissions` (
  `id`              BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id`         BIGINT NOT NULL,
  `permission_id`   INT    NOT NULL,
  UNIQUE KEY `users_user_perms_unique` (`user_id`, `permission_id`),
  CONSTRAINT `fk_users_perms_user`       FOREIGN KEY (`user_id`)       REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_users_perms_permission` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `auth_group_permissions` (
  `id`            BIGINT AUTO_INCREMENT PRIMARY KEY,
  `group_id`      INT NOT NULL,
  `permission_id` INT NOT NULL,
  UNIQUE KEY `auth_group_perms_unique` (`group_id`, `permission_id`),
  CONSTRAINT `fk_auth_group_perms_group`      FOREIGN KEY (`group_id`)      REFERENCES `auth_group` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_auth_group_perms_permission` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Django migration tracking & session (no FKs to other tables)
CREATE TABLE `django_migrations` (
  `id`      BIGINT AUTO_INCREMENT PRIMARY KEY,
  `app`     VARCHAR(255) NOT NULL,
  `name`    VARCHAR(255) NOT NULL,
  `applied` DATETIME(6)  NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `django_session` (
  `session_key`  VARCHAR(40) NOT NULL PRIMARY KEY,
  `session_data` LONGTEXT    NOT NULL,
  `expire_date`  DATETIME(6) NOT NULL,
  INDEX `django_session_expire_date_idx` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =============================================================================
-- 2. OTP — Verification codes
-- =============================================================================
CREATE TABLE `otps` (
  `id`          BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id`     BIGINT       NULL,
  `email`       VARCHAR(254) NULL,
  `phone`       VARCHAR(20)  NULL,
  `otp_code`    VARCHAR(6)   NOT NULL,
  `otp_type`    VARCHAR(20)  NOT NULL DEFAULT 'email',
  `purpose`     VARCHAR(30)  NOT NULL DEFAULT 'registration',
  `is_used`     TINYINT(1)   NOT NULL DEFAULT 0,
  `is_valid`    TINYINT(1)   NOT NULL DEFAULT 1,
  `attempts`    INT          NOT NULL DEFAULT 0,
  `max_attempts` INT         NOT NULL DEFAULT 5,
  `created_at`  DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `expires_at`  DATETIME(6)  NOT NULL,
  `verified_at` DATETIME(6)  NULL,
  `ip_address`  VARCHAR(39)  NULL,
  `user_agent`  TEXT         NULL,

  INDEX `otps_email_purpose_idx` (`email`, `purpose`),
  INDEX `otps_code_idx`          (`otp_code`),
  INDEX `otps_expires_idx`       (`expires_at`),
  CONSTRAINT `fk_otps_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 3. USER SESSIONS — Device tracking
-- =============================================================================
CREATE TABLE `user_sessions` (
  `id`            BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id`       BIGINT       NOT NULL,
  `session_key`   VARCHAR(40)  NOT NULL UNIQUE,
  `ip_address`    VARCHAR(39)  NOT NULL,
  `user_agent`    TEXT         NULL,
  `device_type`   VARCHAR(20)  NOT NULL DEFAULT 'desktop',
  `is_active`     TINYINT(1)   NOT NULL DEFAULT 1,
  `last_activity` DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  `created_at`    DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

  INDEX `sessions_user_active_idx` (`user_id`, `is_active`),
  CONSTRAINT `fk_sessions_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 4. SOCIAL ACCOUNTS — Google/Facebook/Apple login
-- =============================================================================
CREATE TABLE `social_accounts` (
  `id`          BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id`     BIGINT       NOT NULL,
  `provider`    VARCHAR(20)  NOT NULL COMMENT 'google | facebook | apple',
  `provider_id` VARCHAR(255) NOT NULL,
  `extra_data`  JSON         NOT NULL DEFAULT '{}',
  `created_at`  DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at`  DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

  UNIQUE KEY `social_accounts_provider_unique` (`provider`, `provider_id`),
  INDEX `social_accounts_provider_idx` (`provider`, `provider_id`),
  INDEX `social_accounts_user_provider_idx` (`user_id`, `provider`),
  CONSTRAINT `fk_social_accounts_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 5. LOGIN ATTEMPTS — Security monitoring
-- =============================================================================
CREATE TABLE `login_attempts` (
  `id`            BIGINT AUTO_INCREMENT PRIMARY KEY,
  `email`         VARCHAR(254) NOT NULL,
  `ip_address`    VARCHAR(39)  NOT NULL,
  `user_agent`    TEXT         NULL,
  `was_successful` TINYINT(1)  NOT NULL DEFAULT 0,
  `attempted_at`  DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

  INDEX `login_attempts_email_idx` (`email`),
  INDEX `login_attempts_ip_idx` (`ip_address`),
  INDEX `login_attempts_time_idx` (`attempted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 6. STORE CATEGORIES — Classification
-- =============================================================================
CREATE TABLE `store_categories` (
  `id`        INT AUTO_INCREMENT PRIMARY KEY,
  `name`      VARCHAR(100) NOT NULL UNIQUE,
  `icon`      VARCHAR(100) NULL,
  `order`     INT          NOT NULL DEFAULT 0,
  `is_active` TINYINT(1)   NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 7. STORES — Seller profiles
-- =============================================================================
CREATE TABLE `stores` (
  `id`              BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id`         BIGINT       NOT NULL UNIQUE,
  `store_name`      VARCHAR(100) NOT NULL,
  `slug`            VARCHAR(120) NOT NULL UNIQUE,
  `category`        VARCHAR(100) NULL COMMENT 'String category (flexible)',
  `description`     TEXT         NULL,
  `address`         TEXT         NULL,
  `city`            VARCHAR(100) NULL,
  `province`        VARCHAR(100) NULL,
  `postal_code`     VARCHAR(10)  NULL,
  `latitude`        DECIMAL(10,7) NULL,
  `longitude`       DECIMAL(10,7) NULL,
  `open_time`       TIME         NULL,
  `close_time`      TIME         NULL,
  `delivery_type`   VARCHAR(100) NULL,
  `service_area`    VARCHAR(100) NULL,
  `bank_name`       VARCHAR(100) NULL,
  `bank_account`    VARCHAR(100) NULL,
  `bank_owner`      VARCHAR(100) NULL,
  `store_logo`      VARCHAR(100) NULL,
  `store_banner`    VARCHAR(100) NULL,
  `status`          VARCHAR(20)  NOT NULL DEFAULT 'pending' COMMENT 'pending | active | rejected | suspended',
  `follower_count`  INT          NOT NULL DEFAULT 0,
  `product_count`   INT          NOT NULL DEFAULT 0,
  `rating_avg`      DECIMAL(3,2) NOT NULL DEFAULT 0.00,
  `total_sales`     DECIMAL(15,2) NOT NULL DEFAULT 0.00,
  `is_open`         TINYINT(1)   NOT NULL DEFAULT 1,
  `created_at`      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at`      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

  INDEX `stores_name_idx` (`store_name`),
  INDEX `stores_city_idx` (`city`),
  INDEX `stores_status_idx` (`status`),
  INDEX `stores_rating_idx` (`rating_avg`),
  CONSTRAINT `fk_stores_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 8. STORE FOLLOWERS
-- =============================================================================
CREATE TABLE `store_followers` (
  `id`         BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id`    BIGINT      NOT NULL,
  `store_id`   BIGINT      NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

  UNIQUE KEY `store_followers_unique` (`user_id`, `store_id`),
  INDEX `store_followers_user_store_idx` (`user_id`, `store_id`),
  CONSTRAINT `fk_followers_user`  FOREIGN KEY (`user_id`)  REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_followers_store` FOREIGN KEY (`store_id`) REFERENCES `stores` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 9. PRODUCT CATEGORIES
-- =============================================================================
CREATE TABLE `categories` (
  `id`              INT AUTO_INCREMENT PRIMARY KEY,
  `category_name`   VARCHAR(100) NOT NULL,
  `category_icon`   VARCHAR(100) NULL,
  `category_image`  VARCHAR(100) NULL,
  `order`           INT          NOT NULL DEFAULT 0,
  `is_active`       TINYINT(1)   NOT NULL DEFAULT 1,
  `created_at`      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 10. PRODUCTS — Core product listings
-- =============================================================================
CREATE TABLE `products` (
  `id`              BIGINT AUTO_INCREMENT PRIMARY KEY,
  `store_id`        BIGINT       NOT NULL,
  `category_id`     INT          NULL,
  `product_name`    VARCHAR(150) NOT NULL,
  `slug`            VARCHAR(170) NOT NULL,
  `description`     TEXT         NULL,
  `product_photo`   VARCHAR(100) NULL,
  `price`           DECIMAL(10,2) NOT NULL,
  `stock`           INT          NOT NULL DEFAULT 0,
  `unit`            VARCHAR(50)  NOT NULL DEFAULT 'pcs',
  `quality_score`   INT          NOT NULL DEFAULT 0 COMMENT '0-100',
  `product_status`  VARCHAR(20)  NOT NULL DEFAULT 'fresh' COMMENT 'fresh | normal | low | bad',
  `sold_count`      INT          NOT NULL DEFAULT 0,
  `rating_avg`      DECIMAL(3,2) NOT NULL DEFAULT 0.00,
  `review_count`    INT          NOT NULL DEFAULT 0,
  `is_active`       TINYINT(1)   NOT NULL DEFAULT 1,
  `is_featured`     TINYINT(1)   NOT NULL DEFAULT 0,
  `created_at`      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at`      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

  INDEX `products_store_active_idx` (`store_id`, `is_active`),
  INDEX `products_category_idx` (`category_id`),
  INDEX `products_name_idx` (`product_name`),
  INDEX `products_price_idx` (`price`),
  INDEX `products_created_idx` (`created_at`),
  CONSTRAINT `fk_products_store`    FOREIGN KEY (`store_id`)    REFERENCES `stores` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_products_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 11. PRODUCT GALLERY — Additional images
-- =============================================================================
CREATE TABLE `product_gallery` (
  `id`         BIGINT AUTO_INCREMENT PRIMARY KEY,
  `product_id` BIGINT       NOT NULL,
  `image`      VARCHAR(100) NOT NULL,
  `order`      INT          NOT NULL DEFAULT 0,
  `created_at` DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

  CONSTRAINT `fk_gallery_product` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 12. REVIEWS — Product ratings & reviews
-- =============================================================================
CREATE TABLE `reviews` (
  `id`          BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id`     BIGINT       NULL,
  `product_id`  BIGINT       NOT NULL,
  `rating`      INT          NOT NULL COMMENT '1-5',
  `comment`     TEXT         NULL,
  `is_verified` TINYINT(1)   NOT NULL DEFAULT 0,
  `created_at`  DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

  UNIQUE KEY `reviews_user_product_unique` (`user_id`, `product_id`),
  INDEX `reviews_product_rating_idx` (`product_id`, `rating`),
  CONSTRAINT `fk_reviews_user`    FOREIGN KEY (`user_id`)    REFERENCES `users` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_reviews_product` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 13. FAVORITES — Wishlist
-- =============================================================================
CREATE TABLE `favorites` (
  `id`         BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id`    BIGINT      NOT NULL,
  `product_id` BIGINT      NOT NULL,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

  UNIQUE KEY `favorites_user_product_unique` (`user_id`, `product_id`),
  CONSTRAINT `fk_favorites_user`    FOREIGN KEY (`user_id`)    REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_favorites_product` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 14. CART — Shopping cart
-- =============================================================================
CREATE TABLE `cart` (
  `id`         BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id`    BIGINT      NOT NULL,
  `product_id` BIGINT      NOT NULL,
  `qty`        INT         NOT NULL DEFAULT 1,
  `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

  UNIQUE KEY `cart_user_product_unique` (`user_id`, `product_id`),
  CONSTRAINT `fk_cart_user`    FOREIGN KEY (`user_id`)    REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_cart_product` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 15. ORDERS
-- =============================================================================
CREATE TABLE `orders` (
  `id`                BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id`           BIGINT       NULL,
  `store_id`          BIGINT       NULL,
  `order_number`      VARCHAR(30)  NOT NULL UNIQUE,
  `notes`             TEXT         NULL,
  `subtotal`          DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  `shipping_cost`     DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `discount`          DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `total_price`       DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  `payment_method`    VARCHAR(20)  NOT NULL DEFAULT 'midtrans',
  `payment_status`    VARCHAR(20)  NOT NULL DEFAULT 'pending',
  `order_status`      VARCHAR(20)  NOT NULL DEFAULT 'pending'
                       COMMENT 'pending | paid | processed | shipped | completed | cancelled | refunded',
  `delivery_address`  TEXT         NOT NULL,
  `recipient_name`    VARCHAR(100) NULL,
  `recipient_phone`   VARCHAR(20)  NULL,
  `courier`           VARCHAR(50)  NULL,
  `tracking_number`   VARCHAR(100) NULL,
  `estimated_delivery` DATETIME(6) NULL,
  `created_at`        DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at`        DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  `completed_at`      DATETIME(6)  NULL,

  INDEX `orders_user_status_idx` (`user_id`, `order_status`),
  INDEX `orders_store_status_idx` (`store_id`, `order_status`),
  INDEX `orders_number_idx` (`order_number`),
  INDEX `orders_created_idx` (`created_at`),
  CONSTRAINT `fk_orders_user`  FOREIGN KEY (`user_id`)  REFERENCES `users` (`id`)  ON DELETE SET NULL,
  CONSTRAINT `fk_orders_store` FOREIGN KEY (`store_id`) REFERENCES `stores` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 16. ORDER ITEMS
-- =============================================================================
CREATE TABLE `order_items` (
  `id`            BIGINT AUTO_INCREMENT PRIMARY KEY,
  `order_id`      BIGINT       NOT NULL,
  `product_id`    BIGINT       NULL,
  `product_name`  VARCHAR(150) NOT NULL DEFAULT '',
  `product_photo` VARCHAR(255) NOT NULL DEFAULT '',
  `qty`           INT          NOT NULL,
  `price`         DECIMAL(10,2) NOT NULL,
  `subtotal`      DECIMAL(12,2) NOT NULL,

  CONSTRAINT `fk_order_items_order`   FOREIGN KEY (`order_id`)   REFERENCES `orders` (`id`)   ON DELETE CASCADE,
  CONSTRAINT `fk_order_items_product` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 17. DELIVERIES — Tracking info
-- =============================================================================
CREATE TABLE `deliveries` (
  `id`                BIGINT AUTO_INCREMENT PRIMARY KEY,
  `order_id`          BIGINT       NOT NULL UNIQUE,
  `courier_name`      VARCHAR(100) NULL,
  `tracking_number`   VARCHAR(100) NULL,
  `delivery_status`   VARCHAR(20)  NOT NULL DEFAULT 'waiting'
                      COMMENT 'waiting | picked_up | on_delivery | delivered',
  `estimated_time`    VARCHAR(100) NULL,
  `delivered_at`      DATETIME(6)  NULL,
  `notes`             TEXT         NULL,
  `created_at`        DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

  CONSTRAINT `fk_deliveries_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 18. PAYMENT METHODS
-- =============================================================================
CREATE TABLE `payment_methods` (
  `id`            INT AUTO_INCREMENT PRIMARY KEY,
  `name`          VARCHAR(50)  NOT NULL COMMENT 'credit_card | bank_transfer | gopay | ovo | dana | qris | cod',
  `display_name`  VARCHAR(100) NOT NULL,
  `icon`          VARCHAR(255) NULL,
  `is_active`     TINYINT(1)   NOT NULL DEFAULT 1,
  `fee_percent`   DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  `order`         INT          NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 19. PAYMENTS — Transaction records
-- =============================================================================
CREATE TABLE `payments` (
  `id`                    BIGINT AUTO_INCREMENT PRIMARY KEY,
  `order_id`              BIGINT       NOT NULL,
  `user_id`               BIGINT       NULL,
  `payment_type`          VARCHAR(100) NULL,
  `payment_status`        VARCHAR(20)  NOT NULL DEFAULT 'pending'
                          COMMENT 'pending | paid | failed | refunded | expired',
  `amount`                DECIMAL(12,2) NOT NULL,
  `fee`                   DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `net_amount`            DECIMAL(12,2) NULL,
  `transaction_code`      VARCHAR(100) NULL UNIQUE,
  `midtrans_transaction_id` VARCHAR(100) NULL,
  `midtrans_order_id`     VARCHAR(100) NULL,
  `bank_name`             VARCHAR(50)  NULL,
  `va_number`             VARCHAR(50)  NULL,
  `payment_response`      JSON         NULL,
  `paid_at`               DATETIME(6)  NULL,
  `expired_at`            DATETIME(6)  NULL,
  `created_at`            DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at`            DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

  INDEX `payments_txn_code_idx` (`transaction_code`),
  INDEX `payments_status_idx` (`payment_status`),
  INDEX `payments_order_idx` (`order_id`),
  CONSTRAINT `fk_payments_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_payments_user`  FOREIGN KEY (`user_id`)  REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 20. MIDTRANS TRANSACTIONS
-- =============================================================================
CREATE TABLE `midtrans_transactions` (
  `id`                 BIGINT AUTO_INCREMENT PRIMARY KEY,
  `payment_id`         BIGINT       NOT NULL UNIQUE,
  `order_id`           VARCHAR(100) NOT NULL UNIQUE,
  `transaction_id`     VARCHAR(100) NULL,
  `transaction_status` VARCHAR(20)  NOT NULL DEFAULT 'pending',
  `transaction_time`   DATETIME(6)  NULL,
  `settlement_time`    DATETIME(6)  NULL,
  `payment_type`       VARCHAR(50)  NULL,
  `bank`               VARCHAR(50)  NULL,
  `va_number`          VARCHAR(50)  NULL,
  `bill_key`           VARCHAR(100) NULL,
  `biller_code`        VARCHAR(100) NULL,
  `status_code`        VARCHAR(10)  NULL,
  `status_message`     TEXT         NULL,
  `raw_response`       JSON         NULL,
  `fraud_status`       VARCHAR(20)  NULL,
  `created_at`         DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at`         DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

  INDEX `midtrans_order_idx` (`order_id`),
  INDEX `midtrans_status_idx` (`transaction_status`),
  CONSTRAINT `fk_midtrans_payment` FOREIGN KEY (`payment_id`) REFERENCES `payments` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 21. PROMOS — Discount campaigns
-- =============================================================================
CREATE TABLE `promos` (
  `id`              INT AUTO_INCREMENT PRIMARY KEY,
  `promo_name`      VARCHAR(100) NOT NULL,
  `description`     TEXT         NULL,
  `discount_percent` INT         NOT NULL DEFAULT 0 COMMENT '0-100',
  `start_date`      DATE         NOT NULL,
  `end_date`        DATE         NOT NULL,
  `promo_banner`    VARCHAR(100) NULL,
  `is_active`       TINYINT(1)   NOT NULL DEFAULT 1,
  `created_at`      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 22. VOUCHERS — Discount codes
-- =============================================================================
CREATE TABLE `vouchers` (
  `id`              INT AUTO_INCREMENT PRIMARY KEY,
  `voucher_code`    VARCHAR(50)  NOT NULL UNIQUE,
  `discount_amount` DECIMAL(10,2) NOT NULL,
  `min_purchase`    DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `expired_date`    DATE         NOT NULL,
  `is_active`       TINYINT(1)   NOT NULL DEFAULT 1,
  `created_at`      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 23. SALES ANALYTICS — Daily sales aggregation
-- =============================================================================
CREATE TABLE `sales_analytics` (
  `id`                   BIGINT AUTO_INCREMENT PRIMARY KEY,
  `store_id`             BIGINT       NOT NULL,
  `date`                 DATE         NOT NULL,
  `total_sales`          DECIMAL(15,2) NOT NULL DEFAULT 0.00,
  `total_orders`         INT          NOT NULL DEFAULT 0,
  `total_products_sold`  INT          NOT NULL DEFAULT 0,
  `average_order_value`  DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `new_customers`        INT          NOT NULL DEFAULT 0,
  `returning_customers`  INT          NOT NULL DEFAULT 0,
  `hourly_sales`         JSON         NULL,
  `hourly_orders`        JSON         NULL,
  `payment_methods`      JSON         NULL,
  `created_at`           DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at`           DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

  UNIQUE KEY `sales_analytics_store_date_unique` (`store_id`, `date`),
  INDEX `sales_analytics_date_idx` (`date`),
  CONSTRAINT `fk_sales_analytics_store` FOREIGN KEY (`store_id`) REFERENCES `stores` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 24. DEVICE ANALYTICS — Traffic source data
-- =============================================================================
CREATE TABLE `device_analytics` (
  `id`            BIGINT AUTO_INCREMENT PRIMARY KEY,
  `store_id`      BIGINT       NULL,
  `date`          DATE         NOT NULL,
  `device_type`   VARCHAR(20)  NOT NULL COMMENT 'mobile | tablet | desktop',
  `browser`       VARCHAR(50)  NULL,
  `os`            VARCHAR(50)  NULL,
  `visitors_count` INT         NOT NULL DEFAULT 0,
  `page_views`    INT          NOT NULL DEFAULT 0,
  `bounce_rate`   DECIMAL(5,2) NOT NULL DEFAULT 0.00,

  INDEX `device_analytics_store_date_idx` (`store_id`, `date`),
  CONSTRAINT `fk_device_analytics_store` FOREIGN KEY (`store_id`) REFERENCES `stores` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 25. USER ACTIVITIES — Real-time activity tracking
-- =============================================================================
CREATE TABLE `user_activities` (
  `id`            BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id`       BIGINT       NULL,
  `store_id`      BIGINT       NULL,
  `activity_type` VARCHAR(30)  NOT NULL
                  COMMENT 'page_view | search | add_to_cart | checkout | purchase | review | follow_store | share',
  `ip_address`    VARCHAR(39)  NULL,
  `user_agent`    TEXT         NULL,
  `device_type`   VARCHAR(20)  NULL,
  `page_url`      TEXT         NULL,
  `referrer`      TEXT         NULL,
  `metadata`      JSON         NULL,
  `created_at`    DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

  INDEX `activities_store_type_idx` (`store_id`, `activity_type`),
  INDEX `activities_created_idx` (`created_at`),
  INDEX `activities_type_idx` (`activity_type`),
  CONSTRAINT `fk_activities_user`  FOREIGN KEY (`user_id`)  REFERENCES `users`  (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_activities_store` FOREIGN KEY (`store_id`) REFERENCES `stores` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 26. DAILY REPORTS — Seller dashboard summaries
-- =============================================================================
CREATE TABLE `daily_reports` (
  `id`               BIGINT AUTO_INCREMENT PRIMARY KEY,
  `store_id`         BIGINT       NOT NULL,
  `date`             DATE         NOT NULL,
  `total_revenue`    DECIMAL(15,2) NOT NULL DEFAULT 0.00,
  `total_orders`     INT          NOT NULL DEFAULT 0,
  `total_products_sold` INT      NOT NULL DEFAULT 0,
  `new_customers_count` INT      NOT NULL DEFAULT 0,
  `total_visitors`   INT          NOT NULL DEFAULT 0,
  `top_product_id`   INT          NULL,
  `top_product_name` VARCHAR(150) NULL,
  `top_product_sales` INT         NOT NULL DEFAULT 0,
  `conversion_rate`  DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  `revenue_growth`   DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  `is_completed`     TINYINT(1)   NOT NULL DEFAULT 0,
  `generated_at`     DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

  UNIQUE KEY `daily_reports_store_date_unique` (`store_id`, `date`),
  CONSTRAINT `fk_daily_reports_store` FOREIGN KEY (`store_id`) REFERENCES `stores` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 27. NOTIFICATIONS — User notifications
-- =============================================================================
CREATE TABLE `notifications` (
  `id`                BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id`           BIGINT       NOT NULL,
  `notification_type` VARCHAR(20)  NOT NULL DEFAULT 'system'
                      COMMENT 'order | payment | chat | promo | system | follow | review | product',
  `priority`          VARCHAR(20)  NOT NULL DEFAULT 'medium'
                      COMMENT 'low | medium | high | urgent',
  `title`             VARCHAR(255) NOT NULL,
  `description`       TEXT         NULL,
  `action_url`        VARCHAR(500) NULL,
  `action_text`       VARCHAR(100) NULL,
  `icon`              VARCHAR(100) NULL,
  `image`             VARCHAR(100) NULL,
  `is_read`           TINYINT(1)   NOT NULL DEFAULT 0,
  `read_at`           DATETIME(6)  NULL,
  `is_archived`       TINYINT(1)   NOT NULL DEFAULT 0,
  `metadata`          JSON         NULL,
  `created_at`        DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at`        DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

  INDEX `notifications_user_read_idx` (`user_id`, `is_read`),
  INDEX `notifications_user_type_idx` (`user_id`, `notification_type`),
  INDEX `notifications_created_idx` (`created_at`),
  CONSTRAINT `fk_notifications_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 28. NOTIFICATION PREFERENCES — Per-user settings
-- =============================================================================
CREATE TABLE `notification_preferences` (
  `id`               BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id`          BIGINT       NOT NULL UNIQUE,
  `push_orders`      TINYINT(1)   NOT NULL DEFAULT 1,
  `push_payments`    TINYINT(1)   NOT NULL DEFAULT 1,
  `push_chat`        TINYINT(1)   NOT NULL DEFAULT 1,
  `push_promos`      TINYINT(1)   NOT NULL DEFAULT 1,
  `push_system`      TINYINT(1)   NOT NULL DEFAULT 1,
  `email_orders`     TINYINT(1)   NOT NULL DEFAULT 1,
  `email_payments`   TINYINT(1)   NOT NULL DEFAULT 1,
  `email_promos`     TINYINT(1)   NOT NULL DEFAULT 0,
  `email_digest`     TINYINT(1)   NOT NULL DEFAULT 0,
  `sms_orders`       TINYINT(1)   NOT NULL DEFAULT 0,
  `sms_payments`     TINYINT(1)   NOT NULL DEFAULT 1,
  `sms_otp`          TINYINT(1)   NOT NULL DEFAULT 1,
  `quiet_hours_start` TIME        NULL,
  `quiet_hours_end`   TIME        NULL,
  `updated_at`       DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

  CONSTRAINT `fk_notif_prefs_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 29. CONVERSATIONS — Chat between buyers & sellers
-- =============================================================================
CREATE TABLE `conversations` (
  `id`              BIGINT AUTO_INCREMENT PRIMARY KEY,
  `store_id`        BIGINT       NULL,
  `subject`         VARCHAR(255) NULL,
  `last_message`    TEXT         NULL,
  `last_message_at` DATETIME(6)  NULL,
  `last_sender_id`  BIGINT       NULL,
  `unread_count`    INT          NOT NULL DEFAULT 0,
  `is_active`       TINYINT(1)   NOT NULL DEFAULT 1,
  `created_at`      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at`      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

  INDEX `conversations_last_msg_idx` (`last_message_at`),
  CONSTRAINT `fk_conversations_store`   FOREIGN KEY (`store_id`)      REFERENCES `stores` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_conversations_sender`  FOREIGN KEY (`last_sender_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- Conversation participants (M2M)
CREATE TABLE `conversations_participants` (
  `id`              BIGINT AUTO_INCREMENT PRIMARY KEY,
  `conversation_id` BIGINT NOT NULL,
  `user_id`         BIGINT NOT NULL,
  UNIQUE KEY `conv_participants_unique` (`conversation_id`, `user_id`),
  CONSTRAINT `fk_conv_part_conv` FOREIGN KEY (`conversation_id`) REFERENCES `conversations` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_conv_part_user` FOREIGN KEY (`user_id`)         REFERENCES `users` (`id`)         ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 30. MESSAGES (CHATS) — Individual chat messages
-- =============================================================================
CREATE TABLE `chats` (
  `id`              BIGINT AUTO_INCREMENT PRIMARY KEY,
  `conversation_id` BIGINT       NOT NULL,
  `sender_id`       BIGINT       NULL,
  `receiver_id`     BIGINT       NULL,
  `message_type`    VARCHAR(20)  NOT NULL DEFAULT 'text'
                    COMMENT 'text | image | file | order | system',
  `content`         TEXT         NOT NULL,
  `attachment`      VARCHAR(100) NULL,
  `is_read`         TINYINT(1)   NOT NULL DEFAULT 0,
  `read_at`         DATETIME(6)  NULL,
  `ip_address`      VARCHAR(39)  NULL,
  `created_at`      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

  INDEX `chats_conversation_created_idx` (`conversation_id`, `created_at`),
  INDEX `chats_sender_receiver_read_idx` (`sender_id`, `receiver_id`, `is_read`),
  CONSTRAINT `fk_chats_conversation` FOREIGN KEY (`conversation_id`) REFERENCES `conversations` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_chats_sender`   FOREIGN KEY (`sender_id`)   REFERENCES `users` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_chats_receiver` FOREIGN KEY (`receiver_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 31. OCR DETECTION RESULTS — Camera-based product scanning
-- =============================================================================
CREATE TABLE `ocr_detection_results` (
  `id`                    BIGINT AUTO_INCREMENT PRIMARY KEY,
  `seller_id`             BIGINT       NOT NULL,
  `store_id`              BIGINT       NULL,
  `product_name`          VARCHAR(255) NULL COMMENT 'Product name extracted from OCR',
  `category_detected`     VARCHAR(100) NULL COMMENT 'Automatically detected category',
  `category_id`           INT          NULL,
  `ocr_text`              TEXT         NULL COMMENT 'Raw OCR text output',
  `freshness_percentage`  DECIMAL(5,2) NULL COMMENT '0.00 - 100.00',
  `eligibility_percentage` DECIMAL(5,2) NULL COMMENT 'Eligibility score 0.00 - 100.00',
  `confidence_score`      DECIMAL(5,2) NULL COMMENT 'OCR confidence score 0.00 - 100.00',
  `quality_score`         INT          NULL COMMENT '0-100',
  `product_status_hint`   VARCHAR(20)  NULL COMMENT 'fresh | normal | low | bad',
  `detection_image`       VARCHAR(100) NULL COMMENT 'Path to captured/detected image',
  `metadata`              JSON         NULL,
  `is_verified`           TINYINT(1)   NOT NULL DEFAULT 0,
  `detection_timestamp`   DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `created_at`            DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

  INDEX `ocr_seller_idx` (`seller_id`),
  INDEX `ocr_store_idx` (`store_id`),
  INDEX `ocr_timestamp_idx` (`detection_timestamp`),
  INDEX `ocr_confidence_idx` (`confidence_score`),
  CONSTRAINT `fk_ocr_seller` FOREIGN KEY (`seller_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_ocr_store`  FOREIGN KEY (`store_id`)  REFERENCES `stores` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 32. LOGIN HISTORY — Audit trail
-- =============================================================================
CREATE TABLE `login_history` (
  `id`              BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id`         BIGINT       NOT NULL,
  `login_time`      DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `ip_address`      VARCHAR(39)  NOT NULL,
  `device_info`     TEXT         NULL COMMENT 'User agent / device string',
  `device_type`     VARCHAR(20)  NULL COMMENT 'mobile | tablet | desktop',
  `location`        VARCHAR(255) NULL COMMENT 'Geo-location (if available)',
  `is_successful`   TINYINT(1)   NOT NULL DEFAULT 1,
  `failure_reason`  VARCHAR(255) NULL,

  INDEX `login_history_user_idx` (`user_id`),
  INDEX `login_history_time_idx` (`login_time`),
  INDEX `login_history_ip_idx` (`ip_address`),
  CONSTRAINT `fk_login_history_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 33. REALTIME ACTIVITY — Live dashboard feed
-- =============================================================================
CREATE TABLE `realtime_activity` (
  `id`          BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id`     BIGINT       NULL,
  `store_id`    BIGINT       NULL,
  `activity_type` VARCHAR(50) NOT NULL
                 COMMENT 'new_order | payment_received | product_added | review_submitted | new_follower | stock_low | order_shipped',
  `activity_description` TEXT NULL,
  `reference_id` BIGINT     NULL COMMENT 'ID of related entity (order_id, product_id, etc.)',
  `reference_type` VARCHAR(30) NULL COMMENT 'order | product | review | payment',
  `metadata`    JSON         NULL,
  `is_read`     TINYINT(1)   NOT NULL DEFAULT 0,
  `created_at`  DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

  INDEX `realtime_store_type_idx` (`store_id`, `activity_type`),
  INDEX `realtime_created_idx` (`created_at`),
  INDEX `realtime_unread_idx` (`store_id`, `is_read`),
  CONSTRAINT `fk_realtime_user`  FOREIGN KEY (`user_id`)  REFERENCES `users`  (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_realtime_store` FOREIGN KEY (`store_id`) REFERENCES `stores` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 34. QUALITY CHECKS — AI product quality analysis
-- =============================================================================
CREATE TABLE `quality_checks` (
  `id`               BIGINT AUTO_INCREMENT PRIMARY KEY,
  `product_id`       BIGINT       NOT NULL,
  `freshness_score`  INT          NULL COMMENT '0-100',
  `stock_status`     VARCHAR(100) NULL COMMENT 'sufficient | low | critical',
  `ai_result`        TEXT         NULL COMMENT 'Raw AI analysis result',
  `quality_status`   VARCHAR(20)  NOT NULL DEFAULT 'pending'
                     COMMENT 'pending | fresh | normal | warning | rejected',
  `checked_at`       DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `created_at`       DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

  INDEX `quality_checks_product_idx` (`product_id`),
  INDEX `quality_checks_status_idx` (`quality_status`),
  INDEX `quality_checks_checked_idx` (`checked_at`),
  CONSTRAINT `fk_quality_checks_product` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 35. SUPPORTS — Customer support tickets
-- =============================================================================
CREATE TABLE `supports` (
  `id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id`        BIGINT       NULL,
  `subject`        VARCHAR(255) NOT NULL,
  `message`        TEXT         NOT NULL,
  `support_status` VARCHAR(20)  NOT NULL DEFAULT 'open'
                   COMMENT 'open | closed | resolved',
  `priority`       VARCHAR(20)  NOT NULL DEFAULT 'normal'
                   COMMENT 'low | normal | high | urgent',
  `created_at`     DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at`     DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

  INDEX `supports_user_idx` (`user_id`),
  INDEX `supports_status_idx` (`support_status`),
  INDEX `supports_created_idx` (`created_at`),
  CONSTRAINT `fk_supports_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- 36. SUBSCRIPTIONS — Seller subscription plans
-- =============================================================================
CREATE TABLE `subscriptions` (
  `id`            BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id`       BIGINT       NULL,
  `store_id`      BIGINT       NULL,
  `package_name`  VARCHAR(100) NOT NULL COMMENT 'free | basic | premium | enterprise',
  `start_date`    DATE         NOT NULL,
  `end_date`      DATE         NOT NULL,
  `status`        VARCHAR(20)  NOT NULL DEFAULT 'active'
                  COMMENT 'active | expired | cancelled',
  `auto_renew`    TINYINT(1)   NOT NULL DEFAULT 0,
  `amount_paid`   DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  `payment_method` VARCHAR(50) NULL,
  `notes`         TEXT         NULL,
  `created_at`    DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at`    DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

  INDEX `subscriptions_user_idx` (`user_id`),
  INDEX `subscriptions_store_idx` (`store_id`),
  INDEX `subscriptions_status_idx` (`status`),
  INDEX `subscriptions_date_idx` (`end_date`),
  CONSTRAINT `fk_subscriptions_user`  FOREIGN KEY (`user_id`)  REFERENCES `users`  (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_subscriptions_store` FOREIGN KEY (`store_id`) REFERENCES `stores` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- =============================================================================
-- FOREIGN KEY RELATIONSHIP MAP
-- =============================================================================
-- Users (1) ──< OTPs
-- Users (1) ──< UserSessions
-- Users (1) ──< SocialAccounts
-- Users (1) ──< LoginAttempts
-- Users (1) ──< LoginHistory
-- Users (1) ──> Stores (OneToOne: seller profile)
-- Users (1) ──< StoreFollowers
-- Users (1) ──< Reviews
-- Users (1) ──< Favorites
-- Users (1) ──< Cart
-- Users (1) ──< Orders
-- Users (1) ──< Payments
-- Users (1) ──< UserActivities
-- Users (1) ──< Notifications
-- Users (1) ──< NotificationPreferences
-- Users (1) ──< Chats (sender/receiver)
-- Users (1) ──< OCR_DetectionResults (seller)
-- Users (1) ──< RealtimeActivity
--
-- Stores (1) ──< Products
-- Stores (1) ──< Orders
-- Stores (1) ──< StoreFollowers
-- Stores (1) ──< SalesAnalytics
-- Stores (1) ──< DeviceAnalytics
-- Stores (1) ──< UserActivities
-- Stores (1) ──< DailyReports
-- Stores (1) ──< Conversations
-- Stores (1) ──< OCR_DetectionResults
-- Stores (1) ──< RealtimeActivity
--
-- Categories (1) ──< Products
-- Products   (1) ──< OrderItems
-- Products   (1) ──< Reviews
-- Products   (1) ──< Favorites
-- Products   (1) ──< Cart
-- Products   (1) ──< ProductGallery
-- Products   (1) ──< QualityChecks
--
-- Orders     (1) ──< OrderItems
-- Orders     (1) ──< Payments
-- Orders     (1) ──< Deliveries
-- Payments   (1) ──< MidtransTransactions
-- Conversations (1) ──< Chats
-- Conversations (M) >── Participants (M2M)
--
-- Users     (1) ──< Supports
-- Users     (1) ──< Subscriptions
-- Stores    (1) ──< Subscriptions

-- =============================================================================
-- INDEX OPTIMIZATION RECOMMENDATIONS
-- =============================================================================
-- 1. Partitioning: For sales_analytics & user_activities, consider RANGE partitioning
--    by date/month on high-traffic installations.
--
-- 2. Covering indexes: The compound indexes (store_id + date, user_id + status)
--    already cover most common query patterns.
--
-- 3. Full-text search: For product_name and description searching, consider:
--    CREATE FULLTEXT INDEX ft_products_search ON products(product_name, description);
--
-- 4. JSON fields: Consider MariaDB 10.6+ virtual columns with indexes for
--    frequently-queried JSON paths (metadata->>"$.field").
--
-- 5. Archive strategy: For login_attempts and old user_activities > 90 days,
--    implement a scheduled archive to history tables.

-- =============================================================================
-- SAMPLE DATA — phpMyAdmin test inserts
-- =============================================================================

-- Sample store categories
INSERT INTO `store_categories` (`name`, `order`, `is_active`) VALUES
('Warung Makanan',    1, 1),
('Toko Kelontong',   2, 1),
('Buah & Sayur',     3, 1),
('Minuman Segar',    4, 1),
('Sembako',          5, 1),
('Kebutuhan Dapur',  6, 1);

-- Sample product categories
INSERT INTO `categories` (`category_name`, `order`, `is_active`) VALUES
('Beras & Sembako',   1, 1),
('Minyak & Bumbu',    2, 1),
('Minuman',           3, 1),
('Makanan Ringan',    4, 1),
('Buah-buahan',       5, 1),
('Sayur-mayur',       6, 1),
('Susu & Olahan',     7, 1),
('Roti & Kue',        8, 1),
('Perawatan Rumah',   9, 1),
('Produk Segar',     10, 1);

-- Sample users (password hash: "TestPass123!" for all test accounts)
-- PBKDF2 SHA256 hash generated by Django
INSERT INTO `users` (`id`, `password`, `last_login`, `is_superuser`, `username`, `first_name`, `last_name`,
                     `is_staff`, `is_active`, `date_joined`, `email`, `phone`, `full_name`, `role`,
                     `is_verified`, `address`, `bio`, `created_at`, `updated_at`) VALUES
(1, 'pbkdf2_sha256$720000$wJ5HSe7UwVx8$xnGkhj4O45vYwfTdI1nGJfO0JbIQqg/6V5CX3M2XdHE=', NULL, 0,
 'seller_adi', '', '', 0, 1, NOW(),
 'seller@warungio.com', '+6281234567890', 'Adi Pratama', 'seller', 1,
 'Jl. Merdeka No. 10, Jakarta Pusat', 'Penjual sayur dan buah segar',
 NOW(), NOW()),

(2, 'pbkdf2_sha256$720000$wJ5HSe7UwVx8$xnGkhj4O45vYwfTdI1nGJfO0JbIQqg/6V5CX3M2XdHE=', NULL, 0,
 'buyer_siti', '', '', 0, 1, NOW(),
 'buyer@warungio.com', '+6289876543210', 'Siti Rahayu', 'buyer', 1,
 'Jl. Sudirman No. 5, Jakarta Selatan', 'Ibu rumah tangga',
 NOW(), NOW()),

(3, 'pbkdf2_sha256$720000$wJ5HSe7UwVx8$xnGkhj4O45vYwfTdI1nGJfO0JbIQqg/6V5CX3M2XdHE=', NULL, 0,
 'admin_warungio', '', '', 1, 1, NOW(),
 'admin@warungio.com', '+6281122334455', 'Admin Warungio', 'admin', 1,
 'Jl. Thamrin No. 1, Jakarta', 'Administrator platform',
 NOW(), NOW()),

(4, 'pbkdf2_sha256$720000$wJ5HSe7UwVx8$xnGkhj4O45vYwfTdI1nGJfO0JbIQqg/6V5CX3M2XdHE=', NULL, 0,
 'seller_dewi', '', '', 0, 1, NOW(),
 'dewi.seller@warungio.com', '+6285647382910', 'Dewi Sartika', 'seller', 1,
 'Jl. Diponegoro No. 22, Bandung', 'Penjual sembako dan kebutuhan pokok',
 NOW(), NOW()),

(5, 'pbkdf2_sha256$720000$wJ5HSe7UwVx8$xnGkhj4O45vYwfTdI1nGJfO0JbIQqg/6V5CX3M2XdHE=', NULL, 0,
 'buyer_budi', '', '', 0, 1, NOW(),
 'budi@warungio.com', '+6281777888999', 'Budi Santoso', 'buyer', 1,
 'Jl. Anggrek No. 7, Jakarta Barat', 'Karyawan swasta',
 NOW(), NOW());

-- Sample stores
INSERT INTO `stores` (`id`, `user_id`, `store_name`, `slug`, `category`, `description`,
                      `address`, `city`, `province`, `status`, `follower_count`,
                      `product_count`, `rating_avg`, `total_sales`, `is_open`,
                      `created_at`) VALUES
(1, 1, 'Warung Segar Adi', 'warung-segar-adi', 'Buah & Sayur',
 'Menyediakan sayur dan buah segar langsung dari petani. Harga bersahabat!',
 'Jl. Merdeka No. 10', 'Jakarta Pusat', 'DKI Jakarta',
 'active', 25, 12, 4.50, 15000000.00, 1, NOW()),

(2, 4, 'Toko Sembako Dewi', 'toko-sembako-dewi', 'Sembako',
 'Toko sembako lengkap untuk kebutuhan rumah tangga sehari-hari.',
 'Jl. Diponegoro No. 22', 'Bandung', 'Jawa Barat',
 'active', 15, 8, 4.20, 8500000.00, 1, NOW());

-- Sample products
INSERT INTO `products` (`store_id`, `category_id`, `product_name`, `slug`, `description`,
                        `price`, `stock`, `unit`, `quality_score`, `product_status`,
                        `sold_count`, `rating_avg`, `review_count`, `is_active`, `is_featured`,
                        `created_at`) VALUES
(1, 1, 'Beras Premium 5kg',           'beras-premium-5kg',        'Beras kualitas premium pulen enak',          75000,  100, 'kg',  90, 'fresh',  45,  4.50, 12, 1, 1, NOW()),
(1, 2, 'Minyak Goreng 1L',            'minyak-goreng-1l',         'Minyak goreng sehat, dikemas higienis',      20000,  50,  'L',   85, 'fresh',  120, 4.30, 8,  1, 0, NOW()),
(1, 5, 'Apel Fuji 1kg',               'apel-fuji-1kg',            'Apel fuji segar manis, langsung dari Malang', 35000, 30,  'kg',  95, 'fresh',  30,  4.70, 5,  1, 1, NOW()),
(1, 6, 'Bayam Segar 1ikat',           'bayam-segar-1ikat',        'Bayam segar petik hari ini',                 5000,   80,  'ikat', 88, 'fresh',  200, 4.10, 15, 1, 0, NOW()),
(1, 3, 'Air Mineral 600ml',           'air-mineral-600ml',        'Air mineral murni dari sumber pegunungan',   3000,   200, 'botol', 98, 'fresh',  500, 4.80, 25, 1, 1, NOW()),
(2, 1, 'Gula Pasir 1kg',              'gula-pasir-1kg',           'Gula pasir putih bersih kualitas terbaik',   15000,  60,  'kg',  85, 'fresh',  85,  4.20, 6,  1, 0, NOW()),
(2, 2, 'Telur Ayam 1kg',              'telur-ayam-1kg',           'Telur ayam negeri segar',                    28000,  40,  'kg',  80, 'fresh',  65,  4.40, 9,  1, 1, NOW()),
(2, 3, 'Kopi Bubuk 250gr',            'kopi-bubuk-250gr',         'Kopi bubuk pilihan asli Indonesia',          25000,  25,  'pcs',  90, 'fresh',  40,  4.60, 7,  1, 0, NOW());

-- Sample orders
INSERT INTO `orders` (`user_id`, `store_id`, `order_number`, `subtotal`, `shipping_cost`,
                      `discount`, `total_price`, `payment_method`, `payment_status`,
                      `order_status`, `delivery_address`, `recipient_name`, `recipient_phone`,
                      `courier`, `created_at`) VALUES
(2, 1, 'WRG-ORD-0001', 110000.00, 10000.00, 0.00, 120000.00,
 'cod', 'paid', 'completed',
 'Jl. Sudirman No. 5, Jakarta Selatan', 'Siti Rahayu', '6289876543210',
 'GoSend', '2026-05-01 08:30:00'),

(5, 1, 'WRG-ORD-0002',  75000.00, 10000.00, 5000.00, 80000.00,
 'midtrans', 'paid', 'shipped',
 'Jl. Anggrek No. 7, Jakarta Barat', 'Budi Santoso', '6281777888999',
 'JNE', '2026-05-10 10:15:00'),

(2, 2, 'WRG-ORD-0003',  43000.00, 8000.00,  0.00,   51000.00,
 'gopay', 'paid', 'processed',
 'Jl. Sudirman No. 5, Jakarta Selatan', 'Siti Rahayu', '6289876543210',
 'GrabExpress', '2026-05-15 14:00:00');

-- Sample order items
INSERT INTO `order_items` (`order_id`, `product_id`, `product_name`, `qty`, `price`, `subtotal`) VALUES
(1, 1, 'Beras Premium 5kg',    1, 75000,  75000),
(1, 5, 'Air Mineral 600ml',    2, 3000,    6000),
(1, 4, 'Bayam Segar 1ikat',    3, 5000,   15000),
(2, 1, 'Beras Premium 5kg',    1, 75000,  75000),
(3, 6, 'Gula Pasir 1kg',       1, 15000,  15000),
(3, 7, 'Telur Ayam 1kg',       1, 28000,  28000);

-- Sample reviews
INSERT INTO `reviews` (`user_id`, `product_id`, `rating`, `comment`, `is_verified`, `created_at`) VALUES
(2, 1, 5, 'Berasnya pulen dan wangi. Sangat puas!',       1, '2026-05-03 09:00:00'),
(2, 4, 4, 'Bayam segar, cepat sampai. Recommended.',      1, '2026-05-03 09:05:00'),
(5, 1, 5, 'Kualitas beras terbaik, sudah langganan.',      1, '2026-05-12 11:00:00'),
(2, 6, 4, 'Gula pasir bersih, kemasan rapi.',             1, '2026-05-16 08:30:00'),
(2, 7, 5, 'Telur segar, tidak ada yang pecah. Terima kasih!', 1, '2026-05-16 08:35:00');

-- Sample payment methods
INSERT INTO `payment_methods` (`name`, `display_name`, `is_active`, `fee_percent`, `order`) VALUES
('credit_card',   'Kartu Kredit / Debit',   1, 2.90,   1),
('bank_transfer', 'Transfer Bank (BNI, BRI, Mandiri)', 1, 0.00, 2),
('gopay',         'GoPay',                 1, 0.00,   3),
('shopeepay',     'ShopeePay',             1, 0.00,   4),
('ovo',           'OVO',                   1, 0.00,   5),
('dana',          'DANA',                  1, 0.00,   6),
('qris',          'QRIS',                  1, 0.00,   7),
('cod',           'Bayar di Tempat (COD)', 1, 0.00,   8);

-- Sample sales analytics
INSERT INTO `sales_analytics` (`store_id`, `date`, `total_sales`, `total_orders`, `total_products_sold`,
                               `average_order_value`, `new_customers`, `returning_customers`,
                               `created_at`) VALUES
(1, '2026-05-01', 120000.00, 3, 6, 40000.00, 2, 1, NOW()),
(1, '2026-05-02',  85000.00, 2, 4, 42500.00, 1, 1, NOW()),
(1, '2026-05-03', 150000.00, 4, 8, 37500.00, 3, 1, NOW()),
(2, '2026-05-01',  51000.00, 1, 2, 51000.00, 1, 0, NOW());

-- Sample quality checks
INSERT INTO `quality_checks` (`product_id`, `freshness_score`, `stock_status`, `ai_result`, `quality_status`, `checked_at`) VALUES
(1, 92, 'sufficient', 'Produk segar, kualitas premium. Skor kesegaran: 92/100', 'fresh', '2026-05-20 06:00:00'),
(2, 85, 'sufficient', 'Minyak goreng dalam kondisi baik. Skor: 85/100', 'fresh', '2026-05-20 06:05:00'),
(3, 88, 'sufficient', 'Apel fuji segar, tidak ada cacat. Skor: 88/100', 'fresh', '2026-05-20 06:10:00'),
(4, 78, 'low', 'Bayam masih segar, sedikit layu. Skor: 78/100', 'normal', '2026-05-20 06:15:00');

-- Sample support tickets
INSERT INTO `supports` (`user_id`, `subject`, `message`, `support_status`, `priority`, `created_at`) VALUES
(2, 'Pesanan tidak kunjung sampai', 'Halo, pesanan saya #WRG-ORD-0001 sudah 3 hari belum sampai. Mohon bantuannya.', 'open', 'high', '2026-05-04 09:00:00'),
(5, 'Cara mengubah alamat pengiriman', 'Bagaimana cara mengubah alamat pengiriman setelah checkout?', 'closed', 'normal', '2026-05-11 14:30:00'),
(1, 'Pertanyaan tentang fitur toko', 'Apakah ada fitur untuk menjadwalkan buka tutup toko?', 'resolved', 'low', '2026-05-15 10:00:00');

-- Sample subscriptions
INSERT INTO `subscriptions` (`user_id`, `store_id`, `package_name`, `start_date`, `end_date`, `status`, `auto_renew`, `amount_paid`, `created_at`) VALUES
(1, 1, 'basic', '2026-05-01', '2026-07-31', 'active', 1, 99000.00, '2026-05-01 00:00:00'),
(4, 2, 'free', '2026-05-01', '2026-07-31', 'active', 0, 0.00, '2026-05-01 00:00:00');

-- Sample notifications
INSERT INTO `notifications` (`user_id`, `notification_type`, `priority`, `title`, `description`,
                             `action_url`, `is_read`, `created_at`) VALUES
(1, 'order', 'high',    'Pesanan Baru!',     'Ada pesanan baru dari Siti Rahayu',    '/orders/1',     0, '2026-05-01 08:30:00'),
(2, 'order', 'medium',  'Pesanan Dikirim!',  'Pesanan Anda sedang dalam perjalanan', '/orders/1',     0, '2026-05-01 10:00:00'),
(1, 'review', 'low',    'Ulasan Baru',       'Siti Rahayu memberi ulasan 5★',        '/products/1',   0, '2026-05-03 09:00:00'),
(1, 'system', 'low',    'Selamat Datang!',   'Selamat bergabung di Warungio!',       '/seller/dashboard', 1, NOW());

-- Sample OCR detection results
INSERT INTO `ocr_detection_results` (`seller_id`, `store_id`, `product_name`, `category_detected`,
                                     `ocr_text`, `freshness_percentage`, `eligibility_percentage`,
                                     `confidence_score`, `quality_score`, `detection_timestamp`) VALUES
(1, 1, 'Apel Fuji Merah',        'Buah-buahan',
 'APEL FUJI MERAH\nGrade: Premium\nBerat: 1kg\nHarga: Rp35.000',
  92.50, 88.00, 95.30, 90, '2026-05-20 08:00:00'),

(1, 1, 'Bayam Hijau Segar',      'Sayur-mayur',
 'BAYAM HIJAU\nSegar Petik Hari Ini\nBerat: 1 ikat\nHarga: Rp5.000',
  85.00, 95.00, 91.50, 85, '2026-05-20 08:05:00'),

(4, 2, 'Telur Ayam Negeri Fresh', 'Susu & Olahan',
 'TELUR AYAM NEGERI\nFresh - 1kg\nHarga: Rp28.000\nSimpan di kulkas',
  78.50, 90.00, 89.70, 80, '2026-05-20 09:00:00');

-- Sample login history
INSERT INTO `login_history` (`user_id`, `login_time`, `ip_address`, `device_info`, `device_type`, `is_successful`) VALUES
(1, '2026-05-20 07:00:00', '192.168.1.10',  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120',    'desktop', 1),
(2, '2026-05-20 08:00:00', '192.168.1.20',  'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0) Mobile/15E148',  'mobile',  1),
(4, '2026-05-20 08:30:00', '192.168.1.30',  'Mozilla/5.0 (Android 14) Chrome/120 Mobile',               'mobile',  1),
(5, '2026-05-20 09:00:00', '192.168.1.40',  'Mozilla/5.0 (iPad; CPU OS 17_0) Mobile/15E148',             'tablet',  1);

-- Sample realtime activity feed
INSERT INTO `realtime_activity` (`user_id`, `store_id`, `activity_type`, `activity_description`,
                                `reference_id`, `reference_type`, `created_at`) VALUES
(2, 1, 'new_order',        'Siti Rahayu memesan Beras Premium 5kg',         1,  'order',   '2026-05-01 08:30:00'),
(2, 1, 'payment_received', 'Pembayaran untuk Pesanan #WRG-ORD-0001 diterima',1, 'order',   '2026-05-01 08:35:00'),
(1, 1, 'product_added',    'Produk baru: Apel Fuji 1kg ditambahkan',        3,  'product', '2026-05-05 10:00:00'),
(2, 1, 'review_submitted', 'Ulasan baru 5★ untuk Beras Premium 5kg',        1,  'review',  '2026-05-03 09:00:00'),
(5, 1, 'new_follower',     'Budi Santoso mengikuti toko Anda',              NULL, NULL,     '2026-05-10 10:00:00');

-- =============================================================================
-- DATABASE VERIFICATION WORKFLOW (phpMyAdmin)
-- =============================================================================
--
-- 1. Open http://localhost/phpmyadmin → select `warungio_db`
-- 2. Run these verification queries in the SQL tab:
--
--    -- Total tables
--    SELECT COUNT(*) AS total_tables FROM information_schema.tables
--    WHERE table_schema = 'warungio_db';
--
--    -- Row counts per table
--    SELECT table_name, table_rows FROM information_schema.tables
--    WHERE table_schema = 'warungio_db'
--    ORDER BY table_name;
--
--    -- Verify foreign key relationships
--    SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
--    FROM information_schema.KEY_COLUMN_USAGE
--    WHERE TABLE_SCHEMA = 'warungio_db' AND REFERENCED_TABLE_NAME IS NOT NULL;
--
--    -- Verify sample data
--    SELECT 'users' AS tbl, COUNT(*) AS cnt FROM users
--    UNION ALL SELECT 'stores', COUNT(*) FROM stores
--    UNION ALL SELECT 'products', COUNT(*) FROM products
--    UNION ALL SELECT 'orders', COUNT(*) FROM orders
--    UNION ALL SELECT 'reviews', COUNT(*) FROM reviews
--    UNION ALL SELECT 'ocr_detection_results', COUNT(*) FROM ocr_detection_results;
--
--    -- Test CRUD: Insert a favorite
--    INSERT INTO favorites (user_id, product_id) VALUES (2, 3);
--    SELECT * FROM favorites WHERE user_id = 2;
--    DELETE FROM favorites WHERE user_id = 2 AND product_id = 3;
--
--    -- Check analytics aggregation
--    SELECT store_id, SUM(total_sales) AS total_revenue, SUM(total_orders) AS total_orders
--    FROM sales_analytics GROUP BY store_id;

-- =============================================================================
-- REALTIME ANALYTICS CONNECTION RECOMMENDATIONS
-- =============================================================================
--
-- 1. Django Channels WebSocket:
--    - Connect to ws://localhost:8000/ws/dashboard/{store_id}/
--    - Uses channels_redis as backend (fallback to InMemoryChannelLayer for dev)
--    - Real-time events pushed via `realtime_activity` table + AsyncConsumer
--
-- 2. Polling fallback (no WebSocket):
--    - Poll GET /api/analytics/realtime/ every 10 seconds
--    - Returns: today_sales, today_orders, today_visitors, pending_orders
--
-- 3. Dashboard analytics endpoints:
--    - GET /api/analytics/dashboard/         → Full seller dashboard summary
--    - GET /api/analytics/sales/              → Sales history (paginated)
--    - GET /api/analytics/sales/trend/        → Chart data (labels, daily_sales, daily_orders)
--    - GET /api/analytics/devices/            → Device breakdown (mobile/tablet/desktop)
--    - GET /api/analytics/activities/         → Recent user activities
--    - GET /api/analytics/realtime/           → Today's snapshot (for dashboard widgets)
--
-- 4. Database triggers (optional, for denormalized counters):
--    DELIMITER //
--    CREATE TRIGGER after_order_insert AFTER INSERT ON orders
--    FOR EACH ROW
--    BEGIN
--      UPDATE stores SET total_sales = total_sales + NEW.total_price
--      WHERE id = NEW.store_id;
--    END//
--    DELIMITER ;

-- =============================================================================
-- PHP MYADMIN IMPORT INSTRUCTIONS
-- =============================================================================
--
-- Option A: Import via phpMyAdmin UI
--   1. Open http://localhost/phpmyadmin
--   2. Click "New" → Database name: `warungio_db`
--   3. Charset: `utf8mb4_general_ci`
--   4. Click "Create"
--   5. Select the `warungio_db` database
--   6. Click "Import" tab
--   7. Choose this .sql file
--   8. Click "Go"
--
-- Option B: Import via MySQL CLI (XAMPP)
--   mysql -u root -p warungio_db < database/warungio_full_schema.sql
--
-- Option C: Import via Django (already done — Django manages schema automatically)
--   cd django_backend && python manage.py migrate
--   python manage.py loaddata sample_data.json  (if using fixtures)
--
-- The Django backend auto-creates all tables via `python manage.py migrate`.
-- This SQL file is for manual/phpMyAdmin database inspection and verification.
-- =============================================================================
