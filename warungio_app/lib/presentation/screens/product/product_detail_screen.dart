import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../widgets/common/error_widget.dart';
import '../../widgets/common/card_widgets.dart';
import '../../../core/utils/extensions.dart';
import '../../../core/network/dio_client.dart';
import '../../../data/models/product_model.dart';
import '../../../data/models/review_model.dart';
import '../../../data/datasources/product_api.dart';
import '../../../data/datasources/order_api.dart';
import '../../../data/datasources/ai_api.dart';
import '../../../core/routing/route_names.dart' as routes;

/// Provider for product detail.
final productDetailProvider =
    FutureProvider.autoDispose.family<ProductModel, int>((ref, id) {
  return ref.watch(productApiProvider).getProductById(id);
});

/// Provider for product reviews.
final productReviewsProvider =
    FutureProvider.autoDispose.family<List<dynamic>, int>((ref, productId) {
  return ref
      .watch(productApiProvider)
      .getProductById(productId)
      .then((_) => <dynamic>[]); // TODO: Connect to actual reviews API
});

/// Provider for similar products.
final similarProductsProvider =
    FutureProvider.autoDispose.family<List<ProductModel>, int>((ref, productId) {
  final aiApi = ref.watch(aiApiProvider);
  return aiApi.getSimilarProducts(productId).then((r) {
    final data = r.data;
    if (data is Map<String, dynamic>) {
      final results = data['results'] as List<dynamic>? ?? [];
      return results
          .map((e) => ProductModel.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    return <ProductModel>[];
  });
});

class ProductDetailScreen extends ConsumerWidget {
  final int? productId;

  const ProductDetailScreen({super.key, this.productId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final productAsync = ref.watch(productDetailProvider(productId ?? 0));
    final similarAsync = ref.watch(similarProductsProvider(productId ?? 0));

    return productAsync.when(
      data: (product) => _buildContent(context, ref, theme, product, similarAsync),
      loading: () => const Scaffold(body: Center(child: CircularProgressIndicator())),
      error: (e, _) => Scaffold(
        appBar: AppBar(),
        body: AppErrorWidget(
          message: 'Gagal memuat detail produk',
          onRetry: () => ref.invalidate(productDetailProvider(productId ?? 0)),
        ),
      ),
    );
  }

  Widget _buildContent(
    BuildContext context,
    WidgetRef ref,
    ThemeData theme,
    ProductModel product,
    AsyncValue<List<ProductModel>> similarAsync,
  ) {
    final quantityProvider = StateProvider.autoDispose<int>((ref) => 1);
    final quantity = ref.watch(quantityProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(product.productName, overflow: TextOverflow.ellipsis),
        actions: [
          IconButton(
            icon: const Icon(Icons.favorite_outline_rounded),
            onPressed: () {
              // TODO: Toggle favorite
            },
          ),
          IconButton(
            icon: const Icon(Icons.share_outlined),
            onPressed: () {/* TODO: Share product */},
          ),
        ],
      ),
      body: ListView(
        children: [
          // ── Product Image ──
          Container(
            height: 300,
            color: theme.colorScheme.surfaceVariant,
            child: Center(
              child: product.image != null
                  ? Image.network(product.image!, fit: BoxFit.cover)
                  : Icon(Icons.image_outlined,
                      size: 80,
                      color: theme.colorScheme.onSurface.withOpacity(0.3)),
            ),
          ),

          // ── Product Info ──
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  product.productName,
                  style: theme.textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  product.formattedPrice,
                  style: theme.textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: theme.colorScheme.primary,
                  ),
                ),
                const SizedBox(height: 16),

                // Store info
                Row(
                  children: [
                    CircleAvatar(
                      radius: 20,
                      backgroundColor: theme.colorScheme.primary.withOpacity(0.1),
                      child: Text(
                        product.storeName.isNotEmpty
                            ? product.storeName[0].toUpperCase()
                            : 'T',
                        style: TextStyle(
                          color: theme.colorScheme.primary,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(product.storeName,
                              style: theme.textTheme.titleSmall?.copyWith(
                                  fontWeight: FontWeight.w600)),
                          Text('Penjual',
                              style: theme.textTheme.bodySmall?.copyWith(
                                  color: theme.colorScheme.onSurface
                                      .withOpacity(0.6))),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // Stock status
                Row(
                  children: [
                    Icon(Icons.inventory_2_outlined,
                        size: 16,
                        color: product.stock > 0 ? Colors.green : Colors.red),
                    const SizedBox(width: 8),
                    Text(
                      product.stock > 0
                          ? 'Stok: ${product.stock} ${product.unit}'
                          : 'Stok Habis',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: product.stock > 0 ? Colors.green : Colors.red,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    if (product.soldCount != null) ...[
                      const SizedBox(width: 24),
                      Icon(Icons.shopping_bag_outlined,
                          size: 16,
                          color: theme.colorScheme.onSurface.withOpacity(0.5)),
                      const SizedBox(width: 8),
                      Text(
                        'Terjual ${product.soldCount}',
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: theme.colorScheme.onSurface.withOpacity(0.6),
                        ),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 16),

                // Rating
                if (product.ratingAvg != null)
                  Row(
                    children: [
                      Icon(Icons.star_rounded, color: Colors.amber[700], size: 20),
                      const SizedBox(width: 4),
                      Text(
                        product.ratingAvg!.toStringAsFixed(1),
                        style: theme.textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      if (product.reviewCount != null) ...[
                        const SizedBox(width: 4),
                        Text(
                          '(${product.reviewCount} ulasan)',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.onSurface.withOpacity(0.6),
                          ),
                        ),
                      ],
                    ],
                  ),

                const Divider(height: 32),

                // Description
                Text('Deskripsi',
                    style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Text(
                  product.description ?? 'Tidak ada deskripsi',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurface.withOpacity(0.7),
                  ),
                ),

                const Divider(height: 32),

                // Quantity selector
                Row(
                  children: [
                    Text('Jumlah', style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.bold)),
                    const Spacer(),
                    _QuantitySelector(
                      quantity: quantity,
                      min: 1,
                      max: product.stock,
                      onChanged: (q) =>
                          ref.read(quantityProvider.notifier).state = q,
                    ),
                  ],
                ),
              ],
            ),
          ),

          // ── Similar Products ──
          if (similarAsync is AsyncData && similarAsync.value.isNotEmpty) ...[
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
              child: Text('Produk Serupa',
                  style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.bold)),
            ),
            SizedBox(
              height: 200,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                itemCount: similarAsync.value.length,
                separatorBuilder: (_, __) => const SizedBox(width: 12),
                itemBuilder: (context, index) => SizedBox(
                  width: 140,
                  child: ProductCard(
                    product: similarAsync.value[index],
                    isGridView: true,
                    onTap: () {
                      context.pushReplacement(
                        routes.RouteNames.productDetail.replaceAll(
                          ':id',
                          similarAsync.value[index].id.toString(),
                        ),
                      );
                    },
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
      bottomNavigationBar: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: theme.colorScheme.surface,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.05),
              blurRadius: 10,
              offset: const Offset(0, -5),
            ),
          ],
        ),
        child: SafeArea(
          child: Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () {
                    // TODO: Add to cart via OrderApi
                    ref.read(orderApiProvider).addToCart(
                          productId: product.id,
                          quantity: quantity,
                        );
                    context.showSnackBar('Ditambahkan ke keranjang');
                  },
                  icon: const Icon(Icons.shopping_cart_outlined),
                  label: const Text('Keranjang'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: FilledButton.icon(
                  onPressed: () {
                    // Navigate to checkout
                    context.push(routes.RouteNames.checkout);
                  },
                  icon: const Icon(Icons.flash_on_rounded),
                  label: const Text('Beli Sekarang'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _QuantitySelector extends StatelessWidget {
  final int quantity;
  final int min;
  final int max;
  final ValueChanged<int> onChanged;

  const _QuantitySelector({
    required this.quantity,
    required this.min,
    required this.max,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      decoration: BoxDecoration(
        border: Border.all(color: theme.colorScheme.outline.withOpacity(0.3)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            icon: const Icon(Icons.remove_rounded, size: 18),
            onPressed: quantity > min ? () => onChanged(quantity - 1) : null,
            constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
          ),
          SizedBox(
            width: 40,
            child: Text(
              quantity.toString(),
              textAlign: TextAlign.center,
              style: theme.textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.add_rounded, size: 18),
            onPressed: quantity < max ? () => onChanged(quantity + 1) : null,
            constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
          ),
        ],
      ),
    );
  }
}

