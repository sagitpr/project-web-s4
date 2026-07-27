/**
 * Warungio Navigation — mobile menu + bottom tab bar + seller profile loader
 */
(function () {
  'use strict';

  // ── Seller Profile Loader (runs on seller pages only) ──
  function loadSellerProfile() {
    if (!window.WarungioAPI || !window.WarungioAuth) return;
    // Don't run on guest / non-authenticated pages
    if (typeof WarungioAuth.isAuthenticated === 'function' && !WarungioAuth.isAuthenticated()) return;

    // Load user info from auth module (sync, already loaded)
    var user = null;
    if (typeof WarungioAuth.getUser === 'function') {
      try { user = WarungioAuth.getUser(); } catch(e) { /* not available */ }
    }

    if (user) {
      var nameEl = document.getElementById('profileName');
      if (nameEl && user.full_name) nameEl.textContent = user.full_name;

      var avatarEl = document.getElementById('profileAvatar');
      if (avatarEl && user.profile_photo) avatarEl.src = user.profile_photo;

      var sellerNameEl = document.getElementById('sellerName');
      if (sellerNameEl && user.full_name) sellerNameEl.textContent = user.full_name;
    }

    // Load store info from API (async)
    if (typeof WarungioAPI.getMyStore === 'function') {
      WarungioAPI.getMyStore().then(function (res) {
        var store = res && res.data ? res.data : res;
        if (!store) return;

        var shopNameEl = document.getElementById('shopName');
        if (shopNameEl) {
          // Remove skeleton span if present
          var skeleton = shopNameEl.querySelector('.skeleton');
          if (skeleton) skeleton.remove();
          shopNameEl.textContent = store.store_name || 'Warung';
        }

        var shopIdEl = document.getElementById('shopId');
        if (shopIdEl) {
          var sid = store.slug ? store.slug.toUpperCase() : (store.id ? 'WRG' + store.id : '---');
          var skeleton2 = shopIdEl.querySelector('.skeleton');
          if (skeleton2) skeleton2.remove();
          shopIdEl.textContent = 'ID Warung: ' + sid;
        }

        var headerLogo = document.getElementById('headerStoreLogo');
        if (headerLogo && store.store_logo) {
          headerLogo.src = store.store_logo;
          headerLogo.style.display = 'inline-block';
        }

        var headerShopName = document.getElementById('headerShopName');
        if (headerShopName) headerShopName.textContent = store.store_name || 'Warung';
      }).catch(function (err) { console.warn('Store profile load failed:', err); });
    }

    // Load user profile photo from auth if available
    if (typeof WarungioAuth.refreshUser === 'function') {
      WarungioAuth.refreshUser().then(function (u) {
        if (!u) return;
        var avatarEl = document.getElementById('profileAvatar');
        if (avatarEl && u.profile_photo) avatarEl.src = u.profile_photo;
        var nameEl = document.getElementById('profileName');
        if (nameEl && u.full_name) nameEl.textContent = u.full_name;
      }).catch(function (err) { console.warn('User profile refresh failed:', err); });
    }
  }

  // ── Sidebar Badge Loader (order count + loyalty points) ──
  function loadSidebarBadges() {
    if (!window.WarungioAPI || !window.WarungioAuth) return;
    if (typeof WarungioAuth.isAuthenticated === 'function' && !WarungioAuth.isAuthenticated()) return;

    // Order badge — count active orders
    var orderBadge = document.getElementById('sidebarOrderBadge');
    if (orderBadge && typeof WarungioAPI.getOrders === 'function') {
      WarungioAPI.getOrders({ page: 1, page_size: 1 })
        .then(function (data) {
          var total = data.count || (data.results ? data.results.length : 0);
          orderBadge.textContent = total > 0 ? total : '';
          orderBadge.style.display = total > 0 ? 'inline' : 'none';
        })
        .catch(function () {
          orderBadge.style.display = 'none';
        });
    }

    // Points badge — load from loyalty API
    var pointsEl = document.getElementById('sidebarPointsValue');
    if (pointsEl) {
      if (typeof WarungioAuth.api === 'function') {
        WarungioAuth.api('/api/loyalty/account/')
          .then(function (data) {
            var pts = data.points_balance || 0;
            pointsEl.textContent = pts.toLocaleString('id-ID') + ' Poin';
          })
          .catch(function () {
            pointsEl.textContent = '0 Poin';
          });
      }
    }
  }

  // ── Realtime Sidebar Badges via WebSocket ──
  function initRealtimeSidebarBadges() {
    if (!window.WarungioWS || typeof WarungioWS.on !== 'function') return;

    // When order status changes, reload badges
    WarungioWS.on('order_update', function () {
      setTimeout(loadSidebarBadges, 1000);
    });

    // When payment confirmed, reload badges
    WarungioWS.on('payment_update', function () {
      setTimeout(loadSidebarBadges, 1000);
    });

    // When new notification arrives, reload badges
    WarungioWS.on('notification', function () {
      setTimeout(loadSidebarBadges, 1000);
    });

    // When wallet is updated, reload badges
    WarungioWS.on('wallet_update', function () {
      setTimeout(loadSidebarBadges, 1000);
    });
  }

  function initMobileMenu() {
    var btn = document.querySelector('.mobile-menu-btn') || document.getElementById('mobileMenuBtn');
    var drawer = document.getElementById('mobileNavDrawer');
    var overlay = document.getElementById('mobileNavOverlay');
    if (!btn || !drawer) return;

    function close() {
      drawer.classList.remove('open');
      if (overlay) overlay.classList.remove('open');
      document.body.style.overflow = '';
    }

    function open() {
      drawer.classList.add('open');
      if (overlay) overlay.classList.add('open');
      document.body.style.overflow = 'hidden';
    }

    btn.addEventListener('click', function () {
      if (drawer.classList.contains('open')) close();
      else open();
    });

    if (overlay) overlay.addEventListener('click', close);
    drawer.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', close);
    });
  }

  function initSidebarToggle() {
    var toggle = document.getElementById('menuToggle');
    var sidebar = document.querySelector('.page-shell .sidebar') || document.querySelector('.sidebar');
    if (!toggle || !sidebar) return;

    toggle.addEventListener('click', function () {
      sidebar.classList.toggle('open');
    });
  }

  function markActiveBottomNav() {
    var path = window.location.pathname;
    document.querySelectorAll('.bottom-nav a').forEach(function (a) {
      var href = a.getAttribute('href');
      if (href && path.indexOf(href.replace(/\/$/, '')) === 0) {
        a.classList.add('active');
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadSellerProfile();
    loadSidebarBadges();
    initRealtimeSidebarBadges();
    initMobileMenu();
    initSidebarToggle();
    markActiveBottomNav();
    if (document.querySelector('.bottom-nav')) {
      document.body.classList.add('has-bottom-nav');
    }
  });

  // Also call on auth_ready event for pages loaded before auth initialized
  document.addEventListener('warungio:auth_ready', function () {
    loadSellerProfile();
  });
})();
