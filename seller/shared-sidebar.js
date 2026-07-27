/**
 * Warungio Seller Sidebar Injector
 * Ensures consistent sidebar across ALL seller pages.
 * Include this script AFTER auth.js and api.js but BEFORE page-specific scripts.
 * Usage: <script src="../shared-sidebar.js"></script>
 */
(function () {
  'use strict';

  // ── Sidebar menu configuration ──
  var MENU_ITEMS = [
    { label: 'Dashboard', icon: 'fa-house', href: '../dashboard/index.html', id: 'sidebar-dashboard' },
    { label: 'Produk', icon: 'fa-box', href: '../products/index.html', id: 'sidebar-products' },
    { label: 'Pesanan', icon: 'fa-receipt', href: '../orders/index.html', id: 'sidebar-orders' },
    { label: 'Pengiriman', icon: 'fa-truck', href: '#', id: 'sidebar-shipping' },
    { label: 'Pelanggan', icon: 'fa-users', href: '#', id: 'sidebar-customers' },
    { label: 'Promo & Diskon', icon: 'fa-tags', href: '#', id: 'sidebar-promo' },
    { label: 'Keuangan', icon: 'fa-wallet', href: '#', id: 'sidebar-finance' },
    { label: 'Ulasan', icon: 'fa-star', href: '../reviews/index.html', id: 'sidebar-reviews' },
    { label: 'Refund', icon: 'fa-rotate-left', href: '../refunds/index.html', id: 'sidebar-refunds' },
    { label: 'Laporan', icon: 'fa-chart-line', href: '#', id: 'sidebar-reports' },
    { label: 'Pengaturan', icon: 'fa-gear', href: '#', id: 'sidebar-settings' },
    { label: 'Bantuan', icon: 'fa-circle-question', href: '#', id: 'sidebar-help' },
  ];

  // ── Pages where each menu item is "active" ──
  var ACTIVE_MAP = {
    'dashboard/index.html': 'sidebar-dashboard',
    'products/index.html': 'sidebar-products',
    'orders/index.html': 'sidebar-orders',
    'order-detail/index.html': 'sidebar-orders',
    'reviews/index.html': 'sidebar-reviews',
    'refunds/index.html': 'sidebar-refunds',
  };

  function getSidebarHTML(currentPage) {
    var activeId = ACTIVE_MAP[currentPage] || null;

    var html = '';
    html += '<aside class="sidebar">';
    html += '  <div class="logo">';
    html += '    <img src="/static/images/Warungio L.png" alt="logo" />';
    html += '    <div class="logo-text">';
    html += '      <span class="brand-name">Warungio</span>';
    html += '      <small class="brand-tag">Mitra</small>';
    html += '    </div>';
    html += '  </div>';
    html += '  <nav>';

    MENU_ITEMS.forEach(function(item) {
      var isActive = item.id === activeId;
      var cls = isActive ? ' class="active"' : '';
      html += '    <a href="' + item.href + '"' + cls + '><i class="fa-solid ' + item.icon + '"></i> ' + item.label + '</a>';
    });

    html += '    <div style="margin-top:auto;padding-top:12px;border-top:1px solid #e2e8f0;">';
    html += '      <a href="/" style="color:#64748b;font-size:13px;"><i class="fa-solid fa-arrow-left"></i> Lihat Website</a>';
    html += '    </div>';
    html += '  </nav>';
    html += '  <div class="sidebar-ads">';
    html += '    <p>Tingkatkan penjualanmu dengan <b>Warungio Ads</b></p>';
    html += '    <img src="/static/images/ads_penjualan.png" alt="ads" />';
    html += '    <button>Pelajari Sekarang</button>';
    html += '  </div>';
    html += '</aside>';

    return html;
  }

  // ── Auto-inject sidebar into container ──
  // 1. REMOVES any existing sidebar from the page
  // 2. Injects the standardized sidebar
  function injectSidebar() {
    var containers = document.querySelectorAll('.container, .app-shell');
    if (containers.length === 0) return;

    // Determine current page filename
    var pathParts = window.location.pathname.split('/');
    var currentFile = pathParts[pathParts.length - 1] || 'index.html';

    var sidebarHTML = getSidebarHTML(currentFile);

    containers.forEach(function(container) {
      // Remove any existing sidebar, detail-sidebar, or sidebar-related elements
      var existing = container.querySelectorAll('aside.sidebar, aside.detail-sidebar, div.sidebar-ads, div.sidebar-footer');
      existing.forEach(function(el) {
        // Don't remove if it IS the newly injected one
        if (el.getAttribute('data-injected') !== 'true') {
          el.remove();
        }
      });
      // Inject the new sidebar
      var newSidebar = document.createElement('div');
      newSidebar.innerHTML = sidebarHTML;
      var aside = newSidebar.querySelector('aside');
      if (aside) {
        aside.setAttribute('data-injected', 'true');
        container.insertBefore(aside, container.firstChild);
      }
    });
  }

  // ── Run on DOM ready ──
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectSidebar);
  } else {
    injectSidebar();
  }
})();
