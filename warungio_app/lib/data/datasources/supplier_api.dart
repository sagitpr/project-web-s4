import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/dio_client.dart';
import '../../core/constants/api_constants.dart';

/// Provider for SupplierApi.
final supplierApiProvider = Provider<SupplierApi>((ref) {
  return SupplierApi(ref.watch(apiClientProvider));
});

/// Supplier Management API datasource.
class SupplierApi {
  final ApiClient _client;

  SupplierApi(this._client);

  /// Get supplier categories.
  Future<ApiResponse> getCategories() async {
    return _client.get(ApiConstants.supplierCategories);
  }

  /// Get list of suppliers.
  Future<ApiResponse> getSuppliers({int page = 1}) async {
    return _client.get(
      ApiConstants.suppliers,
      queryParameters: {'page': page},
    );
  }

  /// Get supplier detail.
  Future<ApiResponse> getSupplierDetail(int id) async {
    final path =
        ApiConstants.supplierDetail.replaceAll('{id}', id.toString());
    return _client.get(path);
  }

  /// Get products for a supplier.
  Future<ApiResponse> getSupplierProducts(int id, {int page = 1}) async {
    final path =
        ApiConstants.supplierProducts.replaceAll('{id}', id.toString());
    return _client.get(path, queryParameters: {'page': page});
  }
}
