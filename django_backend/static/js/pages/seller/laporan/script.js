/**
 * Warungio Seller — Laporan (Report) Page
 * Fetches live data from WarungioAPI, renders charts via Chart.js.
 */
(function () {
  'use strict';

  /* ── Helpers ── */
  function formatRupiah(n) {
    if (typeof n !== 'number' || isNaN(n)) return 'Rp0';
    return 'Rp' + n.toLocaleString('id-ID');
  }
  function formatRupiahShort(n) {
    if (n >= 1e9) return 'Rp' + (n / 1e9).toFixed(1) + 'M';
    if (n >= 1e6) return 'Rp' + (n / 1e6).toFixed(1) + 'jt';
    if (n >= 1e3) return 'Rp' + (n / 1e3).toFixed(0) + 'rb';
    return 'Rp' + n;
  }
  function formatNumber(n) {
    if (typeof n !== 'number') return '0';
    return n.toLocaleString('id-ID');
  }
  function $(id) { return document.getElementById(id); }

  /* ── Welcome Animation ── */
  function showWelcome() {
    var key = 'warungio_laporan_welcomed';
    if (sessionStorage.getItem(key)) return;
    var overlay = $('welcomeOverlay');
    if (!overlay) return;
    // Try to set store name
    if (window.WarungioAPI && typeof WarungioAPI.getMyStore === 'function') {
      WarungioAPI.getMyStore().then(function (res) {
        var name = (res && res.data && res.data.store_name) || 'Seller';
        $('welcomeText').textContent = 'Selamat Datang Kembali, ' + name;
      }).catch(function () {});
    }
    overlay.style.display = 'flex';
    sessionStorage.setItem(key, '1');
    setTimeout(function () {
      overlay.style.opacity = '0';
      overlay.style.transition = 'opacity 0.4s ease';
      setTimeout(function () { overlay.style.display = 'none'; }, 400);
    }, 2000);
  }

  /* ── Sidebar toggle ── */
  function initSidebar() {
    var btn = $('hamburgerBtn');
    var sidebar = $('sidebarNav');
    var overlay = $('sidebarOverlay');
    if (!btn) return;
    btn.addEventListener('click', function () {
      sidebar.classList.toggle('open');
      overlay.classList.toggle('open');
    });
    if (overlay) overlay.addEventListener('click', function () {
      sidebar.classList.remove('open');
      overlay.classList.remove('open');
    });
    var closeBtn = $('sidebarAdsClose');
    if (closeBtn) closeBtn.addEventListener('click', function () {
      closeBtn.parentElement.style.display = 'none';
    });
  }

  /* ── Export dropdown ── */
  function initExport() {
    var btn = $('exportBtn');
    var menu = $('exportMenu');
    if (!btn || !menu) return;
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      menu.classList.toggle('open');
    });
    document.addEventListener('click', function () { menu.classList.remove('open'); });
    menu.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function (e) {
        e.preventDefault();
        var format = a.getAttribute('data-format');
        exportReport(format);
        menu.classList.remove('open');
      });
    });
  }

  function exportReport(format) {
    showToast('Mengekspor laporan sebagai ' + format.toUpperCase() + '...', 'success');
    if ((format === 'csv' || format === 'excel') && window._dailySalesData) {
      var csv = 'Tanggal,Penjualan,Pesanan\n';
      var d = window._dailySalesData;
      for (var i = 0; i < d.labels.length; i++) {
        csv += d.labels[i] + ',' + (d.daily_sales[i] || 0) + ',' + (d.daily_orders[i] || 0) + '\n';
      }
      var type = format === 'excel' ? 'application/vnd.ms-excel' : 'text/csv';
      var blob = new Blob([csv], { type: type });
      var url = URL.createObjectURL(blob);
      var link = document.createElement('a');
      link.href = url;
      link.download = 'laporan-penjualan.' + (format === 'excel' ? 'xls' : 'csv');
      link.click();
      URL.revokeObjectURL(url);
    } else if (format === 'pdf') {
      window.print();
    }
  }

  function showToast(msg, type) {
    var t = document.createElement('div');
    t.className = 'toast ' + (type || '');
    t.innerHTML = '<i class="fa-solid fa-check-circle"></i> ' + msg;
    t.style.display = 'flex';
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 3000);
  }

  /* ── Date Filter ── */
  function getPeriodDays(val) {
    var map = { 'today': 1, '7days': 7, '30days': 30, 'this_month': 30, 'this_year': 365 };
    return map[val] || 30;
  }

  function getDateRangeLabel(days) {
    var end = new Date();
    var start = new Date();
    start.setDate(end.getDate() - days);
    var opts = { day: 'numeric', month: 'short', year: 'numeric' };
    return start.toLocaleDateString('id-ID', opts) + ' - ' + end.toLocaleDateString('id-ID', opts);
  }

  /* ── Chart instances ── */
  var salesChartInstance = null;
  var categoryChartInstance = null;
  var deviceChartInstance = null;

  /* ── Load Dashboard Data ── */
  function loadData(period) {
    var days = getPeriodDays(period);
    var label = $('dateRangeLabel');
    if (label) label.textContent = getDateRangeLabel(days);

    if (window.WarungioAPI && typeof WarungioAPI.getSellerReport === 'function') {
      WarungioAPI.getSellerReport({ period: period }).then(function (res) {
        var d = res && res.data ? res.data : res;
        renderStats(d);
        window._dailySalesData = d.sales_chart || { labels: [], daily_sales: [], daily_orders: [] };
        renderSalesChart(d.sales_chart || {});
        renderDailySalesTable(d.sales_chart || {});
        renderCategoryChart(d.category_sales || []);
        renderDeviceChart(d.device_sales || []);
        renderTopProducts(d.top_products || []);
        renderPerformance(d.performance || {});
      }).catch(function (err) {
        console.error('Seller report error:', err);
        showDeviceEmpty();
        showToast(err.message || 'Gagal memuat laporan.', 'error');
      });
    } else {
      showToast('Endpoint laporan belum tersedia.', 'error');
    }
  }

  /* ── Render Stats ── */
  function renderStats(d) {
    var metrics = d.metrics || d;
    $('totalSales').textContent = formatRupiah(metrics.total_sales || 0);
    $('totalOrders').textContent = formatNumber(metrics.total_orders || 0);
    $('productsSold').textContent = formatNumber(metrics.products_sold || 0);
    $('newCustomers').textContent = formatNumber(metrics.new_customers || 0);
    var rating = metrics.average_rating || metrics.avg_rating || 0;
    $('avgRating').textContent = rating.toFixed(1) + '/5';

    // Set store name
    if (d.store && d.store.store_name) {
      $('shopName').textContent = d.store.store_name;
      $('welcomeText').textContent = 'Selamat Datang Kembali, ' + d.store.store_name;
    }

    var trends = d.trends || {};
    setTrend('salesTrend', trends.total_sales || 0, trendDir(trends.total_sales));
    setTrend('ordersTrend', trends.total_orders || 0, trendDir(trends.total_orders));
    setTrend('productsTrend', trends.products_sold || 0, trendDir(trends.products_sold));
    setTrend('customersTrend', trends.new_customers || 0, trendDir(trends.new_customers));
    setRatingTrend('ratingTrend', trends.average_rating || 0);
  }

  function trendDir(value) {
    value = Number(value || 0);
    if (value > 0) return 'up';
    if (value < 0) return 'down';
    return 'neutral';
  }

  function setTrend(id, pct, dir) {
    var el = $(id);
    if (!el) return;
    el.className = 'stat-trend ' + dir;
    var icon = dir === 'up' ? 'fa-arrow-up' : dir === 'down' ? 'fa-arrow-down' : 'fa-minus';
    el.innerHTML = '<i class="fa-solid ' + icon + '"></i> <span>' + pct.toFixed(1) + '%</span> dari periode sebelumnya';
  }

  function setRatingTrend(id, value) {
    var el = $(id);
    if (!el) return;
    value = Number(value || 0);
    var dir = value > 0 ? 'up' : value < 0 ? 'down' : 'neutral';
    var icon = dir === 'up' ? 'fa-arrow-up' : dir === 'down' ? 'fa-arrow-down' : 'fa-minus';
    el.className = 'stat-trend ' + dir;
    el.innerHTML = '<i class="fa-solid ' + icon + '"></i> <span>' + value.toFixed(1) + '</span> dari periode sebelumnya';
  }

  /* ── Sales Line Chart ── */
  function renderSalesChart(d) {
    var ctx = $('salesChart');
    if (!ctx) return;
    if (salesChartInstance) salesChartInstance.destroy();

    var labels = d.labels || [];
    var sales = d.daily_sales || [];
    var orders = d.daily_orders || [];

    salesChartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Penjualan (Rp)',
            data: sales,
            borderColor: '#16a34a',
            backgroundColor: 'rgba(22, 163, 74, 0.08)',
            fill: true,
            tension: 0.4,
            borderWidth: 2.5,
            pointRadius: 0,
            pointHoverRadius: 5,
            pointHoverBackgroundColor: '#16a34a',
            yAxisID: 'y',
          },
          {
            label: 'Pesanan',
            data: orders,
            borderColor: '#94a3b8',
            borderDash: [5, 3],
            fill: false,
            tension: 0.4,
            borderWidth: 1.5,
            pointRadius: 0,
            pointHoverRadius: 4,
            pointHoverBackgroundColor: '#94a3b8',
            yAxisID: 'y1',
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { intersect: false, mode: 'index' },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#1e293b',
            padding: 12,
            cornerRadius: 8,
            titleFont: { size: 12, family: 'Plus Jakarta Sans' },
            bodyFont: { size: 12, family: 'Plus Jakarta Sans' },
            callbacks: {
              label: function (ctx) {
                if (ctx.datasetIndex === 0) return 'Penjualan: ' + formatRupiah(ctx.raw);
                return 'Pesanan: ' + ctx.raw;
              }
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { font: { size: 10, family: 'Plus Jakarta Sans' }, color: '#94a3b8', maxTicksLimit: 10 }
          },
          y: {
            position: 'left',
            grid: { color: '#f1f5f9' },
            ticks: {
              font: { size: 10, family: 'Plus Jakarta Sans' }, color: '#94a3b8',
              callback: function (v) { return formatRupiahShort(v); }
            }
          },
          y1: {
            position: 'right',
            grid: { display: false },
            ticks: { font: { size: 10, family: 'Plus Jakarta Sans' }, color: '#94a3b8' }
          }
        }
      }
    });
  }

  /* ── Category Pie Chart ── */
  function renderCategoryChart(items) {
    var ctx = $('categoryChart');
    if (!ctx) return;
    if (categoryChartInstance) categoryChartInstance.destroy();

    items = items || [];
    var categories = items.map(function (item) { return item.category; });
    var values = items.map(function (item) { return Number(item.revenue || 0); });
    var total = values.reduce(function (a, b) { return a + b; }, 0);
    var colors = ['#16a34a', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899'];

    $('pieTotalValue').textContent = formatRupiahShort(total);

    if (total === 0 || !items.length) {
      $('categoryLegend').innerHTML = '<div class="device-empty-state"><p>Data kategori belum tersedia</p></div>';
      return;
    }

    categoryChartInstance = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: categories,
        datasets: [{
          data: values,
          backgroundColor: values.map(function (_, i) { return colors[i % colors.length]; }),
          borderWidth: 0,
          cutout: '65%'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#1e293b',
            padding: 10,
            cornerRadius: 8,
            bodyFont: { size: 12, family: 'Plus Jakarta Sans' },
            callbacks: {
              label: function (ctx) {
                return ctx.label + ': ' + formatRupiah(ctx.raw);
              }
            }
          }
        }
      }
    });

    // Build legend
    var legendEl = $('categoryLegend');
    if (legendEl) {
      legendEl.innerHTML = '';
      for (var i = 0; i < categories.length; i++) {
        var pct = items[i].percentage !== undefined ? Number(items[i].percentage).toFixed(1) : (total > 0 ? ((values[i] / total) * 100).toFixed(1) : 0);
        legendEl.innerHTML +=
          '<div class="pie-legend-item">' +
            '<span class="pie-legend-dot" style="background:' + colors[i % colors.length] + '"></span>' +
            '<span class="pie-legend-name">' + categories[i] + '</span>' +
            '<span class="pie-legend-value">' + formatRupiah(values[i]) + ' · ' + pct + '%</span>' +
          '</div>';
      }
    }
  }

  /* ── Device Doughnut Chart ── */
  function renderDeviceChart(items) {
    items = items || [];
    var total = items.reduce(function (sum, item) { return sum + Number(item.count || 0); }, 0);
    if (total === 0) { showDeviceEmpty(); return; }

    var wrapEl = $('deviceChartWrap');
    var emptyEl = $('deviceEmpty');
    if (wrapEl) wrapEl.style.display = '';
    if (emptyEl) emptyEl.style.display = 'none';

    var ctx = $('deviceChart');
    if (!ctx) return;
    if (deviceChartInstance) deviceChartInstance.destroy();

    var labels = items.map(function (item) { return item.device || 'Unknown'; });
    var values = items.map(function (item) { return Number(item.count || 0); });
    var colors = ['#16a34a', '#f59e0b', '#3b82f6'];

    deviceChartInstance = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: values.map(function (_, i) { return colors[i % colors.length]; }),
          borderWidth: 0,
          cutout: '65%'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#1e293b',
            padding: 10,
            cornerRadius: 8,
            bodyFont: { size: 12, family: 'Plus Jakarta Sans' }
          }
        }
      }
    });

    var legendEl = $('deviceLegend');
    if (legendEl) {
      legendEl.innerHTML = '';
      for (var i = 0; i < labels.length; i++) {
        var pct = items[i].percentage !== undefined ? Number(items[i].percentage).toFixed(1) : (total > 0 ? ((values[i] / total) * 100).toFixed(1) : 0);
        legendEl.innerHTML +=
          '<div class="device-legend-item">' +
            '<span class="device-legend-dot" style="background:' + colors[i % colors.length] + '"></span>' +
            '<span class="device-legend-name">' + labels[i] + '</span>' +
            '<span class="device-legend-value">' + pct + '%</span>' +
          '</div>';
      }
    }
  }

  function showDeviceEmpty() {
    var wrapEl = $('deviceChartWrap');
    var emptyEl = $('deviceEmpty');
    if (wrapEl) wrapEl.style.display = 'none';
    if (emptyEl) emptyEl.style.display = 'flex';
  }

  /* ── Top Products Table ── */
  function renderTopProducts(products) {
    var body = $('topProductsBody');
    if (!body) return;
    if (!products || products.length === 0) {
      body.innerHTML = '<tr><td colspan="4" class="empty-cell">Belum ada data produk</td></tr>';
      return;
    }
    body.innerHTML = '';
    products.forEach(function (p, i) {
      var rankClass = i === 0 ? 'rank-1' : i === 1 ? 'rank-2' : i === 2 ? 'rank-3' : 'rank-default';
      var imgSrc = p.product_photo || p.image || '';
      var imgTag = imgSrc ? '<img src="' + imgSrc + '" class="product-mini-img" alt="">' : '';
      var tr = document.createElement('tr');
      tr.innerHTML =
        '<td><div class="product-rank ' + rankClass + '">' + (i + 1) + '</div></td>' +
        '<td><div class="product-name-cell">' + imgTag + '<span>' + (p.product_name || '-') + '</span></div></td>' +
        '<td>' + formatNumber(p.total_sold || 0) + '</td>' +
        '<td>' + formatRupiah(p.total_revenue || 0) + '</td>';
      body.appendChild(tr);
    });
  }

  /* ── Daily Sales Table ── */
  function renderDailySalesTable(d) {
    var body = $('dailySalesBody');
    if (!body) return;
    var labels = d.labels || [];
    var sales = d.daily_sales || [];
    var orders = d.daily_orders || [];

    if (labels.length === 0) {
      body.innerHTML = '<tr><td colspan="3" class="empty-cell">Belum ada data penjualan</td></tr>';
      return;
    }

    // Show last 10 days
    var start = Math.max(0, labels.length - 10);
    body.innerHTML = '';
    for (var i = labels.length - 1; i >= start; i--) {
      var tr = document.createElement('tr');
      tr.innerHTML =
        '<td>' + labels[i] + '</td>' +
        '<td>' + formatRupiah(sales[i] || 0) + '</td>' +
        '<td>' + formatNumber(orders[i] || 0) + '</td>';
      body.appendChild(tr);
    }

    var badge = $('dailySalesPeriod');
    if (badge) badge.textContent = '(' + Math.min(10, labels.length) + ' Hari Terakhir)';
  }

  /* ── Performance Summary ── */
  function renderPerformance(d) {
    d = d || {};
    var bestDay = d.best_day || {};
    var topProduct = d.top_product || {};
    var topCategory = d.top_category || {};
    var topDevice = d.top_device || {};
    var peak = d.new_customers_peak || {};

    $('perfBestDay').textContent = bestDay.label || '-';
    $('perfBestDayValue').textContent = formatRupiah(bestDay.value || 0);
    $('perfTopProduct').textContent = topProduct.product_name || '-';
    $('perfTopProductValue').textContent = topProduct.total_sold ? formatNumber(topProduct.total_sold) + ' terjual' : '-';
    $('perfTopCategory').textContent = topCategory.category || '-';
    $('perfTopCategoryValue').textContent = topCategory.percentage !== undefined ? topCategory.percentage + '%' : '-';
    $('perfTopDevice').textContent = topDevice.device || '-';
    $('perfTopDeviceValue').textContent = topDevice.percentage !== undefined ? topDevice.percentage + '%' : '-';
    $('perfNewCustomersDate').textContent = peak.date || '-';
    $('perfNewCustomersValue').textContent = formatNumber(peak.count || 0);
  }

  /* ── Init ── */
  document.addEventListener('DOMContentLoaded', function () {
    showWelcome();
    initSidebar();
    initExport();

    var filter = $('dateFilter');
    if (filter) {
      filter.addEventListener('change', function () {
        loadData(filter.value);
      });
    }

    // Initial load
    loadData('30days');
  });
})();
