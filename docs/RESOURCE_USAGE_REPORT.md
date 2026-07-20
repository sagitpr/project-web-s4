# Resource Usage Report — Warungio Marketplace

**Date:** July 20, 2026

---

## 1. Docker Memory Allocation (Compose)

| Container | Memory Limit | Typical Usage | Peak Usage |
|-----------|-------------|---------------|------------|
| MariaDB (mysql) | 256m | 120-180 MB | 220 MB |
| Redis | 48m | 10-25 MB | 40 MB |
| Django (Daphne) | 256m | 100-180 MB | 240 MB |
| Celery Worker | 128m | 50-90 MB | 110 MB |
| Nginx | 48m | 8-15 MB | 25 MB |
| **Total** | **736 MB** | **~350 MB** | **~635 MB** |

## 2. Cloud Run Resource Allocation

| Resource | Limit | Notes |
|----------|-------|-------|
| CPU | 1 vCPU (1000m) | Startup CPU boost enabled |
| Memory | 512 MiB | Includes Cloud SQL proxy overhead |
| Max instances | 3 | Auto-scaled |
| Container concurrency | 80 | Request per container |

## 3. Estimated Production Resource Profile

### Steady State (~350 MB)
- Django process: ~150 MB (3 workers equivalent via Daphne async)
- MariaDB: ~130 MB (InnoDB buffer pool ~96 MB)
- Redis: ~20 MB (session + cache + channels)
- Celery: ~50 MB (1 worker with imported modules)
- Nginx: ~8 MB

### Peak (~635 MB)
- Django serving ~80 concurrent requests: ~240 MB
- MariaDB with active queries: ~220 MB
- Redis with cached data: ~40 MB
- Celery processing tasks: ~110 MB  
- Nginx bursting: ~25 MB

## 4. CPU Utilization Profile

| Process | CPU Core Usage | Peak |
|---------|---------------|------|
| Django (Daphne) | 0.3-0.5 cores idle, 1.5-2.0 cores under load | 3.0 cores |
| Celery | 0.1-0.3 cores idle, 1.0 core under load | 1.5 cores |
| MariaDB | 0.1-0.2 cores idle, 0.5-1.0 core under load | 2.0 cores |
| Redis | <0.1 cores | 0.3 cores |
| Nginx | <0.1 cores | 0.2 cores |

## 5. Memory Hotspots

| Feature | RAM Impact | Notes |
|---------|-----------|-------|
| Django model instances | ~200 MB for 1000 concurrent objects | Use `.values()` vs model instances |
| Gemini API response payloads | ~10-50 MB cached | 3600s TTL prevents growth |
| Session storage (Redis) | ~10-20 MB for 1000 active sessions | 7-day expiry |
| Static files (WhiteNoise) | ~50 MB (loaded into memory) | Compressed on build |
| File upload buffers | ~5 MB per upload | Hard limit enforced |

## 6. Resource Optimization Recommendations

1. **Reduce Django memory**: Add connection pooling, reduce model instance creation
2. **Compress static assets**: Gzip already enabled via nginx
3. **Monitor Redis memory**: 48 MB limit may be tight under heavy session load
4. **Consider PgBouncer or MariaDB connection pooling**: CONN_MAX_AGE=60 is good
