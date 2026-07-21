import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/dio_client.dart';
import '../../core/constants/api_constants.dart';

/// Provider for ChatApi.
final chatApiProvider = Provider<ChatApi>((ref) {
  return ChatApi(ref.watch(apiClientProvider));
});

/// Chat API datasource.
class ChatApi {
  final ApiClient _client;

  ChatApi(this._client);

  /// Get list of conversations.
  Future<ApiResponse> getConversations({int page = 1}) async {
    return _client.get(
      ApiConstants.conversations,
      queryParameters: {'page': page},
    );
  }

  /// Get messages for a conversation.
  Future<ApiResponse> getMessages(int conversationId, {int page = 1}) async {
    final path = ApiConstants.conversationMessages
        .replaceAll('{conversation_id}', conversationId.toString());
    return _client.get(path, queryParameters: {'page': page});
  }

  /// Send a message.
  Future<ApiResponse> sendMessage({
    required int conversationId,
    required String message,
    String? image,
  }) async {
    return _client.post(ApiConstants.sendMessage, data: {
      'conversation_id': conversationId,
      'message': message,
      if (image != null) 'image': image,
    });
  }

  /// Start a new conversation.
  Future<ApiResponse> startConversation({
    required int recipientId,
    String? initialMessage,
  }) async {
    return _client.post(ApiConstants.startConversation, data: {
      'recipient_id': recipientId,
      if (initialMessage != null) 'initial_message': initialMessage,
    });
  }

  /// Get unread conversation count.
  Future<ApiResponse> getUnreadCount() async {
    return _client.get(ApiConstants.chatUnreadCount);
  }
}
