import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../widgets/common/error_widget.dart';
import '../../../core/utils/extensions.dart';
import '../../../core/storage/secure_storage_service.dart';
import '../../../data/repositories/auth_repository.dart';
import '../../../presentation/providers/auth_provider.dart';
import '../../../core/routing/route_names.dart' as routes;

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final authState = ref.watch(authProvider);
    final user = authState.user;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Akun'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            onPressed: () => context.push(routes.RouteNames.settings),
          ),
        ],
      ),
      body: ListView(
        children: [
          // ── Profile Header ──
          Container(
            padding: const EdgeInsets.all(24),
            child: Row(
              children: [
                CircleAvatar(
                  radius: 36,
                  backgroundColor: theme.colorScheme.primary.withOpacity(0.1),
                  child: Text(
                    (user?.fullName ?? 'U').isNotEmpty
                        ? (user!.fullName)[0].toUpperCase()
                        : 'U',
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
                      Text(
                        user?.fullName ?? 'Pengguna',
                        style: theme.textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        user?.email ?? '',
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: theme.colorScheme.onSurface.withOpacity(0.6),
                        ),
                      ),
                      if (user != null)
                        Container(
                          margin: const EdgeInsets.only(top: 8),
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: user.isSeller
                                ? Colors.blue.withOpacity(0.1)
                                : theme.colorScheme.primary.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text(
                            user.isSeller ? 'Penjual' : 'Pembeli',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              color: user.isSeller
                                  ? Colors.blue[700]
                                  : theme.colorScheme.primary,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.edit_outlined),
                  onPressed: () => context.push(routes.RouteNames.editProfile),
                ),
              ],
            ),
          ),

          // ── Quick Stats ──
          if (user != null) ...[
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      _StatItem(
                        icon: Icons.receipt_long_rounded,
                        label: 'Pesanan',
                        value: '0', // TODO: Connect to real data
                      ),
                      _StatItem(
                        icon: Icons.favorite_rounded,
                        label: 'Favorit',
                        value: '0', // TODO: Connect to real data
                      ),
                      _StatItem(
                        icon: Icons.account_balance_wallet_rounded,
                        label: 'Dompet',
                        value: user.walletBalance.toRupiah,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],

          const SizedBox(height: 16),

          // ── Menu Items ──
          _MenuSection(title: 'Transaksi', children: [
            _MenuItem(
              icon: Icons.receipt_long_outlined,
              title: 'Pesanan Saya',
              onTap: () => context.push(routes.RouteNames.orders),
            ),
            _MenuItem(
              icon: Icons.account_balance_wallet_outlined,
              title: 'Dompet',
              onTap: () => context.push(routes.RouteNames.wallet),
            ),
            _MenuItem(
              icon: Icons.favorite_outline,
              title: 'Favorit',
              onTap: () => context.push(routes.RouteNames.favorites),
            ),
            _MenuItem(
              icon: Icons.rate_review_outlined,
              title: 'Ulasan',
              onTap: () => {}, // TODO: Navigate to reviews
            ),
          ]),

          _MenuSection(title: 'Lainnya', children: [
            _MenuItem(
              icon: Icons.notifications_outlined,
              title: 'Notifikasi',
              onTap: () => context.push(routes.RouteNames.notifications),
            ),
            _MenuItem(
              icon: Icons.help_outline,
              title: 'Bantuan',
              onTap: () => context.push(routes.RouteNames.support),
            ),
            _MenuItem(
              icon: Icons.settings_outlined,
              title: 'Pengaturan',
              onTap: () => context.push(routes.RouteNames.settings),
            ),
          ]),

          const SizedBox(height: 24),

          // ── Logout ──
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: OutlinedButton.icon(
              onPressed: () => _showLogoutDialog(context, ref),
              icon: const Icon(Icons.logout_rounded),
              label: const Text('Keluar'),
              style: OutlinedButton.styleFrom(
                foregroundColor: theme.colorScheme.error,
                side: BorderSide(color: theme.colorScheme.error.withOpacity(0.3)),
              ),
            ),
          ),
          const SizedBox(height: 48),
        ],
      ),
    );
  }

  void _showLogoutDialog(BuildContext context, WidgetRef ref) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Keluar'),
        content: const Text('Apakah Anda yakin ingin keluar?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Batal'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(context);
              ref.read(authProvider.notifier).logout();
            },
            child: const Text('Keluar'),
          ),
        ],
      ),
    );
  }
}

class _StatItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _StatItem({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Expanded(
      child: Column(
        children: [
          Icon(icon, color: theme.colorScheme.primary, size: 24),
          const SizedBox(height: 8),
          Text(
            value,
            style: theme.textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          Text(
            label,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurface.withOpacity(0.6),
            ),
          ),
        ],
      ),
    );
  }
}

class _MenuSection extends StatelessWidget {
  final String title;
  final List<Widget> children;

  const _MenuSection({
    required this.title,
    required this.children,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: Text(
            title,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: Theme.of(context)
                      .colorScheme
                      .onSurface
                      .withOpacity(0.6),
                ),
          ),
        ),
        ...children,
      ],
    );
  }
}

class _MenuItem extends StatelessWidget {
  final IconData icon;
  final String title;
  final VoidCallback onTap;

  const _MenuItem({
    required this.icon,
    required this.title,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return ListTile(
      leading: Icon(icon, color: theme.colorScheme.primary),
      title: Text(title),
      trailing: Icon(
        Icons.chevron_right_rounded,
        color: theme.colorScheme.onSurface.withOpacity(0.3),
      ),
      onTap: onTap,
    );
  }
}
