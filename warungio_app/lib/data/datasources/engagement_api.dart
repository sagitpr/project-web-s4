import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/dio_client.dart';
import '../../core/constants/api_constants.dart';

/// Provider for EngagementApi.
final engagementApiProvider = Provider<EngagementApi>((ref) {
  return EngagementApi(ref.watch(apiClientProvider));
});

/// Engagement & Retention Engine API datasource.
class EngagementApi {
  final ApiClient _client;

  EngagementApi(this._client);

  /// Get user engagement profile.
  Future<ApiResponse> getProfile() async {
    return _client.get(ApiConstants.engagementProfile);
  }

  /// Refresh engagement scores.
  Future<ApiResponse> refreshScores() async {
    return _client.post(ApiConstants.engagementProfileRefresh);
  }

  /// Get user behavior events.
  Future<ApiResponse> getEvents({int page = 1}) async {
    return _client.get(
      ApiConstants.engagementEvents,
      queryParameters: {'page': page},
    );
  }

  /// Record a behavior event.
  Future<ApiResponse> recordEvent(Map<String, dynamic> event) async {
    return _client.post(ApiConstants.engagementRecordEvent, data: event);
  }

  /// Register device token for push notifications.
  Future<ApiResponse> registerDeviceToken(String token) async {
    return _client.post(ApiConstants.engagementDeviceRegister, data: {
      'device_token': token,
    });
  }

  /// Unregister device token.
  Future<ApiResponse> unregisterDeviceToken(String token) async {
    return _client.post(ApiConstants.engagementDeviceUnregister, data: {
      'device_token': token,
    });
  }

  /// Get user notification queue.
  Future<ApiResponse> getNotificationQueue({int page = 1}) async {
    return _client.get(
      ApiConstants.engagementNotifications,
      queryParameters: {'page': page},
    );
  }
}
