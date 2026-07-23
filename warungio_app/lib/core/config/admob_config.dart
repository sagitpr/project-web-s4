/// Google AdMob Configuration — Centralized Ad Unit IDs
/// 
/// All Ad Unit IDs are managed in one place for easy switching between
/// Development (Google Test Ads) and Production environments.
///
/// Usage:
///   AdMobConfig.bannerHome   → returns appropriate Ad Unit ID based on env
///
/// To switch to production, change environment from 'development' to 'production'.
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'environment.dart';

/// AdMob configuration holder
class AdMobConfig {
  /// Google AdMob App ID
  static const String appId = 'ca-app-pub-8639756788997808~7569872948';
  
  /// Test App ID (Google test ads)
  static const String testAppId = 'ca-app-pub-3940256099942544~3347511713';

  /// Production Ad Unit IDs
  static const _prod = _AdUnitIds(
    bannerHome: 'ca-app-pub-8639756788997808/6683452671',
    bannerProfile: 'ca-app-pub-8639756788997808/2925151001',
    bannerWishlist: 'ca-app-pub-8639756788997808/7794334302',
    nativeHome: 'ca-app-pub-8639756788997808/1076616786',
    nativeSearch: 'ca-app-pub-8639756788997808/1037354260',
    nativeProduct: 'ca-app-pub-8639756788997808/9602239994',
  );

  /// Test Ad Unit IDs (Google test ads — safe for development)
  static const _test = _AdUnitIds(
    bannerHome: 'ca-app-pub-3940256099942544/6300978111',
    bannerProfile: 'ca-app-pub-3940256099942544/6300978111',
    bannerWishlist: 'ca-app-pub-3940256099942544/6300978111',
    nativeHome: 'ca-app-pub-3940256099942544/2247696110',
    nativeSearch: 'ca-app-pub-3940256099942544/2247696110',
    nativeProduct: 'ca-app-pub-3940256099942544/2247696110',
  );

  final String environment;
  late final _AdUnitIds _ids;

  AdMobConfig({required this.environment}) {
    _ids = environment == 'production' ? _prod : _test;
  }

  /// Whether to use test ads (true for development/staging)
  bool get isTest => environment != 'production';

  /// Banner Home — displayed on home screen bottom
  String get bannerHome => _ids.bannerHome;

  /// Banner Profile — displayed on profile screen
  String get bannerProfile => _ids.bannerProfile;

  /// Banner Wishlist — displayed on wishlist/favorites screen
  String get bannerWishlist => _ids.bannerWishlist;

  /// Native Home — displayed in marketplace feed between products (every 8-12 items)
  String get nativeHome => _ids.nativeHome;

  /// Native Search — displayed in search results between items
  String get nativeSearch => _ids.nativeSearch;

  /// Native Product — displayed below product description / between similar products
  String get nativeProduct => _ids.nativeProduct;
}

/// Private Ad Unit ID container
class _AdUnitIds {
  final String bannerHome;
  final String bannerProfile;
  final String bannerWishlist;
  final String nativeHome;
  final String nativeSearch;
  final String nativeProduct;

  const _AdUnitIds({
    required this.bannerHome,
    required this.bannerProfile,
    required this.bannerWishlist,
    required this.nativeHome,
    required this.nativeSearch,
    required this.nativeProduct,
  });
}

/// Provider: AdMobConfig singleton
final admobConfigProvider = Provider<AdMobConfig>((ref) {
  final env = ref.watch(environmentProvider);
  return AdMobConfig(environment: env);
});
