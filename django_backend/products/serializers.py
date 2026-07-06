"""
Products serializers for Warungio Marketplace.
"""

from rest_framework import serializers
from .models import Category, Product, ProductGallery, Review, Favorite, Promo, RecentlyViewed, Voucher, QualityCheck


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ProductGallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductGallery
        fields = ('id', 'image', 'order')


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight product serializer for listings."""
    store_name = serializers.CharField(source='store.store_name', read_only=True)
    store_slug = serializers.CharField(source='store.slug', read_only=True)
    category_name = serializers.CharField(source='category.category_name', read_only=True)
    product_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ('id', 'product_name', 'slug', 'price', 'stock', 'unit',
                  'product_photo_url', 'product_status', 'quality_score',
                  'sold_count', 'rating_avg', 'review_count', 'store_name',
                  'store_slug', 'category_name', 'is_featured', 'is_active',
                  'created_at')

    def get_product_photo_url(self, obj):
        if obj.product_photo:
            return obj.product_photo.url
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """Detailed product serializer with gallery and reviews."""
    store = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True)
    gallery = ProductGallerySerializer(many=True, read_only=True)
    product_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = '__all__'

    def get_store(self, obj):
        return {
            'id': obj.store.id,
            'store_name': obj.store.store_name,
            'slug': obj.store.slug,
            'store_logo': obj.store.store_logo.url if obj.store.store_logo else None,
            'city': obj.store.city,
            'rating_avg': float(obj.store.rating_avg),
            'follower_count': obj.store.follower_count,
        }

    def get_product_photo_url(self, obj):
        if obj.product_photo:
            return obj.product_photo.url
        return None


class ProductCreateSerializer(serializers.ModelSerializer):
    """Product creation serializer."""
    class Meta:
        model = Product
        fields = ('id', 'category', 'product_name', 'description', 'product_photo',
                  'price', 'stock', 'unit', 'product_status', 'is_featured')
        extra_kwargs = {
            'price': {'required': True},
            'stock': {'required': True},
        }

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Harga harus lebih dari 0.")
        return value

    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError("Stok tidak boleh negatif.")
        return value

    def validate_product_photo(self, value):
        from .validators import validate_image_file
        return validate_image_file(value)


class ProductUpdateSerializer(serializers.ModelSerializer):
    """Product update serializer."""
    class Meta:
        model = Product
        fields = ('category', 'product_name', 'description', 'product_photo',
                  'price', 'stock', 'unit', 'product_status', 'is_active',
                  'is_featured')

    def validate_product_photo(self, value):
        from .validators import validate_image_file
        return validate_image_file(value)


class ReviewSerializer(serializers.ModelSerializer):
    """Review serializer."""
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_photo = serializers.SerializerMethodField()
    product_name = serializers.CharField(source='product.product_name', read_only=True)

    class Meta:
        model = Review
        fields = ('id', 'user', 'user_name', 'user_photo', 'product', 'product_name',
                  'rating', 'comment', 'is_verified', 'seller_reply', 'seller_reply_at', 'created_at')
        read_only_fields = ('user', 'product', 'is_verified', 'created_at', 'seller_reply', 'seller_reply_at')

    def get_user_photo(self, obj):
        if obj.user and obj.user.profile_photo:
            return obj.user.profile_photo.url
        return None

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating harus antara 1-5.")
        return value


class FavoriteSerializer(serializers.ModelSerializer):
    """Favorite/wishlist serializer."""
    product_detail = ProductListSerializer(source='product', read_only=True)

    class Meta:
        model = Favorite
        fields = ('id', 'user', 'product', 'product_detail', 'created_at')
        read_only_fields = ('user', 'created_at')


class PromoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promo
        fields = '__all__'


class QualityCheckSerializer(serializers.ModelSerializer):
    """Quality check result serializer."""
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    store_name = serializers.CharField(source='product.store.store_name', read_only=True)

    class Meta:
        model = QualityCheck
        fields = ('id', 'product', 'product_name', 'store_name', 'freshness_score',
                  'stock_status', 'ai_result', 'quality_status', 'checked_at', 'created_at')
        read_only_fields = ('checked_at', 'created_at')


class RecentlyViewedSerializer(serializers.ModelSerializer):
    """Recently viewed product serializer."""
    product_detail = ProductListSerializer(source='product', read_only=True)

    class Meta:
        model = RecentlyViewed
        fields = ('id', 'user', 'product', 'product_detail', 'viewed_at')
        read_only_fields = ('user', 'viewed_at')


class VoucherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voucher
        fields = '__all__'
