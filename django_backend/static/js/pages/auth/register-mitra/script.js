/**
 * Partner Registration page — Warungio
 * Registers seller + creates store via Django REST API.
 * Cascading region dropdowns: Province → City → District → Village
 */
(function() {
  'use strict';

  const REGIONS_API = '/api/regions/';
  const CACHE_TTL = 30 * 60 * 1000; // 30 min cache for region data

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

  /** Map initialization — called either by &callback=initializeMap or manually on step 0 */
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

  /** Geocoding helper — reverse geocode coordinates to fill address + auto-select region */
  function _reverseGeocode(lat, lng, form) {
    if (typeof google === 'undefined' || !google.maps || !google.maps.Geocoder) return;
    var geocoder = new google.maps.Geocoder();
    geocoder.geocode({ location: { lat: lat, lng: lng } }, function(results, status) {
      if (status !== 'OK' || !results || !results[0]) {
        if (status === 'ZERO_RESULTS') {
          // No results for this location (e.g., middle of ocean) — not an error
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
      // Parse address components for Indonesian hierarchy:
      //   level_1 = Provinsi, level_2 = Kota/Kab, level_3 = Kecamatan,
      //   level_4 = Desa/Kelurahan, sublocality_level_1 = kelurahan (Jakarta)
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
      // Fill postal code from geocoding result
      if (form && form.elements.postalCode && postalCode) {
        form.elements.postalCode.value = postalCode;
      }
      // Auto-select in region dropdowns
      if (province && typeof autoSelectRegion === 'function') {
        autoSelectRegion(province, city, district);
      }
    });
  }

  // ── In-memory cache ──
  const cache = {};

  function cacheGet(key) {
    const entry = cache[key];
    if (!entry) return null;
    if (Date.now() - entry.ts > CACHE_TTL) { delete cache[key]; return null; }
    return entry.data;
  }

  function cacheSet(key, data) { cache[key] = { data, ts: Date.now() }; }

  // ── API helpers ──
  async function fetchJSON(url) {
    const cached = cacheGet(url);
    if (cached) return cached;
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
    const data = await resp.json();
    cacheSet(url, data);
    return data;
  }

  async function loadProvinces() {
    return fetchJSON(REGIONS_API + 'provinces/');
  }

  async function loadRegencies(provCode) {
    return fetchJSON(REGIONS_API + 'regencies/?province=' + provCode);
  }

  async function loadDistricts(regencyCode) {
    return fetchJSON(REGIONS_API + 'districts/?regency=' + regencyCode);
  }

  async function loadVillages(districtCode) {
    return fetchJSON(REGIONS_API + 'villages/?district=' + districtCode);
  }

  // ── Select helpers ──
  function populateSelect(select, items, nameKey, valueKey, placeholder) {
    const val = select.value;
    select.innerHTML = '<option value="">' + placeholder + '</option>';
    items.forEach(function(item) {
      var opt = document.createElement('option');
      // value = Kemendagri code (for hidden input sync), text = display name
      opt.value = item[valueKey || 'code'];
      opt.textContent = item[nameKey || 'display_name'] || item.name;
      select.appendChild(opt);
    });
    // Try to restore previous value
    if (val) { select.value = val; }
  }

  function disableSelect(select, placeholder) {
    select.disabled = true;
    select.innerHTML = '<option value="">' + placeholder + '</option>';
    select.value = '';
  }

  function clearDependent(startSelect) {
    var sel = startSelect;
    while (sel && sel.dataset.next) {
      var next = document.getElementById(sel.dataset.next);
      if (!next) break;
      var placeholder = next.dataset.placeholder || '— Pilih dulu —';
      disableSelect(next, placeholder);
      var hid = next.parentElement.querySelector('input[type="hidden"]');
      if (hid) hid.value = '';
      sel = next;
    }
  }

  // ── Load chain ──
  async function onProvinceChange(select) {
    var provCode = select.value;
    var hidden = select.parentElement.querySelector('input[type="hidden"]');
    if (hidden) { hidden.value = provCode; }

    var citySelect = document.getElementById('regionCity');
    clearDependent(select);
    if (!provCode) { disableSelect(citySelect, '— Pilih Provinsi dulu —'); return; }

    citySelect.disabled = true;
    citySelect.innerHTML = '<option value="">Memuat data...</option>';
    try {
      var cities = await loadRegencies(provCode);
      populateSelect(citySelect, cities, 'display_name', 'code', '— Pilih Kota/Kab —');
      citySelect.disabled = false;
    } catch (e) {
      disableSelect(citySelect, 'Gagal memuat data');
      console.error('Load regencies error:', e);
    }
  }

  async function onCityChange(select) {
    var cityCode = select.value;
    var hidden = select.parentElement.querySelector('input[type="hidden"]');
    if (hidden) { hidden.value = cityCode; }

    var distSelect = document.getElementById('regionDistrict');
    clearDependent(select);
    if (!cityCode) { disableSelect(distSelect, '— Pilih Kota dulu —'); return; }

    distSelect.disabled = true;
    distSelect.innerHTML = '<option value="">Memuat data...</option>';
    try {
      var districts = await loadDistricts(cityCode);
      populateSelect(distSelect, districts, 'display_name', 'code', '— Pilih Kecamatan —');
      distSelect.disabled = false;
    } catch (e) {
      disableSelect(distSelect, 'Gagal memuat data');
      console.error('Load districts error:', e);
    }
  }

  async function onDistrictChange(select) {
    var distCode = select.value;
    var hidden = select.parentElement.querySelector('input[type="hidden"]');
    if (hidden) { hidden.value = distCode; }

    var villageSelect = document.getElementById('regionVillage');
    clearDependent(select);
    if (!distCode) { disableSelect(villageSelect, '— Pilih Kecamatan dulu —'); return; }

    villageSelect.disabled = true;
    villageSelect.innerHTML = '<option value="">Memuat data...</option>';
    try {
      var villages = await loadVillages(distCode);
      populateSelect(villageSelect, villages, 'display_name', 'code', '— Pilih Desa/Kel —');
      villageSelect.disabled = false;
    } catch (e) {
      disableSelect(villageSelect, 'Gagal memuat data');
      console.error('Load villages error:', e);
    }
  }

  function onVillageChange(select) {
    var hidden = select.parentElement.querySelector('input[type="hidden"]');
    if (hidden) { hidden.value = select.value; }
  }

  // ── Try to auto-select region from address components (reverse geocode result) ──
  async function autoSelectRegion(provinceName, cityName, districtName) {
    // Load provinces and find match
    try {
      var provinces = await loadProvinces();
      var province = provinces.find(function(p) {
        return p.name.toUpperCase() === provinceName.toUpperCase() ||
               p.name.toUpperCase().includes(provinceName.toUpperCase());
      });
      if (!province) return;

      var provSelect = document.getElementById('regionProvince');
      provSelect.value = province.code;
      provSelect.dispatchEvent(new Event('change'));

      // Wait for cities to load, then select
      setTimeout(async function() {
        var citySelect = document.getElementById('regionCity');
        if (!cityName || citySelect.options.length < 2) return;

        var matchCity = null;
        for (var i = 0; i < citySelect.options.length; i++) {
          var opt = citySelect.options[i];
          var cleanName = opt.textContent.replace(/^(Kota |Kab\. )/, '');
          if (cleanName.toUpperCase() === cityName.toUpperCase() ||
              cityName.toUpperCase().includes(cleanName.toUpperCase())) {
            matchCity = opt.value;
            break;
          }
        }
        if (!matchCity) return;

        citySelect.value = matchCity;
        citySelect.dispatchEvent(new Event('change'));

        // Wait for districts to load
        setTimeout(function() {
          var distSelect = document.getElementById('regionDistrict');
          if (!districtName || distSelect.options.length < 2) return;

          for (var j = 0; j < distSelect.options.length; j++) {
            var o = distSelect.options[j];
            var cleanDist = o.textContent.replace(/^Kec\. /, '');
            if (cleanDist.toUpperCase() === districtName.toUpperCase() ||
                districtName.toUpperCase().includes(cleanDist.toUpperCase())) {
              distSelect.value = o.value;
              distSelect.dispatchEvent(new Event('change'));
              break;
            }
          }
        }, 300);
      }, 300);
    } catch (e) {
      console.error('Auto-select region error:', e);
    }
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

    // Map & marker
    // (partnerFormMap, partnerFormMarker, partnerFormMapInitialized defined at top level)

    // ── Wire up cascading region selects ──
    var provSelect = document.getElementById('regionProvince');
    var citySelect = document.getElementById('regionCity');
    var distSelect = document.getElementById('regionDistrict');
    var villageSelect = document.getElementById('regionVillage');

    if (provSelect) {
      // Set data-next chain for clearDependent
      provSelect.dataset.next = 'regionCity';
      citySelect.dataset.next = 'regionDistrict';
      distSelect.dataset.next = 'regionVillage';
      // Placeholders
      citySelect.dataset.placeholder = '— Pilih Provinsi dulu —';
      distSelect.dataset.placeholder = '— Pilih Kota dulu —';
      villageSelect.dataset.placeholder = '— Pilih Kecamatan dulu —';

      provSelect.addEventListener('change', function() { onProvinceChange(this); });
      citySelect.addEventListener('change', function() { onCityChange(this); });
      distSelect.addEventListener('change', function() { onDistrictChange(this); });
      villageSelect.addEventListener('change', function() { onVillageChange(this); });

      // Load provinces on page load
      (async function() {
        provSelect.disabled = true;
        provSelect.innerHTML = '<option value="">Memuat data provinsi...</option>';
        try {
          var provinces = await loadProvinces();
          populateSelect(provSelect, provinces, 'name', 'code', '— Pilih Provinsi —');
          provSelect.disabled = false;
        } catch (e) {
          provSelect.innerHTML = '<option value="">Gagal memuat provinsi</option>';
          console.error('Load provinces error:', e);
        }
      })();
    }

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

    // reverseGeocode, gm_authFailure, initializeMap — defined at top level of IIFE

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
          if (typeof window.initializeMap === 'function') {
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
      // Override region name fields with display text from selected options
      // (select value = code, but serializer expects name in city/province/district/village)
      ['province', 'city', 'district', 'village'].forEach(function(key) {
        var el = form.elements[key];
        if (el && el.tagName === 'SELECT' && el.selectedIndex >= 0) {
          payload[key] = el.options[el.selectedIndex].textContent || '';
        }
      });
      // Ensure region codes are included from hidden inputs
      ['province_code', 'city_code', 'district_code', 'village_code'].forEach(function(key) {
        var el = form.elements[key];
        if (el && el.value) payload[key] = el.value;
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
          // Step 1: Register user as seller
          var registerData = await WarungioAPI.register({
            full_name: data.ownerName,
            email: data.ownerEmail,
            phone: data.ownerPhone,
            password: data.ownerPassword || 'Toko12345!',
            password2: data.ownerPassword || 'Toko12345!',
            address: data.address,
            role: 'seller',
          });

          // Store JWT tokens
          if (registerData.access && registerData.refresh && window.WarungioAuth) {
            window.WarungioAuth.login(registerData.access, registerData.refresh, registerData.user);
          }

          // Step 2: Create store with full region data
          var storeData = await WarungioAPI.createStore({
            store_name: data.storeName,
            category: data.category,
            description: data.description,
            address: data.address,
            province: data.province,
            province_code: data.province_code || '',
            city: data.city,
            city_code: data.city_code || '',
            district: data.district,
            district_code: data.district_code || '',
            village: data.village,
            village_code: data.village_code || '',
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
          setTimeout(function() { window.location.href = '/seller/dashboard/'; }, 2000);
        } catch (err) {
          setMsg(err.message || 'Pendaftaran gagal. Silakan coba lagi.', 'error');
          if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = 'Daftar Sekarang'; }
        }
      });
    }

    // Restore draft
    restoreDraft();
  });
})();
