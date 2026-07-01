"""
Indonesian-specific validation utilities for Warungio Marketplace.
NIK (KTP) validation, enhanced phone normalization, address validation.
"""

import re
from datetime import datetime


# ─── Indonesian Province / City / District Data ──────────────────────────────
# Reference: Kemendagri (Ministry of Home Affairs) 2024

PROVINCES = {
    "11": "Aceh",
    "12": "Sumatera Utara",
    "13": "Sumatera Barat",
    "14": "Riau",
    "15": "Jambi",
    "16": "Sumatera Selatan",
    "17": "Bengkulu",
    "18": "Lampung",
    "19": "Kepulauan Bangka Belitung",
    "21": "Kepulauan Riau",
    "31": "DKI Jakarta",
    "32": "Jawa Barat",
    "33": "Jawa Tengah",
    "34": "DI Yogyakarta",
    "35": "Jawa Timur",
    "36": "Banten",
    "51": "Bali",
    "52": "Nusa Tenggara Barat",
    "53": "Nusa Tenggara Timur",
    "61": "Kalimantan Barat",
    "62": "Kalimantan Tengah",
    "63": "Kalimantan Selatan",
    "64": "Kalimantan Timur",
    "65": "Kalimantan Utara",
    "71": "Sulawesi Utara",
    "72": "Sulawesi Tengah",
    "73": "Sulawesi Selatan",
    "74": "Sulawesi Tenggara",
    "75": "Gorontalo",
    "76": "Sulawesi Barat",
    "81": "Maluku",
    "82": "Maluku Utara",
    "91": "Papua",
    "92": "Papua Barat",
    "93": "Papua Selatan",
    "94": "Papua Tengah",
    "95": "Papua Pegunungan",
    "96": "Papua Barat Daya",
}


def normalize_indonesian_phone(value):
    """
    Normalize Indonesian phone numbers to +628xx format.
    
    Accepts: 08xx, 628xx, +628xx, 08xx-xxxx-xxxx, (08xx)xxxxxx
    Returns: +628xxxxxxxxxx
    Raises: ValidationError with Indonesian-language message
    """
    from rest_framework import serializers

    if not value:
        raise serializers.ValidationError("Nomor HP wajib diisi.")

    # Strip all non-digit characters except leading +
    cleaned = re.sub(r'[^\d+]', '', str(value))

    if cleaned.startswith('+62'):
        if not cleaned.startswith('+628'):
            raise serializers.ValidationError(
                "Nomor HP harus menggunakan prefix provider Indonesia (08xx / 628xx / +628xx)."
            )
        digits_only = cleaned[1:]  # strip leading +
        if len(digits_only) < 11 or len(digits_only) > 14:
            raise serializers.ValidationError(
                "Panjang nomor HP tidak valid (harus 10-13 digit setelah 62)."
            )
        return cleaned

    elif cleaned.startswith('62'):
        if not cleaned.startswith('628'):
            raise serializers.ValidationError(
                "Nomor HP harus menggunakan prefix provider Indonesia (08xx / 628xx / +628xx)."
            )
        if len(cleaned) < 11 or len(cleaned) > 14:
            raise serializers.ValidationError(
                "Panjang nomor HP tidak valid (harus 10-13 digit setelah 62)."
            )
        return '+' + cleaned

    elif cleaned.startswith('08'):
        normalized = '+62' + cleaned[1:]
        digits_only = normalized[1:]
        if len(digits_only) < 11 or len(digits_only) > 14:
            raise serializers.ValidationError(
                "Panjang nomor HP tidak valid (harus 10-13 digit setelah 62)."
            )
        return normalized

    else:
        raise serializers.ValidationError(
            "Format nomor HP tidak valid. Gunakan format 08xxxxxxxxxx atau +628xxxxxxxxxx."
        )


def get_phone_provider(phone):
    """
    Detect Indonesian mobile provider from phone number.
    
    Returns one of: 'telkomsel', 'indosat', 'xl', 'tri', 'smart', 'axis', 'byru', 'unknown'
    """
    # Strip to digits only
    digits = re.sub(r'[^\d]', '', phone)
    if digits.startswith('62'):
        digits = '0' + digits[2:]
    
    prefix = digits[:5] if len(digits) >= 5 else digits
    
    # Telkomsel
    if any(prefix.startswith(p) for p in ['0811', '0812', '0813', '0821', '0822', '0823', '0852', '0853']):
        return 'telkomsel'
    # Indosat
    if any(prefix.startswith(p) for p in ['0814', '0815', '0816', '0855', '0856', '0857', '0858']):
        return 'indosat'
    # XL
    if any(prefix.startswith(p) for p in ['0817', '0818', '0819', '0859', '0877', '0878', '0879']):
        return 'xl'
    # Tri (3)
    if any(prefix.startswith(p) for p in ['0895', '0896', '0897', '0898', '0899']):
        return 'tri'
    # Smart
    if any(prefix.startswith(p) for p in ['0881', '0882', '0883', '0884', '0885', '0886', '0887', '0888', '0889']):
        return 'smart'
    # Axis
    if any(prefix.startswith(p) for p in ['0831', '0832', '0833', '0838']):
        return 'axis'
    # ByRU (Telkomsel)
    if any(prefix.startswith(p) for p in ['0851', '0854']):
        return 'byru'
    
    return 'unknown'


# ─── NIK (KTP) Validation ───────────────────────────────────────────────────

def validate_nik(nik: str) -> dict:
    """
    Validate Indonesian NIK (Nomor Induk Kependudukan / KTP number).
    
    16-digit number with embedded information:
    - Digits 1-2: Province code
    - Digits 3-4: City/Regency code  
    - Digits 5-6: District code
    - Digits 7-10: Date of birth (DD/MM/YY for men, DD+40/MM/YY for women)
    - Digits 11-12: Month of birth
    - Digits 13-14: Year of birth
    - Digits 15-16: Computer-generated sequential number
    
    Returns:
        dict with:
        - valid: bool
        - errors: list of error messages
        - parsed: dict with province, city_code, birth_date, gender, is_valid_checksum
    """
    errors = []
    result = {
        'valid': False,
        'errors': errors,
        'parsed': None,
    }

    if not nik:
        errors.append("NIK wajib diisi.")
        return result

    # Clean
    nik = str(nik).strip()
    if not nik.isdigit():
        errors.append("NIK harus berupa 16 digit angka.")
        return result

    if len(nik) != 16:
        errors.append(f"NIK harus 16 digit, ditemukan {len(nik)} digit.")
        return result

    # Parse embedded data
    prov_code = nik[:2]
    city_code = nik[2:4]
    district_code = nik[4:6]

    # Date of birth (NIK uses DD/MM/YY with women's day+40)
    raw_day = int(nik[6:8])
    raw_month = int(nik[8:10])
    raw_year = int(nik[10:12])

    # Determine gender
    is_female = raw_day > 40
    birth_day = raw_day - 40 if is_female else raw_day
    gender = 'female' if is_female else 'male'

    # Determine century for birth year
    if raw_year <= datetime.now().year % 100:
        birth_year = 2000 + raw_year
    else:
        birth_year = 1900 + raw_year

    # Validate month
    if raw_month < 1 or raw_month > 12:
        errors.append("Bulan lahir pada NIK tidak valid (harus 01-12).")
    else:
        month_name = [
            '', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
            'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
        ][raw_month]

    # Validate day for month
    try:
        from calendar import monthrange
        max_day = monthrange(birth_year, raw_month)[1] if 1 <= raw_month <= 12 else 31
        if birth_day < 1 or birth_day > max_day:
            errors.append(f"Tanggal lahir pada NIK tidak valid (1-{max_day} untuk bulan tersebut).")
    except (ValueError, IndexError):
        errors.append("Tanggal lahir pada NIK tidak valid.")

    # Validate province code
    prov_name = PROVINCES.get(prov_code)
    if not prov_name:
        errors.append(f"Kode provinsi {prov_code} tidak dikenal.")

    # Checksum verification (Luhn algorithm)
    if not _luhn_check(nik):
        errors.append("NIK tidak valid (checksum tidak sesuai).")

    if errors:
        return result

    parsed = {
        'nik': nik,
        'province_code': prov_code,
        'province': prov_name,
        'city_code': city_code,
        'district_code': district_code,
        'birth_date': f"{birth_day:02d}-{raw_month:02d}-{birth_year}",
        'birth_year': birth_year,
        'birth_month': raw_month,
        'birth_day': birth_day,
        'gender': gender,
        'is_female': is_female,
    }

    return {
        'valid': True,
        'errors': [],
        'parsed': parsed,
    }


def _luhn_check(nik: str) -> bool:
    """
    Luhn algorithm checksum validation for NIK.
    The last digit is a check digit calculated from the first 15 digits.
    """
    digits = [int(d) for d in nik]
    check_digit = digits.pop()
    
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 0:
            d = d * 2
            if d > 9:
                d = d - 9
        total += d
    
    return (total + check_digit) % 10 == 0


def format_address(
    street: str,
    village: str = '',
    district: str = '',
    city: str = '',
    province: str = '',
    postal_code: str = '',
) -> str:
    """Format an Indonesian address in standard format."""
    parts = [street]
    if village:
        parts.append(village)
    if district:
        parts.append(f"Kec. {district}")
    
    city_prov = city
    if province:
        city_prov = f"{city}, {province}" if city else province
    parts.append(city_prov)
    
    if postal_code:
        parts.append(postal_code)
    
    return ', '.join(parts)


def detect_province_from_nik(nik: str) -> str | None:
    """Extract province name from NIK code."""
    if not nik or len(nik) < 2:
        return None
    return PROVINCES.get(nik[:2])
