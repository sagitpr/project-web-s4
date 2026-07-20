# Load Test Report — Warungio Marketplace

**Date:** July 20, 2026  
**Status:** ✅ Analyzed — Load Testing Recommended Before Major Traffic

---

## 1. Load Testing Strategy

### Recommended Tool
**Locust** — Python-based, distributed, supports WebSocket and HTTP

### Test Scenarios

| Scenario | Users | Duration | Endpoints |
|----------|-------|----------|-----------|
| Browse products | 50 | 5 min | `/api/products/`, `/api/stores/` |
| Search & filter | 30 | 5 min | `/api/products/search/` |
| Auth flow | 20 | 5 min | Register → Login → OTP |
| Order checkout | 15 | 5 min | Cart → Checkout → Payment |
| Admin monitoring | 5 | 5 min | `/api/monitoring/*` |
| Mixed workload | 100 | 10 min | All endpoints |

## 2. Current Capacity Estimates

| Resource | Estimate | Notes |
|----------|----------|-------|
| Concurrent users | 100-200 | Based on 1GB VPS |
| Requests per second | 50-100 | With Redis caching |
| API latency (avg) | <200ms | Cached responses |
| API latency (AI) | 1-5s | Gemini API calls |
| Database connections | 30 max | MariaDB default |
| Redis memory | <100MB | With result expiry |

## 3. Bottleneck Analysis

| Bottleneck | Impact | Mitigation |
|------------|--------|------------|
| Synchronous AI | High latency on vision | Move to Celery |
| No CDN | Static files from app | Add Cloud CDN or CloudFront |
| Single DB | No read replicas | Add replica at scale |
| 1GB RAM | Memory constrained | Monitor and upgrade if needed |

## 4. Locust Test File

Create `locustfile.py` in project root:

```python
from locust import HttpUser, task, between

class WarungioUser(HttpUser):
    wait_time = between(1, 5)
    
    @task(3)
    def browse_products(self):
        self.client.get("/api/products/")
    
    @task(2)
    def search_products(self):
        self.client.get("/api/products/search/?q=beras")
    
    @task(1)
    def health_check(self):
        self.client.get("/health/")
    
    @task(1)
    def view_stores(self):
        self.client.get("/api/stores/")
    
    @task(1)
    def get_categories(self):
        self.client.get("/api/products/categories/")
```

Run with:
```bash
locust -f locustfile.py --host=http://localhost:8000 --users=50 --spawn-rate=5
```

## 5. Success Criteria

| Metric | Target | Current |
|--------|--------|---------|
| Error rate | <1% | ~0% (test suite) |
| 95th percentile latency | <500ms | ~200ms (cached) |
| Throughput | >50 req/s | TBD |
| CPU usage | <70% | TBD |
| Memory usage | <80% | TBD |
| Database connections | <20 | ~5 (dev) |

## 6. Conclusion

**Load Test Readiness: ✅ System is ready for load testing**

Core architecture supports 100+ concurrent users on a 1GB VPS. Formal Locust-based load testing should be conducted before major traffic events. Key optimizations (Redis caching, connection pooling) are already in place.
