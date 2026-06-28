/**
 * Reports / Laporan page - Warungio (Seller)
 * Displays sales analytics and reports from Django analytics API.
 */
document.addEventListener('DOMContentLoaded', async () => {
  if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
    window.location.href = '../auth/login/index.html';
    return;
  }

  const periodButtons = document.querySelectorAll('.period-btn');
  const salesChart = document.getElementById('sales-chart');
  const totalSalesEl = document.getElementById('total-sales');
  const totalOrdersEl = document.getElementById('total-orders');
  const avgOrderEl = document.getElementById('avg-order');
  const topProductsEl = document.getElementById('top-products');
  const recentOrdersEl = document.getElementById('recent-orders');
  const exportBtn = document.getElementById('export-btn');

  let currentPeriod = 'month';
  let chartInstance = null;

  function formatCurrency(val) {
    return 'Rp ' + Number(val || 0).toLocaleString('id-ID');
  }

  function setMsg(text, type) {
    const el = document.getElementById('form-message');
    if (!el) return;
    el.textContent = text;
    el.className = 'form-message ' + (type || 'error');
    el.style.display = 'block';
    setTimeout(() => { el.style.display = 'none'; }, 4000);
  }

  async function loadAnalytics(period) {
    period = period || 'month';
    try {
      const data = await WarungioAPI.getDashboardSummary(period);

      if (totalSalesEl) totalSalesEl.textContent = formatCurrency(data.total_sales);
      if (totalOrdersEl) totalOrdersEl.textContent = data.total_orders || 0;
      if (avgOrderEl) avgOrderEl.textContent = formatCurrency(
        data.total_orders > 0 ? data.total_sales / data.total_orders : 0
      );

      if (salesChart && data.daily_sales) {
        const ctx = salesChart.getContext('2d');
        if (chartInstance) chartInstance.destroy();

        const labels = data.daily_sales.map(d => {
          const date = new Date(d.date);
          return date.toLocaleDateString('id-ID', { day: 'numeric', month: 'short' });
        });
        const values = data.daily_sales.map(d => Number(d.total));

        chartInstance = new Chart(ctx, {
          type: 'line',
          data: {
            labels,
            datasets: [{
              label: 'Penjualan',
              data: values,
              borderColor: '#22c55e',
              backgroundColor: 'rgba(34, 197, 94, 0.1)',
              fill: true,
              tension: 0.4,
            }]
          },
          options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
              y: { beginAtZero: true, ticks: { callback: v => 'Rp ' + Number(v).toLocaleString('id-ID') } }
            }
          }
        });
      }

      if (topProductsEl && data.top_products) {
        topProductsEl.innerHTML = '';
        data.top_products.slice(0, 10).forEach((p, i) => {
          topProductsEl.innerHTML += '<tr><td>' + (i + 1) + '</td><td>' + p.product_name + '</td><td>' + (p.total_sold || 0) + '</td><td>' + formatCurrency(p.total_revenue) + '</td></tr>';
        });
      }

      if (recentOrdersEl && data.recent_orders) {
        recentOrdersEl.innerHTML = '';
        data.recent_orders.slice(0, 10).forEach(o => {
          recentOrdersEl.innerHTML += '<tr><td>' + (o.order_number || '#' + o.id) + '</td><td>' + new Date(o.created_at).toLocaleDateString('id-ID') + '</td><td>' + formatCurrency(o.total_price) + '</td><td><span class="badge ' + (o.status === 'completed' || o.status === 'delivered' ? 'badge-success' : 'badge-info') + '">' + o.status + '</span></td></tr>';
        });
      }
    } catch (err) {
      console.warn('Analytics load fallback:', err);
      setMsg('Gagal memuat data laporan.', 'error');
    }
  }

  periodButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      periodButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentPeriod = btn.dataset.period || 'month';
      loadAnalytics(currentPeriod);
    });
  });

  exportBtn?.addEventListener('click', () => {
    setMsg('Fitur ekspor laporan akan segera tersedia.', 'success');
  });

  loadAnalytics(currentPeriod);
});
