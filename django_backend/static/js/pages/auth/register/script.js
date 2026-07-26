/**
 * Registration page - Warungio
 * Creates user via Django REST API, then redirects to OTP verification.
 * Supports email/password registration + social registration (Google, Facebook, Apple).
 */
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('registerForm');
  const passwordInput = document.getElementById('password');
  const confirmInput = document.getElementById('confirm_password');
  const eyeBtn = document.getElementById('eyeBtn');
  const submitBtn = form?.querySelector('button[type="submit"]');
  const formMessage = document.getElementById('formMessage');

  function setMessage(text, type) {
    if (!formMessage) return;
    formMessage.textContent = text;
    formMessage.className = 'form-message ' + (type || 'error');
    formMessage.style.display = 'block';

    // Auto-dismiss success after 6s
    if (type === 'success') {
      setTimeout(() => {
        if (formMessage && formMessage.textContent === text) {
          formMessage.classList.add('fade-out');
          setTimeout(() => { formMessage.style.display = 'none'; }, 400);
        }
      }, 6000);
    }
  }

  function showToastNotification(title, message) {
    let container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = 'toast-notification-custom';

    const checkIcon = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="20 6 9 17 4 12"></polyline>
      </svg>
    `;

    toast.innerHTML = `
      <div class="toast-custom-icon">
        ${checkIcon}
      </div>
      <div class="toast-custom-content">
        <div class="toast-custom-title">${title}</div>
        <div class="toast-custom-message">${message}</div>
      </div>
    `;

    container.appendChild(toast);

    // Force reflow
    toast.offsetHeight;

    // Show toast with slide-in
    toast.classList.add('show');

    // Auto-remove after 3 seconds
    setTimeout(() => {
      toast.classList.remove('show');
      toast.classList.add('hide');
      setTimeout(() => {
        toast.remove();
        if (container.children.length === 0) {
          container.remove();
        }
      }, 300);
    }, 3000);
  }

  // ── Real-time field validation ──
  const fields = [
    { id: 'name', validate: v => v.trim().length >= 2 },
    { id: 'email', validate: v => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v) },
    { id: 'phone', validate: v => v.trim().length >= 8 },
    { id: 'address', validate: v => v.trim().length >= 5 },
  ];
  fields.forEach(({ id, validate }) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('input', () => {
      const shell = el.closest('.input-shell');
      if (!shell) return;
      const v = el.value;
      if (!v.trim()) {
        shell.classList.remove('is-valid', 'is-invalid');
      } else if (validate(v)) {
        shell.classList.add('is-valid');
        shell.classList.remove('is-invalid');
      } else {
        shell.classList.add('is-invalid');
        shell.classList.remove('is-valid');
      }
    });
  });

  // ── Helper: handle auth response — redirect based on user role from API ──
  // Social login (Google, Facebook, Apple) returns the user's role in the API response.
  // The role is the SINGLE SOURCE OF TRUTH (from database, not query params or localStorage).
  // Uses centralized getRoleDashboardUrl() which maps role→URL:
  //   buyer  → /buyer/home/
  //   seller → /seller/dashboard/
  //   admin  → /admin/
  //   no role → / (Landing Page — the only public homepage)
  function handleAuthResponse(data) {
    window.WarungioAuth.login(data.access, data.refresh, data.user);

    const params = new URLSearchParams(window.location.search);
    const nextUrl = params.get('next');
    
    // Determine the user's actual role from the API response (database)
    var actualRole = data.user ? data.user.role : null;
    
    // Only allow ?next= if it matches the user's role (cross-role guard)
    if (nextUrl && window.WarungioAuth && typeof window.WarungioAuth.isValidRedirect === 'function' && typeof window.WarungioAuth.isRoleAllowedRedirect === 'function') {
      if (window.WarungioAuth.isValidRedirect(nextUrl) && window.WarungioAuth.isRoleAllowedRedirect(nextUrl, actualRole)) {
        window.location.href = nextUrl;
        return;
      }
    } else if (nextUrl && nextUrl.startsWith('/') && !nextUrl.startsWith('//') && !nextUrl.includes('://') && nextUrl.startsWith('/buyer/')) {
      // Legacy fallback (only if auth.js not loaded)
      window.location.href = nextUrl;
      return;
    }

    // Use centralized helper with the API-provided role (source of truth)
    if (window.WarungioAuth && typeof window.WarungioAuth.getRoleDashboardUrl === 'function') {
      window.location.href = window.WarungioAuth.getRoleDashboardUrl(actualRole);
      return;
    }

    // Hard fallback (should not be reached if auth.js is loaded)
    if (actualRole === 'buyer') { window.location.href = '/buyer/home/'; return; }
    if (actualRole === 'seller') { window.location.href = '/seller/dashboard/'; return; }
    if (actualRole === 'admin') { window.location.href = '/admin/'; return; }
    window.location.href = '/';
  }

  /**
   * Handle registration response: redirect to OTP page using backend-provided URL.
   * The backend returns { requires_otp: true, redirect_url: "/auth/otp/?email=..." }
   * The frontend MUST use the backend-provided redirect_url, NEVER construct its own.
   */
  function handleRegisterResponse(data, email) {
    // If backend provides a redirect_url, use it directly
    if (data.redirect_url) {
      window.location.href = data.redirect_url;
      return;
    }
    
    // Fallback: construct redirect URL manually (only if backend didn't provide one)
    const params = new URLSearchParams(window.location.search);
    const nextUrl = params.get('next');
    var redirectUrl = '/auth/otp/?email=' + encodeURIComponent(email) + '&purpose=registration';
    if (nextUrl) {
      redirectUrl += '&next=' + encodeURIComponent(nextUrl);
    }
    window.location.href = redirectUrl;
  }

  if (eyeBtn && passwordInput) {
    let visible = false;
    eyeBtn.addEventListener('click', () => {
      visible = !visible;
      passwordInput.type = visible ? 'text' : 'password';
      const open = document.getElementById('eyeOpen');
      const closed = document.getElementById('eyeClosed');
      if (open) open.style.display = visible ? 'none' : 'block';
      if (closed) closed.style.display = visible ? 'block' : 'none';
    });
  }

  passwordInput?.addEventListener('input', () => {
    const val = passwordInput.value;
    let strength = 0;
    if (val.length >= 8) strength++;
    if (/[A-Z]/.test(val)) strength++;
    if (/[a-z]/.test(val)) strength++;
    if (/[0-9]/.test(val)) strength++;
    if (/[^A-Za-z0-9]/.test(val)) strength++;
    const bar = document.getElementById('strengthBar');
    const text = document.getElementById('strengthText');
    if (!bar) return;
    const levels = ['', 'Lemah', 'Cukup', 'Sedang', 'Kuat', 'Sangat Kuat'];
    const colors = ['', '#ef4444', '#f59e0b', '#eab308', '#22c55e', '#16a34a'];
    bar.style.width = (strength / 5) * 100 + '%';
    bar.style.background = colors[strength] || '#ef4444';
    if (text) text.textContent = levels[strength] || '';
  });

  confirmInput?.addEventListener('input', () => {
    if (confirmInput.value && confirmInput.value !== passwordInput.value) {
      confirmInput.setCustomValidity('Kata sandi tidak cocok');
    } else {
      confirmInput.setCustomValidity('');
    }
  });

  // ── Detect registration role from page URL or query param ──
  // /auth/register/ → buyer (default)
  // /auth/register-mitra/ or ?role=seller → seller
  var detectedRole = 'buyer';
  var pathname = window.location.pathname || '';
  if (pathname.indexOf('mitra') !== -1 || pathname.indexOf('seller') !== -1) {
    detectedRole = 'seller';
  }
  var roleParam = new URLSearchParams(window.location.search).get('role');
  if (roleParam === 'seller' || roleParam === 'buyer') {
    detectedRole = roleParam;
  }

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!form.checkValidity()) { form.reportValidity(); return; }
    if (passwordInput.value !== confirmInput.value) {
      setMessage('Konfirmasi kata sandi tidak cocok.');
      return;
    }
    const name = document.getElementById('name')?.value.trim();
    const email = document.getElementById('email')?.value.trim();
    const phone = document.getElementById('phone')?.value.trim();
    const password = passwordInput.value;
    const address = document.getElementById('address')?.value.trim();

    if (submitBtn) { submitBtn.disabled = true; submitBtn.innerHTML = '<span class="spinner"></span> Mendaftarkan...'; }
    if (formMessage) {
      formMessage.style.display = 'none';
      formMessage.classList.remove('fade-out');
    }

    try {
      const data = await WarungioAPI.register({
        full_name: name,
        email,
        phone,
        password,
        password2: password,
        address,
        role: detectedRole,
      });

      showToastNotification(
        'Registrasi Berhasil',
        'Kode OTP telah dikirim ke email Anda. Silakan cek kotak masuk atau folder spam untuk melakukan verifikasi akun.'
      );

      // CRITICAL: Use backend-provided redirect_url. Never construct manually.
      // The backend ensures the redirect goes to the correct OTP page.
      // Append otp_code for DEBUG mode (frontend development convenience).
      if (data.redirect_url && data.otp_code) {
        var separator = data.redirect_url.indexOf('?') === -1 ? '?' : '&';
        data.redirect_url += separator + 'otp=' + encodeURIComponent(data.otp_code);
      }
      setTimeout(() => {
        handleRegisterResponse(data, email);
      }, 2000);
    } catch (err) {
      setMessage(err.message);
      if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Daftar Sekarang'; }
    }
  });

  // ══════════════════════════════════════════════════════════════════════════
  //  GOOGLE SIGN-IN (GSI) — initialized ONCE, not on every click
  // ══════════════════════════════════════════════════════════════════════════

  let gsiReady = false;
  let gsiClientId = '';
  let gsiInitializing = false;

  function initGSI() {
    if (gsiReady || gsiInitializing) return;
    gsiInitializing = true;

    // Fetch Google Client ID FIRST (before waiting for google.accounts)
    // This prevents the config from being missed if google.accounts script
    // fails to load (e.g., blocked by ad blocker or CSP)
    (async function setup() {
      try {
        if (typeof WarungioAPI !== 'undefined' && WarungioAPI.getSocialAuthConfig) {
          var config = await WarungioAPI.getSocialAuthConfig('google');
          if (config && config.google_client_id && !config.google_client_id.includes('your-google')) {
            gsiClientId = config.google_client_id;
          }
        }
      } catch (e) {
        console.warn('Failed to fetch Google config:', e);
      }

      // 2. Wait for google.accounts to be available (up to 5 seconds)
      var maxAttempts = 50;
      var attempts = 0;
      while ((typeof google === 'undefined' || !google.accounts) && attempts < maxAttempts) {
        await new Promise(function (r) { return setTimeout(r, 100); });
        attempts++;
      }

      if (typeof google === 'undefined' || !google.accounts) {
        if (gsiClientId) {
          console.warn('Google GSI library not loaded (client_id available but GSI blocked)');
        } else {
          console.warn('Google Identity Services library not loaded — Google login unavailable');
        }
        gsiInitializing = false;
        return;
      }

      if (!gsiClientId) {
        console.warn('Google Client ID not available — Google login unavailable');
        gsiInitializing = false;
        return;
      }

      // 3. Initialize GSI once
      google.accounts.id.initialize({
        client_id: gsiClientId,
        callback: handleGSICredential,
        cancel_on_tap_outside: true,
      });

      gsiReady = true;
      gsiInitializing = false;
      console.info('Google Sign-In initialized');
    })();
  }

  /** Shared credential callback for Google One Tap / popup */
  function handleGSICredential(response) {
    if (!response || !response.credential) return;

    var btn = document.querySelector('.btn-social.google');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Memproses...';

    WarungioAPI.socialLogin('google', { credential: response.credential })
      .then(function (data) { handleAuthResponse(data); })
      .catch(function (err) {
        setMessage(err.message);
        btn.disabled = false;
        var img = (typeof WarungioAssets !== 'undefined' && WarungioAssets.img)
          ? WarungioAssets.img('google-logo.png')
          : '/static/images/google-logo.png';
        btn.innerHTML = '<img src="' + img + '" alt="Google" /><span>Google</span>';
      });
  }

  // Kick off GSI initialization immediately
  initGSI();

  // ── Google button click: only prompt() ──
  const googleBtn = document.querySelector('.btn-social.google');
  if (googleBtn) {
    googleBtn.addEventListener('click', function googleRegister() {
      if (typeof google === 'undefined' || !google.accounts) {
        setMessage('Memuat layanan Google... Silakan coba lagi.');
        return;
      }

      if (!gsiReady) {
        setMessage('Memuat layanan Google... Silakan coba lagi.');
        return;
      }

      google.accounts.id.prompt();
    });
  }

  // ── Social Registration: Facebook ──
  const fbBtn = document.querySelector('.btn-social.facebook');
  if (fbBtn) {
    fbBtn.addEventListener('click', function facebookRegister() {
      if (typeof FB === 'undefined') {
        setMessage('Memuat layanan Facebook... Silakan coba lagi.');
        return;
      }

      FB.login(async (response) => {
        if (response.authResponse) {
          const accessToken = response.authResponse.accessToken;
          fbBtn.disabled = true;
          fbBtn.textContent = 'Memproses...';
          try {
            const data = await WarungioAPI.socialLogin('facebook', {
              access_token: accessToken
            });
            handleAuthResponse(data);
          } catch (err) {
            setMessage(err.message);
            fbBtn.disabled = false;
            fbBtn.innerHTML = '<img src="' + WarungioAssets.img('facebook-1.png') + '" alt="Facebook" /><span>Facebook</span>';
          }
        } else {
          setMessage('Login Facebook dibatalkan.');
        }
      }, { scope: 'public_profile,email', return_scopes: true });
    });
  }

  // ── Social Registration: Apple ──
  const appleBtn = document.querySelector('.btn-social.apple');
  if (appleBtn) {
    appleBtn.addEventListener('click', function appleRegister() {
      const redirectUri = window.location.origin + '/social-callback/apple.html';
      const clientId = 'com.warungio.app';

      try {
        if (window.AppleID) {
          AppleID.auth.init({
            clientId: clientId,
            scope: 'name email',
            redirectURI: redirectUri,
            state: window.location.href,
            usePopup: true,
          });
          AppleID.auth.signIn();
        } else {
          window.location.href = 'https://appleid.apple.com/auth/authorize?' +
            'client_id=' + encodeURIComponent(clientId) +
            '&redirect_uri=' + encodeURIComponent(redirectUri) +
            '&response_type=code%20id_token' +
            '&scope=name%20email' +
            '&response_mode=form_post';
        }
      } catch (e) {
        setMessage('Gagal memulai login Apple. Silakan coba lagi.');
      }
    });
  }
});
