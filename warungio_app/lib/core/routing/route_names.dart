/// Centralized route name and path constants for GoRouter.
class RouteNames {
  RouteNames._();

  /// Route paths (used in GoRouter `path` and redirect checks)
  static const String splash = '/splash';
  static const String onboarding = '/onboarding';
  static const String login = '/auth/login';
  static const String register = '/auth/register';
  static const String otpVerify = '/auth/otp';
  static const String forgotPassword = '/auth/forgot-password';
  static const String resetPassword = '/auth/reset-password';

  // Main tabs
  static const String home = '/';
  static const String marketplace = '/marketplace';
  static const String cart = '/cart';
  static const String orders = '/orders';
  static const String profile = '/profile';

  // Marketplace
  static const String categories = '/categories';
  static const String search = '/search';
  static const String productDetail = '/product/:id';
  static const String storeDetail = '/store/:id';

  // Orders
  static const String orderDetail = '/order/:id';

  // Checkout
  static const String checkout = '/checkout';
  static const String checkoutSuccess = '/checkout/success/:orderId';

  // Wallet
  static const String wallet = '/wallet';

  // Notifications
  static const String notifications = '/notifications';

  // Settings
  static const String settings = '/settings';
  static const String changePassword = '/settings/change-password';
  static const String editProfile = '/settings/edit-profile';
  static const String about = '/settings/about';

  // Seller
  static const String sellerDashboard = '/seller/dashboard';

  // Support
  static const String support = '/support';

  // Favorites
  static const String favorites = '/favorites';
}
