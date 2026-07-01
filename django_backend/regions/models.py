"""
Indonesian administrative region models.
Hierarchy: Province → Regency/City → District → Village
Uses official Kemendagri (Ministry of Home Affairs) codes.

Reference: Permendagri No. 137 Tahun 2017 and BPS 2024 updates.
Total: 38 provinces, 514 regencies/cities, 7,277 districts, 83,731 villages.
"""

from django.db import models
from django.core.validators import MinLengthValidator


class Province(models.Model):
    """
    Indonesian province (Provinsi).
    Code: 2-digit Kemendagri code (e.g., "31" = DKI Jakarta).
    """
    code = models.CharField(
        max_length=2, unique=True, primary_key=True,
        validators=[MinLengthValidator(2)],
        verbose_name='Kode Kemendagri'
    )
    name = models.CharField(max_length=100, verbose_name='Nama Provinsi')
    name_upper = models.CharField(max_length=100, db_index=True, verbose_name='Nama (UPPER)')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'regions_province'
        verbose_name = 'Provinsi'
        verbose_name_plural = 'Provinsi'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name_upper = self.name.upper()
        super().save(*args, **kwargs)


class Regency(models.Model):
    """
    Indonesian regency or city (Kabupaten/Kota).
    Code: 4-digit Kemendagri code (province_code + 2-digit regency code).
    e.g., "3171" = Jakarta Pusat (province "31" + city "71").
    """
    REGENCY_TYPE_CHOICES = [
        ('kabupaten', 'Kabupaten'),
        ('kota', 'Kota'),
    ]

    code = models.CharField(
        max_length=4, unique=True, primary_key=True,
        validators=[MinLengthValidator(4)],
        verbose_name='Kode Kemendagri'
    )
    province = models.ForeignKey(
        Province, on_delete=models.CASCADE, related_name='regencies'
    )
    name = models.CharField(max_length=100, verbose_name='Nama Kabupaten/Kota')
    name_upper = models.CharField(max_length=100, db_index=True, verbose_name='Nama (UPPER)')
    type = models.CharField(max_length=20, choices=REGENCY_TYPE_CHOICES, default='kabupaten')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'regions_regency'
        verbose_name = 'Kabupaten/Kota'
        verbose_name_plural = 'Kabupaten/Kota'
        ordering = ['name']
        indexes = [
            models.Index(fields=['province', 'name']),
        ]

    def __str__(self):
        prefix = 'Kota ' if self.type == 'kota' else 'Kab. '
        return f"{prefix}{self.name}"

    def save(self, *args, **kwargs):
        self.name_upper = self.name.upper()
        super().save(*args, **kwargs)


class District(models.Model):
    """
    Indonesian district (Kecamatan).
    Code: 6-digit Kemendagri code.
    """
    code = models.CharField(
        max_length=6, unique=True, primary_key=True,
        validators=[MinLengthValidator(6)],
        verbose_name='Kode Kemendagri'
    )
    regency = models.ForeignKey(
        Regency, on_delete=models.CASCADE, related_name='districts'
    )
    province = models.ForeignKey(
        Province, on_delete=models.CASCADE, related_name='districts'
    )
    name = models.CharField(max_length=100, verbose_name='Nama Kecamatan')
    name_upper = models.CharField(max_length=100, db_index=True, verbose_name='Nama (UPPER)')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'regions_district'
        verbose_name = 'Kecamatan'
        verbose_name_plural = 'Kecamatan'
        ordering = ['name']
        indexes = [
            models.Index(fields=['regency', 'name']),
            models.Index(fields=['province', 'name']),
        ]

    def __str__(self):
        return f"Kec. {self.name}"

    def save(self, *args, **kwargs):
        self.name_upper = self.name.upper()
        super().save(*args, **kwargs)


class Village(models.Model):
    """
    Indonesian village/kelurahan (Desa/Kelurahan).
    Code: 10-digit BPS code (full hierarchy embedded).
    """
    VILLAGE_TYPE_CHOICES = [
        ('desa', 'Desa'),
        ('kelurahan', 'Kelurahan'),
    ]

    code = models.CharField(
        max_length=10, unique=True, primary_key=True,
        validators=[MinLengthValidator(10)],
        verbose_name='Kode BPS'
    )
    district = models.ForeignKey(
        District, on_delete=models.CASCADE, related_name='villages'
    )
    regency = models.ForeignKey(
        Regency, on_delete=models.CASCADE, related_name='villages'
    )
    province = models.ForeignKey(
        Province, on_delete=models.CASCADE, related_name='villages'
    )
    name = models.CharField(max_length=100, verbose_name='Nama Desa/Kelurahan')
    name_upper = models.CharField(max_length=100, db_index=True, verbose_name='Nama (UPPER)')
    type = models.CharField(max_length=20, choices=VILLAGE_TYPE_CHOICES, default='desa')
    postal_code = models.CharField(max_length=5, blank=True, verbose_name='Kode Pos')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'regions_village'
        verbose_name = 'Desa/Kelurahan'
        verbose_name_plural = 'Desa/Kelurahan'
        ordering = ['name']
        indexes = [
            models.Index(fields=['district', 'name']),
            models.Index(fields=['postal_code']),
            models.Index(fields=['name_upper']),
        ]

    def __str__(self):
        prefix = 'Kel. ' if self.type == 'kelurahan' else 'Desa '
        return f"{prefix}{self.name}"

    def save(self, *args, **kwargs):
        self.name_upper = self.name.upper()
        super().save(*args, **kwargs)
