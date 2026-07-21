import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../widgets/common/error_widget.dart';
import '../../../core/utils/extensions.dart';
import '../../../core/network/dio_client.dart';
import '../../../data/models/payment_model.dart';
import '../../../data/datasources/payment_api.dart';

/// Provider for wallet balance.
final walletBalanceProvider = FutureProvider.autoDispose<WalletModel>((ref) {
  final api = ref.watch(paymentApiProvider);
  return api.getWalletBalance().then((r) {
    final data = r.data;
    if (data is Map<String, dynamic>) {
      return WalletModel.fromJson(data);
    }
    return WalletModel(id: 0);
  });
});

/// Provider for wallet transactions.
final walletTransactionsProvider =
    FutureProvider.autoDispose<List<WalletTransactionModel>>((ref) {
  final api = ref.watch(paymentApiProvider);
  return api.getWalletTransactions().then((r) {
    final data = r.data;
    if (data is Map<String, dynamic>) {
      final results = data['results'] as List<dynamic>? ??
          data['data'] as List<dynamic>? ??
          [];
      return results
          .map((e) => WalletTransactionModel.fromJson(e as Map<String, dynamic>))
          .toList();
    }
    return <WalletTransactionModel>[];
  });
});

class WalletScreen extends ConsumerWidget {
  const WalletScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final balanceAsync = ref.watch(walletBalanceProvider);
    final transactionsAsync = ref.watch(walletTransactionsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Dompet')),
      body: ListView(
        children: [
          // ── Balance Card ──
          Container(
            margin: const EdgeInsets.all(16),
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  theme.colorScheme.primary,
                  theme.colorScheme.primary.withOpacity(0.8),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(20),
              boxShadow: [
                BoxShadow(
                  color: theme.colorScheme.primary.withOpacity(0.3),
                  blurRadius: 20,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Saldo Dompet',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onPrimary.withOpacity(0.8),
                  ),
                ),
                const SizedBox(height: 8),
                balanceAsync.when(
                  data: (wallet) => Text(
                    wallet.balance.toRupiah,
                    style: theme.textTheme.headlineLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: theme.colorScheme.onPrimary,
                    ),
                  ),
                  loading: () => const SizedBox(
                    height: 40,
                    child: Center(
                      child: CircularProgressIndicator(color: Colors.white),
                    ),
                  ),
                  error: (_, __) => Text(
                    'Rp0',
                    style: theme.textTheme.headlineLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: theme.colorScheme.onPrimary,
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () {
                          // TODO: Show top-up dialog
                        },
                        icon: const Icon(Icons.add_rounded),
                        label: const Text('Top Up'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: theme.colorScheme.onPrimary,
                          side: BorderSide(
                            color: theme.colorScheme.onPrimary.withOpacity(0.5),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () {
                          // TODO: Show withdraw dialog
                        },
                        icon: const Icon(Icons.arrow_upward_rounded),
                        label: const Text('Tarik'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: theme.colorScheme.onPrimary,
                          side: BorderSide(
                            color: theme.colorScheme.onPrimary.withOpacity(0.5),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // ── Quick Actions ──
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                _ActionButton(
                  icon: Icons.add_circle_outline,
                  label: 'Top Up',
                  onTap: () {},
                ),
                const SizedBox(width: 12),
                _ActionButton(
                  icon: Icons.arrow_upward,
                  label: 'Tarik Dana',
                  onTap: () {},
                ),
                const SizedBox(width: 12),
                _ActionButton(
                  icon: Icons.history_rounded,
                  label: 'Riwayat',
                  onTap: () {},
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // ── Transaction History ──
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Text(
              'Riwayat Transaksi',
              style: theme.textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          const SizedBox(height: 12),
          transactionsAsync.when(
            data: (transactions) {
              if (transactions.isEmpty) {
                return const Padding(
                  padding: EdgeInsets.all(32),
                  child: Center(
                    child: Text('Belum ada transaksi'),
                  ),
                );
              }
              return ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                padding: const EdgeInsets.symmetric(horizontal: 16),
                itemCount: transactions.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final tx = transactions[index];
                  return ListTile(
                    leading: Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        color: tx.type == 'topup' || tx.type == 'credit'
                            ? Colors.green.withOpacity(0.1)
                            : Colors.red.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Icon(
                        tx.type == 'topup' || tx.type == 'credit'
                            ? Icons.arrow_downward_rounded
                            : Icons.arrow_upward_rounded,
                        color: tx.type == 'topup' || tx.type == 'credit'
                            ? Colors.green
                            : Colors.red,
                        size: 20,
                      ),
                    ),
                    title: Text(tx.description ?? tx.type),
                    subtitle: Text(tx.createdAt.timeAgo),
                    trailing: Text(
                      '${tx.type == 'topup' || tx.type == 'credit' ? '+' : '-'}${tx.amount.toRupiah}',
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: tx.type == 'topup' || tx.type == 'credit'
                            ? Colors.green
                            : Colors.red,
                      ),
                    ),
                  );
                },
              );
            },
            loading: () => const Padding(
              padding: EdgeInsets.all(32),
              child: Center(child: CircularProgressIndicator()),
            ),
            error: (_, __) => Padding(
              padding: const EdgeInsets.all(32),
              child: AppErrorWidget(
                message: 'Gagal memuat riwayat transaksi',
                onRetry: () => ref.invalidate(walletTransactionsProvider),
              ),
            ),
          ),
          const SizedBox(height: 32),
        ],
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _ActionButton({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: theme.colorScheme.primary.withOpacity(0.08),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            children: [
              Icon(icon, color: theme.colorScheme.primary, size: 24),
              const SizedBox(height: 4),
              Text(
                label,
                style: theme.textTheme.bodySmall?.copyWith(
                  fontWeight: FontWeight.w500,
                  color: theme.colorScheme.primary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
