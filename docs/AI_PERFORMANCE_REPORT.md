# AI Performance Report — Warungio Marketplace

**Date:** July 20, 2026

---

## 1. Gemini API Latency Profile

| Feature | Model | Avg Latency | P95 Latency | Cost/Request (est.) |
|---------|-------|-------------|-------------|---------------------|
| Text generation | `gemini-2.0-flash` | 1-2s | 4s | $0.0001-0.0003 |
| Structured JSON | `gemini-2.0-flash` | 1-3s | 5s | $0.0002-0.0005 |
| Vision analysis | `gemini-2.0-flash` | 3-8s | 12s | $0.001-0.003 |
| Vision + freshness | `gemini-2.0-flash` | 3-8s | 12s | $0.001-0.003 |

## 2. Cache Hit Rate Strategy

| Cache Key Pattern | TTL | Est. Hit Rate | Benefit |
|------------------|-----|---------------|---------|
| `ai_rec:{user_id}` | 3600s | ~60% | Reduces 60% of Gemini text calls |
| `ai_search:{query}` | 3600s | ~40% | Common searches cached |
| `ai_desc:{product_id}` | 86400s | ~70% | Product descriptions rarely change |
| `ai_reviews:{product_id}` | 3600s | ~50% | Reviews change slowly |
| `ai_suggest:{query}` | 900s | ~80% | Suggestions are repetitive |

## 3. Prompt Optimization

| Feature | Input Tokens (est.) | Output Tokens | Optimization |
|---------|-------------------|---------------|--------------|
| Product recommendation | 500-1000 | 200-500 | Cached per user, concise prompt |
| Smart search | 200-500 | 100-300 | Short query, structured response |
| Vision analysis | 1000-2000 | 100-300 | Response in JSON format |
| Product description | 200-500 | 200-500 | Structured JSON, 24h cache |
| Review analysis | 1000-3000 | 200-500 | Batch up to 50 reviews |
| Chat response | 500-1500 | 200-500 | Context-limited to 5 messages |

## 4. Token Usage Estimate

| Feature | Daily Requests (est.) | Daily Tokens (est.) | Daily Cost (est.) |
|---------|----------------------|--------------------|--------------------|
| Product recommendations | 1,000 | 1M | $0.20-0.50 |
| Smart search | 500 | 0.5M | $0.10-0.25 |
| Vision analysis | 100 | 2M | $0.50-1.50 |
| Product descriptions | 50 | 0.5M | $0.10-0.25 |
| Review analysis | 30 | 0.3M | $0.10-0.15 |
| Fraud detection | 100 | 0.0M (rule-based mostly) | $0.05-0.10 |
| Chat responses | 200 | 0.5M | $0.10-0.25 |
| Dashboard insights | 50 | 0.5M | $0.10-0.25 |
| **Total** | **~2,030** | **~5.3M** | **$1.25-3.25/day** |

## 5. Blocking vs Async Analysis

| Feature | Current | Recommended | Priority |
|---------|---------|-------------|----------|
| Text generation | **Synchronous (blocking)** | Async via Celery | High |
| Vision analysis | **Synchronous (blocking)** | Async via Celery | **Critical** |
| Fraud detection | Synchronous (fast) | Keep sync | Low |
| Review analysis | **Synchronous (blocking)** | Async via Celery | Medium |

## 6. Gemini API Key Usage

| Metric | Value |
|--------|-------|
| API key source | `settings.GEMINI_KEY` (reads from `.env: Gemini_key`) |
| Rate limit (free tier) | 60 requests/minute |
| Rate limit (paid tier) | 2,000 requests/minute |
| Current configuration | Singleton `GeminiClient` with retry + backoff |
| Retry strategy | 2 retries, exponential backoff (1s → 2s → 4s) |
| Timeout | 30s per request |

## 7. Recommendations

1. **Move ALL vision calls to Celery tasks** (3-8s synchronous blocking is unacceptable for web workers)
2. **Add token counting middleware** to track AI API costs in production
3. **Implement semantic caching** — hash-based for identical queries, similarity-based for search
4. **Set up API cost alerts** — notify if daily Gemini spend exceeds $5
