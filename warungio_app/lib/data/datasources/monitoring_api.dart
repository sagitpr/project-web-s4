import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/dio_client.dart';
import '../../core/constants/api_constants.dart';

/// Provider for MonitoringApi.
final monitoringApiProvider = Provider<MonitoringApi>((ref) {
  return MonitoringApi(ref.watch(apiClientProvider));
});

/// System Monitoring API datasource.
class MonitoringApi {
  final ApiClient _client;

  MonitoringApi(this._client);

  /// Check system health.
  Future<ApiResponse> health() async {
    return _client.get(ApiConstants.monitoringHealth);
  }

  /// Get monitoring dashboard data.
  Future<ApiResponse> getDashboard() async {
    return _client.get(ApiConstants.monitoringDashboard);
  }

  /// Get performance metrics.
  Future<ApiResponse> getMetrics({String? period}) async {
    final params = <String, dynamic>{};
    if (period != null) params['period'] = period;
    return _client.get(ApiConstants.monitoringMetrics, queryParameters: params);
  }

  /// Get error logs.
  Future<ApiResponse> getErrorLogs({int page = 1}) async {
    return _client.get(
      ApiConstants.monitoringErrors,
      queryParameters: {'page': page},
    );
  }
}
