import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'app.dart';
import 'core/storage/secure_storage_service.dart';
import 'core/config/environment.dart'; // environmentProvider (shared singleton)

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Set preferred orientations
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  // Initialize local storage
  final prefs = await SharedPreferences.getInstance();
  final secureStorage = SecureStorageService(prefs);

  // Determine environment
  const env = String.fromEnvironment('APP_ENV', defaultValue: 'development');

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
