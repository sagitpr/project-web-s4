class ProductModel {
  final int id;
  final int store;
  final String storeName;
  final String productName;
  final String? description;
  final double price;
  final int stock;
  final int? reservedStock;
  final String unit;
  final String? slug;
  final String? image;
  final String? categoryName;
  final int? category;
  final double? ratingAvg;
  final int? reviewCount;
  final int? soldCount;
  final bool isActive;
  final String? productStatus;
  final int? qualityScore;
  final DateTime? createdAt;

  ProductModel({
    required this.id,
    required this.store,
    required this.storeName,
    required this.productName,
    this.description,
    required this.price,
    required this.stock,
    this.reservedStock,
    required this.unit,
    this.slug,
    this.image,
    this.categoryName,
    this.category,
    this.ratingAvg,
    this.reviewCount,
    this.soldCount,
    this.isActive = true,
    this.productStatus,
    this.qualityScore,
    this.createdAt,
  });

  factory ProductModel.fromJson(Map<String, dynamic> json) {
    return ProductModel(
      id: json['id'] as int,
      store: json['store'] as int? ?? 0,
      storeName: json['store_name'] as String? ?? '',
      productName: json['product_name'] as String? ?? '',
      description: json['description'] as String?,
      price: (json['price'] as num?)?.toDouble() ?? 0.0,
      stock: json['stock'] as int? ?? 0,
      reservedStock: json['reserved_stock'] as int?,
      unit: json['unit'] as String? ?? 'pcs',
      slug: json['slug'] as String?,
      image: json['image'] as String?,
      categoryName: json['category_name'] as String?,
      category: json['category'] as int?,
      ratingAvg: (json['rating_avg'] as num?)?.toDouble(),
      reviewCount: json['review_count'] as int?,
      soldCount: json['sold_count'] as int?,
      isActive: json['is_active'] as bool? ?? true,
      productStatus: json['product_status'] as String?,
      qualityScore: json['quality_score'] as int?,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'store': store,
      'product_name': productName,
      'description': description,
      'price': price,
      'stock': stock,
      'unit': unit,
      'is_active': isActive,
    };
  }

  String get formattedPrice => 'Rp ${price.toStringAsFixed(0).replaceAllMapped(
    RegExp(r'(\d)(?=(\d{3})+(?!\d))'), (m) => '${m[1]}.'),
  }';
}
