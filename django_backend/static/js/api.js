/**
 * Warungio API Client
 *
 * Architecture:
 *   - All methods delegate to auth.api() which handles JWT auth, token refresh,
 *     and CSRF protection.
 *   - No mock layer — every call goes to the real Django REST API.
 *   - All endpoints return promises that resolve to parsed JSON data.
 *
 * Usage:
 *   window.WarungioAPI.getProducts(...)
 *       .then(data => { ... })
 *       .catch(err => { ... });
 */
(function () {
  'use strict';

  var auth = window.WarungioAuth;

  // ──────────────────────────────────────────────────────────────────────────
  //  REAL API  — all methods delegate to auth.api() (works with real backend)
  // ──────────────────────────────────────────────────────────────────────────

  var RealAPI = {};

  // ---- Auth ----
  RealAPI.register = function (data) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/auth/register/', { method: 'POST', body: JSON.stringify(data) });
  };
  RealAPI.login = function (email, password) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/auth/login/', { method: 'POST', body: JSON.stringify({ email: email, password: password }) });
  };
  RealAPI.requestOTP = function (email, purpose) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/auth/otp/request/', { method: 'POST', body: JSON.stringify({ email: email, purpose: purpose || 'registration' }) });
  };
  RealAPI.verifyOTP = function (email, otpCode, purpose) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/auth/otp/verify/', { method: 'POST', body: JSON.stringify({ email: email, otp_code: otpCode, purpose: purpose || 'registration' }) });
  };
  RealAPI.forgotPassword = function (email) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/auth/forgot-password/', { method: 'POST', body: JSON.stringify({ email: email }) });
  };
  RealAPI.resetPassword = function (email, otpCode, newPassword) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/auth/reset-password/', { method: 'POST', body: JSON.stringify({ email: email, otp_code: otpCode, new_password: newPassword, new_password2: newPassword }) });
  };
  RealAPI.checkAuth = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/auth/check-auth/');
  };
  RealAPI.updateProfile = function (data) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/auth/profile/', { method: 'PATCH', body: JSON.stringify(data) });
  };
  RealAPI.changePassword = function (data) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/auth/change-password/', { method: 'POST', body: JSON.stringify(data) });
  };
  RealAPI.uploadProfilePhoto = function (file) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    var fd = new FormData();
    fd.append('profile_photo', file);
    return auth.apiUpload('/auth/profile/', fd, 'PATCH');
  };

  // ---- Social Auth ----
  RealAPI.socialLogin = function (provider, data) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/auth/social/' + provider + '/', { method: 'POST', body: JSON.stringify(data) });
  };
  RealAPI.getSocialAuthConfig = function (provider) {
    if (!auth) return Promise.resolve({});
    return auth.api('/auth/social/config/' + provider + '/').catch(function () { return {}; });
  };
  RealAPI.getSocialAccounts = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/auth/social/accounts/');
  };
  RealAPI.unlinkSocialAccount = function (provider) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/auth/social/accounts/', { method: 'DELETE', body: JSON.stringify({ provider: provider }) });
  };

  // ---- Stores ----
  RealAPI.getStores = function (params) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    var qs = params ? new URLSearchParams(params).toString() : '';
    return auth.api('/stores/' + (qs ? '?' + qs : ''));
  };
  RealAPI.getStore = function (id) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/stores/' + id + '/');
  };
  RealAPI.createStore = function (data) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/stores/create/', { method: 'POST', body: JSON.stringify(data) });
  };
  RealAPI.getMyStore = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/stores/my-store/');
  };
  RealAPI.updateStore = function (id, data) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/stores/my-store/', { method: 'PATCH', body: JSON.stringify(data) });
  };
  RealAPI.followStore = function (id) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/stores/' + id + '/follow/', { method: 'POST' });
  };
  RealAPI.unfollowStore = function (id) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/stores/' + id + '/follow/', { method: 'POST' });
  };
  RealAPI.uploadStoreLogo = function (file) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    var fd = new FormData();
    fd.append('store_logo', file);
    return auth.apiUpload('/stores/my-store/', fd, 'PATCH');
  };
  RealAPI.uploadStoreBanner = function (file) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    var fd = new FormData();
    fd.append('store_banner', file);
    return auth.apiUpload('/stores/my-store/', fd, 'PATCH');
  };
  RealAPI.removeStoreLogo = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/stores/my-store/remove-image/', { method: 'POST', body: JSON.stringify({ image_type: 'logo' }) });
  };
  RealAPI.removeStoreBanner = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/stores/my-store/remove-image/', { method: 'POST', body: JSON.stringify({ image_type: 'banner' }) });
  };

  // ---- Products ----
  RealAPI.getProducts = function (params) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    var qs = params ? new URLSearchParams(params).toString() : '';
    return auth.api('/products/' + (qs ? '?' + qs : ''));
  };
  RealAPI.getMyProducts = function (params) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    var qs = params ? new URLSearchParams(params).toString() : '';
    return auth.api('/products/my-products/' + (qs ? '?' + qs : ''));
  };
  RealAPI.getCategories = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/products/categories/');
  };
  RealAPI.getProduct = function (id) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/products/' + id + '/');
  };
  RealAPI.createProduct = function (data) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/products/create/', { method: 'POST', body: JSON.stringify(data) });
  };
  RealAPI.updateProduct = function (id, data) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/products/' + id + '/manage/', { method: 'PATCH', body: JSON.stringify(data) });
  };
  RealAPI.deleteProduct = function (id) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/products/' + id + '/manage/', { method: 'DELETE' });
  };
  RealAPI.getProductReviews = function (productId) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/products/' + productId + '/reviews/');
  };
  RealAPI.getProductFavorite = function (productId) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/products/' + productId + '/favorite/');
  };
  RealAPI.toggleFavorite = function (productId) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/products/' + productId + '/favorite/', { method: 'POST' });
  };
  RealAPI.getStoreReviews = function (params) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    var qs = params ? new URLSearchParams(params).toString() : '';
    return auth.api('/products/store-reviews/' + (qs ? '?' + qs : ''));
  };
  RealAPI.getSellerPromos = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/products/seller-promos/');
  };
  RealAPI.createSellerPromo = function (data) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/products/seller-promos/', { method: 'POST', body: JSON.stringify(data) });
  };
  RealAPI.updateSellerPromo = function (id, data) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/products/seller-promos/' + id + '/', { method: 'PATCH', body: JSON.stringify(data) });
  };
  RealAPI.deleteSellerPromo = function (id) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/products/seller-promos/' + id + '/', { method: 'DELETE' });
  };

  // ---- Cart / Checkout ----
  RealAPI.getCart = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/orders/cart/');
  };
  RealAPI.getCartCount = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/orders/cart/count/');
  };
  RealAPI.addToCart = function (data) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/orders/cart/', { method: 'POST', body: JSON.stringify(data) });
  };
  RealAPI.updateCartItem = function (itemId, data) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/orders/cart/' + itemId + '/', { method: 'PATCH', body: JSON.stringify(data) });
  };
  RealAPI.removeCartItem = function (itemId) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/orders/cart/' + itemId + '/', { method: 'DELETE' });
  };
  RealAPI.clearCart = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/orders/cart/clear/', { method: 'DELETE' });
  };
  RealAPI.checkout = function (data) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/orders/create/', { method: 'POST', body: JSON.stringify(data) });
  };
  RealAPI.checkVoucher = function (code, total) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/products/check-voucher/', { method: 'POST', body: JSON.stringify({ code: code, total: total }) });
  };

  // ---- Orders ----
  RealAPI.getOrders = function (params) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    var qs = params ? new URLSearchParams(params).toString() : '';
    return auth.api('/orders/my-orders/' + (qs ? '?' + qs : ''));
  };
  RealAPI.getSellerOrders = function (params) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    var qs = params ? new URLSearchParams(params).toString() : '';
    return auth.api('/orders/seller/' + (qs ? '?' + qs : ''));
  };
  RealAPI.getOrder = function (id) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/orders/' + id + '/');
  };
  RealAPI.getDeliveryTracking = function (orderId) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/orders/' + orderId + '/tracking/');
  };
  RealAPI.createOrder = function (data) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/orders/create/', { method: 'POST', body: JSON.stringify(data) });
  };
  RealAPI.updateOrderStatus = function (orderId, status, courier, trackingNumber, cancelReason, cancelReasonText, extraFields) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    extraFields = extraFields || {};
    var body = { status: status };
    if (courier) body.courier = courier;
    if (trackingNumber) body.tracking_number = trackingNumber;
    if (cancelReason) body.cancel_reason = cancelReason;
    if (cancelReasonText) body.cancel_reason_text = cancelReasonText;
    if (extraFields.driver_name) body.driver_name = extraFields.driver_name;
    if (extraFields.driver_phone) body.driver_phone = extraFields.driver_phone;
    if (extraFields.pickup_code) body.pickup_code = extraFields.pickup_code;
    if (extraFields.estimated_time) body.estimated_time = extraFields.estimated_time;
    if (extraFields.estimated_pickup) body.estimated_pickup = extraFields.estimated_pickup;
    return auth.api('/orders/' + orderId + '/status/', { method: 'POST', body: JSON.stringify(body) });
  };
  RealAPI.cancelOrder = function (orderId, reason, reasonText) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    var body = {};
    if (reason) body.reason = reason;
    if (reasonText) body.reason_text = reasonText;
    return auth.api('/orders/' + orderId + '/cancel/', { method: 'POST', body: JSON.stringify(body) });
  };

  // ---- Payments ----
  RealAPI.getShippingMethods = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/orders/shipping-methods/');
  };
  RealAPI.getPaymentMethods = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/payments/methods/');
  };
  RealAPI.getPaymentConfig = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/payments/config/');
  };
  RealAPI.createSnapTransaction = function (orderId, paymentMethod, bank) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    var data = { order_id: orderId, payment_method: paymentMethod || 'bank_transfer' };
    if (bank) data.bank = bank;
    return auth.api('/payments/create-snap/', { method: 'POST', body: JSON.stringify(data) });
  };
  RealAPI.getPaymentStatus = function (orderId) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/payments/status/' + orderId + '/');
  };
  RealAPI.topUpWallet = function (amount) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/payments/wallet/topup/', { method: 'POST', body: JSON.stringify({ amount: amount }) });
  };
  RealAPI.getWalletBalance = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/payments/wallet/balance/');
  };
  RealAPI.getWalletTransactions = function (params) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    var qs = params ? new URLSearchParams(params).toString() : '';
    return auth.api('/payments/wallet/transactions/' + (qs ? '?' + qs : ''));
  };

  // ---- Finance (withdrawal, bank accounts) ----
  RealAPI.getFinanceSummary = function (days) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/payments/finance/summary/');
  };
  RealAPI.getFinanceTransactions = function (params) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    var qs = params ? new URLSearchParams(params).toString() : '';
    return auth.api('/payments/finance/transactions/' + (qs ? '?' + qs : ''));
  };
  RealAPI.getBankAccounts = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/payments/finance/bank-accounts/');
  };
  RealAPI.createBankAccount = function (data) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/payments/finance/bank-accounts/', { method: 'POST', body: JSON.stringify(data) });
  };
  RealAPI.updateBankAccount = function (id, data) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/payments/finance/bank-accounts/' + id + '/', { method: 'PATCH', body: JSON.stringify(data) });
  };
  RealAPI.deleteBankAccount = function (id) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/payments/finance/bank-accounts/' + id + '/', { method: 'DELETE' });
  };
  RealAPI.submitWithdrawal = function (data) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/payments/finance/withdraw/', { method: 'POST', body: JSON.stringify(data) });
  };

  // ---- Analytics ----
  RealAPI.getDashboardSummary = function (period) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/analytics/dashboard/?period=' + (period || 'month'));
  };
  RealAPI.getSalesTrend = function (period) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/analytics/sales/trend/?period=' + (period || '30'));
  };
  RealAPI.getDeviceAnalytics = function (period) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/analytics/devices/?period=' + (period || '30'));
  };
  RealAPI.getSellerReport = function (params) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    var qs = params ? new URLSearchParams(params).toString() : '';
    return auth.api('/analytics/seller-report/' + (qs ? '?' + qs : ''));
  };
  RealAPI.getRealtimeAnalytics = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/analytics/realtime/');
  };
  RealAPI.getSalesAnalytics = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/analytics/sales/');
  };
  RealAPI.getDailyReports = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/analytics/reports/');
  };

  // ---- Smart Scan AI (client-side camera operations, no server state) ----
  RealAPI.getSmartScanConfig = function () {
    // Browser capability check — no server dependency
    var hasCamera = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    return Promise.resolve({
      enabled: hasCamera,
      modes: ['barcode', 'ocr', 'computer_vision', 'manual'],
      supported_devices: ['mobile', 'tablet', 'desktop'],
    });
  };
  RealAPI.createSmartScanSession = function (deviceType) {
    return Promise.resolve({
      session_id: 'smartscan-session-' + Math.random().toString(36).substr(2, 9),
      device_type: deviceType || 'desktop',
      created_at: new Date().toISOString(),
    });
  };
  RealAPI.endSmartScanSession = function (sessionId) {
    return Promise.resolve({
      message: 'Sesi Smart Scan berakhir.',
      session_id: sessionId,
    });
  };
  RealAPI.processSmartScan = function (imageData, productId, scanType, options) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    options = options || {};
    return auth.api('/products/smart-scan/', {
      method: 'POST',
      body: JSON.stringify({
        product_id: Number(productId),
        scan_type: scanType,
        options: {
          barcode: options.barcode,
          bpom_number: options.bpom_number,
          expiration_date: options.expiration_date,
        },
      }),
    });
  };
  RealAPI.getQualityChecks = function (productId) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/products/' + productId + '/quality-checks/');
  };

  // ---- Notifications ----
  RealAPI.getNotifications = function (params) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    var qs = params ? new URLSearchParams(params).toString() : '';
    return auth.api('/notifications/' + (qs ? '?' + qs : ''));
  };
  RealAPI.markNotificationRead = function (id) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/notifications/mark-read/', { method: 'POST', body: JSON.stringify({ notification_ids: [id] }) });
  };
  RealAPI.markAllNotificationsRead = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/notifications/mark-read/', { method: 'POST', body: JSON.stringify({ mark_all: true }) });
  };
  RealAPI.deleteNotification = function (id) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/notifications/' + id + '/delete/', { method: 'DELETE' });
  };

  // ---- Chat ----
  RealAPI.getConversations = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/chat/conversations/');
  };
  RealAPI.getConversationMessages = function (conversationId) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/chat/conversations/' + conversationId + '/messages/');
  };
  RealAPI.sendMessage = function (data) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/chat/messages/send/', { method: 'POST', body: JSON.stringify(data) });
  };
  RealAPI.startConversation = function (receiverId, message) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/chat/conversations/start/', { method: 'POST', body: JSON.stringify({ receiver_id: receiverId, message: message || '' }) });
  };
  RealAPI.getUnreadChatCount = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/chat/unread-count/');
  };

  // ---- Favorites ----
  RealAPI.getFollowedStores = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/stores/my-followed/');
  };
  RealAPI.checkFollowStatus = function (storeId) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/stores/' + storeId + '/follow/');
  };

  // ---- Recently Viewed ----
  RealAPI.recordProductView = function (productId) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/products/recently-viewed/', { method: 'POST', body: JSON.stringify({ product_id: productId }) });
  };
  RealAPI.getRecentlyViewed = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/products/recently-viewed/');
  };

  // ---- Search ----
  RealAPI.searchSuggestions = function (q) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/products/search-suggestions/?q=' + encodeURIComponent(q || ''));
  };
  RealAPI.getSearchHistory = function () {
    try {
      var history = JSON.parse(localStorage.getItem('warungio_search_history') || '[]');
      return Promise.resolve({ count: history.length, results: history });
    } catch (e) {
      return Promise.resolve({ count: 0, results: [] });
    }
  };
  RealAPI.saveSearchHistory = function (query) {
    try {
      var history = JSON.parse(localStorage.getItem('warungio_search_history') || '[]');
      history = history.filter(function (h) { return h.query.toLowerCase() !== query.toLowerCase(); });
      history.unshift({ query: query, timestamp: new Date().toISOString() });
      if (history.length > 10) history = history.slice(0, 10);
      localStorage.setItem('warungio_search_history', JSON.stringify(history));
      return Promise.resolve({ message: 'Tersimpan.', count: history.length });
    } catch (e) {
      return Promise.resolve({ message: 'Gagal menyimpan.', count: 0 });
    }
  };
  RealAPI.clearSearchHistory = function () {
    try {
      localStorage.removeItem('warungio_search_history');
      return Promise.resolve({ message: 'Riwayat pencarian dihapus.' });
    } catch (e) {
      return Promise.resolve({ message: 'Gagal menghapus.' });
    }
  };

  // ---- Refunds ----
  RealAPI.getMyRefunds = function (params) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    var qs = params ? new URLSearchParams(params).toString() : '';
    return auth.api('/refunds/my-refunds/' + (qs ? '?' + qs : ''));
  };
  RealAPI.getRefund = function (id) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/refunds/' + id + '/');
  };
  RealAPI.createRefund = function (data) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/refunds/create/', { method: 'POST', body: JSON.stringify(data) });
  };
  RealAPI.cancelRefund = function (id) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/refunds/' + id + '/cancel/', { method: 'POST' });
  };
  RealAPI.getStoreRefunds = function (params) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    var qs = params ? new URLSearchParams(params).toString() : '';
    return auth.api('/refunds/store-refunds/' + (qs ? '?' + qs : ''));
  };
  RealAPI.sellerRefundAction = function (id, data) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/refunds/' + id + '/seller-action/', { method: 'POST', body: JSON.stringify(data) });
  };
  RealAPI.getAdminRefunds = function (params) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    var qs = params ? new URLSearchParams(params).toString() : '';
    return auth.api('/refunds/admin/all/' + (qs ? '?' + qs : ''));
  };
  RealAPI.adminRefundAction = function (id, data) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/refunds/' + id + '/admin-action/', { method: 'POST', body: JSON.stringify(data) });
  };
  RealAPI.getRefundStats = function () {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/refunds/stats/');
  };

  // ---- Stock Alerts ----
  RealAPI.getLowStockProducts = function (threshold) {
    if (!auth) return Promise.reject({ error: 'WarungioAuth not loaded' });
    return auth.api('/products/low-stock/?threshold=' + (threshold || 5));
  };

  // ──────────────────────────────────────────────────────────────────────────
  //  EXPORT  — all real endpoints, no mock layer
  // ──────────────────────────────────────────────────────────────────────────

  window.WarungioAPI = {};

  // Copy all real methods
  Object.keys(RealAPI).forEach(function (k) {
    window.WarungioAPI[k] = RealAPI[k];
  });

  console.info('WarungioAPI [LIVE MODE] — proxying to backend');
})();
