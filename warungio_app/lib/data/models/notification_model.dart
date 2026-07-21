/// Model representing a notification from the backend.
class NotificationModel {
  final int id;
  final String type;
  final String title;
  final String? body;
  final String? image;
  final String? actionUrl;
  final bool isRead;
  final DateTime createdAt;

  NotificationModel({
    required this.id,
    required this.type,
    required this.title,
    this.body,
    this.image,
    this.actionUrl,
    this.isRead = false,
    required this.createdAt,
  });

  factory NotificationModel.fromJson(Map<String, dynamic> json) {
    return NotificationModel(
      id: json['id'] as int,
      type: json['type'] as String? ?? json['notification_type'] as String? ?? '',
      title: json['title'] as String? ?? json['notification_title'] as String? ?? '',
      body: json['body'] as String? ?? json['message'] as String? ?? json['notification_body'] as String?,
      image: json['image'] as String? ?? json['notification_image'] as String?,
      actionUrl: json['action_url'] as String?,
      isRead: json['is_read'] as bool? ?? false,
      createdAt: DateTime.parse(
          json['created_at'] as String? ?? json['sent_at'] as String? ?? DateTime.now().toIso8601String()),
    );
  }
}

/// Model representing notification preferences.
class NotificationPreferenceModel {
  final bool emailNotifications;
  final bool pushNotifications;
  final bool whatsappNotifications;
  final bool orderUpdates;
  final bool promotions;
  final bool systemAlerts;

  NotificationPreferenceModel({
    this.emailNotifications = true,
    this.pushNotifications = true,
    this.whatsappNotifications = false,
    this.orderUpdates = true,
    this.promotions = true,
    this.systemAlerts = true,
  });

  factory NotificationPreferenceModel.fromJson(Map<String, dynamic> json) {
    return NotificationPreferenceModel(
      emailNotifications: json['email_notifications'] as bool? ?? true,
      pushNotifications: json['push_notifications'] as bool? ?? true,
      whatsappNotifications: json['whatsapp_notifications'] as bool? ?? false,
      orderUpdates: json['order_updates'] as bool? ?? true,
      promotions: json['promotions'] as bool? ?? true,
      systemAlerts: json['system_alerts'] as bool? ?? true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'email_notifications': emailNotifications,
      'push_notifications': pushNotifications,
      'whatsapp_notifications': whatsappNotifications,
      'order_updates': orderUpdates,
      'promotions': promotions,
      'system_alerts': systemAlerts,
    };
  }
}
