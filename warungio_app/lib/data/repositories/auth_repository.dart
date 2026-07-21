import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../datasources/auth_api.dart';
import '../models/auth_response_model.dart';
import '../models/user_model.dart';
import '../../core/storage/secure_storage_service.dart';
import '../../core/network/dio_client.dart'; // For ApiResponse type

/// Repository for authentication operations.
/// Acts as a single source of truth for auth state.
class AuthRepository {
  final AuthApi _authApi;
  final SecureStorageService _secureStorage;

  AuthRepository({
    required AuthApi authApi,
    required SecureStorageService secureStorage,
  })  : _authApi = authApi,
        _secureStorage = secureStorage;

  /// Attempt login and persist tokens on success.
  Future<LoginResponseModel> login({
    required String email,
    required String password,
    String? loginEntry,
  }) async {
    final response = await _authApi.login(
      email: email,
      password: password,
      loginEntry: loginEntry,
    );
    if (response.success && response.accessToken != null) {
      await _secureStorage.setAccessToken(response.accessToken!);
      if (response.refreshToken != null) {
        await _secureStorage.setRefreshToken(response.refreshToken!);
      }
      await _secureStorage.setUserData(response.user.toJson());
    }
    return response;
  }

  /// Register a new user.
  Future<RegisterResponseModel> register({
    required String email,
    required String password,
    required String fullName,
    String? phone,
    String? role,
    String? address,
  }) async {
    return _authApi.register(
      email: email,
      fullName: fullName,
      password: password,
      password2: password,
      phone: phone,
      role: role ?? 'buyer',
      address: address,
    );
  }

  /// Request OTP for email verification.
  Future<ApiResponse> requestOtp({
    required String email,
    String purpose = 'registration',
  }) async {
    return _authApi.requestOTP(email: email, purpose: purpose);
  }

  /// Verify OTP code.
  Future<OTPVerifyResponseModel> verifyOtp({
    required String email,
    required String otpCode,
    String purpose = 'registration',
  }) async {
    final response = await _authApi.verifyOTP(
      email: email,
      otpCode: otpCode,
      purpose: purpose,
    );
    if (response.success && response.accessToken != null) {
      await _secureStorage.setAccessToken(response.accessToken!);
      if (response.refreshToken != null) {
        await _secureStorage.setRefreshToken(response.refreshToken!);
      }
      if (response.user != null) {
        await _secureStorage.setUserData(response.user!.toJson());
      }
    }
    return response;
  }

  /// Refresh the access token.
  Future<String?> refreshToken() async {
    final storedToken = await _secureStorage.getRefreshToken();
    if (storedToken == null) return null;
    try {
      final response = await _authApi.refreshToken(storedToken);
      if (response.success && response.accessToken != null) {
        await _secureStorage.setAccessToken(response.accessToken!);
        return response.accessToken;
      }
    } catch (_) {
      await logout();
    }
    return null;
  }

  /// Logout and clear all stored credentials.
  Future<void> logout() async {
    try {
      final refreshToken = await _secureStorage.getRefreshToken();
      if (refreshToken != null) {
        await _authApi.logout(refreshToken);
      }
    } catch (_) {
      // Logout API may fail, still clear local storage
    }
    await _secureStorage.clearAll();
  }

  /// Check if user is currently authenticated.
  Future<bool> isAuthenticated() async {
    final token = await _secureStorage.getAccessToken();
    return token != null && token.isNotEmpty;
  }

  /// Get current user from local storage.
  Future<UserModel?> getCurrentUser() async {
    final data = await _secureStorage.getUserData();
    if (data == null) return null;
    return UserModel.fromJson(data);
  }

  /// Fetch latest user profile from server.
  Future<UserModel> fetchProfile() async {
    final user = await _authApi.getProfile();
    await _secureStorage.setUserData(user.toJson());
    return user;
  }

  /// Update user profile on server.
  Future<UserModel> updateProfile(Map<String, dynamic> data) async {
    final user = await _authApi.updateProfile(data);
    await _secureStorage.setUserData(user.toJson());
    return user;
  }

  /// Request password reset.
  Future<ApiResponse> requestPasswordReset({required String email}) async {
    return _authApi.forgotPassword(email);
  }

  /// Confirm password reset.
  Future<ApiResponse> confirmPasswordReset({
    required String email,
    required String otpCode,
    required String newPassword,
  }) async {
    return _authApi.resetPassword(
      email: email,
      otpCode: otpCode,
      newPassword: newPassword,
      newPassword2: newPassword,
    );
  }
}

/// Riverpod provider for AuthRepository.
final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final authApi = ref.watch(authApiProvider);
  final secureStorage = ref.watch(secureStorageServiceProvider);
  return AuthRepository(authApi: authApi, secureStorage: secureStorage);
});
