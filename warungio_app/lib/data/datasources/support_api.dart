import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/dio_client.dart';
import '../../core/constants/api_constants.dart';

/// Provider for SupportApi.
final supportApiProvider = Provider<SupportApi>((ref) {
  return SupportApi(ref.watch(apiClientProvider));
});

/// Support & Help Center API datasource.
class SupportApi {
  final ApiClient _client;

  SupportApi(this._client);

  /// Get help categories.
  Future<ApiResponse> getHelpCategories() async {
    return _client.get(ApiConstants.helpCategories);
  }

  /// Get help articles.
  Future<ApiResponse> getHelpArticles({int page = 1}) async {
    return _client.get(
      ApiConstants.helpArticles,
      queryParameters: {'page': page},
    );
  }

  /// Get FAQs.
  Future<ApiResponse> getFAQs() async {
    return _client.get(ApiConstants.faqs);
  }

  /// Search support content.
  Future<ApiResponse> search(String query) async {
    return _client.get(
      ApiConstants.supportSearch,
      queryParameters: {'q': query},
    );
  }

  /// Get support tickets.
  Future<ApiResponse> getTickets({int page = 1}) async {
    return _client.get(
      ApiConstants.supportTickets,
      queryParameters: {'page': page},
    );
  }

  /// Create a support ticket.
  Future<ApiResponse> createTicket({
    required String subject,
    required String message,
    String? category,
    List<String>? images,
  }) async {
    return _client.post(ApiConstants.supportTickets, data: {
      'subject': subject,
      'message': message,
      if (category != null) 'category': category,
      if (images != null) 'images': images,
    });
  }

  /// AI-powered chat with support.
  Future<ApiResponse> aiChat(String message) async {
    return _client.post(ApiConstants.supportAiChat, data: {
      'message': message,
    });
  }
}
