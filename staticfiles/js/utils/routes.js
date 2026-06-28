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
    landing: '/buyer/dashboard/',
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
    bantuan: '/bantuan/',
  };

  window.WarungioRoutes.redirectByRole = function (role) {
    if (role === 'seller') {
      window.location.href = WarungioRoutes.sellerDashboard;
    } else {
      window.location.href = WarungioRoutes.home;
    }
  };
})();
