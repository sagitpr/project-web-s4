/**
 * Seller Dashboard - Warungio
 * Connected to Django analytics API and product management.
 */
document.addEventListener('DOMContentLoaded', () => {
  const DEFAULT_DATA = {
    products: [
      { name: 'Selada Keriting', cat: 'Sayuran', status: 'Kurang Segar', statusClass: 'status-orange', issue: 'Kesegaran menurun', action: 'Perbarui Foto' },
      { name: 'Stok Telur Ayam', cat: 'Sembako', status: 'Stok Rendah', statusClass: 'status-yellow', issue: 'Stok di bawah minimum', action: 'Restock' },
      { name: 'Cabai Rawit Merah', cat: 'Bumbu', status: 'Tidak Layak', statusClass: 'status-red', issue: 'Kualitas tidak memenuhi standar', action: 'Hapus' },
    ],
    activities: [
      { msg: 'Pesanan baru #INV/240501/0012', time: '10 Mei 2024, 10:30' },
      { msg: 'Produk Bayam Hijau Segar Lolos Quality Check', time: '10 Mei 2024, 09:45' },
      { msg: 'Pesanan #INV/240501/0011 dikirim', time: '09 Mei 2024, 18:45' },
    ]
  };

  if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
    window.location.href = '../auth/login/index.html';
    return;
  }

  const tableBody = document.getElementById('product-table');
  const actList = document.getElementById('activity-list');
  const addProductForm = document.getElementById('add-product-form');
  const addProductMessage = document.getElementById('add-product-message');
  let chartInstance = null;

  function initChart(feasible = 78, moderate = 42, low = 8, rejected = 10) {
    const ctx = document.getElementById('eligibilityChart')?.getContext('2d');
    if (!ctx) return;
    if (chartInstance) chartInstance.destroy();
    chartInstance = new Chart(ctx, {
      type: 'doughnut',
      data: {
        datasets: [{
          data: [feasible, moderate, low, rejected],
          backgroundColor: ['#22c55e', '#a3e635', '#facc15', '#ef4444'],
          borderWidth: 0, cutout: '80%',
        }]
      },
      options: { plugins: { tooltip: { enabled: false } }, cutout: '80%' }
    });
  }
  initChart();

  function renderProducts(data) {
    if (!tableBody) return;
    tableBody.innerHTML = '';
    (data.products || []).forEach(p => {
      tableBody.innerHTML += '<tr><td><b>' + p.name + '</b></td><td>' + p.cat + '</td><td><span class="status-pill ' + p.statusClass + '">' + p.status + '</span></td><td>' + p.issue + '</td><td><button class="btn-action">' + p.action + '</button></td></tr>';
    });
  }

  function renderActivities(data) {
    if (!actList) return;
    actList.innerHTML = '';
    (data.activities || []).forEach(a => {
      actList.innerHTML += '<div class="activity-item"><b>' + a.msg + '</b><small>' + a.time + '</small></div>';
    });
  }

  function showAddMsg(text, type) {
    if (!addProductMessage) return;
    addProductMessage.textContent = text;
    addProductMessage.className = 'message ' + type;
    addProductMessage.style.display = 'block';
  }

  function showLoadingSkeleton() {
    ['total-sales','new-orders','active-products','store-rating','store-balance'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = '<div class="skeleton skeleton-stat"></div>';
    });
  }
  showLoadingSkeleton();

  async function loadDashboardData() {
    try {
      const data = await WarungioAPI.getDashboardSummary('month');

      const salesEl = document.getElementById('total-sales');
      const ordersEl = document.getElementById('new-orders');
      const productsEl = document.getElementById('active-products');
      const ratingEl = document.getElementById('store-rating');
      const balanceEl = document.getElementById('store-balance');

      if (salesEl) salesEl.textContent = 'Rp ' + Number(data.total_sales || 0).toLocaleString('id-ID');
      if (ordersEl) ordersEl.textContent = data.total_orders || 0;
      if (productsEl) productsEl.textContent = data.total_products || 0;
      if (ratingEl) ratingEl.textContent = (data.average_rating || 0).toFixed(1);
      if (balanceEl) balanceEl.textContent = 'Rp ' + Number(data.total_sales || 0).toLocaleString('id-ID');

      if (actList) {
        actList.innerHTML = '';
        if (data.recent_orders && data.recent_orders.length > 0) {
          data.recent_orders.forEach(o => {
            actList.innerHTML += '<div class="activity-item"><b>Pesanan #' + o.order_number + '</b><small>' + new Date(o.created_at).toLocaleString('id-ID') + ' - Rp ' + Number(o.total_price).toLocaleString('id-ID') + '</small></div>';
          });
        } else {
          renderActivities(DEFAULT_DATA);
        }
      }

      if (data.top_products && data.top_products.length > 0 && tableBody) {
        tableBody.innerHTML = '';
        data.top_products.forEach(p => {
          tableBody.innerHTML += '<tr><td><b>' + p.product_name + '</b></td><td>Terjual: ' + p.total_sold + '</td><td><span class="status-pill status-green">Laris</span></td><td>Penjualan: Rp ' + Number(p.total_revenue).toLocaleString('id-ID') + '</td><td><button class="btn-action">Detail</button></td></tr>';
        });
      } else {
        renderProducts(DEFAULT_DATA);
      }
    } catch (err) {
      console.warn('Dashboard load fallback:', err);
      renderProducts(DEFAULT_DATA);
      renderActivities(DEFAULT_DATA);
    }
  }

  addProductForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(addProductForm);
    const data = Object.fromEntries(formData.entries());
    const btn = addProductForm.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Menyimpan...';

    try {
      await WarungioAPI.createProduct(data);
      showAddMsg('Produk berhasil ditambahkan!', 'success');
      addProductForm.reset();
      loadDashboardData();
    } catch (err) {
      showAddMsg(err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Tambah Produk';
    }
  });

  loadDashboardData();
});
