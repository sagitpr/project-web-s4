import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../widgets/common/error_widget.dart';
import '../../../core/utils/extensions.dart';
import '../../../data/models/order_model.dart';
import '../../../data/datasources/order_api.dart';
import '../../../core/routing/route_names.dart' as routes;
import '../../../core/network/dio_client.dart';

/// Provider for a single order detail.
final orderDetailProvider =
    FutureProvider.autoDispose.family<OrderModel, int>((ref, orderId) {
  final api = ref.watch(orderApiProvider);
  return api.getOrderDetail(orderId).then((r) {
    final data = r.data;
    if (data is Map<String, dynamic>) {
      return OrderModel.fromJson(data);
    }
    throw Exception('Invalid response format');
  });
});

class OrderDetailScreen extends ConsumerWidget {
  final int orderId;

  const OrderDetailScreen({super.key, required this.orderId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final orderAsync = ref.watch(orderDetailProvider(orderId));

    return orderAsync.when(
      data: (order) => _buildContent(context, ref, theme, order),
      loading: () => const Scaffold(
        appBar: _BackAppBar(),
        body: Center(child: CircularProgressIndicator()),
      ),
      error: (e, _) => Scaffold(
        appBar: const _BackAppBar(),
        body: AppErrorWidget(
          message: 'Gagal memuat detail pesanan',
          onRetry: () => ref.invalidate(orderDetailProvider(orderId)),
        ),
      ),
    );
  }

  Widget _buildContent(
      BuildContext context, WidgetRef ref, ThemeData theme, OrderModel order) {
    return Scaffold(
      appBar: AppBar(title: Text('Pesanan #${order.orderId}')),
      body: ListView(
        children: [
          // ── Status Banner ──
          Container(
            padding: const EdgeInsets.all(16),
            color: _statusColor(order.status).withOpacity(0.1),
            child: Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: _statusColor(order.status).withOpacity(0.2),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    _statusIcon(order.status),
                    color: _statusColor(order.status),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        OrderStatus.label(order.status),
                        style: theme.textTheme.titleSmall
                            ?.copyWith(fontWeight: FontWeight.bold),
                      ),
                      Text(
                        'ID Pesanan: ${order.orderId}',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onSurface.withOpacity(0.6),
                        ),
                      ),
                    ],
                  ),
                ),
                if (order.paymentStatus != null)
                  _buildPaymentChip(theme, order.paymentStatus!),
              ],
            ),
          ),

          // ── Store Info ──
          if (order.storeName != null) ...[
            const SizedBox(height: 8),
            ListTile(
              leading: CircleAvatar(
                backgroundColor: theme.colorScheme.primary.withOpacity(0.1),
                child: Text(
                  order.storeName![0].toUpperCase(),
                  style: TextStyle(color: theme.colorScheme.primary),
                ),
              ),
              title: Text(order.storeName!),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () {
                if (order.storeId != null) {
                  context.push(
                    routes.RouteNames.storeDetail
                        .replaceAll(':id', order.storeId.toString()),
                  );
                }
              },
            ),
          ],
          const Divider(height: 1),

          // ── Order Items ──
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Text('Item Pesanan',
                style: theme.textTheme.titleSmall
                    ?.copyWith(fontWeight: FontWeight.bold)),
          ),
          ...order.items.map((item) => Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                child: Row(
                  children: [
                    Container(
                      width: 56,
                      height: 56,
                      decoration: BoxDecoration(
                        color: theme.colorScheme.surfaceVariant,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(Icons.image_outlined,
                          color: Colors.grey, size: 28),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(item.productName,
                              style: theme.textTheme.bodyMedium
                                  ?.copyWith(fontWeight: FontWeight.w500)),
                          Text('${item.quantity} x ${item.price.toRupiah}',
                              style: theme.textTheme.bodySmall?.copyWith(
                                  color: theme.colorScheme.onSurface
                                      .withOpacity(0.6))),
                        ],
                      ),
                    ),
                    Text(item.subtotal.toRupiah,
                        style: theme.textTheme.titleSmall
                            ?.copyWith(fontWeight: FontWeight.w600)),
                  ],
                ),
              )),

          const Divider(height: 24),

          // ── Price Summary ──
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Column(
              children: [
                _PriceRow(label: 'Subtotal', value: order.subtotal.toRupiah),
                const SizedBox(height: 8),
                _PriceRow(
                    label: 'Ongkos Kirim',
                    value: order.shippingCost.toRupiah),
                const SizedBox(height: 8),
                _PriceRow(
                    label: 'Biaya Admin', value: order.adminFee.toRupiah),
                const Divider(height: 16),
                _PriceRow(
                  label: 'Total Pembayaran',
                  value: order.totalAmount.toRupiah,
                  isTotal: true,
                  color: theme.colorScheme.primary,
                ),
              ],
            ),
          ),

          // ── Shipping Info ──
          if (order.shippingAddress != null ||
              order.shippingMethodName != null) ...[
            const SizedBox(height: 24),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Informasi Pengiriman',
                      style: theme.textTheme.titleSmall
                          ?.copyWith(fontWeight: FontWeight.bold)),
                  if (order.shippingMethodName != null) ...[
                    const SizedBox(height: 8),
                    Text('Metode: ${order.shippingMethodName}'),
                  ],
                  if (order.courier != null) ...[
                    const SizedBox(height: 4),
                    Text('Kurir: ${order.courier}'),
                  ],
                  if (order.trackingNumber != null) ...[
                    const SizedBox(height: 4),
                    Text('No. Resi: ${order.trackingNumber}'),
                  ],
                  if (order.shippingAddress != null) ...[
                    const SizedBox(height: 4),
                    Text('Alamat: ${order.shippingAddress}'),
                  ],
                ],
              ),
            ),
          ],

          const SizedBox(height: 32),

          // ── Action Buttons ──
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Column(
              children: [
                if (order.status == OrderStatus.pending)
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: () => _cancelOrder(context, ref, order),
                      icon: const Icon(Icons.cancel_outlined),
                      label: const Text('Batalkan Pesanan'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: theme.colorScheme.error,
                      ),
                    ),
                  ),
                const SizedBox(height: 12),
                if (order.snapToken != null)
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: () => _openMidtrans(context, order.snapToken!),
                      icon: const Icon(Icons.payment_rounded),
                      label: const Text('Bayar Sekarang'),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 48),
        ],
      ),
    );
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'pending':
        return Colors.orange;
      case 'processing':
      case 'confirmed':
        return Colors.blue;
      case 'shipped':
        return Colors.indigo;
      case 'delivered':
      case 'completed':
        return Colors.green;
      case 'cancelled':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  IconData _statusIcon(String status) {
    switch (status) {
      case 'pending':
        return Icons.hourglass_empty_rounded;
      case 'processing':
      case 'confirmed':
        return Icons.inventory_2_rounded;
      case 'shipped':
        return Icons.local_shipping_rounded;
      case 'delivered':
      case 'completed':
        return Icons.check_circle_rounded;
      case 'cancelled':
        return Icons.cancel_rounded;
      default:
        return Icons.info_rounded;
    }
  }

  Widget _buildPaymentChip(ThemeData theme, String status) {
    Color chipColor;
    switch (status) {
      case 'success':
        chipColor = Colors.green;
        break;
      case 'pending':
        chipColor = Colors.orange;
        break;
      case 'failed':
        chipColor = Colors.red;
        break;
      default:
        chipColor = Colors.grey;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: chipColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: chipColor.withOpacity(0.3)),
      ),
      child: Text(
        status == 'success' ? 'Lunas' : status.capitalize,
        style:
            TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: chipColor),
      ),
    );
  }

  Future<void> _cancelOrder(BuildContext context, WidgetRef ref, OrderModel order) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Batalkan Pesanan'),
        content: const Text('Apakah Anda yakin ingin membatalkan pesanan ini?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Tidak')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Ya, Batalkan')),
        ],
      ),
    );
    if (confirmed == true) {
      await ref.read(orderApiProvider).cancelOrder(order.id);
      ref.invalidate(orderDetailProvider(orderId));
      if (context.mounted) {
        context.showSnackBar('Pesanan berhasil dibatalkan');
      }
    }
  }

  Future<void> _openMidtrans(BuildContext context, String snapToken) async {
    final url = 'https://app.sandbox.midtrans.com/snap/v2/vtweb/$snapToken';
    if (await canLaunchUrl(Uri.parse(url))) {
      await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    } else {
      if (context.mounted) {
        context.showSnackBar('Gagal membuka halaman pembayaran', isError: true);
      }
    }
  }
}

class _BackAppBar extends StatelessWidget implements PreferredSizeWidget {
  const _BackAppBar();
  @override
  Widget build(BuildContext context) => AppBar();
  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);
}

class _PriceRow extends StatelessWidget {
  final String label;
  final String value;
  final bool isTotal;
  final Color? color;

  const _PriceRow({
    required this.label,
    required this.value,
    this.isTotal = false,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label,
            style: isTotal
                ? theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold)
                : theme.textTheme.bodyMedium),
        Text(value,
            style: (isTotal ? theme.textTheme.titleSmall : theme.textTheme.bodyMedium)
                ?.copyWith(fontWeight: isTotal ? FontWeight.bold : null,
                    color: color)),
      ],
    );
  }
}
