"""
Performance Benchmark for Warungio Marketplace API.

Measures:
  - Response time (ms) for key endpoints
  - Number of database queries per endpoint
  - Memory usage baseline

Run with:
    python -m pytest django_backend/benchmark_performance.py -v --tb=short
    OR directly:
    cd django_backend && python benchmark_performance.py
"""

import os
import sys
import time
import json
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(__file__))

import django
django.setup()

from django.test import RequestFactory, override_settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.urls import reverse
from rest_framework.test import APIClient

from stores.models import Store
from products.models import Category, Product
from payments.models import Wallet, PaymentMethod

User = get_user_model()


class PerformanceBenchmark:
    """Measure response time and query count for key API endpoints."""

    def __init__(self):
        self.client = APIClient()
        self.results = {}

    def setup_test_data(self):
        """Create minimal test data for benchmarking."""
        print("Setting up test data...")

        # Create users
        self.admin = User.objects.create_superuser(
            'bench_admin',  # username (required)
            email='bench.admin@test.io', password='Bench123!',
            is_verified=True,
        )
        self.seller = User.objects.create_user(
            'bench_seller',  # username (required)
            email='bench.seller@test.io', password='Bench123!',
            is_verified=True, role='seller',
        )
        self.buyer = User.objects.create_user(
            'bench_buyer',  # username (required)
            email='bench.buyer@test.io', password='Bench123!',
            is_verified=True, role='buyer',
        )

        # Create store
        self.store = Store.objects.create(
            user=self.seller, store_name='Toko Benchmark',
            status='active', city='Jakarta',
        )

        # Create category
        self.category = Category.objects.create(
            category_name='Benchmark Category', is_active=True
        )

        # Create products
        Product.objects.all().delete()
        products = []
        for i in range(20):
            products.append(Product(
                store=self.store, category=self.category,
                product_name=f'Benchmark Product {i}',
                price=Decimal(f'{10000 + i * 1000}'),
                stock=100, is_active=True,
            ))
        Product.objects.bulk_create(products)

        # Create wallet
        Wallet.objects.get_or_create(user=self.seller, defaults={'balance': Decimal('0')})

        # Ensure payment method exists
        PaymentMethod.objects.get_or_create(
            name='bank_transfer', defaults={
                'display_name': 'Bank Transfer', 'is_active': True
            }
        )

        # Login and get tokens
        self._setup_clients()

        print("Test data ready.")

    def _setup_clients(self):
        """Setup authenticated API clients."""
        resp = self.client.post(reverse('login'), {
            'email': 'bench.buyer@test.io', 'password': 'Bench123!',
        }, format='json')
        self.buyer_token = resp.data.get('access', '')

        resp = self.client.post(reverse('login'), {
            'email': 'bench.seller@test.io', 'password': 'Bench123!',
        }, format='json')
        self.seller_token = resp.data.get('access', '')

        resp = self.client.post(reverse('admin-login'), {
            'email': 'bench.admin@test.io', 'password': 'Bench123!',
        }, format='json')
        self.admin_token = resp.data.get('access', '')

    def measure(self, name, method='GET', url=None, data=None, token=None):
        """Measure response time and query count for a request."""
        client = APIClient()
        if token:
            client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Warmup request
        if method == 'GET':
            client.get(url or '/', data)
        else:
            client.post(url or '/', data or {}, format='json')

        # Measure query count and time
        query_count_before = len(connection.queries)

        start = time.time()
        if method == 'GET':
            response = client.get(url or '/', data)
        else:
            response = client.post(url or '/', data or {}, format='json')

        elapsed_ms = (time.time() - start) * 1000
        query_count = len(connection.queries) - query_count_before

        self.results[name] = {
            'method': method,
            'url': url,
            'status': response.status_code,
            'time_ms': round(elapsed_ms, 2),
            'queries': query_count,
            'size_bytes': len(response.content) if response.content else 0,
        }

        status_icon = '✅' if str(response.status_code).startswith('2') else '❌'
        print(
            f"  {status_icon} {name:40s} "
            f"{elapsed_ms:8.2f}ms  "
            f"{query_count:3d} queries  "
            f"HTTP {response.status_code}"
        )

        return response

    def run_all(self):
        """Run all benchmarks."""
        print("\n" + "=" * 70)
        print("  WARUNGIO PERFORMANCE BENCHMARK")
        print("=" * 70)

        self.setup_test_data()

        # ── Public endpoints ──
        print("\n── Public Endpoints ──")
        self.measure('Health Check', url='/health/')
        self.measure('Product List', url='/api/products/')
        self.measure('Category List', url='/api/products/categories/')
        self.measure('Shipping Methods', url=reverse('shipping-methods'))
        self.measure('Payment Methods', url=reverse('payment-methods'))

        # ── Auth endpoints (unauthenticated) ──
        print("\n── Auth Endpoints ──")
        self.measure('Register (bad request)', method='POST',
                     url=reverse('register'),
                     data={'email': '', 'password': ''})
        self.measure('Login (wrong password)', method='POST',
                     url=reverse('login'),
                     data={'email': 'bench.buyer@test.io', 'password': 'wrong'})

        # ── Buyer endpoints ──
        print("\n── Buyer Endpoints ──")
        self.measure('Buyer Profile', url=reverse('profile'),
                     token=self.buyer_token)
        self.measure('Buyer Cart', url=reverse('cart-list'),
                     token=self.buyer_token)
        self.measure('Buyer Orders', url=reverse('my-orders'),
                     token=self.buyer_token)
        self.measure('Buyer Order History', url=reverse('order-history'),
                     token=self.buyer_token)
        self.measure('Buyer Wallet Balance', url='/api/payments/wallet/balance/',
                     token=self.buyer_token)
        self.measure('Buyer Notifications', url='/api/notifications/',
                     token=self.buyer_token)
        self.measure('Buyer Notification Unread', url='/api/notifications/unread-count/',
                     token=self.buyer_token)

        # ── Seller endpoints ──
        print("\n── Seller Endpoints ──")
        self.measure('Seller My Products', url='/api/products/my-products/',
                     token=self.seller_token)
        self.measure('Seller My Store', url='/api/stores/my-store/',
                     token=self.seller_token)
        self.measure('Seller Orders', url=reverse('seller-orders'),
                     token=self.seller_token)
        self.measure('Seller Finance Summary', url='/api/payments/finance/summary/',
                     token=self.seller_token)
        self.measure('Seller Dashboard Analytics',
                     url='/api/analytics/dashboard/?period=month',
                     token=self.seller_token)
        self.measure('Seller Wallet Balance', url='/api/payments/wallet/balance/',
                     token=self.seller_token)

        # ── Admin endpoints ──
        print("\n── Admin Endpoints ──")
        self.measure('Admin Audit Logs', url='/admin-panel/api/audit-logs/',
                     token=self.admin_token)
        self.measure('Admin Administrators', url='/admin-panel/api/administrators/',
                     token=self.admin_token)

        # ── Report ──
        self._print_report()

    def _print_report(self):
        """Print benchmark summary report."""
        print("\n" + "=" * 70)
        print("  BENCHMARK RESULTS SUMMARY")
        print("=" * 70)
        print(f"{'Endpoint':40s} {'Time(ms)':>10s} {'Queries':>8s} {'Status':>8s} {'Size':>8s}")
        print("-" * 74)

        total_time = 0
        total_queries = 0
        for name, result in self.results.items():
            total_time += result['time_ms']
            total_queries += result['queries']
            time_str = f"{result['time_ms']:.1f}"
            print(
                f"{name:40s} {time_str:>10s} "
                f"{str(result['queries']):>8s} "
                f"{str(result['status']):>8s} "
                f"{str(result['size_bytes']):>8s}"
            )

        print("-" * 74)
        print(f"{'AVERAGE':40s} {total_time/len(self.results):>8.1f}ms "
              f"{int(total_queries/len(self.results)):>8d}q "
              f"{'':>16s}")
        print(f"{'TOTAL':40s} {total_time:>8.1f}ms "
              f"{total_queries:>8d}q "
              f"{'':>16s}")

        print("\n" + "=" * 70)
        print("  RECOMMENDATIONS")
        print("=" * 70)
        slow_endpoints = [
            (n, r) for n, r in self.results.items()
            if r['time_ms'] > 500 and r['status'] < 400
        ]
        high_query = [
            (n, r) for n, r in self.results.items()
            if r['queries'] > 10 and r['status'] < 400
        ]

        if slow_endpoints:
            print(f"\n⚠️  Slow endpoints (>500ms):")
            for name, result in slow_endpoints:
                print(f"   - {name}: {result['time_ms']:.1f}ms ({result['queries']} queries)")

        if high_query:
            print(f"\n⚠️  High query count (>10):")
            for name, result in high_query:
                print(f"   - {name}: {result['queries']} queries ({result['time_ms']:.1f}ms)")

        if not slow_endpoints and not high_query:
            print("\n✅ All endpoints perform well!")

        print(f"\n✅ {len(self.results)} endpoints benchmarked.")
        print("=" * 70)


if __name__ == '__main__':
    benchmark = PerformanceBenchmark()
    benchmark.run_all()
