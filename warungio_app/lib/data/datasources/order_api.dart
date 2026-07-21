import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/network/dio_client.dart';
import '../../core/constants/api_constants.dart';
import '../models/cart_model.dart';
import '../models/order_model.dart';
import '../models/shipping_model.dart';

/// Provider for OrderApi.
final orderApiProvider = Provider<OrderApi>((ref) {
  return OrderApi(ref.watch(apiClientProvider));
});

/// Order API datasource.
/// Communicates with the Warungio Django REST orders endpoints.
class OrderApi {
  final ApiClient _client;

  OrderApi(this._client);

  // ── Cart Operations ────────────────────────────────────────────────────

  /// Get current user's cart items.
  Future<ApiResponse> getCart() async {
    return _client.get(ApiConstants.cartList);
  }

  /// Get cart item count.
  Future<ApiResponse> getCartCount() async {
    return _client.get(ApiConstants.cartCount);
  }

  /// Add item to cart.
  Future<ApiResponse> addToCart({
    required int productId,
    int quantity = 1,
  }) async {
    return _client.post(ApiConstants.cartList, data: {
      'product': productId,
      'quantity': quantity,
    });
  }

  /// Update cart item quantity.
  Future<ApiResponse> updateCartItem(int itemId, int quantity) async {
    final path = ApiConstants.cartDetail.replaceAll('{id}', itemId.toString());
    return _client.patch(path, data: {'quantity': quantity});
  }

  /// Remove item from cart.
  Future<ApiResponse> removeFromCart(int itemId) async {
    final path = ApiConstants.cartDetail.replaceAll('{id}', itemId.toString());
    return _client.delete(path);
  }

  /// Clear entire cart.
  Future<ApiResponse> clearCart() async {
    return _client.post(ApiConstants.cartClear);
  }

  // ── Shipping Methods ───────────────────────────────────────────────────

  /// Get available shipping methods.
  Future<ApiResponse> getShippingMethods() async {
    return _client.get(ApiConstants.shippingMethods);
  }

  // ── Order Operations ────────────────────────────────────────────────────

  /// Create a new order (checkout).
  Future<ApiResponse> createOrder({
    required int addressId,
    required int shippingMethodId,
    String? notes,
    int? voucherId,
  }) async {
    return _client.post(ApiConstants.orderCreate, data: {
      'address_id': addressId,
      'shipping_method_id': shippingMethodId,
      if (notes != null) 'notes': notes,
      if (voucherId != null) 'voucher_id': voucherId,
    });
  }

  /// Get current user's orders.
  Future<ApiResponse> getMyOrders({int page = 1, String? status}) async {
    final params = <String, dynamic>{'page': page};
    if (status != null) params['status'] = status;
    return _client.get(ApiConstants.myOrders, queryParameters: params);
  }

  /// Get order history.
  Future<ApiResponse> getOrderHistory({int page = 1}) async {
    return _client.get(
      ApiConstants.orderHistory,
      queryParameters: {'page': page},
    );
  }

  /// Get order detail by ID.
  Future<ApiResponse> getOrderDetail(int orderId) async {
    final path = ApiConstants.orderDetail.replaceAll('{id}', orderId.toString());
    return _client.get(path);
  }

  /// Get seller's orders.
  Future<ApiResponse> getSellerOrders({int page = 1, String? status}) async {
    final params = <String, dynamic>{'page': page};
    if (status != null) params['status'] = status;
    return _client.get(ApiConstants.sellerOrders, queryParameters: params);
  }

  /// Update order status (seller).
  Future<ApiResponse> updateOrderStatus(int orderId, String status) async {
    final path = ApiConstants.orderStatusUpdate
        .replaceAll('{order_id}', orderId.toString());
    return _client.post(path, data: {'status': status});
  }

  /// Cancel order (buyer).
  Future<ApiResponse> cancelOrder(int orderId, {String? reason}) async {
    final path = ApiConstants.orderCancel
        .replaceAll('{order_id}', orderId.toString());
    return _client.post(path, data: {
      if (reason != null) 'reason': reason,
    });
  }

  /// Get delivery tracking info.
  Future<ApiResponse> getDeliveryTracking(int orderId) async {
    final path = ApiConstants.deliveryTracking
        .replaceAll('{order_id}', orderId.toString());
    return _client.get(path);
  }
}

/// Riverpod provider.
final orderRepositoryProvider = Provider<OrderRepository>((ref) {
  return OrderRepository(ref.watch(orderApiProvider));
});

/// Repository for order/cart operations.
class OrderRepository {
  final OrderApi _api;

  OrderRepository(this._api);

  Future<ApiResponse> getCart() => _api.getCart();
  Future<ApiResponse> getCartCount() => _api.getCartCount();
  Future<ApiResponse> addToCart(int productId, {int quantity = 1}) =>
      _api.addToCart(productId: productId, quantity: quantity);
  Future<ApiResponse> updateCartItem(int itemId, int quantity) =>
      _api.updateCartItem(itemId, quantity);
  Future<ApiResponse> removeFromCart(int itemId) =>
      _api.removeFromCart(itemId);
  Future<ApiResponse> clearCart() => _api.clearCart();
  Future<ApiResponse> getShippingMethods() => _api.getShippingMethods();
  Future<ApiResponse> createOrder({
    required int addressId,
    required int shippingMethodId,
    String? notes,
    int? voucherId,
  }) =>
      _api.createOrder(
        addressId: addressId,
        shippingMethodId: shippingMethodId,
        notes: notes,
        voucherId: voucherId,
      );
  Future<ApiResponse> getMyOrders({int page = 1, String? status}) =>
      _api.getMyOrders(page: page, status: status);
  Future<ApiResponse> getOrderDetail(int orderId) =>
      _api.getOrderDetail(orderId);
  Future<ApiResponse> cancelOrder(int orderId, {String? reason}) =>
      _api.cancelOrder(orderId, reason: reason);
  Future<ApiResponse> getDeliveryTracking(int orderId) =>
      _api.getDeliveryTracking(orderId);
}
