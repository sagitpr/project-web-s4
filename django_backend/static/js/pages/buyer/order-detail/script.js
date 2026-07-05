/**
 * Order Detail page - Warungio
 * Loads order detail via API and renders timeline, items, delivery & payment info.
 */
document.addEventListener('DOMContentLoaded', async () => {
  if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
    window.location.href = '/auth/login/?next=' + encodeURIComponent(window.location.pathname + window.location.search);
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

  // ── Tracking Polling ──
  var trackingPollTimer = null;
  var trackingAttempts = 0;
  var MAX_TRACKING_ATTEMPTS = 120; // ~60 menit polling at 30s

  // Clean up tracking polling on navigate away
  function clearTrackingTimer() {
    if (trackingPollTimer) clearInterval(trackingPollTimer);
    trackingPollTimer = null;
  }
  window.addEventListener('beforeunload', clearTrackingTimer);
  window.addEventListener('pagehide', clearTrackingTimer);

  // Track previous delivery status to detect transitions
  var prevDeliveryStatus = '';

  function startTrackingPolling(orderId, order) {
    // Show tracking card for any non-pending status
    var trackingCard = document.getElementById('trackingCard');
    if (!trackingCard) return;

    trackingCard.style.display = 'block';

    var courier = order.courier || (order.delivery && order.delivery.courier_name) || '';
    var trackingNum = order.tracking_number || (order.delivery && order.delivery.tracking_number) || '';
    var delivery = order.delivery || {};

    prevDeliveryStatus = delivery.delivery_status || '';

    document.getElementById('trackingCourier').textContent = courier.toUpperCase() || 'KURIR';
    document.getElementById('trackingResi').textContent = trackingNum || '- - - - - -';

    // Show driver info if available
    if (delivery.driver_name || delivery.driver_phone || delivery.pickup_code) {
      renderDriverInfo(delivery);
    }

    // Show pickup code if available
    if (delivery.pickup_code) {
      renderPickupCode(delivery.pickup_code);
    }

    // Fetch immediately
    fetchTrackingStatus(orderId, true);

    // Determine poll interval based on status
    var status = (order.order_status || '').toLowerCase();
    var interval = 30000; // default 30s
    if (status === 'completed' || status === 'cancelled') {
      interval = 120000; // 2 min for completed/cancelled
      MAX_TRACKING_ATTEMPTS = 10; // stop polling after 20 min for completed
    }

    trackingPollTimer = setInterval(function () {
      if (document.hidden) return;
      if (trackingAttempts >= MAX_TRACKING_ATTEMPTS) {
        clearInterval(trackingPollTimer);
        trackingPollTimer = null;
        return;
      }
      trackingAttempts++;
      fetchTrackingStatus(orderId, false);
    }, interval);
  }

  function renderDriverInfo(delivery) {
    var driverEl = document.getElementById('trackingDriver');
    var nameEl = document.getElementById('trackingDriverName');
    var phoneEl = document.getElementById('trackingDriverPhone');
    if (!driverEl || !nameEl || !phoneEl) return;

    var wasHidden = driverEl.style.display === 'none' || driverEl.style.display === '';
    var changed = false;

    if (delivery.driver_name) {
      if (nameEl.textContent !== delivery.driver_name) {
        nameEl.textContent = delivery.driver_name;
        changed = true;
      }
    }
    if (delivery.driver_phone) {
      if (phoneEl.textContent !== delivery.driver_phone) {
        phoneEl.textContent = delivery.driver_phone;
        phoneEl.href = 'tel:' + delivery.driver_phone;
        changed = true;
      }
    }

    if (delivery.driver_name || delivery.driver_phone) {
      driverEl.style.display = 'flex';
      // Only animate on first appearance or content change
      if (wasHidden || changed) {
        driverEl.style.animation = 'none';
        requestAnimationFrame(function() {
          driverEl.style.animation = 'slideDown 0.3s ease';
        });
      }
    }
  }

  function renderPickupCode(code) {
    var pickupEl = document.getElementById('trackingPickup');
    var codeEl = document.getElementById('trackingPickupCode');
    if (!pickupEl || !codeEl) return;

    var wasHidden = pickupEl.style.display === 'none' || pickupEl.style.display === '';
    var changed = codeEl.textContent !== code;

    if (changed) {
      codeEl.textContent = code;
    }

    pickupEl.style.display = 'flex';

    // Only animate on first appearance or code change
    if (wasHidden || changed) {
      pickupEl.style.animation = 'none';
      requestAnimationFrame(function() {
        pickupEl.style.animation = 'slideDown 0.3s ease';
      });
    }
  }

  async function fetchTrackingStatus(orderId, showLoading) {
    var timeline = document.getElementById('trackingTimeline');
    var errorEl = document.getElementById('trackingError');
    var errorMsg = document.getElementById('trackingErrorMessage');
    var liveBadge = document.getElementById('liveBadge');

    if (!timeline) return;

    if (showLoading) {
      timeline.innerHTML = '<div class="tracking-loading"><span class="tracking-pulse"></span><span>Memuat status pengiriman...</span></div>';
      if (errorEl) errorEl.style.display = 'none';
    }

    try {
      var data = await WarungioAPI.getDeliveryTracking(orderId);

      // ── Update driver info dynamically ──
      if (data.driver_name || data.driver_phone) {
        renderDriverInfo(data);
      }
      if (data.pickup_code) {
        renderPickupCode(data.pickup_code);
      }

      // ── Detect delivery_status transitions for animation ──
      var currentStatus = data.delivery_status || '';
      var statusChanged = currentStatus !== prevDeliveryStatus && prevDeliveryStatus !== '';
      prevDeliveryStatus = currentStatus;

      // Update tracking meta
      if (data.courier && document.getElementById('trackingCourier')) {
        document.getElementById('trackingCourier').textContent = data.courier.toUpperCase();
      }
      if (data.tracking_number && document.getElementById('trackingResi')) {
        document.getElementById('trackingResi').textContent = data.tracking_number;
      }

      // Update the order status badge if delivery status changed
      if (statusChanged && data.delivery_status_label) {
        var badge = document.getElementById('statusBadge');
        if (badge) {
          badge.textContent = data.delivery_status_label;
          badge.className = 'status-badge ' + getBadgeClassForDelivery(currentStatus);
          // Flash animation on badge change
          badge.style.animation = 'none';
          requestAnimationFrame(function() {
            badge.style.animation = 'badgeFlash 0.6s ease';
          });
        }
        // Update the main timeline to reflect new status
        updateMainTimeline(currentStatus, data);
        showToast('Status pengiriman: ' + data.delivery_status_label, '');
      }

      if (!data || !data.milestones || data.milestones.length === 0) {
        if (showLoading) {
          timeline.innerHTML = '<div class="tracking-empty" style="color:var(--text-muted);padding:12px 0;font-size:0.85rem;">Belum ada informasi pelacakan dari kurir.</div>';
        }
        return;
      }

      // Animate render with status change detection
      renderTrackingMilestones(timeline, data, statusChanged);

      // Show live badge if still in transit
      var isActive = currentStatus !== 'pesanan_diterima' && currentStatus !== 'dibatalkan';
      if (liveBadge) {
        if (isActive && currentStatus !== 'menunggu_konfirmasi') {
          liveBadge.style.display = 'inline-flex';
          liveBadge.querySelector('.live-text').textContent = getPollIntervalLabel();
        } else {
          liveBadge.style.display = 'none';
        }
      }

    } catch (err) {
      if (errorEl && errorMsg) {
        if (showLoading) {
          errorEl.style.display = 'flex';
          errorMsg.textContent = err.message || 'Gagal memuat status pengiriman.';
          timeline.innerHTML = '';
        }
      }
    }
  }

  function getPollIntervalLabel() {
    if (!trackingPollTimer) return 'Langsung';
    return '30 detik';
  }

  function getBadgeClassForDelivery(deliveryStatus) {
    var map = {
      'menunggu_konfirmasi': 'status-pending',
      'diproses_penjual': 'status-processed',
      'menunggu_penjemputan': 'status-ready',
      'kurir_menjemput': 'status-courier',
      'dalam_perjalanan': 'status-shipped',
      'pesanan_diterima': 'status-completed',
      'dibatalkan': 'status-cancelled',
    };
    return map[deliveryStatus] || 'status-pending';
  }

  function updateMainTimeline(deliveryStatus, data) {
    // Map delivery status to timeline step
    var deliveryStepMap = {
      'menunggu_konfirmasi': 1,
      'diproses_penjual': 2,
      'menunggu_penjemputan': 3,
      'kurir_menjemput': 4,
      'dalam_perjalanan': 5,
      'pesanan_diterima': 6,
      'dibatalkan': 0,
    };
    var step = deliveryStepMap[deliveryStatus] || 1;
    var steps = [1, 2, 3, 4, 5, 6];
    if (deliveryStatus === 'dibatalkan') {
      // Only show first step as cancelled
      updateTimelineSteps([1]);
      return;
    }
    var activeSteps = steps.filter(function(s) { return s <= step; });
    updateTimelineSteps(activeSteps, data);
  }

  function updateTimelineSteps(activeSteps, data) {
    var els = document.querySelectorAll('.timeline-step');
    els.forEach(function(el) {
      var num = parseInt(el.dataset.step);
      var wasActive = el.classList.contains('active');
      var shouldBeActive = activeSteps.includes(num);

      if (shouldBeActive) {
        if (!wasActive) {
          // Animate in new step
          el.classList.add('active', 'completed', 'step-just-activated');
          setTimeout(function() { el.classList.remove('step-just-activated'); }, 600);
        } else {
          el.classList.add('active', 'completed');
        }
      } else {
        el.classList.remove('active', 'completed');
      }
    });

    // Update step times if available from delivery data
    if (data && data.milestones) {
      data.milestones.forEach(function(m) {
        var stepNum = m.step || 0;
        if (stepNum > 0) {
          var timeEl = document.querySelector('.timeline-step[data-step="' + stepNum + '"] .step-time');
          if (timeEl && m.time) {
            timeEl.textContent = formatDate(m.time);
          }
        }
      });
    }
  }

  // ── Tracking retry button ──
  document.getElementById('retryTrackingBtn')?.addEventListener('click', function () {
    fetchTrackingStatus(orderId, true);
  });

  function renderTrackingMilestones(timeline, data, statusChanged) {
    if (!timeline || !data.milestones) return;

    var wasEmpty = timeline.children.length === 0 ||
      (timeline.children.length === 1 && timeline.querySelector('.tracking-empty'));

    timeline.innerHTML = '';
    timeline.className = 'tracking-timeline';

    var isCompleted = data.delivery_status === 'pesanan_diterima';
    var isCancelled = data.delivery_status === 'dibatalkan';

    if (isCompleted) {
      timeline.classList.add('tracking-completed');
    } else if (isCancelled) {
      timeline.classList.add('tracking-cancelled');
    } else {
      timeline.classList.add('tracking-active');
    }

    data.milestones.forEach(function (milestone, index) {
      var isLast = index === data.milestones.length - 1;
      var div = document.createElement('div');
      div.className = 'tracking-step';

      if (milestone.is_current && !isCompleted && !isCancelled) {
        div.classList.add('current');
      } else if (isCompleted && isLast) {
        div.classList.add('completed', 'last-delivered');
      } else if (isCancelled && isLast) {
        div.classList.add('cancelled-step');
      } else {
        div.classList.add('completed');
      }

      // Animate newly added milestones
      if (statusChanged || wasEmpty) {
        div.style.opacity = '0';
        div.style.transform = 'translateY(12px)';
        setTimeout(function() {
          div.style.transition = 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)';
          div.style.opacity = '1';
          div.style.transform = 'translateY(0)';
        }, index * 80);
      }

      // Determine icon based on milestone type
      var iconHtml = '';
      if (milestone.icon === 'check') {
        iconHtml = '<svg class="track-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>';
      } else if (milestone.icon === 'truck') {
        iconHtml = '<svg class="track-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/></svg>';
      } else if (milestone.icon === 'motorcycle' || milestone.icon === 'rider') {
        iconHtml = '<svg class="track-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/><polyline points="2 14 7 14 10 8 14 8 16 14 22 14"/></svg>';
      } else if (milestone.icon === 'package') {
        iconHtml = '<svg class="track-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/></svg>';
      } else if (milestone.icon === 'x') {
        iconHtml = '<svg class="track-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
      }

      var timeStr = milestone.time ? formatDate(milestone.time) : '';

      div.innerHTML =
        '<div class="track-dot">' + iconHtml + '</div>' +
        '<div class="track-info">' +
          '<span class="track-status">' + escapeHtml(milestone.status) + '</span>' +
          (milestone.location ? '<span class="track-location">' + escapeHtml(milestone.location) + '</span>' : '') +
          (timeStr ? '<span class="track-time">' + timeStr + '</span>' : '') +
        '</div>';

      timeline.appendChild(div);
    });
  }

  // ── Toast helper ──
  function showToast(message, type) {
    var toast = document.createElement('div');
    toast.className = 'toast-notification';
    if (type === 'error') {
      toast.style.background = '#DC2626';
    } else if (type === 'success') {
      toast.style.background = '#16A34A';
    }
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(function () { toast.classList.add('show'); }, 50);
    setTimeout(function () {
      toast.classList.remove('show');
      setTimeout(function () { toast.remove(); }, 300);
    }, 4000);
  }

  // ── Status helpers ──
  const STATUS_LABELS = {
    'pending': 'Menunggu',
    'paid': 'Lunas',
    'processed': 'Diproses',
    'ready_pickup': 'Siap Diambil',
    'courier_pickup': 'Kurir Menjemput',
    'on_delivery': 'Dalam Perjalanan',
    'shipped': 'Dikirim',
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
    'shipped': 'status-shipped',
    'completed': 'status-completed',
    'cancelled': 'status-cancelled',
    'refunded': 'status-refunded',
  };

  const PAYMENT_LABELS = {
    'midtrans': 'Midtrans (Kartu, QRIS, e-Wallet)',
    'cod': 'Bayar di Tempat (COD)',
    'transfer': 'Transfer Bank',
  };

  const DELIVERY_STATUS_LABELS = {
    'menunggu_konfirmasi': 'Menunggu Konfirmasi',
    'diproses_penjual': 'Diproses Penjual',
    'menunggu_penjemputan': 'Menunggu Penjemputan',
    'kurir_menjemput': 'Kurir Menjemput',
    'dalam_perjalanan': 'Dalam Perjalanan',
    'pesanan_diterima': 'Pesanan Diterima',
    'dibatalkan': 'Dibatalkan',
  };

  // ── Map order status & delivery status to timeline steps (hyperlocal: 6 steps) ──
  function getActiveSteps(order) {
    // Prefer delivery status for more granular timeline
    var delivery = order.delivery || {};
    var ds = delivery.delivery_status || '';
    var s = (order.order_status || 'pending').toLowerCase();

    if (ds === 'pesanan_diterima') return [1, 2, 3, 4, 5, 6];
    if (ds === 'dalam_perjalanan') return [1, 2, 3, 4, 5];
    if (ds === 'kurir_menjemput')  return [1, 2, 3, 4];
    if (ds === 'menunggu_penjemputan') return [1, 2, 3];
    if (ds === 'diproses_penjual') return [1, 2];
    if (ds === 'dibatalkan') return [1];

    // Fallback to order status
    if (s === 'completed') return [1, 2, 3, 4, 5, 6];
    if (s === 'on_delivery') return [1, 2, 3, 4, 5];
    if (s === 'courier_pickup') return [1, 2, 3, 4];
    if (s === 'ready_pickup') return [1, 2, 3];
    if (s === 'shipped')    return [1, 2, 3, 4, 5];
    if (s === 'processed')  return [1, 2];
    if (s === 'paid')       return [1, 2];
    if (s === 'cancelled')  return [1];
    if (s === 'refunded')   return [1, 2, 3];
    return [1];
  }

  // ── Load order ──
  try {
    const order = await WarungioAPI.getOrder(orderId);

    if (!order || order.id === undefined) {
      showError('Pesanan tidak ditemukan.');
      return;
    }

    // Hide loading
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

    // Collect timestamps per step
    if (order.created_at) stepTimes[1] = formatDate(order.created_at);
    if (statusKey !== 'pending' && order.updated_at) {
      // Payment step uses paid_at or updated_at
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

    // Render timeline
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

    // Set timeline times
    if ($('stepCreated') && order.created_at) {
      $('stepCreated').textContent = formatDate(order.created_at);
    }
    if ($('stepProcessed') && delivery && delivery.updated_at) {
      // Use order.updated_at or delivery timestamps
      $('stepProcessed').textContent = formatDate(delivery.updated_at || order.updated_at);
    }
    if ($('stepReady') && delivery && delivery.pickup_code) {
      $('stepReady').textContent = delivery.estimated_time || formatDate(delivery.updated_at);
    }
    if ($('stepCourier') && delivery && delivery.picked_up_at) {
      $('stepCourier').textContent = formatDate(delivery.picked_up_at);
    }
    if ($('stepShipped') && order.tracking_number) {
      $('stepShipped').textContent = delivery.estimated_time || formatDate(delivery.updated_at);
    }

    // ── Store info ──
    const storeName = order.store_name || 'Warung';
    $('storeName').textContent = storeName;
    $('storeAvatar').textContent = (storeName.charAt(0) || 'T').toUpperCase();

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
    $('recipientPhone').textContent = order.recipient_phone || '-';

    // Courier & tracking (hyperlocal)
    const delivery = order.delivery;
    if (delivery) {
      var shippingMethodName = delivery.shipping_method_name || order.shipping_method_name || delivery.courier_name || order.courier || '';
      if (shippingMethodName) {
        $('courierRow').style.display = 'flex';
        $('courierName').textContent = shippingMethodName;
      }

      // Driver info
      if (delivery.driver_name || delivery.driver_phone) {
        var driverInfo = [];
        if (delivery.driver_name) driverInfo.push(delivery.driver_name);
        if (delivery.driver_phone) driverInfo.push(delivery.driver_phone);
        $('courierName').textContent = shippingMethodName + ' - ' + driverInfo.join(' / ');
      }

      // Pickup code
      if (delivery.pickup_code) {
        var pickupRow = document.getElementById('pickupRow');
        if (!pickupRow) {
          var deliveryGrid = document.querySelector('.info-grid');
          if (deliveryGrid && deliveryGrid.parentElement && deliveryGrid.parentElement.querySelector('h3')?.textContent.includes('Pengiriman')) {
            var row = document.createElement('div');
            row.className = 'info-row';
            row.id = 'pickupRow';
            row.innerHTML = '<span class="info-label">Kode Pickup</span><span class="info-value pickup-code" id="pickupCodeValue">' + escapeHtml(delivery.pickup_code) + '</span>';
            deliveryGrid.appendChild(row);
          }
        } else {
          pickupRow.style.display = 'flex';
          document.getElementById('pickupCodeValue').textContent = delivery.pickup_code;
        }
      }

      // Tracking info
      if (delivery.tracking_number || order.tracking_number) {
        $('trackingRow').style.display = 'flex';
        var trackingNum = delivery.tracking_number || order.tracking_number;
        var link = $('trackingNumber');
        link.textContent = trackingNum;
        link.href = getTrackingUrl(shippingMethodName, trackingNum);
      }

      // Delivery status
      if (delivery.delivery_status && DELIVERY_STATUS_LABELS[delivery.delivery_status]) {
        var currentStatusEl = document.getElementById('currentDeliveryStatus');
        if (!currentStatusEl) {
          var statusRow = document.createElement('div');
          statusRow.className = 'info-row';
          statusRow.id = 'currentDeliveryStatusRow';
          statusRow.innerHTML = '<span class="info-label">Status Pengiriman</span><span class="info-value" id="currentDeliveryStatus">' + DELIVERY_STATUS_LABELS[delivery.delivery_status] + '</span>';
          var infoGrid = document.querySelector('.info-grid');
          if (infoGrid && infoGrid.parentElement && infoGrid.parentElement.querySelector('h3')?.textContent.includes('Pengiriman')) {
            infoGrid.insertBefore(statusRow, infoGrid.firstChild);
          }
        } else {
          currentStatusEl.textContent = DELIVERY_STATUS_LABELS[delivery.delivery_status];
        }
      }
    } else {
      if (order.courier) {
        $('courierRow').style.display = 'flex';
        $('courierName').textContent = order.courier;
      }
      if (order.tracking_number) {
        $('trackingRow').style.display = 'flex';
        var link = $('trackingNumber');
        link.textContent = order.tracking_number;
        link.href = getTrackingUrl((order.courier || '').toLowerCase(), order.tracking_number);
      }
    }

    // ── Payment Info ──
    const payMethod = order.payment_method || 'midtrans';
    $('paymentMethod').textContent = PAYMENT_LABELS[payMethod] || payMethod;

    const payStatus = order.payment_status || 'pending';
    const payStatusText = payStatus === 'paid' ? 'Lunas' : payStatus === 'pending' ? 'Menunggu Pembayaran' : payStatus;
    $('paymentStatusText').textContent = payStatusText;

    // ── Order Summary ──
    $('summarySubtotal').textContent = toRupiah(order.subtotal || 0);
    $('summaryShipping').textContent = toRupiah(order.shipping_cost || 0);

    if (order.discount && Number(order.discount) > 0) {
      $('summaryDiscountRow').style.display = 'flex';
      $('summaryDiscount').textContent = '-' + toRupiah(order.discount);
    }

    $('summaryTotal').textContent = toRupiah(order.total_price || 0);

    // Store for later use
    orderData = order;

    // ── Update document title ──
    document.title = (order.order_number || '#' + order.id) + ' - Detail Pesanan - Warungio';

    // ── Cancel button visibility ──
    const cancelBtn = document.getElementById('cancelOrderBtn');
    if (cancelBtn && ['pending', 'paid'].includes(statusKey)) {
      cancelBtn.style.display = 'flex';
    }

    // ── Start tracking polling for any active delivery status ──
    var activeDeliveryStatuses = ['menunggu_konfirmasi', 'diproses_penjual', 'menunggu_penjemputan',
                                  'kurir_menjemput', 'dalam_perjalanan', 'pesanan_diterima'];
    var shouldPoll = statusKey !== 'pending' && statusKey !== 'cancelled';
    if (delivery && delivery.delivery_status && activeDeliveryStatuses.includes(delivery.delivery_status)) {
      shouldPoll = true;
    }
    if (shouldPoll) {
      startTrackingPolling(orderId, order);
    }

    // ── Listen for real-time updates ──
    document.addEventListener('warungio:order_update', (e) => {
      if (e.detail && e.detail.order_id == orderId) {
        console.info('Order update received, reloading...');
        setTimeout(() => window.location.reload(), 1500);
      }
    });
    document.addEventListener('warungio:payment_update', (e) => {
      if (e.detail && e.detail.order_id == orderId) {
        console.info('Payment update received, reloading...');
        setTimeout(() => window.location.reload(), 1500);
      }
    });
    document.addEventListener('warungio:delivery_update', (e) => {
      if (e.detail && e.detail.order_id == orderId) {
        console.info('Delivery update received via WebSocket, reloading tracking...');
        // Refresh tracking data without full page reload
        var trackingCard = document.getElementById('trackingCard');
        if (trackingCard && trackingCard.style.display !== 'none') {
          // Re-fetch tracking silently
          fetchTrackingStatus(orderId, false);
        } else {
          setTimeout(() => window.location.reload(), 1500);
        }
      }
    });

  } catch (err) {
    console.error('Failed to load order:', err);
    showError(err.message || 'Gagal memuat detail pesanan. Coba refresh halaman.');
  }

  // ── Helpers ──

  function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('id-ID', {
        day: 'numeric', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      });
    } catch (e) {
      return dateStr;
    }
  }

  function getTrackingUrl(courier, trackingNumber) {
    if (!trackingNumber) return '#';
    var trackNum = encodeURIComponent(trackingNumber);
    var c = (courier || '').toLowerCase();
    if (c.includes('grab') || c.includes('grabexpress')) return 'https://www.grab.com/id/express/';
    if (c.includes('gojek') || c.includes('gosend')) return 'https://www.gojek.com/id-id/gosend/';
    if (c.includes('maxim')) return 'https://maxim.id/tracking';
    // Antar Sendiri — no public tracking URL
    return '#';
  }

  // ── Cancel Order Modal Logic ──
  var modalCancelBtn = document.getElementById('cancelOrderBtn');
  var cancelModal = document.getElementById('cancelModal');
  var cancelModalClose = document.getElementById('cancelModalClose');
  var cancelDismissBtn = document.getElementById('cancelDismissBtn');
  var cancelConfirmBtn = document.getElementById('cancelConfirmBtn');
  var cancelBtnText = document.getElementById('cancelBtnText');
  var cancelBtnLoading = document.getElementById('cancelBtnLoading');
  var cancelReasonText = document.getElementById('cancelReasonText');

  function openCancelModal() {
    if (!cancelModal) return;
    cancelModal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    // Reset form
    var radios = document.querySelectorAll('input[name="cancelReason"]');
    radios.forEach(function(r) { r.checked = false; });
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

  modalCancelBtn?.addEventListener('click', openCancelModal);
  cancelModalClose?.addEventListener('click', closeCancelModal);
  cancelDismissBtn?.addEventListener('click', closeCancelModal);

  // Close on outside click
  cancelModal?.addEventListener('click', function (e) {
    if (e.target === cancelModal) {
      closeCancelModal();
    }
  });

  // Submit cancel
  cancelConfirmBtn?.addEventListener('click', async function () {
    var selectedReason = document.querySelector('input[name="cancelReason"]:checked');
    var reasonValue = selectedReason ? selectedReason.value : '';
    var reasonText = cancelReasonText ? cancelReasonText.value.trim() : '';

    if (!reasonValue && !reasonText) {
      showToast('Silakan pilih alasan pembatalan.', 'error');
      return;
    }

    // Loading state
    if (cancelConfirmBtn) cancelConfirmBtn.disabled = true;
    if (cancelBtnText) cancelBtnText.style.display = 'none';
    if (cancelBtnLoading) cancelBtnLoading.style.display = 'inline';

    try {
      await WarungioAPI.cancelOrder(orderId, reasonValue, reasonText);
      showToast('Pesanan berhasil dibatalkan.', 'success');
      closeCancelModal();
      // Reload after short delay
      setTimeout(function () { window.location.reload(); }, 1500);
    } catch (err) {
      showToast(err.message || 'Gagal membatalkan pesanan. Silakan coba lagi.', 'error');
      if (cancelConfirmBtn) cancelConfirmBtn.disabled = false;
      if (cancelBtnText) cancelBtnText.style.display = 'inline';
      if (cancelBtnLoading) cancelBtnLoading.style.display = 'none';
    }
  });

  // ── Polling for Midtrans pending payment ──
  if (orderData && orderData.payment_method === 'midtrans' && orderData.payment_status !== 'paid') {
    startPaymentPolling(orderId);
  }

  function startPaymentPolling(orderId) {
    let attempts = 0;
    const maxAttempts = 30; // ~2.5 menit

    const poll = setInterval(async () => {
      attempts++;
      try {
        const data = await WarungioAPI.getPaymentStatus(orderId);
        if (data.payment_status === 'paid' || data.payment_status === 'settlement') {
          clearInterval(poll);
          // Show toast and reload
          const toast = document.createElement('div');
          toast.className = 'toast-notification';
          toast.textContent = 'Pembayaran berhasil! Memuat ulang...';
          document.body.appendChild(toast);
          setTimeout(() => { toast.classList.add('show'); }, 100);
          setTimeout(() => window.location.reload(), 2000);
        }
      } catch (e) {
        // Silent
      }
      if (attempts >= maxAttempts) {
        clearInterval(poll);
      }
    }, 5000);
  }
});
