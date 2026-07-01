"""
Tests for the Indonesian region selector system.
Covers models, API views, cascading select, and search.
"""

from django.test import TestCase, override_settings
from django.urls import reverse
from django.db import connection
from rest_framework import status
from rest_framework.test import APIClient

from .models import Province, Regency, District, Village
from .data.provinces import PROVINCES


class RegionModelTests(TestCase):
    """Test region model creation and relationships."""

    @classmethod
    def setUpTestData(cls):
        cls.province = Province.objects.create(
            code='31', name='DKI Jakarta'
        )
        cls.regency = Regency.objects.create(
            code='3171', province=cls.province,
            name='Jakarta Pusat', type='kota'
        )
        cls.district = District.objects.create(
            code='317101', regency=cls.regency,
            province=cls.province, name='Gambir'
        )
        cls.village = Village.objects.create(
            code='3171010001', district=cls.district,
            regency=cls.regency, province=cls.province,
            name='Gambir', type='kelurahan', postal_code='10110'
        )

    def test_province_creation(self):
        self.assertEqual(str(self.province), 'DKI Jakarta')
        self.assertEqual(self.province.code, '31')
        self.assertEqual(self.province.name_upper, 'DKI JAKARTA')

    def test_regency_creation(self):
        self.assertIn('Kota', str(self.regency))
        self.assertEqual(self.regency.province, self.province)

    def test_district_creation(self):
        self.assertIn('Kec.', str(self.district))
        self.assertEqual(self.district.regency, self.regency)
        self.assertEqual(self.district.province, self.province)

    def test_village_creation(self):
        self.assertIn('Kel.', str(self.village))
        self.assertEqual(self.village.district, self.district)
        self.assertEqual(self.village.postal_code, '10110')

    def test_cascading_relationship(self):
        """Test province -> regency -> district -> village chain."""
        prov = Province.objects.get(code='31')
        self.assertEqual(prov.regencies.count(), 1)
        
        reg = prov.regencies.first()
        self.assertEqual(reg.districts.count(), 1)
        
        dist = reg.districts.first()
        self.assertEqual(dist.villages.count(), 1)

    def test_name_upper_auto_populated(self):
        self.assertEqual(self.province.name_upper, 'DKI JAKARTA')
        self.assertEqual(self.regency.name_upper, 'JAKARTA PUSAT')


class RegionAPITests(TestCase):
    """Test region API endpoints."""

    @classmethod
    def setUpTestData(cls):
        cls.province = Province.objects.create(
            code='31', name='DKI Jakarta'
        )
        Regency.objects.create(
            code='3171', province=cls.province,
            name='Jakarta Pusat', type='kota'
        )
        Regency.objects.create(
            code='3172', province=cls.province,
            name='Jakarta Utara', type='kota'
        )
        Province.objects.create(code='32', name='Jawa Barat')

    def setUp(self):
        self.client = APIClient()

    def test_list_provinces(self):
        url = reverse('region-provinces')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_province_detail(self):
        url = reverse('region-province-detail', kwargs={'code': '31'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'DKI Jakarta')
        self.assertIn('regencies', response.data)
        self.assertEqual(len(response.data['regencies']), 2)

    def test_list_regencies_by_province(self):
        url = reverse('region-regencies') + '?province=31'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_list_regencies_unfiltered(self):
        url = reverse('region-regencies')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_regency_detail(self):
        url = reverse('region-regency-detail', kwargs={'code': '3171'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Jakarta Pusat')

    def test_province_not_found(self):
        url = reverse('region-province-detail', kwargs={'code': '99'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class RegionSearchTests(TestCase):
    """Test region search functionality."""

    @classmethod
    def setUpTestData(cls):
        prov = Province.objects.create(code='31', name='DKI Jakarta')
        Regency.objects.create(
            code='3171', province=prov,
            name='Jakarta Pusat', type='kota'
        )
        Regency.objects.create(
            code='3172', province=prov,
            name='Jakarta Utara', type='kota'
        )
        Province.objects.create(code='32', name='Jawa Barat')
        Province.objects.create(code='33', name='Jawa Tengah')
        Province.objects.create(code='35', name='Jawa Timur')

    def setUp(self):
        self.client = APIClient()

    def test_search_provinces(self):
        url = reverse('region-search') + '?q=jawa&type=province'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        names = [r['name'] for r in response.data['results']]
        self.assertIn('Jawa Barat', names)
        self.assertIn('Jawa Tengah', names)

    def test_search_regencies(self):
        url = reverse('region-search') + '?q=jakarta&type=regency'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_search_all_levels(self):
        url = reverse('region-search') + '?q=jawa'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should include provinces matching "jawa"
        provinces = [r for r in response.data['results'] if r['type'] == 'province']
        self.assertEqual(len(provinces), 3)

    def test_search_empty_query(self):
        url = reverse('region-search') + '?q=a'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)


class RegionPathTests(TestCase):
    """Test region path (breadcrumb) API."""

    @classmethod
    def setUpTestData(cls):
        prov = Province.objects.create(code='31', name='DKI Jakarta')
        reg = Regency.objects.create(
            code='3171', province=prov,
            name='Jakarta Pusat', type='kota'
        )
        dist = District.objects.create(
            code='317101', regency=reg,
            province=prov, name='Gambir'
        )
        Village.objects.create(
            code='3171010001', district=dist,
            regency=reg, province=prov,
            name='Gambir', type='kelurahan', postal_code='10110'
        )

    def setUp(self):
        self.client = APIClient()

    def test_path_from_village(self):
        url = reverse('region-path') + '?village_code=3171010001'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['province_name'], 'DKI Jakarta')
        self.assertEqual(response.data['regency_name'], 'Kota Jakarta Pusat')
        self.assertEqual(response.data['district_name'], 'Kec. Gambir')
        self.assertEqual(response.data['village_name'], 'Kel. Gambir')
        self.assertEqual(response.data['postal_code'], '10110')
