/**
 * Warungio API Client
 * Convenience methods for all Django REST API endpoints.
 * Relies on window.WarungioAuth for authenticated requests.
 */
(function () {
  'use strict';

  const auth = window.WarungioAuth;
  if (!auth) {
    console.error('Warungio API: auth.js must be loaded first.');
    return;
  }

  const WarungioAPI = {
    // =========================================================================
    // AUTH
    // =========================================================================
    async register(data) {
      return auth.api('/auth/register/', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    async login(email, password, loginEntry) {
      var body = { email, password };
      if (loginEntry) body.login_entry = loginEntry;
      return auth.api('/auth/login/', {
        method: 'POST',
        body: JSON.stringify(body),
      });
    },

    async requestOTP(email, purpose = 'registration') {
      return auth.api('/auth/otp/request/', {
        method: 'POST',
        body: JSON.stringify({ email, purpose }),
      });
    },

    async verifyOTP(email, otpCode, purpose = 'registration') {
      return auth.api('/auth/otp/verify/', {
        method: 'POST',
        body: JSON.stringify({ email, otp_code: otpCode, purpose }),
      });
    },

    async forgotPassword(email) {
      return auth.api('/auth/forgot-password/', {
        method: 'POST',
        body: JSON.stringify({ email }),
      });
    },

    async resetPassword(email, otpCode, newPassword) {
      return auth.api('/auth/reset-password/', {
        method: 'POST',
        body: JSON.stringify({
          email,
          otp_code: otpCode,
          new_password: newPassword,
          new_password2: newPassword,
        }),
      });
    },

    async checkAuth() {
      return auth.api('/auth/check-auth/');
    },

    async updateProfile(data) {
      return auth.api('/auth/profile/', {
        method: 'PATCH',
        body: JSON.stringify(data),
      });
    },

    async changePassword(data) {
      return auth.api('/auth/change-password/', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    async uploadProfilePhoto(file) {
      const fd = new FormData();
      fd.append('profile_photo', file);
      return auth.apiUpload('/auth/profile/', fd, 'PATCH');
    },

    // =========================================================================
    // SOCIAL AUTHENTICATION
    // =========================================================================
    async socialLogin(provider, data) {
      return auth.api(`/auth/social/${provider}/`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    async checkAvailability(data) {
      // Check if email or phone is already registered (no side effects)
      return auth.api('/auth/check-availability/', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    async getSocialAuthConfig(provider) {
      return auth.api(`/auth/social/config/${provider}/`);
    },

    async getSocialAccounts() {
      return auth.api('/auth/social/accounts/');
    },

    async unlinkSocialAccount(provider) {
      return auth.api('/auth/social/accounts/', {
        method: 'DELETE',
        body: JSON.stringify({ provider }),
      });
    },

    // =========================================================================
    // STORES
    // =========================================================================
    async getStores(params = {}) {
      const qs = new URLSearchParams(params).toString();
      return auth.api(`/stores/${qs ? '?' + qs : ''}`);
    },

    async getStore(id) {
      return auth.api(`/stores/${id}/`);
    },

    async createStore(data) {
      return auth.api('/stores/create/', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    async getMyStore() {
      return auth.api('/stores/my-store/');
    },

    async updateStore(id, data) {
      // MyStoreView handles PATCH at /stores/my-store/
      return auth.api('/stores/my-store/', {
        method: 'PATCH',
        body: JSON.stringify(data),
      });
    },

    async followStore(id) {
      return auth.api(`/stores/${id}/follow/`, { method: 'POST' });
    },

    // Follow/unfollow toggle: POST once to follow, POST again to unfollow (backend toggle)
    async unfollowStore(id) {
      return auth.api(`/stores/${id}/follow/`, { method: 'POST' });
    },

    // =========================================================================
    // PRODUCTS
    // =========================================================================
    async getProducts(params = {}) {
      const qs = new URLSearchParams(params).toString();
      return auth.api(`/products/${qs ? '?' + qs : ''}`);
    },

    async getProduct(id) {
      return auth.api(`/products/${id}/`);
    },

    async createProduct(data) {
      return auth.api('/products/create/', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    async updateProduct(id, data) {
      return auth.api(`/products/${id}/manage/`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      });
    },

    async deleteProduct(id) {
      return auth.api(`/products/${id}/manage/`, { method: 'DELETE' });
    },

    async getProductReviews(productId) {
      return auth.api(`/products/${productId}/reviews/`);
    },

    // My Products (seller)
    async getMyProducts(params = {}) {
      const qs = new URLSearchParams(params).toString();
      return auth.api(`/products/my-products/${qs ? '?' + qs : ''}`);
    },

    // Product categories
    async getCategories() {
      return auth.api('/products/categories/');
    },

    // Product favorite toggle
    async getProductFavorite(productId) {
      return auth.api(`/products/${productId}/favorite/`);
    },
    async toggleFavorite(productId) {
      return auth.api(`/products/${productId}/favorite/`, { method: 'POST' });
    },

    // Seller Store Reviews
    async getStoreReviews(params = {}) {
      const qs = new URLSearchParams(params).toString();
      return auth.api(`/products/store-reviews/${qs ? '?' + qs : ''}`);
    },
    async replyToReview(reviewId, data) {
      return auth.api(`/products/reviews/${reviewId}/`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      });
    },

    // Seller Promos
    async getSellerPromos() {
      return auth.api('/products/seller-promos/');
    },
    async createSellerPromo(data) {
      return auth.api('/products/seller-promos/', { method: 'POST', body: JSON.stringify(data) });
    },
    async updateSellerPromo(id, data) {
      return auth.api(`/products/seller-promos/${id}/`, { method: 'PATCH', body: JSON.stringify(data) });
    },
    async deleteSellerPromo(id) {
      return auth.api(`/products/seller-promos/${id}/`, { method: 'DELETE' });
    },

    // Low Stock Products
    async getLowStockProducts(threshold = 5) {
      return auth.api(`/products/low-stock/?threshold=${threshold}`);
    },

    // Recently Viewed
    async recordProductView(productId) {
      return auth.api('/products/recently-viewed/', { method: 'POST', body: JSON.stringify({ product_id: productId }) });
    },
    async getRecentlyViewed() {
      return auth.api('/products/recently-viewed/');
    },

    // Check Voucher
    async checkVoucher(code, total = 0) {
      return auth.api('/products/check-voucher/', { method: 'POST', body: JSON.stringify({ code, total }) });
    },

    // Search Suggestions
    async searchSuggestions(q) {
      return auth.api(`/products/search-suggestions/?q=${encodeURIComponent(q || '')}`);
    },

    // =========================================================================
    // ORDERS
    // =========================================================================
    async getOrders(params = {}) {
      const qs = new URLSearchParams(params).toString();
      return auth.api(`/orders/my-orders/${qs ? '?' + qs : ''}`);
    },

    async getSellerOrders(params = {}) {
      const qs = new URLSearchParams(params).toString();
      return auth.api(`/orders/seller/${qs ? '?' + qs : ''}`);
    },

    async getOrder(id) {
      return auth.api(`/orders/${id}/`);
    },

    async getDeliveryTracking(orderId) {
      return auth.api(`/orders/${orderId}/tracking/`);
    },

    async createOrder(data) {
      return auth.api('/orders/create/', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    async updateOrderStatus(orderId, status, courier = '', trackingNumber = '', cancelReason = '', cancelReasonText = '', extraFields = {}) {
      var body = { status: status };
      if (courier) body.courier = courier;
      if (trackingNumber) body.tracking_number = trackingNumber;
      if (cancelReason) body.cancel_reason = cancelReason;
      if (cancelReasonText) body.cancel_reason_text = cancelReasonText;
      // Hyperlocal delivery extra fields
      if (extraFields.driver_name) body.driver_name = extraFields.driver_name;
      if (extraFields.driver_phone) body.driver_phone = extraFields.driver_phone;
      if (extraFields.pickup_code) body.pickup_code = extraFields.pickup_code;
      if (extraFields.estimated_time) body.estimated_time = extraFields.estimated_time;
      if (extraFields.estimated_pickup) body.estimated_pickup = extraFields.estimated_pickup;
      return auth.api(`/orders/${orderId}/status/`, {
        method: 'POST',
        body: JSON.stringify(body),
      });
    },

    async cancelOrder(orderId, reason = '', reasonText = '') {
      const body = {};
      if (reason) body.reason = reason;
      if (reasonText) body.reason_text = reasonText;
      return auth.api(`/orders/${orderId}/cancel/`, {
        method: 'POST',
        body: JSON.stringify(body),
      });
    },

    // =========================================================================
    // CART
    // =========================================================================
    async getCart() {
      return auth.api('/orders/cart/');
    },

    async getCartCount() {
      return auth.api('/orders/cart/count/');
    },

    async addToCart(data) {
      return auth.api('/orders/cart/', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    async updateCartItem(itemId, data) {
      return auth.api(`/orders/cart/${itemId}/`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      });
    },

    async removeCartItem(itemId) {
      return auth.api(`/orders/cart/${itemId}/`, { method: 'DELETE' });
    },

    async clearCart() {
      return auth.api('/orders/cart/clear/', { method: 'DELETE' });
    },

    async checkout(data) {
      return auth.api('/orders/create/', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    async checkVoucher(code, total = 0) {
      return auth.api('/products/check-voucher/', {
        method: 'POST',
        body: JSON.stringify({ code, total }),
      });
    },

    // =========================================================================
    // PAYMENTS
    // =========================================================================
    async getShippingMethods() {
      return auth.api('/orders/shipping-methods/');
    },

    async getPaymentMethods() {
      return auth.api('/payments/methods/');
    },

    async getPaymentConfig() {
      return auth.api('/payments/config/');
    },

    async createSnapTransaction(orderId, paymentMethod = 'bank_transfer', bank = null) {
      const data = { order_id: orderId, payment_method: paymentMethod };
      if (bank) data.bank = bank;
      return auth.api('/payments/create-snap/', {
        method: 'POST',
        body: JSON.stringify(data),
      });
    },

    async getPaymentStatus(orderId) {
      return auth.api(`/payments/status/${orderId}/`);
    },

    // =========================================================================
    // ANALYTICS (Seller Dashboard)
    // =========================================================================
    async getDashboardSummary(period = 'month') {
      return auth.api(`/analytics/dashboard/?period=${period}`);
    },

    async getSalesTrend(period = '30') {
      return auth.api(`/analytics/sales/trend/?period=${period}`);
    },

    async getDeviceAnalytics(period = '30') {
      return auth.api(`/analytics/devices/?period=${period}`);
    },

    async getSellerReport(params = {}) {
      const qs = new URLSearchParams(params).toString();
      return auth.api(`/analytics/seller-report/${qs ? '?' + qs : ''}`);
    },

    async getRealtimeAnalytics() {
      return auth.api('/analytics/realtime/');
    },

    async getSalesAnalytics() {
      return auth.api('/analytics/sales/');
    },

    async getDailyReports() {
      return auth.api('/analytics/reports/');
    },

    // =========================================================================
    // NOTIFICATIONS
    // =========================================================================
    async getNotifications(params = {}) {
      const qs = new URLSearchParams(params).toString();
      return auth.api(`/notifications/${qs ? '?' + qs : ''}`);
    },

    async markNotificationRead(id) {
      return auth.api(`/notifications/${id}/read/`, { method: 'POST' });
    },

    async markAllNotificationsRead() {
      return auth.api('/notifications/read-all/', { method: 'POST' });
    },

    // =========================================================================
    // CHAT
    // =========================================================================
    async getConversations() {
      return auth.api('/chat/conversations/');
    },

    async startConversation(receiverId, message = '') {
      return auth.api('/chat/conversations/start/', {
        method: 'POST',
        body: JSON.stringify({ receiver_id: receiverId, message }),
      });
    },

    async getConversationMessages(conversationId) {
      return auth.api(`/chat/conversations/${conversationId}/messages/`);
    },

    async sendMessage(conversationId, receiverId, content) {
      return auth.api('/chat/messages/send/', {
        method: 'POST',
        body: JSON.stringify({ conversation: conversationId, receiver: receiverId, content }),
      });
    },

    async getChatUnreadCount() {
      return auth.api('/chat/unread-count/');
    },

    // =========================================================================
    // FINANCE / KEUANGAN
    // =========================================================================
    async getFinanceSummary(days = 30) {
      return auth.api(`/payments/finance/summary/?days=${days}`);
    },
    async getFinanceTransactions(params = {}) {
      const qs = new URLSearchParams(params).toString();
      return auth.api(`/payments/finance/transactions/${qs ? '?' + qs : ''}`);
    },
    async getBankAccounts() {
      return auth.api('/payments/finance/bank-accounts/');
    },
    async createBankAccount(data) {
      return auth.api('/payments/finance/bank-accounts/', { method: 'POST', body: JSON.stringify(data) });
    },
    async updateBankAccount(id, data) {
      return auth.api(`/payments/finance/bank-accounts/${id}/`, { method: 'PATCH', body: JSON.stringify(data) });
    },
    async deleteBankAccount(id) {
      return auth.api(`/payments/finance/bank-accounts/${id}/`, { method: 'DELETE' });
    },
    async submitWithdrawal(data) {
      return auth.api('/payments/finance/withdraw/', { method: 'POST', body: JSON.stringify(data) });
    },

    // =========================================================================
    // SMART SCAN AI CAMERA
    // =========================================================================
    async getSmartScanConfig() {
      // Static config — no dedicated backend endpoint needed
      return Promise.resolve({
        enabled: true,
        modes: ['barcode', 'ocr', 'computer_vision', 'manual']
      });
    },

    async createSmartScanSession(deviceType = 'desktop') {
      return auth.api('/inventory/ai-scan/start/', {
        method: 'POST',
        body: JSON.stringify({ scan_mode: deviceType === 'mobile' ? 'single' : 'multi' })
      });
    },

    async endSmartScanSession(sessionId) {
      return auth.api(`/inventory/ai-scan/${sessionId}/cancel/`, { method: 'POST' });
    },

    async processSmartScan(imageData, productId, scanType, options = {}) {
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
      }).then(function (result) {
        result.mode = result.mode || scanType;
        result.product_type = result.product?.product_name || 'Produk';
        return result;
      });
    },

    async getQualityChecks(productId) {
      return auth.api(`/products/${productId}/quality-checks/`);
    },

    // =========================================================================
    // WALLET (database-driven)
    // =========================================================================
    async getWalletBalance() {
      return auth.api('/payments/wallet/balance/');
    },
    async getWalletTransactions(params = {}) {
      const qs = new URLSearchParams(params).toString();
      return auth.api(`/payments/wallet/transactions/${qs ? '?' + qs : ''}`);
    },
    async topUpWallet(amount) {
      return auth.api('/payments/wallet/topup/', { method: 'POST', body: JSON.stringify({ amount }) });
    },

    // =========================================================================
    // REFUNDS
    // =========================================================================
    async getMyRefunds(params = {}) {
      const qs = new URLSearchParams(params).toString();
      return auth.api(`/refunds/my-refunds/${qs ? '?' + qs : ''}`);
    },
    async getRefund(id) {
      return auth.api(`/refunds/${id}/`);
    },
    async createRefund(data) {
      return auth.api('/refunds/create/', { method: 'POST', body: JSON.stringify(data) });
    },
    async cancelRefund(id) {
      return auth.api(`/refunds/${id}/cancel/`, { method: 'POST' });
    },
    async getStoreRefunds(params = {}) {
      const qs = new URLSearchParams(params).toString();
      return auth.api(`/refunds/store-refunds/${qs ? '?' + qs : ''}`);
    },
    async sellerRefundAction(id, data) {
      return auth.api(`/refunds/${id}/seller-action/`, { method: 'POST', body: JSON.stringify(data) });
    },

    // =========================================================================
    // NOTIFICATIONS
    // =========================================================================
    async getNotifications(params = {}) {
      const qs = new URLSearchParams(params).toString();
      return auth.api(`/notifications/${qs ? '?' + qs : ''}`);
    },
    async markNotificationRead(id) {
      return auth.api('/notifications/mark-read/', { method: 'POST', body: JSON.stringify({ notification_ids: [id] }) });
    },
    async markAllNotificationsRead() {
      return auth.api('/notifications/mark-read/', { method: 'POST', body: JSON.stringify({ mark_all: true }) });
    },

    // =========================================================================
    // UTILITY
    // =========================================================================
    formatCurrency(value) {
      if (value === null || value === undefined) return 'Rp 0';
      return 'Rp ' + Number(value).toLocaleString('id-ID');
    },
  };

  window.WarungioAPI = WarungioAPI;
})();

