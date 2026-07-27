"""
SEO Landing Page Views for Warungio Marketplace.
Provides server-rendered, indexable landing pages for:
- /kategori/{slug}/ — Product category landing pages
- /kota/{slug}/ — City/geo landing pages
- /toko/{slug}/ — Store public profile pages
- /produk/{slug}/ — Public product detail pages
- /promo/{slug}/ — Promo landing pages

All pages extend base.html for automatic SEO meta, JSON-LD, and navigation.
"""

from django.shortcuts import render, get_object_or_404
from django.http import Http404
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView
from django.utils.text import slugify
from django.db.models import Count, Q

# Lazy-load models to avoid import errors if app isn't ready
try:
    from products.models import Category, Product, Promo, Review
    from stores.models import Store
    from support.models import HelpArticle
    _HAS_PRODUCTS = True
except Exception:
    Category = Product = Promo = Review = None
    Store = None
    HelpArticle = None
    _HAS_PRODUCTS = False


# ── CATEGORY INDEX PAGE ──

@cache_page(3600)
def category_index(request):
    """Render a page listing all product categories."""
    if not _HAS_PRODUCTS or Category is None:
        raise Http404("Kategori tidak tersedia")

    categories = Category.objects.filter(is_active=True).annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).order_by('order')

    total_products = Product.objects.filter(is_active=True).count()

    context = {
        'categories': categories,
        'total_products': total_products,
    }
    return render(request, 'seo/category_index.html', context)


# ── CATEGORY LANDING PAGES ──

@cache_page(3600)  # 1 hour cache
def category_landing(request, slug):
    """Render a category landing page with products and store info."""
    if not _HAS_PRODUCTS or Category is None:
        raise Http404("Kategori tidak tersedia")

    # Find category by slug (match Django's slugify on category_name)
    categories = Category.objects.filter(is_active=True)
    category = None
    for cat in categories:
        if slugify(cat.category_name) == slug:
            category = cat
            break

    if not category:
        raise Http404("Kategori tidak ditemukan")

    # Get products in this category
    products = Product.objects.filter(
        category=category, is_active=True
    ).select_related('store').order_by('-is_featured', '-sold_count')[:40]

    # Get stores that sell products in this category
    stores = Store.objects.filter(
        products__category=category,
        products__is_active=True,
        status='active'
    ).distinct().annotate(
        prod_count=Count('products', filter=Q(products__is_active=True, products__category=category))
    ).order_by('-rating_avg')[:20]

    # Get top products by rating
    top_products = products.order_by('-rating_avg')[:5]

    context = {
        'category': category,
        'products': products,
        'stores': stores,
        'top_products': top_products,
        'product_count': len(products),
        'store_count': len(stores),
    }
    return render(request, 'seo/category_page.html', context)


# ── CITY INDEX PAGE (list all cities) ──

@cache_page(3600)
def city_index(request):
    """Render a page listing all cities with active stores."""
    if not _HAS_PRODUCTS or Store is None:
        raise Http404("Kota tidak tersedia")

    # Group stores by city with counts
    cities = Store.objects.filter(
        status='active'
    ).exclude(
        city__isnull=True
    ).exclude(
        city__exact=''
    ).values('city').annotate(
        store_count=_Count('id'),
        product_count=_Count('products', filter=Q(products__is_active=True))
    ).order_by('-store_count')[:100]

    # Get total counts
    total_stores = Store.objects.filter(status='active').count()
    total_products = Product.objects.filter(is_active=True).count()

    context = {
        'cities': cities,
        'total_stores': total_stores,
        'total_products': total_products,
        'city_count': len(cities),
    }
    return render(request, 'seo/city_index.html', context)


# ── CITY/GEO LANDING PAGES ──

@cache_page(3600)
def city_landing(request, slug):
    """Render a city landing page showing stores and products available in that city."""
    if not _HAS_PRODUCTS or Store is None:
        raise Http404("Kota tidak tersedia")

    # Find city from stores (normalize slug back to city name)
    city_name = slug.replace('-', ' ').title()

    stores = Store.objects.filter(
        city__iexact=city_name,
        status='active'
    ).order_by('-rating_avg')[:30]

    if not stores:
        # Try partial match
        stores = Store.objects.filter(
            city__icontains=city_name.split(' ')[0],
            status='active'
        ).order_by('-rating_avg')[:30]

    if not stores:
        raise Http404("Kota tidak ditemukan")

    # Use the actual city name from the first store found
    actual_city = stores[0].city if stores else city_name

    # Get products from stores in this city
    store_ids = stores.values_list('id', flat=True)
    products = Product.objects.filter(
        store_id__in=store_ids,
        is_active=True
    ).select_related('store').order_by('-is_featured', '-sold_count')[:40]

    # Get unique categories available in this city
    categories_available = Category.objects.filter(
        products__store_id__in=store_ids,
        products__is_active=True,
        is_active=True
    ).distinct().annotate(
        prod_count=Count('products', filter=Q(products__is_active=True, products__store_id__in=store_ids))
    )[:12]

    context = {
        'city_name': actual_city,
        'stores': stores,
        'products': products,
        'categories_available': categories_available,
        'store_count': len(stores),
        'product_count': len(products),
    }
    return render(request, 'seo/city_page.html', context)


# ── STORE PUBLIC PAGES ──

@cache_page(1800)  # 30 min cache
def store_landing(request, slug):
    """Render a public store profile page with products."""
    if not _HAS_PRODUCTS or Store is None:
        raise Http404("Toko tidak tersedia")

    store = get_object_or_404(Store, slug=slug, status='active')

    products = Product.objects.filter(
        store=store, is_active=True
    ).select_related('category').order_by('-is_featured', '-sold_count')[:50]

    # Get categories for this store
    categories = Category.objects.filter(
        products__store=store,
        products__is_active=True,
        is_active=True
    ).distinct()

    context = {
        'store': store,
        'products': products,
        'categories': categories,
        'product_count': len(products),
    }
    return render(request, 'seo/store_page.html', context)


# ── PUBLIC PRODUCT DETAIL PAGES ──

@cache_page(1800)
def product_detail(request, slug):
    """Render a public product detail page without requiring authentication."""
    if not _HAS_PRODUCTS or Product is None:
        raise Http404("Produk tidak tersedia")

    product = get_object_or_404(Product, slug=slug, is_active=True)

    # Get reviews
    reviews = Review.objects.filter(
        product=product
    ).select_related('user').order_by('-created_at')[:10]

    # Get related products from same store
    related_products = Product.objects.filter(
        store=product.store,
        is_active=True
    ).exclude(id=product.id).select_related('store').order_by('-sold_count')[:8]

    # Get more products in same category
    category_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id).select_related('store').order_by('-sold_count')[:8]

    context = {
        'product': product,
        'reviews': reviews,
        'review_count': len(reviews),
        'related_products': related_products,
        'category_products': category_products,
    }
    return render(request, 'seo/product_detail.html', context)


# ── PROMO LANDING PAGES ──

@cache_page(1800)
def promo_landing(request, slug):
    """Render a promo landing page showing products on discount."""
    if not _HAS_PRODUCTS or Promo is None:
        raise Http404("Promo tidak tersedia")

    from django.utils import timezone

    promos = Promo.objects.filter(
        is_active=True,
        start_date__lte=timezone.now().date(),
        end_date__gte=timezone.now().date(),
    )

    # Find promo by slug (match name)
    promo = None
    for p in promos:
        if slugify(p.promo_name) == slug:
            promo = p
            break

    if not promo:
        raise Http404("Promo tidak ditemukan")

    # Get store products for this promo
    products = Product.objects.filter(
        store=promo.store,
        is_active=True,
    ).select_related('store').order_by('-sold_count')[:30]

    context = {
        'promo': promo,
        'products': products,
    }
    return render(request, 'seo/promo_page.html', context)


# ── PUBLIC GUEST CHECKOUT PAGE ──

def public_checkout(request, slug):
    """Render public guest checkout page with store info."""
    if not _HAS_PRODUCTS or Store is None:
        raise Http404("Toko tidak tersedia")

    store = get_object_or_404(Store, slug=slug, status='active')

    context = {
        'store': store,
    }
    return render(request, 'public/checkout/index.html', context)


# ── PUBLIC ORDER TRACKING PAGE ──

def public_tracking(request, order_number):
    """Render public order tracking page."""
    context = {
        'order_number': order_number,
        'store_initial': order_number[:1] if order_number else 'W',
    }
    return render(request, 'public/tracking/index.html', context)
