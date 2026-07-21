import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/utils/validators.dart';
import '../../../core/utils/extensions.dart';
import '../../../core/routing/route_names.dart';
import '../../../presentation/providers/auth_provider.dart';

/// Extracts the email from the query parameter.
final emailQueryProvider = Provider<String?>((ref) => null);

class OtpVerifyScreen extends ConsumerStatefulWidget {
  const OtpVerifyScreen({super.key});

  @override
  ConsumerState<OtpVerifyScreen> createState() => _OtpVerifyScreenState();
}

class _OtpVerifyScreenState extends ConsumerState<OtpVerifyScreen> {
  final _formKey = GlobalKey<FormState>();
  final _otpController = TextEditingController();
  bool _isResending = false;
  int _resendCooldown = 0;

  /// Get email from query parameter or use a fallback.
  String get _email {
    final uri = GoRouterState.of(context).uri;
    return uri.queryParameters['email'] ?? '';
  }

  @override
  void dispose() {
    _otpController.dispose();
    super.dispose();
  }

  Future<void> _handleVerify() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    final email = _email;
    if (email.isEmpty) {
      context.showSnackBar('Email tidak ditemukan', isError: true);
      return;
    }

    final response = await ref.read(authProvider.notifier).verifyOtp(
          email: email,
          otpCode: _otpController.text.trim(),
        );

    if (response != null && response.success && mounted) {
      final state = ref.read(authProvider);
      if (state.isSeller) {
        context.go(RouteNames.sellerDashboard);
      } else {
        context.go(RouteNames.home);
      }
    }
  }

  Future<void> _handleResend() async {
    if (_isResending || _resendCooldown > 0) return;

    setState(() => _isResending = true);

    final email = _email;
    if (email.isNotEmpty) {
      final response = await ref.read(authProvider.notifier).requestOtp(
            email: email,
            purpose: 'registration',
          );

      if (response != null && response.success && mounted) {
        context.showSnackBar('Kode OTP telah dikirim ulang');
        _startCooldown();
      } else if (mounted) {
        context.showSnackBar(
          response?.message ?? 'Gagal mengirim ulang OTP',
          isError: true,
        );
      }
    }

    if (mounted) setState(() => _isResending = false);
  }

  void _startCooldown() {
    const maxCooldown = 60; // seconds, matches backend OTP_COOLDOWN_SECONDS
    setState(() => _resendCooldown = maxCooldown);

    Future.doWhile(() async {
      await Future.delayed(const Duration(seconds: 1));
      if (!mounted) return false;
      setState(() {
        _resendCooldown--;
      });
      return _resendCooldown > 0;
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final authState = ref.watch(authProvider);
    final email = _email;

    return Scaffold(
      appBar: AppBar(title: const Text('Verifikasi OTP')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            children: [
              const SizedBox(height: 32),
              Icon(
                Icons.mail_lock_rounded,
                size: 80,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(height: 16),
              Text(
                'Verifikasi Email Anda',
                style: theme.textTheme.headlineSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                email.isNotEmpty
                    ? 'Kode OTP telah dikirim ke $email'
                    : 'Masukkan kode OTP yang telah dikirim ke email Anda',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 32),

              // ── Error Message ──
              if (authState.errorMessage != null) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.error.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                        color: theme.colorScheme.error.withOpacity(0.3)),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.error_outline,
                          color: theme.colorScheme.error, size: 20),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          authState.errorMessage!,
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.error,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
              ],

              // ── OTP Input ──
              TextFormField(
                controller: _otpController,
                textAlign: TextAlign.center,
                style: const TextStyle(
                    fontSize: 32, fontWeight: FontWeight.bold, letterSpacing: 12),
                keyboardType: TextInputType.number,
                maxLength: 6,
                decoration: InputDecoration(
                  counterText: '',
                  hintText: '000000',
                  hintStyle: TextStyle(
                    fontSize: 32,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 12,
                    color: theme.colorScheme.onSurface.withOpacity(0.2),
                  ),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                validator: Validators.otpCode,
                onFieldSubmitted: (_) => _handleVerify(),
              ),
              const SizedBox(height: 24),

              // ── Verify Button ──
              FilledButton(
                onPressed: authState.status == AuthStatus.loading
                    ? null
                    : _handleVerify,
                style: FilledButton.styleFrom(
                  minimumSize: const Size(double.infinity, 52),
                ),
                child: authState.status == AuthStatus.loading
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Text('Verifikasi'),
              ),
              const SizedBox(height: 16),

              // ── Resend OTP ──
              TextButton(
                onPressed:
                    _resendCooldown > 0 ? null : _handleResend,
                child: _resendCooldown > 0
                    ? Text('Kirim ulang dalam $_resendCooldown detik')
                    : (_isResending
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Kirim ulang kode')),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
