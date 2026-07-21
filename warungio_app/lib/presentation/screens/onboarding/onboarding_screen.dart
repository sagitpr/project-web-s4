import 'package:flutter/material.dart';
import '../../widgets/placeholder/placeholder_screen.dart';

class OnboardingScreen extends StatelessWidget {
  const OnboardingScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return PlaceholderScreen(
      title: 'Selamat Datang',
      subtitle: 'Aplikasi Warungio siap menemani belanja harian Anda',
      icon: Icons.store_rounded,
    );
  }
}
