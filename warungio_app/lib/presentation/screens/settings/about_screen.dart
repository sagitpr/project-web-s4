import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/constants/app_constants.dart';

/// Provider for package info (app version etc).
final packageInfoProvider = FutureProvider<PackageInfo>((ref) {
  return PackageInfo.fromPlatform();
});

class AboutScreen extends ConsumerWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final pkgAsync = ref.watch(packageInfoProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Tentang Aplikasi')),
      body: ListView(
        children: [
          const SizedBox(height: 32),

          // ── Logo & App Name ──
          Center(
            child: Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                color: theme.colorScheme.primary,
                borderRadius: BorderRadius.circular(20),
              ),
              child: Center(
                child: Text('W',
                    style: TextStyle(
                        fontSize: 40,
                        fontWeight: FontWeight.bold,
                        color: theme.colorScheme.onPrimary)),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Center(
            child: Text('Warungio',
                style: theme.textTheme.headlineMedium
                    ?.copyWith(fontWeight: FontWeight.bold)),
          ),
          const SizedBox(height: 8),
          Center(
            child: pkgAsync.when(
              data: (pkg) => Text('Versi ${pkg.version} (build ${pkg.buildNumber})',
                  style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurface.withOpacity(0.6))),
              loading: () => const SizedBox(
                  width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
              error: (_, __) => Text('Versi ${AppConstants.appVersion}',
                  style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurface.withOpacity(0.6))),
            ),
          ),
          const SizedBox(height: 32),

          // ── Description ──
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32),
            child: Text(
              'Warungio adalah hyperlocal marketplace yang menghubungkan pembeli '
              'dengan penjual lokal untuk kebutuhan sehari-hari. Nikmati belanja '
              'cepat, aman, dan terpercaya.',
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurface.withOpacity(0.7),
                height: 1.5,
              ),
              textAlign: TextAlign.center,
            ),
          ),
          const SizedBox(height: 32),

          // ── Links ──
          Card(
            margin: const EdgeInsets.symmetric(horizontal: 16),
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(Icons.description_outlined),
                  title: const Text('Kebijakan Privasi'),
                  trailing: const Icon(Icons.open_in_new_rounded, size: 18),
                  onTap: () => _openUrl('https://warungio.com/privacy'),
                ),
                Divider(height: 1, indent: 16, endIndent: 16, color: theme.dividerColor),
                ListTile(
                  leading: const Icon(Icons.article_outlined),
                  title: const Text('Syarat & Ketentuan'),
                  trailing: const Icon(Icons.open_in_new_rounded, size: 18),
                  onTap: () => _openUrl('https://warungio.com/terms'),
                ),
                Divider(height: 1, indent: 16, endIndent: 16, color: theme.dividerColor),
                ListTile(
                  leading: const Icon(Icons.web_rounded),
                  title: const Text('Kunjungi Website'),
                  trailing: const Icon(Icons.open_in_new_rounded, size: 18),
                  onTap: () => _openUrl('https://warungio.com'),
                ),
                Divider(height: 1, indent: 16, endIndent: 16, color: theme.dividerColor),
                ListTile(
                  leading: const Icon(Icons.mail_outline),
                  title: const Text('Hubungi Kami'),
                  subtitle: const Text('warungio.id@gmail.com'),
                  trailing: const Icon(Icons.open_in_new_rounded, size: 18),
                  onTap: () => _openUrl('mailto:warungio.id@gmail.com'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),

          // ── Credits ──
          Center(
            child: Text('PT Warungio Teknologi Indonesia',
                style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurface.withOpacity(0.4))),
          ),
          Center(
            child: Text('© ${DateTime.now().year} All Rights Reserved',
                style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurface.withOpacity(0.4))),
          ),
          const SizedBox(height: 48),
        ],
      ),
    );
  }

  Future<void> _openUrl(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}

