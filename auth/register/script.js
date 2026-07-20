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

  // ── Helper: handle auth response — redirect based on user role ──
  // Social login (Google, Facebook, Apple) returns the user's role in the API response.
  // Use it to redirect to the correct entry point:
  //   buyer  → /buyer/home/
  //   seller → /seller/dashboard/
  //   admin  → /admin/
  //   no role → / (Landing Page — the only public homepage)
  function handleAuthResponse(data) {
    window.WarungioAuth.login(data.access, data.refresh, data.user);

    // Use centralized helper to get role-appropriate dashboard URL
    if (window.WarungioAuth && typeof window.WarungioAuth.getRoleDashboardUrl === 'function') {
      window.location.href = window.WarungioAuth.getRoleDashboardUrl(data.user ? data.user.role : null);
      return;
    }

    // Fallback: manual role check
    const role = data.user ? data.user.role : null;
    if (role === 'buyer') { window.location.href = '/buyer/home/'; return; }
    if (role === 'seller') { window.location.href = '/seller/dashboard/'; return; }
    if (role === 'admin') { window.location.href = '/admin/'; return; }
    window.location.href = '/';
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

      // Password not stored client-side for security — OTP auto-login handles session
      showToastNotification(
        'Registrasi Berhasil',
        'Kode OTP telah dikirim ke email Anda. Silakan cek kotak masuk atau folder spam untuk melakukan verifikasi akun.'
      );

      const redirectUrl =
        '/auth/otp/?email=' +
        encodeURIComponent(email) +
        (data.otp_code ? '&otp=' + encodeURIComponent(data.otp_code) : '');

      setTimeout(() => {
        window.location.href = redirectUrl;
      }, 2000);
    } catch (err) {
      setMessage(err.message);
      if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Daftar Sekarang'; }
    }
  });

  // ── Social Registration: Google ──
  const googleBtn = document.querySelector('.btn-social.google');
  if (googleBtn) {
    googleBtn.addEventListener('click', async function googleRegister() {
      if (typeof google === 'undefined' || !google.accounts) {
        setMessage('Memuat layanan Google... Silakan coba lagi.');
        return;
      }

      let clientId = '';
      try {
        const config = await WarungioAPI.getSocialAuthConfig('google');
        if (config.google_client_id) clientId = config.google_client_id;
      } catch (e) {
      }

      // Guard: block login if client ID is missing or still placeholder
      if (!clientId || clientId.includes('your-google')) {
        setMessage('Konfigurasi Google Login belum siap. Silakan coba lagi nanti.');
        console.error('Google Client ID not configured:', clientId);
        return;
      }

      google.accounts.id.initialize({
        client_id: clientId,
        callback: async (response) => {
          if (response.credential) {
            googleBtn.disabled = true;
            googleBtn.textContent = 'Memproses...';
            try {
              const data = await WarungioAPI.socialLogin('google', {
                credential: response.credential
              });
              handleAuthResponse(data);
            } catch (err) {
              setMessage(err.message);
              googleBtn.disabled = false;
                var googleImgSrc = (typeof WarungioAssets !== 'undefined' && WarungioAssets.img)
                ? WarungioAssets.img('google-logo.png')
                : '/static/images/google-logo.png';
              googleBtn.innerHTML = '<img src="' + googleImgSrc + '" alt="Google" /><span>Google</span>';
            }
          }
        },
        cancel_on_tap_outside: true,
      });

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
              var fbImgSrc = (typeof WarungioAssets !== 'undefined' && WarungioAssets.img)
                ? WarungioAssets.img('facebook-1.png')
                : '/static/images/facebook-1.png';
              fbBtn.innerHTML = '<img src="' + fbImgSrc + '" alt="Facebook" /><span>Facebook</span>';
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
