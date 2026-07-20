/**
 * Warungio Authentication Utility
 * JWT-based auth for Django REST API.
 * All frontend modules share this via global window.WarungioAuth.
 */
(function () {
  'use strict';

  // Auto-detect API base URL: use relative path, or full URL from env
var API_BASE = (window.API_BASE_URL || '/api').replace(/\/+$/, '');
  const TOKEN_KEY = 'warungio_access_token';
  const REFRESH_KEY = 'warungio_refresh_token';
  const USER_KEY = 'warungio_user';

  /**
   * Read CSRF token from the 'csrftoken' cookie.
   * Falls back to reading the csrfmiddlewaretoken hidden input in the DOM.
   * Requires CSRF_COOKIE_HTTPONLY = False in Django settings.
   * @returns {string|null} The CSRF token value, or null if not found.
   */
  function getCSRFToken() {
    var name = 'csrftoken';
    var cookie = document.cookie.split('; ').find(function (row) {
      return row.startsWith(name + '=');
    });
    var token = cookie ? decodeURIComponent(cookie.split('=')[1]) : null;

    // Fallback: read from hidden input rendered by {% csrf_token %}
    if (!token) {
      var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
      if (input) token = input.value;
    }

    return token;
  }

  const WarungioAuth = {
    /** Store tokens and user data */
    login(accessToken, refreshToken, user) {
      localStorage.setItem(TOKEN_KEY, accessToken);
      localStorage.setItem(REFRESH_KEY, refreshToken);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    },

    /**
     * Full logout — clears ALL client-side state, destroys server session,
     * and always redirects to the Landing Page.
     *
     * - Calls server logout API to blacklist JWT + destroy Django session
     * - Clears ALL localStorage (auth tokens, user data, search history, prefs, drafts)
     * - Clears ALL sessionStorage
     * - Clears Django auth cookies (csrftoken, sessionid)
     * - Clears service worker caches
     * - Replaces history to block browser back from restoring protected pages
     * - Always redirects to Landing Page (/)
     */
    logout() {
      const refresh = this.getRefreshToken();

      // 1. Fire server logout (fire-and-forget — clear client regardless of response)
      if (refresh) {
        var headers = {
          'Content-Type': 'application/json',
        };
        var csrfToken = getCSRFToken();
        if (csrfToken) {
          headers['X-CSRFToken'] = csrfToken;
        }
        // Try the dedicated auth/logout/ endpoint first (destroys Django session too)
        fetch(API_BASE + '/auth/logout/', {
          method: 'POST',
          headers: headers,
          credentials: 'same-origin',
          body: JSON.stringify({ refresh }),
        }).catch(function() {
          // Fallback: token blacklist endpoint only
          fetch(API_BASE + '/token/blacklist/', {
            method: 'POST',
            headers: headers,
            credentials: 'same-origin',
            body: JSON.stringify({ refresh }),
          }).catch(function() {});
        });
      }

      // 2. Clear ALL localStorage (auth tokens, user data, search history, prefs, drafts)
      localStorage.clear();

      // 3. Clear ALL sessionStorage
      sessionStorage.clear();

      // 4. Clear Django auth cookies
      document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/';
      document.cookie = 'sessionid=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/';

      // 5. Clear service worker caches
      if ('caches' in window) {
        caches.keys().then(function(names) {
          names.forEach(function(name) {
            caches.delete(name);
          });
        }).catch(function() {});
      }

      // 6. Replace history to prevent browser back from restoring protected pages
      try { window.history.replaceState(null, '', '/'); } catch(e) {}

      // 7. Always redirect to Landing Page — use replace() to remove the stale protected page
      //    from the browser's session history entirely, so Back button can't restore it.
      window.location.replace('/');
    },

    /** Get access token */
    getAccessToken() {
      return localStorage.getItem(TOKEN_KEY);
    },

    /** Get refresh token */
    getRefreshToken() {
      return localStorage.getItem(REFRESH_KEY);
    },

    /** Get cached user data */
    getUser() {
      try {
        const raw = localStorage.getItem(USER_KEY);
        return raw ? JSON.parse(raw) : null;
      } catch {
        return null;
      }
    },

    /** Check if user is logged in */
    isAuthenticated() {
      return !!this.getAccessToken();
    },

    /** Check if user is verified (OTP completed) */
    isVerified() {
      const user = this.getUser();
      return user && user.is_verified === true;
    },

    /** Check if user is a seller */
    isSeller() {
      const user = this.getUser();
      return user && user.role === 'seller';
    },

    /** Redirect to OTP verification page with the user's email */
    redirectToVerification(email) {
      const emailToUse = email || (this.getUser() && this.getUser().email);
      window.location.href = '/auth/otp/index.html?email=' + encodeURIComponent(emailToUse || '') + '&purpose=registration';
    },

    /**
     * Check if the current user needs verification and redirect if so.
     * Returns true if redirected, false if verification is not needed.
     */
    requireVerified() {
      if (!this.isAuthenticated()) {
        window.location.href = '/auth/login/index.html';
        return true;
      }
      if (!this.isVerified()) {
        const user = this.getUser();
        this.redirectToVerification(user ? user.email : '');
        return true;
      }
      return false;
    },

    /**
     * Get the correct dashboard URL for the given role.
     * Maps role to its designated entry point:
     *   buyer  → /buyer/home/  (Buyer Home)
     *   seller → /seller/dashboard/  (Seller Dashboard)
     *   admin  → /admin/       (Admin Dashboard)
     *   null/other → /         (Landing Page — never auto-redirect to Buyer Home)
     *
     * @param {string} [role] - User role. Reads from cached user if omitted.
     * @returns {string} Dashboard URL path
     */
    getRoleDashboardUrl(role) {
      if (!role) {
        const user = this.getUser();
        role = user ? user.role : null;
      }
      if (role === 'buyer') return '/buyer/home/';
      if (role === 'seller') return '/seller/dashboard/';
      if (role === 'admin') return '/admin/';
      // Default: Landing Page — the only public homepage. Never redirect to Buyer Home
      // unless the user explicitly logged in with ?role=buyer.
      return '/';
    },

    /**
     * Redirect user to their role-appropriate dashboard.
     * Uses getRoleDashboardUrl() which maps roles to correct entry points.
     * Optionally fetches fresh user data from API first.
     * @param {boolean} [forceFresh=false] - Whether to fetch fresh user role from API
     */
    redirectToDashboard(forceFresh) {
      const self = this;
      function doRedirect(role) {
        window.location.href = self.getRoleDashboardUrl(role);
      }

      if (forceFresh && window.WarungioAPI) {
        WarungioAPI.checkAuth()
          .then(function(resp) {
            if (resp && resp.user) {
              self.login(self.getAccessToken(), self.getRefreshToken(), resp.user);
              doRedirect(resp.user.role);
            } else {
              doRedirect();
            }
          })
          .catch(function() { doRedirect(); });
        return;
      }

      doRedirect();
    },

    /**
     * Get the correct login redirect URL for a given role from query param.
     * Delegates to getRoleDashboardUrl() which has the single source of truth
     * for role→URL mapping.
     *
     * @param {string|null} role - Role from query param
     * @returns {string} Redirect URL
     */
    getRoleLoginRedirect(role) {
      return this.getRoleDashboardUrl(role);
    },

    /**
     * Validate redirect URL — only allow relative paths to prevent open redirect.
     * @param {string} url
     * @returns {boolean}
     */
    isValidRedirect(url) {
      if (!url || typeof url !== 'string') return false;
      return url.startsWith('/') && !url.startsWith('//') && !url.includes('://');
    },

    /**
     * Check if a redirect URL matches the user's role prefix.
     * Buyer → /buyer/*, Seller → /seller/*, Admin → /admin/*
     * @param {string} nextUrl
     * @param {string} role
     * @returns {boolean}
     */
    isRoleAllowedRedirect(nextUrl, role) {
      if (!nextUrl || !role) return false;
      if (role === 'buyer') return nextUrl.startsWith('/buyer/');
      if (role === 'seller') return nextUrl.startsWith('/seller/');
      if (role === 'admin') return nextUrl.startsWith('/admin/');
      return false;
    },

    /** Try to refresh the access token */
    async refreshToken() {
      const refresh = this.getRefreshToken();
      if (!refresh) return false;

      try {
        var headers = {
          'Content-Type': 'application/json',
        };

        // Include CSRF token for Django's CsrfViewMiddleware
        var csrfToken = getCSRFToken();
        if (csrfToken) {
          headers['X-CSRFToken'] = csrfToken;
        }

        const res = await fetch(API_BASE + '/token/refresh/', {
          method: 'POST',
          headers: headers,
          credentials: 'same-origin',
          body: JSON.stringify({ refresh }),
        });
        if (!res.ok) {
          this.logout();
          return false;
        }
        const data = await res.json();
        localStorage.setItem(TOKEN_KEY, data.access);
        return true;
      } catch {
        return false;
      }
    },

    /**
     * Universal API fetch wrapper.
     * Automatically attaches JWT, handles 401 refresh, parses JSON.
     * Also includes X-CSRFToken header for unsafe methods and credentials: 'same-origin'
     * for session cookie support.
     *
     * @param {string} endpoint - e.g. '/auth/login/' or '/analytics/dashboard/'
     * @param {Object} options - fetch options
     * @returns {Promise<Object>} parsed JSON response
     */
    async api(endpoint, options = {}) {
      const token = this.getAccessToken();
      const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // Add CSRF token for unsafe methods (POST, PUT, PATCH, DELETE)
      var method = (options.method || 'GET').toUpperCase();
      if (['POST', 'PUT', 'PATCH', 'DELETE'].indexOf(method) !== -1) {
        var csrfToken = getCSRFToken();
        if (csrfToken) {
          headers['X-CSRFToken'] = csrfToken;
        }
      }

      let res = await fetch(API_BASE + endpoint, {
        ...options,
        headers,
        credentials: 'same-origin',
      });

      // If 401, try token refresh
      if (res.status === 401 && this.getRefreshToken()) {
        const refreshed = await this.refreshToken();
        if (refreshed) {
          headers['Authorization'] = `Bearer ${this.getAccessToken()}`;
          res = await fetch(API_BASE + endpoint, {
            ...options,
            headers,
            credentials: 'same-origin',
          });
        } else {
          this.logout();
          throw new Error('Sesi telah berakhir. Silakan login kembali.');
        }
      }

      const data = await res.json();

      if (!res.ok) {
        const msg =
          data.detail ||
          data.message ||
          data.error ||
          (data.email ? data.email.join(', ') : null) ||
          (data.password ? data.password.join(', ') : null) ||
          'Terjadi kesalahan. Silakan coba lagi.';

        // Create an error with extra fields so the caller can inspect
        // needs_verification, email, etc. for OTP redirect logic
        const err = new Error(msg);
        err.status = res.status;
        err.data = data;
        // Attach top-level fields for convenience
        if (data.needs_verification) {
          err.needs_verification = true;
          err.email = data.email || '';
        }
        throw err;
      }

      return data;
    },

    /** Upload a file (multipart) with JWT auth */
    async apiUpload(endpoint, formData, method = 'POST') {
      const token = this.getAccessToken();
      const headers = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // Add CSRF token for unsafe methods
      if (['POST', 'PUT', 'PATCH', 'DELETE'].indexOf(method.toUpperCase()) !== -1) {
        var csrfToken = getCSRFToken();
        if (csrfToken) {
          headers['X-CSRFToken'] = csrfToken;
        }
      }

      let res = await fetch(API_BASE + endpoint, {
        method: method,
        headers,
        credentials: 'same-origin',
        body: formData,
      });

      if (res.status === 401 && this.getRefreshToken()) {
        const refreshed = await this.refreshToken();
        if (refreshed) {
          headers['Authorization'] = `Bearer ${this.getAccessToken()}`;
          res = await fetch(API_BASE + endpoint, {
            method: method,
            headers,
            credentials: 'same-origin',
            body: formData,
          });
        }
      }

      const data = await res.json();
      if (!res.ok) {
        throw new Error(
          data.detail || data.error || 'Upload gagal. Silakan coba lagi.'
        );
      }
      return data;
    },
  };

  // Expose globally
  window.WarungioAuth = WarungioAuth;
  // Also expose getCSRFToken for page scripts to reuse
  window.WarungioAuth.getCSRFToken = getCSRFToken;
})();
