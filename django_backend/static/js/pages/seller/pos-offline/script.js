/* ── AI POS Kasir v2 — AI Camera First (No dropdowns, no manual input) ── */
(function () {
  'use strict';

  // ── State ──
  let cart = [];
  let stream = null;
  let selectedPayment = 'cash';
  let recentTransactions = [];
  let isScanning = false;
  let scanTimer = null;
  let isProcessing = false;
  let scanCount = 0;
  let lastFrameData = null;
  let discountType = 'percent';
  let discountValue = 0;
  let taxEnabled = false;
  const TAX_RATE = 0.11;
  const ADMIN_FEE = 1500;

  // ── DOM Cache ──
  const DOM = {
    video: document.getElementById('posVideoFeed'),
    bboxOverlay: document.getElementById('posBboxOverlay'),
    placeholder: document.getElementById('posPlaceholder'),
    scanIndicator: document.getElementById('posScanIndicator'),
    camInfo: document.getElementById('posCamInfo'),
    aiStatus: document.getElementById('posAIStatus'),
    cartItems: document.getElementById('posCartItems'),
    cartEmpty: document.getElementById('posCartEmpty'),
    cartSummary: document.getElementById('posCartSummary'),
    cartBadge: document.getElementById('cartCountBadge'),
    subtotal: document.getElementById('posSubtotal'),
    discountRow: document.getElementById('posDiscountRow'),
    discountAmount: document.getElementById('posDiscountAmount'),
    taxRow: document.getElementById('posTaxRow'),
    taxAmount: document.getElementById('posTaxAmount'),
    adminFee: document.getElementById('posAdminFee'),
    total: document.getElementById('posTotal'),
    grandTotal: document.getElementById('posGrandTotalAmount'),
    discountInput: document.getElementById('posDiscountInput'),
    discountSuffix: document.getElementById('posDiscountSuffix'),
    taxCheckbox: document.getElementById('posTaxCheckbox'),
    taxSwitch: document.getElementById('posTaxSwitch'),
    buyerName: document.getElementById('posBuyerName'),
    notes: document.getElementById('posNotes'),
    cashAmount: document.getElementById('posCashAmount'),
    changeRow: document.getElementById('posChangeRow'),
    changeAmount: document.getElementById('posChangeAmount'),
    amountInput: document.getElementById('posAmountInput'),
    payBtn: document.getElementById('posProcessPayment'),
    clearCart: document.getElementById('posClearCart'),
    recentBody: document.getElementById('posRecentBody'),
    receiptBody: document.getElementById('receiptBody'),
    btnPrint: document.getElementById('btnPrintReceipt'),
    btnNewTx: document.getElementById('btnNewTransaction'),
    btnCloseReceipt: document.getElementById('btnCloseReceipt'),
    btnStart: document.getElementById('posBtnStart'),
    btnStop: document.getElementById('posBtnStop'),
    shopName: document.getElementById('shopName'),
    shopId: document.getElementById('shopId'),
    profileName: document.getElementById('profileName'),
    profileAvatar: document.getElementById('profileAvatar'),
    // Learning modal
    learningModal: document.getElementById('posLearningModal'),
    learnName: document.getElementById('posLearnName'),
    learnPrice: document.getElementById('posLearnPrice'),
    learnCategory: document.getElementById('posLearnCategory'),
    btnSaveLearning: document.getElementById('btnSavePosLearning'),
    btnCloseLearning: document.getElementById('btnClosePosLearning'),
  };

  let lastScannedImageData = null;

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
    loadRecentTransactions();
    updateClock();
    setInterval(updateClock, 1000);
  });

  function loadProfile() {
    const user = WarungioAuth.getUser();
    if (user) {
      DOM.shopName.textContent = user.store_name || 'Toko Saya';
      DOM.shopId.textContent = 'ID: ' + (user.store_id || '--');
      DOM.profileName.textContent = user.full_name || user.email || 'Seller';
      if (user.avatar) DOM.profileAvatar.src = user.avatar;
    }
  }

  function updateClock() {
    var now = new Date();
    var dateEl = document.getElementById('posDate');
    var timeEl = document.getElementById('posTime');
    if (dateEl) dateEl.textContent = now.toLocaleDateString('id-ID', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    if (timeEl) timeEl.textContent = now.toLocaleTimeString('id-ID');
  }

  function initListeners() {
    // Camera (ONLY two buttons)
    DOM.btnStart.addEventListener('click', startCamera);
    DOM.btnStop.addEventListener('click', stopCamera);

    // Cart
    DOM.clearCart.addEventListener('click', clearCart);
    DOM.payBtn.addEventListener('click', processPayment);

    // Discount type toggle
    document.querySelectorAll('.pos-radio-label[data-dtype]').forEach(function (lbl) {
      lbl.addEventListener('click', function () {
        document.querySelectorAll('.pos-radio-label[data-dtype]').forEach(function (o) { o.classList.remove('active'); });
        this.classList.add('active');
        discountType = this.dataset.dtype;
        DOM.discountSuffix.textContent = discountType === 'percent' ? '%' : 'Rp';
        DOM.discountInput.max = discountType === 'percent' ? '100' : '999999999';
        DOM.discountInput.value = '0';
        discountValue = 0;
        updateTotals();
      });
    });

    // Discount input
    DOM.discountInput.addEventListener('input', function () {
      var val = parseFloat(this.value) || 0;
      if (discountType === 'percent' && val > 100) { val = 100; this.value = 100; }
      discountValue = val;
      updateTotals();
    });

    // Tax toggle
    DOM.taxSwitch.addEventListener('click', function () {
      taxEnabled = !taxEnabled;
      DOM.taxCheckbox.checked = taxEnabled;
      DOM.taxSwitch.querySelector('.pos-switch-track').classList.toggle('active', taxEnabled);
      updateTotals();
    });

    // Payment method
    document.querySelectorAll('.pos-payment-option').forEach(function (opt) {
      opt.addEventListener('click', function () {
        document.querySelectorAll('.pos-payment-option').forEach(function (o) { o.classList.remove('active'); });
        this.classList.add('active');
        selectedPayment = this.dataset.method;
        this.querySelector('input[type="radio"]').checked = true;
        DOM.amountInput.style.display = selectedPayment === 'cash' ? 'block' : 'none';
        updatePayButton();
      });
    });

    // Cash input
    DOM.cashAmount.addEventListener('input', updateChange);

    // Receipt actions
    DOM.btnPrint.addEventListener('click', function () { window.print(); });
    DOM.btnNewTx.addEventListener('click', function () {
      closeModal('receiptModal');
      clearCart();
    });
    DOM.btnCloseReceipt.addEventListener('click', function () {
      closeModal('receiptModal');
    });

    // Learning modal
    DOM.btnSaveLearning.addEventListener('click', savePosLearning);
    DOM.btnCloseLearning.addEventListener('click', function () {
      DOM.learningModal.style.display = 'none';
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', function (e) {
      if (e.key === 'F2') { e.preventDefault(); processPayment(); }
      if (e.key === 'F8') { e.preventDefault(); clearCart(); }
      if (e.key === 'Escape') { closeAllModals(); }
    });

    // Close modal on overlay click
    document.querySelectorAll('.modal-overlay').forEach(function (el) {
      el.addEventListener('click', function (e) {
        if (e.target === this) this.style.display = 'none';
      });
    });
  }

  // ── AI Status ──
  function setAIStatus(type, text) {
    if (DOM.aiStatus) {
      DOM.aiStatus.innerHTML = '<span class="status-dot ' + type + '"></span> ' + text;
    }
    if (DOM.camInfo) DOM.camInfo.textContent = text;
  }

  // ── Camera (Only Start/Stop) ──
  function startCamera() {
    if (stream) { showToast('Kamera sudah aktif', 'info'); return; }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showToast('Browser tidak mendukung kamera', 'error');
      return;
    }
    DOM.btnStart.disabled = true;
    DOM.btnStart.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Mengakses...';
    setAIStatus('scanning', 'Mengakses kamera...');

    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: { ideal: 640 }, height: { ideal: 480 } } })
      .then(function (s) {
        stream = s;
        DOM.video.srcObject = s;
        DOM.video.style.display = 'block';
        DOM.placeholder.style.display = 'none';
        DOM.btnStart.style.display = 'none';
        DOM.btnStop.style.display = 'inline-flex';
        DOM.scanIndicator.style.display = 'flex';
        DOM.btnStart.disabled = false;
        setAIStatus('active', 'AI Aktif — Arahkan produk ke kamera');
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
    if (stream) { stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; }
    DOM.video.style.display = 'none';
    DOM.placeholder.style.display = 'flex';
    DOM.btnStart.style.display = 'inline-flex';
    DOM.btnStop.style.display = 'none';
    DOM.scanIndicator.style.display = 'none';
    clearBboxOverlay();
    clearInterval(scanTimer);
    isScanning = false;
    isProcessing = false;
    setAIStatus('idle', 'Kamera tidak aktif');
    showToast('Kamera dihentikan', 'info');
  }

  // ── Auto Scan (Realtime every 1.5s) ──
  function startAutoScan() {
    if (isScanning) return;
    isScanning = true;
    setTimeout(function () { doAutoScan(); }, 500);
    scanTimer = setInterval(function () {
      if (!isScanning || !stream || isProcessing) return;
      doAutoScan();
    }, 1500);
  }

  function doAutoScan() {
    if (!stream || !DOM.video.videoWidth || isProcessing) return;
    isProcessing = true;
    setAIStatus('scanning', 'Memindai...');

    // Sync bbox overlay size
    if (DOM.bboxOverlay) {
      DOM.bboxOverlay.width = DOM.video.videoWidth;
      DOM.bboxOverlay.height = DOM.video.videoHeight;
    }

    var c = document.createElement('canvas');
    c.width = DOM.video.videoWidth;
    c.height = DOM.video.videoHeight;
    var ctx = c.getContext('2d');
    ctx.drawImage(DOM.video, 0, 0);
    var imageData = c.toDataURL('image/jpeg', 0.6);
    lastScannedImageData = imageData;

    processFrame(imageData);
  }

  // ── Process Frame (AI Recognition) ──
  function processFrame(imageData) {
    var clientStart = Date.now();

    // Client-side barcode (fallback) + Backend AI
    Promise.all([
      scanBarcodeFromImage(imageData),
      callBackendAI(imageData)
    ]).then(function (results) {
      var barcodeRes = results[0];
      var backendRes = results[1];

      isProcessing = false;
      scanCount++;

      // Check if barcode recognized first
      if (barcodeRes && barcodeRes.code) {
        addToCartByBarcode(barcodeRes.code);
        setAIStatus('detected', 'Barcode: ' + barcodeRes.code);
        return;
      }

      // Check backend AI result
      if (backendRes) {
        var productName = backendRes.product_name || '';
        var confidence = backendRes.confidence || 0;

        if (confidence >= 0.6) {
          // High confidence — auto-add to cart
          var productData = {
            id: backendRes.product_id || ('ai_' + Date.now()),
            product_name: productName,
            price: backendRes.estimated_price || backendRes.price || 0,
            stock: backendRes.available_stock != null ? backendRes.available_stock : 999,
            barcode: backendRes.barcode || '',
            brand: backendRes.brand || '',
            imageData: imageData,
          };
          addToCart(productData, backendRes);
          setAIStatus('detected', productName.substring(0, 30) + ' (' + (confidence * 100).toFixed(0) + '%)');
          
          // Draw bounding box
          var vw = DOM.video.videoWidth || 640;
          var vh = DOM.video.videoHeight || 480;
          var bx = backendRes.bounding_box?.x != null ? (backendRes.bounding_box.x / 100 * vw) : vw * 0.15;
          var by = backendRes.bounding_box?.y != null ? (backendRes.bounding_box.y / 100 * vh) : vh * 0.15;
          var bw = backendRes.bounding_box?.width != null ? (backendRes.bounding_box.width / 100 * vw) : vw * 0.7;
          var bh = backendRes.bounding_box?.height != null ? (backendRes.bounding_box.height / 100 * vh) : vh * 0.7;
          drawBbox(bx, by, bw, bh, productName.substring(0, 20), confidence);
        } else if (confidence >= 0.3) {
          // Low confidence — show learning dialog
          setAIStatus('low', 'Akurasi rendah, ajarkan AI');
          showLearningDialog(productName, backendRes);
        } else {
          setAIStatus('active', 'Memindai...');
        }
      } else {
        // No recognition — try OCR as last resort
        scanOCRFromImage(imageData).then(function (ocrRes) {
          if (ocrRes && ocrRes.productName) {
            showToast('OCR: ' + ocrRes.productName, 'info');
            showLearningDialog(ocrRes.productName, {});
          }
          isProcessing = false;
        }).catch(function () {
          isProcessing = false;
        });
      }
    }).catch(function (err) {
      isProcessing = false;
      console.error('Frame error:', err);
      setAIStatus('active', 'Memindai...');
    });
  }

  // ── Barcode Scan ──
  function scanBarcodeFromImage(imageData) {
    return new Promise(function (resolve) {
      if (typeof Quagga === 'undefined') { resolve(null); return; }
      Quagga.decodeSingle({
        src: imageData, numOfWorkers: 1, inputStream: { size: 800 },
        decoder: { readers: ['ean_reader', 'ean_8_reader', 'upc_reader', 'code_128_reader'] },
        locate: true,
      }, function (result) {
        if (result && result.codeResult) {
          resolve({ code: result.codeResult.code, confidence: 0.95 });
        } else { resolve(null); }
      });
    });
  }

  // ── OCR Scan (last resort) ──
  function scanOCRFromImage(imageData) {
    if (typeof Tesseract === 'undefined') return Promise.resolve(null);
    return Tesseract.recognize(imageData, 'ind', { logger: function () {} })
      .then(function (res) {
        var text = res.data.text;
        if (!text || text.length < 5) return null;
        var lines = text.split('\n').filter(function (l) { return l.trim().length > 3; });
        for (var i = 0; i < lines.length; i++) {
          var line = lines[i].trim();
          var firstWord = (line.split(/\s+/)[0] || '').toLowerCase();
          if (line.length > 5 && ['exp','bpom','pom','kg','g','ml','l'].indexOf(firstWord) === -1 && !/^\d/.test(firstWord)) {
            return { productName: line.substring(0, 200), confidence: res.data.confidence / 100 || 0.1 };
          }
        }
        return null;
      }).catch(function () { return null; });
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

  // ── Add to Cart by Barcode ──
  function addToCartByBarcode(barcode) {
    WarungioAuth.api('/api/inventory/barcode-lookup/?barcode=' + encodeURIComponent(barcode))
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.found && data.master_product) {
          var mp = data.master_product;
          return WarungioAPI.getProducts({ search: mp.product_name, limit: 5 });
        }
        return null;
      })
      .then(function (products) {
        if (products && products.results && products.results.length > 0) {
          var p = products.results[0];
          addToCart({
            id: p.id,
            product_name: p.product_name,
            price: parseFloat(p.price),
            stock: p.available_stock != null ? p.available_stock : (p.stock != null ? p.stock : 999),
            barcode: barcode,
          });
        } else {
          showToast('Produk tidak ditemukan: ' + barcode, 'error');
        }
      })
      .catch(function () {
        showToast('Gagal cari produk', 'error');
      });
  }

  // ── Cart ──
  function addToCart(product, backendRes) {
    var productId = product.id;
    var existing = cart.find(function (item) { return item.id === productId; });
    
    var currentStock = product.available_stock != null ? product.available_stock : (product.stock != null ? product.stock : 999);

    if (existing) {
      if (existing.qty < currentStock) {
        existing.qty++;
        playScanSound();
        showToast(product.product_name + ' (x' + existing.qty + ')', 'success');
      } else {
        showToast('Stok ' + product.product_name + ' habis!', 'error');
      }
    } else {
      cart.push({
        id: productId,
        name: product.product_name || 'Produk',
        price: parseFloat(product.price) || 0,
        qty: 1,
        maxStock: currentStock,
        barcode: product.barcode || '',
      });
      playScanSound();
      showToast(product.product_name + ' ditambahkan', 'success');
    }

    // Stock warning toast (only on first scan, not on re-scan increments)
    if (!existing || currentStock !== existing.maxStock) {
      if (currentStock <= 3) {
        showToast('⚠️ Stok ' + (product.product_name || 'produk') + ' tersisa ' + currentStock + ' — segera restok!', 'error', 5000);
      } else if (currentStock <= 10) {
        showToast('ℹ️ Stok ' + (product.product_name || 'produk') + ' tinggal ' + currentStock, 'info', 3000);
      }
    }

    renderCart();
    updatePayButton();
  }

  window.addToCart = addToCart;

  function removeFromCart(id) {
    cart = cart.filter(function (item) { return item.id !== id; });
    renderCart();
    updatePayButton();
  }
  window.removeFromCart = removeFromCart;

  function updateCartQty(id, delta) {
    var item = cart.find(function (i) { return i.id === id; });
    if (!item) return;
    var newQty = item.qty + delta;
    if (newQty <= 0) { removeFromCart(id); return; }
    if (newQty > item.maxStock) { showToast('Stok maks: ' + item.maxStock, 'error'); return; }
    item.qty = newQty;
    renderCart();
  }
  window.updateCartQty = updateCartQty;

  function clearCart() {
    cart = [];
    renderCart();
    updatePayButton();
    DOM.buyerName.value = '';
    DOM.notes.value = '';
    DOM.cashAmount.value = '';
    DOM.changeRow.style.display = 'none';
    // Reset diskon & pajak
    DOM.discountInput.value = '0';
    discountValue = 0;
    taxEnabled = false;
    DOM.taxCheckbox.checked = false;
    if (DOM.taxSwitch) {
      var track = DOM.taxSwitch.querySelector('.pos-switch-track');
      if (track) track.classList.remove('active');
    }
    showToast('Keranjang dikosongkan', 'info');
  }

  function renderCart() {
    var count = cart.reduce(function (sum, item) { return sum + item.qty; }, 0);
    DOM.cartBadge.textContent = count;

    if (cart.length === 0) {
      DOM.cartItems.style.display = 'none';
      DOM.cartEmpty.style.display = 'flex';
      DOM.cartSummary.style.display = 'none';
      return;
    }
    DOM.cartEmpty.style.display = 'none';
    DOM.cartItems.style.display = 'block';
    DOM.cartSummary.style.display = 'block';

    DOM.cartItems.innerHTML = cart.map(function (item) {
      var subtotal = item.price * item.qty;
      var stock = item.maxStock;
      var stockClass = stock <= 3 ? 'stock-low' : (stock <= 10 ? 'stock-medium' : 'stock-ok');
      return '<div class="pos-cart-item">' +
        '<div class="pos-cart-item-info">' +
          '<div class="pos-cart-item-name">' + escapeHtml(item.name) + '</div>' +
          '<div class="pos-cart-item-unit">Rp ' + formatNumber(item.price) + ' x ' + item.qty + '</div>' +
          '<div class="pos-cart-item-stock ' + stockClass + '">' +
            '<i class="fa-solid fa-boxes-stacked"></i> Stok: ' + stock +
          '</div>' +
        '</div>' +
        '<div class="pos-cart-item-qty">' +
          '<button onclick="window.updateCartQty(' + item.id + ', -1)"><i class="fa-solid fa-minus"></i></button>' +
          '<span class="item-qty">' + item.qty + '</span>' +
          '<button onclick="window.updateCartQty(' + item.id + ', 1)"><i class="fa-solid fa-plus"></i></button>' +
        '</div>' +
        '<div class="pos-cart-item-price">Rp ' + formatNumber(subtotal) + '</div>' +
        '<button class="pos-cart-item-remove" onclick="window.removeFromCart(' + item.id + ')"><i class="fa-solid fa-trash-can"></i></button>' +
        '</div>';
    }).join('');

    updateTotals();
  }

  function updateTotals() {
    var subtotal = cart.reduce(function (sum, item) { return sum + (item.price * item.qty); }, 0);
    var fee = subtotal > 0 ? ADMIN_FEE : 0;

    // Calculate discount
    var discount = 0;
    if (discountValue > 0 && subtotal > 0) {
      if (discountType === 'percent') {
        discount = subtotal * (Math.min(discountValue, 100) / 100);
      } else {
        discount = Math.min(discountValue, subtotal);
      }
    }

    // Calculate tax (PPN 11% after discount)
    var afterDiscount = subtotal - discount;
    var tax = taxEnabled ? afterDiscount * TAX_RATE : 0;

    // Grand total
    var total = afterDiscount + tax + fee;
    var grandTotal = total;

    // Update display
    DOM.subtotal.textContent = 'Rp ' + formatNumber(subtotal);

    // Discount row
    if (discount > 0) {
      DOM.discountRow.style.display = 'flex';
      DOM.discountAmount.textContent = '- Rp ' + formatNumber(discount);
    } else {
      DOM.discountRow.style.display = 'none';
    }

    // Tax row
    if (taxEnabled && tax > 0) {
      DOM.taxRow.style.display = 'flex';
      DOM.taxAmount.textContent = 'Rp ' + formatNumber(tax);
    } else {
      DOM.taxRow.style.display = 'none';
    }

    DOM.adminFee.textContent = 'Rp ' + formatNumber(fee);
    DOM.total.textContent = 'Rp ' + formatNumber(total);
    DOM.grandTotal.textContent = 'Rp ' + formatNumber(grandTotal);
  }

  function updatePayButton() {
    DOM.payBtn.disabled = cart.length === 0;
  }

  function updateChange() {
    var cash = parseFloat(DOM.cashAmount.value) || 0;
    var total = parseTotal();
    if (cash >= total) {
      DOM.changeRow.style.display = 'flex';
      DOM.changeAmount.textContent = 'Rp ' + formatNumber(cash - total);
    } else {
      DOM.changeRow.style.display = 'none';
    }
  }

  function parseTotal() {
    var sub = cart.reduce(function (sum, item) { return sum + (item.price * item.qty); }, 0);
    var fee = sub > 0 ? ADMIN_FEE : 0;
    var discount = 0;
    if (discountValue > 0 && sub > 0) {
      discount = discountType === 'percent' ? sub * (Math.min(discountValue, 100) / 100) : Math.min(discountValue, sub);
    }
    var afterDiscount = sub - discount;
    var tax = taxEnabled ? afterDiscount * TAX_RATE : 0;
    return afterDiscount + tax + fee;
  }

  // ── Bounding Box ──
  function drawBbox(x, y, w, h, label, confidence) {
    var canvas = DOM.bboxOverlay;
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    var color = confidence >= 0.7 ? '#22c55e' : '#f59e0b';
    // Dim outside
    ctx.fillStyle = 'rgba(0,0,0,0.2)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.clearRect(x, y, w, h);
    // Outline
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.shadowColor = color;
    ctx.shadowBlur = 10;
    ctx.strokeRect(x, y, w, h);
    ctx.shadowBlur = 0;
    // Label
    ctx.fillStyle = color;
    ctx.font = 'bold 12px system-ui, sans-serif';
    var tw = ctx.measureText(label).width + 12;
    var lx = Math.max(x, 4);
    var ly = Math.max(y - 26, 4);
    ctx.beginPath();
    if (typeof ctx.roundRect === 'function') ctx.roundRect(lx, ly, tw, 24, 6);
    else ctx.rect(lx, ly, tw, 24);
    ctx.fill();
    ctx.fillStyle = '#fff';
    ctx.textBaseline = 'middle';
    ctx.fillText(label, lx + 6, ly + 12);
  }

  function clearBboxOverlay() {
    if (DOM.bboxOverlay) {
      var ctx = DOM.bboxOverlay.getContext('2d');
      ctx.clearRect(0, 0, DOM.bboxOverlay.width, DOM.bboxOverlay.height);
    }
  }

  // ── Learning Dialog ──
  function showLearningDialog(productName, data) {
    if (!DOM.learningModal) return;
    DOM.learnName.value = productName || '';
    DOM.learnPrice.value = data?.estimated_price || data?.price || '';
    DOM.learnCategory.value = data?.category || '';
    DOM.learningModal.style.display = 'flex';
  }

  function savePosLearning() {
    var name = DOM.learnName.value.trim();
    var price = parseFloat(DOM.learnPrice.value) || 0;
    if (!name) { showToast('Nama produk wajib diisi', 'error'); return; }

    // Auto-register as draft + add to cart
    var csrf = getCSRFToken();
    fetch('/api/inventory/ai-auto-register/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify({
        product_name: name,
        category: DOM.learnCategory.value.trim() || 'UMKM',
        estimated_price: price,
        images: lastScannedImageData ? [lastScannedImageData] : [],
        confidence: 0.3,
      }),
    })
    .then(function (res) { return res.json(); })
    .then(function (result) {
      if (result.success) {
        cart.push({
          id: result.product_id,
          name: name,
          price: price,
          qty: 1,
          maxStock: result.available_stock != null ? result.available_stock : 999,
          barcode: result.barcode || '',
        });
        renderCart();
        updatePayButton();
        DOM.learningModal.style.display = 'none';
        showToast('✅ Produk ditambahkan: ' + name, 'success');
      }
    })
    .catch(function (err) {
      showToast('Gagal: ' + err.message, 'error');
    });
  }

  // ── Payment ──
  function processPayment() {
    if (cart.length === 0) return;
    var total = parseTotal();

    if (selectedPayment === 'cash') {
      var cash = parseFloat(DOM.cashAmount.value) || 0;
      if (cash < total) {
        showToast('Uang tunai kurang! Minimal Rp ' + formatNumber(total), 'error');
        return;
      }
    }

    // Processing overlay
    var overlay = document.createElement('div');
    overlay.className = 'pos-processing-overlay';
    overlay.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i><p>Memproses pembayaran...</p>';
    document.body.appendChild(overlay);

    var items = cart.map(function (item) {
      return { product_id: typeof item.id === 'number' ? item.id : null, barcode: item.barcode || '', quantity: item.qty, price: item.price };
    });

    var payload = {
      items: items,
      buyer_name: DOM.buyerName.value.trim() || 'Walk-in Customer',
      payment_method: selectedPayment,
      notes: DOM.notes.value.trim() || 'Transaksi AI POS',
    };

    WarungioAuth.api('/api/orders/pos/checkout/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    .then(function (res) { return res.json(); })
    .then(function (data) {
      document.body.removeChild(overlay);
      if (data.success) {
        showReceipt(data);
        addRecentTransaction(data);
        cart = [];
        renderCart();
        updatePayButton();
        DOM.cashAmount.value = '';
        DOM.changeRow.style.display = 'none';
        DOM.discountInput.value = '0';
        discountValue = 0;
        taxEnabled = false;
        DOM.taxCheckbox.checked = false;
        DOM.taxSwitch.querySelector('.pos-switch-track')?.classList.remove('active');
        updateTotals();
        showToast('✅ Pembayaran berhasil!', 'success');
        clearBboxOverlay();
      } else {
        var errMsg = data.error || (data.errors ? data.errors.map(function (e) { return e.error; }).join(', ') : 'Gagal');
        showToast('❌ ' + errMsg, 'error');
      }
    })
    .catch(function (err) {
      document.body.removeChild(overlay);
      showToast('Error: ' + (err.message || 'Koneksi gagal'), 'error');
    });
  }

  // ── Receipt ──
  function showReceipt(data) {
    var now = new Date();
    var items_html = cart.length > 0 ? cart.map(function (item) {
      return '<div class="receipt-item"><span>' + escapeHtml(item.name) + ' x' + item.qty + '</span><span>Rp ' + formatNumber(item.price * item.qty) + '</span></div>';
    }).join('') : '<div class="receipt-item"><span>Transaksi</span><span>Rp ' + formatNumber(parseTotal()) + '</span></div>';

    var total = parseTotal();
    var storeName = DOM.shopName.textContent || 'Warungio';
    var buyerName = DOM.buyerName.value.trim() || 'Walk-in Customer';

    DOM.receiptBody.innerHTML =
      '<div class="receipt-header">' +
      '<h2>' + escapeHtml(storeName) + '</h2>' +
      '<p>AI POS Kasir - Warungio</p>' +
      '<p>' + now.toLocaleDateString('id-ID') + ' ' + now.toLocaleTimeString('id-ID') + '</p>' +
      '<p>Pembeli: ' + escapeHtml(buyerName) + '</p>' +
      '</div>' +
      '<div class="receipt-divider"></div>' +
      '<div style="display:flex;justify-content:space-between;font-size:11px;font-weight:600;"><span>Item</span><span>Total</span></div>' +
      items_html +
      '<div class="receipt-divider"></div>' +
      '<div class="receipt-total"><span>Total</span><span>Rp ' + formatNumber(total) + '</span></div>' +
      '<div style="display:flex;justify-content:space-between;font-size:11px;padding:2px 0;">' +
      '<span>Metode: ' + selectedPayment.toUpperCase() + '</span>' +
      '<span>Biaya Admin: Rp ' + formatNumber(ADMIN_FEE) + '</span></div>' +
      (discountValue > 0 ? '<div style="display:flex;justify-content:space-between;font-size:11px;"><span>Diskon</span><span style="color:#ef4444;">- Rp ' + formatNumber(parseDiscount()) + '</span></div>' : '') +
      (taxEnabled ? '<div style="display:flex;justify-content:space-between;font-size:11px;"><span>PPN 11%</span><span>Rp ' + formatNumber(parseTax()) + '</span></div>' : '') +
      (selectedPayment === 'cash' && DOM.cashAmount.value ? '<div style="display:flex;justify-content:space-between;font-size:11px;"><span>Tunai: Rp ' + formatNumber(parseFloat(DOM.cashAmount.value)) + '</span>' +
      '<span style="color:#22c55e;">Kembali: Rp ' + formatNumber(parseFloat(DOM.cashAmount.value) - total) + '</span></div>' : '') +
      '<div class="receipt-divider"></div>' +
      '<div class="receipt-footer"><p>Terima kasih telah berbelanja!</p><p>Barang yang sudah dibeli tidak dapat ditukar</p></div>';

    openModal('receiptModal');
  }

  // ── Recent Transactions ──
  function loadRecentTransactions() {
    WarungioAuth.api('/api/orders/offline-sales/?limit=10')
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var sales = data.results || data || [];
        if (Array.isArray(sales) && sales.length > 0) {
          recentTransactions = sales;
          renderRecentTransactions(sales);
        }
      })
      .catch(function () {});
  }

  function renderRecentTransactions(sales) {
    DOM.recentBody.innerHTML = sales.slice(0, 10).map(function (s) {
      return '<div class="pos-recent-item">' +
        '<div><div>' + escapeHtml(s.product_name || 'Produk') + ' x' + (s.quantity != null ? s.quantity : 1) + '</div>' +
        '<div class="recent-method">' + (s.payment_method || 'cash').toUpperCase() + '</div></div>' +
        '<div><div class="recent-total">Rp ' + formatNumber(s.total || 0) + '</div>' +
        '<div class="recent-time">' + (s.created_at ? new Date(s.created_at).toLocaleTimeString('id-ID') : '') + '</div></div></div>';
    }).join('');
  }

  function addRecentTransaction(data) {
    (data.sales || []).forEach(function (s) { recentTransactions.unshift(s); });
    renderRecentTransactions(recentTransactions.slice(0, 10));
  }

  // ── Modal ──
  function openModal(id) { var el = document.getElementById(id); if (el) el.style.display = 'flex'; }
  function closeModal(id) { var el = document.getElementById(id); if (el) el.style.display = 'none'; }
  function closeAllModals() { document.querySelectorAll('.modal').forEach(function (m) { m.style.display = 'none'; }); }

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

  function formatNumber(n) {
    if (n == null) return '0';
    return Number(n).toLocaleString('id-ID');
  }

  function parseDiscount() {
    var sub = cart.reduce(function (sum, item) { return sum + (item.price * item.qty); }, 0);
    if (discountValue <= 0 || sub <= 0) return 0;
    return discountType === 'percent' ? sub * (Math.min(discountValue, 100) / 100) : Math.min(discountValue, sub);
  }

  function parseTax() {
    var sub = cart.reduce(function (sum, item) { return sum + (item.price * item.qty); }, 0);
    var discount = parseDiscount();
    return taxEnabled ? (sub - discount) * TAX_RATE : 0;
  }

  function showToast(msg, type, duration) {
    var d = duration || 3000;
    if (typeof window.showToast === 'function') {
      window.showToast(msg, type);
      // Fallback: manually dismiss if window.showToast doesn't respect duration
    } else {
      var t = document.getElementById('toast-notification');
      if (t) { t.textContent = msg; t.className = 'toast toast-' + (type || 'info'); t.style.display = 'block'; setTimeout(function () { t.style.display = 'none'; }, d); }
    }
  }

  function playScanSound() {
    try { var s = window.WarungioScanSound; if (s && typeof s.play === 'function') s.play(); } catch (e) {}
  }

  // Cleanup
  window.addEventListener('beforeunload', function () {
    if (stream) stream.getTracks().forEach(function (t) { t.stop(); });
    if (scanTimer) clearInterval(scanTimer);
  });

  window.clearCart = clearCart;
  window.processPayment = processPayment;

})();
