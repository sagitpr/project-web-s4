import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

/// Extension methods on [String].
extension StringExtension on String {
  /// Capitalize the first letter of the string.
  String get capitalize {
    if (isEmpty) return this;
    return '${this[0].toUpperCase()}${substring(1)}';
  }

  /// Capitalize the first letter of each word.
  String get titleCase {
    if (isEmpty) return this;
    return split(' ').map((word) {
      if (word.isEmpty) return word;
      return word[0].toUpperCase() + word.substring(1).toLowerCase();
    }).join(' ');
  }

  /// Truncate string to max length with ellipsis.
  String truncate(int maxLength) {
    if (length <= maxLength) return this;
    return '${substring(0, maxLength)}...';
  }

  /// Convert snake_case to Title Case.
  String get snakeToTitle {
    return replaceAll('_', ' ').titleCase;
  }
}

/// Extension methods on [double] for currency formatting.
extension CurrencyExtension on double {
  /// Format as Indonesian Rupiah.
  String get toRupiah {
    final format = NumberFormat('#,###', 'id_ID');
    return 'Rp${format.format(this)}';
  }

  /// Format compact (e.g., 1.5RB for 1500).
  String get toCompactCurrency {
    if (this >= 1000000) {
      final value = (this / 1000000).toStringAsFixed(1);
      return 'Rp${value}JT';
    } else if (this >= 1000) {
      final value = (this / 1000).toStringAsFixed(1);
      return 'Rp${value}RB';
    }
    return toRupiah;
  }
}

/// Extension methods on [int] for IDR formatting.
extension IntCurrencyExtension on int {
  String get toRupiah => (this as double).toRupiah;
  String get toCompactCurrency => (this as double).toCompactCurrency;
}

/// Extension methods on [DateTime].
extension DateTimeExtension on DateTime {
  /// Format as Indonesian date (e.g., "21 Juli 2026").
  String get toIndonesianDate {
    final format = DateFormat('d MMMM yyyy', 'id_ID');
    return format.format(this);
  }

  /// Format as Indonesian date time.
  String get toIndonesianDateTime {
    final format = DateFormat('d MMMM yyyy HH:mm', 'id_ID');
    return format.format(this);
  }

  /// Format as relative time (e.g., "2 jam yang lalu").
  String get timeAgo {
    final now = DateTime.now();
    final diff = now.difference(this);

    if (diff.inDays > 30) {
      return toIndonesianDate;
    } else if (diff.inDays > 0) {
      return '${diff.inDays} hari yang lalu';
    } else if (diff.inHours > 0) {
      return '${diff.inHours} jam yang lalu';
    } else if (diff.inMinutes > 0) {
      return '${diff.inMinutes} menit yang lalu';
    } else {
      return 'Baru saja';
    }
  }
}

/// Extension methods on [BuildContext].
extension BuildContextExtension on BuildContext {
  /// Get theme data.
  ThemeData get theme => Theme.of(this);

  /// Get text theme.
  TextTheme get textTheme => Theme.of(this).textTheme;

  /// Get color scheme.
  ColorScheme get colorScheme => Theme.of(this).colorScheme;

  /// Get media query.
  MediaQueryData get mediaQuery => MediaQuery.of(this);

  /// Get screen size.
  Size get screenSize => MediaQuery.of(this).size;

  /// Get screen width.
  double get screenWidth => MediaQuery.of(this).size.width;

  /// Get screen height.
  double get screenHeight => MediaQuery.of(this).size.height;

  /// Check if device is small (phone).
  bool get isSmallScreen => screenWidth < 600;

  /// Check if device is medium (tablet).
  bool get isMediumScreen => screenWidth >= 600 && screenWidth < 1200;

  /// Check if device is large (desktop/tablet landscape).
  bool get isLargeScreen => screenWidth >= 1200;

  /// Show snackbar with a message.
  void showSnackBar(String message, {bool isError = false}) {
    ScaffoldMessenger.of(this).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? Colors.red.shade700 : null,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
    );
  }
}
