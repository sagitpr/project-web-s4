import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../widgets/common/card_widgets.dart';
import '../../widgets/common/error_widget.dart';
import '../../../core/routing/route_names.dart';
import '../../../data/datasources/product_api.dart';
import '../../../data/datasources/ai_api.dart';
import '../../../core/network/dio_client.dart';

/// Home screen provider state.
final homeProductsProvider = FutureProvider.autoDispose<List<ProductModel>>((ref) {
  final api = ref.watch(productApiProvider);
  return api.getFeaturedProducts(pageSize: 10).then((r) => r.products);
});

final homeRecommendationsProvider =
    FutureProvider.autoDispose<List<ProductModel>>((ref) {
  final api = ref.watch(aiApiProvider);
  return api.getRecommendations(limit: 10).then((r) {
    // Parse recommendations from ApiResponse
    final data = r.data;
    if (data is Map<String, dynamic>) {
      final results = data['results'] as List<dynamic>? ?? data['data'] as List<dynamic>? ?? [];
      return results
          .map((e) => ProductModel.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    return <ProductModel>[];
  });
});

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final featuredAsync = ref.watch(homeProductsProvider);
    final recommendationsAsync = ref.watch(homeRecommendationsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Warungio'),
        actions: [
          IconButton(
            icon: const Icon(Icons.search_rounded),
            onPressed: () => context.push(RouteNames.search),
          ),
          IconButton(
            icon: const Icon(Icons.notifications_outlined),
            onPressed: () => context.push(RouteNames.notifications),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(homeProductsProvider);
          ref.invalidate(homeRecommendationsProvider);
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // ── Search Bar ──
            InkWell(
              onTap: () => context.push(RouteNames.search),
              borderRadius: BorderRadius.circular(12),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                decoration: BoxDecoration(
                  color: theme.colorScheme.surface,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: theme.colorScheme.outline.withOpacity(0.3)),
                ),
                child: Row(
                  children: [
                    Icon(Icons.search_rounded,
                        color: theme.colorScheme.onSurface.withOpacity(0.4)),
                    const SizedBox(width: 12),
                    Text(
                      'Cari produk, toko, atau kategori...',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.colorScheme.onSurface.withOpacity(0.4),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // ── Categories Grid ──
            // TODO: Connect to actual categories API
            Text('Kategori', style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            )),
            const SizedBox(height: 12),
            SizedBox(
              height: 100,
              child: ListView(
                scrollDirection: Axis.horizontal,
                children: [
                  _CategoryChip(
                    icon: Icons.restaurant_rounded,
                    label: 'Makanan',
                    onTap: () => context.push('${RouteNames.categories}?category=makanan'),
                  ),
                  _CategoryChip(
                    icon: Icons.local_drink_rounded,
                    label: 'Minuman',
                    onTap: () => context.push('${RouteNames.categories}?category=minuman'),
                  ),
                  _CategoryChip(
                    icon: Icons.produce_rounded,
                    label: 'Sayur & Buah',
                    onTap: () => context.push('${RouteNames.categories}?category=sayur'),
                  ),
                  _CategoryChip(
                    icon: Icons.kitchen_rounded,
                    label: 'Bumbu Dapur',
                    onTap: () => context.push('${RouteNames.categories}?category=bumbu'),
                  ),
                  _CategoryChip(
                    icon: Icons.egg_rounded,
                    label: 'Protein',
                    onTap: () => context.push('${RouteNames.categories}?category=protein'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // ── Featured Products ──
            Text('Produk Unggulan', style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            )),
            const SizedBox(height: 12),
            featuredAsync.when(
              data: (products) {
                if (products.isEmpty) {
                  return const SizedBox.shrink();
                }
                return SizedBox(
                  height: 220,
                  child: ListView.separated(
                    scrollDirection: Axis.horizontal,
                    itemCount: products.length,
                    separatorBuilder: (_, __) => const SizedBox(width: 12),
                    itemBuilder: (context, index) {
                      final product = products[index];
                      return SizedBox(
                        width: 160,
                        child: ProductCard(
                          product: product,
                          isGridView: true,
                          onTap: () => context.push(
                            RouteNames.productDetail.replaceAll(':id', product.id.toString()),
                          ),
                        ),
                      );
                    },
                  ),
                );
              },
              loading: () => const SizedBox(
                height: 220,
                child: Center(child: CircularProgressIndicator()),
              ),
              error: (_, __) => const SizedBox.shrink(),
            ),
            const SizedBox(height: 24),

            // ── Promo Carousel ──
            // TODO: Connect to promos API
            Container(
              height: 160,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(16),
                gradient: LinearGradient(
                  colors: [
                    theme.colorScheme.primary,
                    theme.colorScheme.primary.withOpacity(0.7),
                  ],
                ),
              ),
              child: Center(
                child: Text(
                  'Promo Spesial',
                  style: theme.textTheme.headlineSmall?.copyWith(
                    color: theme.colorScheme.onPrimary,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 24),

            // ── Recommendations ──
            Text('Rekomendasi Untukmu', style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            )),
            const SizedBox(height: 12),
            recommendationsAsync.when(
              data: (products) {
                if (products.isEmpty) {
                  return const AppEmptyState(message: 'Belum ada rekomendasi');
                }
                return ListView.separated(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: products.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (context, index) => ProductCard(
                    product: products[index],
                    onTap: () => context.push(
                      RouteNames.productDetail.replaceAll(':id', products[index].id.toString()),
                    ),
                  ),
                );
              },
              loading: () => const Padding(
                padding: EdgeInsets.all(32),
                child: Center(child: CircularProgressIndicator()),
              ),
              error: (_, __) => AppErrorWidget(
                message: 'Gagal memuat rekomendasi',
                onRetry: () => ref.invalidate(homeRecommendationsProvider),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CategoryChip extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _CategoryChip({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(right: 12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          width: 80,
          decoration: BoxDecoration(
            color: theme.colorScheme.primary.withOpacity(0.08),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: theme.colorScheme.primary, size: 28),
              const SizedBox(height: 6),
              Text(
                label,
                style: theme.textTheme.bodySmall?.copyWith(
                  fontWeight: FontWeight.w500,
                  color: theme.colorScheme.primary,
                ),
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Helper empty state for home screen.
class AppEmptyState extends StatelessWidget {
  final String message;
  const AppEmptyState({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Text(
          message,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Theme.of(context).colorScheme.onSurface.withOpacity(0.5),
              ),
        ),
      ),
    );
  }
}
