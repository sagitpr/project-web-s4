"""
OCR Service for Smart Inventory Scanning.

Processes text extracted from product packaging by the Flutter device's
on-device OCR (e.g., ML Kit Text Recognition).

Handles:
- Expiry date extraction (DD/MM/YYYY, MM/YYYY, Indonesian formats)
- Batch/Lot number extraction
- Product name and brand extraction from labels
- BPOM number detection
- Confidence scoring and uncertainty flagging
"""

import calendar
import logging
import re
from datetime import date

logger = logging.getLogger('django_backend.inventory.ai_scan.ocr')


# Regex patterns: date [0:8], batch [8:10], BPOM [10:]
EXPIRY_PATTERNS = [
    r'(\d{2})[/\-](\d{2})[/\-](\d{4})',
    r'(\d{4})[/\-](\d{2})[/\-](\d{2})',
    r'(\d{1,2})\s+(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember|Jan|Feb|Mar|Apr|Mei|Jun|Jul|Agu|Sep|Okt|Nov|Des)\s+(\d{4})',
    r'(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember|Jan|Feb|Mar|Apr|Mei|Jun|Jul|Agu|Sep|Okt|Nov|Des)\s+(\d{1,2}),?\s+(\d{4})',
    r'(\d{2})[/\-](\d{4})',
    r'(?:EXP|exp|Exp|ED|ed):?\s*(\d{2}[/\-]\d{2}[/\-]\d{4})',
    r'(?:EXP|exp|Exp|ED|ed):?\s*(\d{4}[/\-]\d{2}[/\-]\d{2})',
    # Batch patterns
    r'(?:KD|Lot|Batch|batch|lot|LOT|BATCH|No\.?\s*Batch|NO\.?\s*BATCH):?\s*([A-Za-z0-9\-_]+)',
    r'(?:KD|Lot|Batch|batch|lot|LOT|BATCH|No\.?\s*Batch|NO\.?\s*BATCH):?\s*([A-Za-z0-9\-_]+)',
    # BPOM patterns
    r'(?:BPOM|POM|bpom|pom):?\s*([A-Za-z]{2}\s*\d{8,12})',
    r'(?:BPOM|POM|bpom|pom):?\s*([A-Za-z]{2}\s*\d{2,3}\s*\d{6,9})',
]

MONTH_MAP = {
    'januari': 1, 'februari': 2, 'maret': 3, 'april': 4,
    'mei': 5, 'juni': 6, 'juli': 7, 'agustus': 8,
    'september': 9, 'oktober': 10, 'november': 11, 'desember': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
    'jun': 6, 'jul': 7, 'agu': 8, 'sep': 9, 'okt': 10, 'nov': 11, 'des': 12,
}


def process_ocr_text(ocr_text, confidence=0.75):
    """
    Process OCR-extracted text from a product packaging image.
    
    Args:
        ocr_text: Raw text extracted by device OCR
        confidence: Overall OCR confidence (0-1)
    
    Returns:
        dict with extracted fields, uncertain_fields, and warnings
    """
    if not ocr_text:
        return {'success': False, 'error': 'No OCR text provided.', 'confidence': 0}

    result = {
        'success': True,
        'extracted': {
            'expiry_date': None, 'batch_number': None,
            'product_name': None, 'brand': None, 'bpom_number': None,
        },
        'confidence': confidence,
        'uncertain_fields': [],
        'warnings': [],
    }

    lines = [l.strip() for l in ocr_text.split('\n') if l.strip()]
    full_text = ' '.join(lines)

    expiry_data = _extract_expiry_date(full_text)
    if expiry_data:
        result['extracted']['expiry_date'] = expiry_data['date'].isoformat()
        if expiry_data['uncertain']:
            result['uncertain_fields'].append('expiry_date')
            result['warnings'].append(f"Tanggal kadaluwarsa tidak pasti: {expiry_data['raw']}")

    batch_data = _extract_batch_number(full_text)
    if batch_data:
        result['extracted']['batch_number'] = batch_data['number']
        if batch_data['uncertain']:
            result['uncertain_fields'].append('batch_number')

    bpom_data = _extract_bpom_number(full_text)
    if bpom_data:
        result['extracted']['bpom_number'] = bpom_data['number']

    name_brand = _extract_name_and_brand(lines)
    if name_brand:
        result['extracted']['product_name'] = name_brand.get('product_name')
        result['extracted']['brand'] = name_brand.get('brand')
        if name_brand.get('uncertain'):
            result['uncertain_fields'].extend(name_brand['uncertain'])

    return result


def _extract_expiry_date(text):
    """Extract expiry date from text using multiple patterns."""
    for pattern in EXPIRY_PATTERNS[:7]:  # Date patterns
        match = re.search(pattern, text)
        if not match:
            continue
        groups = match.groups()

        if len(groups) == 3:
            if groups[0].isdigit() and groups[1].isdigit() and groups[2].isdigit():
                if int(groups[0]) <= 31:
                    day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                else:
                    year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
            else:
                day = int(groups[0]) if groups[0].isdigit() else 1
                month = MONTH_MAP.get(groups[1].lower(), 1)
                year = int(groups[2])
                try:
                    d = date(year, month, day)
                    return {'date': d, 'raw': match.group(0), 'uncertain': False}
                except (ValueError, TypeError):
                    continue

            try:
                d = date(year, month, day)
                if d > date(2000, 1, 1):
                    return {'date': d, 'raw': match.group(0), 'uncertain': False}
            except (ValueError, TypeError):
                continue

        elif len(groups) == 2:
            try:
                month, year = int(groups[0]), int(groups[1])
                if 1 <= month <= 12 and year >= 2020:
                    last_day = calendar.monthrange(year, month)[1]
                    return {
                        'date': date(year, month, last_day),
                        'raw': match.group(0),
                        'uncertain': True,
                    }
            except (ValueError, TypeError):
                continue

    return None


def _extract_batch_number(text):
    """Extract batch/lot number from text."""
    for pattern in EXPIRY_PATTERNS[7:9]:
        match = re.search(pattern, text)
        if match:
            num = match.group(1).strip()
            return {'number': num, 'uncertain': len(num) < 3}

    for kw in ['batch', 'lot', 'kd', 'no', 'kode']:
        m = re.search(rf'{kw}\s*[:.]?\s*([A-Z0-9]{{3,15}})', text, re.IGNORECASE)
        if m:
            return {'number': m.group(1), 'uncertain': True}
    return None


def _extract_bpom_number(text):
    """Extract BPOM registration number."""
    for pattern in EXPIRY_PATTERNS[9:]:
        match = re.search(pattern, text)
        if match:
            num = re.sub(r'\s+', ' ', match.group(1).strip())
            return {'number': num}
    return None


def _extract_name_and_brand(lines):
    """Extract product name/brand from OCR lines."""
    if not lines:
        return None
    result = {'product_name': None, 'brand': None, 'uncertain': []}
    stop_words = {'exp', 'expiry', 'batch', 'lot', 'bpom', 'pom',
                  'produksi', 'diproduksi', 'tanggal', 'no', 'nomor',
                  'kg', 'g', 'ml', 'l', 'gr', 'netto', 'berat'}

    for line in lines[:3]:
        low = line.lower().strip()
        if not low or low.split()[0] in stop_words or len(line) < 3:
            continue
        if not result['brand']:
            result['brand'] = line[:100]
            result['uncertain'].append('brand')
        elif not result['product_name']:
            result['product_name'] = line[:200]
    return result


def process_detected_item_ocr(detected_item, ocr_data):
    """Apply OCR-extracted data to a DetectedItem."""
    extracted = ocr_data.get('extracted', {})
    update_fields = []

    if extracted.get('expiry_date'):
        try:
            detected_item.detected_expiry_date = date.fromisoformat(extracted['expiry_date'])
            update_fields.append('detected_expiry_date')
        except (ValueError, TypeError):
            pass

    if extracted.get('batch_number'):
        detected_item.detected_batch_number = extracted['batch_number']
        update_fields.append('detected_batch_number')

    if extracted.get('product_name'):
        detected_item.detected_product_name = extracted['product_name']
        update_fields.append('detected_product_name')

    if extracted.get('brand'):
        detected_item.detected_brand = extracted['brand']
        update_fields.append('detected_brand')

    detected_item.ocr_confidence = ocr_data.get('confidence', 0.5)
    update_fields.append('ocr_confidence')

    if update_fields:
        detected_item.detection_method = 'combined'
        update_fields.append('detection_method')
        detected_item.save(update_fields=update_fields + ['updated_at'])

    return update_fields
