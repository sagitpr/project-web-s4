import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/dio_client.dart';
import '../../core/constants/api_constants.dart';
import '../models/notification_model.dart';

/// Provider for NotificationApi.
final notificationApiProvider = Provider<NotificationApi>((ref) {
  return NotificationApi(ref.watch(apiClientProvider));
});

/// Notification API datasource.
class NotificationApi {
  final ApiClient _client;

  NotificationApi(this._client);

  /// Get list of notifications.
  Future<ApiResponse> getNotifications({int page = 1}) async {
    return _client.get(
      ApiConstants.notifications,
      queryParameters: {'page': page},
    );
  }

  /// Get unread notification count.
  Future<ApiResponse> getUnreadCount() async {
    return _client.get(ApiConstants.notificationUnreadCount);
  }

  /// Mark notifications as read.
  Future<ApiResponse> markAsRead({List<int>? ids}) async {
    return _client.post(ApiConstants.notificationMarkRead, data: {
      if (ids != null) 'ids': ids,
    });
  }

  /// Get notification preferences.
  Future<ApiResponse> getPreferences() async {
    return _client.get(ApiConstants.notificationPreferences);
  }

  /// Update notification preferences.
  Future<ApiResponse> updatePreferences(
      NotificationPreferenceModel preferences) async {
    return _client.patch(
      ApiConstants.notificationPreferences,
      data: preferences.toJson(),
    );
  }

  /// Delete a notification.
  Future<ApiResponse> deleteNotification(int id) async {
    final path =
        ApiConstants.notificationDelete.replaceAll('{id}', id.toString());
    return _client.delete(path);
  }
}
