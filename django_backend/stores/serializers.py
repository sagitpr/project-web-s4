"""
Stores serializers for Warungio Marketplace.
"""

from rest_framework import serializers
from .models import Store, StoreFollower, StoreCategory


class StoreCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreCategory
        fields = '__all__'


class StoreListSerializer(serializers.ModelSerializer):
    """Lightweight store serializer for listing."""
    owner_name = serializers.CharField(source='user.full_name', read_only=True)
    owner_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Store
        fields = ('id', 'store_name', 'slug', 'category', 'city', 'province',
                  'store_logo', 'status', 'follower_count', 'product_count',
                  'rating_avg', 'total_sales', 'is_open', 'owner_name',
                  'owner_email', 'created_at')


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

    def get_owner(self, obj):
        return {
            'id': obj.user.id,
            'full_name': obj.user.full_name,
            'email': obj.user.email,
            'phone': str(obj.user.phone) if obj.user.phone else None,
            'profile_photo': obj.user.profile_photo.url if obj.user.profile_photo else None,
        }

    def get_store_logo_url(self, obj):
        if obj.store_logo:
            return obj.store_logo.url
        return None

    def get_store_banner_url(self, obj):
        if obj.store_banner:
            return obj.store_banner.url
        return None


class StoreCreateSerializer(serializers.ModelSerializer):
    """Store registration serializer."""
    class Meta:
        model = Store
        fields = ('store_name', 'category', 'description', 'address', 'city',
                  'province', 'postal_code', 'latitude', 'longitude',
                  'open_time', 'close_time', 'delivery_type', 'service_area',
                  'bank_name', 'bank_account', 'bank_owner', 'store_logo',
                  'store_banner')

    def validate_store_name(self, value):
        if Store.objects.filter(store_name__iexact=value).exists():
            raise serializers.ValidationError("Nama toko sudah digunakan.")
        return value


class StoreUpdateSerializer(serializers.ModelSerializer):
    """Store update serializer."""
    class Meta:
        model = Store
        fields = ('store_name', 'category', 'description', 'address', 'city',
                  'province', 'postal_code', 'latitude', 'longitude',
                  'open_time', 'close_time', 'delivery_type', 'service_area',
                  'bank_name', 'bank_account', 'bank_owner', 'store_logo',
                  'store_banner', 'is_open')


class StoreFollowerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreFollower
        fields = ('id', 'user', 'store', 'created_at')
        read_only_fields = ('user', 'created_at')
