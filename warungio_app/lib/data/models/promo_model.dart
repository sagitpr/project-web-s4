/// Model representing a promotion/promo from the backend.
class PromoModel {
  final int id;
  final String name;
  final String? description;
  final String type; // percentage, fixed
  final double value;
  final double? minPurchase;
  final double? maxDiscount;
  final DateTime? startDate;
  final DateTime? endDate;
  final bool isActive;
  final int? storeId;
  final String? storeName;
  final String? image;
  final int? usageLimit;
  final int usedCount;

  PromoModel({
    required this.id,
    required this.name,
    this.description,
    required this.type,
    required this.value,
    this.minPurchase,
    this.maxDiscount,
    this.startDate,
    this.endDate,
    this.isActive = true,
    this.storeId,
    this.storeName,
    this.image,
    this.usageLimit,
    this.usedCount = 0,
  });

  factory PromoModel.fromJson(Map<String, dynamic> json) {
    return PromoModel(
      id: json['id'] as int,
      name: json['name'] as String? ?? json['promo_name'] as String? ?? '',
      description: json['description'] as String?,
      type: json['type'] as String? ?? json['discount_type'] as String? ?? 'percentage',
      value: (json['value'] as num?)?.toDouble() ?? (json['discount_value'] as num?)?.toDouble() ?? 0.0,
      minPurchase: (json['min_purchase'] as num?)?.toDouble(),
      maxDiscount: (json['max_discount'] as num?)?.toDouble(),
      startDate: json['start_date'] != null
          ? DateTime.tryParse(json['start_date'] as String)
          : null,
      endDate: json['end_date'] != null
          ? DateTime.tryParse(json['end_date'] as String)
          : null,
      isActive: json['is_active'] as bool? ?? true,
      storeId: json['store'] as int?,
      storeName: json['store_name'] as String?,
      image: json['image'] as String?,
      usageLimit: json['usage_limit'] as int?,
      usedCount: json['used_count'] as int? ?? 0,
    );
  }
}

/// Model representing a voucher code.
class VoucherModel {
  final int id;
  final String code;
  final String type;
  final double value;
  final double? minPurchase;
  final double? maxDiscount;
  final DateTime? expiresAt;
  final bool isValid;
  final String? message;

  VoucherModel({
    required this.id,
    required this.code,
    required this.type,
    required this.value,
    this.minPurchase,
    this.maxDiscount,
    this.expiresAt,
    this.isValid = true,
    this.message,
  });

  factory VoucherModel.fromJson(Map<String, dynamic> json) {
    return VoucherModel(
      id: json['id'] as int,
      code: json['code'] as String? ?? json['voucher_code'] as String? ?? '',
      type: json['type'] as String? ?? json['discount_type'] as String? ?? 'percentage',
      value: (json['value'] as num?)?.toDouble() ?? 0.0,
      minPurchase: (json['min_purchase'] as num?)?.toDouble(),
      maxDiscount: (json['max_discount'] as num?)?.toDouble(),
      expiresAt: json['expires_at'] != null
          ? DateTime.tryParse(json['expires_at'] as String)
          : null,
      isValid: json['is_valid'] as bool? ?? true,
      message: json['message'] as String?,
    );
  }
}
