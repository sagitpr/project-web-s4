/* ── Smart AI Scan v2 — AI Product Registration (Full Auto) ── */
(function () {
  'use strict';

  let stream = null;
  let isScanning = false;
  let scanTimer = null;
  let detectedProducts = [];
  let autoRegisteredProducts = [];
  let scanCount = 0;
  let barcodeFound = 0;
  let expiryFound = 0;
  let confidenceThreshold = 0.4;
  let isProcessing = false;

  const DOM = {
    video: document.getElementById('videoFeed'),
    canvas: document.getElementById('overlayCanvas'),
    bboxOverlay: document.getElementById('bboxOverlay'),
    placeholder: document.getElementById('cameraPlaceholder'),
    indicator: document.getElementById('scanningIndicator'),
    statusText: document.getElementById('aiStatusText'),
    statusBadge: document.getElementById('aiStatusBadge'),
    btnStart: document.getElementById('btnStartCamera'),
    btnStop: document.getElementById('btnStopCamera'),
    draftList: document.getElementById('draftProductList'),
    draftEmpty: document.getElementById('draftEmpty'),
    scanResultPanel: document.getElementById('scanResultPanel'),
    scanResultBody: document.getElementById('scanResultBody'),
    scanConfidence: document.getElementById('scanConfidence'),
    scanMethod: document.getElementById('scanMethod'),
    btnRegisterDraft: document.getElementById('btnRegisterDraft'),
    btnDiscardScan: document.getElementById('btnDiscardScan'),
    statTotal: document.getElementById('statTotal'),
    statDetected: document.getElementById('statDetected'),
    statRegistered: document.getElementById('statRegistered'),
    scanHistoryBody: document.getElementById('scanHistoryBody'),
    scanHistoryEmpty: document.getElementById('scanHistoryEmpty'),
    suggestionPanel: document.getElementById('suggestionPanel'),
    suggestionList: document.getElementById('suggestionList'),
    btnLearning: document.getElementById('btnLearning'),
    learningModal: document.getElementById('learningModal'),
    learningForm: document.getElementById('learningForm'),
    btnCloseLearning: document.getElementById('btnCloseLearning'),
    btnSaveLearning: document.getElementById('btnSaveLearning'),
    redirectBanner: document.getElementById('redirectBanner'),
    redirectTimer: document.getElementById('redirectTimer'),
    redirectBtn: document.getElementById('redirectBtn'),
    redirectCancel: document.getElementById('redirectCancel'),
  };

  let lastDetectedData = null;

  // ── Auth Guard ──
  if (!WarungioAuth || !WarungioAuth.isAuthenticated()) {
    window.location.href = '/auth/login/';
    return;
  }

  // ── Init ──
  document.addEventListener('DOMContentLoaded', function () {
    WarungioAuthUI?.init({ syncBalance: false, syncCart: false });
    loadProfile();
    initListeners();
    loadScanHistory();
    updateStats();
  });

  function loadProfile() {
    const user = WarungioAuth.getUser();
    if (user) {
      const shopNameEl = document.getElementById('shopName');
      const shopIdEl = document.getElementById('shopId');
      const profileNameEl = document.getElementById('profileName');
      if (shopNameEl) shopNameEl.textContent = user.store_name || 'Toko Saya';
      if (shopIdEl) shopIdEl.textContent = 'ID: ' + (user.store_id || '--');
      if (profileNameEl) profileNameEl.textContent = user.full_name || user.email || 'Seller';
      if (user.avatar) {
        const avatar = document.getElementById('profileAvatar');
        if (avatar) avatar.src = user.avatar;
      }
    }
  }

  function initListeners() {
    DOM.btnStart.addEventListener('click', startCamera);
    DOM.btnStop.addEventListener('click', stopCamera);
    DOM.btnRegisterDraft.addEventListener('click', registerDraftFromScan);
    DOM.btnDiscardScan.addEventListener('click', discardScanResult);
    DOM.btnLearning.addEventListener('click', openLearningModal);
    DOM.btnCloseLearning.addEventListener('click', closeLearningModal);
    DOM.btnSaveLearning.addEventListener('click', saveLearning);

    // Load more history
    document.getElementById('btnRefreshHistory')?.addEventListener('click', loadScanHistory);
  }

  // ── Camera (Simplified: only Start/Stop) ──
  function startCamera() {
    if (stream) { showToast('Kamera sudah aktif', 'info'); return; }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showToast('Browser tidak mendukung kamera. Gunakan Chrome atau Firefox.', 'error');
      return;
    }
    DOM.btnStart.disabled = true;
    DOM.btnStart.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Mengakses Kamera...';
    setAIStatus('connecting', 'Mengakses kamera...');

    navigator.mediaDevices.getUserMedia({ 
      video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } } 
    })
    .then(function (s) {
      stream = s;
      DOM.video.srcObject = s;
      DOM.video.style.display = 'block';
      DOM.placeholder.style.display = 'none';
      DOM.btnStart.style.display = 'none';
      DOM.btnStop.style.display = 'inline-flex';
      DOM.indicator.style.display = 'flex';
      DOM.btnStart.disabled = false;
      setAIStatus('active', 'AI Aktif — Memindai...');
      showToast('Kamera aktif. AI otomatis mendeteksi produk.', 'success');
      startAutoScan();
    })
    .catch(function (err) {
      DOM.btnStart.disabled = false;
      DOM.btnStart.innerHTML = '<i class="fa-solid fa-video"></i> Hidupkan Kamera';
      console.error('Camera error:', err);
      setAIStatus('error', 'Gagal akses kamera');
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
    DOM.btnStop.style.display = 'none';
    DOM.indicator.style.display = 'none';
    DOM.scanResultPanel.style.display = 'none';
    if (DOM.redirectBanner) DOM.redirectBanner.style.display = 'none';
    clearInterval(scanTimer);
    clearBoundingBox();
    isScanning = false;
    isProcessing = false;
    setAIStatus('idle', 'Kamera tidak aktif');
    showToast('Kamera dihentikan', 'info');
  }

  // ── AI Status ──
  function setAIStatus(type, text) {
    if (DOM.statusBadge) {
      DOM.statusBadge.className = 'ai-status-badge ' + type;
      DOM.statusBadge.innerHTML = '<span class="status-dot"></span> ' + text;
    }
    if (DOM.statusText) DOM.statusText.textContent = text;
  }

  // ── Auto Scan (Realtime every 2s) ──
  function startAutoScan() {
    if (isScanning) return;
    isScanning = true;

    // First scan after 1 second
    setTimeout(function () { doAutoScan(); }, 1000);

    // Then every 2 seconds
    scanTimer = setInterval(function () {
      if (!isScanning || !stream || isProcessing) return;
      doAutoScan();
    }, 2000);
  }

  function doAutoScan() {
    if (!stream || !DOM.video.videoWidth || isProcessing) return;
    isProcessing = true;
    setAIStatus('scanning', 'Memindai...');

    // Sync bounding box overlay size with video
    if (DOM.bboxOverlay) {
      DOM.bboxOverlay.width = DOM.video.videoWidth;
      DOM.bboxOverlay.height = DOM.video.videoHeight;
    }

    DOM.canvas.width = DOM.video.videoWidth;
    DOM.canvas.height = DOM.video.videoHeight;
    var ctx = DOM.canvas.getContext('2d');
    ctx.drawImage(DOM.video, 0, 0);
    var imageData = DOM.canvas.toDataURL('image/jpeg', 0.7);

    processFrame(imageData);
  }

  // ── Draw Bounding Box on separate overlay (not cleared by scan loop) ──
  function drawBoundingBox(x, y, w, h, label, confidence) {
    var bboxCanvas = DOM.bboxOverlay;
    if (!bboxCanvas) return;
    var ctx = bboxCanvas.getContext('2d');
    
    // Clear previous bounding box
    ctx.clearRect(0, 0, bboxCanvas.width, bboxCanvas.height);
    
    var color = confidence >= 0.75 ? '#22c55e' : (confidence >= 0.4 ? '#f59e0b' : '#ef4444');
    
    // Semi-transparent background over non-detected area (dim outside box)
    ctx.fillStyle = 'rgba(0,0,0,0.25)';
    ctx.fillRect(0, 0, bboxCanvas.width, bboxCanvas.height);
    ctx.clearRect(x, y, w, h);
    
    // Bounding box outline
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.shadowColor = color;
    ctx.shadowBlur = 12;
    ctx.strokeRect(x, y, w, h);
    ctx.shadowBlur = 0;
    
    // Corner accents (white)
    var cornerLen = 14;
    ctx.lineWidth = 4;
    ctx.strokeStyle = '#fff';
    ctx.beginPath(); ctx.moveTo(x, y + cornerLen); ctx.lineTo(x, y); ctx.lineTo(x + cornerLen, y); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x + w - cornerLen, y); ctx.lineTo(x + w, y); ctx.lineTo(x + w, y + cornerLen); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x, y + h - cornerLen); ctx.lineTo(x, y + h); ctx.lineTo(x + cornerLen, y + h); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x + w - cornerLen, y + h); ctx.lineTo(x + w, y + h); ctx.lineTo(x + w, y + h - cornerLen); ctx.stroke();
    
    // Pulse animation ring
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.globalAlpha = 0.4;
    ctx.strokeRect(x - 4, y - 4, w + 8, h + 8);
    ctx.globalAlpha = 1;
    
    // Label background
    ctx.fillStyle = color;
    ctx.beginPath();
    var labelWidth = ctx.measureText(label).width + 16;
    var labelHeight = 28;
    var labelX = Math.max(x, 4);
    var labelY = Math.max(y - labelHeight - 4, 4);
    if (typeof ctx.roundRect === 'function') {
      ctx.roundRect(labelX, labelY, labelWidth, labelHeight, 6);
    } else {
      ctx.rect(labelX, labelY, labelWidth, labelHeight);
    }
    ctx.fill();
    
    // Label text
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 12px system-ui, sans-serif';
    ctx.textBaseline = 'middle';
    ctx.fillText(label.substring(0, 30), labelX + 8, labelY + labelHeight / 2);
  }

  // ── Clear bounding box overlay ──
  function clearBoundingBox() {
    if (DOM.bboxOverlay) {
      var ctx = DOM.bboxOverlay.getContext('2d');
      ctx.clearRect(0, 0, DOM.bboxOverlay.width, DOM.bboxOverlay.height);
    }
  }

  // ── Process Frame (Client-side + Backend AI) ──
  function processFrame(imageData) {
    var clientStart = Date.now();

    // Run client-side detections
    Promise.all([
      scanBarcodeFromImage(imageData),
      scanOCRFromImage(imageData),
      callBackendAI(imageData)
    ]).then(function (results) {
      var barcodeRes = results[0];
      var ocrRes = results[1];
      var backendRes = results[2];

      var combined = {
        productName: backendRes?.product_name || ocrRes?.productName || '',
        brand: backendRes?.brand || ocrRes?.brand || '',
        barcode: backendRes?.barcode || barcodeRes?.code || '',
        category: backendRes?.category || '',
        subcategory: backendRes?.subcategory || '',
        packagingType: backendRes?.packaging_type || backendRes?.packagingType || '',
        unit: backendRes?.unit || 'pcs',
        estimatedPrice: backendRes?.estimated_price || backendRes?.estimatedPrice || 0,
        weightValue: backendRes?.weight_value || null,
        weightUnit: backendRes?.weight_unit || '',
        description: backendRes?.description || '',
        composition: backendRes?.composition || '',
        expiryDate: ocrRes?.expiryDate || backendRes?.expiry_date || '',
        freshnessScore: backendRes?.freshness_score || null,
        freshnessStatus: backendRes?.freshness_status || '',
        confidence: Math.max(
          barcodeRes?.confidence || 0,
          ocrRes?.confidence || 0,
          backendRes?.confidence || 0
        ),
        method: backendRes?.detection_method || 'vision',
        autoRecognized: backendRes?.auto_recognized || false,
        masterProductId: backendRes?.master_product_id || null,
        isFreshFood: backendRes?.is_fresh_food || false,
        imageData: imageData,
        timestamp: new Date().toISOString(),
        // Pass bounding box coordinates from backend if available
        bbox: backendRes?.bounding_box || null,
      };

      var elapsed = Date.now() - clientStart;
      isProcessing = false;

      // Update scan status
      scanCount++;
      updateStats();

      if (combined.confidence > 0) {
        setAIStatus('detected', 'Produk terdeteksi! (' + (combined.confidence * 100).toFixed(0) + '%)');

        // HIGH CONFIDENCE — Auto-register draft
        if (combined.confidence >= 0.75) {
          lastDetectedData = combined;
          showScanResult(combined);
          // Auto-register to draft
          autoRegisterDraft(combined);
        }
        // MEDIUM CONFIDENCE — Show suggestions
        else if (combined.confidence >= 0.4) {
          lastDetectedData = combined;
          showScanResult(combined);
          showSuggestion(combined);
        }
        // LOW CONFIDENCE — Show gentle prompt
        else {
          setAIStatus('low_confidence', 'Akurasi rendah, coba lagi');
        }
      } else {
        setAIStatus('active', 'Memindai...');
      }
    }).catch(function (err) {
      isProcessing = false;
      console.error('Frame error:', err);
      setAIStatus('active', 'Memindai...');
    });
  }

  // ── Call Backend AI ──
  function callBackendAI(imageData) {
    return new Promise(function (resolve) {
      var csrf = getCSRFToken();
      fetch('/api/inventory/ai-recognize/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify({ image: imageData, scan_mode: 'auto' }),
      })
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) { resolve(data || null); })
      .catch(function () { resolve(null); });
    });
  }

  // ── Auto Register Draft ──
  function autoRegisterDraft(data) {
    var existing = autoRegisteredProducts.find(function (p) {
      return p.productName === data.productName || p.barcode === data.barcode;
    });
    if (existing) {
      existing.count = (existing.count != null ? existing.count : 1) + 1;
      renderDraftProducts();
      return;
    }

    // Call backend to create draft
    var csrf = getCSRFToken();
    fetch('/api/inventory/ai-auto-register/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify({
        product_name: data.productName,
        brand: data.brand,
        category: data.category,
        subcategory: data.subcategory || '',
        packaging_type: data.packagingType,
        unit: data.unit,
        weight_value: data.weightValue,
        weight_unit: data.weightUnit,
        estimated_price: data.estimatedPrice,
        description: data.description,
        composition: data.composition,
        expiry_date: data.expiryDate,
        barcode: data.barcode,
        confidence: data.confidence,
        freshness_score: data.freshnessScore,
        freshness_status: data.freshnessStatus,
      }),
    })
    .then(function (res) { return res.json(); })
    .then(function (result) {
      if (result.success) {
        autoRegisteredProducts.push({
          id: result.product_id,
          productName: data.productName,
          barcode: data.barcode,
          brand: data.brand,
          confidence: data.confidence,
          method: data.method,
          count: 1,
          timestamp: data.timestamp,
          slug: result.product_slug || '',
        });
        renderDraftProducts();
        updateStats();
        showToast('✅ Draft produk: ' + data.productName, 'success');
        setAIStatus('registered', 'Produk terdaftar sebagai draft');

        // Draw bounding box using coordinates from backend or default position
        var vw = DOM.video.videoWidth || 640;
        var vh = DOM.video.videoHeight || 480;
        var bx = data.bbox && data.bbox.x != null ? (data.bbox.x / 100 * vw) : vw * 0.1;
        var by = data.bbox && data.bbox.y != null ? (data.bbox.y / 100 * vh) : vh * 0.1;
        var bw = data.bbox && data.bbox.width != null ? (data.bbox.width / 100 * vw) : vw * 0.8;
        var bh = data.bbox && data.bbox.height != null ? (data.bbox.height / 100 * vh) : vh * 0.8;
        drawBoundingBox(bx, by, bw, bh, data.productName || 'Produk', data.confidence);

        // Non-blocking redirect banner with countdown
        var editUrl = '/seller/products/' + result.product_id + '/manage/';
        showRedirectBanner(data.productName, editUrl);
      }
    })
    .catch(function (err) {
      console.warn('Auto-register failed:', err);
    });
  }

  function showSuggestion(data) {
    if (!DOM.suggestionPanel) return;
    DOM.suggestionPanel.style.display = 'block';
    DOM.suggestionList.innerHTML = '';
    var candidates = [
      { name: data.productName, conf: data.confidence, brand: data.brand },
    ];
    if (data.barcode) {
      candidates.push({ name: 'Produk dengan barcode ' + data.barcode, conf: 0.5, brand: '' });
    }
    candidates.forEach(function (c) {
      var div = document.createElement('div');
      div.className = 'suggestion-item';
      div.innerHTML = '<span class="suggestion-name">' + escapeHtml(c.name) + '</span>' +
        '<span class="suggestion-conf">' + (c.conf * 100).toFixed(0) + '%</span>' +
        '<button class="btn-sm btn-primary" onclick="window.selectSuggestion(\'' + escapeHtml(c.name) + '\', ' + c.conf + ')">Pilih</button>';
      DOM.suggestionList.appendChild(div);
    });
  }

  window.selectSuggestion = function (name, conf) {
    if (lastDetectedData) {
      lastDetectedData.productName = name;
      lastDetectedData.confidence = conf;
      showScanResult(lastDetectedData);
      autoRegisterDraft(lastDetectedData);
    }
    DOM.suggestionPanel.style.display = 'none';
  };

  // ── Show Scan Result ──
  function showScanResult(result) {
    DOM.scanResultPanel.style.display = 'block';
    DOM.scanResultBody.innerHTML = '';

    var confClass = result.confidence > 0.8 ? 'high' : (result.confidence > 0.5 ? 'medium' : 'low');
    DOM.scanConfidence.textContent = (result.confidence * 100).toFixed(0) + '%';
    DOM.scanConfidence.className = 'scan-confidence ' + confClass;
    DOM.scanMethod.textContent = result.method === 'barcode' ? 'Barcode' : 
      (result.method === 'ocr' ? 'OCR' : 'AI Vision');

    var fields = [
      { label: 'Nama Produk', value: result.productName || '—' },
      { label: 'Merek', value: result.brand || '—' },
      { label: 'Kategori', value: result.category || '—' },
    ];
    if (result.barcode) fields.push({ label: 'Barcode', value: result.barcode });
    if (result.packagingType) fields.push({ label: 'Kemasan', value: result.packagingType });
    if (result.estimatedPrice > 0) fields.push({ label: 'Estimasi Harga', value: 'Rp ' + Number(result.estimatedPrice).toLocaleString('id-ID') });
    if (result.expiryDate) fields.push({ label: 'EXP Date', value: result.expiryDate });
    if (result.freshnessStatus) fields.push({ label: 'Kesegaran', value: result.freshnessStatus });
    if (result.composition) fields.push({ label: 'Komposisi', value: result.composition.substring(0, 100) });

    fields.forEach(function (f) {
      var row = document.createElement('div');
      row.className = 'field-row';
      row.innerHTML = '<span class="field-label">' + f.label + '</span><span class="field-value">' + escapeHtml(String(f.value)) + '</span>';
      DOM.scanResultBody.appendChild(row);
    });
  }

  function registerDraftFromScan() {
    if (lastDetectedData) autoRegisterDraft(lastDetectedData);
  }

  function discardScanResult() {
    lastDetectedData = null;
    DOM.scanResultPanel.style.display = 'none';
    DOM.suggestionPanel.style.display = 'none';
  }

  // ── Draft Products ──
  function renderDraftProducts() {
    if (autoRegisteredProducts.length === 0) {
      DOM.draftList.innerHTML = '';
      DOM.draftEmpty.style.display = 'block';
      return;
    }
    DOM.draftEmpty.style.display = 'none';
    var html = '';
    autoRegisteredProducts.forEach(function (item) {
      var editUrl = '/seller/products/' + item.id + '/manage/';
      html += '<div class="draft-item">' +
        '<div class="draft-item-icon"><i class="fa-solid fa-file-pen"></i></div>' +
        '<div class="draft-item-info">' +
          '<div class="draft-item-name">' + escapeHtml(item.productName) + '</div>' +
          '<div class="draft-item-meta">' +
            (item.brand ? escapeHtml(item.brand) + ' · ' : '') +
            (item.barcode ? 'Barcode: ' + escapeHtml(item.barcode) + ' · ' : '') +
            (item.confidence * 100).toFixed(0) + '% akurasi</div>' +
        '</div>' +
        '<a href="' + editUrl + '" class="btn-primary btn-sm" target="_blank"><i class="fa-solid fa-pen-to-square"></i> Edit</a>' +
      '</div>';
    });
    DOM.draftList.innerHTML = html;
  }

  // ── AI Learning ──
  function openLearningModal() {
    if (!lastDetectedData) {
      showToast('Scan produk terlebih dahulu', 'warning');
      return;
    }
    DOM.learningModal.style.display = 'flex';
    document.getElementById('learnProductName').value = lastDetectedData.productName || '';
    document.getElementById('learnBrand').value = lastDetectedData.brand || '';
    document.getElementById('learnCategory').value = lastDetectedData.category || '';
  }

  function closeLearningModal() {
    DOM.learningModal.style.display = 'none';
  }

  function saveLearning() {
    var data = {
      product_name: document.getElementById('learnProductName').value,
      brand: document.getElementById('learnBrand').value,
      category: document.getElementById('learnCategory').value,
      images: lastDetectedData?.imageData ? [lastDetectedData.imageData] : [],
    };
    if (!data.product_name) {
      showToast('Nama produk wajib diisi', 'error');
      return;
    }
    var csrf = getCSRFToken();
    fetch('/api/inventory/ai-learn-product/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify(data),
    })
    .then(function (res) { return res.json(); })
    .then(function (result) {
      closeLearningModal();
      showToast('✅ Produk dipelajari AI: ' + data.product_name, 'success');
    })
    .catch(function (err) {
      showToast('Gagal menyimpan pembelajaran: ' + err.message, 'error');
    });
  }

  // ── Barcode Scan ──
  function scanBarcodeFromImage(imageData) {
    return new Promise(function (resolve) {
      if (typeof Quagga === 'undefined') { resolve(null); return; }
      Quagga.decodeSingle({
        src: imageData,
        numOfWorkers: 1,
        inputStream: { size: 800 },
        decoder: { readers: ['ean_reader', 'ean_8_reader', 'upc_reader', 'code_128_reader'] },
        locate: true,
      }, function (result) {
        if (result && result.codeResult) {
          barcodeFound++;
          resolve({ code: result.codeResult.code, confidence: 0.9, format: result.codeResult.format });
        } else {
          resolve(null);
        }
      });
    });
  }

  // ── OCR Scan ──
  function scanOCRFromImage(imageData) {
    if (typeof Tesseract === 'undefined') return Promise.resolve(null);
    return Tesseract.recognize(imageData, 'ind', { logger: function () {} })
      .then(function (res) {
        var text = res.data.text;
        if (!text || text.length < 5) return null;

        var productName = '';
        var expiryDate = '';
        var lines = text.split('\n').filter(function (l) { return l.trim().length > 3; });

        // Extract expiry date
        var expMatch = text.match(/(?:EXP|exp|Exp|ED|Kadaluwarsa|kedaluwarsa|expiry)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})/);
        if (expMatch) expiryDate = expMatch[1];
        var expMatch2 = text.match(/(\d{2}[\/\-]\d{2}[\/\-]\d{4})/);
        if (!expiryDate && expMatch2) expiryDate = expMatch2[1];

        // Guess product name (first meaningful line)
        var stopWords = ['exp', 'expiry', 'batch', 'lot', 'bpom', 'pom', 'kg', 'g', 'ml', 'l', 'gr', 'netto', 'berat'];
        for (var i = 0; i < lines.length; i++) {
          var line = lines[i].trim();
          var firstWord = (line.split(/\s+/)[0] || '').toLowerCase();
          if (line.length > 5 && stopWords.indexOf(firstWord) === -1 && !/^\d/.test(firstWord)) {
            productName = line.substring(0, 200);
            break;
          }
        }

        if (expiryDate) expiryFound++;
        return {
          productName: productName || '',
          expiryDate: expiryDate || '',
          confidence: res.data.confidence / 100 || 0.1,
        };
      })
      .catch(function () { return null; });
  }

  // ── Stats ──
  function updateStats() {
    if (DOM.statTotal) DOM.statTotal.textContent = scanCount;
    if (DOM.statDetected) DOM.statDetected.textContent = autoRegisteredProducts.length;
    if (DOM.statRegistered) DOM.statRegistered.textContent = autoRegisteredProducts.filter(function (p) { return p.id; }).length;
  }

  // ── Scan History ──
  function loadScanHistory() {
    WarungioAuth.api('/api/inventory/ai-scan/sessions/?limit=20')
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var items = data.results || data || [];
        if (items.length > 0 && DOM.scanHistoryBody) {
          DOM.scanHistoryBody.innerHTML = items.map(function (s) {
            return '<tr>' +
              '<td>' + (s.started_at ? new Date(s.started_at).toLocaleTimeString('id-ID') : '--') + '</td>' +
              '<td>' + escapeHtml(s.product_name || (s.total_items_detected + ' item')) + '</td>' +
              '<td><span class="his-method ' + (s.scan_mode || 'vision') + '">' + (s.scan_mode || 'Auto') + '</span></td>' +
              '<td>' + (s.barcode || '--') + '</td>' +
              '<td>' + (s.detected_expiry || '--') + '</td>' +
              '<td>' + (s.confidence_score ? (s.confidence_score * 100).toFixed(0) + '%' : '--') + '</td>' +
              '</tr>';
          }).join('');
          DOM.scanHistoryBody.style.display = '';
          if (DOM.scanHistoryEmpty) DOM.scanHistoryEmpty.style.display = 'none';
        } else {
          if (DOM.scanHistoryBody) DOM.scanHistoryBody.style.display = 'none';
          if (DOM.scanHistoryEmpty) DOM.scanHistoryEmpty.style.display = '';
        }
      })
      .catch(function () {
        if (DOM.scanHistoryBody) DOM.scanHistoryBody.style.display = 'none';
        if (DOM.scanHistoryEmpty) DOM.scanHistoryEmpty.style.display = '';
      });
  }

  // ── Non-blocking Redirect Banner ──
  var redirectTimerId = null;

  function showRedirectBanner(productName, editUrl) {
    if (!DOM.redirectBanner) return;
    DOM.redirectBanner.style.display = 'flex';
    DOM.redirectBanner.querySelector('.redirect-product-name').textContent = productName || 'Produk';
    DOM.redirectBtn.onclick = function () { window.location.href = editUrl; };
    DOM.redirectCancel.onclick = function () {
      DOM.redirectBanner.style.display = 'none';
      if (redirectTimerId) clearTimeout(redirectTimerId);
    };

    // Auto-redirect after 5 seconds with countdown
    var countdown = 5;
    DOM.redirectTimer.textContent = countdown + 's';
    if (redirectTimerId) clearTimeout(redirectTimerId);
    redirectTimerId = setInterval(function () {
      countdown--;
      DOM.redirectTimer.textContent = countdown + 's';
      if (countdown <= 0) {
        clearInterval(redirectTimerId);
        redirectTimerId = null;
        window.location.href = editUrl;
      }
    }, 1000);
  }

  // ── Helpers ──
  function getCSRFToken() {
    var name = 'csrftoken';
    var match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? match[2] : '';
  }

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

  // Cleanup
  window.addEventListener('beforeunload', function () {
    if (stream) stream.getTracks().forEach(function (t) { t.stop(); });
    if (scanTimer) clearInterval(scanTimer);
  });

})();
