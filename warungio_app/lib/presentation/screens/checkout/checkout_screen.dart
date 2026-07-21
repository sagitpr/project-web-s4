import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../widgets/common/error_widget.dart';
import '../../../core/utils/extensions.dart';
import '../../../core/network/dio_client.dart';
import '../../../data/models/shipping_model.dart';
import '../../../data/models/payment_model.dart';
import '../../../data/datasources/order_api.dart';
import '../../../data/datasources/payment_api.dart';
import '../../../core/utils/extensions.dart';
import '../../../core/routing/route_names.dart' as routes;

/// Provider for shipping methods.
final shippingMethodsProvider =
    FutureProvider.autoDispose<List<ShippingMethodModel>>((ref) {
  final api = ref.watch(orderApiProvider);
  return api.getShippingMethods().then((r) {
    final data = r.data;
    if (data is Map<String, dynamic>) {
      final results = data['results'] as List<dynamic>? ??
          data['data'] as List<dynamic>? ?? [];
      return results
          .map((e) => ShippingMethodModel.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    return <ShippingMethodModel>[];
  });
});

/// Provider for payment methods.
final paymentMethodsProvider =
    FutureProvider.autoDispose<List<PaymentMethodModel>>((ref) {
  final api = ref.watch(paymentApiProvider);
  return api.getPaymentMethods().then((r) {
    final data = r.data;
    if (data is Map<String, dynamic>) {
      final results = data['results'] as List<dynamic>? ??
          data['data'] as List<dynamic>? ?? [];
      return results
          .map((e) => PaymentMethodModel.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    return <PaymentMethodModel>[];
  });
});

class CheckoutScreen extends ConsumerStatefulWidget {
  const CheckoutScreen({super.key});

  @override
  ConsumerState<CheckoutScreen> createState() => _CheckoutScreenState();
}

class _CheckoutScreenState extends ConsumerState<CheckoutScreen> {
  String? _selectedShippingMethod;
  String? _selectedPaymentMethod;
  String _notes = '';
  bool _isProcessing = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final shippingAsync = ref.watch(shippingMethodsProvider);
    final paymentAsync = ref.watch(paymentMethodsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Checkout')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // ── Shipping Address ──
          Text('Alamat Pengiriman',
              style: theme.textTheme.titleSmall
                  ?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Card(
            child: ListTile(
              leading: const Icon(Icons.location_on_outlined),
              title: const Text('Alamat Utama'),
              subtitle: const Text('Jl. Contoh No. 123, Jakarta'),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () {/* TODO: Change address */},
            ),
          ),
          const SizedBox(height: 24),

          // ── Shipping Method ──
          Text('Metode Pengiriman',
              style: theme.textTheme.titleSmall
                  ?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          shippingAsync.when(
            data: (methods) => Column(
              children: methods
                  .map((m) => RadioListTile<String>(
                        title: Text(m.name),
                        subtitle: Text(
                            '${m.estimatedDays ?? '-'} • ${m.cost.toRupiah}'),
                        secondary: Icon(
                          Icons.local_shipping_outlined,
                          color: theme.colorScheme.primary,
                        ),
                        value: m.id.toString(),
                        groupValue: _selectedShippingMethod,
                        onChanged: (v) =>
                            setState(() => _selectedShippingMethod = v),
                      ))
                  .toList(),
            ),
            loading: () => const AppLoadingWidget(),
            error: (_, __) => AppErrorWidget(
              message: 'Gagal memuat metode pengiriman',
              onRetry: () => ref.invalidate(shippingMethodsProvider),
            ),
          ),
          const SizedBox(height: 24),

          // ── Payment Method ──
          Text('Metode Pembayaran',
              style: theme.textTheme.titleSmall
                  ?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          paymentAsync.when(
            data: (methods) => Column(
              children: methods
                  .map((m) => RadioListTile<String>(
                        title: Text(m.name),
                        subtitle: m.description != null
                            ? Text(m.description!)
                            : null,
                        secondary: Icon(
                          Icons.payment_outlined,
                          color: theme.colorScheme.primary,
                        ),
                        value: m.id.toString(),
                        groupValue: _selectedPaymentMethod,
                        onChanged: (v) =>
                            setState(() => _selectedPaymentMethod = v),
                      ))
                  .toList(),
            ),
            loading: () => const AppLoadingWidget(),
            error: (_, __) => AppErrorWidget(
              message: 'Gagal memuat metode pembayaran',
              onRetry: () => ref.invalidate(paymentMethodsProvider),
            ),
          ),
          const SizedBox(height: 24),

          // ── Order Notes ──
          TextField(
            decoration: const InputDecoration(
              labelText: 'Catatan Pesanan (opsional)',
              border: OutlineInputBorder(),
              prefixIcon: Icon(Icons.notes_rounded),
            ),
            maxLines: 3,
            onChanged: (v) => _notes = v,
          ),
          const SizedBox(height: 24),

          // ── Order Summary ──
          Text('Ringkasan Pesanan',
              style: theme.textTheme.titleSmall
                  ?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  _SummaryRow(label: 'Subtotal', value: 'Rp0'),
                  const SizedBox(height: 8),
                  _SummaryRow(label: 'Biaya Kirim', value: 'Rp0'),
                  const SizedBox(height: 8),
                  _SummaryRow(label: 'Biaya Admin', value: 'Rp0'),
                  const Divider(height: 20),
                  _SummaryRow(
                    label: 'Total',
                    value: 'Rp0',
                    isTotal: true,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 100),
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
        child: SafeArea(              child: FilledButton(
            onPressed: _isProcessing
                ? null
                : () async {
                    if (_selectedShippingMethod == null) {
                      context.showSnackBar('Pilih metode pengiriman',
                          isError: true);
                      return;
                    }
                    if (_selectedPaymentMethod == null) {
                      context.showSnackBar('Pilih metode pembayaran',
                          isError: true);
                      return;
                    }

                    setState(() => _isProcessing = true);

                    final response = await ref
                        .read(orderApiProvider)
                        .createOrder(
                          addressId: 1, // TODO: Use selected address
                          shippingMethodId:
                              int.parse(_selectedShippingMethod!),
                          notes: _notes.isNotEmpty ? _notes : null,
                        );

                    if (mounted) {
                      setState(() => _isProcessing = false);
                      if (response.success) {
                        final orderData = response.data;
                        int orderId = 0;
                        if (orderData is Map<String, dynamic>) {
                          orderId =
                              orderData['order_id'] as int? ??
                              orderData['id'] as int? ??
                              0;
                        }
                        context.push(
                          routes.RouteNames.checkoutSuccess.replaceAll(
                              ':orderId', orderId.toString()),
                        );
                      } else {
                        context.showSnackBar(
                          response.message ?? 'Gagal membuat pesanan',
                          isError: true,
                        );
                      }
                    }
                  },
            child: _isProcessing
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: Colors.white),
                  )
                : const Text('Buat Pesanan'),
          ),
        ),
      ),
    );
  }
}

class _SummaryRow extends StatelessWidget {
  final String label;
  final String value;
  final bool isTotal;

  const _SummaryRow({
    required this.label,
    required this.value,
    this.isTotal = false,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: isTotal
              ? theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold)
              : theme.textTheme.bodyMedium,
        ),
        Text(
          value,
          style: isTotal
              ? theme.textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: theme.colorScheme.primary,
                )
              : theme.textTheme.bodyMedium,
        ),
      ],
    );
  }
}
