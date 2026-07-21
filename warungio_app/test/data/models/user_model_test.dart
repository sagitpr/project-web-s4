import 'package:flutter_test/flutter_test.dart';
import 'package:warungio_app/data/models/user_model.dart';

void main() {
  group('UserModel', () {
    final mockJson = {
      'id': 1,
      'email': 'test@warungio.com',
      'full_name': 'Test User',
      'phone': '+628123456789',
      'role': 'buyer',
      'address': 'Jl. Test No. 1',
      'profile_photo': null,
      'bio': 'Test bio',
      'is_verified': true,
      'wallet_balance': 50000.0,
      'created_at': '2026-07-21T10:00:00Z',
    };

    test('fromJson creates correct UserModel', () {
      final user = UserModel.fromJson(mockJson);

      expect(user.id, 1);
      expect(user.email, 'test@warungio.com');
      expect(user.fullName, 'Test User');
      expect(user.phone, '+628123456789');
      expect(user.role, 'buyer');
      expect(user.address, 'Jl. Test No. 1');
      expect(user.profilePhoto, isNull);
      expect(user.bio, 'Test bio');
      expect(user.isVerified, true);
      expect(user.walletBalance, 50000.0);
      expect(user.createdAt, isNotNull);
    });

    test('fromJson handles minimal data gracefully', () {
      final minimalJson = {
        'id': 99,
        'email': 'minimal@test.com',
        'full_name': 'Minimal',
        'role': 'seller',
      };
      final user = UserModel.fromJson(minimalJson);

      expect(user.id, 99);
      expect(user.email, 'minimal@test.com');
      expect(user.fullName, 'Minimal');
      expect(user.phone, isNull);
      expect(user.role, 'seller');
      expect(user.isVerified, false);
      expect(user.walletBalance, 0.0);
    });

    test('fromJson handles null wallet_balance', () {
      final json = {...mockJson, 'wallet_balance': null};
      final user = UserModel.fromJson(json);
      expect(user.walletBalance, 0.0);
    });

    test('toJson produces correct map', () {
      final user = UserModel.fromJson(mockJson);
      final json = user.toJson();

      expect(json['id'], 1);
      expect(json['email'], 'test@warungio.com');
      expect(json['full_name'], 'Test User');
      expect(json['phone'], '+628123456789');
      expect(json['role'], 'buyer');
      expect(json['wallet_balance'], 50000.0);
    });

    test('isSeller returns true for seller role', () {
      final buyer = UserModel.fromJson({...mockJson, 'role': 'buyer'});
      final seller = UserModel.fromJson({...mockJson, 'role': 'seller'});
      final admin = UserModel.fromJson({...mockJson, 'role': 'admin'});

      expect(buyer.isSeller, false);
      expect(buyer.isBuyer, true);
      expect(seller.isSeller, true);
      expect(seller.isBuyer, false);
      expect(admin.isAdmin, true);
    });

    test('fromJson sets default values for missing fields', () {
      final json = <String, dynamic>{};
      final user = UserModel.fromJson(json);

      expect(user.id, 0);
      expect(user.email, '');
      expect(user.fullName, '');
      expect(user.phone, isNull);
      expect(user.role, 'buyer');
      expect(user.isVerified, false);
      expect(user.walletBalance, 0.0);
    });
  });
}
