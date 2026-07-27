/* ── Smart AI Scan — Warungio Seller ── */
(function () {
  'use strict';

  let stream = null;
  let scanMode = 'auto';
  let detectedItems = [];
  let scanHistory = [];
  let isScanning = false;
  let scanTimer = null;
  let sessionId = null;

  const DOM = {
    video: document.getElementById('videoFeed'),
    canvas: document.getElementById('overlayCanvas'),
    placeholder: document.getElementById('cameraPlaceholder'),
    indicator: document.getElementById('scanningIndicator'),
    result: document.getElementById('scanResult'),
    resultBody: document.getElementById('scanResultBody'),
    confidence: document.getElementById('scanConfidence'),
    btnStart: document.getElementById('btnStartCamera'),
    btnCapture: document.getElementById('btnCapture'),
    btnStop: document.getElementById('btnStopCamera'),
    btnApply: document.getElementById('btnApplyScan'),
    btnDiscard: document.getElementById('btnDiscardScan'),
    btnClear: document.getElementById('btnClearDetections'),
    upload: document.getElementById('imageUpload'),
    detectedList: document.getElementById('detectedProductsList'),
    multiGrid: document.getElementById('multiDetectGrid'),
    historyTable: document.getElementById('scanHistoryTable'),
    historyEmpty: document.getElementById('scanHistoryEmpty'),
    statTotal: document.querySelector('#statTotalScans .stat-value'),
    statDetected: document.querySelector('#statProductsDetected .stat-value'),
    statBarcode: document.querySelector('#statBarcodeFound .stat-value'),
    statExpiry: document.querySelector('#statExpiryRead .stat-value'),
    multiCount: document.getElementById('multiDetectCount'),
    modeBtns: document.querySelectorAll('.scan-mode-selector .btn-sm'),
  };

  let lastScanResult = null;

  // ── Auth Guard ──
  if (!WarungioAuth || !WarungioAuth.isAuthenticated()) {
    window.location.href = '/auth/login/';
    return;
  }

  // ── Initialize ──
  document.addEventListener('DOMContentLoaded', function () {
    WarungioAuthUI?.init({ syncBalance: false, syncCart: false });
    loadProfile();
    initEventListeners();
    loadScanHistory();
  });

  function loadProfile() {
    const user = WarungioAuth.getUser();
    if (user) {
      document.getElementById('shopName').textContent = user.store_name || 'Toko Saya';
      document.getElementById('shopId').textContent = 'ID: ' + (user.store_id || '--');
      document.getElementById('profileName').textContent = user.full_name || user.email || 'Seller';
      if (user.avatar) document.getElementById('profileAvatar').src = user.avatar;
    }
  }

  function initEventListeners() {
    DOM.btnStart.addEventListener('click', startCamera);
    DOM.btnCapture.addEventListener('click', captureFrame);
    DOM.btnStop.addEventListener('click', stopCamera);
    DOM.btnApply.addEventListener('click', applyScanResult);
    DOM.btnDiscard.addEventListener('click', discardScanResult);
    DOM.btnClear.addEventListener('click', clearDetections);
    DOM.upload.addEventListener('change', handleImageUpload);
    document.getElementById('btnRefreshHistory')?.addEventListener('click', loadScanHistory);

    DOM.modeBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        DOM.modeBtns.forEach(function (b) { b.classList.remove('active'); b.className = 'btn-sm btn-secondary'; });
        btn.className = 'btn-sm btn-primary active';
        scanMode = btn.dataset.mode;
        showToast('Mode scan: ' + btn.textContent.trim(), 'info');
      });
    });
  }

  // ── Camera ──
  function startCamera() {
    if (stream) { showToast('Kamera sudah aktif', 'info'); return; }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showToast('Browser tidak mendukung kamera. Gunakan Chrome atau Firefox.', 'error');
      return;
    }
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } } })
      .then(function (s) {
        stream = s;
        DOM.video.srcObject = s;
        DOM.video.style.display = 'block';
        DOM.placeholder.style.display = 'none';
        DOM.btnStart.style.display = 'none';
        DOM.btnCapture.style.display = 'inline-flex';
        DOM.btnStop.style.display = 'inline-flex';
        DOM.indicator.style.display = 'flex';
        showToast('Kamera aktif. Arahkan ke produk.', 'success');
        startAutoScan();
      })
      .catch(function (err) {
        console.error('Camera error:', err);
        showToast('Gagal mengakses kamera: ' + err.message, 'error');
      });
  }

  function stopCamera() {
    if (stream) {
      stream.getTracks().forEach(function (t) { t.stop(); });
      stream = null;
    }
    DOM.video.style.display = 'none';
    DOM.placeholder.style.display = 'flex';
    DOM.btnStart.style.display = 'inline-flex';
    DOM.btnCapture.style.display = 'none';
    DOM.btnStop.style.display = 'none';
    DOM.indicator.style.display = 'none';
    clearInterval(scanTimer);
    isScanning = false;
    showToast('Kamera dihentikan', 'info');
  }

  // ── Auto Scan ──
  function startAutoScan() {
    isScanning = true;
    scanTimer = setInterval(function () {
      if (!isScanning || !stream) return;
      if (scanMode === 'auto' || scanMode === 'barcode') scanBarcode();
      if (scanMode === 'auto' || scanMode === 'ocr') scanOCR();
    }, 2000);
  }

  // ── Capture Frame ──
  function captureFrame() {
    if (!stream) { showToast('Aktifkan kamera terlebih dahulu', 'error'); return; }
    DOM.canvas.width = DOM.video.videoWidth;
    DOM.canvas.height = DOM.video.videoHeight;
    var ctx = DOM.canvas.getContext('2d');
    ctx.drawImage(DOM.video, 0, 0);
    var imageData = DOM.canvas.toDataURL('image/jpeg', 0.9);
    processImage(imageData);
  }

  function handleImageUpload(e) {
    var file = e.target.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function (ev) {
      processImage(ev.target.result);
    };
    reader.readAsDataURL(file);
  }

  // ── Process Image (AI Scan) — Client-side + Backend AI Pipeline ──
  function processImage(imageData) {
    showToast('Memproses gambar...', 'info');
    DOM.indicator.style.display = 'flex';

    var clientResults = [
      scanBarcodeFromImage(imageData),
      scanOCRFromImage(imageData),
      detectObjects(imageData)
    ];

    // Also call backend AI pipeline in parallel
    var backendPromise = callBackendAI(imageData);

    Promise.all(clientResults.concat([backendPromise]))
      .then(function (results) {
        DOM.indicator.style.display = 'none';
        var barcodeResult = results[0];
        var ocrResult = results[1];
        var detectionResult = results[2];
        var backendResult = results[3];

        var combined = {
          barcode: barcodeResult?.code || backendResult?.barcode || '',
          productName: ocrResult?.productName || detectionResult?.label || backendResult?.product_name || '',
          brand: ocrResult?.brand || backendResult?.brand || '',
          expiryDate: ocrResult?.expiryDate || backendResult?.expiry_date || '',
          batchNumber: ocrResult?.batchNumber || backendResult?.batch_number || '',
          category: backendResult?.category || '',
          unit: backendResult?.unit || 'pcs',
          confidence: Math.max(
            barcodeResult?.confidence || 0,
            ocrResult?.confidence || 0,
            detectionResult?.confidence || 0,
            backendResult?.confidence || 0
          ),
          method: backendResult?.detection_method || (barcodeResult?.code ? 'barcode' : (ocrResult?.productName ? 'ocr' : 'vision')),
          freshness_score: backendResult?.freshness_score,
          freshness_status: backendResult?.freshness_status,
          packaging_type: backendResult?.packaging_type,
          manufacturer: backendResult?.manufacturer || '',
          auto_recognized: backendResult?.auto_recognized || false,
          master_product_id: backendResult?.master_product_id || null,
          multi_object_count: backendResult?.multi_object_count || 1,
          imageData: imageData,
        };

        lastScanResult = combined;
        showScanResult(combined);
        addDetectedItem(combined);
        updateStats(combined);

        // If backend auto-recognized, show special badge
        if (combined.auto_recognized) {
          showToast('Produk dikenali otomatis oleh AI: ' + combined.productName, 'success');
        }
      }).catch(function (err) {
        DOM.indicator.style.display = 'none';
        console.error('Scan error:', err);
        showToast('Gagal memproses gambar: ' + err.message, 'error');
      });
  }

  // ── Call Backend AI Pipeline Endpoints ──
  function callBackendAI(imageData) {
    return new Promise(function (resolve) {
      // Send image to backend /api/inventory/ai-recognize/
      var payload = JSON.stringify({ image: imageData });
      var csrf = getCSRFToken();

      fetch('/api/inventory/ai-recognize/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: payload,
      })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) {
        resolve(data);
      })
      .catch(function (err) {
        console.warn('Backend AI pipeline unavailable, using client-side only:', err.message);
        resolve(null);
      });
    });
  }

  function getCSRFToken() {
    var name = 'csrftoken';
    var match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? match[2] : '';
  }

  // ── Barcode Scan (QuaggaJS) ──
  function scanBarcode() {
    if (!stream || !DOM.video.videoWidth) return;
    DOM.canvas.width = DOM.video.videoWidth;
    DOM.canvas.height = DOM.video.videoHeight;
    var ctx = DOM.canvas.getContext('2d');
    ctx.drawImage(DOM.video, 0, 0);

    scanBarcodeFromImage(DOM.canvas.toDataURL('image/jpeg', 0.8)).then(function (result) {
      if (result && result.code) {
        showToast('Barcode terdeteksi: ' + result.code, 'success');
        playScanSound();
      }
    }).catch(function () {});
  }

  function scanBarcodeFromImage(imageData) {
    return new Promise(function (resolve) {
      if (typeof Quagga === 'undefined') {
        resolve(null);
        return;
      }
      var img = new Image();
      img.onload = function () {
        var c = document.createElement('canvas');
        c.width = img.width; c.height = img.height;
        var ctx = c.getContext('2d');
        ctx.drawImage(img, 0, 0);
        var data = ctx.getImageData(0, 0, img.width, img.height);

        Quagga.decodeSingle({
          src: imageData,
          numOfWorkers: 1,
          inputStream: { size: 800 },
          decoder: { readers: ['ean_reader', 'ean_8_reader', 'upc_reader', 'code_128_reader'] },
          locate: true,
        }, function (result) {
          if (result && result.codeResult) {
            resolve({ code: result.codeResult.code, confidence: result.codeResult.decodedCodes?.[0]?.confidence || 0.9, format: result.codeResult.format });
          } else {
            resolve(null);
          }
        });
      };
      img.src = imageData;
    });
  }

  // ── OCR Scan (Tesseract.js) ──
  function scanOCR() {
    if (!stream || !DOM.video.videoWidth) return;
    DOM.canvas.width = DOM.video.videoWidth;
    DOM.canvas.height = DOM.video.videoHeight;
    var ctx = DOM.canvas.getContext('2d');
    ctx.drawImage(DOM.video, 0, 0);
    scanOCRFromImage(DOM.canvas.toDataURL('image/jpeg', 0.8)).then(function (result) {
      if (result && result.productName) {
        showToast('OCR: ' + result.productName, 'success');
      }
    }).catch(function () {});
  }

  function scanOCRFromImage(imageData) {
    return Tesseract.recognize(imageData, 'ind', { logger: function () {} })
      .then(function (res) {
        var text = res.data.text;
        if (!text || text.length < 5) return null;

        var productName = '';
        var brand = '';
        var expiryDate = '';
        var batchNumber = '';
        var lines = text.split('\n').filter(function (l) { return l.trim().length > 3; });

        // Extract expiry date patterns
        var expMatch = text.match(/(?:EXP|exp|Exp|ED|ed|Kadaluwarsa|kedaluwarsa|expiry|Expiry)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})/);
        if (expMatch) expiryDate = expMatch[1];

        var expMatch2 = text.match(/(\d{2}[\/\-]\d{2}[\/\-]\d{4})/);
        if (!expiryDate && expMatch2) expiryDate = expMatch2[1];

        // Extract batch number
        var batchMatch = text.match(/(?:Batch|batch|Lot|lot|BATCH|LOT)[:\s]*([A-Za-z0-9\-_]{3,15})/);
        if (batchMatch) batchNumber = batchMatch[1];

        // Guess product name (first meaningful line)
        var stopWords = ['exp', 'expiry', 'batch', 'lot', 'bpom', 'pom', 'kg', 'g', 'ml', 'l', 'gr', 'netto', 'berat', 'produksi', 'diproduksi', 'tanggal', 'no', 'nomor'];
        for (var i = 0; i < lines.length; i++) {
          var line = lines[i].trim();
          var firstWord = line.split(/\s+/)[0]?.toLowerCase() || '';
          if (line.length > 5 && stopWords.indexOf(firstWord) === -1 && !/^\d/.test(firstWord)) {
            if (!brand) brand = line.substring(0, 100);
            else if (!productName) { productName = line.substring(0, 200); break; }
          }
        }

        return {
          text: text,
          productName: productName || '',
          brand: brand || '',
          expiryDate: expiryDate || '',
          batchNumber: batchNumber || '',
          confidence: res.data.confidence / 100,
        };
      })
      .catch(function () { return null; });
  }

  // ── Object Detection ──
  function detectObjects(imageData) {
    return new Promise(function (resolve) {
      // Check for MobileNet/TensorFlow.js availability
      if (typeof mobilenet === 'undefined' || typeof tf === 'undefined') {
        resolve({ label: '', confidence: 0 });
        return;
      }
      var img = new Image();
      img.onload = function () {
        mobilenet.load().then(function (model) {
          return model.classify(img);
        }).then(function (predictions) {
          if (predictions && predictions.length > 0) {
            resolve({ label: predictions[0].className, confidence: predictions[0].probability });
          } else {
            resolve({ label: '', confidence: 0 });
          }
        }).catch(function () { resolve({ label: '', confidence: 0 }); });
      };
      img.src = imageData;
    });
  }

  // ── Show Scan Result ──
  function showScanResult(result) {
    DOM.result.style.display = 'block';
    DOM.resultBody.innerHTML = '';
    var confidenceClass = result.confidence > 0.8 ? 'high' : (result.confidence > 0.5 ? 'medium' : 'low');
    DOM.confidence.textContent = (result.confidence * 100).toFixed(0) + '%';
    DOM.confidence.className = 'scan-confidence ' + confidenceClass;

    var fields = [
      { label: 'Metode', value: result.method === 'barcode' ? 'Barcode' : (result.method === 'ocr' ? 'OCR Text' : 'AI Vision') },
    ];
    if (result.barcode) fields.push({ label: 'Barcode', value: result.barcode });
    if (result.productName) fields.push({ label: 'Nama Produk', value: result.productName.substring(0, 100) });
    if (result.brand) fields.push({ label: 'Merek', value: result.brand });
    if (result.expiryDate) fields.push({ label: 'EXP Date', value: result.expiryDate });
    if (result.batchNumber) fields.push({ label: 'Batch', value: result.batchNumber });

    fields.forEach(function (f) {
      var row = document.createElement('div');
      row.className = 'field-row';
      row.innerHTML = '<span class="field-label">' + f.label + '</span><span class="field-value">' + escapeHtml(f.value) + '</span>';
      DOM.resultBody.appendChild(row);
    });
  }

  function applyScanResult() {
    if (!lastScanResult) return;
    showToast('Data scan siap digunakan', 'success');
    // Data will be used when seller adds product
    DOM.result.style.display = 'none';
  }

  function discardScanResult() {
    lastScanResult = null;
    DOM.result.style.display = 'none';
    showToast('Hasil scan dibatalkan', 'info');
  }

  // ── Detected Items ──
  function addDetectedItem(result) {
    var existing = detectedItems.find(function (item) {
      return item.productName === result.productName && item.barcode === result.barcode;
    });
    if (existing) {
      existing.count = (existing.count || 1) + 1;
    } else {
      detectedItems.push({
        id: Date.now(),
        productName: result.productName || 'Produk Tidak Diketahui',
        barcode: result.barcode || '',
        brand: result.brand || '',
        expiryDate: result.expiryDate || '',
        method: result.method,
        confidence: result.confidence,
        count: 1,
        imageData: result.imageData,
      });
    }

    // Check for multi-object detection
    if (result.confidence > 0.3) {
      addMultiDetectItem(result);
    }

    DOM.btnClear.style.display = detectedItems.length > 0 ? 'inline-flex' : 'none';
    renderDetectedItems();
  }

  function renderDetectedItems() {
    if (detectedItems.length === 0) {
      DOM.detectedList.innerHTML = '<div class="empty-state"><i class="fa-solid fa-camera"></i><h4>Belum Ada Deteksi</h4><p>Arahkan kamera ke produk untuk memulai scan AI.</p></div>';
      DOM.multiCount.textContent = '0 item';
      return;
    }
    var html = '';
    detectedItems.forEach(function (item) {
      var iconClass = item.method === 'barcode' ? 'barcode' : (item.method === 'ocr' ? 'ocr' : 'vision');
      var badgeClass = item.confidence > 0.7 ? 'confirmed' : 'pending';
      var badgeText = item.confidence > 0.7 ? 'Terverifikasi' : 'Pending';
      var name = item.productName || 'Produk Tidak Diketahui';
      var meta = '';
      if (item.barcode) meta += 'Barcode: ' + item.barcode;
      if (item.expiryDate) meta += (meta ? ' | ' : '') + 'EXP: ' + item.expiryDate;
      html += '<div class="detected-item">' +
        '<div class="detected-item-icon ' + iconClass + '"><i class="fa-solid fa-' + (item.method === 'barcode' ? 'barcode' : (item.method === 'ocr' ? 'font' : 'cube')) + '"></i></div>' +
        '<div class="detected-item-info"><div class="detected-item-name">' + escapeHtml(name) + '</div>' +
        '<div class="detected-item-meta">' + escapeHtml(meta) + '</div></div>' +
        '<span class="detected-item-badge ' + badgeClass + '">' + badgeText + '</span>' +
        '<div class="detected-item-actions"><button class="btn-ghost btn-sm" onclick="window.removeDetectedItem(' + item.id + ')"><i class="fa-solid fa-xmark"></i></button></div>' +
        '</div>';
    });
    DOM.detectedList.innerHTML = html;
    DOM.multiCount.textContent = detectedItems.length + ' item';
  }

  window.removeDetectedItem = function (id) {
    detectedItems = detectedItems.filter(function (item) { return item.id !== id; });
    renderDetectedItems();
  };

  function clearDetections() {
    detectedItems = [];
    renderDetectedItems();
    showToast('Semua deteksi dibersihkan', 'info');
  }

  // ── Multi-Object Detection ──
  var multiDetectItems = {};

  function addMultiDetectItem(result) {
    var key = result.productName || result.barcode || 'unknown';
    if (!multiDetectItems[key]) {
      multiDetectItems[key] = { name: key, count: 0, confidence: result.confidence, icon: getProductIcon(key) };
    }
    multiDetectItems[key].count++;
    multiDetectItems[key].confidence = Math.max(multiDetectItems[key].confidence, result.confidence);
    renderMultiDetect();
  }

  function getProductIcon(name) {
    var lower = (name || '').toLowerCase();
    if (lower.indexOf('minuman') !== -1 || lower.indexOf('drink') !== -1) return 'fa-wine-bottle';
    if (lower.indexOf('makanan') !== -1 || lower.indexOf('food') !== -1) return 'fa-utensils';
    if (lower.indexOf('botol') !== -1) return 'fa-bottle-water';
    if (lower.indexOf('kaleng') !== -1) return 'fa-rectangle-ad';
    if (lower.indexOf('kotak') !== -1 || lower.indexOf('box') !== -1) return 'fa-box';
    return 'fa-cube';
  }

  function renderMultiDetect() {
    var keys = Object.keys(multiDetectItems);
    if (keys.length === 0) {
      DOM.multiGrid.innerHTML = '<div class="empty-state"><i class="fa-solid fa-cubes"></i><h4>Belum Ada Deteksi Multi</h4><p>Aktifkan kamera dan arahkan ke rak produk.</p></div>';
      return;
    }
    var html = '';
    keys.forEach(function (key) {
      var item = multiDetectItems[key];
      html += '<div class="multi-detect-item">' +
        '<div class="item-icon"><i class="fa-solid ' + item.icon + '" style="color:var(--color-brand,#6366f1);"></i></div>' +
        '<div class="item-name">' + escapeHtml(item.name.substring(0, 60)) + '</div>' +
        '<div class="item-count">' + item.count + '</div>' +
        '<div class="item-confidence">' + (item.confidence * 100).toFixed(0) + '% akurasi</div>' +
        '</div>';
    });
    DOM.multiGrid.innerHTML = html;
  }

  // ── Update Stats ──
  function updateStats(result) {
    var total = parseInt(DOM.statTotal.textContent) + 1;
    DOM.statTotal.textContent = total;
    var detected = parseInt(DOM.statDetected.textContent) + (result.productName ? 1 : 0);
    DOM.statDetected.textContent = detected;
    if (result.barcode) DOM.statBarcode.textContent = parseInt(DOM.statBarcode.textContent) + 1;
    if (result.expiryDate) DOM.statExpiry.textContent = parseInt(DOM.statExpiry.textContent) + 1;
  }

  // ── Scan History ──
  function loadScanHistory() {
    WarungioAuth.api('/api/inventory/ai-scan/sessions/?limit=20')
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var items = data.results || data || [];
        if (items.length > 0) {
          DOM.historyTable.innerHTML = items.map(function (s) {
            return '<tr>' +
              '<td>' + (s.started_at ? new Date(s.started_at).toLocaleTimeString('id-ID') : '--') + '</td>' +
              '<td>' + escapeHtml(s.product_name || s.total_items_detected + ' item') + '</td>' +
              '<td><span class="scan-history-method ' + (s.scan_mode || 'vision') + '">' + (s.scan_mode || 'Auto') + '</span></td>' +
              '<td>' + (s.barcode || '--') + '</td>' +
              '<td>' + (s.detected_expiry || '--') + '</td>' +
              '<td>' + (s.confidence_score ? (s.confidence_score * 100).toFixed(0) + '%' : '--') + '</td>' +
              '<td><button class="btn-ghost btn-sm"><i class="fa-solid fa-eye"></i></button></td>' +
              '</tr>';
          }).join('');
          DOM.historyTable.style.display = '';
          DOM.historyEmpty.style.display = 'none';
        } else {
          DOM.historyTable.style.display = 'none';
          DOM.historyEmpty.style.display = '';
        }
      })
      .catch(function () {
        DOM.historyTable.style.display = 'none';
        DOM.historyEmpty.style.display = '';
      });
  }

  // ── Helpers ──
  function escapeHtml(s) {
    if (!s) return '';
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/'/g, '&#39;').replace(/"/g, '&#34;');
  }

  function showToast(msg, type) {
    if (typeof window.showToast === 'function') {
      window.showToast(msg, type);
    } else {
      var t = document.getElementById('toast-notification');
      if (t) { t.textContent = msg; t.className = 'toast toast-' + (type || 'info'); t.style.display = 'block'; setTimeout(function () { t.style.display = 'none'; }, 3000); }
    }
  }

  function playScanSound() {
    try {
      var sound = window.WarungioScanSound;
      if (sound && typeof sound.play === 'function') sound.play();
    } catch (e) { /* silent */ }
  }

  // Cleanup on page unload
  window.addEventListener('beforeunload', function () {
    if (stream) { stream.getTracks().forEach(function (t) { t.stop(); }); }
  });

})();
