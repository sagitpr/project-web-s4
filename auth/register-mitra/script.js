/**
 * Partner Registration page - Warungio
 * Registers seller + creates store via Django REST API.
 */
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('partnerForm');
  const panels = [...document.querySelectorAll('.step-panel')];
  const prevBtn = document.getElementById('prevBtn');
  const nextBtn = document.getElementById('nextBtn');
  const submitBtn = document.getElementById('submitBtn');
  const message = document.getElementById('formMessage');
  const description = form?.elements.description;
  const counter = document.querySelector('.counter');
  const storageKey = 'warungio_partner_registration_draft';
  let currentStep = 0;

  window.partnerFormMap = null;
  window.partnerFormMarker = null;
  window.partnerFormMapInitialized = false;

  const requiredByPanel = (panel) => [...panel.querySelectorAll('input, select, textarea')]
    .filter((f) => f.required && f.type !== 'hidden');

  const setMsg = (text, type) => {
    if (!message) return;
    message.textContent = text || '';
    message.className = 'form-message ' + (type || 'error');

    // Auto-dismiss success after 6s
    if (type === 'success') {
      setTimeout(() => {
        if (message && message.textContent === text) {
          message.classList.add('fade-out');
          setTimeout(() => { message.style.display = 'none'; }, 400);
        }
      }, 6000);
    }
  };

  const updateCounter = () => { if (counter) counter.textContent = (description?.value.length || 0) + '/300'; };

  // Geocoding helper
  function reverseGeocode(lat, lng) {
    if (typeof google === 'undefined' || !google.maps || !google.maps.Geocoder) return;
    const geocoder = new google.maps.Geocoder();
    geocoder.geocode({ location: { lat, lng } }, (results, status) => {
      if (status === 'OK' && results[0]) {
        if (form && form.elements.address) {
          form.elements.address.value = results[0].formatted_address;
          form.elements.address.dispatchEvent(new Event('input'));
        }
      }
    });
  }

  // Google Maps Auth Failure callback handler
  window.gm_authFailure = function() {
    const mapStatus = document.getElementById('mapStatus');
    const mapWidget = document.getElementById('mapWidget');
    if (mapStatus) {
      mapStatus.innerHTML = '<span style="color:#ef4444; font-weight:600;">Gagal memuat Google Peta (API Key tidak valid). Koordinat default digunakan.</span>';
    }
    if (mapWidget) {
      mapWidget.style.background = '#fee2e2';
      mapWidget.style.border = '1px solid #fca5a5';
      mapWidget.innerHTML = '<div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; color:#ef4444; padding:20px; text-align:center;"><i class="fa-solid fa-triangle-exclamation" style="font-size:32px; margin-bottom:10px;"></i><b>Layanan Peta Tidak Tersedia</b><span style="font-size:12px; margin-top:4px;">Google Maps API Key tidak valid. Hubungi administrator.</span></div>';
    }
  };

  // Map initialization
  window.initializeMap = function() {
    if (window.partnerFormMapInitialized) return;
    const mapEl = document.getElementById('googleMap');
    if (!mapEl) return;
    const defaultLoc = { lat: -6.2088, lng: 106.8456 };
    try {
      window.partnerFormMap = new google.maps.Map(mapEl, {
        zoom: 13, center: defaultLoc, mapTypeControl: true,
        streetViewControl: false, fullscreenControl: true,
      });
      window.partnerFormMarker = new google.maps.Marker({
        position: defaultLoc, map: window.partnerFormMap, draggable: true,
        title: 'Lokasi Toko Anda',
      });
      if (form) {
        form.elements.latitude.value = defaultLoc.lat;
        form.elements.longitude.value = defaultLoc.lng;
      }
      window.partnerFormMarker.addListener('dragend', () => {
        const pos = window.partnerFormMarker.getPosition();
        const lat = pos.lat();
        const lng = pos.lng();
        if (form) {
          form.elements.latitude.value = lat.toFixed(6);
          form.elements.longitude.value = lng.toFixed(6);
        }
        reverseGeocode(lat, lng);
      });
      window.partnerFormMap.addListener('click', (event) => {
        const lat = event.latLng.lat();
        const lng = event.latLng.lng();
        window.partnerFormMarker.setPosition({ lat, lng });
        if (form) {
          form.elements.latitude.value = lat.toFixed(6);
          form.elements.longitude.value = lng.toFixed(6);
        }
        reverseGeocode(lat, lng);
      });
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition((position) => {
          const ul = { lat: position.coords.latitude, lng: position.coords.longitude };
          window.partnerFormMap.setCenter(ul);
          window.partnerFormMarker.setPosition(ul);
          if (form) {
            form.elements.latitude.value = ul.lat.toFixed(6);
            form.elements.longitude.value = ul.lng.toFixed(6);
          }
          reverseGeocode(ul.lat, ul.lng);
        }, () => {});
      }
      window.partnerFormMapInitialized = true;
    } catch (e) {
      console.error('Maps error:', e);
      window.gm_authFailure();
    }
  };

  const setStep = (index) => {
    currentStep = Math.max(0, Math.min(index, panels.length - 1));
    panels.forEach((panel, i) => panel.classList.toggle('active', i === currentStep));
    if (prevBtn) prevBtn.classList.toggle('hidden', currentStep === 0 || currentStep === panels.length - 1);
    if (nextBtn) nextBtn.classList.toggle('hidden', currentStep >= 3);
    if (submitBtn) submitBtn.classList.toggle('hidden', currentStep !== 3);
    if (currentStep === 0 && !window.partnerFormMapInitialized) {
      setTimeout(() => { if (typeof window.initializeMap === 'function') window.initializeMap(); }, 300);
    }
    document.querySelector('.intro')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setMsg('');
  };

  const validatePanel = (panel) => {
    let valid = true;
    requiredByPanel(panel).forEach((field) => {
      const fv = field.checkValidity();
      field.closest('.field')?.classList.toggle('invalid', !fv);
      if (!fv) valid = false;
    });
    if (panel.dataset.panel === '2' && form && form.querySelectorAll('input[name="deliveryServices"]:checked').length === 0) {
      valid = false; setMsg('Pilih minimal satu layanan pengiriman.');
    }
    if (panel.dataset.panel === '0' && form && (!form.elements.latitude.value || !form.elements.longitude.value)) {
      valid = false; setMsg('Pilih lokasi toko pada peta terlebih dahulu.');
    }
    if (panel.dataset.panel === '3' && form && form.elements.accountNumber.value !== form.elements.accountConfirm.value) {
      valid = false; form.elements.accountConfirm.classList.add('invalid');
      setMsg('Nomor rekening dan konfirmasi belum sama.');
    }
    if (!valid && message && !message.textContent) setMsg('Lengkapi data wajib sebelum melanjutkan.');
    return valid;
  };

  const collectFormData = () => {
    const fd = new FormData(form);
    const payload = {};
    fd.forEach((value, key) => {
      if (key === 'deliveryServices') { payload[key] = payload[key] || []; payload[key].push(value); return; }
      payload[key] = value;
    });
    return payload;
  };

  const saveDraft = () => localStorage.setItem(storageKey, JSON.stringify(collectFormData()));

  const restoreDraft = () => {
    const raw = localStorage.getItem(storageKey);
    if (!raw) return;
    try {
      const data = JSON.parse(raw);
      Object.entries(data).forEach(([key, value]) => {
        if (key === 'deliveryServices' && Array.isArray(value)) {
          value.forEach((item) => {
            const cb = form.querySelector('input[name="' + key + '"][value="' + item + '"]');
            if (cb) cb.checked = true;
          }); return;
        }
        const field = form.elements[key];
        if (!field || key === 'submittedAt') return;
        if (field.type === 'radio') return;
        field.value = value;
      });
      updateCounter();
    } catch (e) { localStorage.removeItem(storageKey); }
  };

  if (description) { description.addEventListener('input', () => { updateCounter(); saveDraft(); }); }
  form?.addEventListener('input', saveDraft);
  form?.addEventListener('change', saveDraft);

  prevBtn?.addEventListener('click', () => setStep(currentStep - 1));
  nextBtn?.addEventListener('click', () => { if (validatePanel(panels[currentStep])) setStep(currentStep + 1); });

  // Submit - register seller + create store
  form?.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!validatePanel(panels[currentStep])) return;

    const data = collectFormData();
    if (submitBtn) { submitBtn.disabled = true; submitBtn.innerHTML = '<span class="spinner"></span> Mendaftarkan...'; }
    setMsg('Mendaftarkan mitra toko...', 'success');

    try {
      // Validate passwords match
      if (data.ownerPassword !== data.ownerPassword2) {
        setMsg('Kata sandi dan konfirmasi tidak sama.', 'error');
        if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = 'Daftar Sekarang'; }
        return;
      }
      if (!data.ownerPassword || data.ownerPassword.length < 8) {
        setMsg('Kata sandi minimal 8 karakter.', 'error');
        if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = 'Daftar Sekarang'; }
        return;
      }

      // Step 1: Register user as seller
      const registerData = await WarungioAPI.register({
        full_name: data.ownerName,
        email: data.ownerEmail,
        phone: data.ownerPhone,
        password: data.ownerPassword,
        password2: data.ownerPassword,
        address: data.address,
        role: 'seller',
      });

      // Store JWT tokens
      if (registerData.access && registerData.refresh) {
        window.WarungioAuth.login(registerData.access, registerData.refresh, registerData.user);
      }

      // Step 2: Create store
      const storeData = await WarungioAPI.createStore({
        store_name: data.storeName,
        category: data.category,
        description: data.description,
        address: data.address,
        city: data.city,
        province: data.province,
        postal_code: data.postalCode,
        latitude: parseFloat(data.latitude),
        longitude: parseFloat(data.longitude),
        phone: data.storePhone,
        email: data.storeEmail,
        open_time: data.openTime,
        close_time: data.closeTime,
        minimum_order: parseInt(data.minimumOrder) || 0,
        delivery_services: data.deliveryServices || [],
        service_area: data.serviceArea,
        bank_name: data.bankName,
        account_number: data.accountNumber,
        account_holder: data.accountHolder,
      });

      setMsg('Pendaftaran mitra berhasil! Mengarahkan ke dashboard...', 'success');
      localStorage.removeItem(storageKey);
      setTimeout(() => {
        window.location.href = '../seller/dashboard/index.html';
      }, 2000);
    } catch (err) {
      setMsg(err.message || 'Pendaftaran gagal. Silakan coba lagi.', 'error');
      if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = 'Daftar Sekarang'; }
    }
  });

  // Restore draft on load
  restoreDraft();
});
