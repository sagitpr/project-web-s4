import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/dio_client.dart';
import '../../core/constants/api_constants.dart';

/// Provider for PaymentApi.
final paymentApiProvider = Provider<PaymentApi>((ref) {
  return PaymentApi(ref.watch(apiClientProvider));
});

/// Payment API datasource.
class PaymentApi {
  final ApiClient _client;

  PaymentApi(this._client);

  /// Get available payment methods.
  Future<ApiResponse> getPaymentMethods() async {
    return _client.get(ApiConstants.paymentMethods);
  }

  /// Get payment configuration (Midtrans client key etc.).
  Future<ApiResponse> getPaymentConfig() async {
    return _client.get(ApiConstants.paymentConfig);
  }

  /// Get public API configuration (safe frontend keys).
  Future<ApiResponse> getPublicApiConfig() async {
    return _client.get(ApiConstants.publicApiConfig);
  }

  /// Create a Midtrans Snap transaction.
  Future<ApiResponse> createSnapTransaction({
    required int orderId,
    required double grossAmount,
    String? customerName,
    String? customerEmail,
    String? customerPhone,
  }) async {
    return _client.post(ApiConstants.createSnapTransaction, data: {
      'order_id': orderId,
      'gross_amount': grossAmount,
      if (customerName != null) 'customer_name': customerName,
      if (customerEmail != null) 'customer_email': customerEmail,
      if (customerPhone != null) 'customer_phone': customerPhone,
    });
  }

  /// Get payment status for an order.
  Future<ApiResponse> getPaymentStatus(int orderId) async {
    final path =
        ApiConstants.paymentStatus.replaceAll('{order_id}', orderId.toString());
    return _client.get(path);
  }

  /// Get payment history.
  Future<ApiResponse> getPaymentHistory({int page = 1}) async {
    return _client.get(
      ApiConstants.paymentHistory,
      queryParameters: {'page': page},
    );
  }

  /// Get wallet balance.
  Future<ApiResponse> getWalletBalance() async {
    return _client.get(ApiConstants.walletBalance);
  }

  /// Get wallet transactions.
  Future<ApiResponse> getWalletTransactions({int page = 1}) async {
    return _client.get(
      ApiConstants.walletTransactions,
      queryParameters: {'page': page},
    );
  }

  /// Top up wallet.
  Future<ApiResponse> walletTopUp({required double amount}) async {
    return _client.post(ApiConstants.walletTopUp, data: {
      'amount': amount,
    });
  }

  /// Get finance summary (seller).
  Future<ApiResponse> getFinanceSummary() async {
    return _client.get(ApiConstants.financeSummary);
  }

  /// Get finance transactions (seller).
  Future<ApiResponse> getFinanceTransactions({int page = 1}) async {
    return _client.get(
      ApiConstants.financeTransactions,
      queryParameters: {'page': page},
    );
  }

  /// Get bank accounts (seller).
  Future<ApiResponse> getBankAccounts() async {
    return _client.get(ApiConstants.financeBankAccounts);
  }

  /// Withdraw balance (seller).
  Future<ApiResponse> withdrawBalance({
    required double amount,
    required int bankAccountId,
  }) async {
    return _client.post(ApiConstants.withdrawBalance, data: {
      'amount': amount,
      'bank_account_id': bankAccountId,
    });
  }
}
