/**
 * Orders page - Warungio
 * Manages orders via Django REST API (buyer & seller).
 */
document.addEventListener('DOMContentLoaded', async () => {
  if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
    window.location.href = '../auth/login/index.html';
    return;
  }

  const orderTable = document.getElementById('order-table') || document.querySelector('.order-table tbody');
  const tabButtons = document.querySelectorAll('.tab-btn');
  const searchInput = document.getElementById('search-order');
  const messageEl = document.getElementById('form-message');

  let currentTab = 'all';
  let currentSearch = '';

  function setMsg(text, type = 'error') {
    if (!messageEl) return;
    messageEl.textContent = text;
    messageEl.className = 'form-message ' + type;
    messageEl.style.display = 'block';
    setTimeout(() => { messageEl.style.display = 'none'; }, 4000);
  }

  function statusBadge(status) {
    const map = {
      'pending': '<span class="status-yellow">Menunggu</span>',
      'confirmed': '<span class="status-blue">Dikonfirmasi</span>',
      'processing': '<span class="status-blue">Diproses</span>',
      'shipped': '<span class="status-purple">Dikirim</span>',
      'delivered': '<span class="status-green">Selesai</span>',
      'cancelled': '<span class="status-red">Dibatalkan</span>',
    };
    return map[status] || '<span class="status-yellow">' + status + '</span>';
  }

  // ── Load orders ──
  async function loadOrders(tab = 'all', search = '') {
    if (!orderTable) return;
    try {
      const params = { page: 1, pageSize: 50 };
      if (tab !== 'all') params.status = tab;
      if (search) params.search = search;

      const data = await WarungioAPI.getOrders(params);
      orderTable.innerHTML = '';

      if (data.results && data.results.length > 0) {
        data.results.forEach(o => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td><b>${o.order_number || '#' + o.id}</b></td>
            <td>${new Date(o.created_at).toLocaleDateString('id-ID')}</td>
            <td>${o.items ? o.items.map(i => i.product_name || 'Produk').join(', ') : '-'}</td>
            <td>Rp ${Number(o.total_price).toLocaleString('id-ID')}</td>
            <td>${statusBadge(o.status)}</td>
            <td>${o.payment_status === 'paid' ? '<span class="status-green">Lunas</span>' : '<span class="status-yellow">Belum Bayar</span>'}</td>
            <td>
              <button class="btn-detail" data-id="${o.id}">Detail</button>
              ${o.status === 'pending' ? '<button class="btn-cancel" data-id="' + o.id + '">Batal</button>' : ''}
            </td>`;
          orderTable.appendChild(tr);

          tr.querySelector('.btn-detail')?.addEventListener('click', () => {
            window.location.href = '../order-detail/index.html?id=' + o.id;
          });
          tr.querySelector('.btn-cancel')?.addEventListener('click', async () => {
            if (!confirm('Batalkan pesanan ini?')) return;
            try {
              await WarungioAPI.updateOrderStatus(o.id, 'cancelled');
              setMsg('Pesanan #' + o.id + ' dibatalkan.', 'success');
              loadOrders(currentTab, currentSearch);
            } catch (err) {
              setMsg(err.message || 'Gagal membatalkan pesanan.');
            }
          });
        });
      } else {
        orderTable.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:2rem;">Belum ada pesanan.</td></tr>';
      }
    } catch (err) {
      console.warn('Load orders fallback:', err);
      orderTable.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:2rem;">Gagal memuat pesanan.</td></tr>';
    }
  }

  // ── Tab switching ──
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      tabButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentTab = btn.dataset.tab || 'all';
      currentSearch = '';
      if (searchInput) searchInput.value = '';
      loadOrders(currentTab);
    });
  });

  // ── Search ──
  searchInput?.addEventListener('input', () => {
    currentSearch = searchInput.value.trim();
    loadOrders(currentTab, currentSearch);
  });

  // ── Init notification widget ──
  if (window.WarungioNotifications) {
    setTimeout(() => {
      WarungioNotifications.init('#notifContainer');
    }, 100);
  }

  // ── Listen for real-time order updates ──
  document.addEventListener('warungio:order_update', (e) => {
    const data = e.detail;
    if (data.order_id) {
      console.info('Order update received:', data.order_number, '-', data.status);
      // Reload orders to reflect changes
      loadOrders(currentTab, currentSearch);
      if (refreshStatus) refreshStatus.textContent = 'Diperbarui: ' + new Date().toLocaleTimeString('id-ID');
      if (lastUpdated) lastUpdated.textContent = new Date().toLocaleString('id-ID');
    }
  });

  document.addEventListener('warungio:payment_update', (e) => {
    const data = e.detail;
    if (data.order_id) {
      console.info('Payment update received:', data.order_number, '-', data.status);
      loadOrders(currentTab, currentSearch);
    }
  });

  // ── Init ──
  loadOrders();
});
