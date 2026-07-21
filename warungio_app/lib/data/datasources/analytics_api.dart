import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/dio_client.dart';
import '../../core/constants/api_constants.dart';
import '../models/analytics_model.dart';

/// Provider for AnalyticsApi.
final analyticsApiProvider = Provider<AnalyticsApi>((ref) {
  return AnalyticsApi(ref.watch(apiClientProvider));
});

/// Analytics API datasource.
class AnalyticsApi {
  final ApiClient _client;

  AnalyticsApi(this._client);

  /// Get dashboard summary for seller.
  Future<ApiResponse> getDashboardSummary() async {
    return _client.get(ApiConstants.analyticsDashboard);
  }

  /// Get sales analytics.
  Future<ApiResponse> getSalesAnalytics({
    String? period,
    DateTime? startDate,
    DateTime? endDate,
  }) async {
    final params = <String, dynamic>{};
    if (period != null) params['period'] = period;
    if (startDate != null) params['start_date'] = startDate.toIso8601String();
    if (endDate != null) params['end_date'] = endDate.toIso8601String();
    return _client.get(ApiConstants.analyticsSales, queryParameters: params);
  }

  /// Get sales trend data.
  Future<ApiResponse> getSalesTrend({
    String? period = '7d',
  }) async {
    return _client.get(
      ApiConstants.salesTrend,
      queryParameters: {'period': period},
    );
  }

  /// Get device analytics.
  Future<ApiResponse> getDeviceAnalytics({
    String? period,
  }) async {
    final params = <String, dynamic>{};
    if (period != null) params['period'] = period;
    return _client.get(ApiConstants.analyticsDevices, queryParameters: params);
  }

  /// Get user activities.
  Future<ApiResponse> getUserActivities({int page = 1}) async {
    return _client.get(
      ApiConstants.userActivities,
      queryParameters: {'page': page},
    );
  }

  /// Get daily reports.
  Future<ApiResponse> getDailyReports({int page = 1}) async {
    return _client.get(
      ApiConstants.dailyReports,
      queryParameters: {'page': page},
    );
  }

  /// Get realtime analytics.
  Future<ApiResponse> getRealtimeAnalytics() async {
    return _client.get(ApiConstants.realtimeAnalytics);
  }

  /// Get AI business insights for seller.
  Future<ApiResponse> getAIBusinessInsights() async {
    return _client.get(ApiConstants.aiBusinessInsights);
  }

  /// Get seller report.
  Future<ApiResponse> getSellerReport({String? period}) async {
    final params = <String, dynamic>{};
    if (period != null) params['period'] = period;
    return _client.get(ApiConstants.sellerReport, queryParameters: params);
  }
}
