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

  /** Validate redirect URL — only allow relative paths to prevent open redirect */
  function isValidRedirect(url) {
    if (!url || typeof url !== 'string') return false;
    return url.startsWith('/') && !url.startsWith('//') && !url.includes('://');
  }

  /**
   * Validate that the next URL matches the user's role.
   * A buyer → /buyer/*, seller → /seller/*, admin → /admin/*
   */
  function isRoleAllowedRedirect(nextUrl, role) {
    if (!nextUrl || !role) return false;
    if (role === 'buyer') return nextUrl.startsWith('/buyer/');
    if (role === 'seller') return nextUrl.startsWith('/seller/');
    if (role === 'admin') return nextUrl.startsWith('/admin/');
    return false;
  }

  // ── Helper: handle auth response and redirect ──
  function handleAuthResponse(data) {
    window.WarungioAuth.login(data.access, data.refresh, data.user);
    const role = data.user.role;
    
    const params = new URLSearchParams(window.location.search);
    const nextUrl = params.get('next');
    // Only allow next parameter if it matches the user's role
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
        role: 'buyer',
      });

      showToastNotification(
        'Registrasi Berhasil',
        'Kode OTP telah dikirim ke email Anda. Silakan cek kotak masuk atau folder spam untuk melakukan verifikasi akun.'
      );

      const params = new URLSearchParams(window.location.search);
      const nextUrl = params.get('next');
      const redirectUrl =
        '/auth/otp/?email=' +
        encodeURIComponent(email) +
        (data.otp_code ? '&otp=' + encodeURIComponent(data.otp_code) : '') +
        (nextUrl ? '&next=' + encodeURIComponent(nextUrl) : '');

      setTimeout(() => {
        window.location.href = redirectUrl;
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

    (async function setup() {
      // 1. Wait for google.accounts to be available
      var maxAttempts = 50;
      var attempts = 0;
      while ((typeof google === 'undefined' || !google.accounts) && attempts < maxAttempts) {
        await new Promise(function (r) { return setTimeout(r, 100); });
        attempts++;
      }

      if (typeof google === 'undefined' || !google.accounts) {
        console.warn('Google Identity Services library not loaded — Google login unavailable');
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
