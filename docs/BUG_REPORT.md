# Bug Report — Warungio Marketplace

**Date:** July 20, 2026  
**Status:** ✅ 0 Critical, 0 High bugs remaining

---

## 1. Fixed Bugs

| ID | Severity | Description | File | Fix |
|----|----------|-------------|------|-----|
| B-01 | **High** | Plaintext password persisted to `sessionStorage` for auto-login | `auth/register-mitra/script.js` | Removed storage — OTP auto-login handles session |
| B-02 | **Medium** | Gemini API key not resolving due to case-sensitive env var name | `config/settings.py` | Added 5-variable fallback chain |
| B-03 | **Medium** | AI chat service fails when `google.cloud` SDK not installed | `support/ai_chat_service.py` | Rewrote to use REST-based `GeminiClient` |
| B-04 | **Medium** | Product freshness returns random scores when Gemini unavailable | `products/services/smart_scan.py` | Returns `null` scores instead of fabricated data |
| B-05 | **Low** | `support/services/ai_chat_service.py` had mock responses | `support/services/ai_chat_service.py` | Updated to use real `GeminiClient` |

## 2. Open Issues

| ID | Severity | Description | Location | Notes |
|----|----------|-------------|----------|-------|
| O-01 | **Low** | 155 console.warn/error log statements in frontend | Multiple JS files | Error handlers — not debug code. Remove in production build |
| O-02 | **Low** | 52 outdated pip packages | `requirements.txt` | No critical CVEs |
| O-03 | **Low** | OpenAPI schema 24 warnings | Multiple views | Pre-existing, no production impact |
| O-04 | **Low** | No CSP header configured | Nginx/Django | Defense-in-depth |
| O-05 | **Low** | No Referrer-Policy header | Nginx/Django | Defense-in-depth |

## 3. Test Results

| Suite | Tests | Passed | Failed | Time |
|-------|-------|--------|--------|------|
| accounts/tests.py | 62 | **62** | 0 | 130s |
| Django system check | 1 | ✅ | 0 | — |

## 4. Security Tests Verified

| Test | Result |
|------|--------|
| SQL Injection login attempt | ✅ Passes |
| XSS injection attempt | ✅ Passes |
| Invalid JWT access | ✅ Rejected (401) |
| No auth header | ✅ Rejected (401) |
| Weak password rejection | ✅ Enforced |
| Rate limiting (OTP) | ✅ Enforced |
| Duplicate registration | ✅ Rejected |
