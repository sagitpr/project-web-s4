/**
 * Partner Registration page — Warungio
 * Registers seller + creates store via Django REST API.
 * Text inputs for region fields (no longer cascading dropdowns).
 */
(function() {
  'use strict';

  // ══════════════════════════════════════════════════════════════════════════
  //  GOOGLE MAPS — defined at script parse time (before DOMContentLoaded)
  //  to avoid callback race condition with Maps API &callback=initializeMap
  // ══════════════════════════════════════════════════════════════════════════

  window.partnerFormMap = null;
  window.partnerFormMarker = null;
  window.partnerFormMapInitialized = false;
  var _mapsLoadAttempted = false;

  /**
   * Dynamically load the Google Maps JavaScript API.
   * Called on demand when the map section is first shown (step 0).
   */
  window.loadMapsAPI = function() {
    if (_mapsLoadAttempted) return;
    _mapsLoadAttempted = true;

    // Read API key from the meta tag or data attribute set by the template
    var apiKey = (document.querySelector('meta[name="google-maps-api-key"]') || {}).content;
    if (!apiKey) {
      var meta = document.getElementById('gmaps-api-key');
      if (meta) apiKey = meta.getAttribute('data-key');
    }
    if (!apiKey) {
      console.warn('Google Maps API key not found — map unavailable');
      _showMapFallback('Konfigurasi Google Maps tidak ditemukan.');
      return;
    }

    var script = document.createElement('script');
    script.src = 'https://maps.googleapis.com/maps/api/js?key=' + encodeURIComponent(apiKey) + '&callback=initializeMap';
    script.async = true;
    script.defer = true;
    script.onerror = function() {
      console.error('Google Maps API script failed to load');
      _showMapFallback('Gagal memuat Google Maps. Periksa koneksi internet.');
    };
    document.head.appendChild(script);
  };

  /** Show fallback UI when map can't load — overlay on top of googleMap div, don't destroy it */
  function _showMapFallback(msg) {
    var mapWidget = document.getElementById('mapWidget');
    var mapStatus = document.getElementById('mapStatus');
    var mapEl = document.getElementById('googleMap');
    if (mapEl && !document.getElementById('mapFallbackOverlay')) {
      var overlay = document.createElement('div');
      overlay.id = 'mapFallbackOverlay';
      overlay.style.cssText = 'position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; background:#fef3c7; color:#92400e; padding:20px; text-align:center; z-index:10; border-radius:8px;';
      overlay.innerHTML = '<i class="fa-solid fa-map" style="font-size:32px; margin-bottom:10px;"></i><b>Peta Tidak Tersedia</b><span style="font-size:12px; margin-top:4px;">' + (msg || '') + '</span><span style="font-size:11px; margin-top:8px; color:#6b7280;">Koordinat default akan digunakan. Anda dapat mengubahnya nanti di pengaturan toko.</span>';
      if (mapWidget) {
        mapWidget.style.position = 'relative';
        mapWidget.appendChild(overlay);
        mapWidget.style.background = '#fef3c7';
        mapWidget.style.border = '1px solid #fcd34d';
      }
    }
    if (mapStatus) mapStatus.textContent = 'Peta tidak dapat dimuat. Koordinat default (Jakarta Pusat) digunakan.';
  }

  /** Google Maps auth failure callback — must be set at global scope */
  window.gm_authFailure = function() {
    var mapStatus = document.getElementById('mapStatus');
    var mapWidget = document.getElementById('mapWidget');
    if (mapStatus) {
      mapStatus.innerHTML = '<span style="color:#ef4444; font-weight:600;">Gagal memuat Google Peta (API Key tidak valid). Koordinat default digunakan.</span>';
    }
    if (mapWidget) {
      mapWidget.style.background = '#fee2e2';
      mapWidget.style.border = '1px solid #fca5a5';
      mapWidget.innerHTML = '<div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; color:#ef4444; padding:20px; text-align:center;"><i class="fa-solid fa-triangle-exclamation" style="font-size:32px; margin-bottom:10px;"></i><b>Layanan Peta Tidak Tersedia</b><span style="font-size:12px; margin-top:4px;">Google Maps API Key tidak valid. Hubungi administrator.</span></div>';
    }
  };

  /** Map initialization — called by &callback=initializeMap or manually */
  window.initializeMap = function() {
    if (window.partnerFormMapInitialized) return;
    var mapEl = document.getElementById('googleMap');
    if (!mapEl) return;
    var defaultLoc = { lat: -6.2088, lng: 106.8456 };
    try {
      window.partnerFormMap = new google.maps.Map(mapEl, {
        zoom: 13, center: defaultLoc, mapTypeControl: true,
        streetViewControl: false, fullscreenControl: true,
      });
      window.partnerFormMarker = new google.maps.Marker({
        position: defaultLoc, map: window.partnerFormMap, draggable: true,
        title: 'Lokasi Toko Anda',
      });
      var form = document.getElementById('partnerForm');
      if (form) {
        if (form.elements.latitude && !form.elements.latitude.value) {
          form.elements.latitude.value = defaultLoc.lat;
        }
        if (form.elements.longitude && !form.elements.longitude.value) {
          form.elements.longitude.value = defaultLoc.lng;
        }
      }
      window.partnerFormMarker.addListener('dragend', function() {
        var pos = window.partnerFormMarker.getPosition();
        var lat = pos.lat();
        var lng = pos.lng();
        if (form) {
          form.elements.latitude.value = lat.toFixed(6);
          form.elements.longitude.value = lng.toFixed(6);
        }
        _reverseGeocode(lat, lng, form);
      });
      window.partnerFormMap.addListener('click', function(event) {
        var lat = event.latLng.lat();
        var lng = event.latLng.lng();
        window.partnerFormMarker.setPosition({ lat: lat, lng: lng });
        if (form) {
          form.elements.latitude.value = lat.toFixed(6);
          form.elements.longitude.value = lng.toFixed(6);
        }
        _reverseGeocode(lat, lng, form);
      });
      // Update status after successful initialization
      var mapStatus = document.getElementById('mapStatus');
      if (mapStatus) {
        mapStatus.textContent = 'Peta siap. Klik pada peta atau seret marker untuk menentukan koordinat toko.';
        mapStatus.style.color = '#166534';
      }

      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function(position) {
          var ul = { lat: position.coords.latitude, lng: position.coords.longitude };
          window.partnerFormMap.setCenter(ul);
          window.partnerFormMarker.setPosition(ul);
          if (form) {
            form.elements.latitude.value = ul.lat.toFixed(6);
            form.elements.longitude.value = ul.lng.toFixed(6);
          }
          _reverseGeocode(ul.lat, ul.lng, form);
          if (mapStatus) {
            mapStatus.textContent = 'Lokasi terdeteksi: ' + ul.lat.toFixed(4) + ', ' + ul.lng.toFixed(4) + '. Seret marker untuk menyesuaikan.';
          }
        }, function() {
          // Geolocation failed or denied — map still works with default center
          if (mapStatus) {
            mapStatus.textContent = 'Lokasi tidak terdeteksi. Klik pada peta untuk menentukan lokasi toko.';
          }
        }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 });
      }
      window.partnerFormMapInitialized = true;
    } catch (e) {
      console.error('Maps error:', e);
      if (typeof window.gm_authFailure === 'function') window.gm_authFailure();
    }
  };

  /** Geocoding helper — reverse geocode coordinates to fill address + region text inputs */
  function _reverseGeocode(lat, lng, form) {
    if (typeof google === 'undefined' || !google.maps || !google.maps.Geocoder) return;
    var geocoder = new google.maps.Geocoder();
    geocoder.geocode({ location: { lat: lat, lng: lng } }, function(results, status) {
      if (status !== 'OK' || !results || !results[0]) {
        if (status === 'ZERO_RESULTS') {
          return;
        }
        if (status === 'OVER_QUERY_LIMIT' || status === 'REQUEST_DENIED') {
          console.error('Geocoder error:', status);
        }
        return;
      }
      var addr = results[0].formatted_address;
      if (form && form.elements.address) {
        form.elements.address.value = addr;
        form.elements.address.dispatchEvent(new Event('input'));
      }
      // Parse address components for Indonesian hierarchy and fill text inputs directly
      var components = results[0].address_components || [];
      var province = '', city = '', district = '', village = '', postalCode = '';
      components.forEach(function(c) {
        var types = c.types || [];
        if (types.indexOf('administrative_area_level_1') !== -1) province = c.long_name;
        if (types.indexOf('administrative_area_level_2') !== -1) city = c.long_name;
        if (types.indexOf('administrative_area_level_3') !== -1) district = c.long_name;
        if (types.indexOf('administrative_area_level_4') !== -1 && !village) village = c.long_name;
        if (types.indexOf('sublocality_level_1') !== -1 && !district) district = c.long_name;
        if (types.indexOf('sublocality_level_2') !== -1 && !village) village = c.long_name;
        if (types.indexOf('postal_code') !== -1) postalCode = c.long_name;
      });
      // Fill text inputs directly
      if (form) {
        if (form.elements.province && province) {
          form.elements.province.value = province;
          form.elements.province.dispatchEvent(new Event('input'));
        }
        if (form.elements.city && city) {
          form.elements.city.value = city;
          form.elements.city.dispatchEvent(new Event('input'));
        }
        if (form.elements.district && district) {
          form.elements.district.value = district;
          form.elements.district.dispatchEvent(new Event('input'));
        }
        if (form.elements.village && village) {
          form.elements.village.value = village;
          form.elements.village.dispatchEvent(new Event('input'));
        }
        if (form.elements.postalCode && postalCode) {
          form.elements.postalCode.value = postalCode;
        }
      }
    });
  }

  // ── DOM Ready ──
  document.addEventListener('DOMContentLoaded', function() {
    var form = document.getElementById('partnerForm');
    var panels = [].slice.call(document.querySelectorAll('.step-panel'));
    var prevBtn = document.getElementById('prevBtn');
    var nextBtn = document.getElementById('nextBtn');
    var submitBtn = document.getElementById('submitBtn');
    var message = document.getElementById('formMessage');
    var description = form && form.elements.description;
    var counter = document.querySelector('.counter');
    var storageKey = 'warungio_partner_registration_draft';
    var currentStep = 0;

    // ── Helpers ──
    var requiredByPanel = function(panel) {
      return [].slice.call(panel.querySelectorAll('input, select, textarea'))
        .filter(function(f) { return f.required && f.type !== 'hidden'; });
    };

    var setMsg = function(text, type) {
      if (!message) return;
      message.textContent = text || '';
      message.className = 'form-message ' + (type || 'error');
      if (type === 'success') {
        setTimeout(function() {
          if (message && message.textContent === text) {
            message.classList.add('fade-out');
            setTimeout(function() { message.style.display = 'none'; }, 400);
          }
        }, 6000);
      }
    };

    var updateCounter = function() {
      if (counter) counter.textContent = (description ? description.value.length : 0) + '/300';
    };

    // ── Step navigation ──
    var setStep = function(index) {
      currentStep = Math.max(0, Math.min(index, panels.length - 1));
      panels.forEach(function(panel, i) {
        panel.classList.toggle('active', i === currentStep);
      });
      if (prevBtn) prevBtn.classList.toggle('hidden', currentStep === 0 || currentStep === panels.length - 1);
      if (nextBtn) nextBtn.classList.toggle('hidden', currentStep >= 3);
      if (submitBtn) submitBtn.classList.toggle('hidden', currentStep !== 3);
      if (currentStep === 0 && !window.partnerFormMapInitialized) {
        setTimeout(function() {
          if (window.google && window.google.maps && typeof window.initializeMap === 'function') {
            window.initializeMap();
          } else if (typeof window.loadMapsAPI === 'function') {
            window.loadMapsAPI();
          }
        }, 300);
      }
      var intro = document.querySelector('.intro');
      if (intro) intro.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setMsg('');
    };

    var validatePanel = function(panel) {
      var valid = true;
      requiredByPanel(panel).forEach(function(field) {
        var fv = field.checkValidity();
        var parent = field.closest('.field');
        if (parent) parent.classList.toggle('invalid', !fv);
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

    // ── Collect form data ──
    var collectFormData = function() {
      var fd = new FormData(form);
      var payload = {};
      fd.forEach(function(value, key) {
        if (key === 'deliveryServices') {
          payload[key] = payload[key] || [];
          payload[key].push(value);
          return;
        }
        payload[key] = value;
      });
      return payload;
    };

    var saveDraft = function() {
      try { localStorage.setItem(storageKey, JSON.stringify(collectFormData())); } catch(e) {}
    };

    var restoreDraft = function() {
      try {
        var raw = localStorage.getItem(storageKey);
        if (!raw) return;
        var data = JSON.parse(raw);
        Object.entries(data).forEach(function(_ref) {
          var key = _ref[0], value = _ref[1];
          if (key === 'deliveryServices' && Array.isArray(value)) {
            value.forEach(function(item) {
              var cb = form.querySelector('input[name="' + key + '"][value="' + item + '"]');
              if (cb) cb.checked = true;
            });
            return;
          }
          var field = form.elements[key];
          if (!field || key === 'submittedAt') return;
          if (field.type === 'radio') return;
          field.value = value;
        });
        updateCounter();
      } catch(e) { localStorage.removeItem(storageKey); }
    };

    // ── Event listeners ──
    if (description) {
      description.addEventListener('input', function() { updateCounter(); saveDraft(); });
    }
    if (form) {
      form.addEventListener('input', saveDraft);
      form.addEventListener('change', saveDraft);
    }

    if (prevBtn) prevBtn.addEventListener('click', function() { setStep(currentStep - 1); });
    if (nextBtn) {
      nextBtn.addEventListener('click', function() {
        if (validatePanel(panels[currentStep])) setStep(currentStep + 1);
      });
    }

    // ── Submit ──
    if (form) {
      form.addEventListener('submit', async function(event) {
        event.preventDefault();
        if (!validatePanel(panels[currentStep])) return;

        var data = collectFormData();
        if (submitBtn) { submitBtn.disabled = true; submitBtn.innerHTML = '<span class="spinner"></span> Mendaftarkan...'; }
        setMsg('Mendaftarkan mitra toko...', 'success');

        try {
          // Validate passwords match
          if (data.ownerPassword !== data.ownerPassword2) {
            setMsg('Kata sandi dan konfirmasi tidak sama.', 'error');
            if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = 'Kirim Pendaftaran'; }
            return;
          }
          if (!data.ownerPassword || data.ownerPassword.length < 8) {
            setMsg('Kata sandi minimal 8 karakter.', 'error');
            if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = 'Kirim Pendaftaran'; }
            return;
          }

          // Step 1: Register user as seller
          var registerData = await WarungioAPI.register({
            full_name: data.ownerName,
            email: data.ownerEmail,
            phone: data.ownerPhone,
            password: data.ownerPassword,
            password2: data.ownerPassword,
            address: data.address,
            role: 'seller',
          });

          // Store JWT tokens
          if (registerData.access && registerData.refresh && window.WarungioAuth) {
            window.WarungioAuth.login(registerData.access, registerData.refresh, registerData.user);
          }

          // Step 2: Create store with region text data
          var storeData = await WarungioAPI.createStore({
            store_name: data.storeName,
            category: data.category,
            description: data.description,
            address: data.address,
            province: data.province,
            city: data.city,
            district: data.district,
            village: data.village,
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

          setMsg('Pendaftaran mitra berhasil!', 'success');
          localStorage.removeItem(storageKey);
          setTimeout(function() { window.location.href = '/auth/otp/?email=' + encodeURIComponent(data.ownerEmail) + '&purpose=registration'; }, 2000);
        } catch (err) {
          setMsg(err.message || 'Pendaftaran gagal. Silakan coba lagi.', 'error');
          if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = 'Daftar Sekarang'; }
        }
      });
    }

    // Initialize map on first load (step 0 is visible by default via CSS class)
    setTimeout(function() {
      if (window.google && window.google.maps && typeof window.initializeMap === 'function') {
        window.initializeMap();
      } else if (typeof window.loadMapsAPI === 'function') {
        window.loadMapsAPI();
      }
    }, 500);

    // Restore draft
    restoreDraft();
  });
})();
