/**
 * Warungio Django URL routes (absolute paths)
 */
(function () {
  'use strict';
  window.WarungioRoutes = {
    login: '/auth/login/',
    register: '/auth/register/',
    otp: '/auth/otp/',
    resetPassword: '/auth/reset-password/',
    registerMitra: '/auth/register-mitra/',
    home: '/home/',
    landing: '/buyer/home/',
    buyerHome: '/buyer/home/',
    buyerDashboard: '/buyer/dashboard/',
    sellerDashboard: '/seller/dashboard/',
    cart: '/buyer/cart/',
    checkout: '/buyer/checkout/',
    orders: '/buyer/orders/',
    orderDetail: '/buyer/order-detail/',
    orderSuccess: '/buyer/order-success/',
    profile: '/buyer/profile/',
    sellerProducts: '/seller/products/',
    sellerOrders: '/seller/orders/',
    sellerOrderDetail: '/seller/order-detail/',
    sellerLaporan: '/seller/laporan/',
    sellerKeuangan: '/seller/keuangan/',
    sellerPelanggan: '/seller/pelanggan/',
    sellerPengaturan: '/seller/pengaturan/',
    sellerPromoDiskon: '/seller/promo-diskon/',
    sellerUlasan: '/seller/ulasan/',
    bantuan: '/bantuan/',
    // New features
    followedStores: '/buyer/followed-stores/',
    recentlyViewed: '/buyer/recently-viewed/',
    stockAlerts: '/seller/stock-alerts/',
    // NEW dedicated pages (v2.0.0)
    products: '/products/',
    favorites: '/favorites/',
    promo: '/promo/',
    settings: '/settings/',
    buyerProducts: '/buyer/products/',
    buyerFavorites: '/buyer/favorites/',
    buyerPromo: '/buyer/promo/',
    buyerSettings: '/buyer/settings/',
  };

  window.WarungioRoutes.redirectByRole = function (role) {
    if (role === 'seller') {
      window.location.href = WarungioRoutes.sellerDashboard;
    } else {
      window.location.href = WarungioRoutes.buyerHome;
    }
  };
})();
