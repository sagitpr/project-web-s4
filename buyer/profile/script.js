/**
 * Buyer Profile Page - Warungio
 * View/edit profile, change password, manage virtual profile details.
 */
(function () {
  'use strict';

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const loadingOverlay = $('#loadingOverlay');
  const profileAvatar = $('#profileAvatar');
  const avatarInput = $('#avatarInput');
  const avatarUploadBtn = $('#avatarUploadBtn');
  const avatarUploadTriggerBtn = $('#avatarUploadTriggerBtn');
  const profileForm = $('#profileForm');
  const profileMessage = $('#profileMessage');
  const saveProfileBtn = $('#saveProfileBtn');

  // Topbar
  const topbarUserName = $('#topbarUserName');
  const topbarUserAvatar = $('#topbarUserAvatar');

  // Password Modal
  const passwordModal = $('#passwordModal');
  const triggerChangePwdBtn = $('#triggerChangePwdBtn');
  const closePwdModalBtn = $('#closePwdModalBtn');
  const passwordForm = $('#passwordForm');
  const passwordMessage = $('#passwordMessage');
  const changePwdBtn = $('#changePwdBtn');
  const strengthBar = $('#strengthBar');
  const strengthText = $('#strengthText');

  let initialData = {};
  let userData = null;

  function showMsg(el, text, type = 'error') {
    if (!el) return;
    el.textContent = text;
    el.className = 'form-message ' + type;
    el.style.display = 'block';
    setTimeout(() => { if (el.textContent === text) el.style.display = 'none'; }, 6000);
  }

  function setLoading(btn, loading) {
    if (!btn) return;
    const text = btn.querySelector('.btn-text');
    const spinner = btn.querySelector('.btn-spinner');
    if (loading) {
      btn.disabled = true;
      if (text) text.textContent = 'Menyimpan...';
      if (spinner) spinner.classList.remove('hidden');
    } else {
      btn.disabled = false;
      if (text) text.textContent = btn.dataset.originalText || 'Simpan Perubahan';
      if (spinner) spinner.classList.add('hidden');
    }
  }

  if (saveProfileBtn) saveProfileBtn.dataset.originalText = 'Simpan Perubahan';
  if (changePwdBtn) changePwdBtn.dataset.originalText = 'Ubah Kata Sandi';

  if (window.WarungioAuth && window.WarungioAuth.requireVerified && window.WarungioAuth.requireVerified()) {
    return;
  }

  async function loadProfile() {
    try {
      loadingOverlay?.classList.remove('hidden');
      const user = window.WarungioAuth.getUser();
      if (user) {
        userData = user;
        renderProfile(user);
      }
      const data = await WarungioAPI.checkAuth();
      userData = data.user || data;
      renderProfile(userData);
      window.WarungioAuth.login(
        window.WarungioAuth.getAccessToken(),
        window.WarungioAuth.getRefreshToken(),
        userData
      );
    } catch (err) {
      console.warn('Load profile error:', err);
      if (userData) renderProfile(userData);
    } finally {
      loadingOverlay?.classList.add('hidden');
    }
  }

  function renderProfile(user) {
    initialData = {
      full_name: user.full_name || '',
      email: user.email || '',
      phone: user.phone || '',
      gender: user.gender || '',
      birth_date: user.birth_date || '',
      job: user.job || '',
      address: user.address || '',
      city: user.city || '',
      province: user.province || '',
      zip_code: user.zip_code || '',
      business_name: user.business_name || '',
      business_type: user.business_type || '',
      business_scale: user.business_scale || '',
      business_description: user.business_description || '',
    };

    // Render values
    if (topbarUserName) {
      topbarUserName.textContent = `Hai, ${user.full_name ? user.full_name.split(' ')[0] : 'User'}`;
    }
    
    const avatarSrc = user.profile_photo
      ? (user.profile_photo.startsWith('http') ? user.profile_photo : window.location.origin + user.profile_photo)
      : '/static/images/av-siti.png';
      
    if (profileAvatar) profileAvatar.src = avatarSrc;
    if (topbarUserAvatar) topbarUserAvatar.src = avatarSrc;

    // Fields
    const fields = {
      fullName: user.full_name || '',
      email: user.email || '',
      phone: user.phone || '',
      gender: user.gender || '',
      birthDate: user.birth_date || '',
      job: user.job || '',
      address: user.address || '',
      city: user.city || '',
      province: user.province || '',
      zipCode: user.zip_code || '',
      businessName: user.business_name || '',
      businessType: user.business_type || '',
      businessScale: user.business_scale || '',
      businessDescription: user.business_description || '',
    };

    Object.entries(fields).forEach(([id, val]) => {
      const el = document.getElementById(id);
      if (el) el.value = val;
    });
  }

  profileForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
      full_name: $('#fullName')?.value.trim(),
      phone: $('#phone')?.value.trim(),
      gender: $('#gender')?.value || '',
      birth_date: $('#birthDate')?.value || '',
      job: $('#job')?.value || '',
      address: $('#address')?.value.trim(),
      city: $('#city')?.value.trim() || '',
      province: $('#province')?.value || '',
      zip_code: $('#zipCode')?.value.trim() || '',
      business_name: $('#businessName')?.value.trim() || '',
      business_type: $('#businessType')?.value || '',
      business_scale: $('#businessScale')?.value || '',
      business_description: $('#businessDescription')?.value.trim() || '',
    };

    if (!data.full_name) {
      showMsg(profileMessage, 'Nama lengkap harus diisi.');
      return;
    }

    setLoading(saveProfileBtn, true);
    try {
      const result = await WarungioAPI.updateProfile(data);
      const user = window.WarungioAuth.getUser();
      Object.assign(user, result);
      window.WarungioAuth.login(window.WarungioAuth.getAccessToken(), window.WarungioAuth.getRefreshToken(), user);
      renderProfile(result);
      showMsg(profileMessage, 'Profil berhasil diperbarui!', 'success');
    } catch (err) {
      showMsg(profileMessage, err.message);
    } finally {
      setLoading(saveProfileBtn, false);
    }
  });

  // Password Modal Triggers
  triggerChangePwdBtn?.addEventListener('click', () => passwordModal?.classList.remove('hidden'));
  closePwdModalBtn?.addEventListener('click', () => passwordModal?.classList.add('hidden'));

  // Password Strength
  const newPwd = $('#newPassword');
  newPwd?.addEventListener('input', () => {
    const val = newPwd.value;
    let strength = 0;
    if (val.length >= 8) strength++;
    if (/[A-Z]/.test(val)) strength++;
    if (/[a-z]/.test(val)) strength++;
    if (/[0-9]/.test(val)) strength++;
    if (/[^A-Za-z0-9]/.test(val)) strength++;
    if (strengthBar) {
      const colors = ['', '#EF4444', '#F59E0B', '#EAB308', '#22C55E', '#16A34A'];
      strengthBar.style.width = (strength / 5) * 100 + '%';
      strengthBar.style.background = colors[strength] || '#EF4444';
    }
    if (strengthText) {
      const labels = ['', 'Lemah', 'Cukup', 'Sedang', 'Kuat', 'Sangat Kuat'];
      strengthText.textContent = labels[strength] || '';
    }
  });

  $$('.toggle-pwd').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = document.getElementById(btn.dataset.target);
      if (!target) return;
      const isPass = target.type === 'password';
      target.type = isPass ? 'text' : 'password';
      btn.querySelector('.eye-open')?.classList.toggle('hidden', !isPass);
      btn.querySelector('.eye-closed')?.classList.toggle('hidden', isPass);
    });
  });

  passwordForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const oldPwd = $('#oldPassword')?.value;
    const newPwdVal = $('#newPassword')?.value;
    const confirmPwd = $('#confirmPassword')?.value;

    if (!oldPwd || !newPwdVal || !confirmPwd) {
      showMsg(passwordMessage, 'Semua field harus diisi.');
      return;
    }
    if (newPwdVal !== confirmPwd) {
      showMsg(passwordMessage, 'Konfirmasi kata sandi tidak cocok.');
      return;
    }
    if (newPwdVal.length < 8) {
      showMsg(passwordMessage, 'Kata sandi minimal 8 karakter.');
      return;
    }

    setLoading(changePwdBtn, true);
    try {
      await WarungioAPI.changePassword({
        old_password: oldPwd,
        new_password: newPwdVal,
        new_password2: confirmPwd,
      });
      showMsg(passwordMessage, 'Kata sandi berhasil diubah!', 'success');
      passwordForm.reset();
      if (strengthBar) strengthBar.style.width = '0';
      if (strengthText) strengthText.textContent = 'Masukkan kata sandi baru';
      setTimeout(() => passwordModal?.classList.add('hidden'), 1500);
    } catch (err) {
      showMsg(passwordMessage, err.message);
    } finally {
      setLoading(changePwdBtn, false);
    }
  });

  // Avatar upload
  avatarUploadBtn?.addEventListener('click', () => avatarInput?.click());
  avatarUploadTriggerBtn?.addEventListener('click', () => avatarInput?.click());
  avatarInput?.addEventListener('change', async function () {
    const file = this.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      showMsg(profileMessage, 'File harus berupa gambar.');
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      showMsg(profileMessage, 'Ukuran maksimal 2MB.');
      return;
    }
    try {
      const data = await WarungioAPI.uploadProfilePhoto(file);
      const avatarSrc = window.location.origin + data.profile_photo + '?t=' + Date.now();
      if (profileAvatar) profileAvatar.src = avatarSrc;
      if (topbarUserAvatar) topbarUserAvatar.src = avatarSrc;

      const user = window.WarungioAuth.getUser();
      if (user && data.profile_photo) user.profile_photo = data.profile_photo;
      if (user) window.WarungioAuth.login(window.WarungioAuth.getAccessToken(), window.WarungioAuth.getRefreshToken(), user);
      showMsg(profileMessage, 'Foto profil berhasil diperbarui!', 'success');
    } catch (err) {
      showMsg(profileMessage, err.message);
    }
  });

  // Init
  loadProfile();
})();
