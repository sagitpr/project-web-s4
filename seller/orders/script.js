/**
 * Seller Orders page - Warungio
 * Lists seller orders with hyperlocal status flow quick actions.
 * Actions: Proses -> Siap Diambil -> Kurir Jemput (modal) -> Dalam Perjalanan (modal) -> Selesai
 */
document.addEventListener('DOMContentLoaded', async () => {
  if (window.WarungioAuth && window.WarungioAuth.requireVerified && window.WarungioAuth.requireVerified()) {
    return;
  }

  // ── DOM refs ──
  const ordersBody = document.getElementById('ordersBody');
  const emptyState = document.getElementById('emptyState');
  const filterTabs = document.getElementById('filterTabs');
  const searchInput = document.getElementById('searchInput');
  const refreshBtn = document.getElementById('refreshBtn');
  const lastRefresh = document.getElementById('lastRefresh');

  let currentFilter = '';
  let currentSearch = '';
  let ordersCache = [];
  let pendingDriverOrderId = null;
  let pendingTransitOrderId = null;
  let pendingCancelOrderId = null;

  // ── Helpers ──
  function $(id) { return document.getElementById(id); }

  function toRupiah(num) {
    return 'Rp ' + Number(num || 0).toLocaleString('id-ID');
  }

  function escapeHtml(str) {
    if (!str) return '';
    var d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
      var d = new Date(dateStr);
      var now = new Date();
      var diff = (now - d) / 1000 / 60;
      if (diff < 60) return Math.round(diff) + ' menit lalu';
      if (diff < 1440) return Math.round(diff / 60) + ' jam lalu';
      return d.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
    } catch (e) { return dateStr; }
  }

  function showToast(message, type) {
    var existing = document.querySelector('.toast-notification');
    if (existing) existing.remove();
    var toast = document.createElement('div');
    toast.className = 'toast-notification';
    if (type === 'error') toast.style.background = '#DC2626';
    else if (type === 'success') toast.style.background = '#16A34A';
    else toast.style.background = '#14532D';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(function () { toast.classList.add('show'); }, 50);
    setTimeout(function () {
      toast.classList.remove('show');
      setTimeout(function () { toast.remove(); }, 300);
    }, 3500);
  }

  // ── Status helpers ──
  const STATUS_MAP = {
    'pending':      { label: 'Menunggu',        cls: 'badge-pending' },
    'paid':         { label: 'Lunas',            cls: 'badge-paid' },
    'processed':    { label: 'Diproses',         cls: 'badge-processed' },
    'ready_pickup': { label: 'Siap Diambil',     cls: 'badge-ready' },
    'courier_pickup': { label: 'Kurir Jemput',   cls: 'badge-courier' },
    'on_delivery':  { label: 'Dalam Perjalanan', cls: 'badge-shipped' },
    'completed':    { label: 'Selesai',          cls: 'badge-completed' },
    'cancelled':    { label: 'Dibatalkan',       cls: 'badge-cancelled' },
    'refunded':     { label: 'Dikembalikan',     cls: 'badge-refunded' },
  };

  // Quick action config per status
  function getQuickAction(statusKey) {
    var actions = {
      'pending':      { next: 'processed',     icon: 'fa-check',         label: 'Proses',          cls: 'act-info', confirmMsg: 'Proses pesanan ini?' },
      'paid':         { next: 'processed',     icon: 'fa-check',         label: 'Proses',          cls: 'act-info', confirmMsg: 'Proses pesanan ini?' },
      'processed':    { next: 'ready_pickup',  icon: 'fa-box-open',      label: 'Siap Diambil',    cls: 'act-warning', confirmMsg: 'Tandai siap diambil kurir?' },
      'ready_pickup': { next: 'courier_pickup', icon: 'fa-motorcycle',   label: 'Kurir Jemput',    cls: 'act-primary', confirmMsg: null, modal: 'driver' },
      'courier_pickup': { next: 'on_delivery', icon: 'fa-truck',         label: 'Dalam Perjalanan', cls: 'act-info', confirmMsg: null, modal: 'transit' },
      'on_delivery':  { next: 'completed',     icon: 'fa-check-circle',  label: 'Selesai',         cls: 'act-success', confirmMsg: 'Konfirmasi pesanan sudah tiba?' },
    };
    return actions[statusKey] || null;
  }

  function canCancel(statusKey) {
    return ['pending', 'paid', 'processed', 'ready_pickup'].includes(statusKey);
  }

  function getDeliveryStatusLabel(deliveryStatus) {
    var labels = {
      'menunggu_konfirmasi': 'Menunggu',
      'diproses_penjual': 'Diproses',
      'menunggu_penjemputan': 'Siap Diambil',
      'kurir_menjemput': 'Kurir Jemput',
      'dalam_perjalanan': 'Dalam Perjalanan',
      'pesanan_diterima': 'Selesai',
      'dibatalkan': 'Dibatalkan',
    };
    return labels[deliveryStatus] || deliveryStatus;
  }

  // ── Stats calculation ──
  function updateStats(orders) {
    var total = orders.length;
    var pending = orders.filter(function(o) { return o.order_status === 'pending' || o.order_status === 'paid'; }).length;
    var processed = orders.filter(function(o) { return o.order_status === 'processed' || o.order_status === 'ready_pickup'; }).length;
    var shipped = orders.filter(function(o) { return o.order_status === 'courier_pickup' || o.order_status === 'on_delivery'; }).length;
    var revenue = orders.reduce(function(sum, o) {
      return sum + (o.order_status === 'completed' || o.order_status === 'on_delivery' || o.order_status === 'courier_pickup' ? Number(o.total_price || 0) : 0);
    }, 0);

    $('statTotal').textContent = total;
    $('statPending').textContent = pending;
    $('statProcessed').textContent = processed;
    $('statShipped').textContent = shipped;
    $('statRevenue').textContent = toRupiah(revenue);
  }

  // ── Render orders table ──
  function renderOrders(orders) {
    if (!ordersBody) return;

    // Filter
    var filtered = orders;
    if (currentFilter) {
      filtered = orders.filter(function(o) { return o.order_status === currentFilter; });
    }
    if (currentSearch) {
      var q = currentSearch.toLowerCase();
      filtered = filtered.filter(function(o) {
        return (o.order_number || '').toLowerCase().includes(q) ||
               (o.user_name || '').toLowerCase().includes(q) ||
               (o.recipient_name || '').toLowerCase().includes(q);
      });
    }

    if (filtered.length === 0) {
      ordersBody.innerHTML = '<tr><td colspan="7" class="empty-cell">' +
        '<div class="empty-rows"><i class="fa-solid fa-inbox"></i><p>Tidak ada pesanan.</p></div></td></tr>';
      if (emptyState) emptyState.style.display = orders.length === 0 ? 'block' : 'none';
      return;
    }
    if (emptyState) emptyState.style.display = 'none';

    ordersBody.innerHTML = '';

    filtered.forEach(function(order) {
      var statusKey = order.order_status || 'pending';
      var statusInfo = STATUS_MAP[statusKey] || { label: statusKey, cls: 'badge-pending' };
      var action = getQuickAction(statusKey);
      var deliveryInfo = order.delivery || {};
      var shippingMethod = deliveryInfo.shipping_method_name || order.shipping_method_name || order.courier || '-';
      var itemCount = order.item_count || (order.items ? order.items.length : '-');
      var orderLabel = order.order_number || '#' + order.id;

      var tr = document.createElement('tr');

      // ── Build action buttons ──
      var actionsHtml = '<div class="action-group">';

      // Quick action button
      if (action) {
        actionsHtml += '<button class="act-btn ' + action.cls + '" data-id="' + order.id + '" data-action="' + action.next + '">' +
          '<i class="fa-solid ' + action.icon + '"></i> ' + action.label +
          '</button>';
      }

      // Detail link
      actionsHtml += '<a href="../order-detail/index.html?id=' + order.id + '" class="act-link" title="Detail">' +
        '<i class="fa-solid fa-arrow-right"></i>' +
        '</a>';

      // Cancel button (for cancellable statuses)
      if (canCancel(statusKey)) {
        actionsHtml += '<button class="act-btn act-danger-sm" data-id="' + order.id + '" data-action="cancel" title="Batalkan">' +
          '<i class="fa-solid fa-ban"></i>' +
          '</button>';
      }

      actionsHtml += '</div>';

      tr.innerHTML =
        '<td class="cell-order">' +
          '<div class="order-label">' + escapeHtml(orderLabel) + '</div>' +
          '<div class="order-time">' + formatDate(order.created_at) + '</div>' +
        '</td>' +
        '<td class="cell-buyer">' +
          '<div class="buyer-name">' + escapeHtml(order.user_name || order.recipient_name || '-') + '</div>' +
        '</td>' +
        '<td class="cell-items">' + itemCount + ' item</td>' +
        '<td class="cell-total">' + toRupiah(order.total_price) + '</td>' +
        '<td class="cell-courier"><span class="courier-badge">' + escapeHtml(shippingMethod) + '</span></td>' +
        '<td class="cell-status"><span class="status-badge ' + statusInfo.cls + '">' + statusInfo.label + '</span></td>' +
        '<td class="cell-actions">' + actionsHtml + '</td>';

      ordersBody.appendChild(tr);
    });

    // ── Attach event listeners ──
    ordersBody.querySelectorAll('.act-btn').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        var orderId = btn.dataset.id;
        var actionType = btn.dataset.action;

        if (actionType === 'cancel') {
          pendingCancelOrderId = orderId;
          openCancelModal(orderId);
          return;
        }

        var actionCfg = getQuickAction(orders.find(function(o) { return o.id == orderId; })?.order_status);
        if (!actionCfg) return;

        // Modal-based actions
        if (actionCfg.modal === 'driver') {
          pendingDriverOrderId = orderId;
          openDriverModal(orderId);
          return;
        }
        if (actionCfg.modal === 'transit') {
          pendingTransitOrderId = orderId;
          openTransitModal(orderId);
          return;
        }

        // Simple confirmation-based actions
        if (actionCfg.confirmMsg && !confirm(actionCfg.confirmMsg)) return;

        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

        WarungioAPI.updateOrderStatus(orderId, actionType)
          .then(function() {
            showToast('Status berhasil diperbarui!', 'success');
            loadOrders();
          })
          .catch(function(err) {
            showToast(err.message || 'Gagal memperbarui status.', 'error');
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid ' + actionCfg.icon + '"></i> ' + actionCfg.label;
          });
      });
    });
  }

  // ── Load orders from API ──
  async function loadOrders() {
    try {
      var data = await WarungioAPI.getSellerOrders();
      ordersCache = data.results || data || [];

      updateStats(ordersCache);
      renderOrders(ordersCache);

      var now = new Date();
      if (lastRefresh) lastRefresh.textContent = 'Terakhir: ' + now.toLocaleTimeString('id-ID');
    } catch (err) {
      console.warn('Load orders error:', err);
      if (ordersBody) {
        ordersBody.innerHTML = '<tr><td colspan="7" class="empty-cell">' +
          '<div class="error-rows"><i class="fa-solid fa-triangle-exclamation"></i><p>Gagal memuat pesanan.</p>' +
          '<button onclick="location.reload()" class="btn btn-outline" style="margin-top:8px">Coba Lagi</button></div></td></tr>';
      }
    }
  }

  // ── Filter + Search ──
  filterTabs?.addEventListener('click', function(e) {
    var btn = e.target.closest('.filter-btn');
    if (!btn) return;
    filterTabs.querySelectorAll('.filter-btn').forEach(function(b) { b.classList.remove('active'); });
    btn.classList.add('active');
    currentFilter = btn.dataset.filter;
    renderOrders(ordersCache);
  });

  searchInput?.addEventListener('input', function() {
    currentSearch = this.value.trim();
    renderOrders(ordersCache);
  });

  refreshBtn?.addEventListener('click', function() {
    refreshBtn.disabled = true;
    refreshBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    loadOrders().finally(function() {
      refreshBtn.disabled = false;
      refreshBtn.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Segarkan';
    });
  });

  // ── Auto-refresh every 30 seconds ──
  var autoRefreshInterval = setInterval(function() {
    loadOrders();
  }, 30000);

  // ── Listen for real-time updates ──
  document.addEventListener('warungio:order_update', function(e) {
    if (e.detail && e.detail.order_id) {
      console.info('Order update received:', e.detail.order_number, '-', e.detail.status);
      loadOrders();
    }
  });

  document.addEventListener('warungio:payment_update', function(e) {
    if (e.detail && e.detail.order_id) {
      console.info('Payment update received:', e.detail.order_number, '-', e.detail.status);
      loadOrders();
    }
  });

  // =========================================================================
  // MODALS
  // =========================================================================

  // ── Cancel Modal ──
  function openCancelModal(orderId) {
    var order = ordersCache.find(function(o) { return o.id == orderId; });
    if (!order) return;
    var modal = document.getElementById('cancelModal');
    if (!modal) return;
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    $('cancelReason').value = '';
    $('cancelReasonText').value = '';
    $('cancelConfirmBtn').disabled = false;
    $('cancelBtnText').style.display = 'inline';
    $('cancelBtnLoading').style.display = 'none';
  }

  function closeCancelModal() {
    var modal = document.getElementById('cancelModal');
    if (!modal) return;
    modal.style.display = 'none';
    document.body.style.overflow = '';
    pendingCancelOrderId = null;
  }

  $('cancelModalClose')?.addEventListener('click', closeCancelModal);
  $('cancelDismissBtn')?.addEventListener('click', closeCancelModal);
  $('cancelModal')?.addEventListener('click', function(e) {
    if (e.target === this) closeCancelModal();
  });

  $('cancelConfirmBtn')?.addEventListener('click', async function() {
    var reason = $('cancelReason').value;
    var reasonText = $('cancelReasonText').value.trim();
    if (!reason) { showToast('Pilih alasan pembatalan.', 'error'); return; }
    if (!confirm('Yakin ingin membatalkan pesanan ini?')) return;
    if (!pendingCancelOrderId) return;

    $('cancelConfirmBtn').disabled = true;
    $('cancelBtnText').style.display = 'none';
    $('cancelBtnLoading').style.display = 'inline';

    try {
      await WarungioAPI.updateOrderStatus(pendingCancelOrderId, 'cancelled', '', '', reason, reasonText);
      showToast('Pesanan dibatalkan.', 'success');
      closeCancelModal();
      loadOrders();
    } catch (err) {
      showToast(err.message || 'Gagal membatalkan.', 'error');
      $('cancelConfirmBtn').disabled = false;
      $('cancelBtnText').style.display = 'inline';
      $('cancelBtnLoading').style.display = 'none';
    }
  });

  // ── Driver Modal (Kurir Menjemput) ──
  function openDriverModal(orderId) {
    var order = ordersCache.find(function(o) { return o.id == orderId; });
    if (!order) return;
    $('driverOrderNumber').textContent = order.order_number || '#' + order.id;
    $('driverNameInput').value = '';
    $('driverPhoneInput').value = '';
    $('pickupCodeInput').value = '';
    $('driverConfirmBtn').disabled = false;
    $('driverBtnText').style.display = 'inline';
    $('driverBtnLoading').style.display = 'none';
    $('driverModal').style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  function closeDriverModal() {
    $('driverModal').style.display = 'none';
    document.body.style.overflow = '';
    pendingDriverOrderId = null;
  }

  $('driverModalClose')?.addEventListener('click', closeDriverModal);
  $('driverDismissBtn')?.addEventListener('click', closeDriverModal);
  $('driverModal')?.addEventListener('click', function(e) {
    if (e.target === this) closeDriverModal();
  });

  $('driverConfirmBtn')?.addEventListener('click', async function() {
    var name = $('driverNameInput').value.trim();
    var phone = $('driverPhoneInput').value.trim();
    var code = $('pickupCodeInput').value.trim();

    if (!name) { showToast('Masukkan nama driver.', 'error'); return; }
    if (!phone) { showToast('Masukkan nomor HP driver.', 'error'); return; }
    if (!pendingDriverOrderId) return;

    $('driverConfirmBtn').disabled = true;
    $('driverBtnText').style.display = 'none';
    $('driverBtnLoading').style.display = 'inline';

    try {
      await WarungioAPI.updateOrderStatus(pendingDriverOrderId, 'courier_pickup', '', '', '', '', {
        driver_name: name,
        driver_phone: phone,
        pickup_code: code,
      });
      showToast('Kurir sedang menjemput!', 'success');
      closeDriverModal();
      loadOrders();
    } catch (err) {
      showToast(err.message || 'Gagal menyimpan driver.', 'error');
      $('driverConfirmBtn').disabled = false;
      $('driverBtnText').style.display = 'inline';
      $('driverBtnLoading').style.display = 'none';
    }
  });

  // ── Transit Modal (Dalam Perjalanan) ──
  function openTransitModal(orderId) {
    var order = ordersCache.find(function(o) { return o.id == orderId; });
    if (!order) return;
    $('transitOrderNumber').textContent = order.order_number || '#' + order.id;
    $('transitEstimateInput').value = '';
    $('transitTrackInput').value = '';
    $('transitConfirmBtn').disabled = false;
    $('transitBtnText').style.display = 'inline';
    $('transitBtnLoading').style.display = 'none';
    $('transitModal').style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  function closeTransitModal() {
    $('transitModal').style.display = 'none';
    document.body.style.overflow = '';
    pendingTransitOrderId = null;
  }

  $('transitModalClose')?.addEventListener('click', closeTransitModal);
  $('transitDismissBtn')?.addEventListener('click', closeTransitModal);
  $('transitModal')?.addEventListener('click', function(e) {
    if (e.target === this) closeTransitModal();
  });

  $('transitConfirmBtn')?.addEventListener('click', async function() {
    var estimate = $('transitEstimateInput').value.trim();
    var trackCode = $('transitTrackInput').value.trim();
    if (!pendingTransitOrderId) return;

    $('transitConfirmBtn').disabled = true;
    $('transitBtnText').style.display = 'none';
    $('transitBtnLoading').style.display = 'inline';

    try {
      await WarungioAPI.updateOrderStatus(pendingTransitOrderId, 'on_delivery', '', trackCode, '', '', {
        estimated_time: estimate,
        tracking_number: trackCode,
      });
      showToast('Pesanan dalam perjalanan!', 'success');
      closeTransitModal();
      loadOrders();
    } catch (err) {
      showToast(err.message || 'Gagal memperbarui.', 'error');
      $('transitConfirmBtn').disabled = false;
      $('transitBtnText').style.display = 'inline';
      $('transitBtnLoading').style.display = 'none';
    }
  });

  // ── Init notification widget ──
  if (window.WarungioNotifications) {
    setTimeout(function() {
      WarungioNotifications.init('#notifContainer');
    }, 100);
  }

  // ── Init ──
  loadOrders();

  // Set seller name
  if (window.WarungioAuth && window.WarungioAuth.getUser) {
    var user = window.WarungioAuth.getUser();
    if (user && user.full_name && $('sellerName')) {
      $('sellerName').textContent = user.full_name;
    }
  }
});
