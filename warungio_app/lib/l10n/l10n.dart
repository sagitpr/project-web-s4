import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Simple localization delegate that loads ARB files.
/// This provides localization without requiring Flutter gen-l10n build step.
class AppLocalization {
  final Locale locale;
  late Map<String, dynamic> _strings;

  AppLocalization(this.locale);

  static AppLocalization of(BuildContext context) {
    return Localizations.of<AppLocalization>(context, AppLocalization)!;
  }

  static const LocalizationDelegate delegate = LocalizationDelegate();

  static final Map<String, Map<String, dynamic>> _cachedStrings = {};

  Future<void> load() async {
    if (_cachedStrings.containsKey(locale.languageCode)) {
      _strings = _cachedStrings[locale.languageCode]!;
      return;
    }

    try {
      final jsonString = await rootBundle.loadString(
        _getArbPath(locale.languageCode),
      );
      final data = json.decode(jsonString) as Map<String, dynamic>;
      // Filter out metadata keys (starting with @@)
      _strings = Map.fromEntries(
        data.entries.where((e) => !e.key.startsWith('@@')),
      );
      _cachedStrings[locale.languageCode] = _strings;
    } catch (e) {
      debugPrint('Failed to load locale ${locale.languageCode}: $e');
      // Fallback to empty strings
      _strings = {};
    }
  }

  String _getArbPath(String languageCode) {
    return 'lib/l10n/app_$languageCode.arb';
  }

  String? operator [](String key) {
    return _strings[key] as String?;
  }

  String translate(String key, {Map<String, String>? args}) {
    String? value = _strings[key] as String?;
    if (value == null) return key;

    if (args != null) {
      for (final entry in args.entries) {
        value = value!.replaceAll('{$entry.key}', entry.value);
      }
    }
    return value!;
  }
}

class LocalizationDelegate extends LocalizationsDelegate<AppLocalization> {
  const LocalizationDelegate();

  @override
  bool isSupported(Locale locale) =>
      locale.languageCode == 'id' || locale.languageCode == 'en';

  @override
  Future<AppLocalization> load(Locale locale) async {
    final localization = AppLocalization(locale);
    await localization.load();
    return localization;
  }

  @override
  bool shouldReload(LocalizationDelegate old) => false;
}
