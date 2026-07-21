import 'package:flutter_test/flutter_test.dart';
import 'package:warungio_app/core/utils/validators.dart';

void main() {
  group('Validators', () {
    group('email', () {
      test('returns null for valid email', () {
        expect(Validators.email('test@example.com'), isNull);
        expect(Validators.email('user+tag@domain.co.id'), isNull);
      });

      test('returns error for empty email', () {
        expect(Validators.email(''), isNotEmpty);
        expect(Validators.email(null), isNotEmpty);
        expect(Validators.email('   '), isNotEmpty);
      });

      test('returns error for invalid email format', () {
        expect(Validators.email('notanemail'), isNotEmpty);
        expect(Validators.email('@domain.com'), isNotEmpty);
        expect(Validators.email('user@'), isNotEmpty);
      });
    });

    group('password', () {
      test('returns null for valid password', () {
        expect(Validators.password('password123'), isNull);
        expect(Validators.password('a' * 8), isNull);
      });

      test('returns error for empty password', () {
        expect(Validators.password(''), isNotEmpty);
        expect(Validators.password(null), isNotEmpty);
      });

      test('returns error for short password', () {
        expect(Validators.password('short'), isNotEmpty);
        expect(Validators.password('a' * 7), isNotEmpty);
      });

      test('returns error for too long password', () {
        expect(Validators.password('a' * 129), isNotEmpty);
      });
    });

    group('phone', () {
      test('returns null for valid Indonesian phone number', () {
        expect(Validators.phone('08123456789'), isNull);
        expect(Validators.phone('+628123456789'), isNull);
        expect(Validators.phone('628123456789'), isNull);
      });

      test('returns error for invalid phone', () {
        expect(Validators.phone(''), isNotEmpty);
        expect(Validators.phone(null), isNotEmpty);
        expect(Validators.phone('12345'), isNotEmpty);
        expect(Validators.phone('08123'), isNotEmpty);
      });
    });

    group('fullName', () {
      test('returns null for valid name', () {
        expect(Validators.fullName('John Doe'), isNull);
        expect(Validators.fullName('A'), isNotEmpty); // too short
      });

      test('returns error for empty name', () {
        expect(Validators.fullName(''), isNotEmpty);
        expect(Validators.fullName(null), isNotEmpty);
      });

      test('returns error for too short name', () {
        expect(Validators.fullName('ab'), isNotEmpty);
      });

      test('returns error for too long name', () {
        expect(Validators.fullName('a' * 101), isNotEmpty);
      });
    });

    group('otpCode', () {
      test('returns null for valid 6-digit OTP', () {
        expect(Validators.otpCode('123456'), isNull);
        expect(Validators.otpCode('000000'), isNull);
      });

      test('returns error for invalid OTP', () {
        expect(Validators.otpCode(''), isNotEmpty);
        expect(Validators.otpCode(null), isNotEmpty);
        expect(Validators.otpCode('12345'), isNotEmpty);
        expect(Validators.otpCode('1234567'), isNotEmpty);
        expect(Validators.otpCode('abcdef'), isNotEmpty);
      });
    });

    group('required', () {
      test('returns null for non-empty value', () {
        expect(Validators.required('test'), isNull);
      });

      test('returns error for empty value', () {
        expect(Validators.required(''), isNotEmpty);
        expect(Validators.required(null), isNotEmpty);
        expect(Validators.required('  '), isNotEmpty);
      });
    });

    group('numeric', () {
      test('returns null for valid numeric', () {
        expect(Validators.numeric('123'), isNull);
        expect(Validators.numeric('123.45'), isNull);
        expect(Validators.numeric('0'), isNull);
      });

      test('returns error for non-numeric', () {
        expect(Validators.numeric(''), isNotEmpty);
        expect(Validators.numeric(null), isNotEmpty);
        expect(Validators.numeric('abc'), isNotEmpty);
        expect(Validators.numeric('-5'), isNotEmpty); // negative
      });
    });

    group('minLength / maxLength', () {
      test('minLength validates correctly', () {
        expect(Validators.minLength('test', 3), isNull);
        expect(Validators.minLength('te', 3), isNotEmpty);
        expect(Validators.minLength('', 3), isNotEmpty);
      });

      test('maxLength validates correctly', () {
        expect(Validators.maxLength('test', 10), isNull);
        expect(Validators.maxLength('', 10), isNull); // empty allowed
        expect(Validators.maxLength('a' * 11, 10), isNotEmpty);
      });
    });
  });
}
