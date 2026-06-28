/**
 * Reset Password page - Warungio
 * Forgot/reset password via Django REST API with OTP.
 */
document.addEventListener('DOMContentLoaded', () => {
  const requestForm = document.getElementById('requestForm');
  const verifyForm = document.getElementById('verifyForm');
  const verifyIdentifier = document.getElementById('verifyIdentifier');
  const backButton = document.getElementById('backButton');
  const tabButtons = document.querySelectorAll('.tab-button');
  const inputIdentifier = document.getElementById('inputIdentifier');
  const otpInputs = document.querySelectorAll('.otp-row input');

  if (!requestForm || !verifyForm) return;

  function setStage(step) {
    requestForm.classList.toggle('hidden', step !== 'request');
    verifyForm.classList.toggle('hidden', step !== 'verify');
  }

  function setMessage(text, type) {
    const el = document.getElementById('formMessage');
    if (!el) return;
    el.textContent = text;
    el.className = 'form-message ' + (type || '');
    el.style.display = 'block';

    // Auto-dismiss success after 6s
    if (type === 'success') {
      setTimeout(() => {
        if (el && el.textContent === text) {
          el.classList.add('fade-out');
          setTimeout(() => { el.style.display = 'none'; }, 400);
        }
      }, 6000);
    }
  }

  // OTP input navigation
  otpInputs.forEach((input, index) => {
    input.addEventListener('input', () => {
      const v = input.value.replace(/[^0-9]/g, '');
      input.value = v;
      if (v && index < otpInputs.length - 1) otpInputs[index + 1].focus();
    });
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Backspace' && !input.value && index > 0) otpInputs[index - 1].focus();
    });
  });

  // Tab switching (email/phone)
  tabButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      tabButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const mode = btn.dataset.mode;
      inputIdentifier.placeholder = mode === 'email' ? 'Masukkan email Anda' : 'Masukkan nomor HP Anda';
      inputIdentifier.type = mode === 'email' ? 'email' : 'tel';
    });
  });

  // Step 1: Request OTP
  requestForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const identifier = inputIdentifier.value.trim();
    if (!identifier) { setMessage('Masukkan email atau nomor HP.', 'error'); return; }

    const btn = requestForm.querySelector('button[type="submit"]');
    btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Mengirim...';

    try {
      const data = await WarungioAPI.forgotPassword(identifier);
      verifyIdentifier.value = identifier;
      setMessage('Kode OTP telah dikirim' + (data.otp_code ? ' — Kode: ' + data.otp_code : ''), 'success');
      setStage('verify');
    } catch (err) {
      setMessage(err.message, 'error');
    } finally {
      btn.disabled = false; btn.innerHTML = 'Kirim Kode OTP';
    }
  });

  // Step 2: Verify OTP + Reset Password
  verifyForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const identifier = verifyIdentifier.value;
    const otpCode = Array.from(otpInputs).map(inp => inp.value).join('');
    const newPass = document.getElementById('newPassword').value;
    const confirmPass = document.getElementById('confirmPassword').value;

    if (otpCode.length !== 6) { setMessage('Isi semua digit OTP.', 'error'); return; }
    if (!newPass || newPass.length < 8) { setMessage('Kata sandi minimal 8 karakter.', 'error'); return; }
    if (newPass !== confirmPass) { setMessage('Konfirmasi kata sandi tidak cocok.', 'error'); return; }

    const btn = verifyForm.querySelector('button[type="submit"]');
    btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Menyimpan...';

    try {
      await WarungioAPI.resetPassword(identifier, otpCode, newPass);
      setMessage('Password berhasil direset! Mengarahkan ke login...', 'success');
      setTimeout(() => { window.location.href = '../auth/login/index.html'; }, 2000);
    } catch (err) {
      setMessage(err.message, 'error');
      btn.disabled = false; btn.innerHTML = 'Ubah Kata Sandi';
    }
  });

  // Back button
  backButton?.addEventListener('click', () => {
    setStage('request');
    history.replaceState(null, '', 'index.html');
  });
});
