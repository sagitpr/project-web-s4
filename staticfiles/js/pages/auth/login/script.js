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

  function handleAuthResponse(data) {
    window.WarungioAuth.login(data.access, data.refresh, data.user);
    const role = data.user.role;
    if (role === 'buyer') {
      window.location.href = '/buyer/dashboard/';
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
        const data = await WarungioAPI.login(email, password);
        handleAuthResponse(data);
      } catch (err) {
        setMessage(err.message);
        if (loginBtn) {
          loginBtn.disabled = false;
          loginBtn.textContent = 'Masuk';
        }
      }
    });
  }

  // ── Social Login: Google ──
  const googleBtn = document.querySelector('.btn-social.google');
  if (googleBtn) {
    googleBtn.addEventListener('click', async function googleLogin() {
      // Check if Google Identity Services is loaded
      if (typeof google === 'undefined' || !google.accounts) {
        setMessage('Memuat layanan Google... Silakan coba lagi.');
        return;
      }

      // Fetch Google Client ID from backend
      let clientId = '';
      try {
        const config = await WarungioAPI.getSocialAuthConfig('google');
        if (config.google_client_id) clientId = config.google_client_id;
      } catch (e) {
        console.warn('Failed to fetch Google config:', e);
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
            googleBtn.innerHTML = '<span class="spinner"></span> Memproses...';
            try {
              const data = await WarungioAPI.socialLogin('google', {
                credential: response.credential
              });
              handleAuthResponse(data);
            } catch (err) {
              setMessage(err.message);
              googleBtn.disabled = false;
              googleBtn.innerHTML = `<img src="${WarungioAssets.img('google-logo.png')}" alt="Google" /><span>Google</span>`;
            }
          }
        },
        cancel_on_tap_outside: true,
      });

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
            fbBtn.innerHTML = `<img src="${WarungioAssets.img('facebook-1.png')}" alt="Facebook" /><span>Facebook</span>`;
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
})();
