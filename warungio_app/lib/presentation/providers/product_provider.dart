import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/models/product_model.dart';
import '../../data/repositories/product_repository.dart';

/// Product list state.
class ProductListState {
  final List<ProductModel> products;
  final bool isLoading;
  final String? errorMessage;
  final int currentPage;
  final bool hasReachedEnd;
  final String? searchQuery;
  final int? selectedCategoryId;

  const ProductListState({
    this.products = const [],
    this.isLoading = false,
    this.errorMessage,
    this.currentPage = 1,
    this.hasReachedEnd = false,
    this.searchQuery,
    this.selectedCategoryId,
  });

  ProductListState copyWith({
    List<ProductModel>? products,
    bool? isLoading,
    String? errorMessage,
    int? currentPage,
    bool? hasReachedEnd,
    String? searchQuery,
    int? selectedCategoryId,
  }) {
    return ProductListState(
      products: products ?? this.products,
      isLoading: isLoading ?? this.isLoading,
      errorMessage: errorMessage,
      currentPage: currentPage ?? this.currentPage,
      hasReachedEnd: hasReachedEnd ?? this.hasReachedEnd,
      searchQuery: searchQuery ?? this.searchQuery,
      selectedCategoryId: selectedCategoryId ?? this.selectedCategoryId,
    );
  }
}

/// StateNotifier for product list with pagination.
class ProductListNotifier extends StateNotifier<ProductListState> {
  final ProductRepository _repository;

  ProductListNotifier({required ProductRepository repository})
      : _repository = repository,
        super(const ProductListState());

  /// Fetch products with optional filters.
  Future<void> fetchProducts({
    bool refresh = false,
    String? search,
    int? categoryId,
  }) async {
    if (refresh) {
      state = const ProductListState();
    }

    if (state.isLoading || state.hasReachedEnd) return;

    state = state.copyWith(
      isLoading: true,
      errorMessage: null,
      searchQuery: search ?? state.searchQuery,
      selectedCategoryId: categoryId ?? state.selectedCategoryId,
    );

    try {
      final page = refresh ? 1 : state.currentPage;
      final response = await _repository.getProducts(
        page: page,
        search: search ?? state.searchQuery,
        categoryId: categoryId ?? state.selectedCategoryId,
      );

      final newProducts = refresh ? response.products : [...state.products, ...response.products];

      state = state.copyWith(
        products: newProducts,
        isLoading: false,
        currentPage: page + 1,
        hasReachedEnd: newProducts.length >= response.total,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        errorMessage: 'Gagal memuat produk. Tarik untuk refresh.',
      );
    }
  }

  /// Search products.
  Future<void> searchProducts(String query) async {
    state = const ProductListState(searchQuery: query);
    await fetchProducts(search: query);
  }

  /// Refresh product list.
  Future<void> refresh() async {
    await fetchProducts(refresh: true);
  }
}

/// Provider for product list state.
final productListProvider =
    StateNotifierProvider<ProductListNotifier, ProductListState>((ref) {
  final repository = ref.watch(productRepositoryProvider);
  return ProductListNotifier(repository: repository);
});

/// Provider for a single product by ID.
final productDetailProvider = FutureProvider.family<ProductModel, int>((ref, id) async {
  final repository = ref.watch(productRepositoryProvider);
  return repository.getProductById(id);
});
