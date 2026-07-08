/**
 * OTP Verification page - Warungio
 * Verifies OTP via Django REST API.
 */
document.addEventListener('DOMContentLoaded', function() {
  const params = new URLSearchParams(window.location.search);
  const email = params.get('email') || '';
  const testOtp = params.get('otp') || '';
  const purpose = params.get('purpose') || 'registration';

  const otpInputs = document.querySelectorAll('.otp-input');
  const otpForm = document.getElementById('otpForm');
  const phoneDisplay = document.querySelector('.phone-number');
  const resendBtn = document.getElementById('resend-button');
  const countdownEl = document.getElementById('countdown');
  const messageEl = document.getElementById('otpMessage');

  let timeLeft = 55;

  function showMsg(text, type) {
    if (!messageEl) return;
    messageEl.textContent = text;
    messageEl.className = 'otp-message ' + type;
    messageEl.style.display = 'block';
    messageEl.classList.remove('fade-out');

    // Auto-dismiss success after 6s
    if (type === 'success') {
      setTimeout(() => {
        if (messageEl && messageEl.textContent === text) {
          messageEl.classList.add('fade-out');
          setTimeout(() => { messageEl.style.display = 'none'; }, 400);
        }
      }, 6000);
    }
  }

  // Handle email query param
  const emailInput = document.getElementById('emailInput');
  const emailGroup = document.getElementById('emailGroup');
  const otpDesc = document.querySelector('.otp-description');

  if (email) {
    if (phoneDisplay) {
      phoneDisplay.textContent = email;
    }
    if (emailInput) {
      emailInput.value = email;
      emailInput.readOnly = true;
    }
    if (emailGroup) {
      emailGroup.style.display = 'block';
    }
    if (otpDesc) {
      otpDesc.innerHTML = 'Kami telah mengirim kode OTP ke:<br><strong>' + email + '</strong>';
    }
  }

  // Show test OTP in debug
  if (testOtp) {
    showMsg('Mode development — Kode OTP: ' + testOtp, 'success');
  }

  // OTP input navigation
  otpInputs.forEach((input, index) => {
    input.addEventListener('input', function(e) {
      e.target.value = e.target.value.replace(/[^0-9]/g, '');
      if (e.target.value) {
        input.classList.add('is-filled');
      } else {
        input.classList.remove('is-filled');
      }
      if (e.target.value.length === 1 && index < otpInputs.length - 1) {
        otpInputs[index + 1].focus();
      }
    });
    input.addEventListener('keydown', function(e) {
      if (e.key === 'Backspace' && !e.target.value && index > 0) {
        otpInputs[index - 1].value = '';
        otpInputs[index - 1].classList.remove('is-filled');
        otpInputs[index - 1].focus();
        e.preventDefault();
      }
    });
    input.addEventListener('paste', function(e) {
      const pasted = (e.clipboardData || window.clipboardData).getData('text').replace(/[^0-9]/g, '');
      if (!pasted) return;
      e.preventDefault();
      pasted.slice(0, otpInputs.length).split('').forEach((d, i) => {
        otpInputs[i].value = d;
        otpInputs[i].classList.add('is-filled');
      });
      const next = Math.min(pasted.length, otpInputs.length) - 1;
      otpInputs[next].focus();
    });
  });

  // Countdown timer
  function updateCountdown() {
    const mins = Math.floor(timeLeft / 60);
    const secs = timeLeft % 60;
    if (countdownEl) {
      countdownEl.textContent = mins.toString().padStart(2, '0') + ':' + secs.toString().padStart(2, '0');
    }
    if (timeLeft <= 0) {
      if (resendBtn) { resendBtn.disabled = false; resendBtn.setAttribute('aria-disabled', 'false'); }
    } else {
      timeLeft--;
      setTimeout(updateCountdown, 1000);
    }
  }
  updateCountdown();
  // Form submit - verify OTP via Django API
  otpForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    const otpValue = Array.from(otpInputs).map(inp => inp.value.trim()).join('');
    if (otpValue.length !== otpInputs.length) {
      showMsg('Isi semua angka OTP terlebih dahulu.', 'error');
      return;
    }
    if (!email) {
      showMsg('Email tidak ditemukan. Silakan daftar ulang.', 'error');
      return;
    }

    const submitBtn = otpForm.querySelector('button[type="submit"]');
    if (submitBtn) { submitBtn.disabled = true; submitBtn.innerHTML = '<span class="spinner"></span> Memverifikasi...'; }

    try {
      const data = await WarungioAPI.verifyOTP(email, otpValue, purpose);
      if (data.verified) {
        showMsg('Verifikasi berhasil! Mengarahkan...', 'success');
        
        // Auto login if tokens are present in the response
        if (data.access && data.user) {
          window.WarungioAuth.login(data.access, data.refresh, data.user);
          sessionStorage.removeItem('register_password');
        } else {
          // Attempt client-side auto login
          const savedPassword = sessionStorage.getItem('register_password');
          if (savedPassword) {
            try {
              const loginData = await WarungioAPI.login(email, savedPassword);
              window.WarungioAuth.login(loginData.access, loginData.refresh, loginData.user);
              sessionStorage.removeItem('register_password'); // clean up
            } catch (loginErr) {
              console.warn('Auto login failed:', loginErr);
            }
          }
        }

        setTimeout(() => {
          // If authenticated after auto-login, redirect directly to role dashboard
          if (window.WarungioAuth.isAuthenticated()) {
            var userRole = null;
            var userData = window.WarungioAuth.getUser();
            if (userData) userRole = userData.role;
            if (window.WarungioAuth && typeof window.WarungioAuth.getRoleDashboardUrl === 'function') {
              window.location.href = window.WarungioAuth.getRoleDashboardUrl(userRole);
            } else {
              if (userRole === 'seller') window.location.href = '/seller/dashboard/';
              else if (userRole === 'buyer') window.location.href = '/buyer/home/';
              else window.location.href = '/';
            }
          } else {
            // Use next_endpoint from backend response for role-appropriate redirect
            var loginBase = data.next_endpoint || '/auth/login/';
            var epBase = loginBase.split('?')[0];
            window.location.href = epBase + '?email=' + encodeURIComponent(email) + '&verified=1';
          }
        }, 1500);
      }
    } catch (err) {
      showMsg(err.message || 'Kode OTP salah atau sudah kadaluwarsa.', 'error');
      if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Verifikasi'; }
    }
  });

  // Resend OTP
  resendBtn.addEventListener('click', async function() {
    if (!email) {
      showMsg('Email tidak ditemukan.', 'error');
      return;
    }
    resendBtn.disabled = true;
    try {
      const data = await WarungioAPI.requestOTP(email, purpose);
      showMsg('Kode OTP telah dikirim ulang' + (data.otp_code ? ' — Kode: ' + data.otp_code : ''), 'success');
      timeLeft = 55;
      updateCountdown();
    } catch (err) {
      showMsg(err.message, 'error');
      resendBtn.disabled = false;
    }
  });
});
