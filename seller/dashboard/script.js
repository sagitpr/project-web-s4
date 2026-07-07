/**
 * Seller Dashboard - Warungio
 * Connected to Django analytics API and product management.
 */
document.addEventListener('DOMContentLoaded', () => {
  if (window.WarungioAuth && window.WarungioAuth.requireVerified && window.WarungioAuth.requireVerified()) {
    return;
  }

  const tableBody = document.getElementById('product-table');
  const actList = document.getElementById('activity-list');
  const addProductForm = document.getElementById('add-product-form');
  const addProductMessage = document.getElementById('add-product-message');
  let chartInstance = null;

  function initChart(feasible = 0, moderate = 0, low = 0, rejected = 0) {
    const ctx = document.getElementById('eligibilityChart')?.getContext('2d');
    if (!ctx) return;
    if (chartInstance) chartInstance.destroy();
    const total = feasible + moderate + low + rejected;
    const chartData = total > 0
      ? [feasible, moderate, low, rejected]
      : [1]; // Placeholder gray dot when no data
    const chartColors = total > 0
      ? ['#22c55e', '#a3e635', '#facc15', '#ef4444']
      : ['#e5e7eb'];
    chartInstance = new Chart(ctx, {
      type: 'doughnut',
      data: {
        datasets: [{
          data: chartData,
          backgroundColor: chartColors,
          borderWidth: 0, cutout: '80%',
        }]
      },
      options: { plugins: { tooltip: { enabled: total > 0 } }, cutout: '80%' }
    });
  }
  initChart();

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
          actList.innerHTML = '<div class="activity-item" style="text-align:center;color:var(--color-text-tertiary);padding:20px;">Belum ada aktivitas terbaru</div>';
        }
      }

      if (data.top_products && data.top_products.length > 0 && tableBody) {
        tableBody.innerHTML = '';
        data.top_products.forEach(p => {
          tableBody.innerHTML += '<tr><td><b>' + p.product_name + '</b></td><td>Terjual: ' + p.total_sold + '</td><td><span class="status-pill status-green">Laris</span></td><td>Penjualan: Rp ' + Number(p.total_revenue).toLocaleString('id-ID') + '</td><td><button class="btn-action">Detail</button></td></tr>';
        });
      } else if (tableBody) {
        tableBody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--color-text-tertiary);padding:20px;">Belum ada data produk</td></tr>';
      }
    } catch (err) {
      console.warn('Dashboard load fallback:', err);
      if (tableBody) tableBody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#ef4444;padding:20px;">Gagal memuat data produk</td></tr>';
      if (actList) actList.innerHTML = '<div class="activity-item" style="text-align:center;color:#ef4444;padding:20px;">Gagal memuat aktivitas</div>';
    }
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
