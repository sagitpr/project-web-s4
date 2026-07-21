/// API endpoint constants matching the Warungio Django backend.
class ApiConstants {
  ApiConstants._();

  /// Base URL - configured per environment.
  static const String baseUrlDev = 'http://localhost:8000';
  static const String baseUrlProd = 'https://api.warungio.com';

  /// API prefix.
  static const String apiPrefix = '/api';

  // ═════════════════════════════════════════════════════════════════════════
  // AUTHENTICATION (/api/auth/)
  // ═════════════════════════════════════════════════════════════════════════
  static const String register = '/auth/register/';
  static const String login = '/auth/login/';
  static const String logout = '/auth/logout/';
  static const String checkAuth = '/auth/check-auth/';
  static const String tokenRefresh = '/auth/token-refresh/';
  static const String profile = '/auth/profile/';
  static const String changePassword = '/auth/change-password/';
  static const String otpRequest = '/auth/otp/request/';
  static const String otpVerify = '/auth/otp/verify/';
  static const String otpResend = '/auth/otp/resend/';
  static const String forgotPassword = '/auth/forgot-password/';
  static const String resetPassword = '/auth/reset-password/';
  static const String checkAvailability = '/auth/check-availability/';
  static const String adminLogin = '/auth/admin-login/';

  // Social Auth
  static const String socialGoogle = '/auth/social/google/';
  static const String socialFacebook = '/auth/social/facebook/';
  static const String socialApple = '/auth/social/apple/';
  static const String socialAccounts = '/auth/social/accounts/';

  // ═════════════════════════════════════════════════════════════════════════
  // STORES (/api/stores/)
  // ═════════════════════════════════════════════════════════════════════════
  static const String stores = '/stores/';
  static const String storeCategories = '/stores/categories/';
  static const String myStore = '/stores/my-store/';
  static const String myStoreRemoveImage = '/stores/my-store/remove-image/';
  static const String createStore = '/stores/create/';
  static const String storeDetail = '/stores/{id}/'; // Replace {id}
  static const String storeDetailSlug = '/stores/slug/{slug}/'; // Replace {slug}
  static const String myFollowedStores = '/stores/my-followed/';
  static const String storeFollow = '/stores/{store_id}/follow/'; // Replace {store_id}
  static const String storeFollowers = '/stores/{store_id}/followers/'; // Replace {store_id}
  static const String storeProductsList = '/products/store/{store_id}/'; // Replace {store_id}

  // ═════════════════════════════════════════════════════════════════════════
  // PRODUCTS (/api/products/)
  // ═════════════════════════════════════════════════════════════════════════
  static const String categoryList = '/products/categories/';
  static const String products = '/products/';
  static const String featuredProducts = '/products/featured/';
  static const String createProduct = '/products/create/';
  static const String myProducts = '/products/my-products/';
  static const String productDetail = '/products/{id}/'; // Replace {id}
  static const String productManage = '/products/{id}/manage/'; // Replace {id}
  static const String productReviewsList = '/products/{product_id}/reviews/'; // Replace {product_id}
  static const String myReviews = '/products/reviews/mine/';
  static const String productFavorite =
      '/products/{product_id}/favorite/'; // Replace {product_id}
  static const String myFavorites = '/products/my-favorites/';
  static const String recentlyViewed = '/products/recently-viewed/';
  static const String promoList = '/products/promos/';
  static const String sellerPromos = '/products/seller-promos/';
  static const String searchSuggestions = '/products/search-suggestions/';
  static const String checkVoucher = '/products/check-voucher/';
  static const String storeReviews = '/products/store-reviews/';

  // ═════════════════════════════════════════════════════════════════════════
  // ORDERS (/api/orders/)
  // ═════════════════════════════════════════════════════════════════════════
  static const String cartList = '/orders/cart/';
  static const String cartCount = '/orders/cart/count/';
  static const String cartClear = '/orders/cart/clear/';
  static const String cartDetail = '/orders/cart/{id}/'; // Replace {id}
  static const String shippingMethods = '/orders/shipping-methods/';
  static const String orderCreate = '/orders/create/';
  static const String myOrders = '/orders/my-orders/';
  static const String orderHistory = '/orders/history/';
  static const String orderDetail = '/orders/{id}/'; // Replace {id}
  static const String sellerOrders = '/orders/seller/';
  static const String orderStatusUpdate = '/orders/{order_id}/status/'; // Replace {order_id}
  static const String orderCancel = '/orders/{order_id}/cancel/'; // Replace {order_id}
  static const String deliveryTracking = '/orders/{order_id}/tracking/'; // Replace {order_id}

  // ═════════════════════════════════════════════════════════════════════════
  // PAYMENTS (/api/payments/)
  // ═════════════════════════════════════════════════════════════════════════
  static const String paymentMethods = '/payments/methods/';
  static const String paymentConfig = '/payments/config/';
  static const String publicApiConfig = '/payments/config/public/';
  static const String createSnapTransaction = '/payments/create-snap/';
  static const String midtransNotification = '/payments/notification/';
  static const String paymentStatus = '/payments/status/{order_id}/'; // Replace {order_id}
  static const String paymentHistory = '/payments/history/';
  static const String walletTopUp = '/payments/wallet/topup/';
  static const String walletBalance = '/payments/wallet/balance/';
  static const String walletTransactions = '/payments/wallet/transactions/';
  static const String financeSummary = '/payments/finance/summary/';
  static const String financeTransactions = '/payments/finance/transactions/';
  static const String financeBankAccounts = '/payments/finance/bank-accounts/';
  static const String withdrawBalance = '/payments/finance/withdraw/';
  static const String merchantStatus = '/payments/merchant-status/';

  // ═════════════════════════════════════════════════════════════════════════
  // NOTIFICATIONS (/api/notifications/)
  // ═════════════════════════════════════════════════════════════════════════
  static const String notifications = '/notifications/';
  static const String notificationMarkRead = '/notifications/mark-read/';
  static const String notificationUnreadCount = '/notifications/unread-count/';
  static const String notificationPreferences = '/notifications/preferences/';
  static const String notificationCreate = '/notifications/create/';
  static const String notificationDelete = '/notifications/{id}/delete/'; // Replace {id}

  // ═════════════════════════════════════════════════════════════════════════
  // ANALYTICS (/api/analytics/)
  // ═════════════════════════════════════════════════════════════════════════
  static const String analyticsDashboard = '/analytics/dashboard/';
  static const String analyticsSales = '/analytics/sales/';
  static const String salesTrend = '/analytics/sales/trend/';
  static const String analyticsDevices = '/analytics/devices/';
  static const String userActivities = '/analytics/activities/';
  static const String dailyReports = '/analytics/reports/';
  static const String realtimeAnalytics = '/analytics/realtime/';
  static const String aiBusinessInsights = '/analytics/ai/insights/';
  static const String sellerReport = '/analytics/seller-report/';
  static const String reportExport = '/analytics/export/';

  // ═════════════════════════════════════════════════════════════════════════
  // AI SERVICES (/api/ai/)
  // ═════════════════════════════════════════════════════════════════════════
  static const String aiHealth = '/ai/health/';
  static const String aiRecommendations = '/ai/recommendations/';
  static const String aiSimilarProducts =
      '/ai/recommendations/similar/{product_id}/';
  static const String aiSmartSearch = '/ai/search/';
  static const String aiSearchSuggestions = '/ai/search/suggestions/';
  static const String aiProductVision = '/ai/vision/';
  static const String aiFreshnessDetection = '/ai/vision/freshness/';
  static const String aiProductDescription = '/ai/describe/';
  static const String aiReviewAnalysis = '/ai/reviews/analyze/';

  // ═════════════════════════════════════════════════════════════════════════
  // CHAT (/api/chat/)
  // ═════════════════════════════════════════════════════════════════════════
  static const String conversations = '/chat/conversations/';
  static const String conversationDetail = '/chat/conversations/{id}/';
  static const String conversationMessages = '/chat/conversations/{conversation_id}/messages/';
  static const String sendMessage = '/chat/messages/send/';
  static const String chatUnreadCount = '/chat/unread-count/';
  static const String startConversation = '/chat/conversations/start/';

  // ═════════════════════════════════════════════════════════════════════════
  // ENGAGEMENT (/api/engagement/)
  // ═════════════════════════════════════════════════════════════════════════
  static const String engagementProfile = '/engagement/profile/';
  static const String engagementProfileRefresh = '/engagement/profile/refresh/';
  static const String engagementEvents = '/engagement/events/';
  static const String engagementRecordEvent = '/engagement/events/record/';
  static const String engagementActivity = '/engagement/activity/';
  static const String engagementDevices = '/engagement/devices/';
  static const String engagementDeviceRegister = '/engagement/devices/register/';
  static const String engagementDeviceUnregister = '/engagement/devices/unregister/';
  static const String engagementNotifications = '/engagement/queue/';

  // ═════════════════════════════════════════════════════════════════════════
  // INVENTORY (/api/inventory/)
  // ═════════════════════════════════════════════════════════════════════════
  static const String inventoryMasterProducts = '/inventory/master-products/';
  static const String inventoryBarcodeLookup = '/inventory/barcode-lookup/';
  static const String inventoryBatches = '/inventory/batches/';
  static const String inventoryBatchDetail = '/inventory/batches/{id}/';
  static const String inventoryStockOut = '/inventory/stock-out/';

  // AI Scan
  static const String aiScanStart = '/inventory/ai-scan/start/';
  static const String aiScanSessions = '/inventory/ai-scan/sessions/';
  static const String aiScanDetail = '/inventory/ai-scan/{session_id}/';

  // ═════════════════════════════════════════════════════════════════════════
  // LOYALTY (/api/loyalty/)
  // ═════════════════════════════════════════════════════════════════════════
  static const String loyaltyPoints = '/loyalty/points/';
  static const String loyaltyAccount = '/loyalty/account/';
  static const String loyaltyTransactions = '/loyalty/transactions/';
  static const String loyaltyRewards = '/loyalty/rewards/';
  static const String loyaltyTiers = '/loyalty/tiers/';

  // ═════════════════════════════════════════════════════════════════════════
  // REFUNDS (/api/refunds/)
  // ═════════════════════════════════════════════════════════════════════════
  static const String refundCreate = '/refunds/create/';
  static const String myRefunds = '/refunds/my-refunds/';
  static const String refundDetail = '/refunds/{id}/';
  static const String storeRefunds = '/refunds/store-refunds/';
  static const String adminRefunds = '/refunds/admin/all/';

  // ═════════════════════════════════════════════════════════════════════════
  // REGIONS (/api/regions/)
  // ═════════════════════════════════════════════════════════════════════════
  static const String provinces = '/regions/provinces/';
  static const String regencies = '/regions/regencies/';
  static const String districts = '/regions/districts/';
  static const String villages = '/regions/villages/';
  static const String regionSearch = '/regions/search/';

  // ═════════════════════════════════════════════════════════════════════════
  // SUPPLIERS (/api/suppliers/)
  // ═════════════════════════════════════════════════════════════════════════
  static const String supplierCategories = '/suppliers/categories/';
  static const String suppliers = '/suppliers/';
  static const String supplierDetail = '/suppliers/{id}/';
  static const String supplierProducts = '/suppliers/{id}/products/';

  // ═════════════════════════════════════════════════════════════════════════
  // SUPPORT (/api/support/)
  // ═════════════════════════════════════════════════════════════════════════
  static const String helpCategories = '/support/categories/';
  static const String helpArticles = '/support/articles/';
  static const String faqs = '/support/faqs/';
  static const String banners = '/support/banners/';
  static const String supportSearch = '/support/search/';
  static const String supportTickets = '/support/tickets/';
  static const String supportAiChat = '/support/ai-chat/';

  // ═════════════════════════════════════════════════════════════════════════
  // SUBSCRIPTIONS (/api/subscriptions/)
  // ═════════════════════════════════════════════════════════════════════════
  static const String subscriptions = '/subscriptions/';
  static const String mySubscription = '/subscriptions/my/';

  // ═════════════════════════════════════════════════════════════════════════
  // MONITORING (/api/monitoring/)
  // ═════════════════════════════════════════════════════════════════════════
  static const String monitoringHealth = '/monitoring/health/';
  static const String monitoringDashboard = '/monitoring/dashboard/';
  static const String monitoringMetrics = '/monitoring/metrics/';
  static const String monitoringErrors = '/monitoring/errors/';

  // ═════════════════════════════════════════════════════════════════════════
  // AI INTELLIGENCE (/api/intelligence/)
  // ═════════════════════════════════════════════════════════════════════════
  static const String digitalTwin = '/intelligence/twin/';
  static const String marketplaceHealth = '/intelligence/marketplace/health/';
  static const String coachInsights = '/intelligence/coach/insights/';
  static const String demandPrediction = '/intelligence/predictions/demand/{product_id}/';
  static const String shoppingInsights = '/intelligence/shopping/insights/';

  // ═════════════════════════════════════════════════════════════════════════
  // JWT & HEALTH
  // ═════════════════════════════════════════════════════════════════════════
  static const String jwtObtain = '/token/';
  static const String jwtRefresh = '/token/refresh/';
  static const String jwtBlacklist = '/token/blacklist/';
  static const String health = '/health/';
}
