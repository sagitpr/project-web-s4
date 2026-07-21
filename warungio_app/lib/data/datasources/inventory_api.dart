import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/dio_client.dart';
import '../../core/constants/api_constants.dart';

/// Provider for InventoryApi.
final inventoryApiProvider = Provider<InventoryApi>((ref) {
  return InventoryApi(ref.watch(apiClientProvider));
});

/// Inventory Management API datasource.
class InventoryApi {
  final ApiClient _client;

  InventoryApi(this._client);

  /// Search master products.
  Future<ApiResponse> searchMasterProducts({
    required String query,
    int page = 1,
  }) async {
    return _client.get(
      ApiConstants.inventoryMasterProducts,
      queryParameters: {'search': query, 'page': page},
    );
  }

  /// Lookup barcode.
  Future<ApiResponse> lookupBarcode(String barcode) async {
    return _client.get(
      ApiConstants.inventoryBarcodeLookup,
      queryParameters: {'barcode': barcode},
    );
  }

  /// Get list of batches.
  Future<ApiResponse> getBatches({
    int page = 1,
    int? productId,
    String? status,
  }) async {
    final params = <String, dynamic>{'page': page};
    if (productId != null) params['product'] = productId;
    if (status != null) params['status'] = status;
    return _client.get(ApiConstants.inventoryBatches, queryParameters: params);
  }

  /// Get batch detail.
  Future<ApiResponse> getBatchDetail(int batchId) async {
    final path = ApiConstants.inventoryBatchDetail
        .replaceAll('{id}', batchId.toString());
    return _client.get(path);
  }

  /// Record stock out.
  Future<ApiResponse> stockOut({
    required int batchId,
    required int quantity,
    String? reason,
  }) async {
    return _client.post(ApiConstants.inventoryStockOut, data: {
      'batch_id': batchId,
      'quantity': quantity,
      if (reason != null) 'reason': reason,
    });
  }

  /// Start AI scan session.
  Future<ApiResponse> startAiScan() async {
    return _client.post(ApiConstants.aiScanStart);
  }

  /// Get AI scan sessions.
  Future<ApiResponse> getAiScanSessions({int page = 1}) async {
    return _client.get(
      ApiConstants.aiScanSessions,
      queryParameters: {'page': page},
    );
  }
}
