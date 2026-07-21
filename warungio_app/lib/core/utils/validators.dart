/// Form input validation utilities.
class Validators {
  /// Validate email address.
  static String? email(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Email tidak boleh kosong';
    }
    final emailRegex = RegExp(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$');
    if (!emailRegex.hasMatch(value.trim())) {
      return 'Format email tidak valid';
    }
    return null;
  }

  /// Validate password.
  static String? password(String? value) {
    if (value == null || value.isEmpty) {
      return 'Kata sandi tidak boleh kosong';
    }
    if (value.length < 8) {
      return 'Kata sandi minimal 8 karakter';
    }
    if (value.length > 128) {
      return 'Kata sandi maksimal 128 karakter';
    }
    return null;
  }

  /// Validate phone number (Indonesian format).
  static String? phone(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Nomor telepon tidak boleh kosong';
    }
    final phoneRegex = RegExp(r'^(\+62|62|0)8[1-9][0-9]{6,11}$');
    if (!phoneRegex.hasMatch(value.trim())) {
      return 'Format nomor telepon tidak valid (contoh: 08123456789)';
    }
    return null;
  }

  /// Validate full name.
  static String? fullName(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Nama lengkap tidak boleh kosong';
    }
    if (value.trim().length < 3) {
      return 'Nama lengkap minimal 3 karakter';
    }
    if (value.trim().length > 100) {
      return 'Nama lengkap maksimal 100 karakter';
    }
    return null;
  }

  /// Validate OTP code (6 digits).
  static String? otpCode(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Kode OTP tidak boleh kosong';
    }
    final otpRegex = RegExp(r'^\d{6}$');
    if (!otpRegex.hasMatch(value.trim())) {
      return 'Kode OTP harus 6 digit angka';
    }
    return null;
  }

  /// Validate required field.
  static String? required(String? value, [String fieldName = 'Field ini']) {
    if (value == null || value.trim().isEmpty) {
      return '$fieldName tidak boleh kosong';
    }
    return null;
  }

  /// Validate numeric value.
  static String? numeric(String? value, [String fieldName = 'Nilai']) {
    if (value == null || value.trim().isEmpty) {
      return '$fieldName tidak boleh kosong';
    }
    final number = double.tryParse(value.trim());
    if (number == null) {
      return '$fieldName harus berupa angka';
    }
    if (number < 0) {
      return '$fieldName tidak boleh negatif';
    }
    return null;
  }

  /// Validate minimum length.
  static String? minLength(String? value, int min, [String fieldName = 'Field ini']) {
    if (value == null || value.trim().isEmpty) {
      return '$fieldName tidak boleh kosong';
    }
    if (value.trim().length < min) {
      return '$fieldName minimal $min karakter';
    }
    return null;
  }

  /// Validate maximum length.
  static String? maxLength(String? value, int max, [String fieldName = 'Field ini']) {
    if (value == null || value.trim().isEmpty) {
      return null; // Allow empty — use required() for required fields
    }
    if (value.trim().length > max) {
      return '$fieldName maksimal $max karakter';
    }
    return null;
  }
}
