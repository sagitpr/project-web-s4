import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../widgets/common/error_widget.dart';
import '../../../core/network/dio_client.dart';
import '../../../data/datasources/support_api.dart';

/// Provider for FAQs.
final faqsProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) {
  final api = ref.watch(supportApiProvider);
  return api.getFAQs().then((r) {
    final list = r.resultsList;
    return list.map((e) => e as Map<String, dynamic>).toList();
  }).catchError((_) => <Map<String, dynamic>>[]);
});

class SupportScreen extends ConsumerStatefulWidget {
  const SupportScreen({super.key});

  @override
  ConsumerState<SupportScreen> createState() => _SupportScreenState();
}

class _SupportScreenState extends ConsumerState<SupportScreen> {
  final _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final faqsAsync = ref.watch(faqsProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Bantuan')),
      body: ListView(
        children: [
          // ── Search ──
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Cari artikel bantuan...',
                prefixIcon: const Icon(Icons.search_rounded),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear_rounded),
                        onPressed: () {
                          _searchController.clear();
                          setState(() {});
                        },
                      )
                    : null,
              ),
              onChanged: (_) => setState(() {}),
            ),
          ),

          // ── Quick Help Cards ──
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                Expanded(
                  child: _HelpCard(
                    icon: Icons.receipt_long_rounded,
                    label: 'Pesanan',
                    color: Colors.blue,
                    onTap: () {},
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _HelpCard(
                    icon: Icons.payment_rounded,
                    label: 'Pembayaran',
                    color: Colors.green,
                    onTap: () {},
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                Expanded(
                  child: _HelpCard(
                    icon: Icons.local_shipping_rounded,
                    label: 'Pengiriman',
                    color: Colors.orange,
                    onTap: () {},
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _HelpCard(
                    icon: Icons.account_balance_wallet_rounded,
                    label: 'Akun',
                    color: Colors.purple,
                    onTap: () {},
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // ── FAQ Section ──
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Text('Pertanyaan Umum (FAQ)',
                style: theme.textTheme.titleMedium
                    ?.copyWith(fontWeight: FontWeight.bold)),
          ),
          const SizedBox(height: 8),

          faqsAsync.when(
            data: (faqs) {
              if (faqs.isEmpty) {
                return _buildDefaultFaqs(theme);
              }
              return Column(
                children: faqs.map((faq) => _FaqTile(
                  question: faq['question'] as String? ?? faq['title'] as String? ?? '',
                  answer: faq['answer'] as String? ?? faq['content'] as String? ?? '',
                )).toList(),
              );
            },
            loading: () => const Padding(
              padding: EdgeInsets.all(16),
              child: Center(child: CircularProgressIndicator()),
            ),
            error: (_, __) => _buildDefaultFaqs(theme),
          ),

          const Divider(height: 32),

          // ── Contact Section ──
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Hubungi Kami',
                    style: theme.textTheme.titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: 12),
                Card(
                  child: Column(
                    children: [
                      ListTile(
                        leading: const Icon(Icons.chat_rounded,
                            color: Colors.blue),
                        title: const Text('Live Chat'),
                        subtitle: const Text('Chat dengan tim support kami'),
                        trailing: const Icon(Icons.chevron_right_rounded),
                        onTap: () {
                          // TODO: Navigate to support chat
                        },
                      ),
                      Divider(height: 1, indent: 16, endIndent: 16, color: theme.dividerColor),
                      ListTile(
                        leading: const Icon(Icons.email_rounded,
                            color: Colors.red),
                        title: const Text('Email'),
                        subtitle: const Text('warungio.id@gmail.com'),
                        trailing: const Icon(Icons.chevron_right_rounded),
                        onTap: () => _launchUrl('mailto:warungio.id@gmail.com'),
                      ),
                      Divider(height: 1, indent: 16, endIndent: 16, color: theme.dividerColor),
                      ListTile(
                        leading: const Icon(Icons.phone_rounded,
                            color: Colors.green),
                        title: const Text('Telepon'),
                        subtitle: const Text('+62 878-3384-7895'),
                        trailing: const Icon(Icons.chevron_right_rounded),
                        onTap: () => _launchUrl('tel:+6287833847895'),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // ── AI Chat ──
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 24, 16, 32),
            child: Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    Colors.indigo.withOpacity(0.1),
                    Colors.purple.withOpacity(0.05),
                  ],
                ),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.indigo.withOpacity(0.2)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: Colors.indigo.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(Icons.auto_awesome_rounded,
                        color: Colors.indigo),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Tanya AI',
                            style: theme.textTheme.titleSmall?.copyWith(
                                fontWeight: FontWeight.bold,
                                color: Colors.indigo)),
                        const SizedBox(height: 4),
                        Text('Dapatkan jawaban cepat dari asisten AI',
                            style: theme.textTheme.bodySmall?.copyWith(
                                color: Colors.indigo.withOpacity(0.7))),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.arrow_forward_rounded),
                    onPressed: () {/* TODO: Open AI chat */},
                    color: Colors.indigo,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDefaultFaqs(ThemeData theme) {
    return Column(
      children: [
        _FaqTile(
          question: 'Bagaimana cara melakukan pemesanan?',
          answer:
              'Pilih produk yang diinginkan, tambahkan ke keranjang, lalu lakukan checkout. '
              'Ikuti petunjuk pembayaran yang diberikan.',
        ),
        _FaqTile(
          question: 'Berapa lama waktu pengiriman?',
          answer:
              'Waktu pengiriman tergantung metode yang dipilih. Rata-rata 1-3 hari kerja '
              'untuk pengiriman dalam kota.',
        ),
        _FaqTile(
          question: 'Bagaimana cara melacak pesanan?',
          answer:
              'Anda dapat melacak pesanan melalui menu Pesanan Saya di halaman utama. '
              'Status pengiriman akan diperbarui secara real-time.',
        ),
        _FaqTile(
          question: 'Bagaimana jika saya ingin membatalkan pesanan?',
          answer:
              'Pembatalan dapat dilakukan selama status pesanan masih "Menunggu Konfirmasi". '
              'Buka detail pesanan dan pilih opsi batalkan.',
        ),
      ],
    );
  }

  Future<void> _launchUrl(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    }
  }
}

class _HelpCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _HelpCard({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 20),
        decoration: BoxDecoration(
          color: color.withOpacity(0.08),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withOpacity(0.2)),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 32),
            const SizedBox(height: 8),
            Text(label,
                style: theme.textTheme.bodySmall
                    ?.copyWith(fontWeight: FontWeight.w600, color: color)),
          ],
        ),
      ),
    );
  }
}

class _FaqTile extends StatefulWidget {
  final String question;
  final String answer;

  const _FaqTile({required this.question, required this.answer});

  @override
  State<_FaqTile> createState() => _FaqTileState();
}

class _FaqTileState extends State<_FaqTile> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: InkWell(
        onTap: () => setState(() => _expanded = !_expanded),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(widget.question,
                        style: Theme.of(context)
                            .textTheme
                            .bodyMedium
                            ?.copyWith(fontWeight: FontWeight.w600)),
                  ),
                  Icon(
                    _expanded
                        ? Icons.expand_less_rounded
                        : Icons.expand_more_rounded,
                    color: Theme.of(context)
                        .colorScheme
                        .onSurface
                        .withOpacity(0.5),
                  ),
                ],
              ),
              if (_expanded) ...[
                const SizedBox(height: 12),
                Text(widget.answer,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context)
                            .colorScheme
                            .onSurface
                            .withOpacity(0.7))),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
