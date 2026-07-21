import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../widgets/common/card_widgets.dart';
import '../../widgets/common/error_widget.dart';
import '../../../data/models/product_model.dart';
import '../../../data/datasources/product_api.dart';
import '../../../data/datasources/ai_api.dart';
import '../../../core/network/dio_client.dart';
import '../../../core/routing/route_names.dart' as routes;

/// Provider for search results.
final searchResultsProvider =
    FutureProvider.autoDispose.family<List<ProductModel>, String>((ref, query) {
  final api = ref.watch(productApiProvider);
  return api.searchProducts(query: query, pageSize: 20).then((r) => r.products);
});

/// Provider for AI search suggestions.
final searchSuggestionsProvider =
    FutureProvider.autoDispose.family<List<String>, String>((ref, query) {
  if (query.length < 2) return Future.value(<String>[]);
  return ref
      .watch(aiApiProvider)
      .getSearchSuggestions(query)
      .then((r) {
        final data = r.data;
        if (data is Map<String, dynamic>) {
          final suggestions = data['suggestions'] as List<dynamic>? ??
              data['results'] as List<dynamic>? ??
              [];
          return suggestions.map((e) => e.toString()).toList();
        }
        return <String>[];
      })
      .catchError((_) => <String>[]);
});

class SearchScreen extends ConsumerStatefulWidget {
  const SearchScreen({super.key});

  @override
  ConsumerState<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends ConsumerState<SearchScreen> {
  final _searchController = TextEditingController();
  bool _isSearching = false;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final query = _searchController.text.trim();
    final resultsAsync = ref.watch(searchResultsProvider(query));
    final suggestionsAsync = ref.watch(searchSuggestionsProvider(query));

    return Scaffold(
      appBar: AppBar(
        title: TextField(
          controller: _searchController,
          autofocus: true,
          decoration: InputDecoration(
            hintText: 'Cari produk...',
            border: InputBorder.none,
            suffixIcon: _searchController.text.isNotEmpty
                ? IconButton(
                    icon: const Icon(Icons.clear_rounded),
                    onPressed: () {
                      _searchController.clear();
                      setState(() => _isSearching = false);
                    },
                  )
                : null,
          ),
          onChanged: (v) {
            setState(() {
              _isSearching = v.isNotEmpty;
            });
          },
          onSubmitted: (v) {
            setState(() => _isSearching = true);
          },
        ),
      ),
      body: _isSearching
          ? resultsAsync.when(
              data: (products) {
                if (products.isEmpty) {
                  return EmptyStateWidget(
                    message: 'Produk tidak ditemukan',
                    subtitle: 'Coba kata kunci lain',
                    icon: Icons.search_off_rounded,
                  );
                }
                return ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: products.length,
                  itemBuilder: (context, index) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: ProductCard(
                      product: products[index],
                      onTap: () => context.push(
                        routes.RouteNames.productDetail.replaceAll(
                          ':id',
                          products[index].id.toString(),
                        ),
                      ),
                    ),
                  ),
                );
              },
              loading: () => const AppLoadingWidget(
                  message: 'Mencari produk...'),
              error: (_, __) => AppErrorWidget(
                message: 'Gagal mencari produk',
                onRetry: () => ref.invalidate(
                    searchResultsProvider(query)),
              ),
            )
          : suggestionsAsync.when(
              data: (suggestions) {
                if (suggestions.isEmpty) {
                  return _buildRecentSearches(theme);
                }
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                      child: Text('Saran Pencarian',
                          style: theme.textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.bold)),
                    ),
                    ...suggestions.map(
                      (s) => ListTile(
                        leading: const Icon(Icons.history_rounded),
                        title: Text(s),
                        onTap: () {
                          _searchController.text = s;
                          setState(() => _isSearching = true);
                        },
                      ),
                    ),
                  ],
                );
              },
              loading: () => const SizedBox.shrink(),
              error: (_, __) => _buildRecentSearches(theme),
            ),
    );
  }

  Widget _buildRecentSearches(ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Pencarian Terakhir',
              style: theme.textTheme.titleSmall
                  ?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Text(
            'Belum ada pencarian',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.5),
            ),
          ),
        ],
      ),
    );
  }
}
