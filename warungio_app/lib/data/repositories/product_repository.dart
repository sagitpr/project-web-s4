import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../datasources/product_api.dart';
import '../models/product_model.dart';

/// Repository for product-related operations.
class ProductRepository {
  final ProductApi _productApi;

  ProductRepository({required ProductApi productApi}) : _productApi = productApi;

  /// Fetch paginated product list.
  Future<ProductListResponse> getProducts({
    int page = 1,
    int pageSize = 20,
    String? search,
    int? categoryId,
    int? storeId,
    String? sortBy,
  }) {
    return _productApi.getProducts(
      page: page,
      pageSize: pageSize,
      search: search,
      categoryId: categoryId,
      storeId: storeId,
      sortBy: sortBy,
    );
  }

  /// Fetch a single product by ID.
  Future<ProductModel> getProductById(int id) {
    return _productApi.getProductById(id);
  }

  /// Fetch a single product by slug.
  Future<ProductModel> getProductBySlug(String slug) {
    return _productApi.getProductBySlug(slug);
  }

  /// Search products with query.
  Future<ProductListResponse> searchProducts({
    required String query,
    int page = 1,
    int pageSize = 20,
  }) {
    return _productApi.searchProducts(query: query, page: page, pageSize: pageSize);
  }

  /// Fetch product categories.
  Future<List<dynamic>> getCategories() {
    return _productApi.getCategories();
  }

  /// Fetch promotional products.
  Future<ProductListResponse> getPromoProducts({int page = 1, int pageSize = 20}) {
    return _productApi.getPromoProducts(page: page, pageSize: pageSize);
  }
}

// Riverpod provider
final productRepositoryProvider = Provider<ProductRepository>((ref) {
  final productApi = ref.watch(productApiProvider);
  return ProductRepository(productApi: productApi);
});
