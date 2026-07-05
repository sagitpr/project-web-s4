/**
 * Checkout page - Warungio
 * Loads selected cart items, handles delivery form, payment, voucher, and place order.
 * Integrates Midtrans Snap popup for online payments.
 */
document.addEventListener('DOMContentLoaded', async () => {
  if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
    window.location.href = '/auth/login/?next=' + encodeURIComponent(window.location.pathname);
    return;
  }

  // ── Get selected items from URL ──
  const params = new URLSearchParams(window.location.search);
  const selectedIds = params.get('items') ? params.get('items').split(',').map(Number).filter(n => !isNaN(n)) : [];

  if (selectedIds.length === 0) {
    window.location.href = '/buyer/cart/';
    return;
  }

  // ── DOM refs ──
  const toast = document.getElementById('toast');
  const orderItemsEl = document.getElementById('orderItems');
  const checkoutSubtotal = document.getElementById('checkoutSubtotal');
  const checkoutTotal = document.getElementById('checkoutTotal');
  const checkoutDiscount = document.getElementById('checkoutDiscount');
  const discountLine = document.getElementById('discountLine');
  const placeOrderBtn = document.getElementById('placeOrderBtn');
  const voucherCode = document.getElementById('voucherCode');
  const checkVoucherBtn = document.getElementById('checkVoucherBtn');
  const voucherResult = document.getElementById('voucherResult');

  // Form fields
  const recipientName = document.getElementById('recipientName');
  const recipientPhone = document.getElementById('recipientPhone');
  const deliveryAddress = document.getElementById('deliveryAddress');
  const deliveryNote = document.getElementById('deliveryNote');

  let cartItems = [];
  let selectedPayment = 'midtrans';
  let voucherDiscount = 0;
  let voucherCodeApplied = '';
  let midtransClientKey = '';
  let snapScriptLoaded = false;

  function showToast(text, type) {
    // Delegate to shared utility — eliminates duplicate code
    if (window.WarungioAuthUI) {
      WarungioAuthUI.showToast(text, type || 'success');
      return;
    }
    // Fallback
    if (!toast) return;
    toast.textContent = text;
    toast.className = 'toast ' + (type || 'success');
    toast.classList.add('show');
    clearTimeout(toast._hide);
    toast._hide = setTimeout(() => toast.classList.remove('show'), 3000);
  }

  function toRupiah(num) {
    return 'Rp ' + Number(num).toLocaleString('id-ID');
  }

  function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ── Load Cart Items ──
  async function loadSelectedItems() {
    try {
      var data = await WarungioAPI.getCart();
      var allItems = data.results || data || [];
      cartItems = allItems.filter(function(item) { return selectedIds.indexOf(item.id) !== -1; });

      if (cartItems.length === 0) {
        showToast('Item tidak ditemukan di keranjang', 'error');
        setTimeout(function() { window.location.href = '/buyer/cart/'; }, 1500);
        return;
      }

      renderOrderItems(cartItems);
      updateTotals();
    } catch (err) {
      showToast('Gagal memuat data: ' + (err.message || 'Coba refresh'), 'error');
    }
  }

  function renderOrderItems(items) {
    orderItemsEl.innerHTML = '';
    items.forEach(function(item) {
      var photo = item.product_photo
        ? (item.product_photo.indexOf('http') === 0 ? '' : window.location.origin) + item.product_photo
        : WarungioAssets.img('vega-fresh.png');
      var name = item.product_name || 'Produk';
      var price = Number(item.product_price || item.price || 0);
      var qty = item.qty || 1;

      var div = document.createElement('div');
      div.className = 'order-item-sm';
      div.innerHTML =
        '<img src="' + photo + '" alt="' + escapeHtml(name) + '" loading="lazy">' +
        '<div class="item-info">' +
          '<p class="item-name">' + escapeHtml(name) + '</p>' +
          '<p class="item-meta">' + qty + ' x ' + toRupiah(price) + '</p>' +
        '</div>' +
        '<span class="item-price-sm">' + toRupiah(price * qty) + '</span>';
      orderItemsEl.appendChild(div);
    });
  }

  function getShippingFee() {
    var selectedRadio = document.querySelector('input[name="shipping"]:checked');
    if (!selectedRadio) return 0;
    var parentLabel = selectedRadio.closest('.shipping-option');
    if (parentLabel) {
      var feeEl = parentLabel.querySelector('.ship-fee');
      if (feeEl && !feeEl.classList.contains('free')) {
        var feeText = feeEl.textContent.replace(/[^0-9]/g, '');
        return parseInt(feeText) || 0;
      }
    }
    return 0;
  }

  function updateTotals() {
    var subtotal = cartItems.reduce(function(sum, i) {
      return sum + (Number(i.product_price || i.price || 0) * i.qty);
    }, 0);
    var shippingCost = getShippingFee();
    var total = Math.max(0, subtotal + shippingCost - voucherDiscount);
    checkoutSubtotal.textContent = toRupiah(subtotal);
    checkoutTotal.textContent = toRupiah(total);

    if (voucherDiscount > 0) {
      discountLine.style.display = 'flex';
      checkoutDiscount.textContent = '-' + toRupiah(voucherDiscount);
    } else {
      discountLine.style.display = 'none';
    }
  }

  // ── Shipping Method Icons ──
  function getShippingIcon(code) {
    const icons = {
      'gosend': '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
      'grabexpress': '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
      'maxim': '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
      'antar_sendiri': '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    };
    return icons[code] || '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/></svg>';
  }

  let selectedShipping = null;

  // ── Load Shipping Methods ──
  async function loadShippingMethods() {
    var container = document.getElementById('shippingMethods');
    var errorEl = document.getElementById('shippingError');
    if (!container) return;

    try {
      var data = await WarungioAPI.getShippingMethods();
      var methods = data.results || data || [];

      if (methods.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted);padding:12px;">Tidak ada metode pengiriman tersedia.</p>';
        return;
      }

      container.innerHTML = '';
      methods.forEach(function(m) {
        var label = document.createElement('label');
        label.className = 'shipping-option';
        if (!selectedShipping) selectedShipping = m.id;
        if (m.id === selectedShipping) label.classList.add('selected');

        label.innerHTML =
          '<input type="radio" name="shipping" value="' + m.id + '" ' + (m.id === selectedShipping ? 'checked' : '') + '>' +
          '<div class="ship-icon">' + getShippingIcon(m.code) + '</div>' +
          '<div class="ship-info">' +
            '<div class="ship-name">' + escapeHtml(m.name) + '</div>' +
            '<div class="ship-desc">' + escapeHtml(m.description || '') + '</div>' +
            '<div class="ship-meta">' +
              (m.base_fee > 0 ? '<span class="ship-fee">Rp ' + Number(m.base_fee).toLocaleString('id-ID') + '</span>' : '<span class="ship-fee free">Gratis</span>') +
              (m.estimated_time ? '<span class="ship-time">' + escapeHtml(m.estimated_time) + '</span>' : '') +
            '</div>' +
          '</div>';
        container.appendChild(label);
      });

      // Update shipping cost display
      updateShippingCost();
      bindShippingEvents();
      updateTotals();
    } catch (err) {
      console.warn('Shipping methods fallback:', err);
      if (errorEl) {
        errorEl.textContent = 'Gagal memuat metode pengiriman.';
        errorEl.style.display = 'block';
      }
    }
  }

  function updateShippingCost() {
    var shipEl = document.getElementById('checkoutShipping');
    if (!shipEl) return;
    if (!selectedShipping) {
      shipEl.textContent = '-';
      return;
    }
    // Look up the selected shipping method cost
    var allRadios = document.querySelectorAll('input[name="shipping"]');
    var selectedRadio = document.querySelector('input[name="shipping"]:checked');
    if (!selectedRadio) { shipEl.textContent = '-' ; return; }

    var parentLabel = selectedRadio.closest('.shipping-option');
    if (parentLabel) {
      var feeEl = parentLabel.querySelector('.ship-fee');
      if (feeEl) {
        shipEl.textContent = feeEl.textContent;
      }
    }
  }

  function bindShippingEvents() {
    document.querySelectorAll('input[name="shipping"]').forEach(function(input) {
      input.addEventListener('change', function() {
        selectedShipping = parseInt(this.value);
        document.querySelectorAll('.shipping-option').forEach(function(el) { el.classList.remove('selected'); });
        this.closest('.shipping-option').classList.add('selected');
        updateShippingCost();
        updateTotals();
      });
    });
  }

  // ── Load Payment Methods ──
  async function loadPaymentMethods() {
    var container = document.getElementById('paymentMethods');
    try {
      var data = await WarungioAPI.getPaymentMethods();
      var methods = data.results || data || [];

      if (methods.length === 0) {
        container.innerHTML = getDefaultPaymentHTML();
        bindPaymentEvents();
        return;
      }

      container.innerHTML = '';
      methods.forEach(function(m) {
        var label = document.createElement('label');
        label.className = 'payment-option' + (m.name === selectedPayment ? ' selected' : '');
        label.innerHTML =
          '<input type="radio" name="payment" value="' + escapeHtml(m.name) + '" ' + (m.name === selectedPayment ? 'checked' : '') + '>' +
          '<div class="pay-icon">' + getPaymentIcon(m.name) + '</div>' +
          '<div><div class="pay-label">' + escapeHtml(m.display_name || m.name) + '</div></div>';
        container.appendChild(label);
      });
      bindPaymentEvents();
    } catch (err) {
      console.warn('Payment methods fallback:', err);
      container.innerHTML = getDefaultPaymentHTML();
      bindPaymentEvents();
    }
  }

  function getDefaultPaymentHTML() {
    return '' +
      '<label class="payment-option' + (selectedPayment === 'midtrans' ? ' selected' : '') + '">' +
        '<input type="radio" name="payment" value="midtrans"' + (selectedPayment === 'midtrans' ? ' checked' : '') + '>' +
        '<div class="pay-icon">' + getPaymentIcon('midtrans') + '</div>' +
        '<div><div class="pay-label">Midtrans (Kartu, QRIS, e-Wallet)</div></div>' +
      '</label>' +
      '<label class="payment-option' + (selectedPayment === 'cod' ? ' selected' : '') + '">' +
        '<input type="radio" name="payment" value="cod"' + (selectedPayment === 'cod' ? ' checked' : '') + '>' +
        '<div class="pay-icon">' + getPaymentIcon('cod') + '</div>' +
        '<div><div class="pay-label">Bayar di Tempat (COD)</div></div>' +
      '</label>';
  }

  function getPaymentIcon(type) {
    if (type === 'cod' || type === 'cash') {
      return '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2"/></svg>';
    }
    return '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>';
  }

  function bindPaymentEvents() {
    document.querySelectorAll('input[name="payment"]').forEach(function(input) {
      input.addEventListener('change', function() {
        selectedPayment = this.value;
        document.querySelectorAll('.payment-option').forEach(function(el) { el.classList.remove('selected'); });
        this.closest('.payment-option').classList.add('selected');
      });
    });
  }

  // ── Voucher ──
  checkVoucherBtn.addEventListener('click', async function() {
    var code = voucherCode.value.trim();
    if (!code) {
      voucherResult.className = 'voucher-result error';
      voucherResult.textContent = 'Masukkan kode voucher';
      voucherResult.style.display = 'block';
      return;
    }

    checkVoucherBtn.disabled = true;
    checkVoucherBtn.textContent = 'Memeriksa...';
    voucherResult.style.display = 'none';

    try {
      var subtotal = cartItems.reduce(function(sum, i) { return sum + (Number(i.product_price || i.price || 0) * i.qty); }, 0);
      var data = await WarungioAPI.checkVoucher(code, subtotal);

      if (data.valid) {
        voucherDiscount = Number(data.discount) || 0;
        voucherCodeApplied = code;
        voucherResult.className = 'voucher-result success';
        voucherResult.textContent = 'Voucher berhasil! Diskon Rp ' + Number(data.discount).toLocaleString('id-ID');
        voucherResult.style.display = 'block';
        updateTotals();
        voucherCode.disabled = true;
      } else {
        voucherDiscount = 0;
        voucherCodeApplied = '';
        voucherResult.className = 'voucher-result error';
        voucherResult.textContent = data.error || 'Kode voucher tidak valid';
        voucherResult.style.display = 'block';
      }
    } catch (err) {
      voucherDiscount = 0;
      voucherCodeApplied = '';
      voucherResult.className = 'voucher-result error';
      voucherResult.textContent = err.message || 'Gagal memeriksa voucher';
      voucherResult.style.display = 'block';
    }

    checkVoucherBtn.disabled = false;
    checkVoucherBtn.textContent = 'Gunakan';
  });

  // ── Midtrans Snap Helpers ──

  /** Load Midtrans Snap JS library dynamically */
  function loadSnapScript(clientKey) {
    return new Promise(function(resolve, reject) {
      if (window.snap && window.snap.pay) {
        snapScriptLoaded = true;
        resolve();
        return;
      }
      var script = document.createElement('script');
      // Use the snap_js_url from payment config, fallback to sandbox
      var snapBaseUrl = window.WARUNGIO_SNAP_BASE_URL || 'https://app.sandbox.midtrans.com';
      script.src = snapBaseUrl + '/snap/snap.js';
      script.setAttribute('data-client-key', clientKey);
      script.onload = function() {
        snapScriptLoaded = true;
        resolve();
      };
      script.onerror = function() {
        reject(new Error('Gagal memuat Midtrans Snap. Coba refresh halaman.'));
      };
      document.head.appendChild(script);
    });
  }

  /** Open Midtrans Snap popup and handle response */
  function openSnapPopup(snapToken, orderId, orderNumber) {
    return new Promise(function(resolve) {
      if (!window.snap || !window.snap.pay) {
        resolve({ status: 'error', message: 'Midtrans Snap tidak tersedia.' });
        return;
      }

      window.snap.pay(snapToken, {
        onSuccess: function(result) {
          resolve({ status: 'success', orderId: orderId, orderNumber: orderNumber, result: result });
        },
        onPending: function(result) {
          resolve({ status: 'pending', orderId: orderId, orderNumber: orderNumber, result: result });
        },
        onError: function(result) {
          resolve({ status: 'error', message: result.status_message || 'Pembayaran gagal.', result: result });
        },
        onClose: function() {
          // Popup closed without finishing — check payment status
          resolve({ status: 'closed', orderId: orderId, orderNumber: orderNumber });
        }
      });
    });
  }

  // ── Place Order ──
  placeOrderBtn.addEventListener('click', async function() {
    // Validate form
    var name = recipientName.value.trim();
    var phone = recipientPhone.value.trim();
    var address = deliveryAddress.value.trim();

    if (!name) { showToast('Nama penerima harus diisi', 'error'); recipientName.focus(); return; }
    if (!phone) { showToast('Nomor HP harus diisi', 'error'); recipientPhone.focus(); return; }
    if (!address) { showToast('Alamat pengiriman harus diisi', 'error'); deliveryAddress.focus(); return; }

    placeOrderBtn.disabled = true;
    placeOrderBtn.textContent = 'Memproses...';

    try {
      // Get selected shipping method
      var shippingRadio = document.querySelector('input[name="shipping"]:checked');
      var shippingMethodId = shippingRadio ? parseInt(shippingRadio.value) : null;

      // Step 1: Create order
      var orderData = await WarungioAPI.createOrder({
        cart_items: selectedIds,
        shipping_method: shippingMethodId,
        delivery_address: address,
        recipient_name: name,
        recipient_phone: phone,
        notes: deliveryNote.value.trim(),
        payment_method: selectedPayment === 'cod' ? 'cod' : 'midtrans',
        vouchers: voucherCodeApplied ? [voucherCodeApplied] : [],
      });

      var orders = orderData.orders || [orderData];
      var orderIds = orders.map(function(o) { return o.id; });
      var orderNumbers = orders.map(function(o) { return o.order_number || '#' + o.id; });

      // Step 2: Handle payment method
      if (selectedPayment === 'midtrans' && orderIds.length > 0) {
        await handleMidtransPayment(orderIds[0], orderNumbers[0], orderIds, orderNumbers);
      } else {
        // COD — redirect to success
        window.location.href = '/buyer/order-success/' +
          '?orders=' + encodeURIComponent(orderIds.join(',')) +
          '&numbers=' + encodeURIComponent(orderNumbers.join(',')) +
          '&payment=cod';
      }
    } catch (err) {
      showToast(err.message || 'Gagal membuat pesanan. Coba lagi.', 'error');
      placeOrderBtn.disabled = false;
      placeOrderBtn.textContent = 'Buat Pesanan';
    }
  });

  /** Handle Midtrans payment flow: get Snap token, open popup, handle result */
  async function handleMidtransPayment(firstOrderId, firstOrderNumber, allOrderIds, allOrderNumbers) {
    placeOrderBtn.textContent = 'Menyiapkan pembayaran...';

    try {
      // STEP 1: Get Midtrans config from backend (client key + snap URL)
      // ⚠️  Client key HARUS dari backend! Jangan hardcode.
      try {
        var config = await WarungioAPI.getPaymentConfig();
        if (config) {
          if (config.client_key) midtransClientKey = config.client_key;
          // Set the correct Snap JS base URL from API config
          if (config.snap_js_url) {
            window.WARUNGIO_SNAP_BASE_URL = new URL(config.snap_js_url).origin;
          }
        }
      } catch (e) {
        console.error('Payment config fetch failed — cannot proceed:', e);
        showToast('Gagal memuat konfigurasi pembayaran.', 'error');
        return;
      }

      // STEP 2: Create Snap transaction — let Snap handle method selection
      placeOrderBtn.textContent = 'Membuat transaksi pembayaran...';
      var snapData = await WarungioAPI.createSnapTransaction(firstOrderId, 'credit_card');

      if (!snapData.token) {
        showToast('Gagal mendapatkan token pembayaran.', 'error');
        placeOrderBtn.disabled = false;
        placeOrderBtn.textContent = 'Buat Pesanan';
        return;
      }

      var snapToken = snapData.token;
      var redirectUrl = snapData.redirect_url || '';

      // STEP 3: Load Snap JS
      placeOrderBtn.textContent = 'Membuka popup pembayaran...';
      await loadSnapScript(midtransClientKey);

      // STEP 4: Open Snap popup — with fallback to redirect if popup blocked
      if (window.snap && window.snap.pay) {
        var result = await openSnapPopup(snapToken, firstOrderId, firstOrderNumber);

        if (result.status === 'success') {
          redirectToSuccess(allOrderIds, allOrderNumbers, 'success');
        } else if (result.status === 'pending') {
          redirectToSuccess(allOrderIds, allOrderNumbers, 'pending');
        } else if (result.status === 'closed') {
          showToast('Pembayaran dibatalkan. Pesanan tetap tersimpan.', 'error');
          window.location.href = '/buyer/orders/';
        } else {
          showToast(result.message || 'Pembayaran gagal. Silakan coba lagi.', 'error');
          placeOrderBtn.disabled = false;
          placeOrderBtn.textContent = 'Buat Pesanan';
        }
      } else if (redirectUrl) {
        // Fallback: popup gagal dibuka (blocker) — redirect ke halaman Midtrans
        window.location.href = redirectUrl;
      } else {
        showToast('Popup pembayaran tidak dapat dibuka. Periksa popup blocker Anda.', 'error');
        placeOrderBtn.disabled = false;
        placeOrderBtn.textContent = 'Buat Pesanan';
      }
    } catch (err) {
      showToast(err.message || 'Gagal memproses pembayaran. Coba lagi.', 'error');
      placeOrderBtn.disabled = false;
      placeOrderBtn.textContent = 'Buat Pesanan';
    }
  }

  /** Helper: redirect to order-success page with params */
  function redirectToSuccess(allOrderIds, allOrderNumbers, status) {
    window.location.href = '/buyer/order-success/' +
      '?orders=' + encodeURIComponent(allOrderIds.join(',')) +
      '&numbers=' + encodeURIComponent(allOrderNumbers.join(',')) +
      '&payment=midtrans&status=' + status;
  }

  // ── Pre-fill user data ──
  function prefillUserData() {
    try {
      var user = window.WarungioAuth.getUser();
      if (user) {
        if (user.full_name && !recipientName.value) recipientName.value = user.full_name;
        if (user.phone && !recipientPhone.value) recipientPhone.value = user.phone;
        if (user.address && !deliveryAddress.value) deliveryAddress.value = user.address;
      }
    } catch (e) { /* silent */ }
  }

  // ── Init ──
  prefillUserData();
  await Promise.all([loadSelectedItems(), loadShippingMethods(), loadPaymentMethods()]);
});
