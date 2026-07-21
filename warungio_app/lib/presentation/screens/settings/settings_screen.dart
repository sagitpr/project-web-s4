import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../widgets/common/error_widget.dart';
import '../../../core/constants/app_constants.dart';
import '../../../core/routing/route_names.dart';
import '../../../presentation/providers/theme_provider.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final themeMode = ref.watch(themeModeProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Pengaturan')),
      body: ListView(
        children: [
          // ── Appearance ──
          _SectionHeader(title: 'Tampilan'),
          Card(
            margin: const EdgeInsets.symmetric(horizontal: 16),
            child: Column(
              children: [
                RadioListTile<ThemeMode>(
                  title: const Text('Terang'),
                  subtitle: const Text('Tampilan cerah'),
                  secondary: const Icon(Icons.light_mode_rounded),
                  value: ThemeMode.light,
                  groupValue: themeMode,
                  onChanged: (mode) =>
                      ref.read(themeModeProvider.notifier).setThemeMode(mode!),
                ),
                Divider(height: 1, indent: 16, endIndent: 16, color: theme.dividerColor),
                RadioListTile<ThemeMode>(
                  title: const Text('Gelap'),
                  subtitle: const Text('Tampilan gelap'),
                  secondary: const Icon(Icons.dark_mode_rounded),
                  value: ThemeMode.dark,
                  groupValue: themeMode,
                  onChanged: (mode) =>
                      ref.read(themeModeProvider.notifier).setThemeMode(mode!),
                ),
                Divider(height: 1, indent: 16, endIndent: 16, color: theme.dividerColor),
                RadioListTile<ThemeMode>(
                  title: const Text('Sistem'),
                  subtitle: const Text('Ikuti pengaturan perangkat'),
                  secondary: const Icon(Icons.settings_brightness_rounded),
                  value: ThemeMode.system,
                  groupValue: themeMode,
                  onChanged: (mode) =>
                      ref.read(themeModeProvider.notifier).setThemeMode(mode!),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // ── Notifications ──
          _SectionHeader(title: 'Notifikasi'),
          Card(
            margin: const EdgeInsets.symmetric(horizontal: 16),
            child: Column(
              children: [
                SwitchListTile(
                  title: const Text('Notifikasi Push'),
                  subtitle: const Text('Terima notifikasi push'),
                  secondary: const Icon(Icons.notifications_active_outlined),
                  value: true,
                  onChanged: (_) {},
                ),
                Divider(
                    height: 1,
                    indent: 16,
                    endIndent: 16,
                    color: theme.dividerColor),
                SwitchListTile(
                  title: const Text('Notifikasi Email'),
                  subtitle: const Text('Terima notifikasi via email'),
                  secondary: const Icon(Icons.email_outlined),
                  value: true,
                  onChanged: (_) {},
                ),
                Divider(
                    height: 1,
                    indent: 16,
                    endIndent: 16,
                    color: theme.dividerColor),
                SwitchListTile(
                  title: const Text('Promosi & Penawaran'),
                  subtitle: const Text('Info promo dan diskon'),
                  secondary: const Icon(Icons.local_offer_outlined),
                  value: false,
                  onChanged: (_) {},
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // ── Account ──
          _SectionHeader(title: 'Akun'),
          Card(
            margin: const EdgeInsets.symmetric(horizontal: 16),
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(Icons.lock_outline),
                  title: const Text('Ubah Kata Sandi'),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () => context.push(RouteNames.changePassword),
                ),
                Divider(
                    height: 1,
                    indent: 16,
                    endIndent: 16,
                    color: theme.dividerColor),
                ListTile(
                  leading: const Icon(Icons.language_outlined),
                  title: const Text('Bahasa'),
                  subtitle: const Text('Indonesia'),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () {},
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // ── About ──
          _SectionHeader(title: 'Tentang'),
          Card(
            margin: const EdgeInsets.symmetric(horizontal: 16),
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(Icons.info_outline),
                  title: const Text('Tentang Aplikasi'),
                  subtitle: const Text('Versi ${AppConstants.appVersion}'),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () => context.push(RouteNames.about),
                ),
                Divider(
                    height: 1,
                    indent: 16,
                    endIndent: 16,
                    color: theme.dividerColor),
                ListTile(
                  leading: const Icon(Icons.description_outlined),
                  title: const Text('Kebijakan Privasi'),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () {},
                ),
                Divider(
                    height: 1,
                    indent: 16,
                    endIndent: 16,
                    color: theme.dividerColor),
                ListTile(
                  leading: const Icon(Icons.article_outlined),
                  title: const Text('Syarat & Ketentuan'),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () {},
                ),
              ],
            ),
          ),
          const SizedBox(height: 48),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;

  const _SectionHeader({required this.title});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
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
    );
  }
}
