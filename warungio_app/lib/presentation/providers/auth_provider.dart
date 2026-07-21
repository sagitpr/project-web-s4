import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/models/auth_response_model.dart';
import '../../data/models/user_model.dart';
import '../../data/repositories/auth_repository.dart';
import '../../core/storage/secure_storage_service.dart';

/// Enum representing authentication status.
enum AuthStatus {
  initial,
  authenticated,
  unauthenticated,
  loading,
}

/// Auth state class.
class AuthState {
  final AuthStatus status;
  final UserModel? user;
  final String? errorMessage;
  final bool isSeller;

  const AuthState({
    this.status = AuthStatus.initial,
    this.user,
    this.errorMessage,
    this.isSeller = false,
  });

  AuthState copyWith({
    AuthStatus? status,
    UserModel? user,
    String? errorMessage,
    bool? isSeller,
  }) {
    return AuthState(
      status: status ?? this.status,
      user: user ?? this.user,
      errorMessage: errorMessage,
      isSeller: isSeller ?? this.isSeller,
    );
  }

  bool get isAuthenticated => status == AuthStatus.authenticated;
}

/// StateNotifier that manages authentication state.
class AuthNotifier extends StateNotifier<AuthState> {
  final AuthRepository _authRepository;
  final SecureStorageService _secureStorage;

  AuthNotifier({
    required AuthRepository authRepository,
    required SecureStorageService secureStorage,
  })  : _authRepository = authRepository,
        _secureStorage = secureStorage,
        super(const AuthState()) {
    _checkAuthStatus();
  }

  /// Check if user is already authenticated on app start.
  Future<void> _checkAuthStatus() async {
    try {
      final isAuth = await _authRepository.isAuthenticated();
      if (isAuth) {
        final user = await _authRepository.getCurrentUser();
        if (user != null) {
          state = AuthState(
            status: AuthStatus.authenticated,
            user: user,
            isSeller: user.isSeller,
          );
        } else {
          // Token exists but no cached user data, try to fetch from server
          try {
            final freshUser = await _authRepository.fetchProfile();
            state = AuthState(
              status: AuthStatus.authenticated,
              user: freshUser,
              isSeller: freshUser.isSeller,
            );
          } catch (_) {
            state = const AuthState(
              status: AuthStatus.unauthenticated,
            );
          }
        }
      } else {
        state = const AuthState(status: AuthStatus.unauthenticated);
      }
    } catch (_) {
      state = const AuthState(status: AuthStatus.unauthenticated);
    }
  }

  /// Login with email and password.
  Future<bool> login({
    required String email,
    required String password,
    String? loginEntry,
  }) async {
    state = state.copyWith(status: AuthStatus.loading, errorMessage: null);
    try {
      final response = await _authRepository.login(
        email: email,
        password: password,
        loginEntry: loginEntry,
      );
      if (response.success && response.user.id > 0) {
        state = AuthState(
          status: AuthStatus.authenticated,
          user: response.user,
          isSeller: response.user.isSeller,
        );
        return true;
      } else {
        state = state.copyWith(
          status: AuthStatus.unauthenticated,
          errorMessage: response.message.isNotEmpty
              ? response.message
              : 'Login gagal',
        );
        return false;
      }
    } catch (e) {
      state = state.copyWith(
        status: AuthStatus.unauthenticated,
        errorMessage: 'Terjadi kesalahan. Silakan coba lagi.',
      );
      return false;
    }
  }

  /// Register a new user.
  Future<RegisterResponseModel?> register({
    required String email,
    required String password,
    required String fullName,
    String? phone,
    String? role,
  }) async {
    state = state.copyWith(status: AuthStatus.loading, errorMessage: null);
    try {
      final response = await _authRepository.register(
        email: email,
        password: password,
        fullName: fullName,
        phone: phone,
        role: role,
      );
      state = state.copyWith(status: AuthStatus.unauthenticated);
      return response;
    } catch (e) {
      state = state.copyWith(
        status: AuthStatus.unauthenticated,
        errorMessage: 'Pendaftaran gagal. Silakan coba lagi.',
      );
      return null;
    }
  }

  /// Request OTP code.
  Future<ApiResponse?> requestOtp({
    required String email,
    String purpose = 'registration',
  }) async {
    try {
      return await _authRepository.requestOtp(email: email, purpose: purpose);
    } catch (_) {
      return null;
    }
  }

  /// Verify OTP and complete registration.
  Future<OTPVerifyResponseModel?> verifyOtp({
    required String email,
    required String otpCode,
  }) async {
    state = state.copyWith(status: AuthStatus.loading, errorMessage: null);
    try {
      final response = await _authRepository.verifyOtp(
        email: email,
        otpCode: otpCode,
      );
      if (response.success && response.user != null) {
        state = AuthState(
          status: AuthStatus.authenticated,
          user: response.user,
          isSeller: response.user!.isSeller,
        );
      }
      return response;
    } catch (e) {
      state = state.copyWith(
        status: AuthStatus.unauthenticated,
        errorMessage: 'Verifikasi OTP gagal.',
      );
      return null;
    }
  }

  /// Logout.
  Future<void> logout() async {
    await _authRepository.logout();
    state = const AuthState(status: AuthStatus.unauthenticated);
  }

  /// Clear any error messages.
  void clearError() {
    state = state.copyWith(errorMessage: null);
  }
}

/// Riverpod provider for auth state.
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  final repository = ref.watch(authRepositoryProvider);
  final secureStorage = ref.watch(secureStorageServiceProvider);
  return AuthNotifier(authRepository: repository, secureStorage: secureStorage);
});
