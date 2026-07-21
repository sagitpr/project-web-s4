import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../widgets/common/card_widgets.dart';
import '../../widgets/common/error_widget.dart';
import '../../../data/models/store_model.dart';
import '../../../data/datasources/store_api.dart';
import '../../../core/routing/route_names.dart' as routes;

/// Provider for stores list.
final storesProvider = FutureProvider.autoDispose<List<StoreModel>>((ref) {
  final api = ref.watch(storeApiProvider);
  return api.getStores().then((r) {
    final data = r.data;
    if (data is Map<String, dynamic>) {
      final results = data['results'] as List<dynamic>? ??
          data['data'] as List<dynamic>? ??
          [];
      return results
          .map((e) => StoreModel.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    return <StoreModel>[];
  });
});

class MarketplaceScreen extends ConsumerWidget {
  const MarketplaceScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final storesAsync = ref.watch(storesProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Marketplace'),
        actions: [
          IconButton(
            icon: const Icon(Icons.search_rounded),
            onPressed: () => context.push(routes.RouteNames.search),
          ),
        ],
      ),
      body: Column(
        children: [
          // ── Category Chips ──
          Container(
            height: 56,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              children: [
                _CategoryChip(label: 'Semua', selected: true, onTap: () {}),
                _CategoryChip(label: 'Makanan', onTap: () {}),
                _CategoryChip(label: 'Minuman', onTap: () {}),
                _CategoryChip(label: 'Sayuran', onTap: () {}),
                _CategoryChip(label: 'Buah', onTap: () {}),
                _CategoryChip(label: 'Bumbu Dapur', onTap: () {}),
              ],
            ),
          ),
          const Divider(height: 1),

          // ── Store List ──
          Expanded(
            child: storesAsync.when(
              data: (stores) {
                if (stores.isEmpty) {
                  return EmptyStateWidget(
                    message: 'Belum ada toko',
                    subtitle: 'Toko akan muncul setelah penjual mendaftar',
                    icon: Icons.store_outlined,
                  );
                }

                return RefreshIndicator(
                  onRefresh: () async =>
                      ref.invalidate(storesProvider),
                  child: ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: stores.length,
                    itemBuilder: (context, index) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: StoreCard(
                        store: stores[index],
                        onTap: () {
                          // Navigate to store detail
                        },
                      ),
                    ),
                  ),
                );
              },
              loading: () => const AppLoadingWidget(message: 'Memuat toko...'),
              error: (_, __) => AppErrorWidget(
                message: 'Gagal memuat toko',
                onRetry: () => ref.invalidate(storesProvider),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _CategoryChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _CategoryChip({
    required this.label,
    this.selected = false,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: FilterChip(
        label: Text(label),
        selected: selected,
        onSelected: (_) => onTap(),
        selectedColor: theme.colorScheme.primary.withOpacity(0.15),
        checkmarkColor: theme.colorScheme.primary,
        labelStyle: TextStyle(
          color: selected ? theme.colorScheme.primary : null,
          fontWeight: selected ? FontWeight.w600 : null,
        ),
      ),
    );
  }
}
