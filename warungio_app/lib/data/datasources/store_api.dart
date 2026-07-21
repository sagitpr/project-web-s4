import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/dio_client.dart';
import '../../core/constants/api_constants.dart';
import '../models/store_model.dart';

/// Provider for StoreApi.
final storeApiProvider = Provider<StoreApi>((ref) {
  return StoreApi(ref.watch(apiClientProvider));
});

/// Store API datasource.
class StoreApi {
  final ApiClient _client;

  StoreApi(this._client);

  /// Get list of stores with optional filters.
  Future<ApiResponse> getStores({
    int page = 1,
    String? search,
    int? categoryId,
    String? city,
  }) async {
    final params = <String, dynamic>{'page': page};
    if (search != null) params['search'] = search;
    if (categoryId != null) params['category'] = categoryId;
    if (city != null) params['city'] = city;
    return _client.get(ApiConstants.stores, queryParameters: params);
  }

  /// Get store categories.
  Future<ApiResponse> getCategories() async {
    return _client.get(ApiConstants.storeCategories);
  }

  /// Get current user's store (seller).
  Future<ApiResponse> getMyStore() async {
    return _client.get(ApiConstants.myStore);
  }

  /// Update my store.
  Future<ApiResponse> updateMyStore(Map<String, dynamic> data) async {
    return _client.patch(ApiConstants.myStore, data: data);
  }

  /// Create a new store.
  Future<ApiResponse> createStore(Map<String, dynamic> data) async {
    return _client.post(ApiConstants.createStore, data: data);
  }

  /// Get store detail by ID.
  Future<ApiResponse> getStoreDetail(int storeId) async {
    final path = ApiConstants.storeDetail.replaceAll('{id}', storeId.toString());
    return _client.get(path);
  }

  /// Get store detail by slug.
  Future<ApiResponse> getStoreBySlug(String slug) async {
    final path = ApiConstants.storeDetailSlug.replaceAll('{slug}', slug);
    return _client.get(path);
  }

  /// Get products for a specific store.
  Future<ApiResponse> getStoreProducts(int storeId, {int page = 1}) async {
    final path =
        ApiConstants.storeProductsList.replaceAll('{store_id}', storeId.toString());
    return _client.get(path, queryParameters: {'page': page});
  }

  /// Toggle follow/unfollow a store.
  Future<ApiResponse> toggleFollow(int storeId) async {
    final path =
        ApiConstants.storeFollow.replaceAll('{store_id}', storeId.toString());
    return _client.post(path);
  }

  /// Get followers of a store.
  Future<ApiResponse> getStoreFollowers(int storeId) async {
    final path =
        ApiConstants.storeFollowers.replaceAll('{store_id}', storeId.toString());
    return _client.get(path);
  }

  /// Get stores followed by current user.
  Future<ApiResponse> getMyFollowedStores() async {
    return _client.get(ApiConstants.myFollowedStores);
  }
}
