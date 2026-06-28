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
    window.location.href = '/auth/login/?next=' + encodeURIComponent(window.location.pathname + window.location.search);
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

  /* ── Init ── */
  document.addEventListener('DOMContentLoaded', function () {
    initCancelModal();
    loadOrder();
  });
})();
