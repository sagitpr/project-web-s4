import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../widgets/common/card_widgets.dart';
import '../../widgets/common/error_widget.dart';
import '../../../core/utils/extensions.dart';
import '../../../data/models/order_model.dart';
import '../../../data/datasources/order_api.dart';
import '../../../core/routing/route_names.dart' as routes;

/// Provider for user's orders with optional status filter.
final ordersProvider =
    FutureProvider.autoDispose.family<List<OrderModel>, String?>((ref, status) {
  final api = ref.watch(orderApiProvider);
  return api.getMyOrders(status: status).then((r) {
    final data = r.data;
    if (data is Map<String, dynamic>) {
      final results = data['results'] as List<dynamic>? ??
          data['data'] as List<dynamic>? ??
          [];
      return results
          .map((e) => OrderModel.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    return <OrderModel>[];
  });
});

class OrdersScreen extends ConsumerStatefulWidget {
  const OrdersScreen({super.key});

  @override
  ConsumerState<OrdersScreen> createState() => _OrdersScreenState();
}

class _OrdersScreenState extends ConsumerState<OrdersScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  static const _tabs = [
    'Semua',
    'Menunggu',
    'Diproses',
    'Dikirim',
    'Selesai',
  ];

  static const _statusValues = [
    null, // All
    'pending',
    'processing',
    'shipped',
    'completed',
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: _tabs.length, vsync: this);
    _tabController.addListener(() {
      if (!_tabController.indexIsChanging) {
        setState(() {});
      }
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final currentStatus = _statusValues[_tabController.index];
    final ordersAsync = ref.watch(ordersProvider(currentStatus));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Pesanan Saya'),
        bottom: TabBar(
          controller: _tabController,
          isScrollable: true,
          tabs: _tabs.map((label) => Tab(text: label)).toList(),
        ),
      ),
      body: ordersAsync.when(
        data: (orders) {
          if (orders.isEmpty) {
            return EmptyStateWidget(
              message: 'Tidak ada pesanan',
              subtitle: _tabController.index == 0
                  ? 'Anda belum memiliki pesanan'
                  : 'Tidak ada pesanan dengan status ini',
              icon: Icons.receipt_long_outlined,
              action: FilledButton(
                onPressed: () => context.push(routes.RouteNames.marketplace),
                child: const Text('Mulai Belanja'),
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(ordersProvider(currentStatus));
            },
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: orders.length,
              itemBuilder: (context, index) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: OrderCard(
                  order: orders[index],
                  onTap: () {
                    // Navigate to order detail
                  },
                ),
              ),
            ),
          );
        },
        loading: () => const AppLoadingWidget(message: 'Memuat pesanan...'),
        error: (_, __) => AppErrorWidget(
          message: 'Gagal memuat pesanan',
          onRetry: () => ref.invalidate(ordersProvider(currentStatus)),
        ),
      ),
    );
  }
}
