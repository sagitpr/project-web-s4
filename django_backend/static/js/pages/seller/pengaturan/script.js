/**
 * Warungio Seller — Pengaturan (Settings) Page
 * Handles store profile, account settings, and password change forms.
 */
(function () {
  'use strict';

  function $(id) { return document.getElementById(id); }

  /* ── Toast ── */
  function showToast(msg, type) {
    if (window.WarungioToast) {
      WarungioToast.show(msg, type || 'success');
      return;
    }
    var t = document.createElement('div');
    t.className = 'toast ' + (type || '');
    t.innerHTML = '<i class="fa-solid fa-check-circle"></i> ' + msg;
    t.style.display = 'flex';
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 3000);
  }

  /* ── Sidebar ── */
  function initSidebar() {
    var btn = $('hamburgerBtn');
    var sidebar = $('sidebarNav');
    var overlay = $('sidebarOverlay');
    if (!btn) return;
    btn.addEventListener('click', function () {
      sidebar.classList.toggle('open');
      overlay.classList.toggle('open');
    });
    if (overlay) overlay.addEventListener('click', function () {
      sidebar.classList.remove('open');
      overlay.classList.remove('open');
    });
    var closeBtn = $('sidebarAdsClose');
    if (closeBtn) closeBtn.addEventListener('click', function () {
      closeBtn.parentElement.style.display = 'none';
    });
  }

  /* ── Load Store & User Data ── */
  function loadSettings() {
    // Load store data
    if (window.WarungioAPI && typeof WarungioAPI.getMyStore === 'function') {
      WarungioAPI.getMyStore().then(function (res) {
        var store = res && res.data ? res.data : res;
        if (!store) return;
        if (store.store_name) $('shopName').textContent = store.store_name;
        if (store.id) $('shopId').textContent = 'ID Warung: WRG' + store.id;
        $('storeNameInput').value = store.store_name || '';
        $('storeDescInput').value = store.description || '';
        $('storeCityInput').value = store.city || '';
        $('storeProvinceInput').value = store.province || '';
        $('storeOpenTimeInput').value = store.open_time || '';
        $('storeCloseTimeInput').value = store.close_time || '';
        $('storeIsOpenInput').checked = store.is_open !== false;
        if (store.category) $('storeCategoryInput').value = store.category;
      }).catch(function () {
        console.warn('Failed to load store data');
      });
    }

    // Load user data
    if (window.WarungioAuth && window.WarungioAuth.getUser) {
      var user = window.WarungioAuth.getUser();
      if (user) {
        $('fullNameInput').value = user.full_name || '';
        $('emailInput').value = user.email || '';
        $('phoneInput').value = user.phone || '';
        $('addressInput').value = user.address || '';
        $('shopName').textContent = user.store_name || $('shopName').textContent;
      }
    }
  }

  /* ── Store Profile Form ── */
  function initStoreForm() {
    var form = $('storeProfileForm');
    if (!form) return;

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var btn = form.querySelector('button[type="submit"]');
      btn.disabled = true;
      btn.textContent = 'Menyimpan...';

      var data = {
        store_name: $('storeNameInput').value,
        description: $('storeDescInput').value,
        city: $('storeCityInput').value,
        province: $('storeProvinceInput').value,
        open_time: $('storeOpenTimeInput').value,
        close_time: $('storeCloseTimeInput').value,
        is_open: $('storeIsOpenInput').checked,
        category: $('storeCategoryInput').value,
      };

      var saveMsg = $('storeSaveMessage');

      if (window.WarungioAPI && typeof WarungioAPI.updateStore === 'function') {
        WarungioAPI.getMyStore().then(function (res) {
          var store = res && res.data ? res.data : res;
          var storeId = store.id;
          return WarungioAPI.updateStore(storeId, data);
        }).then(function () {
          if (saveMsg) { saveMsg.textContent = 'Toko berhasil diperbarui!'; saveMsg.className = 'save-message'; }
          showToast('Profil toko berhasil diperbarui!', 'success');
          if (data.store_name) $('shopName').textContent = data.store_name;
        }).catch(function (err) {
          if (saveMsg) { saveMsg.textContent = 'Gagal menyimpan: ' + (err.message || err); saveMsg.className = 'save-message error'; }
          showToast('Gagal menyimpan profil toko.', 'error');
        }).then(function () {
          btn.disabled = false;
          btn.textContent = 'Simpan Perubahan';
        });
      } else {
        setTimeout(function () {
          if (saveMsg) { saveMsg.textContent = 'Toko berhasil diperbarui!'; saveMsg.className = 'save-message'; }
          showToast('Profil toko berhasil diperbarui!', 'success');
          if (data.store_name) $('shopName').textContent = data.store_name;
          btn.disabled = false;
          btn.textContent = 'Simpan Perubahan';
        }, 500);
      }
    });
  }

  /* ── Account Form ── */
  function initAccountForm() {
    var form = $('accountForm');
    if (!form) return;

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var btn = form.querySelector('button[type="submit"]');
      btn.disabled = true;
      btn.textContent = 'Menyimpan...';

      var data = {
        full_name: $('fullNameInput').value,
        phone: $('phoneInput').value,
        address: $('addressInput').value,
      };

      var saveMsg = $('accountSaveMessage');

      if (window.WarungioAPI && typeof WarungioAPI.updateProfile === 'function') {
        WarungioAPI.updateProfile(data).then(function () {
          if (saveMsg) { saveMsg.textContent = 'Profil berhasil diperbarui!'; saveMsg.className = 'save-message'; }
          showToast('Profil berhasil diperbarui!', 'success');
        }).catch(function (err) {
          if (saveMsg) { saveMsg.textContent = 'Gagal menyimpan: ' + (err.message || err); saveMsg.className = 'save-message error'; }
          showToast('Gagal menyimpan profil.', 'error');
        }).then(function () {
          btn.disabled = false;
          btn.textContent = 'Simpan Profil';
        });
      } else {
        setTimeout(function () {
          if (saveMsg) { saveMsg.textContent = 'Profil berhasil diperbarui!'; saveMsg.className = 'save-message'; }
          showToast('Profil berhasil diperbarui!', 'success');
          btn.disabled = false;
          btn.textContent = 'Simpan Profil';
        }, 500);
      }
    });
  }

  /* ── Password Form ── */
  function initPasswordForm() {
    var form = $('passwordForm');
    if (!form) return;

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var btn = form.querySelector('button[type="submit"]');
      btn.disabled = true;
      btn.textContent = 'Memperbarui...';

      var oldPass = $('oldPasswordInput').value;
      var newPass = $('newPasswordInput').value;
      var confirmPass = $('confirmPasswordInput').value;
      var saveMsg = $('passwordSaveMessage');

      if (!oldPass || !newPass || !confirmPass) {
        if (saveMsg) { saveMsg.textContent = 'Semua field password harus diisi.'; saveMsg.className = 'save-message error'; }
        btn.disabled = false;
        btn.textContent = 'Perbarui Password';
        return;
      }

      if (newPass.length < 8) {
        if (saveMsg) { saveMsg.textContent = 'Password baru minimal 8 karakter.'; saveMsg.className = 'save-message error'; }
        btn.disabled = false;
        btn.textContent = 'Perbarui Password';
        return;
      }

      if (newPass !== confirmPass) {
        if (saveMsg) { saveMsg.textContent = 'Konfirmasi password tidak cocok.'; saveMsg.className = 'save-message error'; }
        btn.disabled = false;
        btn.textContent = 'Perbarui Password';
        return;
      }

      if (window.WarungioAPI && typeof WarungioAPI.changePassword === 'function') {
        WarungioAPI.changePassword({
          old_password: oldPass,
          new_password: newPass,
          new_password2: confirmPass,
        }).then(function () {
          if (saveMsg) { saveMsg.textContent = 'Password berhasil diperbarui!'; saveMsg.className = 'save-message'; }
          showToast('Password berhasil diperbarui!', 'success');
          form.reset();
        }).catch(function (err) {
          if (saveMsg) { saveMsg.textContent = 'Gagal: ' + (err.message || err); saveMsg.className = 'save-message error'; }
          showToast('Gagal memperbarui password.', 'error');
        }).then(function () {
          btn.disabled = false;
          btn.textContent = 'Perbarui Password';
        });
      } else {
        setTimeout(function () {
          if (saveMsg) { saveMsg.textContent = 'Password berhasil diperbarui!'; saveMsg.className = 'save-message'; }
          showToast('Password berhasil diperbarui!', 'success');
          form.reset();
          btn.disabled = false;
          btn.textContent = 'Perbarui Password';
        }, 500);
      }
    });
  }

  /* ── Init ── */
  document.addEventListener('DOMContentLoaded', function () {
    initSidebar();
    loadSettings();
    initStoreForm();
    initAccountForm();
    initPasswordForm();
  });
})();
