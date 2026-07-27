/**
 * Warungio Floating Notification Bubble v2
 * Real-time notification system with WebSocket integration.
 * Features: rich media, dynamic actions per type, expand/collapse groups,
 * swipe dismiss, auto-hide, stacking, grouping.
 * Design System: Warungio marketplace notifications.
 */

(function(global) {
  'use strict';

  // ── Configuration ──
  const CONFIG = {
    maxVisible: 5,
    autoHideDuration: {
      urgent: 15000,
      high: 10000,
      medium: 7000,
      low: 5000,
    },
    groupThreshold: 3,
    wsReconnectDelay: 3000,
  };

  // ── Icon Mapping ──
  const ICONS = {
    order: 'fa-solid fa-receipt',
    payment: 'fa-solid fa-credit-card',
    chat: 'fa-solid fa-comment-dots',
    promo: 'fa-solid fa-tag',
    system: 'fa-solid fa-bell',
    review: 'fa-solid fa-star',
    follow: 'fa-solid fa-heart',
    product: 'fa-solid fa-box',
  };

  // ── Notification Type → Action Buttons ──
  const ACTION_MAP = {
    chat:    [
      { text: 'Balas',  url_field: 'action_url', cls: 'primary', icon: 'fa-regular fa-comment' },
      { text: 'Tutup',  cls: 'secondary' },
    ],
    order:   [
      { text: 'Lacak',  url_field: 'action_url', cls: 'primary', icon: 'fa-regular fa-location-dot' },
      { text: 'Lihat',  url_field: 'action_url', cls: 'secondary', icon: 'fa-regular fa-eye' },
      { text: 'Tutup',  cls: 'secondary' },
    ],
    payment: [
      { text: 'Bayar',  url_field: 'action_url', cls: 'primary', icon: 'fa-regular fa-credit-card' },
      { text: 'Lihat',  url_field: 'action_url', cls: 'secondary', icon: 'fa-regular fa-eye' },
      { text: 'Tutup',  cls: 'secondary' },
    ],
    promo:   [
      { text: 'Lihat',  url_field: 'action_url', cls: 'primary', icon: 'fa-regular fa-gift' },
      { text: 'Tutup',  cls: 'secondary' },
    ],
    review:  [
      { text: 'Lihat',  url_field: 'action_url', cls: 'primary', icon: 'fa-regular fa-star' },
      { text: 'Tutup',  cls: 'secondary' },
    ],
    follow:  [
      { text: 'Lihat',  url_field: 'action_url', cls: 'primary', icon: 'fa-regular fa-heart' },
      { text: 'Tutup',  cls: 'secondary' },
    ],
    product: [
      { text: 'Lihat',  url_field: 'action_url', cls: 'primary', icon: 'fa-regular fa-box' },
      { text: 'Tutup',  cls: 'secondary' },
    ],
    system:  [
      { text: 'Lihat',  url_field: 'action_url', cls: 'primary', icon: 'fa-regular fa-cog' },
      { text: 'Tutup',  cls: 'secondary' },
    ],
  };

  // ── Sound (vibrate fallback) ──
  function playNotificationSound() {
    try {
      if (navigator.vibrate) navigator.vibrate([50, 100, 50]);
    } catch(e) { /* silent fallback */ }
  }

  // ── Time formatter ──
  function formatTime(isoString) {
    if (!isoString) return '';
    const now = new Date();
    const date = new Date(isoString);
    const diffMs = now - date;
    const diffMin = Math.floor(diffMs / 60000);
    const diffHour = Math.floor(diffMs / 3600000);
    const diffDay = Math.floor(diffMs / 86400000);

    if (diffMin < 1) return 'baru saja';
    if (diffMin < 60) return diffMin + 'm';
    if (diffHour < 24) return diffHour + 'j';
    if (diffDay < 7) return diffDay + 'h';
    return date.toLocaleDateString('id-ID', { weekday: 'short', day: 'numeric' });
  }

  // ── Escaped string for HTML attribute values ──
  function escAttr(str) {
    if (!str) return '';
    return String(str).replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/&/g, '&amp;');
  }

  // ── Notification Bubble Manager ──
  const NotificationBubbleManager = {
    container: null,
    bubbles: [],
    ws: null,
    wsConnected: false,
    groupCounts: {},
    groupedNotifs: {},  // type -> [{notif}]
    timers: {},

    // ── Initialize ──
    init: function() {
      if (!document.querySelector('.notif-bubble-container')) {
        this.container = document.createElement('div');
        this.container.className = 'notif-bubble-container';
        document.body.appendChild(this.container);
      } else {
        this.container = document.querySelector('.notif-bubble-container');
      }

      this.loadUnreadNotifications();
      this.connectWebSocket();

      // Polling fallback every 60 seconds
      setInterval(this.loadUnreadNotifications.bind(this), 60000);
    },

    // ── Load Unread Notifications via API ──
    loadUnreadNotifications: function() {
      const token = global.WarungioAuth?.getAccessToken?.() || localStorage.getItem('warungio_access_token');
      if (!token) return;

      fetch('/api/notifications/?unread_only=true&limit=5', {
        headers: { 'Authorization': 'Bearer ' + token, 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'include',
      })
      .then(r => r.json())
      .then(data => {
        const notifs = data.results || data || [];
        notifs.forEach(n => {
          if (!n.is_read) this.show(n);
        });
        this.updateBellBadge(notifs.filter(n => !n.is_read).length);
      })
      .catch(function(){});
    },

    // ── Connect WebSocket ──
    connectWebSocket: function() {
      var protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      var wsUrl = protocol + '//' + window.location.host + '/ws/notifications/';

      try {
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = function() {
          this.wsConnected = true;
        }.bind(this);

        this.ws.onmessage = function(event) {
          try {
            var data = JSON.parse(event.data);
            if (data.type === 'notification') {
              this.show({
                id: data.id,
                notification_type: data.notification_type,
                title: data.title,
                description: data.description,
                priority: data.priority || 'medium',
                action_url: data.action_url,
                image_url: data.image_url,
                metadata: data.metadata || {},
                created_at: data.created_at,
              });
              playNotificationSound();
            } else if (data.type === 'unread_count') {
              this.updateBellBadge(data.count || 0);
            }
          } catch(e) {}
        }.bind(this);

        this.ws.onclose = function() {
          this.wsConnected = false;
          setTimeout(this.connectWebSocket.bind(this), CONFIG.wsReconnectDelay);
        }.bind(this);

        this.ws.onerror = function() {
          this.ws.close();
        }.bind(this);
      } catch(e) {
        setTimeout(this.connectWebSocket.bind(this), CONFIG.wsReconnectDelay);
      }
    },

    // ── Build action buttons HTML for a notification ──
    buildActions: function(notif) {
      var actions = ACTION_MAP[notif.notification_type] || ACTION_MAP.system;
      var html = '';
      for (var i = 0; i < actions.length; i++) {
        var a = actions[i];
        if (a.url_field && notif[a.url_field]) {
          html += '<a href="' + escAttr(notif[a.url_field]) + '" class="notif-action-btn ' + a.cls + '" data-notif-id="' + (notif.id || '') + '">' +
            (a.icon ? '<i class="' + a.icon + '"></i>' : '') +
            escAttr(a.text) + '</a>';
        } else if (!a.url_field) {
          html += '<button class="notif-action-btn ' + a.cls + ' dismiss-btn" data-notif-id="' + (notif.id || '') + '">' +
            (a.icon ? '<i class="' + a.icon + '"></i>' : '') +
            escAttr(a.text) + '</button>';
        }
      }
      return html;
    },

    // ── Build rich media HTML for a notification ──
    buildRichMedia: function(notif) {
      var html = '';
      var m = notif.metadata || {};
      var imgUrl = notif.image_url || m.image || m.thumbnail || '';
      var qrUrl = m.qr_url || '';

      // Thumbnail image
      if (imgUrl) {
        html += '<div class="notif-media"><img src="' + escAttr(imgUrl) + '" alt="" class="notif-thumb" loading="lazy" /></div>';
      }

      // QR code (for payment proof, etc)
      if (qrUrl) {
        html += '<div class="notif-media notif-qr"><img src="' + escAttr(qrUrl) + '" alt="QR" class="notif-qr-img" loading="lazy" /></div>';
      }

      // Status badges (payment/delivery status)
      if (m.status_text) {
        var statusColor = m.status_color || '#22c55e';
        html += '<div class="notif-status" style="--notif-status-color:' + statusColor + '">' + escAttr(m.status_text) + '</div>';
      }

      return html;
    },

    // ── Build icon HTML (support avatar or gradient icon) ──
    buildIcon: function(notif) {
      var typeClass = notif.notification_type || 'system';
      var m = notif.metadata || {};
      var avatarUrl = m.avatar_url || '';

      if (avatarUrl) {
        return '<div class="notif-icon type-' + typeClass + ' has-avatar"><img src="' + escAttr(avatarUrl) + '" alt="" class="avatar-icon" /></div>';
      }
      var icon = ICONS[notif.notification_type] || 'fa-solid fa-bell';
      return '<div class="notif-icon type-' + typeClass + '"><i class="' + icon + '"></i></div>';
    },

    // ── Show a notification bubble ──
    show: function(notif) {
      if (!this.container) return;

      // Track notification for group expand
      var typeClass = notif.notification_type || 'system';
      if (!this.groupedNotifs[typeClass]) this.groupedNotifs[typeClass] = [];
      this.groupedNotifs[typeClass].push(notif);

      // Try grouping first
      if (this.tryGroup(notif)) return;

      // Remove oldest if at max
      while (this.bubbles.length >= CONFIG.maxVisible) {
        var oldest = this.bubbles.shift();
        this.removeBubble(oldest.id);
      }

      var id = (notif.id ? String(notif.id) : 'notif-' + Date.now() + '-' + Math.random());
      var priority = notif.priority || 'medium';
      var autoHideMs = CONFIG.autoHideDuration[priority] || 7000;
      var timeStr = formatTime(notif.created_at);

      // Build bubble
      var el = document.createElement('div');
      el.id = 'bubble-' + id;
      el.className = 'notif-bubble priority-' + priority;
      el.setAttribute('role', 'alert');
      el.setAttribute('aria-live', 'polite');

      var iconHtml = this.buildIcon(notif);
      var actionsHtml = this.buildActions(notif);
      var mediaHtml = this.buildRichMedia(notif);

      el.innerHTML =
        iconHtml +
        '<div class="notif-content">' +
          '<div class="notif-header">' +
            '<span class="notif-app-name">Warungio</span>' +
            '<span class="notif-time">' + timeStr + '</span>' +
          '</div>' +
          '<div class="notif-title">' + this.escapeHtml(notif.title || 'Notifikasi') + '</div>' +
          '<div class="notif-body">' + this.escapeHtml(notif.description || '') + '</div>' +
          mediaHtml +
          '<div class="notif-actions">' + actionsHtml + '</div>' +
        '</div>' +
        '<button class="notif-dismiss" aria-label="Tutup notifikasi">✕</button>';

      this.container.appendChild(el);
      this.bubbles.push({
        id: id,
        el: el,
        type: typeClass,
        priority: priority,
        notifId: notif.id,
      });

      // ── Event: Dismiss button → mark read + remove ──
      var dismissBtn = el.querySelector('.notif-dismiss');
      if (dismissBtn) {
        dismissBtn.addEventListener('click', function(e) {
          e.stopPropagation();
          this.markRead(notif.id);
          this.removeBubble(id);
        }.bind(this));
      }

      // ── Event: Secondary dismiss buttons → mark read + remove ──
      var secBtns = el.querySelectorAll('.dismiss-btn');
      for (var s = 0; s < secBtns.length; s++) {
        secBtns[s].addEventListener('click', function(e) {
          e.stopPropagation();
          this.markRead(notif.id);
          this.removeBubble(id);
        }.bind(this));
      }

      // ── Event: Primary action links → just navigate (server marks read) ──
      var primaryLinks = el.querySelectorAll('.notif-action-btn.primary');
      for (var p = 0; p < primaryLinks.length; p++) {
        if (primaryLinks[p].tagName === 'A') {
          primaryLinks[p].addEventListener('click', function(e) {
            this.markRead(notif.id);
          }.bind(this));
        }
      }

      // ── Swipe to dismiss ──
      this.initSwipe(el, id, notif);

      // ── Auto-hide timer ──
      if (priority !== 'urgent') {
        this.timers[id] = setTimeout(function() {
          this.removeBubble(id);
        }.bind(this), autoHideMs);
      }
    },

    // ── Try grouping with existing bubbles ──
    tryGroup: function(notif) {
      var type = notif.notification_type || 'system';
      var existing = this.bubbles.filter(function(b) {
        return b.type === type && b.el.parentNode;
      });

      if (existing.length >= CONFIG.groupThreshold - 1) {
        this.groupCounts[type] = (this.groupCounts[type] != null ? this.groupCounts[type] : 1) + 1;
        var count = this.groupCounts[type];

        var groupEl = this.container.querySelector('.notif-bubble.group-summary[data-type="' + type + '"]');
        if (!groupEl) {
          var icon = ICONS[type] || 'fa-solid fa-bell';
          var groupId = 'group-' + type + '-' + Date.now();
          var el = document.createElement('div');
          el.id = 'bubble-' + groupId;
          el.className = 'notif-bubble group-summary';
          el.setAttribute('data-type', type);
          el.setAttribute('tabindex', '0');
          el.setAttribute('role', 'button');
          el.innerHTML =
            '<div class="notif-icon type-' + type + '">' +
              '<i class="' + icon + '"></i>' +
            '</div>' +
            '<div class="notif-content">' +
              '<div class="notif-header">' +
                '<span class="notif-app-name">Warungio</span>' +
                '<span class="notif-time">' + formatTime(notif.created_at) + '</span>' +
              '</div>' +
              '<div class="notif-title">' + notif.title + '</div>' +
              '<div class="notif-body">+' + count + ' notifikasi ' + type + '</div>' +
              '<div class="notif-group-expand-hint">Tekan untuk perluas</div>' +
            '</div>' +
            '<button class="notif-dismiss" aria-label="Tutup">✕</button>';

          this.container.appendChild(el);
          this.bubbles.push({ id: groupId, el: el, type: type, isGroup: true });

          // ── Group dismiss ──
          var gDismiss = el.querySelector('.notif-dismiss');
          if (gDismiss) {
            gDismiss.addEventListener('click', function(e) {
              e.stopPropagation();
              this.expandGroup(type, true);
            }.bind(this));
          }

          // ── Click to expand group ──
          el.addEventListener('click', function(e) {
            if (e.target.closest('.notif-dismiss')) return;
            this.expandGroup(type);
          }.bind(this));

        } else {
          var bodyEl = groupEl.querySelector('.notif-body');
          if (bodyEl) {
            bodyEl.textContent = '+' + count + ' notifikasi ' + type;
          }
        }
        return true;
      }
      return false;
    },

    // ── Expand a stacked group into individual bubbles ──
    expandGroup: function(type, removeOnly) {
      var notifs = this.groupedNotifs[type] || [];

      // Find and remove group bubble
      var toRemove = [];
      for (var i = 0; i < this.bubbles.length; i++) {
        if (this.bubbles[i].isGroup && this.bubbles[i].type === type) {
          toRemove.push(this.bubbles[i].id);
        }
      }
      for (var j = 0; j < toRemove.length; j++) {
        this.removeBubble(toRemove[j]);
      }

      delete this.groupCounts[type];

      if (!removeOnly) {
        // Show individual bubbles for all grouped notifs
        for (var k = 0; k < notifs.length; k++) {
          this.show(notifs[k]);
        }
      }
    },

    // ── Remove a bubble with animation ──
    removeBubble: function(id) {
      var idx = this.bubbles.findIndex(function(b) { return b.id === id; });
      if (idx === -1) return;

      var bubble = this.bubbles[idx];
      var el = bubble.el;

      if (this.timers[id]) {
        clearTimeout(this.timers[id]);
        delete this.timers[id];
      }

      el.classList.add('swiped-out');
      el.style.pointerEvents = 'none';

      setTimeout(function() {
        if (el.parentNode) el.parentNode.removeChild(el);
      }, 300);

      this.bubbles.splice(idx, 1);

      if (bubble.isGroup && bubble.type) {
        delete this.groupCounts[bubble.type];
      }

      // Clean up groupedNotifs to prevent ghost bubbles on group expand
      if (bubble.type && this.groupedNotifs[bubble.type]) {
        this.groupedNotifs[bubble.type] = this.groupedNotifs[bubble.type].filter(function(n) {
          return String(n.id) !== String(bubble.notifId) && String(n.notifId) !== String(bubble.notifId);
        });
        if (this.groupedNotifs[bubble.type].length === 0) {
          delete this.groupedNotifs[bubble.type];
        }
      }
    },

    // ── Touch swipe handler │ marks read on dismiss ──
    initSwipe: function(el, id, notif) {
      var startX = 0;
      var currentX = 0;
      var isDragging = false;

      el.addEventListener('touchstart', function(e) {
        startX = e.touches[0].clientX;
        isDragging = true;
        el.classList.add('swiping');
      }, { passive: true });

      el.addEventListener('touchmove', function(e) {
        if (!isDragging) return;
        currentX = e.touches[0].clientX;
        var diff = currentX - startX;
        if (diff < 0) {
          el.style.transform = 'translateX(' + diff + 'px)';
          el.style.opacity = Math.max(0, 1 + diff / 300);
        }
      }, { passive: true });

      el.addEventListener('touchend', function() {
        if (!isDragging) return;
        isDragging = false;
        el.classList.remove('swiping');
        var diff = currentX - startX;
        if (diff < -80) {
          this.markRead(notif && notif.id);
          this.removeBubble(id);
        } else {
          el.style.transform = '';
          el.style.opacity = '';
        }
        startX = 0;
        currentX = 0;
      }.bind(this), { passive: true });
    },

    // ── Update bell badge ──
    updateBellBadge: function(count) {
      var badges = document.querySelectorAll('.notif-bell-badge');
      for (var i = 0; i < badges.length; i++) {
        if (count > 0) {
          badges[i].textContent = count > 99 ? '99+' : count;
          badges[i].classList.remove('hidden');
        } else {
          badges[i].classList.add('hidden');
        }
      }
    },

    // ── Mark notification as read via API (only on user interaction) ──
    markRead: function(notifId) {
      if (!notifId || String(notifId).indexOf('notif-') === 0) return;
      var token = global.WarungioAuth?.getAccessToken?.() || localStorage.getItem('warungio_access_token');
      if (!token) return;

      fetch('/api/notifications/mark-read/', {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer ' + token,
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify({ notification_ids: [notifId] }),
        credentials: 'include',
      }).catch(function(){});
    },

    // ── Escape HTML ──
    escapeHtml: function(str) {
      if (!str) return '';
      var div = document.createElement('div');
      div.appendChild(document.createTextNode(str));
      return div.innerHTML;
    },
  };

  // ── Initialize on DOM ready ──
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { NotificationBubbleManager.init(); });
  } else {
    NotificationBubbleManager.init();
  }

  // ── Expose globally ──
  global.WarungioNotifBubble = NotificationBubbleManager;

})(window);
