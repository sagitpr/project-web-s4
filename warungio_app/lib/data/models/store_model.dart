/// Model representing a store (seller shop) from the backend.
class StoreModel {
  final int id;
  final int userId;
  final String storeName;
  final String? slug;
  final String? description;
  final String? address;
  final String? city;
  final int? categoryId;
  final String? categoryName;
  final String? logo;
  final String? banner;
  final String status;
  final double? ratingAvg;
  final int? reviewCount;
  final int? followerCount;
  final int? productCount;
  final bool isFollowed;
  final DateTime? createdAt;

  StoreModel({
    required this.id,
    required this.userId,
    required this.storeName,
    this.slug,
    this.description,
    this.address,
    this.city,
    this.categoryId,
    this.categoryName,
    this.logo,
    this.banner,
    this.status = 'pending',
    this.ratingAvg,
    this.reviewCount,
    this.followerCount,
    this.productCount,
    this.isFollowed = false,
    this.createdAt,
  });

  factory StoreModel.fromJson(Map<String, dynamic> json) {
    return StoreModel(
      id: json['id'] as int,
      userId: json['user'] as int? ?? 0,
      storeName: json['store_name'] as String? ?? '',
      slug: json['slug'] as String?,
      description: json['description'] as String?,
      address: json['address'] as String?,
      city: json['city'] as String?,
      categoryId: json['category'] as int?,
      categoryName: json['category_name'] as String?,
      logo: json['logo'] as String?,
      banner: json['banner'] as String?,
      status: json['status'] as String? ?? 'pending',
      ratingAvg: (json['rating_avg'] as num?)?.toDouble(),
      reviewCount: json['review_count'] as int?,
      followerCount: json['follower_count'] as int?,
      productCount: json['product_count'] as int?,
      isFollowed: json['is_followed'] as bool? ?? false,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'store_name': storeName,
      'description': description,
      'address': address,
      'city': city,
      'category': categoryId,
    };
  }

  bool get isActive => status == 'active';
  bool get isPending => status == 'pending';
}

/// Store category model.
class StoreCategoryModel {
  final int id;
  final String name;
  final String? icon;
  final int? storeCount;

  StoreCategoryModel({
    required this.id,
    required this.name,
    this.icon,
    this.storeCount,
  });

  factory StoreCategoryModel.fromJson(Map<String, dynamic> json) {
    return StoreCategoryModel(
      id: json['id'] as int,
      name: json['name'] as String? ?? '',
      icon: json['icon'] as String?,
      storeCount: json['store_count'] as int?,
    );
  }
}
