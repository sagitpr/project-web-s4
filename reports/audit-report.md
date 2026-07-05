# Warungio Full Repository Health Check — Audit Report

> Generated: Comprehensive scan of 77 templates, 34 CSS files, 45 JS files

---

## 🔴 CRITICAL (Will cause errors or broken functionality)

| # | Issue | Location | Detail |
|---|---|---|---|
| 1 | **XXX marker** | `buyer/order-detail/index.html` | Unresolved marker in template |
| 2 | **Legacy element IDs** | `buyer/chat/index.html` | Uses `#topbarUserName`/`#topbarUserAvatar` instead of standard `#userName`/`#userAvatar` |
| 3 | **Missing -webkit-backdrop-filter** | 12+ CSS files | Glassmorphism effects broken on Safari/Firefox |
| 4 | **Missing alt text** | `admin/monitoring/index.html`, `admin/users/index.html` | Accessibility violation |
| 5 | **Console.log in production** | `pwa-register.js` (5x), `websocket.js` (1x) | Debug output in production |

## 🟡 HIGH (Duplication and code quality)

| # | Issue | Detail |
|---|---|---|
| 6 | **showToast duplicated 15x** | Same toast function defined in 15 different files — cart, checkout, order-detail, orders, product-detail, wallet, keuangan, laporan, pengaturan, promo-diskon, ulasan, auth-ui, notifications |
| 7 | **bindDropdown duplicated 2x** | `script.js` and `orders/script.js` — auth-ui.js already handles this |
| 8 | **Hardcoded URLs** | `base.html` (11 hardcoded paths), `buyer/dashboard/index.html` (18 hardcoded paths) — should use `{% url %}` |
| 9 | **Large inline CSS** | 10+ buyer pages have 50-380 lines of inline `<style>` |
| 10 | **Large inline JS** | 10+ buyer pages have 60-482 lines of inline `<script>` |
| 11 | **!important overuse** | `home/style.css` — 180 `!important` declarations |

## 🟢 MODERATE (CSS/JS best practices)

| # | Issue | Detail |
|---|---|---|
| 12 | **MANY_VAR** | 15 JS files use `var` instead of `let`/`const` |
| 13 | **MANY_PX** | 30+ CSS files use `px` instead of `rem` |
| 14 | **MANY_HEX_COLORS** | 15+ CSS files use hardcoded hex instead of CSS variables |
| 15 | **Missing font fallback** | Several CSS files declare `font-family` without `sans-serif` fallback |
| 16 | **Chat page** | Still uses legacy IDs, not patched into auth-ui system |

---

## Perbaikan Prioritas

### Phase 1 — Critical Bugs
1. ✅ Fix XXX marker in order-detail
2. ✅ Fix chat page element IDs
3. ✅ Add -webkit-backdrop-filter to CSS files
4. ✅ Add missing alt text
5. ✅ Clean console.log from production JS (keep PWA logs — they're intentional)

### Phase 2 — Code Duplication
6. ✅ Consolidate showToast in buyer pages to use shared utility
7. ✅ Remove duplicate bindDropdown
8. ✅ Fix hardcoded URLs in base.html and dashboard

### Phase 3 — Refactoring
9. ✅ Extract large inline CSS from buyer pages to CSS files
10. ✅ Extract large inline JS from buyer pages to JS files
11. ✅ Reduce !important in home/style.css

### Phase 4 — Polish
12-16. Best practices improvements where safe
