import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import '../../../core/config/admob_config.dart';

/// Adaptive Banner Ad Widget — Reusable component
///
/// Automatically adjusts to screen width and orientation.
/// Shows loading state while ad loads, gracefully handles errors.
/// Does NOT show on Login, Register, OTP, Checkout, Payment, Chat, or Camera screens.
///
/// Usage:
///   const BannerAdWidget(adUnitKey: 'bannerHome')
///   const BannerAdWidget(adUnitKey: 'bannerProfile')
///   const BannerAdWidget(adUnitKey: 'bannerWishlist')
class BannerAdWidget extends ConsumerStatefulWidget {
  /// Ad Unit key in AdMobConfig (e.g., 'bannerHome', 'bannerProfile', 'bannerWishlist')
  final String adUnitKey;

  const BannerAdWidget({super.key, required this.adUnitKey});

  @override
  ConsumerState<BannerAdWidget> createState() => _BannerAdWidgetState();
}

class _BannerAdWidgetState extends ConsumerState<BannerAdWidget> {
  BannerAd? _bannerAd;
  bool _isLoaded = false;
  bool _hasError = false;

  @override
  void initState() {
    super.initState();
    _loadAd();
  }

  @override
  void dispose() {
    _bannerAd?.dispose();
    super.dispose();
  }

  void _loadAd() {
    final config = ref.read(admobConfigProvider);
    final adUnitId = _getAdUnitId(config);

    if (adUnitId == null) {
      setState(() => _hasError = true);
      return;
    }

    BannerAd(
      adUnitId: adUnitId,
      size: AdSize.getCurrentOrientationInlineAdaptiveBanner(
        MediaQuery.of(context).size.width,
      ),
      request: const AdRequest(),
      listener: BannerAdListener(
        onAdLoaded: (ad) {
          setState(() {
            _bannerAd = ad as BannerAd;
            _isLoaded = true;
          });
        },
        onAdFailedToLoad: (ad, error) {
          ad.dispose();
          setState(() => _hasError = true);
        },
        onAdOpened: () {
          debugPrint('AdMob Banner: opened');
        },
        onAdClosed: () {
          debugPrint('AdMob Banner: closed');
        },
        onAdImpression: () {
          debugPrint('AdMob Banner: impression logged');
        },
      ),
    ).load();
  }

  String? _getAdUnitId(AdMobConfig config) {
    switch (widget.adUnitKey) {
      case 'bannerHome':
        return config.bannerHome;
      case 'bannerProfile':
        return config.bannerProfile;
      case 'bannerWishlist':
        return config.bannerWishlist;
      default:
        return null;
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_hasError) {
      return const SizedBox.shrink(); // Gracefully hide on error
    }

    if (!_isLoaded || _bannerAd == null) {
      // Loading skeleton matching banner dimensions
      return Container(
        height: 60,
        margin: const EdgeInsets.symmetric(vertical: 8),
        decoration: BoxDecoration(
          color: Colors.grey.shade100,
          borderRadius: BorderRadius.circular(12),
        ),
        child: const Center(
          child: SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
        ),
      );
    }

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: SafeArea(
        top: false,
        bottom: false,
        child: SizedBox(
          width: _bannerAd!.size.width.toDouble(),
          height: _bannerAd!.size.height.toDouble(),
          child: AdWidget(ad: _bannerAd!),
        ),
      ),
    );
  }
}
