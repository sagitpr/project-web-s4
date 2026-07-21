import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/dio_client.dart';
import '../../core/constants/api_constants.dart';

/// Provider for LoyaltyApi.
final loyaltyApiProvider = Provider<LoyaltyApi>((ref) {
  return LoyaltyApi(ref.watch(apiClientProvider));
});

/// Loyalty Program API datasource.
class LoyaltyApi {
  final ApiClient _client;

  LoyaltyApi(this._client);

  /// Get loyalty points and account info.
  Future<ApiResponse> getPoints() async {
    return _client.get(ApiConstants.loyaltyPoints);
  }

  /// Get loyalty account details.
  Future<ApiResponse> getAccount() async {
    return _client.get(ApiConstants.loyaltyAccount);
  }

  /// Get loyalty transaction history.
  Future<ApiResponse> getTransactions({int page = 1}) async {
    return _client.get(
      ApiConstants.loyaltyTransactions,
      queryParameters: {'page': page},
    );
  }

  /// Get available loyalty rewards.
  Future<ApiResponse> getRewards() async {
    return _client.get(ApiConstants.loyaltyRewards);
  }

  /// Get loyalty tiers.
  Future<ApiResponse> getTiers() async {
    return _client.get(ApiConstants.loyaltyTiers);
  }
}
