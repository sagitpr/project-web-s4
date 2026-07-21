import 'package:flutter_test/flutter_test.dart';
import 'package:warungio_app/data/models/product_model.dart';

void main() {
  group('ProductModel', () {
    final mockJson = {
      'id': 1,
      'store': 10,
      'store_name': 'Toko Segar',
      'product_name': 'Beras Premium 5kg',
      'description': 'Beras kualitas terbaik',
      'price': 75000.0,
      'stock': 50,
      'unit': 'kg',
      'slug': 'beras-premium-5kg',
      'image': '/media/products/beras.jpg',
      'category_name': 'Bahan Pokok',
      'category': 5,
      'rating_avg': 4.5,
      'review_count': 120,
      'sold_count': 500,
      'is_active': true,
      'product_status': 'active',
      'created_at': '2026-07-21T10:00:00Z',
    };

    test('fromJson creates correct ProductModel', () {
      final product = ProductModel.fromJson(mockJson);

      expect(product.id, 1);
      expect(product.store, 10);
      expect(product.storeName, 'Toko Segar');
      expect(product.productName, 'Beras Premium 5kg');
      expect(product.description, 'Beras kualitas terbaik');
      expect(product.price, 75000.0);
      expect(product.stock, 50);
      expect(product.unit, 'kg');
      expect(product.slug, 'beras-premium-5kg');
      expect(product.image, '/media/products/beras.jpg');
      expect(product.categoryName, 'Bahan Pokok');
      expect(product.ratingAvg, 4.5);
      expect(product.reviewCount, 120);
      expect(product.soldCount, 500);
      expect(product.isActive, true);
    });

    test('fromJson handles minimal data gracefully', () {
      final minimalJson = {
        'id': 2,
        'store': 10,
        'product_name': 'Gula Pasir 1kg',
        'price': 15000.0,
        'stock': 100,
        'unit': 'kg',
      };
      final product = ProductModel.fromJson(minimalJson);

      expect(product.id, 2);
      expect(product.productName, 'Gula Pasir 1kg');
      expect(product.price, 15000.0);
      expect(product.stock, 100);
      expect(product.isActive, true);
      expect(product.ratingAvg, isNull);
    });

    test('price defaults to 0.0 when missing', () {
      final json = {'id': 3, 'store': 1, 'product_name': 'Test', 'stock': 10, 'unit': 'pcs'};
      final product = ProductModel.fromJson(json);
      expect(product.price, 0.0);
    });

    test('formattedPrice formats correctly', () {
      final product = ProductModel.fromJson({
        ...mockJson,
        'price': 75000,
      });
      // Verify it contains formatted price
      expect(product.formattedPrice, contains('Rp'));
      expect(product.formattedPrice, contains('75'));
    });

    test('toJson returns correct map', () {
      final product = ProductModel.fromJson(mockJson);
      final json = product.toJson();

      expect(json['id'], 1);
      expect(json['product_name'], 'Beras Premium 5kg');
      expect(json['price'], 75000.0);
    });

    test('stock information is correct', () {
      final inStock = ProductModel.fromJson({...mockJson, 'stock': 10});
      final outOfStock = ProductModel.fromJson({...mockJson, 'stock': 0});

      expect(inStock.stock, 10);
      expect(outOfStock.stock, 0);
    });
  });
}
