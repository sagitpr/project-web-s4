/**
 * Seller Order Detail page - Warungio
 * Loads order detail, renders timeline/buyer/items, manages status updates.
 * Actions: Proses → Kirim (modal) → Selesai.
 */
document.addEventListener('DOMContentLoaded', async () => {
  if (window.WarungioAuth && window.WarungioAuth.requireVerified && window.WarungioAuth.requireVerified()) {
    return;
  }

  // ── Get order ID from URL ──
  const params = new URLSearchParams(window.location.search);
  const orderId = params.get('id');

  if (!orderId) {
    showError('ID pesanan tidak ditemukan.');
    return;
  }

  // ── DOM refs ──
  const loadingEl = document.getElementById('loadingOverlay');
  const errorEl = document.getElementById('errorState');
  const errorMsg = document.getElementById('errorMessage');
  const orderNumberEl = document.getElementById('orderNumber');
  const statusBadge = document.getElementById('statusBadge');
  const actionsContainer = document.getElementById('actionButtons');

  let orderData = null;

  function $(id) { return document.getElementById(id); }

  function toRupiah(num) {
    return 'Rp ' + Number(num).toLocaleString('id-ID');
  }

  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function showError(msg) {
    if (loadingEl) loadingEl.style.display = 'none';
    if (errorEl) {
      errorEl.style.display = 'flex';
      if (errorMsg) errorMsg.textContent = msg || 'Pesanan tidak ditemukan.';
    }
  }

  function showToast(message, type) {
    var toast = document.createElement('div');
    toast.className = 'toast-notification';
    if (type === 'error') toast.style.background = '#DC2626';
    else if (type === 'success') toast.style.background = '#16A34A';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(function () { toast.classList.add('show'); }, 50);
    setTimeout(function () {
      toast.classList.remove('show');
      setTimeout(function () { toast.remove(); }, 300);
    }, 4000);
  }

  // ── Hyperlocal Status helpers ──
  // Map order_status (from backend) to human-readable labels and CSS classes
  const STATUS_LABELS = {
    'pending': 'Menunggu Konfirmasi',
    'paid': 'Lunas',
    'processed': 'Diproses Penjual',
    'ready_pickup': 'Siap Diambil Kurir',
    'courier_pickup': 'Kurir Menjemput',
    'on_delivery': 'Dalam Perjalanan',
    'completed': 'Pesanan Diterima',
    'cancelled': 'Dibatalkan',
    'refunded': 'Dikembalikan',
  };

  const STATUS_CLASSES = {
    'pending': 'status-pending',
    'paid': 'status-paid',
    'processed': 'status-processed',
    'ready_pickup': 'status-ready',
    'courier_pickup': 'status-courier',
    'on_delivery': 'status-shipped',
    'completed': 'status-completed',
    'cancelled': 'status-cancelled',
    'refunded': 'status-refunded',
  };

  const PAYMENT_LABELS = {
    'midtrans': 'Midtrans',
    'cod': 'Bayar di Tempat (COD)',
    'transfer': 'Transfer Bank',
  };

  // Hyperlocal delivery timeline:
  // Step 1: Pesanan Dibuat (pending/paid)
  // Step 2: Diproses Penjual (processed)
  // Step 3: Siap Diambil Kurir (ready_pickup)
  // Step 4: Dalam Perjalanan (courier_pickup / on_delivery)
  // Step 5: Selesai (completed)
  function getActiveSteps(order) {
    var s = (order.order_status || 'pending').toLowerCase();
    if (s === 'completed')      return [1, 2, 3, 4, 5];
    if (s === 'on_delivery')    return [1, 2, 3, 4];
    if (s === 'courier_pickup') return [1, 2, 3, 4];
    if (s === 'ready_pickup')   return [1, 2, 3];
    if (s === 'processed')      return [1, 2];
    if (s === 'paid')           return [1, 2];
    if (s === 'cancelled')      return [1];
    if (s === 'refunded')       return [1, 2];
    return [1];
  }

  function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
      var d = new Date(dateStr);
      return d.toLocaleDateString('id-ID', {
        day: 'numeric', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      });
    } catch (e) { return dateStr; }
  }

  // ── Translate order_status for display in status-based UI ──
  // The backend stores order_status as: pending, processed, ready_pickup, courier_pickup, on_delivery, completed, cancelled
  function getNextAction(statusKey) {
    var flow = {
      'pending':      { next: 'processed',     label: 'Proses Pesanan',    icon: 'check',         cls: 'btn-info' },
      'paid':         { next: 'processed',     label: 'Proses Pesanan',    icon: 'check',         cls: 'btn-info' },
      'processed':    { next: 'ready_pickup',  label: 'Siap Diambil Kurir', icon: 'box-open',    cls: 'btn-warning' },
      'ready_pickup': { next: 'courier_pickup', label: 'Kurir Sudah Menjemput', icon: 'motorcycle', cls: 'btn-primary' },
      'courier_pickup': { next: 'on_delivery', label: 'Dalam Perjalanan',  icon: 'truck',         cls: 'btn-info' },
      'on_delivery':  { next: 'completed',      label: 'Pesanan Tiba',      icon: 'check-circle',  cls: 'btn-success' },
    };
    return flow[statusKey] || null;
  }

  // ── Which statuses allow cancellation ──
  function canCancel(statusKey) {
    return ['pending', 'paid', 'processed', 'ready_pickup'].includes(statusKey);
  }

  // ── Render actions based on status ──
  function renderActions(statusKey) {
    if (!actionsContainer) return;

    // Keep the back-to-dashboard link
    actionsContainer.innerHTML = '<a href="../dashboard/index.html" class="btn btn-outline"><i class="fa-solid fa-arrow-left"></i> Dashboard</a>';

    var nextAction = getNextAction(statusKey);

    if (nextAction) {
      var btn = document.createElement('button');
      btn.className = 'btn ' + nextAction.cls;
      btn.innerHTML = '<i class="fa-solid fa-' + nextAction.icon + '"></i> ' + nextAction.label;

      btn.addEventListener('click', function () {
        var nextStatus = nextAction.next;

        if (nextStatus === 'ready_pickup') {
          // Open ready-for-pickup modal: just a simple confirm
          if (!confirm('Tandai pesanan ini sebagai Siap Diambil Kurir?')) return;
          btn.disabled = true;
          btn.textContent = 'Menyimpan...';
          WarungioAPI.updateOrderStatus(orderId, 'ready_pickup')
            .then(function () {
              showToast('Pesanan siap dijemput kurir.', 'success');
              setTimeout(function () { window.location.reload(); }, 1200);
            })
            .catch(function (err) {
              showToast(err.message || 'Gagal memperbarui status.', 'error');
              btn.disabled = false;
              btn.innerHTML = '<i class="fa-solid fa-box-open"></i> Siap Diambil Kurir';
            });
        } else if (nextStatus === 'courier_pickup') {
          // Open courier pickup modal — input driver info
          openDriverModal();
        } else if (nextStatus === 'on_delivery') {
          // Open in-transit modal — input tracking if available
          openTransitModal();
        } else if (nextStatus === 'completed') {
          if (!confirm('Konfirmasi pesanan sudah tiba? Pembeli akan mendapat notifikasi.')) return;
          btn.disabled = true;
          btn.textContent = 'Menyelesaikan...';
          WarungioAPI.updateOrderStatus(orderId, 'completed')
            .then(function () {
              showToast('Pesanan selesai.', 'success');
              setTimeout(function () { window.location.reload(); }, 1200);
            })
            .catch(function (err) {
              showToast(err.message || 'Gagal menyelesaikan pesanan.', 'error');
              btn.disabled = false;
              btn.innerHTML = '<i class="fa-solid fa-check-circle"></i> Pesanan Tiba';
            });
        } else {
          // Simple status update (e.g., processed)
          btn.disabled = true;
          btn.textContent = 'Memproses...';
          WarungioAPI.updateOrderStatus(orderId, nextStatus)
            .then(function () {
              var msgs = { 'processed': 'Pesanan sedang diproses.' };
              showToast(msgs[nextStatus] || 'Status berhasil diperbarui.', 'success');
              setTimeout(function () { window.location.reload(); }, 1200);
            })
            .catch(function (err) {
              showToast(err.message || 'Gagal memperbarui status.', 'error');
              btn.disabled = false;
              btn.innerHTML = '<i class="fa-solid fa-' + nextAction.icon + '"></i> ' + nextAction.label;
            });
        }
      });
      actionsContainer.appendChild(btn);
    }

    // ── Cancel button (for cancellable statuses) ──
    if (canCancel(statusKey)) {
      var wrapper = document.createElement('div');
      wrapper.className = 'btn-cancel-wrapper';
      var cancelBtn = document.createElement('button');
      cancelBtn.className = 'btn btn-outline-danger';
      cancelBtn.innerHTML = '<i class="fa-solid fa-ban"></i> Batalkan Pesanan';
      cancelBtn.addEventListener('click', function () {
        openCancelModal();
      });
      wrapper.appendChild(cancelBtn);
      actionsContainer.appendChild(wrapper);
    }
  }

  // ── Cancel Modal Logic ──
  var cancelModal = document.getElementById('cancelModal');
  var cancelModalClose = document.getElementById('cancelModalClose');
  var cancelDismissBtn = document.getElementById('cancelDismissBtn');
  var cancelConfirmBtn = document.getElementById('cancelConfirmBtn');
  var cancelReason = document.getElementById('cancelReason');
  var cancelReasonText = document.getElementById('cancelReasonText');
  var cancelBtnText = document.getElementById('cancelBtnText');
  var cancelBtnLoading = document.getElementById('cancelBtnLoading');

  function openCancelModal() {
    if (!cancelModal) return;
    cancelModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    // Reset form
    if (cancelReason) cancelReason.value = '';
    if (cancelReasonText) cancelReasonText.value = '';
    if (cancelConfirmBtn) cancelConfirmBtn.disabled = false;
    if (cancelBtnText) cancelBtnText.style.display = 'inline';
    if (cancelBtnLoading) cancelBtnLoading.style.display = 'none';
  }

  function closeCancelModal() {
    if (!cancelModal) return;
    cancelModal.style.display = 'none';
    document.body.style.overflow = '';
  }

  cancelModalClose?.addEventListener('click', closeCancelModal);
  cancelDismissBtn?.addEventListener('click', closeCancelModal);
  cancelModal?.addEventListener('click', function (e) {
    if (e.target === cancelModal) closeCancelModal();
  });

  cancelConfirmBtn?.addEventListener('click', async function () {
    var reason = cancelReason ? cancelReason.value : '';
    var reasonText = cancelReasonText ? cancelReasonText.value.trim() : '';

    if (!reason) {
      showToast('Silakan pilih alasan pembatalan.', 'error');
      return;
    }

    // Double confirm
    if (!confirm('Apakah Anda yakin ingin membatalkan pesanan ini? Tindakan ini akan mengembalikan stok produk.')) {
      return;
    }

    // Loading state
    if (cancelConfirmBtn) cancelConfirmBtn.disabled = true;
    if (cancelBtnText) cancelBtnText.style.display = 'none';
    if (cancelBtnLoading) cancelBtnLoading.style.display = 'inline';

    try {
      await WarungioAPI.updateOrderStatus(orderId, 'cancelled', '', '', reason, reasonText);
      showToast('Pesanan berhasil dibatalkan.', 'success');
      closeCancelModal();
      setTimeout(function () { window.location.reload(); }, 1200);
    } catch (err) {
      showToast(err.message || 'Gagal membatalkan pesanan.', 'error');
      if (cancelConfirmBtn) cancelConfirmBtn.disabled = false;
      if (cancelBtnText) cancelBtnText.style.display = 'inline';
      if (cancelBtnLoading) cancelBtnLoading.style.display = 'none';
    }
  });

  // ── Driver Modal Logic (Kurir Menjemput) ──
  var driverModal = document.getElementById('driverModal');
  var driverModalClose = document.getElementById('driverModalClose');
  var driverDismissBtn = document.getElementById('driverDismissBtn');
  var driverConfirmBtn = document.getElementById('driverConfirmBtn');
  var driverNameInput = document.getElementById('driverNameInput');
  var driverPhoneInput = document.getElementById('driverPhoneInput');
  var pickupCodeInput = document.getElementById('pickupCodeInput');
  var driverBtnText = document.getElementById('driverBtnText');
  var driverBtnLoading = document.getElementById('driverBtnLoading');

  function openDriverModal() {
    if (!driverModal) return;
    driverModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    if (driverNameInput) driverNameInput.value = '';
    if (driverPhoneInput) driverPhoneInput.value = '';
    if (pickupCodeInput) pickupCodeInput.value = '';
    if (driverConfirmBtn) driverConfirmBtn.disabled = false;
    if (driverBtnText) driverBtnText.style.display = 'inline';
    if (driverBtnLoading) driverBtnLoading.style.display = 'none';
  }

  function closeDriverModal() {
    if (!driverModal) return;
    driverModal.style.display = 'none';
    document.body.style.overflow = '';
  }

  driverModalClose?.addEventListener('click', closeDriverModal);
  driverDismissBtn?.addEventListener('click', closeDriverModal);
  driverModal?.addEventListener('click', function (e) {
    if (e.target === driverModal) closeDriverModal();
  });

  driverConfirmBtn?.addEventListener('click', async function () {
    var driverName = driverNameInput ? driverNameInput.value.trim() : '';
    var driverPhone = driverPhoneInput ? driverPhoneInput.value.trim() : '';
    var pickupCode = pickupCodeInput ? pickupCodeInput.value.trim() : '';

    if (!driverName) {
      showToast('Silakan masukkan nama driver.', 'error');
      return;
    }
    if (!driverPhone) {
      showToast('Silakan masukkan nomor HP driver.', 'error');
      return;
    }

    // Loading state
    if (driverConfirmBtn) driverConfirmBtn.disabled = true;
    if (driverBtnText) driverBtnText.style.display = 'none';
    if (driverBtnLoading) driverBtnLoading.style.display = 'inline';

    try {
      await WarungioAPI.updateOrderStatus(orderId, 'courier_pickup', '', '', '', '', {
        driver_name: driverName,
        driver_phone: driverPhone,
        pickup_code: pickupCode,
      });
      showToast('Kurir sedang menjemput pesanan!', 'success');
      closeDriverModal();
      setTimeout(function () { window.location.reload(); }, 1200);
    } catch (err) {
      showToast(err.message || 'Gagal menyimpan data driver.', 'error');
      if (driverConfirmBtn) driverConfirmBtn.disabled = false;
      if (driverBtnText) driverBtnText.style.display = 'inline';
      if (driverBtnLoading) driverBtnLoading.style.display = 'none';
    }
  });

  // ── Transit Modal Logic (Dalam Perjalanan) ──
  var transitModal = document.getElementById('transitModal');
  var transitModalClose = document.getElementById('transitModalClose');
  var transitDismissBtn = document.getElementById('transitDismissBtn');
  var transitConfirmBtn = document.getElementById('transitConfirmBtn');
  var transitEstimateInput = document.getElementById('transitEstimateInput');
  var transitTrackInput = document.getElementById('transitTrackInput');
  var transitBtnText = document.getElementById('transitBtnText');
  var transitBtnLoading = document.getElementById('transitBtnLoading');

  function openTransitModal() {
    if (!transitModal) return;
    transitModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    if (transitEstimateInput) transitEstimateInput.value = '';
    if (transitTrackInput) transitTrackInput.value = '';
    if (transitConfirmBtn) transitConfirmBtn.disabled = false;
    if (transitBtnText) transitBtnText.style.display = 'inline';
    if (transitBtnLoading) transitBtnLoading.style.display = 'none';
  }

  function closeTransitModal() {
    if (!transitModal) return;
    transitModal.style.display = 'none';
    document.body.style.overflow = '';
  }

  transitModalClose?.addEventListener('click', closeTransitModal);
  transitDismissBtn?.addEventListener('click', closeTransitModal);
  transitModal?.addEventListener('click', function (e) {
    if (e.target === transitModal) closeTransitModal();
  });

  transitConfirmBtn?.addEventListener('click', async function () {
    var estimate = transitEstimateInput ? transitEstimateInput.value.trim() : '';
    var trackCode = transitTrackInput ? transitTrackInput.value.trim() : '';

    // Loading state
    if (transitConfirmBtn) transitConfirmBtn.disabled = true;
    if (transitBtnText) transitBtnText.style.display = 'none';
    if (transitBtnLoading) transitBtnLoading.style.display = 'inline';

    try {
      await WarungioAPI.updateOrderStatus(orderId, 'on_delivery', '', trackCode, '', '', {
        estimated_time: estimate,
        tracking_number: trackCode,
      });
      showToast('Pesanan dalam perjalanan!', 'success');
      closeTransitModal();
      setTimeout(function () { window.location.reload(); }, 1200);
    } catch (err) {
      showToast(err.message || 'Gagal memperbarui status.', 'error');
      if (transitConfirmBtn) transitConfirmBtn.disabled = false;
      if (transitBtnText) transitBtnText.style.display = 'inline';
      if (transitBtnLoading) transitBtnLoading.style.display = 'none';
    }
  });

  // ── Load order ──
  try {
    const order = await WarungioAPI.getOrder(orderId);

    if (!order || order.id === undefined) {
      showError('Pesanan tidak ditemukan.');
      return;
    }

    if (loadingEl) loadingEl.style.display = 'none';

    // ── Header ──
    orderNumberEl.textContent = order.order_number || '#' + order.id;

    const status = order.order_status || 'pending';
    const statusKey = status.toLowerCase();
    statusBadge.textContent = STATUS_LABELS[statusKey] || status;
    statusBadge.className = 'status-badge ' + (STATUS_CLASSES[statusKey] || 'status-pending');

    // ── Timeline ──
    const activeSteps = getActiveSteps(order);
    const stepTimes = {};

    if (order.created_at) stepTimes[1] = formatDate(order.created_at);
    if (statusKey !== 'pending' && order.updated_at) {
      stepTimes[2] = order.paid_at ? formatDate(order.paid_at) : formatDate(order.updated_at);
    }
    if (statusKey === 'processed' || statusKey === 'shipped' || statusKey === 'completed') {
      stepTimes[3] = formatDate(order.updated_at);
    }
    if (statusKey === 'shipped' || statusKey === 'completed') {
      stepTimes[4] = formatDate(order.updated_at);
    }
    if (statusKey === 'completed') {
      stepTimes[5] = order.completed_at ? formatDate(order.completed_at) : formatDate(order.updated_at);
    }

    const timelineSteps = document.querySelectorAll('.timeline-step');
    timelineSteps.forEach((stepEl) => {
      const stepNum = parseInt(stepEl.dataset.step);
      if (activeSteps.includes(stepNum)) {
        stepEl.classList.add('active', 'completed');
      }
      const timeEl = stepEl.querySelector('.step-time');
      if (timeEl && stepTimes[stepNum]) {
        timeEl.textContent = stepTimes[stepNum];
      }
    });

    if ($('stepCreated') && order.created_at) {
      $('stepCreated').textContent = formatDate(order.created_at);
    }

    // ── Buyer info ──
    const buyerName = order.user_name || 'Pembeli';
    $('buyerName').textContent = buyerName;
    $('buyerAvatar').textContent = (buyerName.charAt(0) || 'P').toUpperCase();
    $('buyerEmail').textContent = order.user_email || '-';
    $('buyerPhone').textContent = order.recipient_phone || '-';

    // ── Items ──
    const itemsContainer = $('itemsList');
    itemsContainer.innerHTML = '';

    if (order.items && order.items.length > 0) {
      order.items.forEach((item) => {
        const photo = item.product_photo
          ? (item.product_photo.indexOf('http') === 0 ? '' : window.location.origin) + item.product_photo
          : WarungioAssets.img('vega-fresh.png');

        const div = document.createElement('div');
        div.className = 'order-item';
        div.innerHTML =
          '<img src="' + photo + '" alt="' + escapeHtml(item.product_name) + '" class="item-image" loading="lazy">' +
          '<div class="item-body">' +
            '<p class="item-name">' + escapeHtml(item.product_name) + '</p>' +
            '<p class="item-meta">' + item.qty + ' x ' + toRupiah(item.price) + '</p>' +
          '</div>' +
          '<span class="item-total">' + toRupiah(item.subtotal) + '</span>';
        itemsContainer.appendChild(div);
      });
    } else {
      itemsContainer.innerHTML = '<p style="color:var(--text-muted);font-size:0.9rem;padding:12px 0;">Tidak ada item.</p>';
    }

    // ── Notes ──
    if (order.notes) {
      $('notesSection').style.display = 'block';
      $('orderNotes').textContent = order.notes;
    }

    // ── Delivery Info ──
    $('deliveryAddress').textContent = order.delivery_address || '-';
    $('recipientName').textContent = order.recipient_name || order.user_name || '-';

    const delivery = order.delivery;
    if (delivery) {
      if (delivery.courier_name || order.courier) {
        $('courierRow').style.display = 'flex';
        $('courierName').textContent = delivery.courier_name || order.courier || '-';
      }
      if (delivery.tracking_number || order.tracking_number) {
        $('trackingRow').style.display = 'flex';
        $('trackingNumber').textContent = delivery.tracking_number || order.tracking_number;
      }
    } else {
      if (order.courier) {
        $('courierRow').style.display = 'flex';
        $('courierName').textContent = order.courier;
      }
      if (order.tracking_number) {
        $('trackingRow').style.display = 'flex';
        $('trackingNumber').textContent = order.tracking_number;
      }
    }

    // ── Payment Info ──
    $('paymentMethod').textContent = PAYMENT_LABELS[order.payment_method] || order.payment_method || 'Midtrans';
    const payStatus = order.payment_status || 'pending';
    $('paymentStatusText').textContent = payStatus === 'paid' ? 'Lunas' : payStatus === 'pending' ? 'Menunggu' : payStatus;

    // ── Order Summary ──
    $('summarySubtotal').textContent = toRupiah(order.subtotal || 0);
    $('summaryShipping').textContent = toRupiah(order.shipping_cost || 0);

    if (order.discount && Number(order.discount) > 0) {
      $('summaryDiscountRow').style.display = 'flex';
      $('summaryDiscount').textContent = '-' + toRupiah(order.discount);
    }

    $('summaryTotal').textContent = toRupiah(order.total_price || 0);

    // Store for later
    orderData = order;

    // ── Document title ──
    document.title = (order.order_number || '#' + order.id) + ' - Detail Pesanan - Warungio Seller';

    // ── Render action buttons ──
    renderActions(statusKey);

    // ── Listen for real-time updates ──
    document.addEventListener('warungio:order_update', (e) => {
      if (e.detail && e.detail.order_id == orderId) {
        console.info('Order update received, reloading...');
        setTimeout(function () { window.location.reload(); }, 1500);
      }
    });
    document.addEventListener('warungio:payment_update', (e) => {
      if (e.detail && e.detail.order_id == orderId) {
        console.info('Payment update received, reloading...');
        setTimeout(function () { window.location.reload(); }, 1500);
      }
    });

    // Init notification widget
    if (window.WarungioNotifications) {
      setTimeout(function () {
        WarungioNotifications.init('#notifContainer');
      }, 100);
    }

  } catch (err) {
    console.error('Failed to load order:', err);
    showError(err.message || 'Gagal memuat detail pesanan. Coba refresh halaman.');
  }
});
