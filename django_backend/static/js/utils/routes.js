/**
 * Centralized route definitions for Warungio.
 * Single source of truth for URL paths used across the application.
 */
(function () {
  'use strict';

  var ROUTES = {
    LANDING: '/',
    LOGIN: '/auth/login/',
    LOGIN_SELLER: '/auth/login-seller/',
    REGISTER: '/auth/register/',
    REGISTER_MITRA: '/auth/register-mitra/',
    OTP: '/auth/otp/',
    BUYER_HOME: '/buyer/home/',
    BUYER_DASHBOARD: '/buyer/dashboard/',
    BUYER_ORDERS: '/buyer/orders/',
    BUYER_PRODUCTS: '/buyer/products/',
    BUYER_CART: '/buyer/cart/',
    BUYER_FAVORITES: '/buyer/favorites/',
    BUYER_PROMO: '/buyer/promo/',
    BUYER_WALLET: '/buyer/wallet/',
    BUYER_SETTINGS: '/buyer/settings/',
    BUYER_REVIEWS: '/buyer/reviews/',
    BUYER_PROFILE: '/buyer/profile/',
    BUYER_CHAT: '/buyer/chat/',
    BUYER_REFUNDS: '/buyer/refunds/',
    SELLER_DASHBOARD: '/seller/dashboard/',
    SELLER_PRODUCTS: '/seller/products/',
    SELLER_ORDERS: '/seller/orders/',
    SELLER_LAPORAN: '/seller/laporan/',
    SELLER_KEUANGAN: '/seller/keuangan/',
    SELLER_PENGATURAN: '/seller/pengaturan/',
    SELLER_PROMO: '/seller/promo-diskon/',
    SELLER_REVIEWS: '/seller/ulasan/',
    SELLER_SUPPLIER: '/seller/supplier/',
    SELLER_REFUNDS: '/seller/refunds/',
    ADMIN_DASHBOARD: '/admin/',
  };

  if (typeof window !== 'undefined') {
    window.WarungioRoutes = ROUTES;
  }
})();
