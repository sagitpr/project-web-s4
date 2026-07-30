/**
 * Warungio Buyer — Dashboard (Consolidated)
 * Loads profile, orders, promos, wallet balance, and renders dynamic UI.
 */
(function () {
  'use strict';

  /* ── Helpers ── */
  function $(id) { return document.getElementById(id); }

  function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function showToast(msg, type) {
    if (window.WarungioToast && typeof WarungioToast.show === 'function') {
      WarungioToast.show(msg, type || 'success');
      return;
    }
    var t = document.createElement('div');
    t.className = 'toast-' + (type || 'success');
    t.textContent = msg;
    t.style.cssText = 'position:fixed;bottom:20px;right:20px;padding:12px 20px;border-radius:10px;font-size:13px;font-weight:600;z-index:9999;box-shadow:0 4px 12px rgba(0,0,0,.15);animation:fadeInUp .3s ease;';
    if (type === 'error') { t.style.background = '#fee2e2'; t.style.color = '#991b1b'; }
    else { t.style.background = '#dcfce7'; t.style.color = '#166534'; }
    document.body.appendChild(t);
    setTimeout(function () { if (t.parentNode) t.remove(); }, 3500);
  }

  function toRupiah(num) {
    return 'Rp ' + Number(num || 0).toLocaleString('id-ID');
  }

  /* ── Load Profile & Wallet ── */
  async function loadProfile() {
    if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) return;
    try {
      var u = await WarungioAPI.checkAuth();
      if (!u || !u.user) return;
      var greetEl = $('dashGreeting');
      var avatarEl = $('dashAvatar');
      var balanceEl = $('dashWalletBalance');
      var badgeEl = $('dashMemberBadge');
      var displayName = u.user.full_name || u.user.email;
      if (greetEl) greetEl.textContent = 'Halo, ' + (displayName ? displayName.split(' ')[0] : '') + '!';
      if (balanceEl) balanceEl.textContent = toRupiah(u.user.wallet_balance || 0);
      if (u.user.profile_photo && avatarEl) avatarEl.src = u.user.profile_photo;
      if (badgeEl) badgeEl.textContent = (u.user.role === 'seller') ? 'Penjual' : 'Member';
    } catch (err) { console.warn('Dashboard profile error:', err); }
  }

  /* ── Load Orders Stats & Recent Orders ── */
  async function loadOrders() {
    if (!window.WarungioAPI) return;
    try {
      var allOrders = await WarungioAPI.getOrders({ page: 1, pageSize: 100 });
      var orders = allOrders.results || [];
      var counts = { pending: 0, processed: 0, shipped: 0, completed: 0 };
      orders.forEach(function (o) {
        var s = (o.order_status || '').toLowerCase();
        if (s === 'pending') counts.pending++;
        else if (s === 'paid' || s === 'processed') counts.processed++;
        else if (s === 'shipped' || s === 'on_delivery') counts.shipped++;
        else if (s === 'completed' || s === 'delivered') counts.completed++;
      });
      var statPending = $('statPending');
      var statProcessed = $('statProcessed');
      var statShipped = $('statShipped');
      var statCompleted = $('statCompleted');
      if (statPending) statPending.textContent = counts.pending;
      if (statProcessed) statProcessed.textContent = counts.processed;
      if (statShipped) statShipped.textContent = counts.shipped;
      if (statCompleted) statCompleted.textContent = counts.completed;

      // Recent orders
      var recentGrid = $('recentOrdersGrid');
      if (recentGrid && orders.length > 0) {
        var STATUS_LABELS = {
          pending: 'Menunggu', paid: 'Dibayar', processed: 'Diproses',
          shipped: 'Dikirim', on_delivery: 'Dikirim', completed: 'Selesai',
          delivered: 'Selesai', cancelled: 'Dibatalkan', refunded: 'Dikembalikan'
        };
        recentGrid.innerHTML = '';
        orders.slice(0, 6).forEach(function (o) {
          var statusKey = (o.order_status || 'pending').toLowerCase();
          var statusLabel = STATUS_LABELS[statusKey] || statusKey;
          var badgeClass = statusKey === 'on_delivery' ? 'shipped' : statusKey;
          var itemNames = o.items ? o.items.map(function (i) { return i.product_name || 'Produk'; }).join(', ') : '-';
          if (itemNames.length > 55) itemNames = itemNames.substring(0, 52) + '...';
          var card = document.createElement('div');
          card.className = 'order-card-dash';
          card.innerHTML =
            '<div class="order-card-top">' +
              '<div>' +
                '<div class="order-card-number">' + (o.order_number || '#' + o.id) + '</div>' +
                (o.store_name ? '<div class="order-card-store">' + escapeHtml(o.store_name) + '</div>' : '') +
              '</div>' +
              '<span class="order-card-badge ' + badgeClass + '">' + statusLabel + '</span>' +
            '</div>' +
            '<div class="order-card-body">' + escapeHtml(itemNames) + '</div>' +
            '<div class="order-card-footer">' +
              '<span class="order-card-total">' + toRupiah(o.total_price || 0) + '</span>' +
              '<a href="/buyer/order-detail/?id=' + o.id + '" class="order-card-link">Lihat Detail →</a>' +
            '</div>';
          recentGrid.appendChild(card);
        });
      }
    } catch (err) { console.warn('Dashboard orders error:', err); }
  }

  /* ── Load Promos ── */
  async function loadPromos() {
    if (!window.WarungioAPI) return;
    try {
      var promoData = await WarungioAPI.getPromos();
      var promos = promoData.results || promoData || [];
      var promoGrid = $('promoDashGrid');
      var promoLoading = $('promoDashLoading');
      if (!promoGrid) return;
      if (promoLoading) promoLoading.style.display = 'none';
      if (promos.length > 0) {
        promoGrid.innerHTML = '';
        promos.slice(0, 4).forEach(function (promo) {
          var card = document.createElement('div');
          card.className = 'promo-card-dash';
          var discDesc = promo.discount_percent ? 'Diskon ' + promo.discount_percent + '%' : (promo.discount_amount ? 'Diskon Rp ' + Number(promo.discount_amount).toLocaleString('id-ID') : promo.promo_name);
          var promoIcon = promo.icon_url || '/static/images/discount.png';
          card.innerHTML = '<img src="' + promoIcon + '" alt="Promo" onerror="this.src=\'/static/images/discount.png\'" /><div><h4>' + escapeHtml(promo.promo_name || 'Promo') + '</h4><p>' + escapeHtml(discDesc) + '</p></div>';
          promoGrid.appendChild(card);
        });
      } else {
        promoGrid.innerHTML = '<div class="promo-loading-state">Belum ada promo aktif</div>';
      }
    } catch (err) {
      console.warn('Dashboard promos error:', err);
      var promoGrid = $('promoDashGrid');
      if (promoGrid) promoGrid.innerHTML = '<div class="promo-loading-state">Belum ada promo aktif</div>';
    }
  }

  /* ── Top Up Button ── */
  function initTopUp() {
    var btn = $('btnTopUpDash');
    if (btn) {
      btn.addEventListener('click', function () {
        window.location.href = '/buyer/wallet/';
      });
    }
  }

  /* ── Init ── */
  document.addEventListener('DOMContentLoaded', async function () {
    // Auth guard
    if (window.WarungioAuth && window.WarungioAuth.requireVerified && window.WarungioAuth.requireVerified()) {
      return;
    }

    // Initialize Auth UI (handles profile dropdown, logout, auth/guest toggle)
    if (window.WarungioAuthUI && typeof WarungioAuthUI.init === 'function') {
      WarungioAuthUI.init({ syncBalance: false, syncCart: false });
    }

    // Load all sections in parallel
    await Promise.all([
      loadProfile(),
      loadOrders(),
      loadPromos(),
    ]);

    initTopUp();
  });
})();
