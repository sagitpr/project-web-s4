/**
 * Login page - Warungio
 * JWT authentication via Django REST API.
 * Supports email/password login + social login (Google, Facebook, Apple).
 * Redirects to buyer or seller dashboard based on user role.
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

  /** Validate redirect URL — only allow relative paths to prevent open redirect */
  function isValidRedirect(url) {
    if (!url || typeof url !== 'string') return false;
    return url.startsWith('/') && !url.startsWith('//') && !url.includes('://');
  }

  /**
   * Validate that the next URL matches the user's role.
   * A buyer can only be redirected to /buyer/* paths.
   * A seller can only be redirected to /seller/* paths.
   * An admin can only be redirected to /admin/* paths.
   * If no role-specific prefix matches, fall back to role-based redirect.
   */
  function isRoleAllowedRedirect(nextUrl, role) {
    if (!nextUrl || !role) return false;
    if (role === 'buyer') return nextUrl.startsWith('/buyer/');
    if (role === 'seller') return nextUrl.startsWith('/seller/');
    if (role === 'admin') return nextUrl.startsWith('/admin/');
    return false;
  }

  function handleAuthResponse(data) {
    window.WarungioAuth.login(data.access, data.refresh, data.user);
    const role = data.user.role;
    
    const params = new URLSearchParams(window.location.search);
    const nextUrl = params.get('next');
    // Only allow next parameter if it matches the user's role — prevents role mismatch
    if (nextUrl && isValidRedirect(nextUrl) && isRoleAllowedRedirect(nextUrl, role)) {
      window.location.href = nextUrl;
      return;
    }

    if (role === 'buyer') {
      window.location.href = '/buyer/home/';
    } else if (role === 'seller') {
      window.location.href = '/seller/dashboard/';
    } else if (role === 'admin') {
      window.location.href = '/admin/';
    } else {
      window.location.href = '/';
    }
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
            loginBtn.textContent = 'Masuk';
          }
          return;
        }
        const data = await WarungioAPI.login(email, password);
        handleAuthResponse(data);
      } catch (err) {
        // Network errors (server down) show "Failed to fetch" — replace with friendlier message
        var msg = err.message;
        if (!msg || msg === 'Failed to fetch' || msg === 'NetworkError' || msg.indexOf('NetworkError') !== -1 || msg.indexOf('Failed to fetch') !== -1) {
          msg = 'Gagal terhubung ke server. Pastikan server Warungio berjalan.';
        }
        setMessage(msg);
        if (loginBtn) {
          loginBtn.disabled = false;
          loginBtn.textContent = 'Masuk';
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
              access_token: accessToken
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
          });
          handleAuthResponse(data);
        } catch (err) {
          setMessage(err.message);
        }
      })();
    }
  })();

  // ── Pre-fill email from query param (after registration) ──
  const params = new URLSearchParams(window.location.search);
  const registeredEmail = params.get('email');
  if (registeredEmail && emailInput) {
    emailInput.value = registeredEmail;
    if (pwdInput) pwdInput.focus();
  }

  // ── Auto-redirect if already authenticated via JWT ──
  // Prevents redirect loop: user with valid JWT in localStorage but expired
  // Django session gets redirected to /auth/login/ by login_required decorator.
  // Detect valid JWT → redirect to role-appropriate dashboard immediately.
  (function checkExistingAuth() {
    if (window.WarungioAuth && window.WarungioAuth.isAuthenticated()) {
      const user = window.WarungioAuth.getUser();
      if (user && user.role) {
        const role = user.role;
        // Use the next parameter if present and matches role, otherwise use default
        const nextUrl = params.get('next');
        if (nextUrl && isValidRedirect(nextUrl) && role === 'buyer' && nextUrl.startsWith('/buyer/')) {
          window.location.href = nextUrl;
        } else if (nextUrl && isValidRedirect(nextUrl) && role === 'seller' && nextUrl.startsWith('/seller/')) {
          window.location.href = nextUrl;
        } else if (role === 'seller') {
          window.location.href = '/seller/dashboard/';
        } else if (role === 'admin') {
          window.location.href = '/admin/';
        } else {
          window.location.href = '/buyer/home/';
        }
      }
    }
  })();
})();
