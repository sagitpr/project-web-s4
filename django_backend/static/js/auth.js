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

    /** Clear all auth data and redirect to landing page */
    logout() {
      const refresh = this.getRefreshToken();
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_KEY);
      localStorage.removeItem(USER_KEY);
      // Try to blacklist refresh token on server
      if (refresh) {
        var headers = {
          'Content-Type': 'application/json',
        };
        var csrfToken = getCSRFToken();
        if (csrfToken) {
          headers['X-CSRFToken'] = csrfToken;
        }
        fetch(API_BASE + '/token/blacklist/', {
          method: 'POST',
          headers: headers,
          credentials: 'same-origin',
          body: JSON.stringify({ refresh }),
        }).catch(function () {});
      }
      window.location.href = '/';
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

    /** Check if user is a seller */
    isSeller() {
      const user = this.getUser();
      return user && user.role === 'seller';
    },

    /**
     * Get the correct dashboard URL for the given role.
     * @param {string} [role] - User role. Reads from cached user if omitted.
     * @returns {string} Dashboard URL path
     */
    getRoleDashboardUrl(role) {
      if (!role) {
        const user = this.getUser();
        role = user ? user.role : null;
      }
      if (role === 'seller') return '/seller/dashboard/';
      if (role === 'admin') return '/admin/';
      // Default for buyers and unknown roles
      return '/buyer/home/';
    },

    /**
     * Redirect user to their role-appropriate dashboard.
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
        throw new Error(msg);
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
