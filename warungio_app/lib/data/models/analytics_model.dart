/// Model for analytics dashboard summary.
class DashboardSummaryModel {
  final double totalRevenue;
  final int totalOrders;
  final int totalProducts;
  final int totalCustomers;
  final double averageOrderValue;
  final double todayRevenue;
  final int todayOrders;
  final double revenueGrowth;
  final int orderGrowth;

  DashboardSummaryModel({
    this.totalRevenue = 0.0,
    this.totalOrders = 0,
    this.totalProducts = 0,
    this.totalCustomers = 0,
    this.averageOrderValue = 0.0,
    this.todayRevenue = 0.0,
    this.todayOrders = 0,
    this.revenueGrowth = 0.0,
    this.orderGrowth = 0,
  });

  factory DashboardSummaryModel.fromJson(Map<String, dynamic> json) {
    return DashboardSummaryModel(
      totalRevenue: (json['total_revenue'] as num?)?.toDouble() ?? 0.0,
      totalOrders: json['total_orders'] as int? ?? 0,
      totalProducts: json['total_products'] as int? ?? 0,
      totalCustomers: json['total_customers'] as int? ?? 0,
      averageOrderValue:
          (json['average_order_value'] as num?)?.toDouble() ?? 0.0,
      todayRevenue: (json['today_revenue'] as num?)?.toDouble() ?? 0.0,
      todayOrders: json['today_orders'] as int? ?? 0,
      revenueGrowth: (json['revenue_growth'] as num?)?.toDouble() ?? 0.0,
      orderGrowth: json['order_growth'] as int? ?? 0,
    );
  }
}

/// Model for sales trend data point.
class SalesTrendPoint {
  final DateTime date;
  final double revenue;
  final int orders;

  SalesTrendPoint({
    required this.date,
    this.revenue = 0.0,
    this.orders = 0,
  });

  factory SalesTrendPoint.fromJson(Map<String, dynamic> json) {
    return SalesTrendPoint(
      date: DateTime.parse(json['date'] as String? ?? DateTime.now().toIso8601String()),
      revenue: (json['revenue'] as num?)?.toDouble() ?? 0.0,
      orders: json['orders'] as int? ?? 0,
    );
  }
}

/// Model for device analytics breakdown.
class DeviceAnalyticsModel {
  final String deviceType;
  final int visitors;
  final double percentage;

  DeviceAnalyticsModel({
    required this.deviceType,
    this.visitors = 0,
    this.percentage = 0.0,
  });

  factory DeviceAnalyticsModel.fromJson(Map<String, dynamic> json) {
    return DeviceAnalyticsModel(
      deviceType: json['device_type'] as String? ?? '',
      visitors: json['visitors'] as int? ?? 0,
      percentage: (json['percentage'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

/// Model for AI business insight.
class BusinessInsightModel {
  final String type;
  final String title;
  final String description;
  final String? suggestion;
  final String? impact;
  final DateTime createdAt;

  BusinessInsightModel({
    required this.type,
    required this.title,
    required this.description,
    this.suggestion,
    this.impact,
    required this.createdAt,
  });

  factory BusinessInsightModel.fromJson(Map<String, dynamic> json) {
    return BusinessInsightModel(
      type: json['type'] as String? ?? 'info',
      title: json['title'] as String? ?? '',
      description: json['description'] as String? ?? '',
      suggestion: json['suggestion'] as String?,
      impact: json['impact'] as String?,
      createdAt: DateTime.parse(
          json['created_at'] as String? ?? DateTime.now().toIso8601String()),
    );
  }
}
