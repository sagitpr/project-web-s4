/// Model representing an order item.
class OrderItemModel {
  final int id;
  final int productId;
  final String productName;
  final String? productImage;
  final double price;
  final int quantity;
  final String? unit;

  OrderItemModel({
    required this.id,
    required this.productId,
    required this.productName,
    this.productImage,
    required this.price,
    required this.quantity,
    this.unit,
  });

  factory OrderItemModel.fromJson(Map<String, dynamic> json) {
    final product = json['product'];
    int productId;
    String productName;
    String? productImage;

    if (product is Map<String, dynamic>) {
      productId = product['id'] as int? ?? 0;
      productName = product['product_name'] as String? ?? '';
      productImage = product['image'] as String?;
    } else {
      productId = (product as int?) ?? 0;
      productName = json['product_name'] as String? ?? '';
      productImage = json['image'] as String?;
    }

    return OrderItemModel(
      id: json['id'] as int,
      productId: productId,
      productName: productName,
      productImage: productImage,
      price: (json['price'] as num?)?.toDouble() ?? 0.0,
      quantity: json['quantity'] as int? ?? 0,
      unit: json['unit'] as String?,
    );
  }

  double get subtotal => price * quantity;
}

/// Model representing an order from the backend.
class OrderModel {
  final int id;
  final String orderId;
  final List<OrderItemModel> items;
  final double subtotal;
  final double shippingCost;
  final double adminFee;
  final double totalAmount;
  final String status;
  final String? paymentStatus;
  final String? paymentMethod;
  final String? snapToken;
  final String? shippingMethodName;
  final String? shippingAddress;
  final String? courier;
  final String? trackingNumber;
  final String? notes;
  final int? storeId;
  final String? storeName;
  final DateTime createdAt;
  final DateTime? paidAt;

  OrderModel({
    required this.id,
    required this.orderId,
    this.items = const [],
    this.subtotal = 0.0,
    this.shippingCost = 0.0,
    this.adminFee = 0.0,
    this.totalAmount = 0.0,
    this.status = 'pending',
    this.paymentStatus,
    this.paymentMethod,
    this.snapToken,
    this.shippingMethodName,
    this.shippingAddress,
    this.courier,
    this.trackingNumber,
    this.notes,
    this.storeId,
    this.storeName,
    required this.createdAt,
    this.paidAt,
  });

  factory OrderModel.fromJson(Map<String, dynamic> json) {
    final List<dynamic> rawItems =
        json['items'] as List<dynamic>? ?? json['order_items'] as List<dynamic>? ?? [];
    final items = rawItems
        .map((e) => OrderItemModel.fromJson(e as Map<String, dynamic>))
        .toList();

    return OrderModel(
      id: json['id'] as int,
      orderId: json['order_id'] as String? ?? json['id'].toString(),
      items: items,
      subtotal: (json['subtotal'] as num?)?.toDouble() ?? 0.0,
      shippingCost: (json['shipping_cost'] as num?)?.toDouble() ?? 0.0,
      adminFee: (json['admin_fee'] as num?)?.toDouble() ?? 0.0,
      totalAmount: (json['total_amount'] as num?)?.toDouble() ?? 0.0,
      status: json['status'] as String? ?? 'pending',
      paymentStatus: json['payment_status'] as String?,
      paymentMethod: json['payment_method'] as String?,
      snapToken: json['snap_token'] as String?,
      shippingMethodName: json['shipping_method_name'] as String?,
      shippingAddress: json['shipping_address'] as String?,
      courier: json['courier'] as String?,
      trackingNumber: json['tracking_number'] as String?,
      notes: json['notes'] as String?,
      storeId: json['store'] as int?,
      storeName: json['store_name'] as String?,
      createdAt: DateTime.parse(
          json['created_at'] as String? ?? DateTime.now().toIso8601String()),
      paidAt: json['paid_at'] != null
          ? DateTime.tryParse(json['paid_at'] as String)
          : null,
    );
  }
}

/// Order status constants matching backend.
class OrderStatus {
  static const String pending = 'pending';
  static const String confirmed = 'confirmed';
  static const String processing = 'processing';
  static const String packed = 'packed';
  static const String shipped = 'shipped';
  static const String delivered = 'delivered';
  static const String completed = 'completed';
  static const String cancelled = 'cancelled';

  static String label(String status) {
    switch (status) {
      case pending:
        return 'Menunggu Konfirmasi';
      case confirmed:
        return 'Dikonfirmasi';
      case processing:
        return 'Diproses';
      case packed:
        return 'Dikemas';
      case shipped:
        return 'Dikirim';
      case delivered:
        return 'Terkirim';
      case completed:
        return 'Selesai';
      case cancelled:
        return 'Dibatalkan';
      default:
        return status;
    }
  }
}

/// Payment status constants.
class PaymentStatus {
  static const String pending = 'pending';
  static const String success = 'success';
  static const String failed = 'failed';
  static const String expired = 'expired';
  static const String refund = 'refund';
  static const String partialRefund = 'partial_refund';
}
