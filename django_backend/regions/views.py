"""
API views for Indonesian region selector.
Cascading: Province → Regency → District → Village
With prefix search across all levels. Flutter-ready JSON responses.

Data sources (priority):
  1. Local database (seeded via management commands)
  2. Binderbyte Wilayah API (fallback when local data empty AND BINDERBYTE_API_KEY is set)

All list views are cached 1 hour since region data is static.
"""

import logging
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.conf import settings
from rest_framework import status, generics, permissions, views
from rest_framework.response import Response

from .models import Province, Regency, District, Village
from drf_spectacular.utils import extend_schema
from .serializers import (
    ProvinceSerializer,
    ProvinceDetailSerializer,
    RegencySerializer,
    RegencyDetailSerializer,
    DistrictSerializer,
    DistrictDetailSerializer,
    VillageSerializer,
    SearchResultSerializer,
    RegionPathSerializer,
)

logger = logging.getLogger(__name__)


def _fetch_from_binderbyte(level, parent_code=''):
    """Fetch region data from Binderbyte Wilayah API if available."""
    if not settings.BINDERBYTE_API_KEY:
        return None
    try:
        from orders.services.binderbyte import (
            fetch_provinces, fetch_regencies, fetch_districts, fetch_villages
        )
        fetchers = {
            'province': lambda: fetch_provinces(),
            'regency': lambda: fetch_regencies(parent_code),
            'district': lambda: fetch_districts(parent_code),
            'village': lambda: fetch_villages(parent_code),
        }
        fetcher_fn = fetchers.get(level)
        if fetcher_fn:
            return fetcher_fn()
    except Exception as e:
        logger.warning('Binderbyte fetch failed for %s: %s', level, str(e))
    return None


def _normalize_binderbyte_result(level, data, parent_code=''):
    """
    Transform raw Binderbyte Wilayah API result to match frontend expectations.
    
    Binderbyte returns {code, name} items. We add parent codes, display_name,
    and defaults so the frontend can render dropdown options correctly.
    
    Returns a flat list of dicts (NOT serialized through DRF ModelSerializers,
    because ModelSerializers with SerializerMethodField crash on plain dicts).
    """
    if not data:
        return None
    result = []
    for item in data:
        raw_name = item.get('name', '')
        entry = {
            'code': item.get('code', ''),
            'name': raw_name,
            'display_name': raw_name,
            'is_active': True,
        }
        if level == 'regency':
            entry['province_code'] = parent_code
            # Detect type from name: "Kota ..." → 'kota', otherwise 'kabupaten'
            if raw_name.upper().startswith('KOTA'):
                entry['type'] = 'kota'
                entry['display_name'] = f"Kota {raw_name[4:].strip()}"
            else:
                entry['type'] = 'kabupaten'
                entry['display_name'] = f"Kab. {raw_name}"
        elif level == 'district':
            entry['regency_code'] = parent_code
            entry['display_name'] = f"Kec. {raw_name}"
        elif level == 'village':
            entry['district_code'] = parent_code
            entry['type'] = 'desa'
            entry['postal_code'] = item.get('postal_code', '')
            entry['display_name'] = f"Desa {raw_name}"
        result.append(entry)
    return result


class BinderbyteFallbackMixin:
    """
    Mixin for region list views.
    Falls back to Binderbyte Wilayah API when local DB is empty
    and BINDERBYTE_API_KEY is configured.
    
    CRITICAL: Always returns a flat JSON array (NOT {count, results}) so the
    frontend can iterate it directly with forEach/populateSelect.
    
    Usage: subclass must implement _fetch_binderbyte(self, request)
    which returns a list of dicts with at minimum {'code', 'name'} or None.
    """
    
    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        
        # If local DB has data, use standard DRF list (returns flat array)
        if qs.exists():
            serializer = self.get_serializer(qs, many=True)
            return Response(serializer.data)
        
        # No local data — try Binderbyte (if configured)
        if not settings.BINDERBYTE_API_KEY:
            return Response([])
        
        binderbyte_data = self._fetch_binderbyte(request)
        if binderbyte_data:
            return Response(binderbyte_data)
        
        return Response([])

# Cache for 1 hour — region data is read-only, only changes via seed commands
CACHE_TIME = 60 * 60


@method_decorator(cache_page(CACHE_TIME), name='dispatch')
class ProvinceListView(BinderbyteFallbackMixin, generics.ListAPIView):
    """
    List all active provinces.
    Falls back to Binderbyte Wilayah API when local data is empty.
    """
    queryset = Province.objects.filter(is_active=True)
    serializer_class = ProvinceSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None

    def _fetch_binderbyte(self, request):
        raw = _fetch_from_binderbyte('province')
        normalized = _normalize_binderbyte_result('province', raw)
        # Return raw dict data directly — ModelSerializer would crash on
        # SerializerMethodField (get_regency_count) which calls obj.regencies.filter()
        return normalized


@method_decorator(cache_page(CACHE_TIME), name='dispatch')
class ProvinceDetailView(generics.RetrieveAPIView):
    """Get province details with regency list."""
    queryset = Province.objects.filter(is_active=True)
    serializer_class = ProvinceDetailSerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = 'code'


@method_decorator(cache_page(CACHE_TIME), name='dispatch')
class RegencyListView(BinderbyteFallbackMixin, generics.ListAPIView):
    """
    List regencies/cities for a province.
    Use ?province=31 to get regencies in DKI Jakarta.
    Falls back to Binderbyte Wilayah API when local data is empty.
    """
    serializer_class = RegencySerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None

    def get_queryset(self):
        qs = Regency.objects.filter(is_active=True)
        province_code = self.request.query_params.get('province')
        if province_code:
            qs = qs.filter(province__code=province_code)
        return qs.select_related('province')

    def _fetch_binderbyte(self, request):
        province_code = request.query_params.get('province', '')
        raw = _fetch_from_binderbyte('regency', province_code)
        normalized = _normalize_binderbyte_result('regency', raw, parent_code=province_code)
        return normalized


@method_decorator(cache_page(CACHE_TIME), name='dispatch')
class RegencyDetailView(generics.RetrieveAPIView):
    """Get regency details with district list."""
    queryset = Regency.objects.filter(is_active=True)
    serializer_class = RegencyDetailSerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = 'code'


@method_decorator(cache_page(CACHE_TIME), name='dispatch')
class DistrictListView(BinderbyteFallbackMixin, generics.ListAPIView):
    """
    List districts for a regency.
    Use ?regency=3171 to get districts in Jakarta Pusat.
    Falls back to Binderbyte Wilayah API when local data is empty.
    """
    serializer_class = DistrictSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None

    def get_queryset(self):
        qs = District.objects.filter(is_active=True)
        regency_code = self.request.query_params.get('regency')
        if regency_code:
            qs = qs.filter(regency__code=regency_code)
        return qs.select_related('regency', 'province')

    def _fetch_binderbyte(self, request):
        regency_code = request.query_params.get('regency', '')
        raw = _fetch_from_binderbyte('district', regency_code)
        normalized = _normalize_binderbyte_result('district', raw, parent_code=regency_code)
        return normalized


@method_decorator(cache_page(CACHE_TIME), name='dispatch')
class DistrictDetailView(generics.RetrieveAPIView):
    """Get district details with village list."""
    queryset = District.objects.filter(is_active=True)
    serializer_class = DistrictDetailSerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = 'code'


@method_decorator(cache_page(CACHE_TIME), name='dispatch')
class VillageListView(BinderbyteFallbackMixin, generics.ListAPIView):
    """
    List villages for a district.
    Use ?district=317101 to get villages in Gambir, Jakarta Pusat.
    Falls back to Binderbyte Wilayah API when local data is empty.
    """
    serializer_class = VillageSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None

    def get_queryset(self):
        qs = Village.objects.filter(is_active=True)
        district_code = self.request.query_params.get('district')
        if district_code:
            qs = qs.filter(district__code=district_code)
        return qs.select_related('district', 'regency', 'province')

    def _fetch_binderbyte(self, request):
        district_code = request.query_params.get('district', '')
        raw = _fetch_from_binderbyte('village', district_code)
        normalized = _normalize_binderbyte_result('village', raw, parent_code=district_code)
        return normalized


@extend_schema(exclude=True)
class RegionSearchView(views.APIView):
    """
    Search across all region levels (province, regency, district, village).
    
    Use ?q=jakarta to search all levels.
    Use ?q=jakarta&type=regency to filter by level.
    Use ?q=jaka&limit=10 to limit results.
    
    Returns unified JSON with type field for Flutter to render appropriately.
    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        region_type = request.query_params.get('type', '').strip().lower()
        limit = int(request.query_params.get('limit', 20))

        if not query or len(query) < 2:
            return Response({
                'count': 0,
                'results': [],
                'query': query,
            })

        results = []
        query_upper = query.upper()

        # Search provinces
        if not region_type or region_type == 'province':
            provinces = Province.objects.filter(
                Q(name_upper__startswith=query_upper) |
                Q(name_upper__icontains=query_upper)
            ).filter(is_active=True)[:limit]
            for p in provinces:
                results.append({
                    'id': p.code,
                    'name': p.name,
                    'display_name': p.name,
                    'type': 'province',
                    'parent_name': '',
                    'parent_code': '',
                    'code': p.code,
                    'postal_code': '',
                    'latitude': float(p.latitude) if p.latitude else None,
                    'longitude': float(p.longitude) if p.longitude else None,
                })

        # Search regencies
        if not region_type or region_type == 'regency':
            regencies = Regency.objects.filter(
                Q(name_upper__startswith=query_upper) |
                Q(name_upper__icontains=query_upper)
            ).filter(is_active=True).select_related('province')[:limit]
            for r in regencies:
                prefix = 'Kota ' if r.type == 'kota' else 'Kab. '
                results.append({
                    'id': r.code,
                    'name': r.name,
                    'display_name': f"{prefix}{r.name}",
                    'type': 'regency',
                    'parent_name': r.province.name,
                    'parent_code': r.province.code,
                    'code': r.code,
                    'postal_code': '',
                    'latitude': float(r.latitude) if r.latitude else None,
                    'longitude': float(r.longitude) if r.longitude else None,
                })

        # Search districts
        if not region_type or region_type == 'district':
            districts = District.objects.filter(
                Q(name_upper__startswith=query_upper) |
                Q(name_upper__icontains=query_upper)
            ).filter(is_active=True).select_related('regency', 'province')[:limit]
            for d in districts:
                results.append({
                    'id': d.code,
                    'name': d.name,
                    'display_name': f"Kec. {d.name}",
                    'type': 'district',
                    'parent_name': d.regency.name,
                    'parent_code': d.regency.code,
                    'code': d.code,
                    'postal_code': '',
                    'latitude': float(d.latitude) if d.latitude else None,
                    'longitude': float(d.longitude) if d.longitude else None,
                })

        # Search villages
        if not region_type or region_type == 'village':
            villages = Village.objects.filter(
                Q(name_upper__startswith=query_upper) |
                Q(name_upper__icontains=query_upper)
            ).filter(is_active=True).select_related('district', 'regency')[:limit]
            for v in villages:
                prefix = 'Kel. ' if v.type == 'kelurahan' else 'Desa '
                results.append({
                    'id': v.code,
                    'name': v.name,
                    'display_name': f"{prefix}{v.name}",
                    'type': 'village',
                    'parent_name': f"Kec. {v.district.name}",
                    'parent_code': v.district.code,
                    'code': v.code,
                    'postal_code': v.postal_code,
                    'latitude': float(v.latitude) if v.latitude else None,
                    'longitude': float(v.longitude) if v.longitude else None,
                })

        # Limit total results
        results = results[:limit]

        serializer = SearchResultSerializer(results, many=True)
        return Response({
            'count': len(results),
            'results': serializer.data,
            'query': query,
        })


@extend_schema(exclude=True)
class RegionPathView(views.APIView):
    """
    Get full address path for a village/district/regency code.
    
    Use ?village_code=3171010010 for breadcrumb:
    DKI Jakarta > Jakarta Pusat > Gambir > Kel. Gambir
    
    Use ?district_code=317101 to get path up to district level.
    """
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        village_code = request.query_params.get('village_code', '').strip()
        district_code = request.query_params.get('district_code', '').strip()

        try:
            if village_code:
                village = Village.objects.select_related(
                    'district', 'regency', 'province'
                ).get(code=village_code, is_active=True)
                data = {
                    'province_code': village.province.code,
                    'province_name': village.province.name,
                    'regency_code': village.regency.code,
                    'regency_name': str(village.regency),
                    'district_code': village.district.code,
                    'district_name': str(village.district),
                    'village_code': village.code,
                    'village_name': str(village),
                    'postal_code': village.postal_code,
                }
            elif district_code:
                district = District.objects.select_related(
                    'regency', 'province'
                ).get(code=district_code, is_active=True)
                data = {
                    'province_code': district.province.code,
                    'province_name': district.province.name,
                    'regency_code': district.regency.code,
                    'regency_name': str(district.regency),
                    'district_code': district.code,
                    'district_name': str(district),
                    'village_code': '',
                    'village_name': '',
                    'postal_code': '',
                }
            else:
                return Response(
                    {'error': 'Parameter village_code atau district_code diperlukan.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = RegionPathSerializer(data)
            return Response(serializer.data)

        except Village.DoesNotExist:
            return Response(
                {'error': 'Desa/Kelurahan tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except District.DoesNotExist:
            return Response(
                {'error': 'Kecamatan tidak ditemukan.'},
                status=status.HTTP_404_NOT_FOUND
            )
