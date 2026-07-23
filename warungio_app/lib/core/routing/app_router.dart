import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'route_names.dart';
import '../../presentation/providers/auth_provider.dart';
import '../../presentation/screens/splash/splash_screen.dart';
import '../../presentation/screens/onboarding/onboarding_screen.dart';
import '../../presentation/screens/auth/login_screen.dart';
import '../../presentation/screens/auth/register_screen.dart';
import '../../presentation/screens/auth/otp_verify_screen.dart';
import '../../presentation/screens/home/home_screen.dart';
import '../../presentation/screens/marketplace/marketplace_screen.dart';
import '../../presentation/screens/marketplace/store_detail_screen.dart';
import '../../presentation/screens/cart/cart_screen.dart';
import '../../presentation/screens/orders/orders_screen.dart';
import '../../presentation/screens/orders/order_detail_screen.dart';
import '../../presentation/screens/profile/profile_screen.dart';
import '../../presentation/screens/profile/favorites_screen.dart';
import '../../presentation/screens/product/product_detail_screen.dart';
import '../../presentation/screens/search/search_screen.dart';
import '../../presentation/screens/categories/categories_screen.dart';
import '../../presentation/screens/checkout/checkout_screen.dart';
import '../../presentation/screens/checkout/checkout_success_screen.dart';
import '../../presentation/screens/wallet/wallet_screen.dart';
import '../../presentation/screens/notifications/notifications_screen.dart';
import '../../presentation/screens/settings/settings_screen.dart';
import '../../presentation/screens/settings/edit_profile_screen.dart';
import '../../presentation/screens/settings/change_password_screen.dart';
import '../../presentation/screens/settings/about_screen.dart';
import '../../presentation/screens/support/support_screen.dart';
import '../../presentation/screens/auth/forgot_password_screen.dart';
import '../../presentation/screens/auth/reset_password_screen.dart';
import '../../presentation/screens/seller/seller_dashboard_screen.dart';
import '../../presentation/widgets/main_shell.dart';

final _rootNavigatorKey = GlobalKey<NavigatorState>();
final _shellNavigatorKey = GlobalKey<NavigatorState>();

/// Builds the GoRouter with all app routes.
final appRouterProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authProvider);

  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: RouteNames.splash,
    debugLogDiagnostics: false,

    redirect: (context, state) {
      final isLoggedIn = authState.isAuthenticated;
      final isSeller = authState.isSeller;
      final location = state.matchedLocation;

      // Public routes — always accessible (no auth required)
      if (location == RouteNames.splash ||
          location == RouteNames.onboarding ||
          location.startsWith('/auth/')) {
        return null;
      }

      // Not logged in → redirect to login
      if (!isLoggedIn) {
        return RouteNames.login;
      }

      // Logged in seller at buyer home (/) → redirect to seller dashboard
      if (isLoggedIn && isSeller && location == RouteNames.home) {
        return RouteNames.sellerDashboard;
      }

      return null;
    },

    routes: [
      // ── Public Routes ──
      GoRoute(
        name: 'splash',
        path: RouteNames.splash,
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(
        name: 'onboarding',
        path: RouteNames.onboarding,
        builder: (context, state) => const OnboardingScreen(),
      ),
      GoRoute(
        name: 'login',
        path: RouteNames.login,
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        name: 'register',
        path: RouteNames.register,
        builder: (context, state) => const RegisterScreen(),
      ),
      GoRoute(
        name: 'otp-verify',
        path: RouteNames.otpVerify,
        builder: (context, state) => const OtpVerifyScreen(),
      ),
      GoRoute(
        name: 'forgot-password',
        path: RouteNames.forgotPassword,
        builder: (context, state) => const ForgotPasswordScreen(),
      ),
      GoRoute(
        name: 'reset-password',
        path: RouteNames.resetPassword,
        builder: (context, state) => const ResetPasswordScreen(),
      ),

      // ── Shell Routes (Bottom Nav) ──
      ShellRoute(
        navigatorKey: _shellNavigatorKey,
        builder: (context, state, child) => MainShell(child: child),
        routes: [
          GoRoute(
            name: 'home',
            path: RouteNames.home,
            builder: (context, state) => const HomeScreen(),
          ),
          GoRoute(
            name: 'marketplace',
            path: RouteNames.marketplace,
            builder: (context, state) => const MarketplaceScreen(),
          ),
          GoRoute(
            name: 'cart',
            path: RouteNames.cart,
            builder: (context, state) => const CartScreen(),
          ),
          GoRoute(
            name: 'orders',
            path: RouteNames.orders,
            builder: (context, state) => const OrdersScreen(),
          ),
          GoRoute(
            name: 'profile',
            path: RouteNames.profile,
            builder: (context, state) => const ProfileScreen(),
          ),
        ],
      ),

      // ── Full-Screen Routes ──
      GoRoute(
        name: 'product-detail',
        path: RouteNames.productDetail,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) {
          final id = int.tryParse(state.pathParameters['id'] ?? '');
          return ProductDetailScreen(productId: id);
        },
      ),
      GoRoute(
        name: 'store-detail',
        path: RouteNames.storeDetail,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) {
          final id = int.tryParse(state.pathParameters['id'] ?? '');
          return StoreDetailScreen(storeId: id ?? 0);
        },
      ),
      GoRoute(
        name: 'order-detail',
        path: RouteNames.orderDetail,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) {
          final id = int.tryParse(state.pathParameters['id'] ?? '');
          return OrderDetailScreen(orderId: id ?? 0);
        },
      ),
      GoRoute(
        name: 'search',
        path: RouteNames.search,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const SearchScreen(),
      ),
      GoRoute(
        name: 'categories',
        path: RouteNames.categories,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const CategoriesScreen(),
      ),
      GoRoute(
        name: 'checkout',
        path: RouteNames.checkout,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const CheckoutScreen(),
      ),
      GoRoute(
        name: 'checkout-success',
        path: RouteNames.checkoutSuccess,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) {
          final orderId = state.pathParameters['orderId'] ?? '0';
          return CheckoutSuccessScreen(orderId: orderId);
        },
      ),
      GoRoute(
        name: 'wallet',
        path: RouteNames.wallet,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const WalletScreen(),
      ),
      GoRoute(
        name: 'notifications',
        path: RouteNames.notifications,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const NotificationsScreen(),
      ),
      GoRoute(
        name: 'settings',
        path: RouteNames.settings,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const SettingsScreen(),
      ),
      GoRoute(
        name: 'change-password',
        path: RouteNames.changePassword,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const ChangePasswordScreen(),
      ),
      GoRoute(
        name: 'edit-profile',
        path: RouteNames.editProfile,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const EditProfileScreen(),
      ),
      GoRoute(
        name: 'seller-dashboard',
        path: RouteNames.sellerDashboard,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const SellerDashboardScreen(),
      ),
      GoRoute(
        name: 'support',
        path: RouteNames.support,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const SupportScreen(),
      ),
      GoRoute(
        name: 'about',
        path: RouteNames.about,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const AboutScreen(),
      ),
      GoRoute(
        name: 'favorites',
        path: RouteNames.favorites,
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const FavoritesScreen(),
      ),

    ],
  );
});

