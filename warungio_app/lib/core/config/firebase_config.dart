import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

/// Provider that indicates whether Firebase is initialized.
final firebaseInitializedProvider = StateProvider<bool>((ref) => false);

/// Provider for FirebaseMessaging instance.
final firebaseMessagingProvider = Provider<FirebaseMessaging?>((ref) {
  final initialized = ref.watch(firebaseInitializedProvider);
  if (initialized) {
    return FirebaseMessaging.instance;
  }
  return null;
});

/// Provider for the FCM token.
final fcmTokenProvider = FutureProvider<String?>((ref) {
  final messaging = ref.watch(firebaseMessagingProvider);
  if (messaging == null) return Future.value(null);
  return messaging.getToken();
});

/// ── Firebase Background Handler ────────────────────────────────────────
///
/// IMPORTANT: This MUST be a top-level function, NOT a method inside a class.
/// Firebase background handlers run in a separate isolate where class
/// context is unavailable.
@pragma('vm:entry-point')
Future<void> firebaseBackgroundMessageHandler(RemoteMessage message) async {
  debugPrint(
      'Firebase background message: ${message.notification?.title ?? '(no title)'}');
  // Handle background data payload here
  // e.g., update badge count, save to local storage
}

/// Service class for Firebase Cloud Messaging setup.
class FirebaseConfig {
  /// Initialize Firebase. Call this once in main.dart.
  static Future<void> initialize() async {
    try {
      await Firebase.initializeApp();

      // Request notification permissions (required for iOS)
      final messaging = FirebaseMessaging.instance;
      final settings = await messaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
        provisional: false,
      );

      debugPrint('FCM permission granted: ${settings.authorizationStatus}');

      // Register for remote messages
      await messaging.registerDeviceForRemoteMessages();

      // Set up foreground message handler
      FirebaseMessaging.onMessage.listen(_handleForegroundMessage);

      // Set up background message handler (top-level function)
      FirebaseMessaging.onBackgroundMessage(firebaseBackgroundMessageHandler);

      // Handle notification taps when app was in background
      FirebaseMessaging.onMessageOpenedApp.listen(_handleNotificationTap);

      // Handle notification that opened the app from terminated state
      final initialMessage = await messaging.getInitialMessage();
      if (initialMessage != null) {
        _handleNotificationTap(initialMessage);
      }

      debugPrint('Firebase initialized successfully');
    } catch (e) {
      debugPrint('Firebase initialization failed: $e');
      // In development, Firebase may not be configured — this is non-fatal
    }
  }

  /// Handle foreground message — show local notification.
  static void _handleForegroundMessage(RemoteMessage message) {
    debugPrint('Foreground notification: ${message.notification?.title}');
    // TODO: Display local notification using flutter_local_notifications
  }

  /// Handle notification tap — navigate to relevant screen.
  static void _handleNotificationTap(RemoteMessage message) {
    final data = message.data;
    debugPrint('Notification tapped with data: $data');

    // Navigate based on notification type
    // if (data['type'] == 'order') {
    //   final orderId = data['order_id'];
    //   // Navigate to order detail screen
    // }
  }
}
