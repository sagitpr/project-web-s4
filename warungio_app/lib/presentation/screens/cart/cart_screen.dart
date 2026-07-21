import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../widgets/common/card_widgets.dart';
import '../../widgets/common/error_widget.dart';
import '../../../core/utils/extensions.dart';
import '../../../core/network/dio_client.dart';
import '../../../data/models/cart_model.dart';
import '../../../data/datasources/order_api.dart';
import '../../../core/routing/route_names.dart' as routes;

/// Provider for cart items.
final cartItemsProvider = FutureProvider.autoDispose<CartSummaryModel>((ref) {
  final api = ref.watch(orderApiProvider);
  return api.getCart().then((r) {
    final data = r.data;
    if (data is Map<String, dynamic>) {
      return CartSummaryModel.fromJson(data);
    }
    return CartSummaryModel(items: []);
  });
});

class CartScreen extends ConsumerWidget {
  const CartScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final cartAsync = ref.watch(cartItemsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Keranjang'),
        actions: [
          cartAsync.whenOrNull(
                data: (cart) => cart.items.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.delete_sweep_outlined),
                        onPressed: () async {
                          // TODO: Show confirmation dialog
                          await ref.read(orderApiProvider).clearCart();
                          ref.invalidate(cartItemsProvider);
                        },
                      )
                    : null,
              ) ??
              const SizedBox.shrink(),
        ],
      ),
      body: cartAsync.when(
        data: (cart) {
          if (cart.items.isEmpty) {
            return EmptyStateWidget(
              message: 'Keranjang belanja Anda kosong',
              subtitle: 'Tambahkan produk favorit Anda sekarang',
              icon: Icons.shopping_cart_outlined,
              action: FilledButton(
                onPressed: () => context.push(routes.RouteNames.marketplace),
                child: const Text('Mulai Belanja'),
              ),
            );
          }

          return Column(
            children: [
              Expanded(
                child: ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: cart.items.length,
                  itemBuilder: (context, index) {
                    final item = cart.items[index];
                    return _CartItemCard(
                      item: item,
                      onQuantityChanged: (newQty) async {
                        if (newQty == 0) {
                          await ref
                              .read(orderApiProvider)
                              .removeFromCart(item.id);
                        } else {
                          await ref
                              .read(orderApiProvider)
                              .updateCartItem(item.id, newQty);
                        }
                        ref.invalidate(cartItemsProvider);
                      },
                    );
                  },
                ),
              ),

              // ── Summary & Checkout ──
              Container(
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
                  child: Column(
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            'Total (${cart.totalItems} item)',
                            style: theme.textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          Text(
                            cart.totalPrice.toRupiah,
                            style: theme.textTheme.titleLarge?.copyWith(
                              fontWeight: FontWeight.bold,
                              color: theme.colorScheme.primary,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      FilledButton.icon(
                        onPressed: () => context.push(routes.RouteNames.checkout),
                        icon: const Icon(Icons.shopping_bag_rounded),
                        label: const Text('Checkout'),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          );
        },
        loading: () => const AppLoadingWidget(message: 'Memuat keranjang...'),
        error: (e, _) => AppErrorWidget(
          message: 'Gagal memuat keranjang',
          onRetry: () => ref.invalidate(cartItemsProvider),
        ),
      ),
    );
  }
}

class _CartItemCard extends StatelessWidget {
  final CartItemModel item;
  final ValueChanged<int> onQuantityChanged;

  const _CartItemCard({
    required this.item,
    required this.onQuantityChanged,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            // Product image
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: theme.colorScheme.surfaceVariant,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.image_outlined, color: Colors.grey),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.productName,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    item.subtotal.toRupiah,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: theme.colorScheme.primary,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      _QuantityControl(
                        quantity: item.quantity,
                        max: item.maxQuantity,
                        onChanged: onQuantityChanged,
                      ),
                      const Spacer(),
                      IconButton(
                        icon: Icon(Icons.delete_outline,
                            size: 20, color: theme.colorScheme.error),
                        onPressed: () => onQuantityChanged(0),
                        constraints: const BoxConstraints(
                          minWidth: 32,
                          minHeight: 32,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _QuantityControl extends StatelessWidget {
  final int quantity;
  final int max;
  final ValueChanged<int> onChanged;

  const _QuantityControl({
    required this.quantity,
    required this.max,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      decoration: BoxDecoration(
        border: Border.all(color: theme.colorScheme.outline.withOpacity(0.3)),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          InkWell(
            onTap: quantity > 1 ? () => onChanged(quantity - 1) : null,
            child: Padding(
              padding: const EdgeInsets.all(6),
              child: Icon(Icons.remove_rounded,
                  size: 16,
                  color: quantity > 1
                      ? theme.colorScheme.onSurface
                      : theme.colorScheme.outline),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Text(
              quantity.toString(),
              style: theme.textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          InkWell(
            onTap: quantity < max ? () => onChanged(quantity + 1) : null,
            child: Padding(
              padding: const EdgeInsets.all(6),
              child: Icon(Icons.add_rounded,
                  size: 16,
                  color: quantity < max
                      ? theme.colorScheme.onSurface
                      : theme.colorScheme.outline),
            ),
          ),
        ],
      ),
    );
  }
}
