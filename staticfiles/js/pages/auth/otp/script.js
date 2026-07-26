/**
 * OTP Verification page - Warungio
 * Verifies OTP via Django REST API.
 * 
 * FLOW:
 * 1. Read email, purpose, role from URL params
 * 2. User enters 6-digit OTP code
 * 3. Submit to backend for verification
 * 4. Backend verifies, activates account, generates JWT tokens
 * 5. Frontend stores tokens (auto-login) and redirects based on role
 * 
 * Auto-login: Backend returns JWT access+refresh tokens after successful OTP.
 * No separate login step needed. The user is immediately authenticated.
 */
document.addEventListener('DOMContentLoaded', function() {
  const params = new URLSearchParams(window.location.search);
  const email = params.get('email') || '';
  const testOtp = params.get('otp') || '';
  const purpose = params.get('purpose') || 'registration';
  const role = params.get('role') || 'buyer';

  const otpInputs = document.querySelectorAll('.otp-input');
  const otpForm = document.getElementById('otpForm');
  const phoneDisplay = document.querySelector('.phone-number');
  const resendBtn = document.getElementById('resend-button');
  const countdownEl = document.getElementById('countdown');
  const messageEl = document.getElementById('otpMessage');

  // ── State ──
  // OTP_EXPIRY_MINUTES: total OTP lifetime (from backend response or settings)
  // RESEND_COOLDOWN: seconds before user can request a new OTP
  let otpExpirySeconds = (parseInt(params.get('expires_in')) || 15) * 60;  // Default 15 menit
  let resendCooldown = 55;  // Cooldown in seconds before resend allowed
  let _verifying = false;
  const OTP_LENGTH = 6;

  // ── Helper: show message ──
  function showMsg(text, type) {
    if (!messageEl) return;
    messageEl.textContent = text;
    messageEl.className = 'otp-message ' + type;
    messageEl.style.display = 'block';
    messageEl.classList.remove('fade-out');

    if (type === 'success') {
      setTimeout(() => {
        if (messageEl && messageEl.textContent === text) {
          messageEl.classList.add('fade-out');
          setTimeout(() => { messageEl.style.display = 'none'; }, 400);
        }
      }, 6000);
    }
  }

  // ── Handle email query param ──
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

  // ── Show test OTP in debug ──
  if (testOtp) {
    showMsg('Mode development — Kode OTP: ' + testOtp, 'success');
  }

  // ── Auto-focus first input ──
  if (otpInputs.length > 0) {
    otpInputs[0].focus();
  }

  // ── OTP input navigation ──
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

  // ── Timer UI: Show BOTH OTP expiry and resend cooldown ──
  // We need to find or create the display elements
  const otpExpiryEl = document.getElementById('otpExpiryTimer') || (function() {
    if (!countdownEl || !countdownEl.parentNode) return null;
    var el = document.createElement('div');
    el.id = 'otpExpiryTimer';
    el.className = 'timer-text otp-expiry';
    el.style.cssText = 'color:#059669;font-weight:700;font-size:0.95rem;margin-bottom:4px;';
    countdownEl.parentNode.insertBefore(el, countdownEl);
    return el;
  })();
  
  const resendCooldownEl = countdownEl;  // Reuse existing #countdown element
  
  // Update both timers every second
  function updateTimers() {
    // ── OTP Expiry Timer (counts down from e.g. 15 minutes) ──
    if (otpExpiryEl) {
      var expMins = Math.floor(otpExpirySeconds / 60);
      var expSecs = otpExpirySeconds % 60;
      var expiryStr = expMins.toString().padStart(2, '0') + ':' + expSecs.toString().padStart(2, '0');
      otpExpiryEl.innerHTML = '⏱ OTP berlaku selama <strong>' + expiryStr + '</strong>';
      
      // Visual warning: yellow at < 3 min, red at < 1 min
      if (otpExpirySeconds <= 60) {
        otpExpiryEl.style.color = '#ef4444';
      } else if (otpExpirySeconds <= 180) {
        otpExpiryEl.style.color = '#d97706';
      } else {
        otpExpiryEl.style.color = '#059669';
      }
    }
    
    // ── Resend Cooldown Timer (counts down from 55 seconds) ──
    if (resendCooldownEl) {
      var coolMins = Math.floor(resendCooldown / 60);
      var coolSecs = resendCooldown % 60;
      resendCooldownEl.textContent = coolMins.toString().padStart(2, '0') + ':' + coolSecs.toString().padStart(2, '0');
      
      if (resendCooldown <= 10) {
        resendCooldownEl.style.color = '#ef4444';
      } else {
        resendCooldownEl.style.color = '';
      }
    }
    
    // ── Decrement timers ──
    if (otpExpirySeconds > 0) {
      otpExpirySeconds--;
    } else {
      // OTP has expired — warn user
      if (otpExpiryEl) {
        otpExpiryEl.innerHTML = '⏱ <strong>OTP telah kadaluwarsa!</strong>';
        otpExpiryEl.style.color = '#ef4444';
      }
    }
    
    if (resendCooldown > 0) {
      resendCooldown--;
    } else {
      // Resend cooldown finished — enable resend button
      if (resendBtn) { 
        resendBtn.disabled = false; 
        resendBtn.setAttribute('aria-disabled', 'false'); 
      }
      if (resendCooldownEl) {
        resendCooldownEl.textContent = '00:00';
        resendCooldownEl.style.color = '#059669';
      }
    }
    
    // Continue timer loop (unless both are done and we're just keeping resend enabled)
    if (otpExpirySeconds > 0 || resendCooldown > 0) {
      setTimeout(updateTimers, 1000);
    }
  }
  updateTimers();

  // ── Form submit - verify OTP via Django API ──
  otpForm.addEventListener('submit', async function(e) {
    e.preventDefault();

    // Guard: prevent duplicate submissions
    if (_verifying) return;

    const otpValue = Array.from(otpInputs).map(inp => inp.value.trim()).join('');
    if (otpValue.length !== OTP_LENGTH) {
      showMsg('Isi semua ' + OTP_LENGTH + ' angka OTP terlebih dahulu.', 'error');
      return;
    }
    if (!email) {
      showMsg('Email tidak ditemukan. Silakan daftar ulang.', 'error');
      return;
    }

    _verifying = true;
    const submitBtn = otpForm.querySelector('button[type="submit"]');
    if (submitBtn) { submitBtn.disabled = true; submitBtn.innerHTML = '<span class="spinner"></span> Memverifikasi...'; }

    try {
      const data = await WarungioAPI.verifyOTP(email, otpValue, purpose);
      
      if (data.verified) {
        showMsg('Verifikasi berhasil! Mengarahkan ke dashboard...', 'success');
        
        // ── CRITICAL: Backend returns JWT tokens after successful OTP verification.
        // Store them immediately for auto-login. No need for separate login step.
        if (data.access && data.user) {
          window.WarungioAuth.login(data.access, data.refresh, data.user);
          sessionStorage.removeItem('register_password');
          sessionStorage.removeItem('warungio_partner_registration_data');
        }
        
        // ── Redirect using backend-provided redirect_url or role-based logic ──
        setTimeout(function() {
          // Priority 1: Backend-provided redirect_url (most reliable)
          if (data.redirect_url) {
            window.location.href = data.redirect_url;
            return;
          }
          
          // Priority 2: If authenticated, use role-based dashboard URL
          if (window.WarungioAuth && window.WarungioAuth.isAuthenticated()) {
            var userData = window.WarungioAuth.getUser();
            var userRole = userData ? userData.role : (role || 'buyer');
            
            if (window.WarungioAuth.getRoleDashboardUrl) {
              window.location.href = window.WarungioAuth.getRoleDashboardUrl(userRole);
            } else {
              // Hard fallback
              window.location.href = userRole === 'seller' ? '/seller/dashboard/' : '/buyer/home/';
            }
            return;
          }
          
          // Priority 3: Fallback to login page with success message
          window.location.href = '/auth/login/?email=' + encodeURIComponent(email) + '&verified=1';
        }, 1000);
      }
    } catch (err) {
      // ── Handle known OTP error codes ──
      if (err.message && err.message.indexOf('kadaluwarsa') !== -1) {
        showMsg('Kode OTP sudah kadaluwarsa. Silakan kirim ulang OTP.', 'error');
        // Enable resend button
        if (resendBtn) { resendBtn.disabled = false; }
      } else if (err.message && err.message.indexOf('terlalu banyak') !== -1) {
        showMsg('Terlalu banyak percobaan salah. Silakan kirim ulang OTP.', 'error');
        if (resendBtn) { resendBtn.disabled = false; }
      } else {
        showMsg(err.message || 'Kode OTP salah atau sudah kadaluwarsa.', 'error');
      }
      
      _verifying = false;
      if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Verifikasi'; }
      
      // Clear inputs for retry
      otpInputs.forEach(function(inp) {
        inp.value = '';
        inp.classList.remove('is-filled');
      });
      if (otpInputs.length > 0) {
        otpInputs[0].focus();
      }
    }
  });

  // ── Resend OTP ──
  resendBtn.addEventListener('click', async function() {
    if (!email) {
      showMsg('Email tidak ditemukan.', 'error');
      return;
    }
    
    resendBtn.disabled = true;
    resendBtn.innerHTML = '<span class="spinner"></span> Mengirim...';
    
    try {
      const data = await WarungioAPI.requestOTP(email, purpose);
      
      showMsg('Kode OTP telah dikirim ulang ke email Anda.' + 
        (data.otp_code ? ' (Debug: ' + data.otp_code + ')' : ''), 'success');
      
      // Reset BOTH timers: OTP expiry (15 min) + resend cooldown (55s)
      otpExpirySeconds = (parseInt(params.get('expires_in')) || 15) * 60;
      resendCooldown = 55;
      updateTimers();
      
      // Reset button text after a moment
      setTimeout(function() {
        if (resendBtn) {
          resendBtn.innerHTML = 'Kirim Ulang';
        }
      }, 1000);
      
    } catch (err) {
      showMsg(err.message || 'Gagal mengirim ulang OTP. Silakan coba lagi.', 'error');
      resendBtn.disabled = false;
      resendBtn.innerHTML = 'Kirim Ulang';
    }
  });
});
