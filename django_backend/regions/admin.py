from django.contrib import admin
from .models import Province, Regency, District, Village


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'name']


@admin.register(Regency)
class RegencyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'province', 'type', 'is_active']
    list_filter = ['province', 'type', 'is_active']
    search_fields = ['code', 'name']


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'regency', 'is_active']
    list_filter = ['regency__province', 'is_active']
    search_fields = ['code', 'name']


@admin.register(Village)
class VillageAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'type', 'district', 'postal_code', 'is_active']
    list_filter = ['district__regency__province', 'type', 'is_active']
    search_fields = ['code', 'name', 'postal_code']
