import 'user_model.dart';

/// Response from the login endpoint.
class LoginResponseModel {
  final String message;
  final String access;
  final String refresh;
  final UserModel user;
  final String? redirect;

  LoginResponseModel({
    required this.message,
    required this.access,
    required this.refresh,
    required this.user,
    this.redirect,
  });

  factory LoginResponseModel.fromJson(Map<String, dynamic> json) {
    return LoginResponseModel(
      message: json['message'] as String? ?? '',
      access: json['access'] as String? ?? '',
      refresh: json['refresh'] as String? ?? '',
      user: UserModel.fromJson(json['user'] as Map<String, dynamic>),
      redirect: json['redirect'] as String?,
    );
  }

  bool get success => access.isNotEmpty;

  String? get accessToken => access.isNotEmpty ? access : null;

  String? get refreshToken => refresh.isNotEmpty ? refresh : null;
}

/// Response from the register endpoint.
class RegisterResponseModel {
  final String message;
  final UserModel user;
  final String? otpCode;
  final List<String>? otpChannels;

  RegisterResponseModel({
    required this.message,
    required this.user,
    this.otpCode,
    this.otpChannels,
  });

  factory RegisterResponseModel.fromJson(Map<String, dynamic> json) {
    return RegisterResponseModel(
      message: json['message'] as String? ?? '',
      user: UserModel.fromJson(json['user'] as Map<String, dynamic>),
      otpCode: json['otp_code'] as String?,
      otpChannels: (json['otp_channels'] as List<dynamic>?)
          ?.map((e) => e.toString())
          .toList(),
    );
  }

  bool get success => message.isNotEmpty;
}

/// Response from the OTP verify endpoint.
class OTPVerifyResponseModel {
  final String message;
  final bool verified;
  final String? nextStep;
  final String? nextEndpoint;
  final String? access;
  final String? refresh;
  final UserModel? user;

  OTPVerifyResponseModel({
    required this.message,
    required this.verified,
    this.nextStep,
    this.nextEndpoint,
    this.access,
    this.refresh,
    this.user,
  });

  factory OTPVerifyResponseModel.fromJson(Map<String, dynamic> json) {
    return OTPVerifyResponseModel(
      message: json['message'] as String? ?? '',
      verified: json['verified'] as bool? ?? false,
      nextStep: json['next_step'] as String?,
      nextEndpoint: json['next_endpoint'] as String?,
      access: json['access'] as String?,
      refresh: json['refresh'] as String?,
      user: json['user'] != null
          ? UserModel.fromJson(json['user'] as Map<String, dynamic>)
          : null,
    );
  }

  bool get success => verified;

  String? get accessToken => access;

  String? get refreshToken => refresh;
}

/// Response from the token refresh endpoint.
class TokenRefreshResponseModel {
  final String access;

  TokenRefreshResponseModel({required this.access});

  factory TokenRefreshResponseModel.fromJson(Map<String, dynamic> json) {
    return TokenRefreshResponseModel(
      access: json['access'] as String? ?? '',
    );
  }

  bool get success => access.isNotEmpty;

  String? get accessToken => access.isNotEmpty ? access : null;
}
