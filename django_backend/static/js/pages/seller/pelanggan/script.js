/**
 * Warungio Seller — Pelanggan (Customers) Page
 * Fetches seller orders to derive customer insights and displays in a table.
 */
(function () {
  'use strict';

  function formatRupiah(n) {
    if (typeof n !== 'number' || isNaN(n)) return 'Rp0';
    return 'Rp' + n.toLocaleString('id-ID');
  }
  function formatNumber(n) {
    if (typeof n !== 'number') return '0';
    return n.toLocaleString('id-ID');
  }
  function $(id) { return document.getElementById(id); }

  /* ── Helpers ── */
  function getInitials(name) {
    if (!name) return '?';
    var parts = name.split(' ');
    return parts[0][0] + (parts[1] ? parts[1][0] : '');
  }

  function getCustomerBadge(totalOrders, totalSpent) {
    if (totalOrders >= 10) return { text: 'VIP', cls: 'vip' };
    if (totalOrders >= 3) return { text: 'Pembeli Setia', cls: 'regular' };
    if (totalOrders === 1) return { text: 'Pembeli Baru', cls: 'new' };
    return { text: 'Sekali', cls: 'one-time' };
  }

  /* ── Sidebar ── */
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

  /* ── Search & Filter ── */
  var allCustomers = [];
  var currentFilter = 'all';

  function initSearch() {
    var input = $('customerSearch');
    if (!input) return;
    input.addEventListener('input', function () {
      renderTable();
    });
    var filter = $('orderFilter');
    if (filter) {
      filter.addEventListener('change', function () {
        currentFilter = filter.value;
        renderTable();
      });
    }
  }

  function filterCustomers() {
    var query = ($('customerSearch') ? $('customerSearch').value.toLowerCase() : '').trim();
    var list = allCustomers;

    // Search filter
    if (query) {
      list = list.filter(function (c) {
        return (c.name && c.name.toLowerCase().indexOf(query) !== -1) ||
               (c.email && c.email.toLowerCase().indexOf(query) !== -1) ||
               (c.phone && c.phone.indexOf(query) !== -1);
      });
    }

    // Status filter
    if (currentFilter === 'repeat') {
      list = list.filter(function (c) { return c.totalOrders >= 2; });
    } else if (currentFilter === 'new') {
      list = list.filter(function (c) { return c.totalOrders === 1; });
    } else if (currentFilter === 'top') {
      list = list.slice().sort(function (a, b) { return b.totalSpent - a.totalSpent; }).slice(0, 10);
    }

    return list;
  }

  /* ── Load Data ── */
  function loadData() {
    if (window.WarungioAPI && typeof WarungioAPI.getSellerOrders === 'function') {
      WarungioAPI.getSellerOrders({}).then(function (res) {
        var ordersData = res && res.results ? res.results : (Array.isArray(res) ? res : []);
        processOrders(ordersData);
      }).catch(function (err) {
        console.warn('Seller orders fetch failed:', err);
        allCustomers = [];
        renderStats();
        renderTable();
        renderPagination();
      });
    } else {
      allCustomers = [];
      renderStats();
      renderTable();
      renderPagination();
    }
  }

  function processOrders(ordersData) {
    var customerMap = {};

    ordersData.forEach(function (order) {
      var user = order.user || order.buyer || {};
      var userId = user.id || user.email || 'anon_' + order.id;
      var userName = user.full_name || user.name || 'Anonymous';
      var userEmail = user.email || '-';
      var userPhone = user.phone || '-';
      var userAvatar = user.profile_photo || '';

      if (!customerMap[userId]) {
        customerMap[userId] = {
          id: userId,
          name: userName,
          email: userEmail,
          phone: userPhone,
          avatar: userAvatar,
          totalOrders: 0,
          totalSpent: 0,
          lastOrderDate: null,
          firstOrderDate: null,
        };
      }

      var c = customerMap[userId];
      c.totalOrders += 1;
      c.totalSpent += Number(order.total_price || 0);
      var created = order.created_at ? new Date(order.created_at) : null;
      if (created) {
        if (!c.firstOrderDate || created < c.firstOrderDate) c.firstOrderDate = created;
        if (!c.lastOrderDate || created > c.lastOrderDate) c.lastOrderDate = created;
      }
    });

    allCustomers = Object.keys(customerMap).map(function (key) { return customerMap[key]; });
    allCustomers.sort(function (a, b) { return b.totalSpent - a.totalSpent; });

    renderStats();
    renderTable();
    renderPagination();
  }

  /* ── Render Stats ── */
  function renderStats() {
    var totalCustomers = allCustomers.length;
    var activeThreshold = new Date();
    activeThreshold.setDate(activeThreshold.getDate() - 30);
    var activeCustomers = allCustomers.filter(function (c) { return c.lastOrderDate && new Date(c.lastOrderDate) >= activeThreshold; }).length;
    var returningCustomers = allCustomers.filter(function (c) { return c.totalOrders >= 2; }).length;
    var totalSpent = allCustomers.reduce(function (sum, c) { return sum + c.totalSpent; }, 0);
    var avgSpending = totalCustomers > 0 ? totalSpent / totalCustomers : 0;
    var topCustomer = allCustomers.length > 0 ? allCustomers[0] : null;

    $('totalCustomers').textContent = formatNumber(totalCustomers);
    $('activeCustomers').textContent = formatNumber(activeCustomers);
    $('returningCustomers').textContent = formatNumber(returningCustomers);
    $('avgSpending').textContent = formatRupiah(Math.round(avgSpending));
    $('topCustomer').textContent = topCustomer ? topCustomer.name : '-';

    var activePct = totalCustomers > 0 ? Math.round((activeCustomers / totalCustomers) * 100) : 0;
    var activeTrend = $('activeTrend');
    if (activeTrend) {
      activeTrend.innerHTML = '<i class="fa-solid fa-chart-line"></i> <span>' + activePct + '%</span> dari total';
    }
  }

  /* ── Render Table ── */
  function renderTable() {
    var body = $('customerTableBody');
    if (!body) return;

    var filtered = filterCustomers();
    if (filtered.length === 0) {
      body.innerHTML = '<tr><td colspan="7" class="empty-cell">Tidak ada pelanggan ditemukan</td></tr>';
      return;
    }

    body.innerHTML = '';
    filtered.forEach(function (c) {
      var initials = getInitials(c.name);
      var avatarHtml = c.avatar
        ? '<img src="' + c.avatar + '" class="customer-avatar" alt="">'
        : '<div class="customer-avatar">' + initials + '</div>';
      var badge = getCustomerBadge(c.totalOrders, c.totalSpent);
      var lastOrder = c.lastOrderDate ? c.lastOrderDate.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' }) : '-';

      var tr = document.createElement('tr');
      tr.innerHTML =
        '<td><div class="customer-cell">' + avatarHtml + '<div><span class="customer-name">' + escapeHtml(c.name) + '</span><span class="customer-email">' + escapeHtml(c.email) + '</span></div></div></td>' +
        '<td>' + escapeHtml(c.phone) + '</td>' +
        '<td>' + formatNumber(c.totalOrders) + '</td>' +
        '<td>' + formatRupiah(c.totalSpent) + '</td>' +
        '<td>' + lastOrder + '</td>' +
        '<td><span class="badge-customer ' + badge.cls + '">' + badge.text + '</span></td>' +
        '<td style="text-align:right;"><button class="btn-action" data-customer-id="' + c.id + '">Detail</button></td>';
      body.appendChild(tr);
    });
  }

  function escapeHtml(str) {
    if (typeof str !== 'string') return str;
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function renderPagination() {
    var el = $('customerPaginationInfo');
    if (!el) return;
    var filtered = filterCustomers();
    el.textContent = 'Menampilkan ' + filtered.length + ' dari ' + allCustomers.length + ' pelanggan';
  }

  /* ── Init ── */
  document.addEventListener('DOMContentLoaded', function () {
    initSidebar();
    initSearch();

    // Set store name if available
    if (window.WarungioAPI && typeof WarungioAPI.getMyStore === 'function') {
      WarungioAPI.getMyStore().then(function (res) {
        var store = res && res.data ? res.data : res;
        if (store && store.store_name) $('shopName').textContent = store.store_name;
        if (store && store.id) $('shopId').textContent = 'ID Warung: WRG' + store.id;
      }).catch(function () {});
    }

    loadData();
  });
})();
