import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../widgets/common/card_widgets.dart';
import '../../widgets/common/error_widget.dart';
import '../../../data/models/store_model.dart';
import '../../../data/models/product_model.dart';
import '../../../data/datasources/store_api.dart';
import '../../../data/datasources/product_api.dart';
import '../../../core/routing/route_names.dart' as routes;
import '../../../core/network/dio_client.dart';

/// Provider for store detail.
final storeDetailProvider =
    FutureProvider.autoDispose.family<StoreModel, int>((ref, storeId) {
  final api = ref.watch(storeApiProvider);
  return api.getStoreDetail(storeId).then((r) {
    final data = r.data;
    if (data is Map<String, dynamic>) {
      return StoreModel.fromJson(data);
    }
    throw Exception('Invalid response format');
  });
});

/// Provider for store products.
final storeProductsProvider =
    FutureProvider.autoDispose.family<List<ProductModel>, int>((ref, storeId) {
  final api = ref.watch(productApiProvider);
  return api.getStoreProducts(storeId: storeId, pageSize: 50).then((r) => r.products);
});

class StoreDetailScreen extends ConsumerWidget {
  final int storeId;

  const StoreDetailScreen({super.key, required this.storeId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final storeAsync = ref.watch(storeDetailProvider(storeId));
    final productsAsync = ref.watch(storeProductsProvider(storeId));

    return storeAsync.when(
      data: (store) => Scaffold(
        body: CustomScrollView(
          slivers: [
            // ── Sliver AppBar ──
            SliverAppBar(
              expandedHeight: 200,
              pinned: true,
              flexibleSpace: FlexibleSpaceBar(
                background: Container(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        theme.colorScheme.primary,
                        theme.colorScheme.primary.withOpacity(0.7),
                      ],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                  ),
                  child: Center(
                    child: Text(
                      store.storeName[0].toUpperCase(),
                      style: const TextStyle(
                          fontSize: 72,
                          fontWeight: FontWeight.bold,
                          color: Colors.white30),
                    ),
                  ),
                ),
              ),
              title: Text(store.storeName),
            ),

            // ── Store Info ──
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        CircleAvatar(
                          radius: 32,
                          backgroundColor:
                              theme.colorScheme.primary.withOpacity(0.1),
                          child: Text(
                            store.storeName.isNotEmpty
                                ? store.storeName[0].toUpperCase()
                                : 'T',
                            style: theme.textTheme.headlineMedium?.copyWith(
                              color: theme.colorScheme.primary,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(store.storeName,
                                  style: theme.textTheme.titleLarge
                                      ?.copyWith(fontWeight: FontWeight.bold)),
                              if (store.city != null)
                                Text(store.city!,
                                    style: theme.textTheme.bodySmall?.copyWith(
                                        color: theme.colorScheme.onSurface
                                            .withOpacity(0.6))),
                            ],
                          ),
                        ),
                        // ── Follow Button ──
                        FilledButton.tonal(
                          onPressed: () async {
                            await ref
                                .read(storeApiProvider)
                                .toggleFollow(storeId);
                            ref.invalidate(storeDetailProvider(storeId));
                          },
                          child: Text(store.isFollowed ? 'Mengikuti' : 'Ikuti'),
                        ),
                      ],
                    ),

                    // ── Stats Row ──
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        if (store.ratingAvg != null) ...[
                          Icon(Icons.star_rounded,
                              color: Colors.amber[700], size: 20),
                          const SizedBox(width: 4),
                          Text(store.ratingAvg!.toStringAsFixed(1),
                              style: theme.textTheme.titleSmall
                                  ?.copyWith(fontWeight: FontWeight.w600)),
                          const SizedBox(width: 16),
                        ],
                        if (store.productCount != null)
                          _StatText(
                              '${store.productCount}', 'Produk'),
                        if (store.followerCount != null) ...[
                          const SizedBox(width: 16),
                          _StatText(
                              '${store.followerCount}', 'Pengikut'),
                        ],
                      ],
                    ),

                    // ── Description ──
                    if (store.description != null &&
                        store.description!.isNotEmpty) ...[
                      const SizedBox(height: 16),
                      Text(store.description!,
                          style: theme.textTheme.bodyMedium?.copyWith(
                              color: theme.colorScheme.onSurface
                                  .withOpacity(0.7))),
                    ],
                  ],
                ),
              ),
            ),

            // ── Products Header ──
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
                child: Text('Produk',
                    style: theme.textTheme.titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold)),
              ),
            ),

            // ── Products Grid ──
            productsAsync.when(
              data: (products) {
                if (products.isEmpty) {
                  return const SliverToBoxAdapter(
                    child: Padding(
                      padding: EdgeInsets.all(32),
                      child: Center(child: Text('Belum ada produk')),
                    ),
                  );
                }
                return SliverGrid(
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    mainAxisSpacing: 8,
                    crossAxisSpacing: 8,
                    childAspectRatio: 0.7,
                  ),
                  delegate: SliverChildBuilderDelegate(
                    (context, index) => ProductCard(
                      product: products[index],
                      isGridView: true,
                      onTap: () => context.push(
                        routes.RouteNames.productDetail.replaceAll(
                          ':id', products[index].id.toString()),
                      ),
                    ),
                    childCount: products.length,
                  ),
                );
              },
              loading: () => const SliverToBoxAdapter(
                child: Center(
                    child: Padding(
                  padding: EdgeInsets.all(32),
                  child: CircularProgressIndicator(),
                )),
              ),
              error: (_, __) => SliverToBoxAdapter(
                child: AppErrorWidget(
                  message: 'Gagal memuat produk',
                  onRetry: () =>
                      ref.invalidate(storeProductsProvider(storeId)),
                ),
              ),
            ),
            const SliverToBoxAdapter(child: SizedBox(height: 32)),
          ],
        ),
      ),
      loading: () => const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      ),
      error: (_, __) => Scaffold(
        appBar: AppBar(),
        body: AppErrorWidget(
          message: 'Gagal memuat detail toko',
          onRetry: () => ref.invalidate(storeDetailProvider(storeId)),
        ),
      ),
    );
  }
}

class _StatText extends StatelessWidget {
  final String value;
  final String label;
  const _StatText(this.value, this.label);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(value,
            style: theme.textTheme.titleSmall
                ?.copyWith(fontWeight: FontWeight.bold)),
        Text(label,
            style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.6))),
      ],
    );
  }
}
