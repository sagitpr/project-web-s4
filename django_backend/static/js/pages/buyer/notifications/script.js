/**
 * Halaman Notifikasi - JavaScript Controller
 * Terintegrasi dengan API notifikasi Warungio backend.
 */
(function () {
  'use strict';

  if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
    window.location.href = '/auth/login/?next=' + encodeURIComponent(window.location.pathname);
    return;
  }

  // ── DOM Elements ──
  var notifList = document.getElementById('notificationList');
  var loadingState = document.getElementById('loadingState');
  var unreadBadge = document.getElementById('unreadCountBadge');
  var btnMarkAll = document.getElementById('btnMarkAllRead');
  var tabBtns = document.querySelectorAll('.notif-tab');

  var currentType = 'all';
  var allNotifications = [];

  // ── Helper: format IDR ──
  function formatIDR(amount) {
    if (amount === undefined || amount === null) return '';
    return 'Rp ' + Number(amount).toLocaleString('id-ID');
  }

  // ── Helper: time ago ──
  function timeAgo(dateStr) {
    if (!dateStr) return '';
    var diff = Date.now() - new Date(dateStr).getTime();
    var mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Baru saja';
    if (mins < 60) return mins + ' menit lalu';
    var hours = Math.floor(mins / 60);
    if (hours < 24) return hours + ' jam lalu';
    var days = Math.floor(hours / 24);
    if (days < 7) return days + ' hari lalu';
    return new Date(dateStr).toLocaleDateString('id-ID', { day: 'numeric', month: 'short' });
  }

  // ── Helper: type icon ──
  function getIcon(type) {
    var map = {
      order: '<i class="fa-solid fa-box"></i>',
      payment: '<i class="fa-solid fa-credit-card"></i>',
      chat: '<i class="fa-solid fa-comment-dots"></i>',
      promo: '<i class="fa-solid fa-tag"></i>',
      system: '<i class="fa-solid fa-bell"></i>',
    };
    return map[type] || map.system;
  }

  // ── Load notifications ──
  async function loadNotifications(type) {
    if (!notifList) return;

    if (loadingState) loadingState.style.display = 'block';

    try {
      var params = {};
      if (type && type !== 'all') params.type = type;

      var data = await WarungioAuth.api('/api/notifications/', { params: params });
      allNotifications = data.results || data || [];
      renderNotifications();

      // Refresh unread count
      loadUnreadCount();
    } catch (err) {
      console.warn('Failed to load notifications:', err);
      if (loadingState) loadingState.style.display = 'none';
      if (notifList) {
        notifList.innerHTML = '<div class="notif-empty-state"><i class="fa-solid fa-exclamation-triangle"></i><h3>Gagal Memuat</h3><p>Terjadi kesalahan saat memuat notifikasi. Silakan coba lagi.</p></div>';
      }
    }
  }

  // ── Render notifications ──
  function renderNotifications() {
    if (loadingState) loadingState.style.display = 'none';
    if (!notifList) return;

    if (!allNotifications.length) {
      notifList.innerHTML = '<div class="notif-empty-state"><i class="fa-regular fa-bell-slash"></i><h3>Tidak Ada Notifikasi</h3><p>' + (currentType === 'all' ? 'Belum ada notifikasi untuk kamu.' : 'Tidak ada notifikasi ' + currentType + '.') + '</p></div>';
      return;
    }

    notifList.innerHTML = allNotifications.map(function (n) {
      var isUnread = !n.is_read;
      var iconType = n.notification_type || 'system';
      var actionUrl = n.action_url || null;

      return '<div class="notif-card ' + (isUnread ? 'unread' : '') + '" data-id="' + n.id + '"' + (actionUrl ? ' data-url="' + actionUrl + '"' : '') + '>' +
        '<div class="notif-icon ' + iconType + '">' + getIcon(iconType) + '</div>' +
        '<div class="notif-body">' +
          '<p class="notif-title">' + (n.title || 'Notifikasi') + '</p>' +
          (n.description ? '<p class="notif-desc">' + n.description + '</p>' : '') +
          '<div class="notif-meta">' +
            '<span>' + timeAgo(n.created_at) + '</span>' +
            (n.action_text ? '<span class="notif-action-link">' + n.action_text + '</span>' : '') +
          '</div>' +
        '</div>' +
        '<div class="notif-read-dot"></div>' +
      '</div>';
    }).join('');

    // Bind click events
    document.querySelectorAll('.notif-card').forEach(function (card) {
      card.addEventListener('click', function () {
        var id = parseInt(this.dataset.id);
        var url = this.dataset.url;
        if (id) markAsRead(id);
        if (url) window.location.href = url;
      });
    });
  }

  // ── Mark as read ──
  async function markAsRead(id) {
    try {
      await WarungioAuth.api('/api/notifications/mark-read/', {
        method: 'POST',
        body: JSON.stringify({ notification_ids: [id] }),
        headers: { 'Content-Type': 'application/json' }
      });
      loadUnreadCount();
    } catch (err) {
      console.warn('Failed to mark as read:', err);
    }
  }

  // ── Mark all as read ──
  async function markAllAsRead() {
    if (btnMarkAll) btnMarkAll.disabled = true;
    try {
      await WarungioAuth.api('/api/notifications/mark-read/', {
        method: 'POST',
        body: JSON.stringify({ mark_all: true }),
        headers: { 'Content-Type': 'application/json' }
      });
      if (typeof window.showToast === 'function') {
        window.showToast('Semua notifikasi ditandai sudah dibaca.', 'success');
      }
      loadNotifications(currentType);
    } catch (err) {
      console.warn('Failed to mark all as read:', err);
      if (typeof window.showToast === 'function') {
        window.showToast('Gagal menandai notifikasi.', 'error');
      }
    } finally {
      if (btnMarkAll) btnMarkAll.disabled = false;
    }
  }

  // ── Load unread count ──
  async function loadUnreadCount() {
    try {
      var data = await WarungioAuth.api('/api/notifications/unread-count/');
      if (data && data.total_unread !== undefined) {
        if (unreadBadge) {
          unreadBadge.textContent = data.total_unread;
          unreadBadge.style.display = data.total_unread > 0 ? 'inline-flex' : 'none';
        }
      }
    } catch (err) {
      console.warn('Failed to load unread count:', err);
    }
  }

  // ── Init ──
  document.addEventListener('DOMContentLoaded', function () {
    // Bind filter tabs
    tabBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        tabBtns.forEach(function (b) { b.classList.remove('active'); });
        this.classList.add('active');
        currentType = this.dataset.type || 'all';
        loadNotifications(currentType);
      });
    });

    // Bind mark all as read
    if (btnMarkAll) {
      btnMarkAll.addEventListener('click', markAllAsRead);
    }

    // Initial load
    loadNotifications('all');
  });
})();
