/**
 * Warungio Seller — Order Detail Page
 * Loads order details, manages status updates with hyperlocal delivery flow,
 * and provides real-time delivery tracking for sellers.
 */
(function () {
  'use strict';

  var auth = window.WarungioAuth;
  var API = window.WarungioAPI;

  if (!auth || !auth.isAuthenticated()) {
    window.location.href = '/?next=' + encodeURIComponent(window.location.pathname + window.location.search);
    return;
  }

  /* ── Helpers ── */
  function $(id) { return document.getElementById(id); }

  function toRupiah(num) {
    return 'Rp ' + Number(num).toLocaleString('id-ID');
  }

  function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
      var d = new Date(dateStr);
      return d.toLocaleDateString('id-ID', {
        day: 'numeric', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      });
    } catch (e) {
      return dateStr;
    }
  }

  function showToast(msg, type) {
    if (window.WarungioToast) {
      WarungioToast.show(msg, type || 'success');
      return;
    }
    var t = document.createElement('div');
    t.className = 'toast-notification';
    t.textContent = msg;
    if (type === 'error') t.style.background = '#DC2626';
    else t.style.background = '#16A34A';
    document.body.appendChild(t);
    setTimeout(function () { t.classList.add('show'); }, 50);
    setTimeout(function () {
      t.classList.remove('show');
      setTimeout(function () { t.remove(); }, 300);
    }, 4000);
  }

  /* ── Modal ── */
  function openModal(id) { var el = $(id); if (el) el.style.display = 'flex'; }
  function closeModal(id) { var el = $(id); if (el) el.style.display = 'none'; }

  /* ── Constants ── */
  var STATUS_LABELS = {
    'pending': 'Menunggu', 'paid': 'Lunas', 'processed': 'Diproses',
    'ready_pickup': 'Siap Diambil', 'courier_pickup': 'Kurir Menjemput',
    'on_delivery': 'Dalam Perjalanan', 'shipped': 'Dikirim',
    'completed': 'Pesanan Diterima', 'cancelled': 'Dibatalkan', 'refunded': 'Dikembalikan',
  };

  var STATUS_CLASSES = {
    'pending': 'status-pending', 'paid': 'status-paid', 'processed': 'status-processed',
    'ready_pickup': 'status-ready', 'courier_pickup': 'status-courier',
    'on_delivery': 'status-shipped', 'shipped': 'status-shipped',
    'completed': 'status-completed', 'cancelled': 'status-cancelled', 'refunded': 'status-refunded',
  };

  var DELIVERY_STATUS_LABELS = {
    'menunggu_konfirmasi': 'Menunggu Konfirmasi', 'diproses_penjual': 'Diproses Penjual',
    'menunggu_penjemputan': 'Menunggu Penjemputan', 'kurir_menjemput': 'Kurir Menjemput',
    'dalam_perjalanan': 'Dalam Perjalanan', 'pesanan_diterima': 'Pesanan Diterima', 'dibatalkan': 'Dibatalkan',
  };

  /* ── Order Data ── */
  var orderId = null;
  var orderData = null;

  /* ── Load Order ── */
  function loadOrder() {
    var params = new URLSearchParams(window.location.search);
    orderId = params.get('id');
    if (!orderId) {
      showError('ID pesanan tidak ditemukan.');
      return;
    }

    if (!API || typeof API.getOrder !== 'function') {
      showError('API tidak tersedia.');
      return;
    }

    API.getOrder(orderId).then(function (order) {
      if (!order || order.id === undefined) {
        showError('Pesanan tidak ditemukan.');
        return;
      }
      orderData = order;
      renderOrder(order);
    }).catch(function (err) {
      showError(err.message || 'Gagal memuat pesanan.');
    });
  }

  function showError(msg) {
    var loading = $('loadingOverlay');
    var errorEl = $('errorState');
    var errorMsg = $('errorMessage');
    if (loading) loading.style.display = 'none';
    if (errorEl) {
      errorEl.style.display = 'flex';
      if (errorMsg) errorMsg.textContent = msg || 'Pesanan tidak ditemukan.';
    }
  }

  /* ── Render Order ── */
  function renderOrder(order) {
    var loading = $('loadingOverlay');
    var content = $('orderContent');
    if (loading) loading.style.display = 'none';
    if (content) content.style.display = 'block';

    // Header
    var orderNumEl = $('orderNumber');
    var statusBadge = $('statusBadge');
    if (orderNumEl) orderNumEl.textContent = order.order_number || '#' + order.id;
    var statusKey = (order.order_status || 'pending').toLowerCase();
    if (statusBadge) {
      statusBadge.textContent = STATUS_LABELS[statusKey] || statusKey;
      statusBadge.className = 'status-badge ' + (STATUS_CLASSES[statusKey] || 'status-pending');
    }

    // Store info
    var storeName = $('storeName');
    var storeAvatar = $('storeAvatar');
    if (storeName) storeName.textContent = order.store_name || 'Warung';
    if (storeAvatar) storeAvatar.textContent = (order.store_name || 'T').charAt(0).toUpperCase();

    // Items
    renderItems(order.items);

    // Delivery info
    renderDeliveryInfo(order);

    // Payment info
    renderPaymentInfo(order);

    // Summary
    renderSummary(order);

    // Title
    document.title = (order.order_number || '#' + order.id) + ' - Detail Pesanan - Warungio';

    // Update status buttons
    renderStatusActions(order);
  }

  function renderItems(items) {
    var container = $('itemsList');
    if (!container) return;
    if (!items || items.length === 0) {
      container.innerHTML = '<p style="color:var(--text-muted);font-size:0.9rem;padding:12px 0;">Tidak ada item.</p>';
      return;
    }
    container.innerHTML = '';
    items.forEach(function (item) {
      var div = document.createElement('div');
      div.className = 'order-item';
      var imgSrc = item.product_photo || '';
      div.innerHTML =
        '<img src="' + imgSrc + '" alt="' + escapeHtml(item.product_name) + '" class="item-image" loading="lazy" onerror="this.style.display=\'none\'">' +
        '<div class="item-body">' +
          '<p class="item-name">' + escapeHtml(item.product_name) + '</p>' +
          '<p class="item-meta">' + item.qty + ' x ' + toRupiah(item.price) + '</p>' +
        '</div>' +
        '<span class="item-total">' + toRupiah(item.subtotal) + '</span>';
      container.appendChild(div);
    });
  }

  function renderDeliveryInfo(order) {
    var delivery = order.delivery || {};
    $('deliveryAddress').textContent = order.delivery_address || '-';
    $('recipientName').textContent = order.recipient_name || order.user_name || '-';
    $('recipientPhone').textContent = order.recipient_phone || '-';

    var courierName = delivery.shipping_method_name || order.shipping_method_name || delivery.courier_name || order.courier || '';
    if (courierName) {
      $('courierRow').style.display = 'flex';
      $('courierName').textContent = courierName;
    }
    if (delivery.delivery_status && DELIVERY_STATUS_LABELS[delivery.delivery_status]) {
      var dsEl = document.getElementById('currentDeliveryStatus');
      if (!dsEl) {
        var row = document.createElement('div');
        row.className = 'info-row';
        row.id = 'currentDeliveryStatusRow';
        row.innerHTML = '<span class="info-label">Status Pengiriman</span><span class="info-value" id="currentDeliveryStatus">' + DELIVERY_STATUS_LABELS[delivery.delivery_status] + '</span>';
        var grid = document.querySelector('.info-grid');
        if (grid) grid.insertBefore(row, grid.firstChild);
      } else {
        dsEl.textContent = DELIVERY_STATUS_LABELS[delivery.delivery_status];
      }
    }
  }

  function renderPaymentInfo(order) {
    var payLabels = { 'midtrans': 'Midtrans', 'cod': 'COD', 'transfer': 'Transfer Bank' };
    $('paymentMethod').textContent = payLabels[order.payment_method] || order.payment_method || '-';
    var payStatus = order.payment_status || 'pending';
    $('paymentStatusText').textContent = payStatus === 'paid' ? 'Lunas' : payStatus === 'pending' ? 'Menunggu Pembayaran' : payStatus;
  }

  function renderSummary(order) {
    $('summarySubtotal').textContent = toRupiah(order.subtotal || 0);
    $('summaryShipping').textContent = toRupiah(order.shipping_cost || 0);
    if (order.discount && Number(order.discount) > 0) {
      $('summaryDiscountRow').style.display = 'flex';
      $('summaryDiscount').textContent = '-' + toRupiah(order.discount);
    }
    $('summaryTotal').textContent = toRupiah(order.total_price || 0);
  }

  function renderStatusActions(order) {
    var container = $('statusActions');
    if (!container) return;
    container.innerHTML = '';

    var status = (order.order_status || '').toLowerCase();
    var validTransitions = [];

    // Define valid transitions based on current status
    if (status === 'pending' || status === 'paid') {
      validTransitions.push({ status: 'processed', label: 'Proses Pesanan', icon: 'check', color: 'primary' });
      validTransitions.push({ status: 'cancelled', label: 'Batalkan', icon: 'x', color: 'danger' });
    } else if (status === 'processed') {
      validTransitions.push({ status: 'ready_pickup', label: 'Siap Diambil Kurir', icon: 'clock', color: 'primary' });
      validTransitions.push({ status: 'cancelled', label: 'Batalkan', icon: 'x', color: 'danger' });
    } else if (status === 'ready_pickup') {
      validTransitions.push({ status: 'on_delivery', label: 'Kirim (Dalam Perjalanan)', icon: 'truck', color: 'primary' });
      validTransitions.push({ status: 'cancelled', label: 'Batalkan', icon: 'x', color: 'danger' });
    } else if (status === 'on_delivery') {
      validTransitions.push({ status: 'completed', label: 'Tandai Selesai', icon: 'check', color: 'primary' });
    }
    // completed, cancelled, refunded — no actions

    validTransitions.forEach(function (t) {
      var btn = document.createElement('button');
      btn.className = 'btn-status-action btn-' + t.color;
      btn.innerHTML = (t.icon === 'x' ? '&times; ' : '&#10003; ') + t.label;
      btn.addEventListener('click', function () {
        if (t.status === 'cancelled') {
          openCancelModal();
        } else {
          updateOrderStatus(t.status);
        }
      });
      container.appendChild(btn);
    });
  }

  function updateOrderStatus(newStatus) {
    var data = { status: newStatus };
    if (!API || typeof API.updateOrderStatus !== 'function') {
      showToast('Fungsi API tidak tersedia.', 'error');
      return;
    }
    API.updateOrderStatus(orderId, newStatus).then(function (res) {
      showToast('Status berhasil diubah: ' + (STATUS_LABELS[newStatus] || newStatus), 'success');
      setTimeout(function () { window.location.reload(); }, 1500);
    }).catch(function (err) {
      showToast(err.message || 'Gagal mengubah status.', 'error');
    });
  }

  /* ── Cancel Order Modal ── */
  function openCancelModal() {
    openModal('cancelModal');
  }

  function initCancelModal() {
    var closeBtn = $('cancelModalClose');
    var dismissBtn = $('cancelDismissBtn');
    var confirmBtn = $('cancelConfirmBtn');
    var reasonText = $('cancelReasonText');

    if (closeBtn) closeBtn.addEventListener('click', function () { closeModal('cancelModal'); });
    if (dismissBtn) dismissBtn.addEventListener('click', function () { closeModal('cancelModal'); });

    var modal = $('cancelModal');
    if (modal) modal.addEventListener('click', function (e) {
      if (e.target === modal) closeModal('cancelModal');
    });

    if (confirmBtn) {
      confirmBtn.addEventListener('click', function () {
        var selectedReason = document.querySelector('input[name="cancelReason"]:checked');
        var reason = selectedReason ? selectedReason.value : '';
        var reasonTextVal = reasonText ? reasonText.value.trim() : '';

        var data = { status: 'cancelled' };
        if (reason) data.cancel_reason = reason;
        if (reasonTextVal) data.cancel_reason_text = reasonTextVal;

        confirmBtn.disabled = true;
        var btnText = $('cancelBtnText');
        var btnLoading = $('cancelBtnLoading');
        if (btnText) btnText.style.display = 'none';
        if (btnLoading) btnLoading.style.display = 'inline';

        API.updateOrderStatus(orderId, data).then(function () {
          showToast('Pesanan berhasil dibatalkan.', 'success');
          closeModal('cancelModal');
          setTimeout(function () { window.location.reload(); }, 1500);
        }).catch(function (err) {
          showToast(err.message || 'Gagal membatalkan pesanan.', 'error');
          confirmBtn.disabled = false;
          if (btnText) btnText.style.display = 'inline';
          if (btnLoading) btnLoading.style.display = 'none';
        });
      });
    }
  }

  /* ── WebSocket Realtime Tracking ── */
  function initRealtimeOrderTracking() {
    var _wsRetries = 0;
    var _wsMaxRetries = 10;

    function trySetup() {
      if (_wsRetries >= _wsMaxRetries) return;
      if (typeof WarungioWS === 'undefined' || typeof WarungioWS.on !== 'function') {
        _wsRetries++;
        setTimeout(trySetup, 1000);
        return;
      }

      // Delivery update → reload order detail when status changes
      WarungioWS.on('delivery_update', function (data) {
        if (!data.order_id) return;
        if (!orderId || Number(data.order_id) !== Number(orderId)) return;
        // Silently reload order data without full page refresh
        API.getOrder(orderId).then(function (order) {
          if (!order || order.id === undefined) return;
          orderData = order;
          // Re-render only the changed sections
          var oldStatus = document.getElementById('statusBadge');
          var newStatusKey = (order.order_status || '').toLowerCase();
          if (oldStatus) {
            oldStatus.textContent = STATUS_LABELS[newStatusKey] || newStatusKey;
            oldStatus.className = 'status-badge ' + (STATUS_CLASSES[newStatusKey] || 'status-pending');
          }
          renderItems(order.items);
          renderDeliveryInfo(order);
          renderPaymentInfo(order);
          renderSummary(order);
          renderStatusActions(order);
          showToast(data.message || 'Status pesanan berubah: ' + (DELIVERY_STATUS_LABELS[data.delivery_status] || data.delivery_status), 'success');
        }).catch(function () {});
      });

      // Order update (cancelled) → reload
      WarungioWS.on('order_update', function (data) {
        if (!data.order_id) return;
        if (!orderId || Number(data.order_id) !== Number(orderId)) return;
        if (data.status === 'cancelled' || data.status === 'completed') {
          showToast('Status pesanan berubah: ' + (STATUS_LABELS[data.status] || data.status), 'info');
          setTimeout(function () { window.location.reload(); }, 2000);
        }
      });

      // Payment update → reload if paid
      WarungioWS.on('payment_update', function (data) {
        if (!data.order_id) return;
        if (!orderId || Number(data.order_id) !== Number(orderId)) return;
        if (data.status === 'settlement' || data.status === 'paid') {
          showToast('Pembayaran telah diterima!', 'success');
          setTimeout(function () { window.location.reload(); }, 1500);
        }
      });
    }
    trySetup();
  }

  /* ── QR Code Generation & Display ── */
  var qrDeliveryCode = null;
  var qrPickupCode = null;

  /* ── Proof of Delivery (POD) Section ── */
  function renderPODSection(order) {
    var container = $('order-detail-content');
    if (!container) return;
    var delivery = order.delivery || {};

    // Remove existing POD section
    var existingPOD = $('podSection');
    if (existingPOD) existingPOD.remove();

    var podSection = document.createElement('div');
    podSection.className = 'qr-section';
    podSection.id = 'podSection';

    var hasPOD = delivery.pod_photo || delivery.pod_signature;
    var podPhotoUrl = delivery.pod_photo || '';
    var podSignedAt = delivery.pod_signed_at ? formatDate(delivery.pod_signed_at) : '';

    podSection.innerHTML = '<h3><i class="fa-solid fa-check-circle"></i> Bukti Pengiriman (POD)</h3>' +
      (hasPOD ?
        '<div class="pod-display">' +
          (podPhotoUrl ? '<div class="pod-photo"><img src="' + podPhotoUrl + '" alt="POD Photo" style="max-width:200px;border-radius:8px;border:1px solid #e2e8f0;" /></div>' : '') +
          (delivery.pod_signature ? '<div class="pod-signature"><strong>Tanda Tangan:</strong><pre style="font-size:18px;letter-spacing:2px;">' + escapeHtml(delivery.pod_signature) + '</pre></div>' : '') +
          (podSignedAt ? '<div class="pod-time"><strong>Waktu:</strong> ' + podSignedAt + '</div>' : '') +
          (delivery.pod_notes ? '<div class="pod-notes"><strong>Catatan:</strong> ' + escapeHtml(delivery.pod_notes) + '</div>' : '') +
        '</div>'
        : '<p style="color:#64748b;font-size:14px;">Belum ada bukti pengiriman (POD).</p>') +
      '<div class="pod-upload-form" style="margin-top:12px;padding-top:12px;border-top:1px solid #e2e8f0;">' +
        '<div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;">' +
          '<div style="flex:1;min-width:200px;">' +
            '<label style="display:block;font-size:12px;font-weight:600;color:#475569;margin-bottom:4px;">Foto Bukti</label>' +
            '<input type="file" id="podPhotoInput" accept="image/*" style="font-size:13px;" />' +
          '</div>' +
          '<div style="flex:1;min-width:200px;">' +
            '<label style="display:block;font-size:12px;font-weight:600;color:#475569;margin-bottom:4px;">Catatan</label>' +
            '<input type="text" id="podNotesInput" placeholder="Catatan pengiriman..." style="padding:8px 12px;border:1px solid #e2e8f0;border-radius:8px;font-size:13px;width:100%;" />' +
          '</div>' +
          '<button class="btn btn-primary" id="uploadPODBtn" style="margin-top:20px;"><i class="fa-solid fa-upload"></i> Upload POD</button>' +
        '</div>' +
      '</div>';

    container.appendChild(podSection);

    var uploadBtn = $('uploadPODBtn');
    if (uploadBtn) {
      uploadBtn.addEventListener('click', function() { uploadPOD(order.id); });
    }
  }

  async function uploadPOD(orderId) {
    var photoInput = $('podPhotoInput');
    var notesInput = $('podNotesInput');
    var btn = $('uploadPODBtn');

    if (!photoInput || !photoInput.files || !photoInput.files[0]) {
      showToast('Pilih foto bukti pengiriman terlebih dahulu.', 'error');
      return;
    }

    if (btn) { btn.disabled = true; btn.innerHTML = 'Mengupload...'; }

    try {
      var fd = new FormData();
      fd.append('pod_photo', photoInput.files[0]);
      if (notesInput && notesInput.value.trim()) {
        fd.append('pod_notes', notesInput.value.trim());
      }
      var res = await API.uploadPOD(orderId, fd);
      showToast('Bukti pengiriman berhasil diupload!', 'success');
      setTimeout(function() { loadOrder(); }, 1500);
    } catch (e) {
      showToast(e.message || 'Gagal upload POD', 'error');
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-upload"></i> Upload POD'; }
    }
  }

  /* ── Camera QR Scanner ── */
  var html5QrScanner = null;

  function renderQRScanner(order) {
    var container = $('order-detail-content');
    if (!container) return;
    // Only show scanner if order has delivery
    if (!order || !order.delivery) return;

    var existingScanner = $('qrScannerSection');
    if (existingScanner) existingScanner.remove();

    var scannerSection = document.createElement('div');
    scannerSection.className = 'qr-section';
    scannerSection.id = 'qrScannerSection';

    scannerSection.innerHTML = '<h3><i class="fa-solid fa-camera"></i> Scan QR Code (Kamera)</h3>' +
      '<div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:12px;">' +
        '<button class="btn btn-outline" id="startScannerBtn"><i class="fa-solid fa-camera"></i> Buka Kamera</button>' +
        '<button class="btn btn-outline" id="stopScannerBtn" style="display:none;"><i class="fa-solid fa-stop"></i> Tutup Kamera</button>' +
      '</div>' +
      '<div id="qrScannerContainer" style="width:100%;max-width:400px;margin:0 auto;display:none;"></div>' +
      '<div id="qrScannerResult" style="margin-top:8px;font-size:14px;color:#64748b;"></div>';

    container.appendChild(scannerSection);

    var startBtn = $('startScannerBtn');
    var stopBtn = $('stopScannerBtn');
    var scannerContainer = $('qrScannerContainer');

    if (startBtn) {
      startBtn.addEventListener('click', function() {
        startBtn.style.display = 'none';
        stopBtn.style.display = 'inline-flex';
        scannerContainer.style.display = 'block';
        startQRScanner();
      });
    }

    if (stopBtn) {
      stopBtn.addEventListener('click', function() {
        stopQRScanner();
        startBtn.style.display = 'inline-flex';
        stopBtn.style.display = 'none';
        scannerContainer.style.display = 'none';
      });
    }
  }

  function startQRScanner() {
    if (typeof Html5Qrcode === 'undefined') {
      showToast('Library QR Scanner tidak tersedia.', 'error');
      return;
    }

    var resultDiv = $('qrScannerResult');
    var scannerContainer = $('qrScannerContainer');
    if (!scannerContainer) return;

    if (html5QrScanner) {
      html5QrScanner.stop().catch(function() {});
      html5QrScanner.clear();
    }

    html5QrScanner = new Html5Qrcode('qrScannerContainer');

    html5QrScanner.start(
      { facingMode: 'environment' },
      {
        fps: 10,
        qrbox: { width: 250, height: 250 },
      },
      function(qrCodeMessage) {
        // On QR decode success
        if (resultDiv) {
          resultDiv.innerHTML = 'QR terdeteksi: <strong>' + escapeHtml(qrCodeMessage) + '</strong>';
        }
        // Auto-verify if we have an order
        if (orderId && qrCodeMessage) {
          // Determine code type from prefix
          var codeType = 'delivery';
          if (qrCodeMessage.indexOf('WRG-PICKUP-') === 0 || qrCodeMessage.indexOf('WRG-PICKP-') === 0) {
            codeType = 'pickup';
          }
          // Auto-verify
          verifyQRFromScanner(orderId, qrCodeMessage, codeType);
        }
        // Stop scanner after successful scan
        stopQRScanner();
      },
      function(errorMessage) {
        // Ignore continuous scanning errors
      }
    ).catch(function(err) {
      showToast('Gagal mengakses kamera: ' + err, 'error');
      var startBtn = $('startScannerBtn');
      var stopBtn = $('stopScannerBtn');
      if (startBtn) startBtn.style.display = 'inline-flex';
      if (stopBtn) stopBtn.style.display = 'none';
      if (scannerContainer) scannerContainer.style.display = 'none';
    });
  }

  function stopQRScanner() {
    if (html5QrScanner) {
      try {
        html5QrScanner.stop().catch(function() {});
        html5QrScanner.clear();
      } catch (e) {}
      html5QrScanner = null;
    }
  }

  async function verifyQRFromScanner(orderId, qrCode, codeType) {
    var btn = $('verifyQrBtn');
    showToast('QR terdeteksi! Memverifikasi...', 'info');
    try {
      var res = await API.verifyDeliveryQR(orderId, qrCode, codeType);
      showToast(res.message || 'QR berhasil diverifikasi!', 'success');
      setTimeout(function() { loadOrder(); }, 1500);
    } catch (e) {
      showToast(e.message || 'Verifikasi QR gagal.', 'error');
    }
  }

  function renderQRCard(order) {
    var container = $('order-detail-content');
    if (!container) return;

    // Remove existing QR section to prevent duplication
    var existingQr = $('qrSection');
    if (existingQr) existingQr.remove();

    var delivery = order.delivery || {};
    var status = delivery.delivery_status || order.order_status || '';
    qrDeliveryCode = delivery.qr_delivery_code || null;
    qrPickupCode = delivery.qr_pickup_code || null;

    var pickupCode = delivery.pickup_code || '';
    var otpCode = delivery.pickup_code || ''; // OTP = pickup_code for verification

    var qrSection = document.createElement('div');
    qrSection.className = 'qr-section';
    qrSection.id = 'qrSection';

    var deliveryQrHtml = qrDeliveryCode
      ? '<div class="qr-display" id="deliveryQrDisplay"><div class="qr-img" id="deliveryQrImg"></div><div class="qr-info"><div class="qr-label">QR Delivery</div><div class="qr-code-text">' + escapeHtml(qrDeliveryCode) + '</div><span class="qr-status active">Aktif</span></div></div>'
      : '<div class="qr-display" id="deliveryQrDisplay" style="display:none;"></div>';

    var pickupQrHtml = qrPickupCode
      ? '<div class="qr-display" id="pickupQrDisplay"><div class="qr-img" id="pickupQrImg"></div><div class="qr-info"><div class="qr-label">QR Pickup</div><div class="qr-code-text">' + escapeHtml(qrPickupCode) + '</div><span class="qr-status active">Aktif</span></div></div>'
      : '<div class="qr-display" id="pickupQrDisplay" style="display:none;"></div>';

    qrSection.innerHTML = '<h3><i class="fa-solid fa-qrcode"></i> Verifikasi QR & Pengiriman</h3>' +
      '<div class="qr-actions">' +
        '<button class="btn btn-primary" id="generateDeliveryQRBtn"><i class="fa-solid fa-qrcode"></i> Generate QR Delivery</button>' +
        '<button class="btn btn-outline" id="generatePickupQRBtn"><i class="fa-solid fa-box"></i> Generate QR Pickup</button>' +
        '<button class="btn btn-outline" id="refreshQrBtn"><i class="fa-solid fa-rotate"></i> Refresh</button>' +
        (qrDeliveryCode ? '<button class="btn btn-outline" id="printQrBtn"><i class="fa-solid fa-print"></i> Print</button>' : '') +
        '<button class="btn btn-outline" id="downloadQrBtn"><i class="fa-solid fa-download"></i> Download</button>' +
      '</div>' +
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">' +
        '<div><h4 style="font-size:13px;color:#64748b;margin-bottom:8px;">QR Delivery</h4>' + deliveryQrHtml + '</div>' +
        '<div><h4 style="font-size:13px;color:#64748b;margin-bottom:8px;">QR Pickup</h4>' + pickupQrHtml + '</div>' +
      '</div>' +
      (pickupCode ? '<div class="pickup-code-display"><div><div style="font-size:12px;color:#166534;font-weight:600;">Kode Pickup</div><div class="code">' + escapeHtml(pickupCode) + '</div></div></div>' : '') +
      (otpCode ? '<div class="otp-section"><div class="otp-label">OTP Verifikasi</div><div class="otp-value">' + escapeHtml(otpCode) + '</div><div style="font-size:11px;color:#9a3412;">Bagikan OTP ini ke driver untuk verifikasi pengiriman.</div></div>' : '') +
      '<div class="verify-qr-row">' +
        '<input type="text" id="verifyQrInput" placeholder="Masukkan kode QR dari pembeli...">' +
        '<select id="verifyQrType" style="padding:10px;border:1px solid #e2e8f0;border-radius:10px;font-size:13px;">' +
          '<option value="delivery">Delivery</option>' +
          '<option value="pickup">Pickup</option>' +
        '</select>' +
        '<button class="btn btn-primary" id="verifyQrBtn"><i class="fa-solid fa-check"></i> Verifikasi</button>' +
      '</div>';

    container.appendChild(qrSection);

    // Render QR images
    if (qrDeliveryCode) renderQRImage('deliveryQrImg', qrDeliveryCode);
    if (qrPickupCode) renderQRImage('pickupQrImg', qrPickupCode);

    // Attach events
    $('generateDeliveryQRBtn')?.addEventListener('click', function() { generateQR(order.id, 'delivery'); });
    $('generatePickupQRBtn')?.addEventListener('click', function() { generateQR(order.id, 'pickup'); });
    $('refreshQrBtn')?.addEventListener('click', function() { loadOrder(); });
    $('printQrBtn')?.addEventListener('click', printQR);
    $('downloadQrBtn')?.addEventListener('click', downloadQR);
    $('verifyQrBtn')?.addEventListener('click', function() { verifyQR(order.id); });
  }

  function renderQRImage(containerId, code) {
    var el = $(containerId);
    if (!el || typeof QRCode === 'undefined') return;
    el.innerHTML = '';
    new QRCode(el, { text: code, width: 100, height: 100, colorDark: '#1e293b', colorLight: '#ffffff', correctLevel: QRCode.CorrectLevel.H });
  }

  async function generateQR(orderId, codeType) {
    var btn = $(codeType === 'delivery' ? 'generateDeliveryQRBtn' : 'generatePickupQRBtn');
    if (btn) { btn.disabled = true; btn.innerHTML = 'Memproses...'; }
    try {
      var res = await API.generateDeliveryQR(orderId, codeType);
      showToast('QR ' + (codeType === 'delivery' ? 'Delivery' : 'Pickup') + ' berhasil dibuat!', 'success');
      setTimeout(function() { loadOrder(); }, 1000);
    } catch (e) {
      showToast(e.message || 'Gagal generate QR', 'error');
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-qrcode"></i> Generate QR ' + (codeType === 'delivery' ? 'Delivery' : 'Pickup'); }
    }
  }

  async function verifyQR(orderId) {
    var input = $('verifyQrInput');
    var typeSelect = $('verifyQrType');
    var btn = $('verifyQrBtn');
    if (!input || !input.value.trim()) { showToast('Masukkan kode QR terlebih dahulu.', 'error'); return; }
    if (btn) { btn.disabled = true; btn.innerHTML = 'Memverifikasi...'; }
    try {
      var res = await API.verifyDeliveryQR(orderId, input.value.trim(), typeSelect ? typeSelect.value : 'delivery');
      showToast(res.message || 'QR berhasil diverifikasi!', 'success');
      setTimeout(function() { loadOrder(); }, 1500);
    } catch (e) {
      showToast(e.message || 'Verifikasi gagal.', 'error');
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-check"></i> Verifikasi'; }
    }
  }

  function printQR() {
    var content = document.getElementById('qrSection');
    if (!content) return;
    var win = window.open('', '_blank');
    win.document.write('<html><head><title>QR Code - Warungio</title><style>body{font-family:sans-serif;padding:20px;text-align:center;}img{max-width:200px;}</style></head><body>');
    win.document.write('<h2>QR Code Pengiriman</h2>');
    var qrImgs = content.querySelectorAll('.qr-img canvas');
    qrImgs.forEach(function(c) { win.document.write(c.toDataURL ? '<img src="' + c.toDataURL() + '" style="margin:10px;">' : ''); });
    win.document.write('</body></html>');
    win.print();
  }

  function downloadQR() {
    var qrImgs = document.querySelectorAll('.qr-img canvas');
    qrImgs.forEach(function(c, i) {
      if (c.toDataURL) {
        var link = document.createElement('a');
        link.download = 'warungio-qr-' + (i === 0 ? 'delivery' : 'pickup') + '.png';
        link.href = c.toDataURL('image/png');
        link.click();
      }
    });
  }

  /* ── Override renderOrder to add QR + POD + Scanner after main render ── */
  var _origRenderOrder = renderOrder;
  renderOrder = function(order) {
    _origRenderOrder(order);
    renderQRCard(order);
    renderPODSection(order);
    renderQRScanner(order);
  };

  /* ── Init ── */
  document.addEventListener('DOMContentLoaded', function () {
    initCancelModal();
    loadOrder();
    initRealtimeOrderTracking();

    // Stop camera when leaving page
    window.addEventListener('beforeunload', stopQRScanner);
    window.addEventListener('pagehide', stopQRScanner);
  });
})();
