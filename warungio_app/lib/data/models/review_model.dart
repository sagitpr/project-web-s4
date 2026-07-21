/// Model representing a product review from the backend.
class ReviewModel {
  final int id;
  final int? userId;
  final String? userName;
  final String? userPhoto;
  final int productId;
  final String? productName;
  final int rating;
  final String? comment;
  final List<String>? images;
  final String? sellerReply;
  final DateTime createdAt;
  final DateTime? updatedAt;

  ReviewModel({
    required this.id,
    this.userId,
    this.userName,
    this.userPhoto,
    required this.productId,
    this.productName,
    required this.rating,
    this.comment,
    this.images,
    this.sellerReply,
    required this.createdAt,
    this.updatedAt,
  });

  factory ReviewModel.fromJson(Map<String, dynamic> json) {
    return ReviewModel(
      id: json['id'] as int,
      userId: json['user'] as int? ?? json['user_id'] as int?,
      userName: json['user_name'] as String? ?? json['username'] as String?,
      userPhoto: json['user_photo'] as String? ?? json['profile_photo'] as String?,
      productId: json['product'] as int? ?? json['product_id'] as int? ?? 0,
      productName: json['product_name'] as String?,
      rating: json['rating'] as int? ?? 5,
      comment: json['comment'] as String? ?? json['review'] as String?,
      images: (json['images'] as List<dynamic>?)
          ?.map((e) => e.toString())
          .toList(),
      sellerReply: json['seller_reply'] as String?,
      createdAt: DateTime.parse(
          json['created_at'] as String? ?? DateTime.now().toIso8601String()),
      updatedAt: json['updated_at'] != null
          ? DateTime.tryParse(json['updated_at'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'rating': rating,
      'comment': comment,
    };
  }
}
