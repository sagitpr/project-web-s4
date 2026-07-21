import 'package:flutter_test/flutter_test.dart';
import 'package:warungio_app/data/models/auth_response_model.dart';
import 'package:warungio_app/data/models/user_model.dart';

void main() {
  group('LoginResponseModel', () {
    final mockJson = {
      'message': 'Login berhasil.',
      'access': 'eyJhbGciOiJIUzI1NiIs...',
      'refresh': 'dGhpcyBpcyBhIHJlZnJl...',
      'user': {
        'id': 1,
        'email': 'test@warungio.com',
        'full_name': 'Test User',
        'role': 'buyer',
        'is_verified': true,
        'wallet_balance': 0.0,
      },
    };

    test('fromJson creates correct LoginResponseModel', () {
      final response = LoginResponseModel.fromJson(mockJson);

      expect(response.message, 'Login berhasil.');
      expect(response.access, 'eyJhbGciOiJIUzI1NiIs...');
      expect(response.refresh, 'dGhpcyBpcyBhIHJlZnJl...');
      expect(response.user, isA<UserModel>());
      expect(response.user.email, 'test@warungio.com');
      expect(response.success, true);
      expect(response.accessToken, isNotNull);
      expect(response.refreshToken, isNotNull);
    });

    test('fromJson handles missing tokens as failed', () {
      final json = {'message': 'Login failed', 'user': mockJson['user']};
      final response = LoginResponseModel.fromJson(json);

      expect(response.access, '');
      expect(response.refresh, '');
      expect(response.success, false);
      expect(response.accessToken, isNull);
    });

    test('fromJson handles redirect field', () {
      final json = {...mockJson, 'redirect': '/admin-panel/'};
      final response = LoginResponseModel.fromJson(json);
      expect(response.redirect, '/admin-panel/');
    });
  });

  group('RegisterResponseModel', () {
    final mockJson = {
      'message': 'Registrasi berhasil',
      'user': {
        'id': 2,
        'email': 'newuser@warungio.com',
        'full_name': 'New User',
        'role': 'seller',
      },
      'otp_code': '123456',
      'otp_channels': ['email', 'whatsapp'],
    };

    test('fromJson creates correct RegisterResponseModel', () {
      final response = RegisterResponseModel.fromJson(mockJson);

      expect(response.message, 'Registrasi berhasil');
      expect(response.user.email, 'newuser@warungio.com');
      expect(response.otpCode, '123456');
      expect(response.otpChannels, ['email', 'whatsapp']);
      expect(response.success, true);
    });

    test('fromJson handles missing otp fields', () {
      final json = {
        'message': 'Registrasi berhasil',
        'user': mockJson['user'],
      };
      final response = RegisterResponseModel.fromJson(json);

      expect(response.otpCode, isNull);
      expect(response.otpChannels, isNull);
      expect(response.success, true);
    });

    test('success returns false when message is empty', () {
      final json = {
        'message': '',
        'user': mockJson['user'],
      };
      final response = RegisterResponseModel.fromJson(json);
      expect(response.success, false);
    });
  });

  group('OTPVerifyResponseModel', () {
    final mockJson = {
      'message': 'Verifikasi OTP berhasil.',
      'verified': true,
      'next_step': 'complete',
      'next_endpoint': '/seller/dashboard/',
      'access': 'new_access_token',
      'refresh': 'new_refresh_token',
      'user': {
        'id': 1,
        'email': 'test@warungio.com',
        'full_name': 'Test User',
        'role': 'seller',
        'is_verified': true,
      },
    };

    test('fromJson creates correct OTPVerifyResponseModel', () {
      final response = OTPVerifyResponseModel.fromJson(mockJson);

      expect(response.message, 'Verifikasi OTP berhasil.');
      expect(response.verified, true);
      expect(response.nextStep, 'complete');
      expect(response.nextEndpoint, '/seller/dashboard/');
      expect(response.access, 'new_access_token');
      expect(response.refresh, 'new_refresh_token');
      expect(response.user, isA<UserModel>());
      expect(response.success, true);
    });

    test('fromJson handles verification failure', () {
      final json = {
        'message': 'Kode OTP tidak valid',
        'verified': false,
      };
      final response = OTPVerifyResponseModel.fromJson(json);

      expect(response.verified, false);
      expect(response.success, false);
      expect(response.user, isNull);
    });

    test('fromJson handles nullable user', () {
      final json = {...mockJson, 'user': null};
      final response = OTPVerifyResponseModel.fromJson(json);
      expect(response.user, isNull);
    });
  });

  group('TokenRefreshResponseModel', () {
    test('fromJson creates correct model', () {
      final json = {'access': 'new_access_token'};
      final response = TokenRefreshResponseModel.fromJson(json);

      expect(response.access, 'new_access_token');
      expect(response.success, true);
      expect(response.accessToken, 'new_access_token');
    });

    test('fromJson handles empty token', () {
      final json = <String, dynamic>{};
      final response = TokenRefreshResponseModel.fromJson(json);

      expect(response.access, '');
      expect(response.success, false);
      expect(response.accessToken, isNull);
    });
  });
}
