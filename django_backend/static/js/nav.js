/**
 * Warungio Navigation — mobile menu + bottom tab bar + profile loader (Seller + Buyer)
 */
(function () {
  'use strict';

  // ── Profile Loader (runs on ALL authenticated pages) ──
  function loadProfile() {
    if (!window.WarungioAPI || !window.WarungioAuth) {
      // Retry if auth not loaded yet
      setTimeout(loadProfile, 500);
      return;
    }
    if (typeof WarungioAuth.isAuthenticated === 'function' && !WarungioAuth.isAuthenticated()) return;

    console.debug('[nav.js] Loading profile...');

    // Load user info from auth module (sync from localStorage)
    var user = null;
    if (typeof WarungioAuth.getUser === 'function') {
      try { user = WarungioAuth.getUser(); } catch(e) { console.warn('[nav.js] getUser failed:', e); }
    }

    function updateNameAvatar(u) {
      if (!u) return;
      var nameEl = document.getElementById('profileName');
      if (nameEl) {
        var skeleton = nameEl.querySelector('.skeleton');
        if (skeleton) skeleton.remove();
        if (u.full_name) nameEl.textContent = u.full_name;
      }

      var sellerNameEl = document.getElementById('sellerName');
      if (sellerNameEl) sellerNameEl.textContent = u.full_name || '';

      var avatarEl = document.getElementById('profileAvatar');
      if (avatarEl) {
        if (u.profile_photo && typeof u.profile_photo === 'string' && (u.profile_photo.startsWith('http') || u.profile_photo.startsWith('/'))) {
          avatarEl.src = u.profile_photo;
        } else {
          // Fallback: use initial
          avatarEl.src = '/static/images/av-siti.png';
        }
      }
    }

    // First pass: from cached user (sync, instant)
    if (user) updateNameAvatar(user);

    // Second pass: refresh from API (async, gets latest data)
    function refreshFromAPI() {
      var retries = 0;
      var maxRetries = 3;

      function tryRefresh() {
        if (typeof WarungioAuth.api !== 'function') {
          if (retries < maxRetries) {
            retries++;
            setTimeout(tryRefresh, 1000);
          }
          return;
        }

        WarungioAuth.api('/auth/check-auth/')
          .then(function(resp) {
            if (resp && resp.user) {
              // Update localStorage with fresh data
              localStorage.setItem('warungio_user', JSON.stringify(resp.user));
              updateNameAvatar(resp.user);
              console.debug('[nav.js] Profile refreshed from API:', resp.user.full_name);
            }
          })
          .catch(function(err) {
            console.warn('[nav.js] API refresh failed:', err);
            if (retries < maxRetries) {
              retries++;
              setTimeout(tryRefresh, 2000);
            }
          });
      }

      // Try store info too (for seller pages)
      if (typeof WarungioAPI.getMyStore === 'function') {
        WarungioAPI.getMyStore().then(function(res) {
          var store = res && res.data ? res.data : res;
          if (!store) return;
          console.debug('[nav.js] Store loaded:', store.store_name);

          var shopNameEl = document.getElementById('shopName');
          if (shopNameEl) {
            var skel = shopNameEl.querySelector('.skeleton');
            if (skel) skel.remove();
            shopNameEl.textContent = store.store_name || 'Warung';
          }

          var shopIdEl = document.getElementById('shopId');
          if (shopIdEl) {
            var sid = store.slug ? store.slug.toUpperCase() : (store.id ? 'WRG' + store.id : '---');
            var skel2 = shopIdEl.querySelector('.skeleton');
            if (skel2) skel2.remove();
            shopIdEl.textContent = 'ID Warung: ' + sid;
          }

          var headerLogo = document.getElementById('headerStoreLogo');
          if (headerLogo && store.store_logo) {
            headerLogo.src = store.store_logo;
            headerLogo.style.display = 'inline-block';
          }
        }).catch(function(err) { console.warn('[nav.js] Store load failed:', err); });
      }

      tryRefresh();
    }

    refreshFromAPI();
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
    loadProfile();
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
    loadProfile();
  });
  // Also listen for login event
  document.addEventListener('warungio:login', function () {
    loadProfile();
  });
})();
