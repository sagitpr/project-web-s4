/**
 * Warungio Auth UI — Shared utility for auth-dependent DOM manipulation.
 * Eliminates duplicate DOMContentLoaded auth logic across 15+ templates.
 *
 * Usage:
 *   <script src="{% static 'js/utils/auth-ui.js' %}"></script>
 *   <script>WarungioAuthUI.init()</script>
 *
 * Dependencies: WarungioAuth (auth.js), WarungioAPI (api.js)
 */
(function() {
  'use strict';

  var WarungioAuthUI = {
    /**
     * Initialize auth UI: show correct header/sidebar, bind dropdown, set user info
     * @param {Object} [opts]
     * @param {boolean} [opts.syncBalance=false] Whether to fetch wallet balance
     * @param {boolean} [opts.syncCart=false] Whether to fetch cart count
     */
    init: function(opts) {
      opts = opts || {};
      this._bindProfileDropdown();
      this._bindLogout();
      this._toggleAuthState();

      if (this.isAuthenticated()) {
        if (opts.syncBalance !== false) this._syncBalance();
        if (opts.syncCart !== false) this._syncCartCount();
      }
    },

    /**
     * Check if user is authenticated via WarungioAuth
     */
    isAuthenticated: function() {
      return !!(window.WarungioAuth && window.WarungioAuth.isAuthenticated());
    },

    /**
     * Get user data from WarungioAuth
     */
    getUser: function() {
      if (!window.WarungioAuth) return null;
      try { return window.WarungioAuth.getUser(); } catch(e) { return null; }
    },

    /**
     * Toggle between authenticated and guest UI states
     * Uses standard element IDs used across all Buyer templates
     */
    _toggleAuthState: function() {
      var authEl = document.getElementById('authHeaderActions');
      var guestEl = document.getElementById('guestHeaderActions');

      if (!authEl && !guestEl) return;

      if (this.isAuthenticated()) {
        if (authEl) authEl.style.display = 'flex';
        if (guestEl) guestEl.style.display = 'none';
        this._setUserName();
      } else {
        if (authEl) authEl.style.display = 'none';
        if (guestEl) guestEl.style.display = 'flex';
      }
    },

    /**
     * Set user name/avatar from WarungioAuth data
     */
    _setUserName: function() {
      var nameEl = document.getElementById('userName');
      var avatarEl = document.getElementById('userAvatar');

      if (!nameEl && !avatarEl) return;

      var u = this.getUser();
      if (!u) return;

      var displayName = u.full_name || u.email || 'User';
      var firstName = displayName.split(' ')[0];

      if (nameEl) nameEl.textContent = 'Hai, ' + firstName;
      if (avatarEl && u.profile_photo) avatarEl.src = u.profile_photo;

      // Try to fetch fresh data from API for accuracy
      if (window.WarungioAPI) {
        WarungioAPI.checkAuth().then(function(resp) {
          if (resp && resp.user) {
            var fresh = resp.user;
            if (nameEl) nameEl.textContent = 'Hai, ' + (fresh.full_name || fresh.email || '').split(' ')[0];
            if (avatarEl && fresh.profile_photo) avatarEl.src = fresh.profile_photo;

            // Update role badge
            var badgeEl = document.getElementById('userRoleBadge');
            if (badgeEl) {
              badgeEl.textContent = (fresh.role === 'seller' || fresh.role === 'mitra') ? 'Penjual' : 'Member';
            }
          }
        }).catch(function() {});
      }
    },

    /**
     * Sync wallet balance dropdown label
     */
    _syncBalance: function() {
      if (!window.WarungioAPI) return;
      var balanceEl = document.getElementById('userBalanceDropdown');
      if (!balanceEl) return;

      WarungioAPI.getWalletBalance().then(function(data) {
        if (data && data.balance !== undefined) {
          balanceEl.textContent = 'Rp ' + Number(data.balance).toLocaleString('id-ID');
        }
      }).catch(function() {});
    },

    /**
     * Sync cart count badge
     */
    _syncCartCount: function() {
      if (!window.WarungioAPI) return;
      var cartBadge = document.getElementById('cartBadgeHeader');
      if (!cartBadge) return;

      WarungioAPI.getCartCount().then(function(res) {
        if (res && res.count !== undefined) {
          cartBadge.textContent = res.count;
        }
      }).catch(function() {});
    },

    /**
     * Bind profile dropdown toggle
     */
    _bindProfileDropdown: function() {
      var profileBox = document.getElementById('profileBox');
      var dropdown = document.getElementById('dropdownMenu');

      if (!profileBox || !dropdown) return;

      profileBox.addEventListener('click', function(e) {
        e.stopPropagation();
        dropdown.classList.toggle('show');
      });

      document.addEventListener('click', function() {
        dropdown.classList.remove('show');
      });
    },

    /**
     * Bind logout button
     */
    _bindLogout: function() {
      var logoutBtn = document.getElementById('btnLogout');
      if (!logoutBtn) return;

      logoutBtn.addEventListener('click', function(e) {
        e.preventDefault();
        if (window.WarungioAuth) {
          window.WarungioAuth.logout();
          window.location.href = '/';
        }
      });
    },

    /**
     * Show a toast notification using WarungioAPI or fallback
     * Consolidated to eliminate 12× duplicate showToast functions
     */
    showToast: function(message, type) {
      type = type || 'info';
      
      // Use WarungioAPI.showToast if available
      if (window.WarungioAPI && window.WarungioAPI.showToast) {
        WarungioAPI.showToast(message, type);
        return;
      }

      // Fallback: create toast element manually
      var container = document.getElementById('toastContainer');
      if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        container.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;pointer-events:none;';
        document.body.appendChild(container);
      }

      var toast = document.createElement('div');
      toast.className = 'toast ' + type;
      toast.style.cssText = 'display:flex;align-items:center;gap:8px;padding:12px 20px;border-radius:12px;font-size:13px;font-weight:600;box-shadow:0 4px 12px rgba(0,0,0,.1);animation:slideIn .3s ease;margin-bottom:8px;pointer-events:auto;max-width:400px;';

      var colors = {
        success: { bg: '#dcfce7', text: '#166534', border: '#bbf7d0' },
        error: { bg: '#fee2e2', text: '#991b1b', border: '#fecaca' },
        info: { bg: '#dbeafe', text: '#1e40af', border: '#bfdbfe' },
        warning: { bg: '#fef3c7', text: '#92400e', border: '#fde68a' }
      };

      var c = colors[type] || colors.info;
      toast.style.background = c.bg;
      toast.style.color = c.text;
      toast.style.border = '1px solid ' + c.border;
      toast.innerHTML = '<span>' + message + '</span>';

      container.appendChild(toast);
      setTimeout(function() {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(function() { if (toast.parentNode) toast.remove(); }, 300);
      }, 3500);
    }
  };

  // Expose globally (also set window.showToast for backward compatibility with existing pages)
  window.WarungioAuthUI = WarungioAuthUI;
  window.showToast = function(msg, type) {
    return WarungioAuthUI.showToast(msg, type);
  };

})();
