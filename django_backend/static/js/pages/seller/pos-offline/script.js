/* ── Smart POS Offline — Warungio Seller ── */
(function () {
  'use strict';

  // ── State ──
  let cart = [];
  let stream = null;
  let selectedPayment = 'cash';
  let recentTransactions = [];

  const ADMIN_FEE_RP = 1500; // Biaya admin per transaksi

  // ── DOM Cache ──
  const DOM = {
    video: document.getElementById('posVideoFeed'),
    placeholder: document.getElementById('posPlaceholder'),
    cartItems: document.getElementById('posCartItems'),
    cartEmpty: document.getElementById('posCartEmpty'),
    cartSummary: document.getElementById('posCartSummary'),
    subtotal: document.getElementById('posSubtotal'),
    adminFee: document.getElementById('posAdminFee'),
    discount: document.getElementById('posDiscount'),
    total: document.getElementById('posTotal'),
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
    productSearch: document.getElementById('posProductSearch'),
    searchResults: document.getElementById('posSearchResults'),
    quickList: document.getElementById('posQuickList'),
    shopName: document.getElementById('shopName'),
    shopId: document.getElementById('shopId'),
    profileName: document.getElementById('profileName'),
    profileAvatar: document.getElementById('profileAvatar'),
    posModeCamera: document.getElementById('posModeCamera'),
    posModeBarcode: document.getElementById('posModeBarcode'),
    posModeManual: document.getElementById('posModeManual'),
    manualSearch: document.getElementById('posManualSearch'),
    btnStart: document.getElementById('posBtnStart'),
    btnStop: document.getElementById('posBtnStop'),
    btnScanBarcode: document.getElementById('posBtnScanBarcode'),
  };

  // ── Auth Guard ──
  if (!WarungioAuth || !WarungioAuth.isAuthenticated()) {
    window.location.href = '/auth/login/';
    return;
  }

  // ── QR Scanner integration ──
  var currentDeliveryOrderId = null;

  window.scanQRForDelivery = function (orderId) {
    currentDeliveryOrderId = orderId || null;
    var modal = document.getElementById('qrScannerModal');
    if (modal && typeof openQRScanner === 'function') {
      openQRScanner(function (qrData) {
        // QR scanned — verify against backend
        var orderIdToUse = currentDeliveryOrderId || qrData.order_id || qrData.orderId || qrData.id;
        if (!orderIdToUse) {
          showToast('QR tidak mengandung order_id. Gunakan manual.', 'error');
          return;
        }
        WarungioAuth.api('/api/orders/' + orderIdToUse + '/delivery/qr/verify/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ qr_data: JSON.stringify(qrData), order_id: orderIdToUse }),
        })
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (data.success || data.verified) {
            showToast('✅ QR terverifikasi! Status: ' + (data.delivery_status || 'OK'), 'success');
            loadRecentTransactions();
          } else {
            showToast('❌ Verifikasi gagal: ' + (data.error || 'QR tidak valid'), 'error');
          }
        })
        .catch(function (err) {
          showToast('Error verifikasi: ' + (err.message || 'Gagal koneksi'), 'error');
        });
      }, { mode: 'delivery' });
    } else {
      showToast('QR Scanner tidak tersedia', 'error');
    }
  };

  // ── Init ──
  document.addEventListener('DOMContentLoaded', function () {
    WarungioAuthUI?.init({ syncBalance: false, syncCart: false });
    loadProfile();
    initEventListeners();
    loadRecentTransactions();
    loadQuickProducts();
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

  function initEventListeners() {
    // Camera
    DOM.btnStart.addEventListener('click', startPOSCamera);
    DOM.btnStop.addEventListener('click', stopPOSCamera);
    DOM.btnScanBarcode.addEventListener('click', scanBarcodeFromCamera);

    // Mode switching
    DOM.posModeCamera.addEventListener('click', function () { setPOSMode('camera'); });
    DOM.posModeBarcode.addEventListener('click', function () { setPOSMode('barcode'); });
    DOM.posModeManual.addEventListener('click', function () { setPOSMode('manual'); });

    // Cart
    DOM.clearCart.addEventListener('click', clearCart);
    DOM.payBtn.addEventListener('click', processPayment);

    // Payment method selection
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

    // Cash amount input
    DOM.cashAmount.addEventListener('input', updateChange);

    // Product search
    DOM.productSearch.addEventListener('input', debounce(function () {
      var q = DOM.productSearch.value.trim();
      if (q.length >= 2) searchProducts(q);
      else DOM.searchResults.innerHTML = '';
    }, 300));

    // Receipt actions
    DOM.btnPrint.addEventListener('click', function () { window.print(); });
    DOM.btnNewTx.addEventListener('click', function () {
      closeModal('receiptModal');
      clearCart();
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', function (e) {
      if (e.key === 'F2') { e.preventDefault(); processPayment(); }
      if (e.key === 'F8') { e.preventDefault(); DOM.clearCart.click(); }
      if (e.key === 'Escape') { closeAllModals(); }
    });
  }

  function setPOSMode(mode) {
    [DOM.posModeCamera, DOM.posModeBarcode, DOM.posModeManual].forEach(function (btn) {
      btn.className = 'btn-sm btn-secondary';
    });
    if (mode === 'camera') { DOM.posModeCamera.className = 'btn-sm btn-primary'; stopPOSCamera(); startPOSCamera(); }
    else if (mode === 'barcode') { DOM.posModeBarcode.className = 'btn-sm btn-primary'; stopPOSCamera(); startPOSCamera(); }
    else if (mode === 'manual') {
      DOM.posModeManual.className = 'btn-sm btn-primary';
      stopPOSCamera();
      DOM.manualSearch.style.display = 'block';
    }
    if (mode !== 'manual') DOM.manualSearch.style.display = 'none';
  }

  // ── Camera ──
  function startPOSCamera() {
    if (stream) return;
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      showToast('Browser tidak mendukung kamera', 'error');
      return;
    }
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment', width: { ideal: 640 }, height: { ideal: 480 } } })
      .then(function (s) {
        stream = s;
        DOM.video.srcObject = s;
        DOM.video.style.display = 'block';
        DOM.placeholder.style.display = 'none';
        DOM.btnStart.style.display = 'none';
        DOM.btnStop.style.display = 'inline-flex';
        DOM.btnScanBarcode.style.display = 'inline-flex';
        showToast('Kamera aktif. Arahkan ke barcode produk.', 'success');
      })
      .catch(function (err) {
        showToast('Gagal akses kamera: ' + err.message, 'error');
      });
  }

  function stopPOSCamera() {
    if (stream) { stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; }
    DOM.video.style.display = 'none';
    DOM.placeholder.style.display = 'flex';
    DOM.btnStart.style.display = 'inline-flex';
    DOM.btnStop.style.display = 'none';
    DOM.btnScanBarcode.style.display = 'none';
  }

  function scanBarcodeFromCamera() {
    if (!stream || !DOM.video.videoWidth) return;
    var c = document.createElement('canvas');
    c.width = DOM.video.videoWidth;
    c.height = DOM.video.videoHeight;
    var ctx = c.getContext('2d');
    ctx.drawImage(DOM.video, 0, 0);
    var imageData = c.toDataURL('image/jpeg', 0.8);

    if (typeof Quagga !== 'undefined') {
      Quagga.decodeSingle({
        src: imageData,
        numOfWorkers: 1,
        inputStream: { size: 800 },
        decoder: { readers: ['ean_reader', 'ean_8_reader', 'upc_reader', 'code_128_reader'] },
        locate: true,
      }, function (result) {
        if (result && result.codeResult) {
          var barcode = result.codeResult.code;
          showToast('Barcode: ' + barcode, 'success');
          lookupAndAddToCart(barcode);
          playScanSound();
        } else {
          showToast('Barcode tidak terdeteksi. Coba lagi.', 'error');
        }
      });
    } else {
      // Fallback: simulate barcode scan
      showToast('Library barcode tidak tersedia. Gunakan mode Manual.', 'info');
    }
  }

  // ── Product Lookup ──
  // ── Barcode → Product cache untuk auto-increment pada re-scan ──
  var barcodeProductCache = {};

  function lookupAndAddToCart(barcode) {
    // Check cache first untuk instant add
    if (barcodeProductCache[barcode]) {
      var cached = barcodeProductCache[barcode];
      addToCart(cached, null, barcode);
      return;
    }

    WarungioAuth.api('/api/inventory/barcode-lookup/?barcode=' + encodeURIComponent(barcode))
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.found && data.master_product) {
          var mp = data.master_product;
          // Cari produk di toko dengan nama
          return WarungioAPI.getProducts({ search: mp.product_name, limit: 5 })
            .then(function (products) {
              var product = products.results ? products.results[0] : null;
              if (product) {
                // Cache barcode → product untuk re-scan auto-increment
                barcodeProductCache[barcode] = product;
                addToCart(product, mp, barcode);
              } else {
                showToast('Produk tidak ditemukan di toko. Tambahkan dulu.', 'error');
              }
            });
        } else {
          showToast('Barcode tidak dikenal: ' + barcode, 'error');
        }
      })
      .catch(function () {
        showToast('Gagal lookup barcode', 'error');
      });
  }

  function searchProducts(q) {
    WarungioAPI.getProducts({ search: q, limit: 8 })
      .then(function (data) {
        var products = data.results || [];
        if (products.length === 0) {
          DOM.searchResults.innerHTML = '<div style="padding:12px;font-size:12px;color:#94a3b8;text-align:center;">Produk tidak ditemukan</div>';
          return;
        }
        DOM.searchResults.innerHTML = products.map(function (p) {
          return '<div class="pos-search-result" data-id="' + p.id + '" data-name="' + escapeHtml(p.product_name) + '" data-price="' + p.price + '" data-stock="' + (p.available_stock || p.stock || 0) + '">' +
            '<span class="result-name">' + escapeHtml(p.product_name) + '</span>' +
            '<span class="result-price">Rp ' + formatNumber(p.price) + '</span></div>';
        }).join('');
        DOM.searchResults.querySelectorAll('.pos-search-result').forEach(function (el) {
          el.addEventListener('click', function () {
            addToCart({
              id: parseInt(this.dataset.id),
              product_name: this.dataset.name,
              price: parseFloat(this.dataset.price),
              stock: parseInt(this.dataset.stock),
            });
            DOM.productSearch.value = '';
            DOM.searchResults.innerHTML = '';
          });
        });
      })
      .catch(function () {});
  }

  // ── Cart ──
  function addToCart(product, masterProduct, barcode) {
    var productId = product.id;
    var existing = cart.find(function (item) { return item.id === productId; });
    if (existing) {
      if (existing.qty < (product.available_stock || product.stock || 999)) {
        existing.qty++;
        playScanSound();
        showToast(product.product_name + ' (x' + existing.qty + ') ditambahkan', 'success');
      } else {
        showToast('Stok tidak mencukupi!', 'error');
        return;
      }
    } else {
      cart.push({
        id: productId,
        name: product.product_name || masterProduct?.product_name || 'Produk',
        price: parseFloat(product.price) || 0,
        qty: 1,
        maxStock: product.available_stock || product.stock || 999,
        barcode: barcode || '',
      });
      playScanSound();
    }
    renderCart();
    updatePayButton();
  }

  function removeFromCart(id) {
    cart = cart.filter(function (item) { return item.id !== id; });
    renderCart();
    updatePayButton();
  }

  function updateCartQty(id, delta) {
    var item = cart.find(function (i) { return i.id === id; });
    if (!item) return;
    var newQty = item.qty + delta;
    if (newQty <= 0) { removeFromCart(id); return; }
    if (newQty > item.maxStock) { showToast('Stok maksimal: ' + item.maxStock, 'error'); return; }
    item.qty = newQty;
    renderCart();
  }

  function clearCart() {
    cart = [];
    renderCart();
    updatePayButton();
    DOM.buyerName.value = '';
    DOM.notes.value = '';
    DOM.cashAmount.value = '';
    DOM.changeRow.style.display = 'none';
    showToast('Keranjang dikosongkan', 'info');
  }

  function renderCart() {
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
      return '<div class="pos-cart-item">' +
        '<div class="pos-cart-item-name">' + escapeHtml(item.name) + '</div>' +
        '<div class="pos-cart-item-qty">' +
        '<button onclick="window.updateCartQty(' + item.id + ', -1)"><i class="fa-solid fa-minus"></i></button>' +
        '<span class="item-qty">' + item.qty + '</span>' +
        '<button onclick="window.updateCartQty(' + item.id + ', 1)"><i class="fa-solid fa-plus"></i></button>' +
        '</div>' +
        '<div class="pos-cart-item-price">Rp ' + formatNumber(subtotal) + '</div>' +
        '<span class="pos-cart-item-remove" onclick="window.removeFromCart(' + item.id + ')"><i class="fa-solid fa-trash-can"></i></span>' +
        '</div>';
    }).join('');

    updateTotals();
  }

  function updateTotals() {
    var subtotal = cart.reduce(function (sum, item) { return sum + (item.price * item.qty); }, 0);
    var adminFee = subtotal > 0 ? ADMIN_FEE_RP : 0;
    var total = subtotal + adminFee;
    DOM.subtotal.textContent = 'Rp ' + formatNumber(subtotal);
    DOM.adminFee.textContent = 'Rp ' + formatNumber(adminFee);
    DOM.total.textContent = 'Rp ' + formatNumber(total);
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
    var subtotal = cart.reduce(function (sum, item) { return sum + (item.price * item.qty); }, 0);
    return subtotal + (subtotal > 0 ? ADMIN_FEE_RP : 0);
  }

  // Expose cart helpers globally for inline onclick
  window.addToCart = addToCart;
  window.removeFromCart = removeFromCart;
  window.updateCartQty = updateCartQty;

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

    // Show processing overlay
    var overlay = document.createElement('div');
    overlay.className = 'pos-processing-overlay';
    overlay.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i><p>Memproses pembayaran...</p>';
    document.body.appendChild(overlay);

    // Prepare payload
    var items = cart.map(function (item) {
      return { barcode: '', product_id: item.id, quantity: item.qty };
    });

    // Try to get barcodes from API
    var barcodePromises = cart.map(function (item) {
      return WarungioAuth.api('/api/inventory/master-products/?q=' + encodeURIComponent(item.name))
        .then(function (r) { return r.json(); })
        .then(function (data) {
          var mp = data.results && data.results[0];
          return { id: item.id, barcode: mp?.barcode || '', quantity: item.qty, price: item.price };
        })
        .catch(function () {
          return { id: item.id, barcode: '', quantity: item.qty, price: item.price };
        });
    });

    Promise.all(barcodePromises).then(function (payloadItems) {
      var payload = {
        items: payloadItems.map(function (pi) {
          return { barcode: pi.barcode || '', product_id: pi.id, quantity: pi.quantity };
        }),
        buyer_name: DOM.buyerName.value.trim() || '',
        payment_method: selectedPayment,
        notes: DOM.notes.value.trim() || '',
      };

      // Send to POS API
      return WarungioAuth.api('/api/orders/pos/checkout/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    }).then(function (res) {
      return res.json();
    }).then(function (data) {
      document.body.removeChild(overlay);

      if (data.success || data.sales?.length > 0) {
        showReceipt(data);
        addRecentTransaction(data);
        cart = [];
        renderCart();
        updatePayButton();
        DOM.cashAmount.value = '';
        DOM.changeRow.style.display = 'none';
        showToast('Pembayaran berhasil!', 'success');
      } else {
        var errMsg = data.errors ? data.errors.map(function (e) { return e.error; }).join(', ') : 'Gagal memproses pembayaran';
        showToast(errMsg, 'error');
      }
    }).catch(function (err) {
      document.body.removeChild(overlay);
      showToast('Error: ' + (err.message || 'Gagal koneksi'), 'error');
    });
  }

  // ── Receipt ──
  function showReceipt(data) {
    var sales = data.sales || [];
    var now = new Date();
    var items_html = cart.length > 0 ? cart.map(function (item) {
      return '<div class="receipt-item"><span>' + escapeHtml(item.name) + ' x' + item.qty + '</span><span>Rp ' + formatNumber(item.price * item.qty) + '</span></div>';
    }).join('') : (data.sales || []).map(function (sale) {
      return '<div class="receipt-item"><span>' + escapeHtml(sale.product_name || 'Produk') + ' x' + (sale.quantity || 1) + '</span><span>Rp ' + formatNumber(sale.total || 0) + '</span></div>';
    }).join('');

    var total = parseTotal() || (data.total_amount || 0);
    var storeName = document.getElementById('shopName')?.textContent || 'Warungio';
    var buyerName = DOM.buyerName.value.trim() || 'Walk-in Customer';

    DOM.receiptBody.innerHTML =
      '<div class="receipt-header">' +
      '<h2>' + escapeHtml(storeName) + '</h2>' +
      '<p>POS Offline - Warungio</p>' +
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
      '<span>Biaya Admin: Rp ' + formatNumber(ADMIN_FEE_RP) + '</span></div>' +
      (selectedPayment === 'cash' && DOM.cashAmount.value ? '<div style="display:flex;justify-content:space-between;font-size:11px;padding:2px 0;"><span>Tunai</span><span>Rp ' + formatNumber(parseFloat(DOM.cashAmount.value)) + '</span></div>' : '') +
      (selectedPayment === 'cash' && DOM.cashAmount.value && parseFloat(DOM.cashAmount.value) >= total ? '<div style="display:flex;justify-content:space-between;font-size:11px;padding:2px 0;color:#22c55e;"><span>Kembalian</span><span>Rp ' + formatNumber(parseFloat(DOM.cashAmount.value) - total) + '</span></div>' : '') +
      '<div class="receipt-divider"></div>' +
      '<div class="receipt-footer">' +
      '<p>Terima kasih telah berbelanja!</p>' +
      '<p>Barang yang sudah dibeli tidak dapat ditukar/kembali</p>' +
      '</div>';

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
        '<div><div>' + escapeHtml(s.product_name || 'Produk') + ' x' + (s.quantity || 1) + '</div>' +
        '<div class="recent-method">' + (s.payment_method || 'cash').toUpperCase() + '</div></div>' +
        '<div><div class="recent-total">Rp ' + formatNumber(s.total || 0) + '</div>' +
        '<div class="recent-time">' + (s.created_at ? new Date(s.created_at).toLocaleTimeString('id-ID') : '') + '</div></div></div>';
    }).join('');
  }

  function addRecentTransaction(data) {
    var sales = data.sales || [];
    sales.forEach(function (s) {
      recentTransactions.unshift(s);
    });
    renderRecentTransactions(recentTransactions.slice(0, 10));
  }

  // ── Quick Products ──
  function loadQuickProducts() {
    WarungioAPI.getProducts({ limit: 12, ordering: '-total_sold' })
      .then(function (data) {
        var products = data.results || [];
        if (products.length > 0) {
          DOM.quickList.innerHTML = products.map(function (p) {
            return '<span class="pos-quick-item" data-id="' + p.id + '" data-name="' + escapeHtml(p.product_name) + '" data-price="' + p.price + '" data-stock="' + (p.available_stock || p.stock || 0) + '">' +
              escapeHtml(p.product_name.substring(0, 20)) + '</span>';
          }).join('');
          DOM.quickList.querySelectorAll('.pos-quick-item').forEach(function (el) {
            el.addEventListener('click', function () {
              addToCart({
                id: parseInt(this.dataset.id),
                product_name: this.dataset.name,
                price: parseFloat(this.dataset.price),
                stock: parseInt(this.dataset.stock),
              });
            });
          });
        }
      })
      .catch(function () {});
  }

  // ── Modal ──
  function openModal(id) {
    var el = document.getElementById(id);
    if (el) { el.style.display = 'flex'; }
  }
  function closeModal(id) {
    var el = document.getElementById(id);
    if (el) { el.style.display = 'none'; }
  }
  function closeAllModals() {
    document.querySelectorAll('.modal').forEach(function (m) { m.style.display = 'none'; });
  }

  // ── Helpers ──
  function escapeHtml(s) {
    if (!s) return '';
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/'/g, '&#39;').replace(/"/g, '&#34;');
  }

  function formatNumber(n) {
    if (n === null || n === undefined) return '0';
    return Number(n).toLocaleString('id-ID');
  }

  function debounce(fn, ms) {
    var timer;
    return function () {
      var args = arguments;
      var ctx = this;
      clearTimeout(timer);
      timer = setTimeout(function () { fn.apply(ctx, args); }, ms);
    };
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

  // Cleanup
  window.addEventListener('beforeunload', function () {
    if (stream) stream.getTracks().forEach(function (t) { t.stop(); });
  });

  // Expose to window for inline handlers
  window.clearCart = clearCart;
  window.processPayment = processPayment;

})();
