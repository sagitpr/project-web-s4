"""
AI Smart Search — Natural language product search with semantic understanding,
spelling correction, and intent recognition using Gemini API.
"""

import logging
import re
from typing import Optional, Dict, Any, List
from django.db.models import Q, Value, FloatField
from django.db.models.functions import Coalesce
from django.core.cache import cache

from products.models import Product, Category
from stores.models import Store
from .gemini_client import get_gemini_client

logger = logging.getLogger('django_backend.ai_services.search')


class AISmartSearch:
    """
    AI-powered smart search for products.
    
    Features:
    - Natural language query understanding
    - Spelling correction for Indonesian product names
    - Semantic search (beyond keyword matching)
    - Intent recognition (find by price, category, store, etc.)
    - Query categorization (product, store, category, general)
    """

    def __init__(self):
        self.client = get_gemini_client()

    def search(self, query: str, limit: int = 20, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Main search entry point.
        """
        if not query or not query.strip():
            return {'results': [], 'total': 0, 'query': query}

        query = query.strip()

        # 1. Analyze query intent
        intent = self._analyze_intent(query)

        # 2. Correct spelling
        corrected = self._correct_spelling(query)
        search_query = corrected or query

        # 3. Extract price filters from query
        price_filters = self._extract_price_filters(search_query)
        clean_query = self._remove_price_filters(search_query, price_filters)

        # 4. Extract category/store mentions
        category_filter = self._detect_category(clean_query)
        store_filter = self._detect_store(clean_query)

        # 5. Build database query
        results = self._search_database(
            query=clean_query,
            category=category_filter,
            store=store_filter,
            price_min=price_filters.get('min'),
            price_max=price_filters.get('max'),
            limit=limit,
        )

        # 6. If enough results, use AI to re-rank
        if len(results) >= 3:
            ai_ranked = self._ai_rerank(clean_query, results, limit)
            if ai_ranked:
                results = ai_ranked

        return {
            'results': results,
            'total': len(results),
            'query': query,
            'corrected_query': corrected,
            'intent': intent,
            'suggestions': self._get_suggestions(clean_query, limit=5),
        }

    def _analyze_intent(self, query: str) -> Dict[str, Any]:
        """Analyze user intent from the search query."""
        cache_key = f'ai_search_intent:{query.lower()}'
        cached = cache.get(cache_key)
        if cached:
            return cached

        prompt = (
            f"Analisis intent pencarian ini: \"{query}\"\n\n"
            "Kembalikan JSON dengan format:\n"
            "{\n"
            '  "intent_type": "product_search|category_browse|store_search|price_query|general",\n'
            '  "category": "nama kategori atau null",\n'
            '  "price_min": null atau angka,\n'
            '  "price_max": null atau angka,\n'
            '  "is_location_based": true/false,\n'
            '  "keywords": ["kata kunci 1", "kata kunci 2"],\n'
            '  "language": "id|en",\n'
            '  "summary": "1 kalimat ringkasan apa yang dicari"'
            "}"
        )

        result = self.client.generate_structured(prompt=prompt, temperature=0.1, cache_key=cache_key)
        if result:
            cache.set(cache_key, result, 3600)
        return result or {'intent_type': 'general', 'keywords': [query]}

    def _correct_spelling(self, query: str) -> Optional[str]:
        """Correct common Indonesian product spelling errors."""
        cache_key = f'ai_search_spell:{query.lower()}'
        cached = cache.get(cache_key)
        if cached:
            return cached if cached != query else None

        # Quick common corrections (no API call for simple cases)
        corrections = {
            'sayur': 'sayur', 'sayuran': 'sayuran',
            'buah': 'buah', 'buan': 'buah',
            'sembako': 'sembako', 'sembako': 'sembako',
            'beras': 'beras', 'bras': 'beras',
            'gula': 'gula', 'gla': 'gula',
            'minyak': 'minyak', 'minak': 'minyak',
            'telor': 'telur',
            'cabai': 'cabai', 'cabe': 'cabai',
            'pisang': 'pisang', 'pisan': 'pisang',
            'kelapa': 'kelapa', 'klapa': 'kelapa',
        }

        words = query.lower().split()
        corrected_words = []
        for word in words:
            if word in corrections:
                corrected_words.append(corrections[word])
            else:
                corrected_words.append(word)

        corrected = ' '.join(corrected_words)
        if corrected != query.lower():
            return corrected

        # For more complex corrections, use Gemini
        if len(query) > 3 and not self._is_known_query(query):
            prompt = (
                f"Perbaiki ejaan pencarian produk ini (Bahasa Indonesia):\n"
                f"\"{query}\"\n\n"
                f"Jika benar, kembalikan teks yang sama. Jika salah, perbaiki ejaannya.\n"
                f"Kembalikan JSON: {{\"corrected\": \"teks yang sudah diperbaiki atau sama\"}}"
            )
            result = self.client.generate_structured(prompt=prompt, temperature=0.1, cache_key=cache_key)
            if result and result.get('corrected') and result['corrected'] != query:
                cache.set(cache_key, result['corrected'], 3600)
                return result['corrected']

        return None

    def _is_known_query(self, query: str) -> bool:
        """Check if query is already a valid product/word."""
        # Check if similar products exist
        similar = Product.objects.filter(
            Q(product_name__icontains=query) |
            Q(description__icontains=query)
        ).count()
        return similar > 0

    def _extract_price_filters(self, query: str) -> Dict[str, Optional[float]]:
        """Extract price filters like 'dibawah 50000' or '10000-50000'."""
        filters = {'min': None, 'max': None}

        # Pattern: "dibawah 50000", "kurang dari 50000", "dibawah Rp50.000"
        below = re.search(r'(?:dibawah|kurang dari|di bawah|bawah)\s*(?:Rp|rp)?\s*([\d.,]+)', query)
        if below:
            filters['max'] = self._parse_price(below.group(1))

        # Pattern: "diatas 50000", "lebih dari 50000", "diatas Rp50.000"
        above = re.search(r'(?:diatas|di atas|lebih dari|atas)\s*(?:Rp|rp)?\s*([\d.,]+)', query)
        if above:
            filters['min'] = self._parse_price(above.group(1))

        # Pattern: "10000-50000" or "Rp10.000 - Rp50.000"
        range_match = re.search(r'(?:Rp|rp)?\s*([\d.,]+)\s*[-–]\s*(?:Rp|rp)?\s*([\d.,]+)', query)
        if range_match:
            filters['min'] = self._parse_price(range_match.group(1))
            filters['max'] = self._parse_price(range_match.group(2))

        return filters

    def _parse_price(self, text: str) -> float:
        """Parse price string to float."""
        cleaned = text.replace('.', '').replace(',', '').strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _remove_price_filters(self, query: str, filters: Dict) -> str:
        """Remove price-related parts from query for clean search."""
        clean = query
        # Remove "dibawah Rp 50000" patterns
        clean = re.sub(r'(?:dibawah|kurang dari|di bawah|bawah|diatas|di atas|lebih dari|atas)\s*(?:Rp|rp)?\s*[\d.,]+\s*', '', clean)
        # Remove "Rp 10000 - Rp 50000" patterns
        clean = re.sub(r'(?:Rp|rp)?\s*[\d.,]+\s*[-–]\s*(?:Rp|rp)?\s*[\d.,]+\s*', '', clean)
        return clean.strip()

    def _detect_category(self, query: str) -> Optional[int]:
        """Detect if query mentions a product category."""
        categories = Category.objects.filter(is_active=True)
        for cat in categories:
            if cat.category_name.lower() in query.lower():
                return cat.id
        return None

    def _detect_store(self, query: str) -> Optional[int]:
        """Detect if query mentions a store name."""
        stores = Store.objects.filter(status='active')
        for store in stores:
            if store.store_name.lower() in query.lower():
                return store.id
        return None

    def _search_database(
        self,
        query: str,
        category: Optional[int] = None,
        store: Optional[int] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """Search products in database with filters."""
        qs = Product.objects.filter(is_active=True, stock__gt=0)

        if query:
            qs = qs.filter(
                Q(product_name__icontains=query) |
                Q(description__icontains=query) |
                Q(category__category_name__icontains=query) |
                Q(store__store_name__icontains=query)
            )

        if category:
            qs = qs.filter(category_id=category)
        if store:
            qs = qs.filter(store_id=store)
        if price_min is not None:
            qs = qs.filter(price__gte=price_min)
        if price_max is not None:
            qs = qs.filter(price__lte=price_max)

        qs = qs.select_related('store', 'category').order_by('-rating', '-sold_count')[:limit]

        results = []
        for p in qs:
            results.append({
                'id': p.id,
                'product_name': p.product_name,
                'price': float(p.price),
                'price_formatted': f"Rp {p.price:,.0f}",
                'image_url': p.image_url or '',
                'rating': float(p.rating or 0),
                'sold_count': p.sold_count or 0,
                'stock': p.stock,
                'store_name': p.store.store_name if p.store else '',
                'category_name': p.category.category_name if p.category else '',
                'store_id': p.store.id if p.store else None,
            })

        return results

    def _ai_rerank(self, query: str, results: List[Dict], limit: int) -> Optional[List[Dict]]:
        """Use Gemini AI to re-rank search results by relevance."""
        query_lower = query.lower()

        results_text = "\n".join([
            f"- ID: {r['id']}, Nama: {r['product_name']}, Harga: Rp {r['price']:,.0f}, "
            f"Toko: {r['store_name']}, Rating: {r['rating']}"
            for r in results
        ])

        prompt = (
            f"Anda adalah AI pencarian produk untuk Warungio.\n\n"
            f"Pencarian: \"{query}\"\n\n"
            f"Hasil:\n{results_text}\n\n"
            f"Urutkan hasil ini berdasarkan relevansi dengan pencarian.\n"
            f"Kembalikan JSON array:\n"
            f"[{{\"product_id\": int, \"relevance_score\": float 0-1, \"reason\": \"Alasan relevansi\"}}]"
        )

        ai_sorted = self.client.generate_structured(prompt=prompt, temperature=0.2)

        if not ai_sorted or not isinstance(ai_sorted, list):
            return None

        result_map = {r['id']: r for r in results}
        reranked = []
        seen_ids = set()

        for item in sorted(ai_sorted, key=lambda x: x.get('relevance_score', 0), reverse=True):
            pid = item.get('product_id')
            if pid in result_map and pid not in seen_ids:
                reranked.append(result_map[pid])
                seen_ids.add(pid)

        # Add any missed results at end
        for r in results:
            if r['id'] not in seen_ids:
                reranked.append(r)

        return reranked[:limit]

    def get_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """Get real-time search suggestions from database."""
        return self._get_suggestions(query, limit)

    def _get_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """Get search suggestions from database."""
        if not query or len(query) < 2:
            return []

        # Get matching product names
        products = Product.objects.filter(
            product_name__icontains=query,
            is_active=True,
        ).values_list('product_name', flat=True).distinct()[:limit]

        suggestions = list(products)

        # Add category suggestions
        categories = Category.objects.filter(
            category_name__icontains=query,
            is_active=True,
        ).values_list('category_name', flat=True)[:3]

        for cat in categories:
            if cat not in suggestions:
                suggestions.append(cat)

        return suggestions[:limit]


def get_smart_search() -> AISmartSearch:
    """Get smart search instance."""
    return AISmartSearch()
