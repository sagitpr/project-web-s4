# Memory Analysis Report — Warungio Marketplace

**Date:** July 20, 2026

---

## 1. Django Process Memory Profile

| Component | Estimated RAM | Details |
|-----------|--------------|---------|
| Python interpreter | ~20 MB | Base interpreter overhead |
| Django framework | ~30 MB | Imported modules, apps |
| DRF + JWT middleware | ~10 MB | REST framework + auth |
| Channels + Daphne | ~15 MB | ASGI server + WebSocket |
| Celery (worker) | ~25 MB | Task framework + imported apps |
| ORM + Database driver | ~15 MB | SQLAlchemy/MySQL driver |
| Template engines | ~10 MB | Django templates loaded |
| **Total per process** | **~125 MB** | Base without request handling |

## 2. Per-Request Memory Cost

| Request Type | Memory Added | Duration | Notes |
|-------------|-------------|----------|-------|
| Simple API (list) | ~1-3 MB | 50-200ms | JSON serialization |
| Auth (register/login) | ~2-5 MB | 100-500ms | Password hashing |
| AI text generation | ~5-15 MB | 1-3s | API response + JSON parse |
| AI vision analysis | ~10-30 MB | 3-8s | Image data in memory |
| File upload (5MB) | ~5-10 MB | 500ms-2s | In-memory buffer |
| WebSocket connection | ~0.5 MB | Persistent | Per connection |

## 3. Memory Leak Detection

| Component | Risk | Mitigation |
|-----------|------|------------|
| Django ORM query cache | Low | `_result_cache` cleared per request |
| Celery worker | ✅ Controlled | Restarted every 500 tasks |
| WebSocket connections | Low | Disconnect cleanup implemented |
| AI response cache | ✅ Controlled | 3600s TTL limits growth |
| Session storage | ✅ Controlled | 7-day expiry, Redis LRU eviction |
| File upload temp files | ✅ Controlled | 5MB limit, temp file cleanup |

## 4. MariaDB Memory Allocation

| Buffer | Size | Purpose |
|--------|------|---------|
| InnoDB buffer pool | 96 MB | Cached table/index data |
| InnoDB log buffer | 16 MB | Transaction logs |
| Query cache | 0 (disabled) | Not recommended in MariaDB 10.11 |
| Thread stack | 192 KB/connection | ~30 connections = ~6 MB |
| **Total estimated** | **~120-180 MB** | Steady state |

## 5. Redis Memory Breakdown

| Data Type | Estimated Size | TTL |
|-----------|---------------|-----|
| Django cache keys | ~5-10 MB | 15 min |
| Session data | ~10-15 MB | 7 days |
| Channel layer | ~5-10 MB | 60s |
| AI cache | ~5-10 MB | 1 hour |
| Chat context | ~2-5 MB | 30 min |
| **Total estimated** | **~30-50 MB** | Under 48 MB limit |

## 6. Recommendations

1. **Monitor Celery memory growth**: Restart at 500 tasks is conservative but safe
2. **Consider increasing Redis `maxmemory` to 64 MB** if sessions grow >10K active users
3. **Use `--max-requests` for Daphne** as a safety net for memory leaks
4. **Monitor Django process RSS** in production — threshold alert at 300 MB
