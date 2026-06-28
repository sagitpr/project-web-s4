/**
 * Halaman Pesanan Saya - JavaScript Controller
 * Integrasi API Warungio backend untuk melacak & mengelola pesanan.
 */

document.addEventListener('DOMContentLoaded', async () => {
  // Auth guard: redirect to login if not authenticated
  if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
    window.location.href = '/auth/login/';
    return;
  }

  // DOM Elements
  const ordersListContainer = document.getElementById('ordersListContainer');
  const activeTrackingCard = document.getElementById('activeTrackingCard');
  const orderDetailSideCard = document.getElementById('orderDetailSideCard');
  const cancelModal = document.getElementById('cancelModal');
  const tabBtns = document.querySelectorAll('.tab-btn[data-status]');
  
  // State
  let currentStatus = 'all';
  let activeOrderCoordinates = null;
  let orderIdToCancel = null;

  // Status mappings
  const STATUS_LABELS = {
    pending: 'Menunggu',
    paid: 'Lunas',
    processed: 'Diproses',
    shipped: 'Dikirim',
    on_delivery: 'Dikirim',
    completed: 'Selesai',
    delivered: 'Selesai',
    cancelled: 'Dibatalkan',
  };

  /**
   * Helper to format numbers to IDR currency
   */
  function formatIDR(amount) {
    return 'Rp ' + Number(amount || 0).toLocaleString('id-ID');
  }

  /**
   * Helper to format date string
   */
  function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('id-ID', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    }) + ' ' + date.toLocaleTimeString('id-ID', {
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  /**
   * Load and render order list based on status filter
   */
  async function loadOrders(status) {
    if (!ordersListContainer) return;
    ordersListContainer.innerHTML = `
      <div style="text-align:center;padding:40px;color:var(--color-text-muted);font-size:13px;">
        <span class="spinner" style="border-top-color:var(--color-primary);margin-bottom:10px;"></span>
        <p>Memuat daftar pesanan...</p>
      </div>
    `;

    try {
      const params = { page: 1, pageSize: 50 };
      if (status && status !== 'all') {
        params.order_status = status;
      }

      const data = await WarungioAPI.getOrders(params);
      const orders = data.results || [];

      if (orders.length === 0) {
        ordersListContainer.innerHTML = `
          <div class="empty-state">
            <img src="/static/images/list.png" alt="No orders" />
            <h3>Belum ada pesanan</h3>
            <p>Yuk mulai belanja kebutuhan harianmu di Warungio!</p>
            <a href="/home/" class="btn-primary">Belanja Sekarang</a>
          </div>
        `;
        activeTrackingCard.style.display = 'none';
        orderDetailSideCard.style.display = 'none';
        return;
      }

      ordersListContainer.innerHTML = '';
      
      // Look for the first active delivery order (pending, paid, processed, shipped, on_delivery)
      const activeOrder = orders.find(o => 
        ['pending', 'paid', 'processed', 'shipped', 'on_delivery'].includes(o.order_status.toLowerCase())
      );

      if (activeOrder) {
        populateActiveOrder(activeOrder);
        populateSideDetail(activeOrder);
      } else {
        // Fallback to the first completed/cancelled order for detail sidebar
        populateSideDetail(orders[0]);
        activeTrackingCard.style.display = 'none';
      }

      orders.forEach(order => {
        const statusKey = (order.order_status || 'pending').toLowerCase();
        const statusLabel = STATUS_LABELS[statusKey] || order.order_status;
        const itemNames = order.items ? order.items.map(i => i.product_name).join(', ') : 'Produk';
        const truncatedItems = itemNames.length > 50 ? itemNames.substring(0, 47) + '...' : itemNames;
        
        // Define Action Button based on status
        let actionBtnHtml = '';
        if (statusKey === 'shipped' || statusKey === 'on_delivery') {
          actionBtnHtml = `
            <button class="btn-order-action btn-lacak-item" data-id="${order.id}">
              Lacak Pesanan
            </button>
          `;
        } else if (statusKey === 'completed' || statusKey === 'delivered') {
          actionBtnHtml = `
            <button class="btn-order-action btn-pesan-lagi" data-id="${order.id}">
              🔄 Pesan Lagi
            </button>
          `;
        } else if (statusKey === 'pending') {
          actionBtnHtml = `
            <button class="btn-order-action danger btn-batalkan-pesanan" data-id="${order.id}">
              Batalkan
            </button>
          `;
        }

        const card = document.createElement('div');
        card.className = 'order-history-card';
        card.innerHTML = `
          <div class="order-img-wrapper">
            <img src="${order.store_logo || '/static/images/store-icon-T.png'}" alt="Store Logo" />
          </div>
          <div class="order-info-mid">
            <div class="order-invoice-row">
              <a href="/buyer/order-detail/?id=${order.id}" class="order-inv-num">${order.order_number}</a>
              <span class="status-badge ${statusKey}">${statusLabel}</span>
            </div>
            <div class="order-store-name">${order.store_name || 'Warung'}</div>
            <div class="order-date-text">${formatDate(order.created_at)}</div>
          </div>
          <div class="order-price-col">
            <span>${formatIDR(order.total_price)}</span>
          </div>
          <div class="order-actions-col">
            ${actionBtnHtml}
            <a href="/buyer/order-detail/?id=${order.id}" class="chevron-link">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 5l7 7-7 7" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </a>
          </div>
        `;
        ordersListContainer.appendChild(card);
      });

      // Bind events to dynamically created buttons
      bindCardActions();

    } catch (err) {
      console.error('Gagal memuat pesanan:', err);
      ordersListContainer.innerHTML = `
        <div style="text-align:center;padding:40px;color:red;font-size:13px;">
          Gagal memuat pesanan. Silakan coba lagi.
        </div>
      `;
    }
  }

  /**
   * Populate and display the active tracking timeline card
   */
  async function populateActiveOrder(order) {
    const invNumEl = document.getElementById('activeOrderNumber');
    const statusEl = document.getElementById('activeOrderStatus');
    const trackingBtn = document.getElementById('btnLacakPeta');

    if (invNumEl) invNumEl.textContent = `Pesanan ${order.order_number}`;
    if (statusEl) {
      const statusKey = order.order_status.toLowerCase();
      statusEl.textContent = STATUS_LABELS[statusKey] || order.order_status;
      statusEl.className = `badge status-badge ${statusKey}`;
    }

    activeTrackingCard.style.display = 'block';

    try {
      const tracking = await WarungioAPI.getDeliveryTracking(order.id);
      if (tracking) {
        activeOrderCoordinates = {
          latitude: tracking.latitude,
          longitude: tracking.longitude
        };

        // Milestone step mapping
        let maxStep = 1;
        tracking.milestones.forEach(m => {
          if (m.step > maxStep) maxStep = m.step;
        });

        // 6 steps mapped to 5 UI nodes
        const stepMappings = {
          1: 1, // Pesanan Dibuat
          2: 2, // Diproses Warung
          3: 3, // Dijemput Kurir
          4: 3, // Dijemput Kurir
          5: 4, // Dalam Pengiriman
          6: 5  // Sampai Tujuan
        };

        const activeMilestone = stepMappings[maxStep] || 1;

        // Set status classes on UI circles
        for (let i = 1; i <= 5; i++) {
          const stepEl = document.getElementById(`step-${i}`);
          if (stepEl) {
            stepEl.classList.remove('completed', 'active');
            if (i < activeMilestone) {
              stepEl.classList.add('completed');
            } else if (i === activeMilestone) {
              if (order.order_status.toLowerCase() === 'completed' && i === 5) {
                stepEl.classList.add('completed');
              } else {
                stepEl.classList.add('active');
              }
            }
          }
        }

        // Set line progress percentage
        const progressLine = document.getElementById('timelineProgressLine');
        if (progressLine) {
          progressLine.style.width = `${(activeMilestone - 1) * 25}%`;
        }

        // Set milestone times
        tracking.milestones.forEach(m => {
          const milestoneIdx = stepMappings[m.step];
          const timeEl = document.getElementById(`time-step-${milestoneIdx}`);
          if (timeEl && m.time) {
            const date = new Date(m.time);
            timeEl.textContent = date.toLocaleDateString('id-ID', { day: 'numeric', month: 'short' }) + ' ' + date.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
          }
        });

        // Set estimasi text
        const estimasiEl = document.getElementById('activeOrderEstimasi');
        if (estimasiEl) {
          if (tracking.estimated_time) {
            estimasiEl.textContent = `Estimasi sampai: ${tracking.estimated_time}`;
          } else {
            estimasiEl.textContent = 'Estimasi sampai: sedang dihitung...';
          }
        }
      }
    } catch (err) {
      console.warn('Failed to load delivery tracking details:', err);
    }
  }

  /**
   * Populate right sidebar detail card
   */
  async function populateSideDetail(order) {
    try {
      // Fetch full order detail to get complete items/delivery information
      const detailedOrder = await WarungioAPI.getOrder(order.id);
      if (!detailedOrder) return;

      orderDetailSideCard.style.display = 'block';

      const storeNameEl = document.getElementById('sideStoreName');
      const productCountEl = document.getElementById('sideProductCount');
      const totalPriceEl = document.getElementById('sideTotalPrice');
      const shippingCostEl = document.getElementById('sideShippingCost');
      const paymentMethodEl = document.getElementById('sidePaymentMethod');
      const addressEl = document.getElementById('sideAddress');
      
      const btnSideDetail = document.getElementById('btnSideDetail');
      const btnSideProducts = document.getElementById('btnSideProducts');

      if (storeNameEl) storeNameEl.textContent = detailedOrder.store_name || 'Warungio';
      if (productCountEl) {
        const count = detailedOrder.items ? detailedOrder.items.length : 0;
        productCountEl.textContent = `${count} Produk`;
      }
      if (totalPriceEl) totalPriceEl.textContent = formatIDR(detailedOrder.total_price);
      if (shippingCostEl) shippingCostEl.textContent = formatIDR(detailedOrder.shipping_cost);
      if (paymentMethodEl) {
        const pm = (detailedOrder.payment_method || 'midtrans').toUpperCase();
        paymentMethodEl.textContent = pm === 'COD' ? 'COD (Bayar di Tempat)' : pm;
      }
      if (addressEl) addressEl.textContent = detailedOrder.delivery_address || '-';

      const detailUrl = `/buyer/order-detail/?id=${detailedOrder.id}`;
      if (btnSideDetail) btnSideDetail.href = detailUrl;
      if (btnSideProducts) btnSideProducts.href = detailUrl;

    } catch (err) {
      console.warn('Failed to populate sidebar order details:', err);
    }
  }

  /**
   * Bind click event handlers to order action buttons
   */
  function bindCardActions() {
    // "Lacak Pesanan" button
    document.querySelectorAll('.btn-lacak-item').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const id = btn.dataset.id;
        window.location.href = `/buyer/order-detail/?id=${id}`;
      });
    });

    // "Pesan Lagi" button
    document.querySelectorAll('.btn-pesan-lagi').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const id = btn.dataset.id;
        handleReorder(id);
      });
    });

    // "Batalkan" button
    document.querySelectorAll('.btn-batalkan-pesanan').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = btn.dataset.id;
        showCancelModal(id);
      });
    });
  }

  /**
   * Process Cart Reorder
   */
  async function handleReorder(orderId) {
    if (typeof window.showToast === 'function') {
      window.showToast('Menambahkan produk ke keranjang...', 'info');
    }
    try {
      const order = await WarungioAPI.getOrder(orderId);
      if (order && order.items) {
        for (const item of order.items) {
          await WarungioAPI.addToCart({
            product: item.product,
            qty: item.qty
          });
        }
        if (typeof window.showToast === 'function') {
          window.showToast('Produk berhasil dimasukkan ke keranjang!', 'success');
        }
        setTimeout(() => {
          window.location.href = '/buyer/cart/';
        }, 800);
      }
    } catch (err) {
      console.error('Failed to reorder:', err);
      if (typeof window.showToast === 'function') {
        window.showToast('Gagal memproses Pesan Lagi.', 'error');
      }
    }
  }

  /**
   * Modal actions for cancellation
   */
  function showCancelModal(orderId) {
    orderIdToCancel = orderId;
    if (cancelModal) cancelModal.style.display = 'flex';
  }

  function hideCancelModal() {
    orderIdToCancel = null;
    if (cancelModal) cancelModal.style.display = 'none';
  }

  async function handleCancelOrder() {
    if (!orderIdToCancel) return;
    if (typeof window.showToast === 'function') {
      window.showToast('Membatalkan pesanan...', 'info');
    }
    try {
      await WarungioAPI.cancelOrder(orderIdToCancel, 'change_mind', 'Dibatalkan oleh pembeli');
      if (typeof window.showToast === 'function') {
        window.showToast('Pesanan berhasil dibatalkan.', 'success');
      }
      hideCancelModal();
      loadOrders(currentStatus);
    } catch (err) {
      console.error('Failed to cancel order:', err);
      if (typeof window.showToast === 'function') {
        window.showToast('Gagal membatalkan pesanan.', 'error');
      }
      hideCancelModal();
    }
  }

  // Cancel Modal Event Listeners
  const btnDismissCancel = document.getElementById('btnDismissCancel');
  const btnConfirmCancel = document.getElementById('btnConfirmCancel');
  
  if (btnDismissCancel) btnDismissCancel.addEventListener('click', hideCancelModal);
  if (btnConfirmCancel) btnConfirmCancel.addEventListener('click', handleCancelOrder);

  // Tab Filtering Listeners
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentStatus = btn.dataset.status || 'all';
      loadOrders(currentStatus);
    });
  });

  // Lacak di Peta action
  const btnLacakPeta = document.getElementById('btnLacakPeta');
  if (btnLacakPeta) {
    btnLacakPeta.addEventListener('click', () => {
      if (activeOrderCoordinates && activeOrderCoordinates.latitude && activeOrderCoordinates.longitude) {
        const url = `https://www.google.com/maps?q=${activeOrderCoordinates.latitude},${activeOrderCoordinates.longitude}`;
        window.open(url, '_blank');
      } else {
        if (typeof window.showToast === 'function') {
          window.showToast('Titik kurir belum tersedia.', 'error');
        }
      }
    });
  }

  // ── Profile Dropdown Binding ──
  function bindDropdownMenu() {
    const profileBox = document.getElementById('profileBox');
    const dropdownMenu = document.getElementById('dropdownMenu');
    const btnLogout = document.getElementById('btnLogout');

    if (profileBox && dropdownMenu) {
      profileBox.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdownMenu.classList.toggle('show');
      });

      document.addEventListener('click', () => {
        dropdownMenu.classList.remove('show');
      });
    }

    if (btnLogout) {
      btnLogout.addEventListener('click', (e) => {
        e.preventDefault();
        if (window.WarungioAuth) {
          window.WarungioAuth.logout();
          window.location.href = '/home/';
        }
      });
    }
  }

  // ── Load User Profile ──
  async function loadUserProfile() {
    try {
      const u = await WarungioAPI.checkAuth();
      if (u && u.user) {
        const userNameEl = document.getElementById('userName');
        const userAvatarEl = document.getElementById('userAvatar');
        const userRoleBadge = document.getElementById('userRoleBadge');

        const displayName = u.user.full_name || u.user.email;
        if (userNameEl) userNameEl.textContent = `Hai, ${displayName}`;
        if (u.user.profile_photo && userAvatarEl) {
          userAvatarEl.src = u.user.profile_photo;
        }
        if (userRoleBadge) {
          userRoleBadge.textContent = u.user.role === 'seller' ? 'Penjual' : 'Member';
        }
      }
    } catch (err) {
      console.warn('Failed to load user profile:', err);
    }
  }

  // Initial Load
  bindDropdownMenu();
  await loadUserProfile();
  loadOrders('all');
});
