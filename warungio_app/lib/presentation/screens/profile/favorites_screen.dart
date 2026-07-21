import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../widgets/common/card_widgets.dart';
import '../../widgets/common/error_widget.dart';
import '../../../data/models/product_model.dart';
import '../../../data/datasources/product_api.dart';
import '../../../core/routing/route_names.dart' as routes;

/// Provider for favorite products list.
final favoritesProvider = FutureProvider.autoDispose<List<ProductModel>>((ref) {
  final api = ref.watch(productApiProvider);
  return api.getMyFavorites(pageSize: 50).then((r) => r.products);
});

class FavoritesScreen extends ConsumerWidget {
  const FavoritesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final favoritesAsync = ref.watch(favoritesProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Favorit')),
      body: favoritesAsync.when(
        data: (products) {
          if (products.isEmpty) {
            return EmptyStateWidget(
              message: 'Belum ada produk favorit',
              subtitle: 'Tambahkan produk favorit Anda dengan menekan ikon hati',
              icon: Icons.favorite_outline_rounded,
              action: FilledButton(
                onPressed: () => context.push(routes.RouteNames.marketplace),
                child: const Text('Jelajahi Produk'),
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(favoritesProvider),
            child: GridView.builder(
              padding: const EdgeInsets.all(16),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                mainAxisSpacing: 12,
                crossAxisSpacing: 12,
                childAspectRatio: 0.7,
              ),
              itemCount: products.length,
              itemBuilder: (context, index) {
                final product = products[index];
                return Stack(
                  children: [
                    ProductCard(
                      product: product,
                      isGridView: true,
                      onTap: () => context.push(
                        routes.RouteNames.productDetail.replaceAll(
                            ':id', product.id.toString()),
                      ),
                    ),
                    Positioned(
                      top: 4,
                      right: 4,
                      child: IconButton(
                        icon: Icon(Icons.favorite_rounded,
                            color: Colors.red[400], size: 22),
                        onPressed: () async {
                          await ref
                              .read(productApiProvider)
                              .toggleFavorite(product.id);
                          ref.invalidate(favoritesProvider);
                        },
                        style: IconButton.styleFrom(
                          backgroundColor: Colors.white.withOpacity(0.9),
                          padding: const EdgeInsets.all(4),
                          minimumSize: const Size(32, 32),
                        ),
                      ),
                    ),
                  ],
                );
              },
            ),
          );
        },
        loading: () =>
            const AppLoadingWidget(message: 'Memuat favorit...'),
        error: (_, __) => AppErrorWidget(
          message: 'Gagal memuat favorit',
          onRetry: () => ref.invalidate(favoritesProvider),
        ),
      ),
    );
  }
}
