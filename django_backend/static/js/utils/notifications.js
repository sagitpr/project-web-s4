/**
 * Warungio Notification Widget — Premium Design System
 * Live notification badge + dropdown for seller pages.
 * Integrates with WebSocket for real-time updates.
 *
 * Features:
 *  - Premium Warungio design system using tokens.css variables
 *  - Category filter tabs (Semua, Pesanan, Pembayaran, Promo, Sistem)
 *  - Unread indicator (green left dot)
 *  - Click notification → navigate to action_url + mark as read
 *  - Delete individual notification (X button, slides in on hover)
 *  - Mark all as read
 *  - Smooth dropdown open/close animations
 *  - Staggered item entrance animation
 *  - Skeleton loading state (3 shimmer rows)
 *  - Premium empty state with illustration
 *  - Pagination (Load More button)
 *  - Real-time WebSocket updates with toast for urgent
 *  - Fallback polling every 60s
 *  - Responsive layout (full-screen on mobile)
 *
 * Usage:
 *   WarungioNotifications.init('#notif-container');
 */
(function () {
  'use strict';

  var POLL_INTERVAL = 60000;
  var PAGE_SIZE = 20;

  function NotificationWidget() {
    this.container = null;
    this.badge = null;
    this.dropdown = null;
    this.trigger = null;
    this.notifList = null;
    this.markAllBtn = null;
    this.filterBar = null;
    this.loadMoreBtn = null;
    this.unreadCount = 0;
    this.notifications = [];
    this.pollTimer = null;
    this.unsubscribers = [];
    this.initialized = false;
    this.loading = false;
    this.currentFilter = 'all';
    this.page = 1;
    this.hasMore = false;
  }

  NotificationWidget.prototype.init = function (containerEl) {
    if (this.initialized) return;
    this.initialized = true;

    this.container = typeof containerEl === 'string'
      ? document.querySelector(containerEl)
      : containerEl;

    if (!this.container) return;

    this._render();
    this._bindEvents();
    this._fetchUnreadCount();
    this._connectWS();
    this.pollTimer = setInterval(this._bindFetchUnreadCount.bind(this), POLL_INTERVAL);
  };

  NotificationWidget.prototype.destroy = function () {
    if (this.pollTimer) clearInterval(this.pollTimer);
    for (var i = 0; i < this.unsubscribers.length; i++) {
      if (typeof this.unsubscribers[i] === 'function') this.unsubscribers[i]();
    }
    this.unsubscribers = [];
    this.initialized = false;
  };

  // ── Render ──

  NotificationWidget.prototype._render = function () {
    this.container.innerHTML =
      '<div class="nw-widget">' +
        // Trigger button
        '<button class="nw-trigger" aria-label="Notifikasi" title="Notifikasi">' +
          '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
            '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>' +
            '<path d="M13.73 21a2 2 0 0 1-3.46 0"/>' +
          '</svg>' +
          '<span class="nw-badge" style="display:none">0</span>' +
        '</button>' +
        // Dropdown
        '<div class="nw-dropdown">' +
          // Header
          '<div class="nw-header">' +
            '<div class="nw-header-left">' +
              '<h3>Notifikasi</h3>' +
              '<span class="nw-header-count">0 baru</span>' +
            '</div>' +
            '<button class="nw-mark-all">Baca Semua</button>' +
          '</div>' +
          // Filter tabs
          '<div class="nw-filters" id="nwFilterBar">' +
            '<button class="nw-filter active" data-filter="all">Semua</button>' +
            '<button class="nw-filter" data-filter="order">Pesanan</button>' +
            '<button class="nw-filter" data-filter="payment">Pembayaran</button>' +
            '<button class="nw-filter" data-filter="promo">Promo</button>' +
            '<button class="nw-filter" data-filter="system">Sistem</button>' +
          '</div>' +
          // Notification list
          '<div class="nw-list">' +
            '<div class="nw-skeleton">' +
              '<div class="nw-sk-row"><div class="nw-sk-shape nw-sk-icon"></div><div class="nw-sk-shape nw-sk-line1"></div><div class="nw-sk-shape nw-sk-line2"></div></div>' +
              '<div class="nw-sk-row"><div class="nw-sk-shape nw-sk-icon"></div><div class="nw-sk-shape nw-sk-line1"></div><div class="nw-sk-shape nw-sk-line2"></div></div>' +
              '<div class="nw-sk-row"><div class="nw-sk-shape nw-sk-icon"></div><div class="nw-sk-shape nw-sk-line1"></div><div class="nw-sk-shape nw-sk-line2"></div></div>' +
            '</div>' +
          '</div>' +
          // Load more
          '<div class="nw-footer">' +
            '<button class="nw-load-more" style="display:none">Muat lebih banyak</button>' +
          '</div>' +
        '</div>' +
      '</div>';

    this.badge = this.container.querySelector('.nw-badge');
    this.dropdown = this.container.querySelector('.nw-dropdown');
    this.trigger = this.container.querySelector('.nw-trigger');
    this.notifList = this.container.querySelector('.nw-list');
    this.markAllBtn = this.container.querySelector('.nw-mark-all');
    this.filterBar = this.container.querySelector('#nwFilterBar');
    this.loadMoreBtn = this.container.querySelector('.nw-load-more');
    this.headerCount = this.container.querySelector('.nw-header-count');
  };

  // ── Bind Events ──

  NotificationWidget.prototype._bindEvents = function () {
    var self = this;

    // Toggle dropdown
    this.trigger.addEventListener('click', function (e) {
      e.stopPropagation();
      self._toggleDropdown();
    });

    // Close on outside click
    document.addEventListener('click', function (e) {
      if (self.container && !self.container.contains(e.target)) {
        self._closeDropdown();
      }
    });

    // Mark all as read
    this.markAllBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      self._markAllRead();
    });

    // Filter clicks
    this.filterBar.addEventListener('click', function (e) {
      var btn = e.target.closest('.nw-filter');
      if (!btn) return;
      e.stopPropagation();
      var filter = btn.getAttribute('data-filter');
      if (filter === self.currentFilter) return;
      self.currentFilter = filter;
      self.filterBar.querySelectorAll('.nw-filter').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      self._fetchNotifications();
    });

    // Load more
    this.loadMoreBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      self._loadMore();
    });

    // Prevent dropdown close when clicking inside
    this.dropdown.addEventListener('click', function (e) {
      e.stopPropagation();
    });
  };

  NotificationWidget.prototype._toggleDropdown = function () {
    if (this.dropdown.classList.contains('nw-open')) {
      this._closeDropdown();
    } else {
      this._openDropdown();
    }
  };

  NotificationWidget.prototype._openDropdown = function () {
    this.dropdown.classList.add('nw-open');
    this.dropdown.style.display = 'block';
    // Reset filter
    this.currentFilter = 'all';
    this.page = 1;
    var activeFilter = this.filterBar.querySelector('.nw-filter.active');
    if (activeFilter && activeFilter.getAttribute('data-filter') !== 'all') {
      this.filterBar.querySelectorAll('.nw-filter').forEach(function (b) { b.classList.remove('active'); });
      var allBtn = this.filterBar.querySelector('[data-filter="all"]');
      if (allBtn) allBtn.classList.add('active');
    }
    this._fetchNotifications();
  };

  NotificationWidget.prototype._closeDropdown = function () {
    this.dropdown.classList.remove('nw-open');
    var self = this;
    setTimeout(function () {
      self.dropdown.style.display = 'none';
    }, 200);
  };

  // ── WebSocket ──

  NotificationWidget.prototype._connectWS = function () {
    var self = this;
    if (!window.WarungioWS) return;
    var ws = window.WarungioWS;

    this.unsubscribers.push(
      ws.on('unread_count', function (data) {
        self.unreadCount = data.count || 0;
        self._updateBadge();
      })
    );

    this.unsubscribers.push(
      ws.on('notification', function (data) {
        self.unreadCount++;
        self._updateBadge();
        if (self.dropdown.classList.contains('nw-open')) {
          self._prependNotification(data);
        }
        if (data.priority === 'high' || data.priority === 'urgent') {
          self._showToast(data.title, data.description);
        }
      })
    );
  };

  // ── API ──

  NotificationWidget.prototype._bindFetchUnreadCount = function () {
    this._fetchUnreadCount();
  };

  NotificationWidget.prototype._fetchUnreadCount = function () {
    var self = this;
    if (!window.WarungioAPI) return;
    WarungioAPI.getNotifications({ unread: 'true' }).then(function (data) {
      var items = data.results || data || [];
      self.unreadCount = Array.isArray(items) ? items.length : (data.total_unread || data.count || 0);
      self._updateBadge();
    }).catch(function () {});
  };

  NotificationWidget.prototype._fetchNotifications = function () {
    var self = this;
    if (!window.WarungioAPI) return;
    self.page = 1;
    self._showLoading();
    var params = { pageSize: PAGE_SIZE };
    if (self.currentFilter !== 'all') {
      params.type = self.currentFilter;
    }
    WarungioAPI.getNotifications(params).then(function (data) {
      self.notifications = data.results || data || [];
      self.hasMore = (data.results && data.results.length >= PAGE_SIZE) || false;
      self._renderNotifications();
    }).catch(function () {
      self._showError();
    });
  };

  NotificationWidget.prototype._loadMore = function () {
    var self = this;
    if (!window.WarungioAPI || this.loading) return;
    self.loading = true;
    self.loadMoreBtn.textContent = 'Memuat...';
    self.loadMoreBtn.disabled = true;
    self.page++;
    var params = { pageSize: PAGE_SIZE, page: self.page };
    if (self.currentFilter !== 'all') {
      params.type = self.currentFilter;
    }
    WarungioAPI.getNotifications(params).then(function (data) {
      var newItems = data.results || data || [];
      self.notifications = self.notifications.concat(newItems);
      self.hasMore = (data.results && data.results.length >= PAGE_SIZE) || false;
      self._appendNotifications(newItems);
      self.loading = false;
      self.loadMoreBtn.textContent = 'Muat lebih banyak';
      self.loadMoreBtn.disabled = false;
      if (!self.hasMore) {
        self.loadMoreBtn.style.display = 'none';
      }
    }).catch(function () {
      self.loading = false;
      self.loadMoreBtn.textContent = 'Muat lebih banyak';
      self.loadMoreBtn.disabled = false;
    });
  };

  NotificationWidget.prototype._showLoading = function () {
    this.notifList.innerHTML =
      '<div class="nw-skeleton">' +
        '<div class="nw-sk-row"><div class="nw-sk-shape nw-sk-icon"></div><div class="nw-sk-shape nw-sk-line1"></div><div class="nw-sk-shape nw-sk-line2"></div></div>' +
        '<div class="nw-sk-row"><div class="nw-sk-shape nw-sk-icon"></div><div class="nw-sk-shape nw-sk-line1"></div><div class="nw-sk-shape nw-sk-line2"></div></div>' +
        '<div class="nw-sk-row"><div class="nw-sk-shape nw-sk-icon"></div><div class="nw-sk-shape nw-sk-line1"></div><div class="nw-sk-shape nw-sk-line2"></div></div>' +
      '</div>';
    this.loadMoreBtn.style.display = 'none';
  };

  NotificationWidget.prototype._showError = function () {
    this.notifList.innerHTML = '<div class="nw-empty"><div class="nw-empty-icon"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div><h3>Gagal Memuat</h3><p>Terjadi kesalahan. Silakan coba lagi.</p></div>';
    this.loadMoreBtn.style.display = 'none';
  };

  NotificationWidget.prototype._markAllRead = function () {
    var self = this;
    if (!window.WarungioAPI || this.unreadCount === 0) return;
    WarungioAPI.markAllNotificationsRead().then(function () {
      self.unreadCount = 0;
      self._updateBadge();
      var unreadEls = self.notifList.querySelectorAll('.nw-item.unread');
      for (var i = 0; i < unreadEls.length; i++) {
        unreadEls[i].classList.remove('unread');
      }
      if (self.headerCount) self.headerCount.textContent = '0 baru';
    }).catch(function () {});
  };

  NotificationWidget.prototype._markRead = function (id) {
    var self = this;
    if (!window.WarungioAPI) return;
    WarungioAPI.markNotificationRead(id).then(function () {
      for (var i = 0; i < self.notifications.length; i++) {
        if (self.notifications[i].id === id) {
          self.notifications[i].is_read = true;
          break;
        }
      }
      self.unreadCount = Math.max(0, self.unreadCount - 1);
      self._updateBadge();
    }).catch(function () {});
  };

  NotificationWidget.prototype._deleteNotification = function (id) {
    var self = this;
    if (!window.WarungioAPI) return;
    WarungioAPI.deleteNotification(id).then(function () {
      var item = self.notifList.querySelector('[data-nid="' + id + '"]');
      if (item) {
        item.style.transform = 'translateX(40px)';
        item.style.opacity = '0';
        setTimeout(function () {
          if (item.parentNode) item.remove();
          self._checkEmpty();
        }, 200);
      }
      for (var i = 0; i < self.notifications.length; i++) {
        if (self.notifications[i].id === id) {
          if (!self.notifications[i].is_read) {
            self.unreadCount = Math.max(0, self.unreadCount - 1);
          }
          self.notifications.splice(i, 1);
          break;
        }
      }
      self._updateBadge();
    }).catch(function () {});
  };

  NotificationWidget.prototype._checkEmpty = function () {
    if (this.notifList.querySelectorAll('.nw-item').length === 0) {
      this.notifList.innerHTML = '<div class="nw-empty"><div class="nw-empty-icon"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg></div><h3>Belum Ada Notifikasi</h3><p>Tidak ada notifikasi untuk ditampilkan saat ini.</p></div>';
      this.loadMoreBtn.style.display = 'none';
    }
  };

  // ── Click handler: navigate + mark as read ──

  NotificationWidget.prototype._handleItemClick = function (notifId, actionUrl, isRead) {
    if (!isRead) {
      this._markRead(notifId);
    }
    if (actionUrl) {
      window.location.href = actionUrl;
    }
  };

  // ── UI Updates ──

  NotificationWidget.prototype._updateBadge = function () {
    if (!this.badge) return;
    if (this.unreadCount > 0) {
      this.badge.textContent = this.unreadCount > 99 ? '99+' : this.unreadCount;
      this.badge.style.display = 'flex';
      this.badge.classList.add('nw-badge-pulse');
    } else {
      this.badge.style.display = 'none';
      this.badge.classList.remove('nw-badge-pulse');
    }
    if (this.headerCount) {
      this.headerCount.textContent = this.unreadCount > 0 ? this.unreadCount + ' baru' : '0 baru';
    }
  };

  NotificationWidget.prototype._renderNotifications = function () {
    var self = this;
    if (!this.notifList) return;

    if (this.notifications.length === 0) {
      this.notifList.innerHTML = '<div class="nw-empty"><div class="nw-empty-icon"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg></div><h3>Belum Ada Notifikasi</h3><p>Tidak ada notifikasi untuk ditampilkan saat ini. Notifikasi baru akan muncul di sini.</p></div>';
      this.loadMoreBtn.style.display = 'none';
      return;
    }

    this.notifList.innerHTML = '';
    var count = Math.min(this.notifications.length, PAGE_SIZE);
    for (var i = 0; i < count; i++) {
      var n = this.notifications[i];
      var el = self._createItem(n, i);
      this.notifList.appendChild(el);
      // Stagger animation
      (function (el, i) {
        setTimeout(function () {
          el.style.opacity = '1';
          el.style.transform = 'translateX(0)';
        }, 30 * Math.min(i, 10));
      })(el, i);
    }

    // Load more visibility
    if (this.hasMore && this.notifications.length >= PAGE_SIZE) {
      this.loadMoreBtn.style.display = 'flex';
    } else {
      this.loadMoreBtn.style.display = 'none';
    }
  };

  NotificationWidget.prototype._appendNotifications = function (newItems) {
    var self = this;
    var startIdx = this.notifications.length - newItems.length;
    for (var i = 0; i < newItems.length; i++) {
      var n = newItems[i];
      var el = self._createItem(n, startIdx + i);
      self.notifList.appendChild(el);
    }
  };

  NotificationWidget.prototype._createItem = function (n, idx) {
    var self = this;
    var el = document.createElement('div');
    el.className = 'nw-item' + (n.is_read ? '' : ' unread');
    el.setAttribute('data-nid', n.id);
    el.style.opacity = '0';
    el.style.transform = 'translateX(20px)';

    var type = n.notification_type || 'system';
    el.innerHTML =
      '<div class="nw-item-left">' +
        '<div class="nw-icon ' + type + '" data-type="' + type + '">' +
          self._getIcon(type) +
        '</div>' +
      '</div>' +
      '<div class="nw-item-body">' +
        '<div class="nw-item-title">' + self._escape(n.title) + '</div>' +
        (n.description ? '<div class="nw-item-desc">' + self._escape(n.description) + '</div>' : '') +
        '<div class="nw-item-time">' +
          '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>' +
          (n.time_ago || '') +
        '</div>' +
      '</div>' +
      '<div class="nw-item-actions">' +
        '<button class="nw-del-btn" title="Hapus" data-del-id="' + n.id + '">' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>' +
        '</button>' +
      '</div>';

    // Click to navigate + mark as read
    el.addEventListener('click', function (e) {
      var del = e.target.closest('.nw-del-btn');
      if (del) return;
      self._handleItemClick(n.id, n.action_url, n.is_read);
    });

    // Delete button
    var delBtn = el.querySelector('.nw-del-btn');
    if (delBtn) {
      delBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        self._deleteNotification(n.id);
      });
    }

    return el;
  };

  NotificationWidget.prototype._prependNotification = function (data) {
    var self = this;
    if (!this.notifList) return;

    var empty = this.notifList.querySelector('.nw-empty, .nw-skeleton');
    if (empty) empty.remove();
    this.loadMoreBtn.style.display = 'none';

    var el = document.createElement('div');
    el.className = 'nw-item unread';
    el.setAttribute('data-nid', data.id || Date.now());
    el.style.opacity = '0';
    el.style.transform = 'translateX(-20px)';

    var type = data.notification_type || 'system';
    el.innerHTML =
      '<div class="nw-item-left">' +
        '<div class="nw-icon ' + type + '">' +
          self._getIcon(type) +
        '</div>' +
      '</div>' +
      '<div class="nw-item-body">' +
        '<div class="nw-item-title">' + self._escape(data.title || '') + '</div>' +
        (data.description ? '<div class="nw-item-desc">' + self._escape(data.description) + '</div>' : '') +
        '<div class="nw-item-time">' +
          '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>' +
          'Baru saja' +
        '</div>' +
      '</div>' +
      '<div class="nw-item-actions">' +
        '<button class="nw-del-btn" title="Hapus" data-del-id="' + (data.id || '') + '">' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>' +
        '</button>' +
      '</div>';

    el.addEventListener('click', function (e) {
      var del = e.target.closest('.nw-del-btn');
      if (del) return;
      self._handleItemClick(data.id, data.action_url, false);
    });

    var delBtn = el.querySelector('.nw-del-btn');
    if (delBtn) {
      delBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        self._deleteNotification(data.id);
      });
    }

    this.notifList.insertBefore(el, this.notifList.firstChild);
    // Animate in
    requestAnimationFrame(function () {
      el.style.opacity = '1';
      el.style.transform = 'translateX(0)';
    });
  };

  NotificationWidget.prototype._showToast = function (title, message) {
    var toast = document.createElement('div');
    toast.className = 'nw-toast';
    toast.innerHTML =
      '<div class="nw-toast-inner">' +
        '<strong>' + this._escape(title) + '</strong>' +
        (message ? '<p>' + this._escape(message) + '</p>' : '') +
      '</div>' +
      '<button class="nw-toast-close">&times;</button>';
    document.body.appendChild(toast);

    requestAnimationFrame(function () { toast.classList.add('show'); });

    var timer = setTimeout(function () {
      toast.classList.remove('show');
      setTimeout(function () { toast.remove(); }, 300);
    }, 5000);

    toast.querySelector('.nw-toast-close').addEventListener('click', function () {
      clearTimeout(timer);
      toast.classList.remove('show');
      setTimeout(function () { toast.remove(); }, 300);
    });
  };

  NotificationWidget.prototype._getIcon = function (type) {
    var icons = {
      order: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>',
      payment: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>',
      chat: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
      promo: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 12V8H6a2 2 0 0 1-2-2c0-1.1.9-2 2-2h12v4"/><path d="M4 6v12c0 1.1.9 2 2 2h14v-4"/><path d="M18 12a2 2 0 0 0-2 2c0 1.1.9 2 2 2h4v-4h-4z"/></svg>',
      system: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
      review: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
      product: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>',
    };
    return icons[type] || icons.system;
  };

  NotificationWidget.prototype._escape = function (str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  };

  // ── Singleton ──

  var instance = new NotificationWidget();
  window.WarungioNotifications = instance;

  // ── Auto-inject premium styles (uses tokens.css variables with fallbacks) ──

  if (!document.getElementById('warungio-notif-styles')) {
    var style = document.createElement('style');
    style.id = 'warungio-notif-styles';
    style.textContent = [
      '/* Warungio Notification Widget — Premium Design */',

      '/* ── Widget Container ── */',
      '.nw-widget { position: relative; display: inline-flex; }',

      '/* ── Trigger Button ── */',
      '.nw-trigger {',
      '  position: relative; width: 42px; height: 42px;',
      '  border: 1px solid var(--color-border, #e2e8f0); background: var(--color-surface, #fff);',
      '  border-radius: var(--radius-lg, 12px); cursor: pointer;',
      '  display: flex; align-items: center; justify-content: center;',
      '  color: var(--color-text-secondary, #64748b);',
      '  transition: all 0.2s var(--ease-out, cubic-bezier(0.16,1,0.3,1));',
      '}',
      '.nw-trigger:hover {',
      '  background: var(--color-brand-soft, #f0fdf4);',
      '  border-color: var(--color-brand, #16a34a);',
      '  color: var(--color-brand, #16a34a);',
      '}',

      '/* ── Badge ── */',
      '.nw-badge {',
      '  position: absolute; top: -5px; right: -5px;',
      '  min-width: 20px; height: 20px; padding: 0 5px;',
      '  background: var(--color-danger, #ef4444); color: white;',
      '  font-size: 10px; font-weight: 800; line-height: 1;',
      '  border-radius: var(--radius-full, 9999px);',
      '  align-items: center; justify-content: center;',
      '  border: 2px solid var(--color-surface, #fff);',
      '  box-shadow: 0 2px 6px rgba(239,68,68,0.3);',
      '  transition: transform 0.2s var(--ease-spring, cubic-bezier(0.34,1.56,0.64,1));',
      '}',
      '.nw-badge-pulse { animation: nwBadgePop 0.3s var(--ease-spring, cubic-bezier(0.34,1.56,0.64,1)); }',
      '@keyframes nwBadgePop {',
      '  0% { transform: scale(0.5); }',
      '  50% { transform: scale(1.2); }',
      '  100% { transform: scale(1); }',
      '}',

      '/* ── Dropdown ── */',
      '.nw-dropdown {',
      '  position: absolute; top: calc(100% + 10px); right: 0;',
      '  width: 400px; max-height: 560px;',
      '  background: var(--color-surface, #fff);',
      '  border-radius: var(--radius-squircle-lg, 20px);',
      '  border: 1px solid var(--color-border, #e2e8f0);',
      '  box-shadow: var(--shadow-bezel-xl, 0 8px 32px rgba(0,0,0,0.06), 0 2px 8px rgba(0,0,0,0.04), inset 0 1.5px 0 rgba(255,255,255,1));',
      '  z-index: 1000; display: none; overflow: hidden;',
      '  opacity: 0; transform: translateY(-8px) scale(0.97);',
      '  transform-origin: top right;',
      '  transition: opacity 0.2s var(--ease-out, cubic-bezier(0.16,1,0.3,1)),',
      '              transform 0.25s var(--ease-out, cubic-bezier(0.16,1,0.3,1));',
      '}',
      '.nw-dropdown.nw-open {',
      '  opacity: 1; transform: translateY(0) scale(1);',
      '}',

      '/* ── Header ── */',
      '.nw-header {',
      '  display: flex; justify-content: space-between; align-items: center;',
      '  padding: var(--space-5, 20px) var(--space-5, 20px) var(--space-3, 12px);',
      '}',
      '.nw-header-left { display: flex; align-items: baseline; gap: 10px; }',
      '.nw-header-left h3 {',
      '  margin: 0; font-size: 1rem; font-weight: 800;',
      '  color: var(--color-text-primary, #0f172a);',
      '}',
      '.nw-header-count {',
      '  font-size: 0.7rem; font-weight: 600;',
      '  color: var(--color-text-tertiary, #94a3b8);',
      '  background: var(--color-gray-100, #f1f5f9);',
      '  padding: 2px 10px; border-radius: var(--radius-full, 9999px);',
      '}',
      '.nw-mark-all {',
      '  border: none; background: transparent;',
      '  color: var(--color-brand, #16a34a); font-size: 0.75rem; font-weight: 700;',
      '  cursor: pointer; padding: 6px 12px; border-radius: var(--radius-md, 8px);',
      '  transition: all 0.15s; line-height: 1;',
      '  font-family: var(--font-sans, "Plus Jakarta Sans"), sans-serif;',
      '}',
      '.nw-mark-all:hover { background: var(--color-brand-soft, #f0fdf4); }',

      '/* ── Filter Tabs ── */',
      '.nw-filters {',
      '  display: flex; gap: 4px; padding: 0 var(--space-5, 20px) var(--space-3, 12px);',
      '  border-bottom: 1px solid var(--color-border-light, #f1f5f9);',
      '  overflow-x: auto; -webkit-overflow-scrolling: touch;',
      '  scrollbar-width: none;',
      '}',
      '.nw-filters::-webkit-scrollbar { display: none; }',
      '.nw-filter {',
      '  padding: 6px 14px; border: none; background: transparent;',
      '  font-size: 0.75rem; font-weight: 600; color: var(--color-text-tertiary, #94a3b8);',
      '  cursor: pointer; border-radius: var(--radius-md, 8px);',
      '  transition: all 0.15s; white-space: nowrap;',
      '  font-family: var(--font-sans, "Plus Jakarta Sans"), sans-serif;',
      '  position: relative;',
      '}',
      '.nw-filter:hover { color: var(--color-text-primary, #0f172a); }',
      '.nw-filter.active {',
      '  background: var(--color-brand, #16a34a); color: white;',
      '  box-shadow: 0 2px 8px rgba(22,163,74,0.2);',
      '}',

      '/* ── List ── */',
      '.nw-list { max-height: 380px; overflow-y: auto; }',
      '.nw-list::-webkit-scrollbar { width: 4px; }',
      '.nw-list::-webkit-scrollbar-track { background: transparent; }',
      '.nw-list::-webkit-scrollbar-thumb { background: var(--color-gray-200, #e2e8f0); border-radius: 99px; }',

      '/* ── Notification Item ── */',
      '.nw-item {',
      '  display: flex; gap: 12px; padding: 14px 20px;',
      '  border-bottom: 1px solid var(--hairline-light, rgba(0,0,0,0.04));',
      '  transition: background 0.15s, opacity 0.2s, transform 0.2s;',
      '  align-items: flex-start; cursor: pointer; position: relative;',
      '}',
      '.nw-item:hover {',
      '  background: var(--color-surface-secondary, #f8fafc);',
      '}',
      '.nw-item.unread {',
      '  background: var(--color-brand-soft, #f0fdf4);',
      '  border-left: 3px solid var(--color-brand, #16a34a);',
      '  padding-left: 17px;',
      '}',
      '.nw-item:last-child { border-bottom: none; }',

      '/* ── Icon ── */',
      '.nw-item-left { flex-shrink: 0; }',
      '.nw-icon {',
      '  width: 38px; height: 38px; border-radius: var(--radius-squircle-sm, 10px);',
      '  display: flex; align-items: center; justify-content: center;',
      '  flex-shrink: 0; background: var(--color-surface-tertiary, #f1f5f9);',
      '  color: var(--color-text-secondary, #64748b);',
      '}',
      '.nw-icon.order { background: var(--color-success-soft, #dcfce7); color: var(--color-brand, #16a34a); }',
      '.nw-icon.payment { background: var(--color-info-soft, #dbeafe); color: var(--color-info, #3b82f6); }',
      '.nw-icon.chat { background: #fce7f3; color: #db2777; }',
      '.nw-icon.promo { background: var(--color-warning-soft, #fef3c7); color: #d97706; }',
      '.nw-icon.system { background: #e0e7ff; color: #4f46e5; }',
      '.nw-icon.review { background: #fef9c3; color: #ca8a04; }',
      '.nw-icon.product { background: var(--color-success-soft, #dcfce7); color: var(--color-brand, #16a34a); }',

      '/* ── Item Body ── */',
      '.nw-item-body { flex: 1; min-width: 0; }',
      '.nw-item-title {',
      '  font-size: 0.8125rem; font-weight: 600;',
      '  color: var(--color-text-primary, #0f172a);',
      '  line-height: 1.35; margin-bottom: 2px;',
      '  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;',
      '  overflow: hidden;',
      '}',
      '.nw-item-desc {',
      '  font-size: 0.75rem; color: var(--color-text-secondary, #475569);',
      '  line-height: 1.45; margin-top: 1px;',
      '  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;',
      '  overflow: hidden;',
      '}',
      '.nw-item-time {',
      '  font-size: 0.6875rem; color: var(--color-text-tertiary, #94a3b8);',
      '  margin-top: 5px; display: flex; align-items: center; gap: 4px;',
      '}',
      '.nw-item-time svg { flex-shrink: 0; opacity: 0.6; }',

      '/* ── Delete Button ── */',
      '.nw-item-actions {',
      '  flex-shrink: 0; display: flex; align-items: center;',
      '  opacity: 0; transition: opacity 0.15s;',
      '}',
      '.nw-item:hover .nw-item-actions { opacity: 1; }',
      '.nw-del-btn {',
      '  border: none; background: transparent;',
      '  color: var(--color-text-tertiary, #94a3b8);',
      '  width: 28px; height: 28px; border-radius: var(--radius-md, 8px);',
      '  cursor: pointer; display: flex; align-items: center;',
      '  justify-content: center; transition: all 0.15s;',
      '}',
      '.nw-del-btn:hover { color: var(--color-danger, #ef4444); background: var(--color-danger-soft, #fef2f2); }',

      '/* ── Loading Skeleton ── */',
      '.nw-skeleton { padding: 12px 20px; }',
      '.nw-sk-row {',
      '  display: flex; gap: 12px; align-items: center;',
      '  padding: 10px 0;',
      '}',
      '.nw-sk-shape {',
      '  background: linear-gradient(90deg, var(--color-gray-100, #f1f5f9) 25%, var(--color-gray-50, #f8fafc) 50%, var(--color-gray-100, #f1f5f9) 75%);',
      '  background-size: 200% 100%;',
      '  border-radius: var(--radius-md, 8px);',
      '  animation: nwShimmer 1.5s infinite;',
      '}',
      '.nw-sk-icon { width: 38px; height: 38px; flex-shrink: 0; }',
      '.nw-sk-line1 { height: 14px; flex: 1; }',
      '.nw-sk-line2 { height: 10px; width: 60%; }',
      '@keyframes nwShimmer {',
      '  0% { background-position: -200% 0; }',
      '  100% { background-position: 200% 0; }',
      '}',

      '/* ── Empty State ── */',
      '.nw-empty {',
      '  display: flex; flex-direction: column; align-items: center;',
      '  justify-content: center; padding: 48px 32px; text-align: center;',
      '}',
      '.nw-empty-icon {',
      '  width: 64px; height: 64px; border-radius: var(--radius-xl, 16px);',
      '  background: var(--color-gray-100, #f1f5f9);',
      '  display: flex; align-items: center; justify-content: center;',
      '  color: var(--color-text-tertiary, #94a3b8);',
      '  margin-bottom: 16px;',
      '}',
      '.nw-empty h3 {',
      '  font-size: 0.95rem; font-weight: 700;',
      '  color: var(--color-text-primary, #0f172a);',
      '  margin: 0 0 6px;',
      '}',
      '.nw-empty p {',
      '  font-size: 0.8rem; color: var(--color-text-tertiary, #94a3b8);',
      '  margin: 0; line-height: 1.5; max-width: 260px;',
      '}',

      '/* ── Footer / Load More ── */',
      '.nw-footer {',
      '  padding: var(--space-3, 12px);',
      '  border-top: 1px solid var(--color-border-light, #f1f5f9);',
      '  display: flex; justify-content: center;',
      '}',
      '.nw-load-more {',
      '  border: none; background: var(--color-gray-100, #f1f5f9);',
      '  color: var(--color-text-secondary, #64748b);',
      '  padding: 8px 20px; border-radius: var(--radius-md, 8px);',
      '  font-size: 0.75rem; font-weight: 600; cursor: pointer;',
      '  transition: all 0.15s; display: none; align-items: center; gap: 6px;',
      '  font-family: var(--font-sans, "Plus Jakarta Sans"), sans-serif;',
      '}',
      '.nw-load-more:hover { background: var(--color-brand-soft, #f0fdf4); color: var(--color-brand, #16a34a); }',
      '.nw-load-more:disabled { opacity: 0.5; cursor: not-allowed; }',

      '/* ── Toast ── */',
      '.nw-toast {',
      '  position: fixed; bottom: 24px; right: 24px;',
      '  max-width: 380px;',
      '  background: var(--color-gray-900, #1e293b); color: white;',
      '  border-radius: var(--radius-squircle-md, 14px); padding: 16px 20px;',
      '  box-shadow: 0 16px 40px rgba(0,0,0,0.2);',
      '  z-index: 9999; display: flex; gap: 12px;',
      '  align-items: flex-start;',
      '  opacity: 0; transform: translateY(16px);',
      '  transition: all 0.3s var(--ease-out, cubic-bezier(0.16,1,0.3,1));',
      '  pointer-events: none;',
      '}',
      '.nw-toast.show { opacity: 1; transform: translateY(0); pointer-events: auto; }',
      '.nw-toast-inner { flex: 1; }',
      '.nw-toast strong { display: block; font-size: 0.875rem; margin-bottom: 4px; }',
      '.nw-toast p { margin: 0; font-size: 0.75rem; opacity: 0.85; line-height: 1.4; }',
      '.nw-toast-close {',
      '  border: none; background: rgba(255,255,255,0.12);',
      '  color: white; width: 24px; height: 24px;',
      '  border-radius: 50%; cursor: pointer;',
      '  display: flex; align-items: center; justify-content: center;',
      '  flex-shrink: 0; font-size: 14px;',
      '  transition: background 0.15s;',
      '}',
      '.nw-toast-close:hover { background: rgba(255,255,255,0.25); }',

      '/* ── Responsive (mobile full-screen) ── */',
      '@media (max-width: 480px) {',
      '  .nw-dropdown {',
      '    position: fixed; top: 0; left: 0; right: 0; bottom: 0;',
      '    width: 100%; max-height: 100%;',
      '    border-radius: 0; border: none;',
      '    box-shadow: none;',
      '    transform: translateY(20px);',
      '    z-index: 2000;',
      '  }',
      '  .nw-dropdown.nw-open { transform: translateY(0); }',
      '  .nw-list { max-height: calc(100vh - 200px); }',
      '  .nw-header { padding: var(--space-6, 24px) var(--space-5, 20px) var(--space-3, 12px); padding-top: max(var(--space-6, 24px), env(safe-area-inset-top, 24px)); }',
      '}',
    ].join('\n');
    document.head.appendChild(style);
  }
})();
