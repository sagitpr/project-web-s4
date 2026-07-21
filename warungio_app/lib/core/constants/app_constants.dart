/// Application-wide constants
class AppConstants {
  AppConstants._();

  /// App metadata
  static const String appName = 'Warungio';
  static const String appVersion = '1.0.0';
  static const String packageName = 'com.warungio.app';

  /// Supported locales
  static const List<Locale> supportedLocales = [
    Locale('id', 'ID'),
    Locale('en', 'US'),
  ];

  /// Default locale
  static const Locale defaultLocale = Locale('id', 'ID');

  /// Page sizes
  static const int defaultPageSize = 20;
  static const int maxPageSize = 100;

  /// Timeouts
  static const int connectionTimeout = 30000; // 30 seconds
  static const int receiveTimeout = 30000;
  static const int sendTimeout = 30000;

  /// Cache durations
  static const int defaultCacheMinutes = 15;
  static const int productCacheMinutes = 5;
  static const int categoryCacheMinutes = 30;

  /// Storage keys
  static const String accessTokenKey = 'access_token';
  static const String refreshTokenKey = 'refresh_token';
  static const String userDataKey = 'user_data';
  static const String themeModeKey = 'theme_mode';
  static const String localeKey = 'locale';
}
