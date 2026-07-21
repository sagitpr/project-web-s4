import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/dio_client.dart';
import '../../core/constants/api_constants.dart';

/// Provider for AIApi.
final aiApiProvider = Provider<AIApi>((ref) {
  return AIApi(ref.watch(apiClientProvider));
});

/// AI Services API datasource.
class AIApi {
  final ApiClient _client;

  AIApi(this._client);

  /// Check AI service health.
  Future<ApiResponse> health() async {
    return _client.get(ApiConstants.aiHealth);
  }

  /// Get AI product recommendations for a user.
  Future<ApiResponse> getRecommendations({int? limit}) async {
    return _client.get(
      ApiConstants.aiRecommendations,
      queryParameters: limit != null ? {'limit': limit} : null,
    );
  }

  /// Get similar products.
  Future<ApiResponse> getSimilarProducts(int productId) async {
    final path = ApiConstants.aiSimilarProducts
        .replaceAll('{product_id}', productId.toString());
    return _client.get(path);
  }

  /// Smart search using AI.
  Future<ApiResponse> smartSearch(String query, {int? limit}) async {
    final params = <String, dynamic>{'q': query};
    if (limit != null) params['limit'] = limit;
    return _client.get(ApiConstants.aiSmartSearch, queryParameters: params);
  }

  /// Get AI search suggestions.
  Future<ApiResponse> getSearchSuggestions(String query) async {
    return _client.get(
      ApiConstants.aiSearchSuggestions,
      queryParameters: {'q': query},
    );
  }

  /// Analyze product image using AI vision.
  Future<ApiResponse> analyzeProductImage(String imagePath) async {
    return _client.post(ApiConstants.aiProductVision, data: {
      'image': imagePath,
    });
  }

  /// Detect freshness of a product from image.
  Future<ApiResponse> detectFreshness(String imagePath) async {
    return _client.post(ApiConstants.aiFreshnessDetection, data: {
      'image': imagePath,
    });
  }

  /// Generate product description using AI.
  Future<ApiResponse> generateDescription({
    required String productName,
    String? category,
    String? keywords,
  }) async {
    return _client.post(ApiConstants.aiProductDescription, data: {
      'product_name': productName,
      if (category != null) 'category': category,
      if (keywords != null) 'keywords': keywords,
    });
  }

  /// Analyze product reviews.
  Future<ApiResponse> analyzeReviews(int productId) async {
    return _client.get(
      ApiConstants.aiReviewAnalysis,
      queryParameters: {'product_id': productId},
    );
  }
}
