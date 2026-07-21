/// Model representing a product category from the backend.
class CategoryModel {
  final int id;
  final String name;
  final String? slug;
  final String? icon;
  final String? image;
  final int? parentId;
  final String? parentName;
  final int? productCount;
  final bool isActive;

  CategoryModel({
    required this.id,
    required this.name,
    this.slug,
    this.icon,
    this.image,
    this.parentId,
    this.parentName,
    this.productCount,
    this.isActive = true,
  });

  factory CategoryModel.fromJson(Map<String, dynamic> json) {
    return CategoryModel(
      id: json['id'] as int,
      name: json['name'] as String? ?? json['category_name'] as String? ?? '',
      slug: json['slug'] as String?,
      icon: json['icon'] as String?,
      image: json['image'] as String?,
      parentId: json['parent'] as int?,
      parentName: json['parent_name'] as String?,
      productCount: json['product_count'] as int?,
      isActive: json['is_active'] as bool? ?? true,
    );
  }
}
