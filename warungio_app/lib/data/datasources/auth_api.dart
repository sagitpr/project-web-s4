import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/dio_client.dart';
import '../../core/constants/api_constants.dart';
import '../models/auth_response_model.dart';
import '../models/user_model.dart';

/// Provider for the AuthApi datasource.
final authApiProvider = Provider<AuthApi>((ref) {
  return AuthApi(ref.watch(apiClientProvider));
});

/// Authentication API datasource.
/// Communicates with the Warungio Django REST auth endpoints.
class AuthApi {
  final ApiClient _client;

  AuthApi(this._client);

  /// Register a new user.
  Future<RegisterResponseModel> register({
    required String email,
    required String fullName,
    required String password,
    required String password2,
    String? phone,
    String? address,
    String role = 'buyer',
  }) async {
    final response = await _client.post(
      ApiConstants.register,
      data: {
        'email': email,
        'full_name': fullName,
        'password': password,
        'password2': password2,
        if (phone != null) 'phone': phone,
        if (address != null) 'address': address,
        'role': role,
      },
    );
    return RegisterResponseModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Login with email and password.
  Future<LoginResponseModel> login({
    required String email,
    required String password,
    String? loginEntry,
  }) async {
    final response = await _client.post(
      ApiConstants.login,
      data: {
        'email': email,
        'password': password,
        if (loginEntry != null) 'login_entry': loginEntry,
      },
    );
    return LoginResponseModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Logout - blacklist refresh token.
  Future<ApiResponse> logout(String refreshToken) async {
    return _client.post(ApiConstants.logout, data: {
      'refresh': refreshToken,
    });
  }

  /// Get authenticated user profile.
  Future<UserModel> getProfile() async {
    final response = await _client.get(ApiConstants.profile);
    return UserModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Update user profile.
  Future<UserModel> updateProfile(Map<String, dynamic> data) async {
    final response = await _client.patch(ApiConstants.profile, data: data);
    return UserModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Check authentication status.
  Future<Map<String, dynamic>> checkAuth() async {
    final response = await _client.get(ApiConstants.checkAuth);
    return response.data as Map<String, dynamic>;
  }

  /// Refresh JWT access token.
  Future<TokenRefreshResponseModel> refreshToken(String refresh) async {
    final response = await _client.post(
      ApiConstants.tokenRefresh,
      data: {'refresh': refresh},
    );
    return TokenRefreshResponseModel.fromJson(
        response.data as Map<String, dynamic>);
  }

  /// Change password for authenticated user.
  Future<ApiResponse> changePassword({
    required String oldPassword,
    required String newPassword,
    required String newPassword2,
  }) async {
    return _client.post(ApiConstants.changePassword, data: {
      'old_password': oldPassword,
      'new_password': newPassword,
      'new_password2': newPassword2,
    });
  }

  /// Request OTP code for verification.
  Future<ApiResponse> requestOTP({
    required String email,
    String purpose = 'registration',
    String? phone,
  }) async {
    return _client.post(ApiConstants.otpRequest, data: {
      'email': email,
      'purpose': purpose,
      if (phone != null) 'phone': phone,
    });
  }

  /// Verify OTP code.
  Future<OTPVerifyResponseModel> verifyOTP({
    required String email,
    required String otpCode,
    String purpose = 'registration',
    String? phone,
  }) async {
    final response = await _client.post(ApiConstants.otpVerify, data: {
      'email': email,
      'otp_code': otpCode,
      'purpose': purpose,
      if (phone != null) 'phone': phone,
    });
    return OTPVerifyResponseModel.fromJson(
        response.data as Map<String, dynamic>);
  }

  /// Resend OTP code.
  Future<ApiResponse> resendOTP({
    required String email,
    String purpose = 'registration',
  }) async {
    return _client.post(ApiConstants.otpResend, data: {
      'email': email,
      'purpose': purpose,
    });
  }

  /// Request password reset (sends OTP to email).
  Future<ApiResponse> forgotPassword(String email) async {
    return _client.post(ApiConstants.forgotPassword, data: {
      'email': email,
    });
  }

  /// Reset password with OTP verification.
  Future<ApiResponse> resetPassword({
    required String email,
    required String otpCode,
    required String newPassword,
    required String newPassword2,
  }) async {
    return _client.post(ApiConstants.resetPassword, data: {
      'email': email,
      'otp_code': otpCode,
      'new_password': newPassword,
      'new_password2': newPassword2,
    });
  }

  /// Check if email or phone is already registered.
  Future<ApiResponse> checkAvailability({
    String? email,
    String? phone,
  }) async {
    return _client.post(ApiConstants.checkAvailability, data: {
      if (email != null) 'email': email,
      if (phone != null) 'phone': phone,
    });
  }

  /// Admin login endpoint.
  Future<LoginResponseModel> adminLogin({
    required String email,
    required String password,
  }) async {
    final response = await _client.post(ApiConstants.adminLogin, data: {
      'email': email,
      'password': password,
    });
    return LoginResponseModel.fromJson(response.data as Map<String, dynamic>);
  }
}
