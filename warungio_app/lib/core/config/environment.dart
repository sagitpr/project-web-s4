import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Provider that exposes the current deployment environment.
///
/// Possible values:
///   - 'development' (default) → uses localhost:8000
///   - 'staging'                → uses staging API
///   - 'production'             → uses production API
///
/// This provider is overridden in [main.dart] via ProviderScope.overrides.
/// All consumers (dio_client, config, etc.) import this single variable
/// to ensure the override applies everywhere.
final environmentProvider = Provider<String>((ref) => 'development');
