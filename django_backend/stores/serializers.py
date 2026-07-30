"""
Stores serializers for Warungio Marketplace.
"""

from rest_framework import serializers
from .models import Store, StoreFollower, StoreCategory
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.openapi import OpenApiTypes


class StoreCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreCategory
        fields = '__all__'


class StoreListSerializer(serializers.ModelSerializer):
    """Lightweight store serializer for listing."""
    owner_name = serializers.CharField(source='user.full_name', read_only=True)
    owner_email = serializers.EmailField(source='user.email', read_only=True)
    store_logo_url = serializers.SerializerMethodField()
    store_banner_url = serializers.SerializerMethodField()
    featured_products = serializers.SerializerMethodField()
    has_active_promo = serializers.BooleanField(read_only=True, default=False)
    active_promo_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Store
        fields = ('id', 'store_name', 'slug', 'category', 'city', 'province',
                  'district', 'description', 'address',
                  'store_logo', 'store_logo_url', 'store_banner_url',
                  'status', 'follower_count', 'product_count',
                  'rating_avg', 'total_sales', 'is_open', 'owner_name',
                  'owner_email', 'created_at', 'open_time', 'close_time',
                  'featured_products', 'has_active_promo', 'active_promo_count')

    @extend_schema_field(OpenApiTypes.STR)
    def get_store_logo_url(self, obj):
        if obj.store_logo:
            return obj.store_logo.url
        return None

    @extend_schema_field(OpenApiTypes.STR)
    def get_store_banner_url(self, obj):
        if obj.store_banner:
            return obj.store_banner.url
        return None

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_featured_products(self, obj):
        products = getattr(obj, '_featured_products', [])
        result = []
        for p in products:
            item = {
                'id': p.id,
                'product_name': p.product_name,
                'slug': p.slug,
                'price': float(p.price),
                'product_photo_url': p.product_photo.url if p.product_photo else None,
                'sold_count': p.sold_count,
                'rating_avg': float(p.rating_avg) if p.rating_avg else 0,
            }
            result.append(item)
        return result


class StoreDetailSerializer(serializers.ModelSerializer):
    """Detailed store serializer."""
    owner = serializers.SerializerMethodField()
    store_logo_url = serializers.SerializerMethodField()
    store_banner_url = serializers.SerializerMethodField()

    class Meta:
        model = Store
        fields = '__all__'
        read_only_fields = ('user', 'follower_count', 'product_count',
                           'rating_avg', 'total_sales', 'created_at', 'updated_at')

    @extend_schema_field(OpenApiTypes.STR)


    def get_owner(self, obj):
        return {
            'id': obj.user.id,
            'full_name': obj.user.full_name,
            'email': obj.user.email,
            'phone': str(obj.user.phone) if obj.user.phone else None,
            'profile_photo': obj.user.profile_photo.url if obj.user.profile_photo else None,
        }

    @extend_schema_field(OpenApiTypes.STR)
    def get_store_logo_url(self, obj):
        if obj.store_logo:
            return obj.store_logo.url
        return None

    @extend_schema_field(OpenApiTypes.STR)
    def get_store_banner_url(self, obj):
        if obj.store_banner:
            return obj.store_banner.url
        return None


class StoreCreateSerializer(serializers.ModelSerializer):
    """Store registration serializer with full region hierarchy."""
    class Meta:
        model = Store
        fields = ('id', 'store_name', 'category', 'description', 'address',
                  'province', 'province_code',
                  'city', 'city_code',
                  'district', 'district_code',
                  'village', 'village_code',
                  'postal_code', 'latitude', 'longitude',
                  'open_time', 'close_time', 'delivery_type', 'service_area',
                  'bank_name', 'bank_account', 'bank_owner', 'store_logo',
                  'store_banner')

    def validate_store_name(self, value):
        if Store.objects.filter(store_name__iexact=value).exists():
            raise serializers.ValidationError("Nama toko sudah digunakan.")
        return value

    def validate_store_logo(self, value):
        from products.validators import validate_image_file
        return validate_image_file(value)

    def validate_store_banner(self, value):
        from products.validators import validate_image_file
        return validate_image_file(value)


class StoreUpdateSerializer(serializers.ModelSerializer):
    """Store update serializer with full region hierarchy."""
    class Meta:
        model = Store
        fields = ('store_name', 'category', 'description', 'address',
                  'province', 'province_code',
                  'city', 'city_code',
                  'district', 'district_code',
                  'village', 'village_code',
                  'postal_code', 'latitude', 'longitude',
                  'open_time', 'close_time', 'delivery_type', 'service_area',
                  'bank_name', 'bank_account', 'bank_owner', 'store_logo',
                  'store_banner', 'is_open')

    def validate_store_logo(self, value):
        from products.validators import validate_image_file
        return validate_image_file(value)

    def validate_store_banner(self, value):
        from products.validators import validate_image_file
        return validate_image_file(value)


class StoreFollowerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreFollower
        fields = ('id', 'user', 'store', 'created_at')
        read_only_fields = ('user', 'created_at')
