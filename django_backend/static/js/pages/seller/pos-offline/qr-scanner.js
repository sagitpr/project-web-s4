/**
 * QR Scanner Modal for POS Offline — Warungio Seller
 * 
 * Camera-based QR code scanner using browser MediaDevices API.
 * Scans delivery QR codes for pickup/delivery verification.
 * Used by: POS Offline, Order Detail, Delivery pages.
 */

(function () {
  'use strict';

  let qrStream = null;
  let qrScanTimer = null;
  let isScanning = false;

  const QR_DOM = {
    modal: document.getElementById('qrScannerModal'),
    video: document.getElementById('qrScannerVideo'),
    canvas: document.getElementById('qrScannerCanvas'),
    placeholder: document.getElementById('qrScannerPlaceholder'),
    result: document.getElementById('qrScannerResult'),
    resultText: document.getElementById('qrScannerResultText'),
    resultData: document.getElementById('qrScannerResultData'),
    btnStart: document.getElementById('qrScannerBtnStart'),
    btnStop: document.getElementById('qrScannerBtnStop'),
    btnClose: document.getElementById('qrScannerBtnClose'),
    btnConfirm: document.getElementById('qrScannerBtnConfirm'),
    btnCancel: document.getElementById('qrScannerBtnCancel'),
    indicator: document.getElementById('qrScannerIndicator'),
    manualInput: document.getElementById('qrScannerManualInput'),
    manualBtn: document.getElementById('qrScannerManualBtn'),
  };

  let lastScanResult = null;
  let onScanCallback = null;

  // ── Open QR Scanner Modal ──
  window.openQRScanner = function (callback, options) {
    onScanCallback = callback || null;
    var mode = options?.mode || 'delivery'; // 'pickup', 'delivery', 'verify'

    if (!QR_DOM.modal) {
      console.warn('QR Scanner modal not found in DOM');
      return;
    }

    QR_DOM.modal.style.display = 'flex';
    QR_DOM.modal.querySelector('.modal-header h3').innerHTML =
      '<i class="fa-solid fa-qrcode"></i> ' + (mode === 'pickup' ? 'Scan QR Pickup' : mode === 'verify' ? 'Scan QR Verifikasi' : 'Scan QR Pengiriman');

    startQRScanner();
  };

  // ── Start Camera ──
  function startQRScanner() {
    if (qrStream) { return; }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showQRToast('Browser tidak mendukung kamera', 'error');
      return;
    }

    navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment', width: { ideal: 640 }, height: { ideal: 480 } }
    })
    .then(function (s) {
      qrStream = s;
      if (QR_DOM.video) {
        QR_DOM.video.srcObject = s;
        QR_DOM.video.style.display = 'block';
      }
      if (QR_DOM.placeholder) QR_DOM.placeholder.style.display = 'none';
      if (QR_DOM.btnStart) QR_DOM.btnStart.style.display = 'none';
      if (QR_DOM.btnStop) QR_DOM.btnStop.style.display = 'inline-flex';
      if (QR_DOM.indicator) QR_DOM.indicator.style.display = 'flex';
      isScanning = true;
      startQRScanLoop();
    })
    .catch(function (err) {
      showQRToast('Gagal akses kamera: ' + err.message, 'error');
    });
  }

  // ── Stop Camera ──
  function stopQRScanner() {
    isScanning = false;
    if (qrScanTimer) { clearInterval(qrScanTimer); qrScanTimer = null; }
    if (qrStream) {
      qrStream.getTracks().forEach(function (t) { t.stop(); });
      qrStream = null;
    }
    if (QR_DOM.video) QR_DOM.video.style.display = 'none';
    if (QR_DOM.placeholder) QR_DOM.placeholder.style.display = 'flex';
    if (QR_DOM.btnStart) QR_DOM.btnStart.style.display = 'inline-flex';
    if (QR_DOM.btnStop) QR_DOM.btnStop.style.display = 'none';
    if (QR_DOM.indicator) QR_DOM.indicator.style.display = 'none';
  }

  // ── QR Scan Loop (capture frame + decode) ──
  function startQRScanLoop() {
    if (qrScanTimer) return;
    qrScanTimer = setInterval(function () {
      if (!isScanning || !qrStream || !QR_DOM.video?.videoWidth) return;
      captureQRFrame();
    }, 500);
  }

  function captureQRFrame() {
    if (!QR_DOM.canvas || !QR_DOM.video) return;
    QR_DOM.canvas.width = QR_DOM.video.videoWidth;
    QR_DOM.canvas.height = QR_DOM.video.videoHeight;
    var ctx = QR_DOM.canvas.getContext('2d');
    ctx.drawImage(QR_DOM.video, 0, 0);
    var imageData = QR_DOM.canvas.toDataURL('image/jpeg', 0.7);
    decodeQRFromImage(imageData);
  }

  // ── Decode QR (uses jsQR or Quagga fallback) ──
  function decodeQRFromImage(imageData) {
    if (typeof jsQR === 'undefined') {
      // Try Quagga fallback for barcode detection
      if (typeof Quagga !== 'undefined') {
        Quagga.decodeSingle({
          src: imageData,
          numOfWorkers: 1,
          inputStream: { size: 800 },
          decoder: { readers: ['qr_reader', 'ean_reader', 'code_128_reader'] },
          locate: true,
        }, function (result) {
          if (result && result.codeResult) {
            onQRCodeDetected(result.codeResult.code);
          }
        });
      }
      return;
    }

    // Use jsQR library
    QR_DOM.canvas.width = QR_DOM.video.videoWidth;
    QR_DOM.canvas.height = QR_DOM.video.videoHeight;
    var ctx = QR_DOM.canvas.getContext('2d');
    ctx.drawImage(QR_DOM.video, 0, 0);
    var imageData2 = ctx.getImageData(0, 0, QR_DOM.canvas.width, QR_DOM.canvas.height);

    var code = jsQR(imageData2.data, imageData2.width, imageData2.height, {
      inversionAttempts: 'dontInvert',
    });

    if (code && code.data) {
      onQRCodeDetected(code.data);
    }
  }

  // ── QR Code Detected ──
  function onQRCodeDetected(data) {
    if (!data || lastScanResult === data) return;
    lastScanResult = data;

    // Stop scanning
    isScanning = false;
    if (qrScanTimer) { clearInterval(qrScanTimer); qrScanTimer = null; }
    stopQRScanner();

    // Parse QR data (JSON or plain text)
    var parsed = null;
    try { parsed = JSON.parse(data); } catch (e) { parsed = { raw: data }; }

    // Show result
    if (QR_DOM.result) QR_DOM.result.style.display = 'block';
    if (QR_DOM.resultText) {
      QR_DOM.resultText.textContent = parsed?.order_number || parsed?.order_id || parsed?.raw || data.substring(0, 50);
    }
    if (QR_DOM.resultData) {
      QR_DOM.resultData.textContent = JSON.stringify(parsed, null, 2);
    }

    playScanSound();
    showQRToast('QR Code terdeteksi!', 'success');

    // Auto-confirm if callback provided
    if (onScanCallback) {
      if (QR_DOM.btnConfirm) QR_DOM.btnConfirm.style.display = 'inline-flex';
      QR_DOM.btnConfirm.onclick = function () {
        onScanCallback(parsed || { raw: data, qr_data: data });
        closeQRScanner();
      };
    }
  }

  // ── Manual QR Input ──
  if (QR_DOM.manualBtn) {
    QR_DOM.manualBtn.addEventListener('click', function () {
      var input = QR_DOM.manualInput?.value?.trim();
      if (!input) { showQRToast('Masukkan data QR', 'error'); return; }
      onQRCodeDetected(input);
    });
  }

  // ── Manual Input by Enter key ──
  if (QR_DOM.manualInput) {
    QR_DOM.manualInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        QR_DOM.manualBtn?.click();
      }
    });
  }

  // ── Close Scanner ──
  function closeQRScanner() {
    stopQRScanner();
    lastScanResult = null;
    if (QR_DOM.modal) QR_DOM.modal.style.display = 'none';
    if (QR_DOM.result) QR_DOM.result.style.display = 'none';
    if (QR_DOM.manualInput) QR_DOM.manualInput.value = '';
    if (QR_DOM.btnConfirm) QR_DOM.btnConfirm.style.display = 'none';
  }

  // ── Event Listeners ──
  if (QR_DOM.btnClose) QR_DOM.btnClose.addEventListener('click', closeQRScanner);
  if (QR_DOM.btnCancel) QR_DOM.btnCancel.addEventListener('click', closeQRScanner);
  if (QR_DOM.btnStart) QR_DOM.btnStart.addEventListener('click', startQRScanner);
  if (QR_DOM.btnStop) QR_DOM.btnStop.addEventListener('click', function () {
    stopQRScanner();
    if (QR_DOM.btnStart) QR_DOM.btnStart.style.display = 'inline-flex';
  });

  // Close on overlay click
  if (QR_DOM.modal) {
    QR_DOM.modal.addEventListener('click', function (e) {
      if (e.target === QR_DOM.modal) closeQRScanner();
    });
  }

  // Cleanup on page unload
  window.addEventListener('beforeunload', function () {
    if (qrStream) qrStream.getTracks().forEach(function (t) { t.stop(); });
  });

  // ── Helpers ──
  function showQRToast(msg, type) {
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

  console.info('QR Scanner POS initialized — call window.openQRScanner(callback) to use');
})();
