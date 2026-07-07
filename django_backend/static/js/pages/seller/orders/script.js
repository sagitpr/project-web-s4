/**
 * Seller Orders - Warungio
 * Connected to Django order management API.
 */
document.addEventListener('DOMContentLoaded', () => {
  // Auth check
  if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
    window.location.href = '/?next=' + encodeURIComponent(window.location.pathname);
    return;
  }

  const tbody = document.getElementById('orders-tbody');
  const emptyState = document.getElementById('orders-empty-state');
  const searchInput = document.getElementById('search-order');
  const dateFilter = document.getElementById('date-filter');
  const tabButtons = document.querySelectorAll('.tab-btn');
  const statCards = document.querySelectorAll('.stats-grid .stat-card');

  // Detail panel DOM
  const detailPanel = document.getElementById('order-detail-panel');
  const detailInvoice = document.getElementById('detail-invoice');
  const detailBadge = document.getElementById('detail-badge');
  const detailItemsList = document.getElementById('detail-items-list');
  const detailCustomerName = document.getElementById('detail-customer-name');
  const detailCustomerPhone = document.getElementById('detail-customer-phone');
  const detailCustomerAddress = document.getElementById('detail-customer-address');
  const detailShippingSelect = document.getElementById('detail-shipping-select');
  const detailNotes = document.getElementById('detail-notes');
  
  const btnCloseDetail = document.getElementById('btn-close-detail');
  const btnDetailCancel = document.getElementById('btn-detail-cancel');
  const btnDetailProcess = document.getElementById('btn-detail-process');

  let ordersData = [];
  let activeTab = 'all';
  let activeSearch = '';
  let activeDate = 'all';
  let selectedOrderId = null;

  const STATUS_LABELS = {
    pending: 'Menunggu',
    paid: 'Lunas',
    processed: 'Diproses',
    shipped: 'Dikirim',
    completed: 'Selesai',
    cancelled: 'Batal',
    refunded: 'Refunded'
  };

  const STATUS_CLASSES = {
    pending: 'status-yellow',
    paid: 'status-blue',
    processed: 'status-blue',
    shipped: 'status-purple',
    completed: 'status-green',
    cancelled: 'status-red',
    refunded: 'status-red'
  };

  function toRupiah(num) {
    return 'Rp ' + Number(num).toLocaleString('id-ID');
  }

  // Fetch orders from API
  async function fetchOrders() {
    try {
      const params = {};
      if (activeTab !== 'all') {
        params.status = activeTab;
      }
      if (activeSearch) {
        params.search = activeSearch;
      }
      if (activeDate !== 'all') {
        params.date_filter = activeDate;
      }

      // Query real backend orders list
      const res = await WarungioAPI.getSellerOrders(params);
      ordersData = Array.isArray(res) ? res : (res.results || []);
      
      updateStats();
      renderOrders();
    } catch (err) {
      console.warn('Failed to load seller orders:', err);
      ordersData = [];
      renderOrders();
    }
  }

  // Calculate statistics from the full dataset (or fallback summary counts)
  function updateStats() {
    // Count local items
    const counts = { all: 0, pending: 0, processing: 0, shipped: 0, completed: 0 };
    
    // We request full listing once to set accurate metrics
    ordersData.forEach(o => {
      counts.all++;
      const status = (o.order_status || o.status || 'pending').toLowerCase();
      if (status === 'pending' || status === 'paid') counts.pending++;
      else if (status === 'processed') counts.processing++;
      else if (status === 'shipped') counts.shipped++;
      else if (status === 'completed') counts.completed++;
    });

    // Update UI elements
    const setStatText = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };

    setStatText('stat-count-all', counts.all);
    setStatText('stat-count-pending', counts.pending);
    setStatText('stat-count-processing', counts.processing);
    setStatText('stat-count-shipped', counts.shipped);
    setStatText('stat-count-completed', counts.completed);
  }

  // Render orders in the table
  function renderOrders() {
    if (!tbody) return;
    tbody.innerHTML = '';

    if (ordersData.length === 0) {
      if (emptyState) emptyState.style.display = 'block';
      return;
    }

    if (emptyState) emptyState.style.display = 'none';

    ordersData.forEach(o => {
      const invoice = o.order_number || `#INV-${o.id}`;
      const statusKey = (o.order_status || o.status || 'pending').toLowerCase();
      const statusLabel = STATUS_LABELS[statusKey] || statusKey;
      const statusClass = STATUS_CLASSES[statusKey] || 'status-yellow';
      
      const customer = o.recipient_name || o.user_name || 'Pelanggan';
      const phone = o.recipient_phone || '-';
      const dateStr = new Date(o.created_at).toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' });
      const total = toRupiah(o.total_price || 0);
      const paymentMethod = o.payment_method === 'cod' ? 'COD' : 'Midtrans';

      // Thumbnail list
      let thumbsHtml = '';
      if (o.items && o.items.length > 0) {
        o.items.slice(0, 3).forEach(item => {
          const img = item.product_photo || WarungioAssets.img('vega-fresh.png');
          thumbsHtml += `<img src="${img}" style="width: 24px; height: 24px; border-radius: 4px; object-fit: cover; border: 1px solid var(--border-color);" alt="" /> `;
        });
        if (o.items.length > 3) {
          thumbsHtml += `<span class="badge" style="background:#f1f5f9;color:var(--text-muted);font-size:10px;padding:2px 4px;">+${o.items.length - 3}</span>`;
        }
      }

      const tr = document.createElement('tr');
      tr.style.cursor = 'pointer';
      tr.style.borderBottom = '1px solid var(--border-color)';
      tr.innerHTML = `
        <td style="padding: 14px 12px;">
          <div style="font-weight: 700; color: var(--text-main);">${invoice}</div>
          <div style="display: flex; align-items: center; gap: 4px; margin-top: 6px;">${thumbsHtml}</div>
        </td>
        <td style="padding: 14px 12px;">
          <div style="font-weight: 600;">${customer}</div>
          <div style="font-size: 11px; color: var(--text-muted);">${phone}</div>
        </td>
        <td style="padding: 14px 12px; color: var(--text-muted);">${dateStr}</td>
        <td style="padding: 14px 12px; font-weight: 700;">${total}</td>
        <td style="padding: 14px 12px;"><span class="status-pill ${statusClass}" style="padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 700;">${statusLabel}</span></td>
        <td style="padding: 14px 12px;"><span style="font-weight: 600; color: #475569;">${paymentMethod}</span></td>
        <td style="padding: 14px 12px; text-align: right;"><button class="btn-action btn-view-detail" style="padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 600;">Detail</button></td>
      `;

      tbody.appendChild(tr);

      // Event listener to open details
      const openDetailAction = (e) => {
        e.stopPropagation();
        openOrderDetail(o);
      };
      tr.addEventListener('click', openDetailAction);
      tr.querySelector('.btn-view-detail')?.addEventListener('click', openDetailAction);
    });
  }

  // Open order detail slider/drawer
  function openOrderDetail(order) {
    selectedOrderId = order.id;
    if (detailPanel) detailPanel.style.display = 'block';
    
    if (detailInvoice) detailInvoice.textContent = order.order_number || `#INV-${order.id}`;
    
    const statusKey = (order.order_status || order.status || 'pending').toLowerCase();
    if (detailBadge) {
      detailBadge.textContent = STATUS_LABELS[statusKey] || statusKey;
      detailBadge.className = 'status-pill ' + (STATUS_CLASSES[statusKey] || 'status-yellow');
    }

    if (detailCustomerName) detailCustomerName.textContent = order.recipient_name || order.user_name || 'Pelanggan';
    if (detailCustomerPhone) detailCustomerPhone.textContent = order.recipient_phone || '-';
    if (detailCustomerAddress) detailCustomerAddress.textContent = order.delivery_address || '-';
    
    if (detailNotes) detailNotes.value = order.notes || '';

    // Render items list
    if (detailItemsList) {
      detailItemsList.innerHTML = '';
      if (order.items && order.items.length > 0) {
        order.items.forEach(item => {
          const img = item.product_photo || WarungioAssets.img('vega-fresh.png');
          const subtotal = toRupiah(Number(item.price || 0) * (item.qty || 1));
          
          detailItemsList.innerHTML += `
            <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px dashed var(--border-color); padding-bottom: 8px;">
              <div style="display: flex; align-items: center; gap: 10px;">
                <img src="${img}" style="width: 36px; height: 36px; border-radius: 6px; object-fit: cover;" alt="" />
                <div>
                  <b style="font-size: 13px; color: var(--text-main);">${item.product_name || 'Produk'}</b>
                  <span style="display: block; font-size: 11px; color: var(--text-muted);">${item.qty} x ${toRupiah(item.price)}</span>
                </div>
              </div>
              <span style="font-weight: 700; font-size: 13px; color: var(--text-main);">${subtotal}</span>
            </div>
          `;
        });
      } else {
        detailItemsList.innerHTML = '<p style="color:var(--text-muted);font-size:12px;">Tidak ada item.</p>';
      }
    }

    // Configure shipping method selector if saved
    if (detailShippingSelect && order.shipping_method) {
      detailShippingSelect.value = order.shipping_method;
    }

    // Set buttons visibilities based on status
    if (btnDetailProcess) {
      if (statusKey === 'pending' || statusKey === 'paid') {
        btnDetailProcess.style.display = 'block';
        btnDetailProcess.textContent = 'Proses Pesanan';
        btnDetailProcess.setAttribute('data-target-status', 'processed');
      } else if (statusKey === 'processed') {
        btnDetailProcess.style.display = 'block';
        btnDetailProcess.textContent = 'Kirim Pesanan';
        btnDetailProcess.setAttribute('data-target-status', 'shipped');
      } else if (statusKey === 'shipped') {
        btnDetailProcess.style.display = 'block';
        btnDetailProcess.textContent = 'Selesaikan Pesanan';
        btnDetailProcess.setAttribute('data-target-status', 'completed');
      } else {
        btnDetailProcess.style.display = 'none';
      }
    }

    if (btnDetailCancel) {
      if (statusKey === 'pending' || statusKey === 'paid' || statusKey === 'processed') {
        btnDetailCancel.style.display = 'block';
      } else {
        btnDetailCancel.style.display = 'none';
      }
    }
  }

  // Close order detail slider
  btnCloseDetail?.addEventListener('click', () => {
    if (detailPanel) detailPanel.style.display = 'none';
    selectedOrderId = null;
  });

  // Handle Cancel Order click
  btnDetailCancel?.addEventListener('click', async () => {
    if (!selectedOrderId) return;
    const confirmVal = confirm('Apakah Anda yakin ingin membatalkan pesanan ini? Tindakan ini tidak dapat dibatalkan.');
    if (!confirmVal) return;

    try {
      btnDetailCancel.disabled = true;
      btnDetailCancel.textContent = 'Membatalkan...';

      await WarungioAPI.updateOrderStatus(
        selectedOrderId,
        'cancelled',
        '',                   // courier
        '',                   // tracking number
        'other',              // cancel_reason (enum: out_of_stock, seller_unavailable, wrong_price, address_invalid, product_damaged, other)
        detailNotes?.value || 'Dibatalkan oleh penjual',  // cancel_reason_text
        {}                    // extraFields
      );
      
      window.WarungioToast?.show('Pesanan berhasil dibatalkan.', 'success');
      if (detailPanel) detailPanel.style.display = 'none';
      selectedOrderId = null;
      fetchOrders();
    } catch (err) {
      window.WarungioToast?.show(err.message || 'Gagal membatalkan pesanan.', 'error');
    } finally {
      btnDetailCancel.disabled = false;
      btnDetailCancel.textContent = 'Batal';
    }
  });

  // Handle Process/Ship Order click
  btnDetailProcess?.addEventListener('click', async () => {
    if (!selectedOrderId) return;
    const nextStatus = btnDetailProcess.getAttribute('data-target-status');
    let shipMethod = detailShippingSelect?.value || '';
    let extraFields = {};

    // Set appropriate fields based on next status
    if (nextStatus === 'on_delivery') {
      extraFields.tracking_number = `TRK-${selectedOrderId}`;
      extraFields.estimated_time = '30-60 menit';
    }
    if (nextStatus === 'courier_pickup') {
      extraFields.courier = shipMethod;
      extraFields.driver_name = document.getElementById('detail-driver-name')?.value || '';
      extraFields.driver_phone = document.getElementById('detail-driver-phone')?.value || '';
    }

    try {
      btnDetailProcess.disabled = true;
      btnDetailProcess.textContent = 'Memproses...';

      // Call API status transition
      await WarungioAPI.updateOrderStatus(
        selectedOrderId,
        nextStatus,
        shipMethod,
        nextStatus === 'on_delivery' ? `TRK-${selectedOrderId}` : '',
        '',
        '',
        extraFields
      );

      window.WarungioToast?.show(`Status pesanan diperbarui ke "${STATUS_LABELS[nextStatus]}".`, 'success');
      if (detailPanel) detailPanel.style.display = 'none';
      selectedOrderId = null;
      fetchOrders();
    } catch (err) {
      window.WarungioToast?.show(err.message || 'Gagal memperbarui status pesanan.', 'error');
    } finally {
      btnDetailProcess.disabled = false;
    }
  });

  // Tab buttons triggers
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      tabButtons.forEach(b => {
        b.classList.remove('active');
        b.style.background = 'transparent';
        b.style.color = 'var(--text-muted)';
      });
      btn.classList.add('active');
      btn.style.background = 'white';
      btn.style.color = 'var(--text-main)';

      activeTab = btn.dataset.tab;
      if (detailPanel) detailPanel.style.display = 'none';
      selectedOrderId = null;
      fetchOrders();
    });
  });

  // Stat cards quick triggers
  statCards.forEach(card => {
    card.addEventListener('click', () => {
      const status = card.dataset.status;
      const matchingTab = document.querySelector(`.status-tabs .tab-btn[data-tab="${status}"]`);
      if (matchingTab) {
        matchingTab.click();
      }
    });
  });

  // Search input filter
  searchInput?.addEventListener('input', () => {
    activeSearch = searchInput.value.trim();
    fetchOrders();
  });

  // Date select filter
  dateFilter?.addEventListener('change', () => {
    activeDate = dateFilter.value;
    fetchOrders();
  });

  // ── Real-time WebSocket order updates ──
  // Automatically refresh the orders list and stats when:
  //   - A new order is placed → order_update with status='pending'
  //   - Order status changes → order_update (processed, shipped, completed, cancelled)
  //   - Payment is confirmed → payment_update (paid)
  //
  // Events are broadcast by the backend via NotificationConsumer WebSocket.
  // The client (WarungioWS) is already connected — we just subscribe to events.

  var _wsRetries = 0;
  var _wsMaxRetries = 10;

  function setupRealtimeUpdates() {
    if (typeof WarungioWS === 'undefined' || typeof WarungioWS.on !== 'function') {
      // WebSocket not yet initialized — retry after a short delay
      if (++_wsRetries >= _wsMaxRetries) return;
      setTimeout(setupRealtimeUpdates, 1000);
      return;
    }

    // When any order is created or status changes, refresh the full list
    WarungioWS.on('order_update', function (data) {
      console.info('[Orders WS] Order update:', data.order_number, '→', data.status);

      // Show brief toast for significant events
      if (data.status === 'pending') {
        window.WarungioToast?.show('Pesanan baru masuk: ' + (data.order_number || ''), 'info');
      }

      // Refresh the entire orders list to stay in sync
      fetchOrders();
    });

    // Also refresh on payment confirmation (pending → paid)
    WarungioWS.on('payment_update', function (data) {
      console.info('[Orders WS] Payment update:', data.order_number, '→', data.status);
      fetchOrders();
    });

    // When WebSocket reconnects after disconnection, refresh to catch missed updates
    WarungioWS.on('connected', function () {
      console.info('[Orders WS] Reconnected — refreshing orders');
      fetchOrders();
    });
  }

  // Initialize real-time WebSocket subscriptions
  setupRealtimeUpdates();

  // Initialize page
  fetchOrders();
});
