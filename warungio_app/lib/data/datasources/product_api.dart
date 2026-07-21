import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/dio_client.dart';
import '../../core/constants/api_constants.dart';
import '../models/product_model.dart';

/// Provider for ProductApi.
final productApiProvider = Provider<ProductApi>((ref) {
  return ProductApi(ref.watch(apiClientProvider));
});

/// Product API datasource.
/// Communicates with the Warungio Django REST products endpoints.
class ProductApi {
  final ApiClient _client;

  ProductApi(this._client);

  /// Fetch paginated product list with optional filters.
  Future<ProductListResponse> getProducts({
    int page = 1,
    int pageSize = 20,
    String? search,
    int? categoryId,
    int? storeId,
    String? ordering,
  }) async {
    final queryParams = <String, dynamic>{
      'page': page,
      'page_size': pageSize,
      if (search != null) 'search': search,
      if (categoryId != null) 'category': categoryId,
      if (storeId != null) 'store': storeId,
      if (ordering != null) 'ordering': ordering,
    };

    final response = await _client.get(
      ApiConstants.products,
      queryParameters: queryParams,
    );

    final data = response.data as Map<String, dynamic>? ?? {};
    final List<dynamic> results = data['results'] as List<dynamic>? ?? [];
    final products = results
        .map((e) => ProductModel.fromJson(e as Map<String, dynamic>))
        .toList();
    final total = data['count'] as int? ?? products.length;

    return ProductListResponse(products: products, total: total);
  }

  /// Fetch featured products.
  Future<ProductListResponse> getFeaturedProducts({
    int page = 1,
    int pageSize = 20,
  }) async {
    final response = await _client.get(
      ApiConstants.featuredProducts,
      queryParameters: {'page': page, 'page_size': pageSize},
    );
    final data = response.data as Map<String, dynamic>? ?? {};
    final List<dynamic> results = data['results'] as List<dynamic>? ?? [];
    final products = results
        .map((e) => ProductModel.fromJson(e as Map<String, dynamic>))
        .toList();
    return ProductListResponse(
        products: products, total: data['count'] as int? ?? products.length);
  }

  /// Fetch a single product by ID.
  Future<ProductModel> getProductById(int id) async {
    final path = ApiConstants.productDetail.replaceAll('{id}', id.toString());
    final response = await _client.get(path);
    return ProductModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Fetch a single product by slug.
  Future<ProductModel> getProductBySlug(String slug) async {
    final response = await _client.get('/products/$slug/');
    return ProductModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Fetch products by store.
  Future<ProductListResponse> getStoreProducts({
    required int storeId,
    int page = 1,
    int pageSize = 20,
  }) async {
    final path =
        ApiConstants.storeProductsList.replaceAll('{store_id}', storeId.toString());
    final response = await _client.get(
      path,
      queryParameters: {'page': page, 'page_size': pageSize},
    );
    final data = response.data as Map<String, dynamic>? ?? {};
    final List<dynamic> results = data['results'] as List<dynamic>? ?? [];
    final products = results
        .map((e) => ProductModel.fromJson(e as Map<String, dynamic>))
        .toList();
    return ProductListResponse(
        products: products, total: data['count'] as int? ?? products.length);
  }

  /// Fetch product categories.
  Future<ApiResponse> getCategories() async {
    return _client.get(ApiConstants.categoryList);
  }

  /// Search products with query.
  Future<ProductListResponse> searchProducts({
    required String query,
    int page = 1,
    int pageSize = 20,
  }) async {
    return getProducts(search: query, page: page, pageSize: pageSize);
  }

  /// Fetch promotional products.
  Future<ProductListResponse> getPromoProducts({
    int page = 1,
    int pageSize = 20,
  }) async {
    final response = await _client.get(
      ApiConstants.promoList,
      queryParameters: {'page': page, 'page_size': pageSize},
    );
    final data = response.data as Map<String, dynamic>? ?? {};
    final List<dynamic> results = data['results'] as List<dynamic>? ?? [];
    final products = results
        .map((e) => ProductModel.fromJson(e as Map<String, dynamic>))
        .toList();
    return ProductListResponse(
        products: products, total: data['count'] as int? ?? products.length);
  }

  /// Get my products (seller).
  Future<ProductListResponse> getMyProducts({int page = 1, int pageSize = 20}) async {
    final response = await _client.get(
      ApiConstants.myProducts,
      queryParameters: {'page': page, 'page_size': pageSize},
    );
    final data = response.data as Map<String, dynamic>? ?? {};
    final List<dynamic> results = data['results'] as List<dynamic>? ?? [];
    final products = results
        .map((e) => ProductModel.fromJson(e as Map<String, dynamic>))
        .toList();
    return ProductListResponse(
        products: products, total: data['count'] as int? ?? products.length);
  }

  /// Create a new product.
  Future<ApiResponse> createProduct(Map<String, dynamic> data) async {
    return _client.post(ApiConstants.createProduct, data: data);
  }

  /// Update a product.
  Future<ApiResponse> updateProduct(int id, Map<String, dynamic> data) async {
    final path = ApiConstants.productManage.replaceAll('{id}', id.toString());
    return _client.patch(path, data: data);
  }

  /// Delete a product.
  Future<ApiResponse> deleteProduct(int id) async {
    final path = ApiConstants.productManage.replaceAll('{id}', id.toString());
    return _client.delete(path);
  }

  /// Toggle favorite on a product.
  Future<ApiResponse> toggleFavorite(int productId) async {
    final path = ApiConstants.productFavorite.replaceAll(
        '{product_id}', productId.toString());
    return _client.post(path);
  }

  /// Get my favorites.
  Future<ProductListResponse> getMyFavorites({int page = 1, int pageSize = 20}) async {
    final response = await _client.get(
      ApiConstants.myFavorites,
      queryParameters: {'page': page, 'page_size': pageSize},
    );
    final data = response.data as Map<String, dynamic>? ?? {};
    final List<dynamic> results = data['results'] as List<dynamic>? ?? [];
    final products = results
        .map((e) => ProductModel.fromJson(e as Map<String, dynamic>))
        .toList();
    return ProductListResponse(
        products: products, total: data['count'] as int? ?? products.length);
  }

  /// Get recently viewed products.
  Future<ApiResponse> getRecentlyViewed() async {
    return _client.get(ApiConstants.recentlyViewed);
  }

  /// Search suggestions (autocomplete).
  Future<ApiResponse> getSearchSuggestions(String query) async {
    return _client.get(
      ApiConstants.searchSuggestions,
      queryParameters: {'q': query},
    );
  }
}

/// Wrapper for paginated product list response.
class ProductListResponse {
  final List<ProductModel> products;
  final int total;

  const ProductListResponse({
    required this.products,
    this.total = 0,
  });
}
