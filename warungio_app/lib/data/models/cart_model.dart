/// Model representing a cart item from the backend orders cart endpoint.
class CartItemModel {
  final int id;
  final int productId;
  final String productName;
  final String? productImage;
  final double price;
  final int quantity;
  final int maxQuantity;
  final String? unit;
  final String? note;

  CartItemModel({
    required this.id,
    required this.productId,
    required this.productName,
    this.productImage,
    required this.price,
    required this.quantity,
    this.maxQuantity = 999,
    this.unit,
    this.note,
  });

  factory CartItemModel.fromJson(Map<String, dynamic> json) {
    // Handle nested product object or flat structure
    int productId;
    String productName;
    String? productImage;
    double price;
    String? unit;

    final product = json['product'];
    if (product is Map<String, dynamic>) {
      productId = product['id'] as int? ?? 0;
      productName = product['product_name'] as String? ?? '';
      productImage = product['image'] as String?;
      price = (product['price'] as num?)?.toDouble() ?? 0.0;
      unit = product['unit'] as String?;
    } else {
      productId = (product as int?) ?? (json['product_id'] as int? ?? 0);
      productName = json['product_name'] as String? ?? '';
      productImage = json['image_url'] as String? ?? json['image'] as String?;
      price = (json['price'] as num?)?.toDouble() ?? 0.0;
      unit = json['unit'] as String?;
    }

    return CartItemModel(
      id: json['id'] as int,
      productId: productId,
      productName: productName,
      productImage: productImage,
      price: price,
      quantity: json['quantity'] as int? ?? 0,
      maxQuantity: json['max_quantity'] as int? ?? json['stock'] as int? ?? 999,
      unit: unit,
      note: json['note'] as String?,
    );
  }

  double get subtotal => price * quantity;

  Map<String, dynamic> toJson() {
    return {
      'product': productId,
      'quantity': quantity,
    };
  }
}

/// Cart summary from the backend.
class CartSummaryModel {
  final List<CartItemModel> items;
  final int totalItems;
  final double totalPrice;

  CartSummaryModel({
    required this.items,
    this.totalItems = 0,
    this.totalPrice = 0.0,
  });

  factory CartSummaryModel.fromJson(Map<String, dynamic> json) {
    final List<dynamic> rawItems = json['data']?['items'] ??
        json['items'] ??
        json['results'] ??
        json['data'] ??
        [];
    final items = rawItems
        .map((e) => CartItemModel.fromJson(e as Map<String, dynamic>))
        .toList();

    return CartSummaryModel(
      items: items,
      totalItems: json['total_items'] as int? ?? items.length,
      totalPrice: (json['total_price'] as num?)?.toDouble() ??
          items.fold(0.0, (sum, item) => sum + item.subtotal),
    );
  }
}
