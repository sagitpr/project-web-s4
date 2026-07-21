/// Model representing a shipping method from the backend.
class ShippingMethodModel {
  final int id;
  final String name;
  final String? description;
  final String? courier;
  final String? serviceType;
  final double cost;
  final String? estimatedDays;
  final bool isActive;

  ShippingMethodModel({
    required this.id,
    required this.name,
    this.description,
    this.courier,
    this.serviceType,
    required this.cost,
    this.estimatedDays,
    this.isActive = true,
  });

  factory ShippingMethodModel.fromJson(Map<String, dynamic> json) {
    return ShippingMethodModel(
      id: json['id'] as int,
      name: json['name'] as String? ?? json['shipping_method'] as String? ?? '',
      description: json['description'] as String?,
      courier: json['courier'] as String?,
      serviceType: json['service_type'] as String?,
      cost: (json['cost'] as num?)?.toDouble() ?? 0.0,
      estimatedDays: json['estimated_days'] as String?,
      isActive: json['is_active'] as bool? ?? true,
    );
  }
}
