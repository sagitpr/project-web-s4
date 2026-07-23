import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'app.dart';
import 'core/storage/secure_storage_service.dart';
import 'core/config/environment.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Google AdMob
  const env = String.fromEnvironment('APP_ENV', defaultValue: 'development');
  final appId = env == 'production'
      ? 'ca-app-pub-8639756788997808~7569872948'
      : 'ca-app-pub-3940256099942544~3347511713';
  await MobileAds.instance.initialize();
  debugPrint('AdMob initialized with app ID: $appId');

  // Set preferred orientations
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  // Initialize local storage
  final prefs = await SharedPreferences.getInstance();
  final secureStorage = SecureStorageService(prefs);

  runApp(
    ProviderScope(
      overrides: [
        environmentProvider.overrideWithValue(env),
        secureStorageServiceProvider.overrideWithValue(secureStorage),
      ],
      child: const WarungioApp(),
    ),
  );
}
