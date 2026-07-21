import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/dio_client.dart';
import '../../core/constants/api_constants.dart';

/// Provider for RefundApi.
final refundApiProvider = Provider<RefundApi>((ref) {
  return RefundApi(ref.watch(apiClientProvider));
});

/// Refund API datasource.
class RefundApi {
  final ApiClient _client;

  RefundApi(this._client);

  /// Create a refund request.
  Future<ApiResponse> createRefund({
    required int orderId,
    required String reason,
    String? description,
    List<String>? images,
  }) async {
    return _client.post(ApiConstants.refundCreate, data: {
      'order_id': orderId,
      'reason': reason,
      if (description != null) 'description': description,
      if (images != null) 'images': images,
    });
  }

  /// Get my refund requests.
  Future<ApiResponse> getMyRefunds({int page = 1}) async {
    return _client.get(
      ApiConstants.myRefunds,
      queryParameters: {'page': page},
    );
  }

  /// Get refund detail.
  Future<ApiResponse> getRefundDetail(int id) async {
    final path = ApiConstants.refundDetail.replaceAll('{id}', id.toString());
    return _client.get(path);
  }
}
