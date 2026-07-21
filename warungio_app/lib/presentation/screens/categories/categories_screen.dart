import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../widgets/placeholder/placeholder_screen.dart';

class CategoriesScreen extends ConsumerWidget {
  const CategoriesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return const PlaceholderScreen(
      title: 'Kategori',
      icon: Icons.category_rounded,
      subtitle: 'Kategori Produk',
      description: 'Halaman kategori produk dengan hierarki dan filter berdasarkan jenis produk.',
    );
  }
}
