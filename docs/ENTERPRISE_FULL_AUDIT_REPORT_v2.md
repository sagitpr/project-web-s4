# 🛡️ WARUNGIO ENTERPRISE FULL AUDIT REPORT v2.0

**Date:** July 21, 2026  
**Auditor:** Security Engineer / DevSecOps Engineer / SRE / Penetration Tester  
**Scope:** Source Code, Infrastructure, Deployment, Security, Performance  
**Domain:** https://warungio.web.id

---

## 📋 EXECUTIVE SUMMARY

| Metrik | Status |
|--------|--------|
| Total Temuan Critical | **8** |
| Total Temuan High | **12** |
| Total Temuan Medium | **15** |
| Total Temuan Low | **10** |
| Security Headers | ✅ HSTS, CSP, X-Frame-Options configured |
| Secret Leakage in Source | ⚠️ Placeholders exist, no real secrets found |
| SSL/TLS | ⚠️ Partial - config exists but certs not mounted |
| Docker Security | ⚠️ Runs as root, no security options |
| Rate Limiting | ✅ Configured (Nginx + DRF) |
| Backup Strategy | ❌ No automated backup |
| Monitoring | ✅ Prometheus stack configured |

---

## 🔴 CRITICAL FINDINGS

### C-01: SSL Certificate Not Mounted in Docker Compose

**Severity:** CRITICAL  
**File:** `docker-compose.yml`, `nginx/warungio.conf`  
**Bukti:** 
- `nginx/warungio.conf` line 27-28: `ssl_certificate /etc/nginx/ssl/warungio.crt` dan `ssl_certificate_key /etc/nginx/ssl/warungio.key`
- Tidak ada volume mount untuk `/etc/nginx/ssl/` di docker-compose.yml atau docker-compose.prod.yml
- SSL certs harus ditempatkan manual di server

**Patch:** Tambahkan volume mount untuk SSL certificates di docker-compose.yml:
```yaml
volumes:
  - ./nginx/ssl:/etc/nginx/ssl:ro
```

**Status:** ❌ BELUM DIPERBAIKI

### C-02: warungio.web.id Tidak Ada di ALLOWED_HOSTS

**Severity:** CRITICAL  
**File:** `django_backend/config/settings.py` line 48-52, `cloudrun.yaml` line 37  
**Bukti:**
```python
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get(
        'DJANGO_ALLOWED_HOSTS',
        'localhost,127.0.0.1,0.0.0.0,.run.app'
    ).split(',')
    if h.strip()
]
```
- Default ALLOWED_HOSTS tidak mencakup `warungio.web.id` atau `www.warungio.web.id`
- Cloud Run config juga hanya punya `.run.app`

**Patch:** Set environment variable:
```
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,.run.app,warungio.web.id,www.warungio.web.id
```

**Status:** ❌ BELUM DIPERBAIKI

### C-03: Cloud Run Mengizinkan Semua Ingress (ingress: all)

**Severity:** CRITICAL  
**File:** `cloudrun.yaml` line 5-6  
**Bukti:**
```yaml
run.googleapis.com/ingress: all
run.googleapis.com/ingress-status: all
```

**Risk:** Menerima traffic langsung dari internet tanpa melalui Cloud Load Balancer atau Cloud CDN. Tidak ada WAF protection.

**Patch:** Ubah ke `internal` atau `internal-and-cloud-load-balancing`:
```yaml
run.googleapis.com/ingress: internal-and-cloud-load-balancing
```

**Status:** ❌ BELUM DIPERBAIKI

### C-04: Tidak Ada SSL/TLS di Development Nginx Config

**Severity:** CRITICAL (untuk ERR_CONNECTION_REFUSED)  
**File:** `nginx/nginx.dev.conf`, `docker-compose.yml`  
**Bukti:**
- `docker-compose.yml` mount: `./nginx/nginx.dev.conf:/etc/nginx/conf.d/warungio.conf:ro`
- `nginx.dev.conf` hanya listen port 80, **tidak ada konfigurasi HTTPS**
- `warungio.conf` (yang punya SSL) hanya di-mount via `docker-compose.prod.yml`

**Akar Penyebab ERR_CONNECTION_REFUSED:**
- `docker-compose up` hanya menggunakan nginx.dev.conf (port 80 saja)
- https://localhost menuju port 443 yang **tidak ada listener**
- Browser mengirim koneksi ke port 443 → connection refused

**Akar Penyebab SSL_ERROR_SYSCALL:**
- Jika SSL cert dipasang manual tapi path cert tidak sesuai dengan volume mount
- Atau SSL cert sudah expired
- Atau ada mismatch antara sertifikat dan konfigurasi

**Patch:** Untuk development, gunakan self-signed cert atau non-SSL mode. Untuk production, pastikan:
1. SSL cert files ada di `./nginx/ssl/`
2. Jalankan: `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d`
3. Verifikasi: `docker-compose exec nginx nginx -t`

**Status:** ❌ BELUM DIPERBAIKI

### C-05: SMTP Credentials Masih Placeholder

**Severity:** CRITICAL  
**File:** `cloudrun.yaml` line 64  
**Bukti:**
```yaml
- name: EMAIL_HOST_USER
  value: "your-email@gmail.com"
```

**Risk:** Email OTP tidak akan terkirim di production karena placeholder credentials.

**Status:** ❌ BELUM DIPERBAIKI

### C-06: Cloud SQL Connection String Masih Placeholder

**Severity:** CRITICAL  
**File:** `cloudrun.yaml` line 45  
**Bukti:**
```yaml
- name: CLOUD_SQL_INSTANCE
  value: "your-project:asia-southeast2:your-instance"
```

**Status:** ❌ BELUM DIPERBAIKI

### C-07: CORS_ALLOWED_ORIGINS Placeholder di Cloud Run

**Severity:** CRITICAL  
**File:** `cloudrun.yaml` line 82  
**Bukti:**
```yaml
- name: CORS_ALLOWED_ORIGINS
  value: "https://your-project.asia-southeast2.run.app,https://yourdomain.com"
```

**Risk:** CORS akan gagal untuk origin `https://warungio.web.id`

**Status:** ❌ BELUM DIPERBAIKI

### C-08: Tidak Ada Automated Backup Database

**Severity:** CRITICAL  
**File:** Tidak ada  
**Bukti:** Tidak ada script backup, tidak ada cron job, tidak ada dokumentasi backup strategy.

**Risk:** Data loss jika terjadi korupsi database, container crash, atau serangan ransomware.

**Patch:** Implementasi backup otomatis via cron atau Cloud SQL automated backups.

**Status:** ❌ BELUM DIPERBAIKI

---

## 🟠 HIGH FINDINGS

### H-01: DEBUG Mode Fallback SECRET_KEY

**Severity:** HIGH  
**File:** `django_backend/config/settings.py` line 27  
**Bukti:**
```python
SECRET_KEY = 'django-insecure-dev-only-key-do-not-use-in-production'
```

**Risk:** Jika DJANGO_SECRET_KEY tidak diset di env, Django akan menggunakan key insecure ini. Key ini diketahui publik dan bisa digunakan untuk memalsukan JWT token.

**Status:** ⚠️ Mitigasi: settings.py mewajibkan SECRET_KEY di production (raise ImproperlyConfigured). Tapi fallback di development tetap riskan.

### H-02: CORS_ALLOW_ALL_ORIGINS in Development

**Severity:** HIGH  
**File:** `django_backend/config/settings.py` line 466  
**Bukti:**
```python
CORS_ALLOW_ALL_ORIGINS = DEBUG and not os.environ.get('CORS_ALLOWED_ORIGINS')
```

**Risk:** Saat DEBUG=True dan CORS_ALLOWED_ORIGINS tidak diset, semua origin diizinkan mengakses API.

**Patch:** Selalu set CORS_ALLOWED_ORIGINS di .env dan production.

**Status:** ⚠️ Acceptable untuk development, harus diwaspadai di staging.

### H-03: CSRF_COOKIE_HTTPONLY = False

**Severity:** HIGH  
**File:** `django_backend/config/settings.py` line 787  
**Bukti:**
```python
CSRF_COOKIE_HTTPONLY = False
```

**Risk:** JavaScript bisa membaca CSRF token cookie. Meskipun dijelaskan sebagai intentional untuk SPA pattern, ini meningkatkan surface area XSS attack.

**Status:** ⚠️ Diterima dengan mitigasi SameSite=Lax + JWT sebagai primary auth.

### H-04: MariaDB Performance Schema Dinonaktifkan

**Severity:** HIGH  
**File:** `mariadb/conf.d/low-memory.cnf` line 50  
**Bukti:**
```ini
performance_schema = OFF
```

**Risk:** Tidak bisa melakukan diagnostic performance database. Query slow, deadlock, dan lock contention tidak terdeteksi.

**Status:** ⚠️ Trade-off untuk 1GB RAM VPS.

### H-05: innodb_flush_log_at_trx_commit = 2

**Severity:** HIGH  
**File:** `mariadb/conf.d/low-memory.cnf` line 24  
**Bukti:**
```ini
innodb_flush_log_at_trx_commit = 2
```

**Risk:** Kehilangan data hingga 1 detik jika server crash (bukan korupsi data, tapi loss).

**Status:** ⚠️ Trade-off performance untuk 1GB VPS.

### H-06: Tidak Ada Input Validation di PHP Backend

**Severity:** HIGH  
**File:** `backend/config/api_keys.php`  
**Risk:** PHP code masih ada sebagai legacy. Perlu diverifikasi tidak ada endpoint aktif yang bisa dieksploitasi.

**Status:** ⚠️ Legacy - perlu audit endpoint PHP aktif.

### H-07: Google OAuth Client ID Placeholder di Frontend

**Severity:** HIGH  
**File:** `auth/register/index.html` line 25, `auth/login/index.html` line 22  
**Bukti:**
```javascript
appId: 'your-facebook-app-id',
```

**Risk:** Social login akan gagal di production karena placeholder credentials. Juga menyebabkan JavaScript runtime error.

**Status:** ❌ BELUM DIPERBAIKI

### H-08: Production Logging Hanya WARNING Level

**Severity:** HIGH  
**File:** `django_backend/config/settings.py` line 700-720  
**Bukti:**
```python
'level': 'WARNING',
```

**Risk:** INFO-level events seperti login success, payment success, registrations tidak tercatat. Sulit melakukan security audit dan forensik.

**Status:** ⚠️ Trade-off untuk hemat I/O disk 1GB VPS.

### H-09: Docker Container Berjalan Sebagai Root

**Severity:** HIGH  
**File:** `Dockerfile`  
**Risk:** Container berjalan dengan user root. Jika attacker berhasil escape container, mereka punya akses root ke host.

**Patch:** Tambahkan user non-root di Dockerfile:
```dockerfile
RUN useradd -m -u 1000 warungio
USER warungio
```

**Status:** ❌ BELUM DIPERBAIKI

### H-10: Container Tidak Memiliki Security Options

**Severity:** HIGH  
**File:** `docker-compose.yml`  
**Risk:** Container bisa mengakses resource host tanpa batasan. Tidak ada `cap_drop`, `security_opt`, `read_only` filesystem.

**Patch:** Tambahkan security hardening ke setiap service:
```yaml
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
```

**Status:** ❌ BELUM DIPERBAIKI

### H-11: Tidak Ada SPF/DKIM/DMARC Record untuk warungio.web.id

**Severity:** HIGH  
**Risk:** Email OTP dari noreply@warungio.com bisa masuk ke SPAM folder penerima. Email delivery tidak terjamin.

**Status:** ❌ BELUM DIPERBAIKI (butuh DNS configuration)

### H-12: CI/CD Menggunakan Hardcoded Test Password

**Severity:** HIGH  
**File:** `.github/workflows/django.yml` line 31, 48, 107  
**Bukti:**
```yaml
DJANGO_SECRET_KEY: ci-test-secret-key-not-for-production
MARIADB_ROOT_PASSWORD: ${{ secrets.MYSQL_ROOT_PASSWORD || 'testpass123' }}
```

**Risk:** Password fallback ke 'testpass123' jika secret tidak tersedia di CI environment. Berlaku di public GitHub repository.

**Status:** ⚠️ Mitigasi: Hanya untuk CI testing. Tapi fallback password harus dihindari.

---

## 🟡 MEDIUM FINDINGS

### M-01: Prometheus Tidak Terautentikasi

**File:** `monitoring/prometheus.yml`, `docker-compose.yml`  
**Risk:** Jika port Prometheus terekspos, siapapun bisa mengakses metrik.

**Status:** ⚠️ Hanya di internal Docker network.

### M-02: Node Exposer dan cAdvisor Mount /:/host

**File:** `docker-compose.yml`  
**Risk:** Container monitoring memiliki akses root filesystem host.

**Status:** ⚠️ Diperlukan untuk monitoring. Risiko diterima.

### M-03: Tidak Ada Resource Limits di docker-compose untuk CPU

**File:** `docker-compose.yml`  
**Bukti:** `mem_limit` diset tapi `cpus` atau `cpuset` tidak dikonfigurasi.

**Status:** ⚠️ Mem_limit saja sudah baik untuk 1GB VPS.

### M-04: Proxy Buffer Size Sangat Kecil

**File:** `nginx/warungio.conf` line 68-71  
**Bukti:**
```
proxy_buffer_size 4k;
proxy_buffers 8 4k;
```

**Risk:** Response API besar bisa menyebabkan disk buffering.

**Status:** ⚠️ Sesuai untuk 1GB VPS.

### M-05: Django CONN_MAX_AGE = 60 Detik

**File:** `django_backend/config/settings.py` line 222  
**Risk:** Koneksi database tetap terbuka 60 detik. Dengan max_connections=20, bisa kehabisan koneksi saat traffic spike.

**Status:** ⚠️ Risk diterima untuk performance.

### M-06: Celery Worker Concurrency = 1

**File:** `django_backend/config/settings.py` line 361  
**Risk:** Hanya 1 task dalam satu waktu. Task berat akan memblokir task lain.

**Status:** ⚠️ Trade-off untuk 1GB VPS.

### M-07: Celery Task Timeout 5 Menit

**File:** `django_backend/config/settings.py` line 343  
**Risk:** Task yang hang akan memblokir worker selama 5 menit.

**Status:** ⚠️ Wajar untuk OTP email dan AI processing.

### M-08: Tidak Ada Redis Password

**File:** `docker-compose.yml` line 48  
**Risk:** Redis di Docker network tanpa autentikasi.

**Status:** ⚠️ Hanya terakses dari Docker internal network.

### M-09: Static Files dari Host Assets (60MB) Tidak Masuk Image

**File:** `Dockerfile`  
**Risk:** Assets tidak di-copy ke runtime image. Jika container di-restart, assets mungkin tidak tersedia.

**Status:** ✅ Sudah benar - assets diserve langsung oleh Nginx dari volume mount.

### M-10: Tidak Ada Version Pinning di package.json

**File:** `package.json`  
**Bukti:**
```json
"bcrypt": "latest",
"express": "latest",
```

**Risk:** Build bisa berbeda setiap kali karena dependency diambil versi terbaru.

**Status:** ⚠️ package.json legacy, tidak dipakai di production.

### M-11: Celery Beat Scheduler Pakai File

**File:** `django_backend/config/settings.py` line 384  
```python
CELERY_BEAT_SCHEDULE_FILENAME = '/tmp/celerybeat-schedule'
```

**Risk:** Schedule file di /tmp bisa hilang saat container restart.

**Status:** ⚠️ Risk diterima - schedule akan dibuat ulang.

### M-12: Tidak Ada Rate Limiting untuk WebSocket

**File:** `nginx/nginx.dev.conf`, `nginx/warungio.conf`  
**Risk:** WebSocket connections bisa digunakan untuk DDoS.

**Status:** ⚠️ Nginx `limit_req` diterapkan untuk /ws/ endpoint di warungio.conf.

### M-13: Nginx access_log Off

**File:** `nginx/nginx.conf` line 15  
```nginx
access_log off;
```

**Risk:** Tidak ada audit trail untuk HTTP requests. Sulit melakukan forensik jika terjadi serangan.

**Status:** ⚠️ Trade-off untuk hemat I/O VPS.

### M-14: IDOR Potensial di API Endpoints

**File:** Multiple views  
**Risk:** Beberapa endpoint menggunakan `pk` atau `id` dari request tanpa validasi kepemilikan. Contoh: `ProductManageView.get_queryset()` sudah benar filter by store. Tapi perlu audit semua endpoint.

**Status:** ⚠️ Sebagian views sudah menggunakan permission classes (IsStoreOwner, IsSeller).

### M-15: Tidak Ada Web Application Firewall (WAF)

**File:** Tidak ada  
**Risk:** Tidak ada proteksi terhadap SQL injection, XSS, atau serangan umum web lainnya di layer HTTP.

**Status:** ❌ BELUM ADA - Cloud Armor atau mod_security bisa ditambahkan.

---

## 🟢 LOW FINDINGS

### L-01: JWT Menggunakan HS256 (Symmetric)

**File:** `django_backend/config/settings.py` line 447  
**Risk:** Jika SECRET_KEY bocor, semua JWT token bisa dipalsukan.

**Recommendation:** Gunakan RS256 (asymmetric) untuk production.

### L-02: Tidak Ada gRPC atau HTTP/2 untuk Internal Services

**File:** Tidak ada  
**Risk:** Komunikasi inter-service via HTTP/1.1 tanpa enkripsi internal.

### L-03: Tidak Ada Error Tracking (Sentry, etc.)

**File:** Tidak ada  
**Risk:** Error di production hanya tercatat di Docker logs, tidak ada notifikasi realtime.

### L-04: Django Admin Tidak Dibatasi IP

**File:** Tidak ada  
**Risk:** /admin/ endpoint bisa diakses dari mana saja.

### L-05: Tidak Ada Session Timeout di Frontend

**File:** Multiple frontend JS files  
**Risk:** JWT refresh token berlaku 30 hari. Session bisa tetap aktif di browser tanpa aktivitas.

### L-06: Tidak Ada 2FA/MFA untuk Admin

**File:** Tidak ada  
**Risk:** Admin panel hanya dilindungi password.

### L-07: Tidak Ada Content Security Policy Report-URI

**File:** `nginx/warungio.conf`  
**Risk:** CSP violation tidak dilaporkan ke admin.

### L-08: cloudrun.yaml Bisa Diekspos Public

**File:** `cloudrun.yaml`  
**Risk:** Berisi placeholder yang bisa memberikan informasi tentang arsitektur ke attacker.

### L-09: requirements.txt Tidak Memiliki Hash Pinning

**File:** `django_backend/requirements.txt`  
**Risk:** Supply chain attack jika PyPI package dibajak.

### L-10: Tidak Ada Vulnerability Scanning Automation

**File:** Tidak ada  
**Risk:** Tidak ada Dependabot atau Snyk untuk mendeteksi CVE di dependencies.

---

## 🔍 DIAGNOSIS: ERR_CONNECTION_REFUSED & SSL_ERROR_SYSCALL

### ERR_CONNECTION_REFUSED

**Root Cause:** Nginx dev config (`nginx.dev.conf`) hanya listen di **port 80**. Saat `curl https://localhost` atau browser mengakses `https://warungio.web.id`, koneksi menuju port 443 yang **tidak ada listener**.

**Verification:**
```bash
# Test port 80 (should work):
curl http://localhost

# Test port 443 (should fail):
curl https://localhost
# → curl: (7) Failed to connect to localhost port 443: Connection refused
```

**Fix:**
```bash
# 1. Pastikan SSL certs ada di ./nginx/ssl/
# 2. Jalankan dengan production config:
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
# 3. Verify:
docker-compose exec nginx nginx -t
```

### SSL_ERROR_SYSCALL

**Root Cause:** Jika port 443 bisa diakses tapi SSL handshake gagal:
1. SSL certificate file tidak ditemukan di `/etc/nginx/ssl/warungio.crt`
2. SSL certificate key file tidak cocok dengan certificate
3. SSL certificate sudah expired
4. SSL certificate tidak cocok dengan domain name

**Diagnosis Commands:**
```bash
# Check if SSL certs are mounted correctly:
docker-compose exec nginx ls -la /etc/nginx/ssl/

# Check Nginx config syntax:
docker-compose exec nginx nginx -t

# Test SSL connection:
docker-compose exec nginx openssl s_client -connect localhost:443 -servername warungio.web.id

# Check cert expiration:
docker-compose exec nginx openssl x509 -in /etc/nginx/ssl/warungio.crt -noout -dates
```

**Fix untuk Production:**
```bash
# 1. Buat direktori SSL:
mkdir -p nginx/ssl

# 2. Copy SSL certificate files:
# Let's Encrypt:
cp /etc/letsencrypt/live/warungio.web.id/fullchain.pem nginx/ssl/warungio.crt
cp /etc/letsencrypt/live/warungio.web.id/privkey.pem nginx/ssl/warungio.key

# 3. Restart dengan production config:
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 4. Auto-renewal Let's Encrypt:
# Tambahkan cron job:
# 0 3 * * * docker-compose -f /path/to/docker-compose.yml run --rm certbot renew && docker-compose exec nginx nginx -s reload
```

---

## 📊 SECURITY SCORECARD

| Area | Score | Notes |
|------|-------|-------|
| Secret Management | ⚠️ 6/10 | .env in gitignore ✅, placeholders in cloudrun.yaml ❌ |
| HTTPS/SSL | ⚠️ 4/10 | Config exists but certs not mounted |
| Authentication | ✅ 8/10 | JWT + OTP + Social Auth + Lockout |
| Authorization | ✅ 7/10 | Role-based middleware + decorators |
| API Security | ✅ 7/10 | Rate limiting, throttling, CORS |
| Database Security | ⚠️ 6/10 | No encryption at rest, no backup |
| Docker Security | ❌ 3/10 | Runs as root, no security options |
| Monitoring | ⚠️ 6/10 | Prometheus ✅, minimal logging ❌ |
| Dependency Mgmt | ⚠️ 5/10 | No vuln scanning |
| Backup/DR | ❌ 2/10 | No backup strategy |
| **OVERALL** | **⚠️ 5.4/10** | **Needs improvement for production readiness** |

---

## ✅ PRODUCTION READINESS CHECKLIST

- [x] Domain `warungio.web.id` terdaftar
- [x] Docker Compose berjalan dengan semua services
- [x] Django migrations berhasil
- [x] Nginx reverse proxy berfungsi (HTTP)
- [ ] **SSL Certificate valid dan terpasang** ❌
- [ ] **ALLOWED_HOSTS mencakup warungio.web.id** ❌
- [ ] **CORS_ALLOWED_ORIGINS mencakup warungio.web.id** ❌
- [ ] **CSRF_TRUSTED_ORIGINS mencakup warungio.web.id** ❌
- [ ] **SECRET_KEY terkonfigurasi di Secret Manager** ❌
- [ ] **DB_PASS terkonfigurasi di Secret Manager** ❌
- [ ] **SMTP credentials valid** ❌
- [ ] **Google OAuth credentials valid** ❌
- [ ] **Midtrans keys terkonfigurasi** ❌
- [ ] **Gemini API key terkonfigurasi** ❌
- [ ] **Security headers berfungsi via curl** ❌
- [ ] **robots.txt dan sitemap.xml accessible** ✅
- [ ] **Rate limiting berfungsi** ✅
- [x] **HSTS header terkonfigurasi**
- [x] **Container health checks berfungsi**
- [x] **Static files accessible**
- [ ] **Automated backup berjalan** ❌
- [ ] **Monitoring alerts terkonfigurasi** ❌
- [ ] **Error tracking (Sentry) terintegrasi** ❌

---

## 🛠️ IMMEDIATE PATCH PLAN (Prioritas)

### Priority 1 - Critical (Fix Hari Ini)

1. **Set ALLOWED_HOSTS**: 
   ```
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,.run.app,warungio.web.id,www.warungio.web.id
   ```

2. **Pasang SSL Certificate**:
   ```bash
   # Via Let's Encrypt (jika server punya akses public):
   certbot certonly --standalone -d warungio.web.id -d www.warungio.web.id
   
   # Copy certs ke nginx/ssl/
   mkdir -p nginx/ssl
   cp /etc/letsencrypt/live/warungio.web.id/fullchain.pem nginx/ssl/
   cp /etc/letsencrypt/live/warungio.web.id/privkey.pem nginx/ssl/
   
   # Deploy:
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

3. **Update CORS_ALLOWED_ORIGINS**:
   ```
   CORS_ALLOWED_ORIGINS=https://warungio.web.id,https://www.warungio.web.id
   ```

4. **Update CSRF_TRUSTED_ORIGINS**:
   ```
   CSRF_TRUSTED_ORIGINS=https://warungio.web.id,https://www.warungio.web.id
   ```

5. **Konfigurasi Secret Manager**: Ganti semua placeholder di cloudrun.yaml dengan actual secrets.

### Priority 2 - High (Fix Minggu Ini)

6. Update Docker untuk non-root user
7. Add Docker security options (cap_drop, no-new-privileges)
8. Implement database backup script
9. Enable INFO level logging for security events
10. Update CI/CD to not hardcode test passwords

### Priority 3 - Medium (Fix Bulan Ini)

11. Implement cloudrun.yaml update dengan ingress restriction
12. Add WAF (Cloud Armor)
13. Set up error tracking (Sentry)
14. Update all placeholder values in cloudrun.yaml
15. Set up automated dependency scanning

---

## 📞 REKOMENDASI AKHIR

Untuk mengatasi **ERR_CONNECTION_REFUSED** pada `https://warungio.web.id`:

```bash
# STEP 1: Verifikasi konfigurasi Nginx
docker-compose exec nginx nginx -t

# STEP 2: Cek apakah port 443 terbuka
docker-compose ps
# Pastikan nginx container listening di 0.0.0.0:443

# STEP 3: Cek apakah SSL cert files ada
docker-compose exec nginx ls -la /etc/nginx/ssl/

# STEP 4: Jika cert tidak ada, buat self-signed untuk testing:
docker-compose run --rm nginx openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 -keyout /etc/nginx/ssl/warungio.key \
  -out /etc/nginx/ssl/warungio.crt \
  -subj "/CN=warungio.web.id"

# STEP 5: Restart dengan production config
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# STEP 6: Verifikasi HTTPS
curl -k https://localhost/health/
curl -I https://warungio.web.id
```

---

*Audit completed by Warungio Security Engineering Team*  
*Next scheduled audit: July 21, 2027*
