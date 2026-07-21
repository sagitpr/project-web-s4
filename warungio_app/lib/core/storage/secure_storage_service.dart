import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Service for local storage of auth tokens and user data.
/// Uses SharedPreferences for simplicity. For production, consider
/// flutter_secure_storage for encrypted storage.
class SecureStorageService {
  final SharedPreferences _prefs;

  SecureStorageService(this._prefs);

  // ── Access Token ──

  Future<void> setAccessToken(String token) async {
    await _prefs.setString('access_token', token);
  }

  Future<String?> getAccessToken() async {
    return _prefs.getString('access_token');
  }

  Future<void> removeAccessToken() async {
    await _prefs.remove('access_token');
  }

  // ── Refresh Token ──

  Future<void> setRefreshToken(String token) async {
    await _prefs.setString('refresh_token', token);
  }

  Future<String?> getRefreshToken() async {
    return _prefs.getString('refresh_token');
  }

  Future<void> removeRefreshToken() async {
    await _prefs.remove('refresh_token');
  }

  // ── User Data ──

  Future<void> setUserData(Map<String, dynamic> data) async {
    await _prefs.setString('user_data', jsonEncode(data));
  }

  Future<Map<String, dynamic>?> getUserData() async {
    final json = _prefs.getString('user_data');
    if (json == null) return null;
    try {
      return jsonDecode(json) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  // ── User ID ──

  Future<void> setUserId(int id) async {
    await _prefs.setInt('user_id', id);
  }

  Future<int?> getUserId() async {
    return _prefs.getInt('user_id');
  }

  // ── Onboarding ──

  Future<void> setOnboardingCompleted() async {
    await _prefs.setBool('onboarding_completed', true);
  }

  Future<bool> isOnboardingCompleted() async {
    return _prefs.getBool('onboarding_completed') ?? false;
  }

  // ── Theme ──

  Future<void> setThemeMode(String mode) async {
    await _prefs.setString('theme_mode', mode);
  }

  Future<String?> getThemeMode() async {
    return _prefs.getString('theme_mode');
  }

  // ── Clear All ──

  Future<void> clearAll() async {
    await _prefs.remove('access_token');
    await _prefs.remove('refresh_token');
    await _prefs.remove('user_data');
    await _prefs.remove('user_id');
  }
}

/// Riverpod provider for SecureStorageService.
final secureStorageServiceProvider = Provider<SecureStorageService>((ref) {
  throw UnimplementedError(
    'SecureStorageService must be initialized in main.dart using '
    'SecureStorageService.init() provider override.',
  );
});

/// Provider that initializes SecureStorageService with SharedPreferences.
final secureStorageInitProvider = FutureProvider<SecureStorageService>((ref) async {
  final prefs = await SharedPreferences.getInstance();
  return SecureStorageService(prefs);
});
