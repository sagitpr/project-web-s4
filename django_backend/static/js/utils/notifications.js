/**
 * Warungio Notification Widget
 * Reusable notification badge + dropdown for buyer/seller pages.
 * Integrates with WarungioWS WebSocket for real-time updates.
 *
 * Usage:
 *   WarungioNotifications.init('#notif-container');
 *
 * Dependencies:
 *   - WarungioAPI (for REST API calls)
 *   - WarungioWS (for real-time notifications)
 */
(function () {
  'use strict';

  const NOTIF_POLL_INTERVAL = 60000; // Fallback polling every 60s

  class NotificationWidget {
    constructor() {
      this.container = null;
      this.badge = null;
      this.dropdown = null;
      this.unreadCount = 0;
      this.notifications = [];
      this.pollTimer = null;
      this.unsubscribers = [];
      this.initialized = false;
    }

    /**
     * Initialize the notification widget in a container element.
     * @param {string|Element} containerEl - CSS selector or DOM element
     */
    init(containerEl) {
      if (this.initialized) return;
      this.initialized = true;

      this.container = typeof containerEl === 'string'
        ? document.querySelector(containerEl)
        : containerEl;

      if (!this.container) {
        console.warn('WarungioNotifications: Container not found:', containerEl);
        return;
      }

      this._render();
      this._bindEvents();

      // Load initial unread count
      this._fetchUnreadCount();

      // Connect WebSocket listeners
      this._connectWS();

      // Fallback polling
      this.pollTimer = setInterval(() => this._fetchUnreadCount(), NOTIF_POLL_INTERVAL);
    }

    /**
     * Clean up the widget.
     */
    destroy() {
      if (this.pollTimer) clearInterval(this.pollTimer);
      this.unsubscribers.forEach(function (fn) { fn(); });
      this.unsubscribers = [];
      this.initialized = false;
    }

    // ── Render ──

    _render() {
      this.container.innerHTML =
        '<div class="notif-widget">' +
          '<button class="notif-trigger" aria-label="Notifikasi" title="Notifikasi">' +
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
              '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>' +
              '<path d="M13.73 21a2 2 0 0 1-3.46 0"/>' +
            '</svg>' +
            '<span class="notif-badge" style="display:none">0</span>' +
          '</button>' +
          '<div class="notif-dropdown" style="display:none">' +
            '<div class="notif-dropdown-header">' +
              '<h4>Notifikasi</h4>' +
              '<button class="notif-mark-all" title="Tandai semua sudah dibaca">Baca Semua</button>' +
            '</div>' +
            '<div class="notif-list">' +
              '<div class="notif-loading">Memuat...</div>' +
            '</div>' +
          '</div>' +
        '</div>';

      this.badge = this.container.querySelector('.notif-badge');
      this.dropdown = this.container.querySelector('.notif-dropdown');
      this.trigger = this.container.querySelector('.notif-trigger');
      this.notifList = this.container.querySelector('.notif-list');
      this.markAllBtn = this.container.querySelector('.notif-mark-all');
    }

    _bindEvents() {
      var self = this;

      // Toggle dropdown
      this.trigger.addEventListener('click', function (e) {
        e.stopPropagation();
        var isOpen = self.dropdown.style.display === 'block';
        self.dropdown.style.display = isOpen ? 'none' : 'block';
        if (!isOpen) {
          self._fetchNotifications();
          // NOTE: do NOT call _markAllRead here — that's only for the button click.
          // Marking all as read on open is aggressive UX.
        }
      });

      // Close dropdown on outside click
      document.addEventListener('click', function (e) {
        if (self.container && !self.container.contains(e.target)) {
          self.dropdown.style.display = 'none';
        }
      });

      // Mark all as read
      this.markAllBtn.addEventListener('click', async function () {
        try {
          await WarungioAPI.markAllNotificationsRead();
          self.unreadCount = 0;
          self._updateBadge();
          var unreadItems = self.notifList.querySelectorAll('.notif-item.unread');
          unreadItems.forEach(function (el) { el.classList.remove('unread'); });
        } catch (e) {
          console.warn('WarungioNotifications: Mark all read failed:', e);
        }
      });
    }

    // ── WebSocket ──

    _connectWS() {
      if (!window.WarungioWS) return;

      var self = this;
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
          self._prependNotification(data);

          // Show toast for important notifications
          if (data.priority === 'high' || data.priority === 'urgent') {
            self._showToast(data.title, data.description);
          }
        })
      );

      this.unsubscribers.push(
        ws.on('order_update', function (data) {
          self._showToast(
            'Pesanan ' + (data.order_number || '#' + data.order_id),
            data.message || 'Status pesanan berubah: ' + data.status
          );
          document.dispatchEvent(new CustomEvent('warungio:order_update', {
            detail: data
          }));
        })
      );

      this.unsubscribers.push(
        ws.on('payment_update', function (data) {
          self._showToast(
            'Pembayaran ' + (data.order_number || '#' + data.order_id),
            data.message || 'Status pembayaran: ' + data.status
          );
          document.dispatchEvent(new CustomEvent('warungio:payment_update', {
            detail: data
          }));
        })
      );
    }

    // ── API ──

    async _fetchUnreadCount() {
      if (!window.WarungioAPI) return;
      try {
        // Use the unread-count endpoint which returns { total_unread, order_unread, ... }
        var data = await WarungioAPI.getNotifications({ unread: 'true' });
        // The list endpoint returns paginated { count, results } where results is the notif array
        // The unread-count endpoint returns { total_unread, order_unread, ... }
        if (data && typeof data.total_unread === 'number') {
          this.unreadCount = data.total_unread;
        } else if (data && data.count !== undefined) {
          this.unreadCount = data.count;
        } else if (Array.isArray(data)) {
          this.unreadCount = data.length;
        } else if (data && Array.isArray(data.results)) {
          this.unreadCount = data.results.length;
        } else {
          this.unreadCount = 0;
        }
        this._updateBadge();
      } catch (e) {
        // Silent
      }
    }

    async _fetchNotifications() {
      if (!window.WarungioAPI) return;
      this.notifList.innerHTML = '<div class="notif-loading">Memuat...</div>';
      try {
        // Use smaller page size to ensure we get recent notifications
        var data = await WarungioAPI.getNotifications({ pageSize: 20 });
        this.notifications = data && data.results ? data.results : (Array.isArray(data) ? data : []);
        this._renderNotifications();
      } catch (e) {
        this.notifList.innerHTML = '<div class="notif-empty">Gagal memuat notifikasi.</div>';
      }
    }

    async _markAllRead() {
      if (!window.WarungioAPI || this.unreadCount === 0) return;
      try {
        await WarungioAPI.markAllNotificationsRead();
        this.unreadCount = 0;
        this._updateBadge();
      } catch (e) {
        // Silent
      }
    }

    // ── UI Updates ──

    _updateBadge() {
      if (!this.badge) return;
      if (this.unreadCount > 0) {
        this.badge.textContent = this.unreadCount > 99 ? '99+' : this.unreadCount;
        this.badge.style.display = 'flex';
      } else {
        this.badge.style.display = 'none';
      }
    }

    _renderNotifications() {
      if (!this.notifList) return;

      if (this.notifications.length === 0) {
        this.notifList.innerHTML = '<div class="notif-empty">Belum ada notifikasi.</div>';
        return;
      }

      this.notifList.innerHTML = '';
      var self = this;
      this.notifications.slice(0, 20).forEach(function (n) {
        var el = document.createElement('div');
        el.className = 'notif-item' + (n.is_read ? '' : ' unread');
        el.innerHTML =
          '<div class="notif-icon ' + (n.notification_type || 'system') + '">' +
            self._getIcon(n.notification_type) +
          '</div>' +
          '<div class="notif-content">' +
            '<div class="notif-title">' + self._escape(n.title) + '</div>' +
            (n.description ? '<div class="notif-desc">' + self._escape(n.description) + '</div>' : '') +
            '<div class="notif-time">' + (n.time_ago || '') + '</div>' +
          '</div>' +
          (n.action_url ? '<a href="' + self._escape(n.action_url) + '" class="notif-action">' + (n.action_text || 'Lihat') + '</a>' : '');
        self.notifList.appendChild(el);
      });
    }

    _prependNotification(data) {
      if (!this.notifList) return;
      // Only prepend if dropdown is open
      if (this.dropdown.style.display !== 'block') return;

      var empty = this.notifList.querySelector('.notif-empty, .notif-loading');
      if (empty) empty.remove();

      var el = document.createElement('div');
      el.className = 'notif-item unread';
      el.innerHTML =
        '<div class="notif-icon ' + (data.notification_type || 'system') + '">' +
          this._getIcon(data.notification_type) +
        '</div>' +
        '<div class="notif-content">' +
          '<div class="notif-title">' + this._escape(data.title || '') + '</div>' +
          (data.description ? '<div class="notif-desc">' + this._escape(data.description) + '</div>' : '') +
          '<div class="notif-time">Baru saja</div>' +
        '</div>';
      this.notifList.insertBefore(el, this.notifList.firstChild);
    }

    _showToast(title, message) {
      var toast = document.createElement('div');
      toast.className = 'warungio-toast';
      toast.innerHTML =
        '<div class="warungio-toast-inner">' +
          '<strong>' + this._escape(title) + '</strong>' +
          (message ? '<p>' + this._escape(message) + '</p>' : '') +
        '</div>' +
        '<button class="warungio-toast-close">&times;</button>';
      document.body.appendChild(toast);

      requestAnimationFrame(function () { toast.classList.add('show'); });

      var timer = setTimeout(function () {
        toast.classList.remove('show');
        setTimeout(function () { if (toast.parentNode) toast.remove(); }, 300);
      }, 5000);

      toast.querySelector('.warungio-toast-close').addEventListener('click', function () {
        clearTimeout(timer);
        toast.classList.remove('show');
        setTimeout(function () { if (toast.parentNode) toast.remove(); }, 300);
      });
    }

    _getIcon(type) {
      var icons = {
        order: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>',
        payment: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>',
        chat: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
        promo: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 12V8H6a2 2 0 0 1-2-2c0-1.1.9-2 2-2h12v4"/><path d="M4 6v12c0 1.1.9 2 2 2h14v-4"/><path d="M18 12a2 2 0 0 0-2 2c0 1.1.9 2 2 2h4v-4h-4z"/></svg>',
        system: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
      };
      return icons[type] || icons.system;
    }

    _escape(str) {
      if (!str) return '';
      var div = document.createElement('div');
      div.textContent = str;
      return div.innerHTML;
    }
  }

  // Singleton
  var instance = new NotificationWidget();

  // Expose globally
  window.WarungioNotifications = instance;

  // Add CSS automatically once
  if (!document.getElementById('warungio-notif-styles')) {
    var style = document.createElement('style');
    style.id = 'warungio-notif-styles';
    style.textContent =
      '.notif-widget { position: relative; display: inline-flex; }\n' +
      '.notif-trigger { position: relative; width: 40px; height: 40px; border: none; background: #f1f5f9; border-radius: 12px; cursor: pointer; display: flex; align-items: center; justify-content: center; color: #475569; transition: all 0.2s; }\n' +
      '.notif-trigger:hover { background: #dcfce7; color: #16a34a; }\n' +
      '.notif-badge { position: absolute; top: -4px; right: -4px; min-width: 18px; height: 18px; padding: 0 4px; background: #ef4444; color: white; font-size: 10px; font-weight: 800; border-radius: 999px; align-items: center; justify-content: center; border: 2px solid white; }\n' +
      '.notif-dropdown { position: absolute; top: calc(100% + 8px); right: 0; width: 360px; max-height: 480px; background: white; border-radius: 16px; border: 1px solid rgba(34, 197, 94, 0.18); box-shadow: 0 20px 60px rgba(0, 0, 0, 0.12); z-index: 1000; display: none; overflow: hidden; }\n' +
      '.notif-dropdown-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid rgba(34, 197, 94, 0.12); }\n' +
      '.notif-dropdown-header h4 { margin: 0; font-size: 0.95rem; font-weight: 700; }\n' +
      '.notif-mark-all { border: none; background: transparent; color: #16a34a; font-size: 0.8rem; font-weight: 600; cursor: pointer; padding: 4px 8px; border-radius: 6px; }\n' +
      '.notif-mark-all:hover { background: #dcfce7; }\n' +
      '.notif-list { max-height: 380px; overflow-y: auto; }\n' +
      '.notif-item { display: flex; gap: 12px; padding: 14px 20px; border-bottom: 1px solid rgba(34, 197, 94, 0.06); transition: background 0.15s; align-items: flex-start; }\n' +
      '.notif-item:hover { background: #f8fafc; }\n' +
      '.notif-item.unread { background: #f0fdf4; }\n' +
      '.notif-icon { width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; background: #f1f5f9; color: #64748b; }\n' +
      '.notif-icon.order { background: #dcfce7; color: #16a34a; }\n' +
      '.notif-icon.payment { background: #dbeafe; color: #2563eb; }\n' +
      '.notif-icon.chat { background: #fce7f3; color: #db2777; }\n' +
      '.notif-icon.promo { background: #fef3c7; color: #d97706; }\n' +
      '.notif-icon.system { background: #e0e7ff; color: #4f46e5; }\n' +
      '.notif-content { flex: 1; min-width: 0; }\n' +
      '.notif-title { font-size: 0.85rem; font-weight: 600; color: #0f172a; }\n' +
      '.notif-desc { font-size: 0.8rem; color: #475569; margin-top: 2px; line-height: 1.4; }\n' +
      '.notif-time { font-size: 0.75rem; color: #94a3b8; margin-top: 4px; }\n' +
      '.notif-action { font-size: 0.8rem; font-weight: 600; color: #16a34a; white-space: nowrap; text-decoration: none; padding: 4px 8px; border-radius: 6px; flex-shrink: 0; }\n' +
      '.notif-action:hover { background: #dcfce7; }\n' +
      '.notif-loading, .notif-empty { padding: 32px 20px; text-align: center; color: #94a3b8; font-size: 0.85rem; }\n' +
      '.warungio-toast { position: fixed; bottom: 24px; right: 24px; max-width: 380px; background: #1e293b; color: white; border-radius: 14px; padding: 16px 20px; box-shadow: 0 16px 40px rgba(0, 0, 0, 0.2); z-index: 9999; display: flex; gap: 12px; align-items: flex-start; opacity: 0; transform: translateY(16px); transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); pointer-events: none; }\n' +
      '.warungio-toast.show { opacity: 1; transform: translateY(0); pointer-events: auto; }\n' +
      '.warungio-toast-inner { flex: 1; }\n' +
      '.warungio-toast strong { display: block; font-size: 0.9rem; margin-bottom: 4px; }\n' +
      '.warungio-toast p { margin: 0; font-size: 0.8rem; opacity: 0.85; line-height: 1.4; }\n' +
      '.warungio-toast-close { border: none; background: rgba(255,255,255,0.15); color: white; width: 24px; height: 24px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 14px; }\n' +
      '.warungio-toast-close:hover { background: rgba(255,255,255,0.25); }';
    document.head.appendChild(style);
  }
})();
