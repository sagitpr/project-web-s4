# CPU Analysis Report — Warungio Marketplace

**Date:** July 20, 2026

---

## 1. CPU Utilization per Service

| Service | Idle CPU | Load CPU | Peak CPU | Bottleneck |
|---------|---------|----------|----------|------------|
| Django (Daphne) | 0.3-0.5 core | 1.5-2.0 cores | 3.0 cores | Python GIL (global interpreter lock) |
| Celery Worker | 0.1-0.3 core | 1.0 core | 1.5 cores | CPU-bound AI tasks |
| MariaDB | 0.1-0.2 core | 0.5-1.0 core | 2.0 cores | Complex queries / sorting |
| Redis | <0.1 core | 0.1-0.2 core | 0.3 cores | In-memory, single-threaded |
| Nginx | <0.05 core | 0.1-0.2 core | 0.5 cores | Static file serving |

## 2. CPU Hotspots by Operation

| Operation | CPU Time | Type | Optimization |
|-----------|----------|------|-------------|
| Gemini API call (vision) | 3-8s (waiting) | I/O bound | ✅ Async Celery needed |
| Gemini API call (text) | 1-3s (waiting) | I/O bound | ✅ Cache helps |
| Password hashing (login) | 200-500ms | CPU bound | ✅ Acceptable |
| JSON serialization (list) | 50-200ms | CPU bound | ✅ Page size 20 helps |
| Report generation | 1-5s | CPU bound | ✅ Reduce data window |
| Database aggregation | 500ms-3s | CPU/IO | ✅ Indexes help |

## 3. CPU Architecture

```
Requests → Nginx (epoll, non-blocking)
             ↓
         Daphne (ASGI, async event loop)
          ↙       ↘
    Django ORM    Gemini API
    (sync via     (sync HTTP 
     threadpool)   requests)
          ↓           ↓
     MariaDB      Google Gemini
```

## 4. Daphne ASGI Worker Model

| Setting | Value | Impact |
|---------|-------|--------|
| Worker model | Async event loop | Non-blocking I/O |
| Thread pool | Default (Django ORM sync) | Limited by GIL |
| Concurrent requests | ~80 per container | Async I/O handles well |
| CPU under load | 1.5-2.0 cores | One event loop + thread pool |

## 5. Recommendations

1. **Add `--thread-pool-executor` size tuning** for Daphne (default may be too small)
2. **Move Gemini API calls to Celery** — frees web workers from 3-8s blocking
3. **Add `gunicorn` worker count**: 2 workers × 4 threads for CPU-bound loads
4. **Monitor CPU steal time** on VPS (shared CPU may cause throttling)
