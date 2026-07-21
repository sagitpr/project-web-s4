import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../widgets/common/card_widgets.dart';
import '../../widgets/common/error_widget.dart';
import '../../../data/models/notification_model.dart';
import '../../../data/datasources/notification_api.dart';

/// Provider for notifications list.
final notificationsListProvider =
    FutureProvider.autoDispose<List<NotificationModel>>((ref) {
  final api = ref.watch(notificationApiProvider);
  return api.getNotifications().then((r) {
    final data = r.data;
    if (data is Map<String, dynamic>) {
      final results = data['results'] as List<dynamic>? ??
          data['data'] as List<dynamic>? ??
          [];
      return results
          .map((e) => NotificationModel.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    return <NotificationModel>[];
  });
});

class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notificationsAsync = ref.watch(notificationsListProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifikasi'),
        actions: [
          notificationsAsync.whenOrNull(
                data: (notifications) => notifications.isNotEmpty
                    ? TextButton(
                        onPressed: () {
                          // TODO: Mark all as read
                        },
                        child: const Text('Baca Semua'),
                      )
                    : null,
              ) ??
              const SizedBox.shrink(),
        ],
      ),
      body: notificationsAsync.when(
        data: (notifications) {
          if (notifications.isEmpty) {
            return EmptyStateWidget(
              message: 'Tidak ada notifikasi',
              subtitle: 'Notifikasi akan muncul di sini',
              icon: Icons.notifications_none_rounded,
            );
          }

          return RefreshIndicator(
            onRefresh: () async =>
                ref.invalidate(notificationsListProvider),
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: notifications.length,
              itemBuilder: (context, index) => NotificationCard(
                notification: notifications[index],
                onTap: () {
                  // Mark as read
                  ref
                      .read(notificationApiProvider)
                      .markAsRead(ids: [notifications[index].id]);
                  ref.invalidate(notificationsListProvider);
                  // TODO: Navigate based on notification type
                },
              ),
            ),
          );
        },
        loading: () => const AppLoadingWidget(message: 'Memuat notifikasi...'),
        error: (_, __) => AppErrorWidget(
          message: 'Gagal memuat notifikasi',
          onRetry: () => ref.invalidate(notificationsListProvider),
        ),
      ),
    );
  }
}
