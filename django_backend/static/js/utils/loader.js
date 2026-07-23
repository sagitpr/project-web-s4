/**
 * Warungio Global Premium Loader — v1
 * Reusable loading overlay for all async operations.
 * GPU-accelerated, accessible, zero layout shift.
 *
 * ── Usage ──
 *   WarungioLoader.show()           // Show full-page loader
 *   WarungioLoader.hide()           // Hide loader
 *   WarungioLoader.showMini(el)     // Show mini-loader inside an element
 *   WarungioLoader.hideMini(el)     // Remove mini-loader
 *   WarungioLoader.setStatus(text)  // Update status text
 *
 * ── Auto-intercepted operations ──
 *   - All fetch() calls (via monkey-patch)
 *   - AJAX (XMLHttpRequest)
 *   - Form submissions (via .warungio-loading class)
 *
 * Dependencies: None (vanilla JS, works standalone)
 */

(function() {
  'use strict';

  var LOADER_ID = 'warungioLoaderOverlay';
  var LOADER_HTML = null; // Will be set from the DOM template

  var WarungioLoader = {
    _activeRequests: new Set(),
    _autoShow: true,
    _initialized: false,
    _minDuration: 300,
    _showTimer: null,
    _hideQueued: false,

    /**
     * Initialize loader — call once after DOM is ready
     * Creates the overlay from existing template or builds inline
     */
    init: function(opts) {
      if (this._initialized) return;
      opts = opts || {};
      this._autoShow = opts.autoShow !== false;
      if (opts.minDuration !== undefined) this._minDuration = opts.minDuration;

      // Try to find existing loader template
      var template = document.getElementById('warungioLoaderTemplate');
      if (template) {
        LOADER_HTML = template.innerHTML;
      }

      // If no overlay exists yet, create one
      if (!document.getElementById(LOADER_ID)) {
        this._createOverlay();
      }

      // Intercept fetch() for auto-show/hide
      if (this._autoShow && !this._patched) {
        this._patchFetch();
        this._patchXHR();
        this._patchHTMX();
        this._patchWebSocket();
        this._patched = true;
      }

      this._initialized = true;
    },

    /**
     * Show full-page loading overlay
     * Respects minimum duration to prevent flash for fast requests
     */
    show: function(statusText) {
      var self = this;

      // Update status text if provided
      if (statusText) {
        this.setStatus(statusText);
      }

      // Debounce: don't show immediately for fast requests
      if (this._showTimer) clearTimeout(this._showTimer);
      this._showTimer = setTimeout(function() {
        var overlay = document.getElementById(LOADER_ID);
        if (!overlay) {
          self._createOverlay();
          overlay = document.getElementById(LOADER_ID);
        }
        requestAnimationFrame(function() {
          overlay.classList.remove('fade-out');
          overlay.classList.add('active');
        });
      }, this._minDuration);

      return this;
    },

    /**
     * Hide loading overlay with smooth fade
     */
    hide: function() {
      var self = this;

      // Clear pending show timer
      if (this._showTimer) {
        clearTimeout(this._showTimer);
        this._showTimer = null;
      }

      var overlay = document.getElementById(LOADER_ID);
      if (!overlay) return this;

      overlay.classList.add('fade-out');
      overlay.classList.remove('active');

      // Clean up after transition
      setTimeout(function() {
        overlay.classList.remove('fade-out');
      }, 400);

      return this;
    },

    /**
     * Update the status text shown below the loader
     */
    setStatus: function(text) {
      var statusEl = document.getElementById('warungioLoaderStatus');
      if (!statusEl) return this;
      statusEl.textContent = text || '';
      return this;
    },

    /**
     * Show mini-inline loader inside a container (buttons, small areas)
     */
    showMini: function(container) {
      if (!container) return;
      var existing = container.querySelector('.warungio-loader-mini');
      if (existing) return;

      var mini = document.createElement('span');
      mini.className = 'warungio-loader-mini';
      mini.innerHTML = [
        '<svg viewBox="0 0 24 24" width="18" height="18">',
        '  <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2.5" opacity="0.2"/>',
        '  <path d="M12 3a9 9 0 0 1 9 9" fill="none" stroke="var(--color-brand,#16a34a)" stroke-width="2.5" stroke-linecap="round"/>',
        '</svg>'
      ].join('');

      container.style.position = 'relative';
      container.appendChild(mini);
    },

    /**
     * Hide mini-inline loader
     */
    hideMini: function(container) {
      if (!container) return;
      var mini = container.querySelector('.warungio-loader-mini');
      if (mini) mini.remove();
    },

    /**
     * Create the loader overlay DOM
     */
    _createOverlay: function() {
      var existing = document.getElementById(LOADER_ID);
      if (existing) return existing;

      var overlay = document.createElement('div');
      overlay.id = LOADER_ID;
      overlay.className = 'warungio-loader-overlay';
      overlay.setAttribute('role', 'status');
      overlay.setAttribute('aria-live', 'polite');

      // Use template HTML or fallback
      if (LOADER_HTML) {
        overlay.innerHTML = LOADER_HTML;
      } else {
        overlay.innerHTML = [
          '<div class="warungio-loader">',
          '  <svg class="warungio-loader-svg" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">',
          '    <circle class="loader-ring" cx="40" cy="40" r="28"/>',
          '    <path class="loader-arc" d="M40 12 A28 28 0 0 1 68 40" stroke-linecap="round"/>',
          '    <circle class="loader-dot" cx="40" cy="12" r="4"/>',
          '    <circle class="loader-dot" cx="68" cy="40" r="3.5"/>',
          '    <circle class="loader-dot" cx="40" cy="68" r="3"/>',
          '  </svg>',
          '  <div class="warungio-loader-text">',
          '    <span class="text-warung">Warung</span><span class="text-io">io</span>',
          '  </div>',
          '  <div class="warungio-loader-status" id="warungioLoaderStatus">Memuat...</div>',
          '</div>'
        ].join('\n');
      }

      document.body.appendChild(overlay);
      return overlay;
    },

    /**
     * Monkey-patch fetch() to auto-show/hide loader
     * Only intercepts POST/PUT/DELETE/PATCH (mutations), not GET reads
     */
    _patchFetch: function() {
      var self = this;
      var originalFetch = window.fetch;
      var reqId = 0;

      window.fetch = function() {
        var args = arguments;
        var url = typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url ? args[0].url : '');
        var method = typeof args[1] === 'object' && args[1].method ? args[1].method.toUpperCase() : 'GET';
        
        // Only intercept mutating requests (POST, PUT, DELETE, PATCH)
        if (!self._shouldIntercept(url, method)) {
          return originalFetch.apply(window, args);
        }

        var id = ++reqId;
        self._activeRequests.add(id);
        if (self._autoShow && self._activeRequests.size === 1) {
          self.show();
        }

        return originalFetch.apply(window, args)
          .then(function(response) {
            self._activeRequests.delete(id);
            if (self._activeRequests.size === 0) {
              self.hide();
            }
            return response;
          })
          .catch(function(error) {
            self._activeRequests.delete(id);
            if (self._activeRequests.size === 0) {
              self.hide();
            }
            throw error;
          });
      };
    },

    /**
     * Monkey-patch XMLHttpRequest for AJAX intercept
     * Only intercepts mutating methods (POST, PUT, DELETE, PATCH)
     */
    _patchXHR: function() {
      var self = this;
      var reqId = 0;
      var originalOpen = XMLHttpRequest.prototype.open;

      XMLHttpRequest.prototype.open = function(method, url) {
        this._warungioUrl = typeof url === 'string' ? url : '';
        this._warungioMethod = typeof method === 'string' ? method.toUpperCase() : 'GET';
        return originalOpen.apply(this, arguments);
      };

      var originalSend = XMLHttpRequest.prototype.send;
      XMLHttpRequest.prototype.send = function() {
        if (self._shouldIntercept(this._warungioUrl || '', this._warungioMethod || 'GET')) {
          var id = ++reqId;
          self._activeRequests.add(id);
          if (self._autoShow && self._activeRequests.size === 1) {
            self.show();
          }

          this.addEventListener('loadend', function() {
            self._activeRequests.delete(id);
            if (self._activeRequests.size === 0) {
              self.hide();
            }
          });
        }
        return originalSend.apply(this, arguments);
      };
    },

    /**
     * Integrate with HTMX via custom events
     * Only intercepts mutating verbs (post, put, delete, patch), not GET
     */
    _patchHTMX: function() {
      var self = this;
      var reqId = 0;

      document.addEventListener('htmx:beforeRequest', function(e) {
        var el = e.target;
        var detail = e.detail || {};
        var requestConfig = detail.requestConfig || {};
        var verb = (requestConfig.verb || 'get').toLowerCase();

        // Only intercept mutating HTMX requests, not GET partial loads
        if (verb === 'get' || verb === 'head') return;

        // Skip if element has hx-indicator=none or no-loader class
        if (el && (el.getAttribute('hx-indicator') === 'none' || el.classList.contains('no-loader'))) return;

        var id = ++reqId;
        el._warungioLoaderId = id;
        self._activeRequests.add(id);
        if (self._autoShow && self._activeRequests.size === 1) {
          self.show();
        }
      });

      document.addEventListener('htmx:afterRequest', function(e) {
        var el = e.target;
        if (el && el._warungioLoaderId) {
          self._activeRequests.delete(el._warungioLoaderId);
          delete el._warungioLoaderId;
          if (self._activeRequests.size === 0) {
            self.hide();
          }
        }
      });
    },

    /**
     * Show loading indicator on WebSocket reconnect/disconnect
     */
    _patchWebSocket: function() {
      var self = this;
      var wsTimer = null;

      document.addEventListener('warungio:ws-connecting', function() {
        self.show('Menghubungkan kembali...');
      });

      document.addEventListener('warungio:ws-connected', function() {
        self.hide();
        if (window.WarungioToast) WarungioToast.success('Koneksi tersambung');
      });

      document.addEventListener('warungio:ws-disconnected', function() {
        wsTimer = setTimeout(function() {
          self.show('Koneksi terputus. Menghubungkan kembali...');
        }, 3000);
      });

      document.addEventListener('warungio:ws-reconnected', function() {
        if (wsTimer) { clearTimeout(wsTimer); wsTimer = null; }
        self.hide();
        if (window.WarungioToast) WarungioToast.success('Koneksi tersambung kembali');
      });
    },

    /**
     * Determine if a URL should trigger the loader
     * @param {string} url - The request URL
     * @param {string} method - HTTP method (GET, POST, PUT, DELETE, PATCH)
     */
    _shouldIntercept: function(url, method) {
      if (!url || typeof url !== 'string') return false;
      
      // Only intercept mutating requests (not GET reads)
      if (method === 'GET' || method === 'HEAD' || method === 'OPTIONS') return false;

      // Skip static assets
      if (url.includes('/static/') || url.includes('/media/') || url.includes('/favicon')) return false;
      
      // Skip analytics/telemetry
      if (url.includes('google-analytics') || url.includes('facebook') || url.includes('analytics')) return false;
      
      // Intercept same-origin requests
      try {
        var parsed = new URL(url, window.location.origin);
        if (parsed.origin === window.location.origin) {
          if (parsed.pathname.startsWith('/static/') || parsed.pathname.startsWith('/media/')) return false;
          return true;
        }
      } catch(e) {
        // Relative URL - treat as same-origin
        if (!url.startsWith('http://') && !url.startsWith('https://') && !url.startsWith('//')) {
          if (url.startsWith('/static/') || url.startsWith('/media/')) return false;
          return true;
        }
      }
      
      return false;
    }
  };

  // Auto-init on DOMContentLoaded
  // autoShow: true enables automatic interception of fetch(), XHR, HTMX, WebSocket
  // For pages that want manual control, call WarungioLoader.init({ autoShow: false }) before DOMContentLoaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      WarungioLoader.init({ autoShow: true });
    });
  } else {
    WarungioLoader.init({ autoShow: true });
  }

  // Expose globally
  window.WarungioLoader = WarungioLoader;

  // Helper: show loader during form submissions
  document.addEventListener('submit', function(e) {
    var form = e.target;
    if (form && form.classList.contains('warungio-loading')) {
      WarungioLoader.show('Memproses...');
    }
  });

})();
