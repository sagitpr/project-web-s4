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

  const WarungioAuth = {
    /** Store tokens and user data */
    login(accessToken, refreshToken, user) {
      localStorage.setItem(TOKEN_KEY, accessToken);
      localStorage.setItem(REFRESH_KEY, refreshToken);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    },

    /** Clear all auth data */
    logout() {
      const refresh = this.getRefreshToken();
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_KEY);
      localStorage.removeItem(USER_KEY);
      // Try to blacklist refresh token on server
      if (refresh) {
        fetch(API_BASE + '/token/blacklist/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh }),
        }).catch(() => {});
      }
      window.location.href = '/auth/login/index.html';
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

    /** Try to refresh the access token */
    async refreshToken() {
      const refresh = this.getRefreshToken();
      if (!refresh) return false;

      try {
        const res = await fetch(API_BASE + '/token/refresh/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
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

      let res = await fetch(API_BASE + endpoint, {
        ...options,
        headers,
      });

      // If 401, try token refresh
      if (res.status === 401 && this.getRefreshToken()) {
        const refreshed = await this.refreshToken();
        if (refreshed) {
          headers['Authorization'] = `Bearer ${this.getAccessToken()}`;
          res = await fetch(API_BASE + endpoint, {
            ...options,
            headers,
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

      let res = await fetch(API_BASE + endpoint, {
        method: method,
        headers,
        body: formData,
      });

      if (res.status === 401 && this.getRefreshToken()) {
        const refreshed = await this.refreshToken();
        if (refreshed) {
          headers['Authorization'] = `Bearer ${this.getAccessToken()}`;
          res = await fetch(API_BASE + endpoint, {
            method: method,
            headers,
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
})();
