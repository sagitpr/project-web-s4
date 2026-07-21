/**
 * Login page - Warungio
 * JWT authentication via Django REST API.
 * Supports email/password login + social login (Google, Facebook, Apple).
 *
 * After successful authentication, the redirect target is determined by the
 * user's ACTUAL role returned by the API (from the database), NOT from the
 * ?role= query parameter. This prevents role spoofing via URL manipulation.
 *
 * Redirect priority:
 *   1. ?next= param if it matches the user's role prefix (cross-role guard)
 *   2. Role-based redirect using the API response's user.role (the source of truth)
 *   3. Default → / (Landing Page — never auto-redirect to Buyer Home)
 */
(function () {
  'use strict';

  const eyeBtn = document.getElementById('eyeBtn');
  const pwdInput = document.getElementById('password');
  const eyeOpen = document.getElementById('eyeOpen');
  const eyeClosed = document.getElementById('eyeClosed');
  const loginForm = document.getElementById('loginForm');
  const loginBtn = document.getElementById('loginBtn');
  const formMessage = document.getElementById('formMessage');
  const emailInput = document.getElementById('email');

  // ── Read redirect-related query params (next only, NOT role) ──
  const loginParams = new URLSearchParams(window.location.search);
  
  // ── Detect login entry point: 'seller' or 'buyer' (default) ──
  // Determined from the URL path: /auth/login-seller/ → seller, /auth/login/ → buyer
  var loginEntry = 'buyer';
  if (window.location.pathname.indexOf('login-seller') !== -1) {
    loginEntry = 'seller';
  }

  // ── Password toggle ──
  if (eyeBtn && pwdInput && eyeOpen && eyeClosed) {
    let visible = false;
    eyeBtn.addEventListener('click', () => {
      visible = !visible;
      pwdInput.type = visible ? 'text' : 'password';
      eyeOpen.style.display = visible ? 'none' : 'block';
      eyeClosed.style.display = visible ? 'block' : 'none';
    });
  }

  // ── Helper: show form message ──
  function setMessage(text, type) {
    if (!formMessage) return;
    formMessage.textContent = text;
    formMessage.className = 'form-message ' + (type || 'error');
    formMessage.style.display = 'block';
    
    // Auto-dismiss success messages after 6s
    if (type === 'success') {
      setTimeout(() => {
        if (formMessage && formMessage.textContent === text) {
          formMessage.classList.add('fade-out');
          setTimeout(() => { formMessage.style.display = 'none'; }, 400);
        }
      }, 6000);
    }
    
    // Shake animation on error, clean up after animation
    if (type === 'error') {
      const shell = emailInput?.closest('.input-shell') || pwdInput?.closest('.input-shell');
      if (shell) {
        shell.classList.remove('shake');
        void shell.offsetWidth; // force reflow to restart animation
        shell.classList.add('shake');
        setTimeout(() => shell.classList.remove('shake'), 500);
      }
    }
  }

  // ── Real-time field validation ──
  function validateField(input) {
    const shell = input?.closest('.input-shell');
    if (!shell) return;
    if (input.value.trim()) {
      if (input.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.value)) {
        shell.classList.add('is-invalid');
        shell.classList.remove('is-valid');
      } else {
        shell.classList.add('is-valid');
        shell.classList.remove('is-invalid');
      }
    } else {
      shell.classList.remove('is-valid', 'is-invalid');
    }
  }
  emailInput?.addEventListener('input', () => validateField(emailInput));
  pwdInput?.addEventListener('input', () => {
    const shell = pwdInput.closest('.input-shell');
    if (shell) {
      if (pwdInput.value.length >= 8) {
        shell.classList.add('is-valid');
        shell.classList.remove('is-invalid');
      } else if (pwdInput.value.length > 0) {
        shell.classList.add('is-invalid');
        shell.classList.remove('is-valid');
      } else {
        shell.classList.remove('is-valid', 'is-invalid');
      }
    }
  });

  /**
   * Determine the redirect URL after successful login.
   * Uses the user's ACTUAL role from the API response (database), NOT query params.
   * Priority:
   *   1. ?next= param if it matches the user's role prefix (prevents cross-role redirects)
   *   2. Role-based redirect from the API response (single source of truth)
   *   3. Default → / (Landing Page — the only public homepage)
   *
   * @param {string|null} apiRole - The user's actual role from the API response
   */
  function getRedirectUrl(apiRole) {
    const nextUrl = loginParams.get('next');
    // Only allow ?next= if it belongs to the authenticated user's role
    if (nextUrl && nextUrl.startsWith('/') && !nextUrl.startsWith('//') && !nextUrl.includes('://')) {
      if (window.WarungioAuth && typeof window.WarungioAuth.isRoleAllowedRedirect === 'function') {
        // Cross-role guard: Seller cannot be redirected to /buyer/* and vice versa
        if (window.WarungioAuth.isRoleAllowedRedirect(nextUrl, apiRole)) {
          return nextUrl;
        }
      } else {
        // Fallback: basic safety check
        return nextUrl;
      }
    }
    // Use the API-provided role (source of truth from database)
    if (window.WarungioAuth && typeof window.WarungioAuth.getRoleDashboardUrl === 'function') {
      return window.WarungioAuth.getRoleDashboardUrl(apiRole);
    }
    // Hard fallback (should not be reached if auth.js is loaded)
    if (apiRole === 'seller') return '/seller/dashboard/';
    if (apiRole === 'buyer') return '/buyer/home/';
    if (apiRole === 'admin') return '/admin/';
    return '/';
  }

  /**
   * Handle login response: store tokens and redirect explicitly.
   * Uses the user's ACTUAL role from the API response (database) for redirect.
   * NEVER relies on query params or localStorage for role determination.
   */
  function handleAuthResponse(data) {
    window.WarungioAuth.login(data.access, data.refresh, data.user);
    // Use the API-provided role (from database) — not query params, not localStorage
    var actualRole = data.user ? data.user.role : null;
    window.location.href = getRedirectUrl(actualRole);
  }

  // ── Login submit ──
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      const email = emailInput.value.trim();
      const password = pwdInput.value;

      if (!email || !password) {
        setMessage('Email dan password harus diisi.');
        return;
      }

      // Loading state
      if (loginBtn) {
        loginBtn.disabled = true;
        loginBtn.innerHTML =
          '<span class="spinner"></span> Memproses...';
      }
      if (formMessage) {
        formMessage.style.display = 'none';
        formMessage.classList.remove('fade-out');
      }

      try {
        if (typeof WarungioAPI === 'undefined' || typeof WarungioAPI.login !== 'function') {
          setMessage('Gagal memuat API. Periksa koneksi internet atau coba refresh halaman.');
          if (loginBtn) {
            loginBtn.disabled = false;
            loginBtn.textContent = loginEntry === 'seller' ? 'Masuk sebagai Mitra' : 'Masuk Sekarang';
          }
          return;
        }
        // Send login_entry to backend for role validation
        const data = await WarungioAPI.login(email, password, loginEntry);
        handleAuthResponse(data);
      } catch (err) {
        // ── Check if the account is unverified → redirect to OTP verification ──
        // Backend returns HTTP 403 with requires_otp=true and redirect_url
        if (err.requires_otp || err.needs_verification) {
          var verificationEmail = err.email || email;
          
          // Reset button state before redirect
          if (loginBtn) {
            loginBtn.disabled = false;
            loginBtn.textContent = loginEntry === 'seller' ? 'Masuk sebagai Mitra' : 'Masuk Sekarang';
          }
          
          // CRITICAL: Use backend-provided redirect_url when available.
          // The backend ensures the correct OTP page with proper parameters.
          if (err.redirect_url) {
            window.location.href = err.redirect_url;
          } else {
            // Fallback: construct redirect manually
            window.location.href = '/auth/otp/?email=' + encodeURIComponent(verificationEmail) + '&purpose=registration';
          }
          return;
        }

        // Network errors (server down) show "Failed to fetch" — replace with friendlier message
        var msg = err.message;
        if (!msg || msg === 'Failed to fetch' || msg === 'NetworkError' || msg.indexOf('NetworkError') !== -1 || msg.indexOf('Failed to fetch') !== -1) {
          msg = 'Gagal terhubung ke server. Pastikan server Warungio berjalan.';
        }
        setMessage(msg);
        if (loginBtn) {
          loginBtn.disabled = false;
          loginBtn.textContent = loginEntry === 'seller' ? 'Masuk sebagai Mitra' : 'Masuk Sekarang';
        }
      }
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  //  GOOGLE SIGN-IN (GSI) — initialized ONCE, not on every click
  // ══════════════════════════════════════════════════════════════════════════

  let gsiReady = false;          // true after google.accounts.id.initialize() called
  let gsiClientId = '';         // cached Google Client ID
  let gsiInitializing = false;   // guard against concurrent init attempts

  /**
   * Poll for GSI library readiness, then fetch config + initialize once.
   * Called immediately on page load.
   */
  function initGSI() {
    if (gsiReady || gsiInitializing) return;
    gsiInitializing = true;

    // Wrap in IIFE so we can use async/await
    (async function setup() {
      // 1. Wait for google.accounts to be available
      var maxAttempts = 50;       // ~5 seconds (50 × 100ms)
      var attempts = 0;
      while ((typeof google === 'undefined' || !google.accounts) && attempts < maxAttempts) {
        await new Promise(function (r) { return setTimeout(r, 100); });
        attempts++;
      }

      if (typeof google === 'undefined' || !google.accounts) {
        console.warn('Google Identity Services library not loaded after 5s — Google login unavailable');
        gsiInitializing = false;
        return;
      }

      // 2. Fetch Google Client ID from backend (only once)
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

      if (!gsiClientId) {
        console.error('Google Client ID not configured — Google login unavailable');
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

    WarungioAPI.socialLogin('google', { credential: response.credential, login_entry: loginEntry })
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

  // ── Google button click: only prompt() — initialize already done ──
  const googleBtn = document.querySelector('.btn-social.google');
  if (googleBtn) {
    googleBtn.addEventListener('click', function googleLogin() {
      if (typeof google === 'undefined' || !google.accounts) {
        setMessage('Memuat layanan Google... Silakan coba lagi.');
        return;
      }

      if (!gsiReady) {
        setMessage('Memuat layanan Google... Silakan coba lagi.');
        return;
      }

      google.accounts.id.prompt(); // Show One Tap or popup
    });
  }

  // ── Social Login: Facebook ──
  const fbBtn = document.querySelector('.btn-social.facebook');
  if (fbBtn) {
    fbBtn.addEventListener('click', function facebookLogin() {
      if (typeof FB === 'undefined') {
        setMessage('Memuat layanan Facebook... Silakan coba lagi.');
        return;
      }

      FB.login(async (response) => {
        if (response.authResponse) {
          const accessToken = response.authResponse.accessToken;
          fbBtn.disabled = true;
          fbBtn.innerHTML = '<span class="spinner"></span> Memproses...';
          try {
            const data = await WarungioAPI.socialLogin('facebook', {
              access_token: accessToken,
              login_entry: loginEntry
            });
            handleAuthResponse(data);
          } catch (err) {
            setMessage(err.message);
            fbBtn.disabled = false;
            var fbImg = (typeof WarungioAssets !== 'undefined' && WarungioAssets.img) ? WarungioAssets.img('facebook-1.png') : '/static/images/facebook-1.png';
            fbBtn.innerHTML = '<img src="' + fbImg + '" alt="Facebook" /><span>Facebook</span>';
          }
        } else {
          setMessage('Login Facebook dibatalkan.');
        }
      }, { scope: 'public_profile,email', return_scopes: true });
    });
  }

  // ── Social Login: Apple ──
  const appleBtn = document.querySelector('.btn-social.apple');
  if (appleBtn) {
    appleBtn.addEventListener('click', function appleLogin() {
      // Apple Sign-In requires a redirect-based flow
      // We'll open a popup/callback approach
      const redirectUri = window.location.origin + '/social-callback/apple.html';
      const clientId = 'com.warungio.app';

      // Store the current page so we can return after auth
      sessionStorage.setItem('warungio_social_login_pending', 'true');

      // Use Apple's Sign In with JS (if loaded) or redirect
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
          // Fallback: redirect to Apple Sign-In page
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

  // ── Handle Apple callback (if redirected back) ──
  (function handleAppleCallback() {
    const urlParams = new URLSearchParams(window.location.hash.replace('#', '?'));
    const idToken = urlParams.get('id_token');
    const authCode = urlParams.get('authorization_code');
    const userData = urlParams.get('user');

    if (idToken) {
      (async () => {
        try {
          const data = await WarungioAPI.socialLogin('apple', {
            identity_token: idToken,
            authorization_code: authCode,
            user: userData ? JSON.parse(decodeURIComponent(userData)) : {},
            login_entry: loginEntry,
          });
          handleAuthResponse(data);
        } catch (err) {
          setMessage(err.message);
        }
      })();
    }
  })();

  // ── Pre-fill email from query param (after OTP verification redirect) ──
  const params = new URLSearchParams(window.location.search);
  const registeredEmail = params.get('email');
  if (registeredEmail && emailInput) {
    emailInput.value = registeredEmail;
    if (pwdInput) pwdInput.focus();
  }
  
  // ── Show success message when redirected from OTP verification ──
  if (params.get('verified') === '1') {
    var successMsg = loginEntry === 'seller'
      ? 'Akun Mitra berhasil diverifikasi! Silakan masuk dengan email dan password Anda.'
      : 'Akun berhasil diverifikasi! Silakan masuk dengan email dan password Anda.';
    setMessage(successMsg, 'success');
  }

  // ── Auto-redirect if already authenticated via SESSION (not JWT) ──
  // 
  // CRITICAL: We verify the Django SESSION exists, NOT just the JWT in localStorage.
  // 
  // Why: JWT expires in 2 hours (access) / 30 days (refresh). 
  //      Django session expires in 14 days (default SESSION_COOKIE_AGE).
  //      If the session cookie expires but JWT is still valid, the old code
  //      would redirect to a login_required page → 302 redirect back to login → LOOP!
  //
  // Fix: Make a fetch to /api/auth/check/ WITHOUT JWT Authorization header.
  //      - SessionAuthentication checks the session cookie.
  //      - If session valid → 200 → redirect using API role.
  //      - If session invalid → 401 → stay on login page (no loop!).
  //
  (async function checkExistingSession() {
    if (!window.WarungioAuth) return;
    
    // Quick check: no JWT in localStorage → definitely not logged in
    if (!window.WarungioAuth.getAccessToken()) return;
    
    // JWT exists — but does the Django session cookie exist and validate?
    // Call /api/auth/check/ WITHOUT JWT header (only session cookie via credentials).
    // If session exists → SessionAuthentication returns user → 200.
    // If no session → 401/403 → stay on login page (don't redirect!).
    try {
      var checkHeaders = { 'Accept': 'application/json' };
      // Reuse centralized getCSRFToken from auth.js
      if (window.WarungioAuth && typeof window.WarungioAuth.getCSRFToken === 'function') {
        var csrfToken = window.WarungioAuth.getCSRFToken();
        if (csrfToken) {
          checkHeaders['X-CSRFToken'] = csrfToken;
        }
      }

      const resp = await fetch('/api/auth/check-auth/', {
        method: 'GET',
        credentials: 'same-origin',
        headers: checkHeaders,
      });
      
      if (!resp.ok) {
        // Session is invalid/expired — stay on login page
        return;
      }
      
      // Session exists! Redirect using the user's ACTUAL role from the API response.
      const data = await resp.json();
      if (!data || !data.authenticated || !data.user) {
        return;  // Safety check
      }
      
      // Use the API-provided role (from database) — never from query params or localStorage
      var sessionRole = data.user.role;
      
      var nextUrl = loginParams.get('next');
      // Only allow ?next= if it matches the user's role (cross-role guard)
      if (nextUrl && window.WarungioAuth.isValidRedirect(nextUrl) && window.WarungioAuth.isRoleAllowedRedirect(nextUrl, sessionRole)) {
        window.location.href = nextUrl;
      } else {
        // Use role from API (database) — not query params
        window.location.href = getRedirectUrl(sessionRole);
      }
    } catch (e) {
      // Network error — stay on login page, don't redirect
      console.warn('Session check failed (non-blocking):', e);
    }
  })();
})();
