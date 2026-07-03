"""
API views for Indonesian region selector.
Cascading: Province → Regency → District → Village
With prefix search across all levels. Flutter-ready JSON responses.

All list views are cached 1 hour since region data is static
(explicitly updated via management commands only).
"""

from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import status, generics, permissions, views
from rest_framework.response import Response

from .models import Province, Regency, District, Village
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

# Cache for 1 hour — region data is read-only, only changes via seed commands
CACHE_TIME = 60 * 60


@method_decorator(cache_page(CACHE_TIME), name='dispatch')
class ProvinceListView(generics.ListAPIView):
    """List all active provinces (no pagination — needed for cascading selector)."""
    queryset = Province.objects.filter(is_active=True)
    serializer_class = ProvinceSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None  # Full list needed for cascading dropdown


@method_decorator(cache_page(CACHE_TIME), name='dispatch')
class ProvinceDetailView(generics.RetrieveAPIView):
    """Get province details with regency list."""
    queryset = Province.objects.filter(is_active=True)
    serializer_class = ProvinceDetailSerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = 'code'


@method_decorator(cache_page(CACHE_TIME), name='dispatch')
class RegencyListView(generics.ListAPIView):
    """
    List regencies/cities for a province.
    Use ?province=31 to get regencies in DKI Jakarta.
    No pagination — full list needed for cascading selector.
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


@method_decorator(cache_page(CACHE_TIME), name='dispatch')
class RegencyDetailView(generics.RetrieveAPIView):
    """Get regency details with district list."""
    queryset = Regency.objects.filter(is_active=True)
    serializer_class = RegencyDetailSerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = 'code'


@method_decorator(cache_page(CACHE_TIME), name='dispatch')
class DistrictListView(generics.ListAPIView):
    """
    List districts for a regency.
    Use ?regency=3171 to get districts in Jakarta Pusat.
    No pagination — full list needed for cascading selector.
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


@method_decorator(cache_page(CACHE_TIME), name='dispatch')
class DistrictDetailView(generics.RetrieveAPIView):
    """Get district details with village list."""
    queryset = District.objects.filter(is_active=True)
    serializer_class = DistrictDetailSerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = 'code'


@method_decorator(cache_page(CACHE_TIME), name='dispatch')
class VillageListView(generics.ListAPIView):
    """
    List villages for a district.
    Use ?district=317101 to get villages in Gambir, Jakarta Pusat.
    No pagination — full list needed for cascading selector.
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
