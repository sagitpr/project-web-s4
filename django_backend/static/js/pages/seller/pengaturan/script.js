/**
 * Warungio Seller — Pengaturan (Settings) Page
 * Handles store profile, account settings, password change forms,
 * and store logo/banner image upload with cropping.
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

  /* ── Store Image Data ── */
  var storeData = {
    id: null,
    store_logo_url: null,
    store_banner_url: null,
    store_name: '',
  };

  /* ── Cropper State ── */
  var cropModalOverlay = $('cropModalOverlay');
  var cropImage = $('cropImage');
  var cropModalTitle = $('cropModalTitle');
  var currentCropType = null; // 'logo' or 'banner'
  var currentCropFile = null;
  var cropper = null;

  /* ── Image Upload Handlers ── */
  function initImageUpload() {
    // Logo
    initUploadButton('logoFileInput', 'btnUploadLogo', 'btnReplaceLogo', 'btnRemoveLogo', 'logoImg', 'logoUploadStatus', 'logo');
    // Banner
    initUploadButton('bannerFileInput', 'btnUploadBanner', 'btnReplaceBanner', 'btnRemoveBanner', 'bannerImg', 'bannerUploadStatus', 'banner');
  }

  function initUploadButton(fileInputId, uploadBtnId, replaceBtnId, removeBtnId, imgId, statusId, type) {
    var fileInput = $(fileInputId);
    var uploadBtn = $(uploadBtnId);
    var replaceBtn = $(replaceBtnId);
    var removeBtn = $(removeBtnId);
    var img = $(imgId);
    var status = $(statusId);

    if (!fileInput || !uploadBtn) return;

    // Upload button → file picker
    uploadBtn.addEventListener('click', function () { fileInput.click(); });
    if (replaceBtn) {
      replaceBtn.addEventListener('click', function () { fileInput.click(); });
    }

    // File selected → open crop modal
    fileInput.addEventListener('change', function () {
      var file = fileInput.files && fileInput.files[0];
      if (!file) return;

      // Validate size (5MB)
      if (file.size > 5 * 1024 * 1024) {
        showToast('Ukuran file maksimal 5MB.', 'error');
        fileInput.value = '';
        return;
      }

      // Validate type
      var allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
      if (allowedTypes.indexOf(file.type) === -1) {
        showToast('Format file tidak didukung. Gunakan JPG, PNG, atau WEBP.', 'error');
        fileInput.value = '';
        return;
      }

      openCropModal(file, type);
    });

    // Remove button
    if (removeBtn) {
      removeBtn.addEventListener('click', function () {
        if (!confirm('Hapus ' + (type === 'logo' ? 'logo' : 'sampul') + ' toko?')) return;
        removeBtn.disabled = true;
        status.style.display = 'flex';
        status.innerHTML = '<span class="spinner"></span> Menghapus...';

        var apiMethod = type === 'logo' ? window.WarungioAPI.removeStoreLogo : window.WarungioAPI.removeStoreBanner;
        if (apiMethod) {
          apiMethod().then(function () {
            img.src = type === 'logo' ? '/static/images/store-placeholder.png' : '';
            img.style.display = type === 'banner' ? 'none' : 'block';
            if (type === 'banner' && $('coverPlaceholder')) $('coverPlaceholder').style.display = 'flex';
            uploadBtn.style.display = 'inline-flex';
            replaceBtn.style.display = 'none';
            removeBtn.style.display = 'none';
            status.style.display = 'none';
            // Hide header logo
            if (type === 'logo' && $('headerStoreLogo')) $('headerStoreLogo').style.display = 'none';
            showToast((type === 'logo' ? 'Logo' : 'Sampul') + ' toko berhasil dihapus.', 'success');
          }).catch(function (err) {
            showToast('Gagal menghapus: ' + (err.message || 'Terjadi kesalahan'), 'error');
            status.style.display = 'none';
          }).then(function () {
            removeBtn.disabled = false;
          });
        } else {
          status.style.display = 'none';
          removeBtn.disabled = false;
          showToast('Fitur belum tersedia.', 'error');
        }
      });
    }
  }

  /* ── Crop Modal ── */
  function openCropModal(file, type) {
    currentCropType = type;
    currentCropFile = file;

    cropModalTitle.textContent = 'Potong ' + (type === 'logo' ? 'Logo Toko' : 'Sampul Toko');

    // Read file as data URL
    var reader = new FileReader();
    reader.onload = function (e) {
      cropImage.src = e.target.result;
      cropImage.onload = function () {
        cropModalOverlay.classList.add('open');

        // Destroy previous cropper
        if (cropper) { cropper.destroy(); cropper = null; }

        // Aspect ratio for logo (1:1 square) or banner (3:1 wide)
        var aspectRatio = type === 'logo' ? 1 : 3;

        cropper = new Cropper(cropImage, {
          aspectRatio: aspectRatio,
          viewMode: 1,
          dragMode: 'move',
          autoCropArea: 1,
          cropBoxMovable: true,
          cropBoxResizable: true,
          toggleDragModeOnDblclick: false,
          background: false,
          minCropBoxWidth: type === 'logo' ? 100 : 400,
          minCropBoxHeight: type === 'logo' ? 100 : 100,
        });
      };
    };
    reader.readAsDataURL(file);
  }

  function closeCropModal() {
    cropModalOverlay.classList.remove('open');
    if (cropper) { cropper.destroy(); cropper = null; }
    cropImage.src = '';
    currentCropType = null;
    currentCropFile = null;
    // Reset file inputs
    if ($('logoFileInput')) $('logoFileInput').value = '';
    if ($('bannerFileInput')) $('bannerFileInput').value = '';
  }

  function confirmCrop() {
    if (!cropper || !currentCropType) return;

    var type = currentCropType;
    var confirmBtn = $('cropModalConfirm');
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<span class="spinner" style="width:16px;height:16px;border-width:2px;"></span> Mengunggah...';

    // Get cropped canvas
    var canvas = cropper.getCroppedCanvas({
      width: type === 'logo' ? 400 : 1200,
      height: type === 'logo' ? 400 : 400,
      imageSmoothingEnabled: true,
      imageSmoothingQuality: 'high',
    });

    // Convert canvas to blob
    canvas.toBlob(function (blob) {
      if (!blob) {
        showToast('Gagal memproses gambar.', 'error');
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = '<i class="fa-solid fa-crop"></i> Potong & Unggah';
        return;
      }

      // Create a File from the blob
      var originalName = currentCropFile ? currentCropFile.name : 'cropped.jpg';
      var croppedFile = new File([blob], originalName, { type: 'image/jpeg', lastModified: Date.now() });

      var apiMethod = type === 'logo' ? window.WarungioAPI.uploadStoreLogo : window.WarungioAPI.uploadStoreBanner;

      if (apiMethod) {
        apiMethod(croppedFile).then(function (res) {
          closeCropModal();
          showToast((type === 'logo' ? 'Logo' : 'Sampul') + ' toko berhasil diperbarui!', 'success');

          // Update the preview
          var img = type === 'logo' ? $('logoImg') : $('bannerImg');
          if (img) {
            // Add cache-busting query param
            var ts = new Date().getTime();
            var url = URL.createObjectURL(blob);
            img.src = url;
            img.style.display = 'block';

            // Also reload from server after a brief delay
            setTimeout(function () {
              // Try to get updated URL from store data
              if (window.WarungioAPI && typeof WarungioAPI.getMyStore === 'function') {
                WarungioAPI.getMyStore().then(function (res) {
                  var store = res && res.data ? res.data : res;
                  if (store) {
                    var logoUrl = store.store_logo_url || store.store_logo;
                    var bannerUrl = store.store_banner_url || store.store_banner;
                    if (type === 'logo' && logoUrl) {
                      img.src = logoUrl + '?t=' + ts;
                      var headerLogo = $('headerStoreLogo');
                      if (headerLogo) { headerLogo.src = logoUrl + '?t=' + ts; headerLogo.style.display = 'block'; }
                    } else if (type === 'banner' && bannerUrl) {
                      img.src = bannerUrl + '?t=' + ts;
                    }
                  }
                }).catch(function () {});
              }
            }, 500);
          }

          // Toggle button visibility
          var uploadBtn = type === 'logo' ? $('btnUploadLogo') : $('btnUploadBanner');
          var replaceBtn = type === 'logo' ? $('btnReplaceLogo') : $('btnReplaceBanner');
          var removeBtn = type === 'logo' ? $('btnRemoveLogo') : $('btnRemoveBanner');
          if (uploadBtn) uploadBtn.style.display = 'none';
          if (replaceBtn) replaceBtn.style.display = 'inline-flex';
          if (removeBtn) removeBtn.style.display = 'inline-flex';
          if (type === 'banner' && $('coverPlaceholder')) $('coverPlaceholder').style.display = 'none';
          
          // Reload store data to refresh header logo
          if (type === 'logo' && window.WarungioAPI && typeof WarungioAPI.getMyStore === 'function') {
            WarungioAPI.getMyStore().then(function (res) {
              var s = res && res.data ? res.data : res;
              if (s) {
                var ul = s.store_logo_url || s.store_logo;
                if (ul && $('headerStoreLogo')) {
                  $('headerStoreLogo').src = ul + '?t=' + new Date().getTime();
                  $('headerStoreLogo').style.display = 'block';
                }
              }
            }).catch(function() {});
          }

          confirmBtn.disabled = false;
          confirmBtn.innerHTML = '<i class="fa-solid fa-crop"></i> Potong & Unggah';
        }).catch(function (err) {
          showToast('Gagal mengunggah: ' + (err.message || 'Terjadi kesalahan'), 'error');
          confirmBtn.disabled = false;
          confirmBtn.innerHTML = '<i class="fa-solid fa-crop"></i> Potong & Unggah';
        });
      } else {
        closeCropModal();
        showToast('Fitur belum tersedia.', 'error');
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = '<i class="fa-solid fa-crop"></i> Potong & Unggah';
      }
    }, 'image/jpeg', 0.92);
  }

  /* ── Load Store & User Data ── */
  function loadSettings() {
    // Load store data
    if (window.WarungioAPI && typeof WarungioAPI.getMyStore === 'function') {
      WarungioAPI.getMyStore().then(function (res) {
        var store = res && res.data ? res.data : res;
        if (!store) return;
        storeData = store;

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

        // Load store logo
        var logoUrl = store.store_logo_url || store.store_logo;
        var logoImg = $('logoImg');
        if (logoUrl && logoImg) {
          logoImg.src = logoUrl;
          $('btnUploadLogo').style.display = 'none';
          $('btnReplaceLogo').style.display = 'inline-flex';
          $('btnRemoveLogo').style.display = 'inline-flex';
          // Show in header
          var headerLogo = $('headerStoreLogo');
          if (headerLogo) { headerLogo.src = logoUrl; headerLogo.style.display = 'block'; }
        }

        // Load store banner
        var bannerUrl = store.store_banner_url || store.store_banner;
        var bannerImg = $('bannerImg');
        if (bannerUrl && bannerImg) {
          bannerImg.src = bannerUrl;
          bannerImg.style.display = 'block';
          if ($('coverPlaceholder')) $('coverPlaceholder').style.display = 'none';
          $('btnUploadBanner').style.display = 'none';
          $('btnReplaceBanner').style.display = 'inline-flex';
          $('btnRemoveBanner').style.display = 'inline-flex';
        }
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

  /* ── Crop Modal Event Handlers ── */
  function initCropModal() {
    if ($('cropModalClose')) {
      $('cropModalClose').addEventListener('click', closeCropModal);
    }
    if ($('cropModalCancel')) {
      $('cropModalCancel').addEventListener('click', closeCropModal);
    }
    if ($('cropModalConfirm')) {
      $('cropModalConfirm').addEventListener('click', confirmCrop);
    }
    // Close on overlay click
    if (cropModalOverlay) {
      cropModalOverlay.addEventListener('click', function (e) {
        if (e.target === cropModalOverlay) closeCropModal();
      });
    }
    // Close on Escape key
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && cropModalOverlay && cropModalOverlay.classList.contains('open')) {
        closeCropModal();
      }
    });
  }

  /* ── Init ── */
  document.addEventListener('DOMContentLoaded', function () {
    initSidebar();
    initImageUpload();
    initCropModal();
    loadSettings();
    initStoreForm();
    initAccountForm();
    initPasswordForm();
  });
})();
