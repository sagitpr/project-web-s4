/**
 * Warungio Auth Guard — Cross-tab logout detection & page access protection.
 *
 * Place this at the TOP of every protected page's <head> (before any other JS)
 * to prevent flash-of-protected-page when the user's session has expired.
 *
 * Features:
 * - Detects cross-tab logout events via localStorage
 * - Prevents browser back button from showing cached protected pages
 * - Redirects unauthenticated users from protected pages to Landing Page
 * - Shows notification toast when session expires
 *
 * Usage in templates:
 *   <script src="{% static 'js/utils/auth-guard.js' %}"></script>
 *   <script>WarungioAuthGuard.init({ protected: true })</script>
 *
 * For public pages (no redirect on unauthenticated):
 *   <script>WarungioAuthGuard.init({ protected: false })</script>
 */
(function() {
  'use strict';

  var LOGOUT_EVENT_KEY = 'warungio_logout';

  var WarungioAuthGuard = {
    /**
     * Initialize auth guard.
     * @param {Object} opts
     * @param {boolean} opts.protected - If true, redirect to landing page when unauthenticated
     * @param {string} opts.redirectUrl - URL to redirect to (default: '/')
     */
    init: function(opts) {
      opts = opts || {};

      // 1. Listen for cross-tab logout events
      this._listenCrossTabLogout();

      // 2. Check auth state on page visibility change (back button, tab switch)
      this._listenVisibilityChange(opts);

      // 3. Check auth state on page show (browser back/forward cache)
      this._listenPageShow(opts);

      // 4. Initial check — redirect if on protected page without auth
      if (opts.protected !== false) {
        this._checkAuthAndRedirect(opts.redirectUrl || '/');
      }
    },

    /**
     * Listen for localStorage changes from other tabs.
     * When another tab fires logout(), it sets 'warungio_logout'.
     * This tab detects it and redirects immediately.
     */
    _listenCrossTabLogout: function() {
      var self = this;
      try {
        window.addEventListener('storage', function(e) {
          if (e.key === LOGOUT_EVENT_KEY && e.newValue) {
            // Another tab logged out — follow suit
            try {
              localStorage.removeItem(LOGOUT_EVENT_KEY);
            } catch(_) {}
            self._doRedirect('/');
          }
        });
      } catch(e) {
        // localStorage not available — ignore
      }
    },

    /**
     * Listen for page visibility changes.
     * When user switches back to this tab, re-check auth state.
     * Catches cases where user logs out in another tab then returns here.
     */
    _listenVisibilityChange: function(opts) {
      var self = this;
      document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
          // Tab became visible — check if we're still authenticated
          if (opts.protected !== false) {
            self._checkAuthAndRedirect(opts.redirectUrl || '/');
          }
        }
      });
    },

    /**
     * Listen for pageshow event (fires when page is restored from bfcache).
     * Browser's back/forward cache can restore a previous page state even
     * after logout. This ensures we re-check auth state on every page show.
     */
    _listenPageShow: function(opts) {
      var self = this;
      window.addEventListener('pageshow', function(event) {
        // event.persisted === true when page was restored from bfcache
        if (event.persisted && opts.protected !== false) {
          self._checkAuthAndRedirect(opts.redirectUrl || '/');
        }
      });
    },

    /**
     * Check if user is authenticated. If not, redirect to landing page.
     */
    _checkAuthAndRedirect: function(redirectUrl) {
      var isAuth = !!(window.WarungioAuth && window.WarungioAuth.isAuthenticated());
      if (!isAuth) {
        // Check if current page is a protected path.
        // Protected pages start with /seller/, /buyer/, /admin-panel/, or /admin/.
        // All other paths (/, /auth/, /info/, /bantuan/, /store/, /order/, /download/)
        // are public and accessible without auth.
        var path = window.location.pathname;
        var isProtectedPage = (
          path.startsWith('/seller/') ||
          path.startsWith('/buyer/') ||
          path.startsWith('/admin-panel/') ||
          path.startsWith('/admin/')
        );
        if (isProtectedPage) {
          this._doRedirect(redirectUrl);
        }
      }
    },

    /**
     * Perform redirect with history replacement.
     */
    _doRedirect: function(url) {
      try {
        window.history.replaceState(null, '', url);
      } catch(e) {}
      window.location.replace(url);
    }
  };

  // Expose globally
  window.WarungioAuthGuard = WarungioAuthGuard;
})();
