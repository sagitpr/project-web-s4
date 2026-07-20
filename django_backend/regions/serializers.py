"""
Serializers for the Indonesian region API.
Provides nested and flat serializers optimized for cascading selectors (Provinces/Regencies/Districts/Villages).
Flutter-ready with consistent JSON structure.
"""

from rest_framework import serializers
from .models import Province, Regency, District, Village
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.openapi import OpenApiTypes


class ProvinceSerializer(serializers.ModelSerializer):
    """Basic province serializer — lightweight for list views."""
    regency_count = serializers.SerializerMethodField()

    class Meta:
        model = Province
        fields = ['code', 'name', 'latitude', 'longitude', 'regency_count', 'is_active']

    @extend_schema_field(OpenApiTypes.STR)
    def get_regency_count(self, obj):
        return obj.regencies.filter(is_active=True).count()


class ProvinceDetailSerializer(serializers.ModelSerializer):
    """Detailed province serializer with regency list."""
    regencies = serializers.SerializerMethodField()

    class Meta:
        model = Province
        fields = ['code', 'name', 'latitude', 'longitude', 'is_active', 'regencies']

    @extend_schema_field(OpenApiTypes.STR)
    def get_regencies(self, obj):
        qs = obj.regencies.filter(is_active=True)
        return RegencySerializer(qs, many=True).data


class RegencySerializer(serializers.ModelSerializer):
    """Regency/city serializer with optional district count."""
    display_name = serializers.SerializerMethodField()
    district_count = serializers.SerializerMethodField()
    province_code = serializers.SerializerMethodField()

    class Meta:
        model = Regency
        fields = [
            'code', 'province_code', 'name', 'display_name',
            'type', 'latitude', 'longitude', 'district_count', 'is_active',
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_province_code(self, obj):
        return obj.province.code

    @extend_schema_field(OpenApiTypes.STR)
    def get_display_name(self, obj):
        prefix = 'Kota ' if obj.type == 'kota' else 'Kab. '
        return f"{prefix}{obj.name}"

    @extend_schema_field(OpenApiTypes.STR)
    def get_district_count(self, obj):
        return obj.districts.filter(is_active=True).count()


class RegencyDetailSerializer(serializers.ModelSerializer):
    """Detailed regency serializer with district list."""
    display_name = serializers.SerializerMethodField()
    province_name = serializers.SerializerMethodField()
    province_code = serializers.SerializerMethodField()
    districts = serializers.SerializerMethodField()

    class Meta:
        model = Regency
        fields = [
            'code', 'province_code', 'province_name', 'name', 'display_name',
            'type', 'latitude', 'longitude', 'is_active', 'districts',
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_province_code(self, obj):
        return obj.province.code

    @extend_schema_field(OpenApiTypes.STR)
    def get_province_name(self, obj):
        return obj.province.name

    @extend_schema_field(OpenApiTypes.STR)
    def get_display_name(self, obj):
        prefix = 'Kota ' if obj.type == 'kota' else 'Kab. '
        return f"{prefix}{obj.name}"

    @extend_schema_field(OpenApiTypes.STR)


    def get_districts(self, obj):
        qs = obj.districts.filter(is_active=True)
        return DistrictSerializer(qs, many=True).data


class DistrictSerializer(serializers.ModelSerializer):
    """District serializer with village count."""
    display_name = serializers.SerializerMethodField()
    village_count = serializers.SerializerMethodField()
    regency_name = serializers.CharField(source='regency.name', read_only=True)

    class Meta:
        model = District
        fields = [
            'code', 'regency_code', 'regency_name', 'name', 'display_name',
            'latitude', 'longitude', 'village_count', 'is_active',
        ]

    regency_code = serializers.CharField(source='regency.code', read_only=True)

    def get_display_name(self, obj):
        return f"Kec. {obj.name}"

    @extend_schema_field(OpenApiTypes.STR)
    def get_village_count(self, obj):
        return obj.villages.filter(is_active=True).count()


class DistrictDetailSerializer(serializers.ModelSerializer):
    """Detailed district serializer with village list."""
    display_name = serializers.SerializerMethodField()
    regency_name = serializers.CharField(source='regency.name', read_only=True)
    province_name = serializers.CharField(source='province.name', read_only=True)
    villages = serializers.SerializerMethodField()

    class Meta:
        model = District
        fields = [
            'code', 'regency_code', 'regency_name', 'province_name',
            'name', 'display_name', 'latitude', 'longitude', 'is_active', 'villages',
        ]

    regency_code = serializers.CharField(source='regency.code', read_only=True)

    def get_display_name(self, obj):
        return f"Kec. {obj.name}"

    @extend_schema_field(OpenApiTypes.STR)
    def get_villages(self, obj):
        qs = obj.villages.filter(is_active=True)
        return VillageSerializer(qs, many=True).data


class VillageSerializer(serializers.ModelSerializer):
    """Village/kelurahan serializer."""
    display_name = serializers.SerializerMethodField()
    district_name = serializers.CharField(source='district.name', read_only=True)

    class Meta:
        model = Village
        fields = [
            'code', 'district_code', 'district_name', 'name', 'display_name',
            'type', 'postal_code', 'latitude', 'longitude', 'is_active',
        ]

    district_code = serializers.CharField(source='district.code', read_only=True)

    def get_display_name(self, obj):
        prefix = 'Kel. ' if obj.type == 'kelurahan' else 'Desa '
        return f"{prefix}{obj.name}"


class SearchResultSerializer(serializers.Serializer):
    """Unified search result — works across all region levels."""
    id = serializers.CharField()
    name = serializers.CharField()
    display_name = serializers.CharField()
    type = serializers.CharField()  # 'province', 'regency', 'district', 'village'
    parent_name = serializers.CharField(required=False, allow_blank=True)
    parent_code = serializers.CharField(required=False, allow_blank=True)
    code = serializers.CharField()
    postal_code = serializers.CharField(required=False, allow_blank=True)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)


class RegionPathSerializer(serializers.Serializer):
    """
    Full address path from province down to village.
    Useful for Flutter to display breadcrumb: Province > City > District > Village
    """
    province_code = serializers.CharField()
    province_name = serializers.CharField()
    regency_code = serializers.CharField()
    regency_name = serializers.CharField()
    district_code = serializers.CharField()
    district_name = serializers.CharField()
    village_code = serializers.CharField(required=False, allow_blank=True)
    village_name = serializers.CharField(required=False, allow_blank=True)
    postal_code = serializers.CharField(required=False, allow_blank=True)
