import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import '../../../core/config/admob_config.dart';
import '../../../core/theme/app_theme.dart';

/// Native Ad Widget — Displays ads that blend with Warungio UI
///
/// Fully styled with Warungio design system (colors, border radius, typography).
/// Shows loading skeleton, error state with retry, and a subtle "Sponsor" label.
///
/// Usage:
///   const NativeAdWidget(adUnitKey: 'nativeHome')
///   const NativeAdWidget(adUnitKey: 'nativeSearch')
///   const NativeAdWidget(adUnitKey: 'nativeProduct')
class NativeAdWidget extends ConsumerStatefulWidget {
  final String adUnitKey;

  const NativeAdWidget({super.key, required this.adUnitKey});

  @override
  ConsumerState<NativeAdWidget> createState() => _NativeAdWidgetState();
}

class _NativeAdWidgetState extends ConsumerState<NativeAdWidget> {
  NativeAd? _nativeAd;
  bool _isLoaded = false;
  bool _hasError = false;

  @override
  void initState() {
    super.initState();
    _loadAd();
  }

  @override
  void dispose() {
    _nativeAd?.dispose();
    super.dispose();
  }

  void _loadAd() {
    final config = ref.read(admobConfigProvider);
    final adUnitId = _getAdUnitId(config);

    if (adUnitId == null) {
      setState(() => _hasError = true);
      return;
    }

    NativeAd(
      adUnitId: adUnitId,
      request: const AdRequest(),
      // NativeAdStyle removed for v5 compatibility.
      // Apply styling via Container wrapper around the AdWidget below.
      listener: NativeAdListener(
        onAdLoaded: (ad) {
          setState(() {
            _nativeAd = ad as NativeAd;
            _isLoaded = true;
          });
        },
        onAdFailedToLoad: (ad, error) {
          ad.dispose();
          setState(() => _hasError = true);
        },
      ),
    ).load();
  }

  String? _getAdUnitId(AdMobConfig config) {
    switch (widget.adUnitKey) {
      case 'nativeHome':
        return config.nativeHome;
      case 'nativeSearch':
        return config.nativeSearch;
      case 'nativeProduct':
        return config.nativeProduct;
      default:
        return null;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (_hasError) {
      // Error state with retry
      return Container(
        margin: const EdgeInsets.symmetric(vertical: 8),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.grey.shade50,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.grey.shade200),
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                'Iklan tidak tersedia',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: Colors.grey.shade500,
                ),
              ),
            ),
            TextButton.icon(
              onPressed: () {
                setState(() {
                  _hasError = false;
                });
                _loadAd();
              },
              icon: const Icon(Icons.refresh_rounded, size: 16),
              label: const Text('Muat Ulang', style: TextStyle(fontSize: 12)),
            ),
          ],
        ),
      );
    }

    if (!_isLoaded || _nativeAd == null) {
      // Skeleton loading placeholder matching native ad card size
      return Container(
        margin: const EdgeInsets.symmetric(vertical: 8),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.grey.shade100,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            Container(
              width: 60,
              height: 60,
              decoration: BoxDecoration(
                color: Colors.grey.shade200,
                borderRadius: BorderRadius.circular(8),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [                    Container(
                      height: 14,
                      width: 120.0,
                      decoration: BoxDecoration(
                      color: Colors.grey.shade200,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                  const SizedBox(height: 8),                    Container(
                      height: 10,
                      width: 80.0,
                      decoration: BoxDecoration(
                      color: Colors.grey.shade200,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    }

    // Ad loaded successfully — display with Warungio styling
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade200),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Sponsor label
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.grey.shade50,
              border: Border(
                bottom: BorderSide(color: Colors.grey.shade200),
              ),
            ),
            child: Row(
              children: [
                Icon(Icons.info_outline_rounded, size: 12, color: Colors.grey.shade400),
                const SizedBox(width: 4),
                Text(
                  'Sponsor',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    color: Colors.grey.shade500,
                    letterSpacing: 0.5,
                  ),
                ),
              ],
            ),
          ),
          // Native ad content
          ClipRRect(
            borderRadius: const BorderRadius.only(
              bottomLeft: Radius.circular(12),
              bottomRight: Radius.circular(12),
            ),
            child: SizedBox(
              height: 120,
              child: AdWidget(ad: _nativeAd!),
            ),
          ),
        ],
      ),
    );
  }
}
