/**
 * Warungio WebSocket Client — WarungioWS
 * Real-time notification and event system for authenticated users.
 *
 * Auto-connects to the WebSocket NotificationConsumer when
 * WarungioAuth has a valid JWT token.
 *
 * Usage:
 *   // Subscribe to events
 *   var unsub = WarungioWS.on('notification', function(data) { ... });
 *   // Later: unsub();  // to remove listener
 *
 *   // Manually connect/disconnect
 *   WarungioWS.connect();
 *   WarungioWS.disconnect();
 *
 * Events emitted:
 *   'notification'    — new notification from server
 *   'order_update'    — order status changed
 *   'payment_update'  — payment status changed
 *   'delivery_update' — delivery tracking updated
 *   'unread_count'    — unread notification count
 *   'connected'       — WebSocket connected
 *   'disconnected'    — WebSocket disconnected
 *   'error'           — WebSocket error
 */
(function () {
  'use strict';

  var WS = {};
  var ws = null;
  var listeners = {};
  var reconnectTimer = null;
  var pingInterval = null;
  var isConnecting = false;

  var RECONNECT_DELAY = 3000;   // Initial reconnect delay (ms)
  var MAX_RECONNECT_DELAY = 30000; // Max reconnect delay cap
  var PING_INTERVAL = 25000;    // Send ping every 25s

  var currentReconnectDelay = RECONNECT_DELAY;

  // ── Determine WebSocket URL ──

  function getWebSocketUrl() {
    var token = null;
    if (window.WarungioAuth && typeof window.WarungioAuth.getAccessToken === 'function') {
      token = window.WarungioAuth.getAccessToken();
    } else if (window.WarungioAuth && window.WarungioAuth.token) {
      token = window.WarungioAuth.token;
    }

    if (!token) return null;

    var protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    var host = window.location.host;
    return protocol + '//' + host + '/ws/notifications/?token=' + encodeURIComponent(token);
  }

  // ── Event System ──

  /**
   * Subscribe to a WebSocket event.
   * @param {string} event - Event name (notification, order_update, etc.)
   * @param {function} callback - Function to call when event fires
   * @returns {function} Unsubscribe function
   */
  WS.on = function (event, callback) {
    if (!listeners[event]) listeners[event] = [];
    listeners[event].push(callback);

    var called = false;
    return function () {
      if (called) return;
      called = true;
      if (listeners[event]) {
        listeners[event] = listeners[event].filter(function (cb) { return cb !== callback; });
      }
    };
  };

  /**
   * Remove all listeners for an event.
   */
  WS.off = function (event) {
    delete listeners[event];
  };

  function emit(event, data) {
    var evtListeners = listeners[event];
    if (evtListeners) {
      evtListeners.forEach(function (cb) {
        try { cb(data); } catch (e) { console.warn('WarungioWS listener error:', e); }
      });
    }
  }

  // ── Connection Management ──

  /**
   * Connect to the WebSocket server.
   * Uses JWT token from WarungioAuth for authentication.
   */
  WS.connect = function () {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
    if (isConnecting) return;

    var url = getWebSocketUrl();
    if (!url) {
      // // console.debug (production-safe) (production-safe)('WarungioWS: No auth token available, skipping WebSocket connection');
      return;
    }

    isConnecting = true;

    try {
      ws = new WebSocket(url);
    } catch (e) {
      console.warn('WarungioWS: Failed to create WebSocket:', e);
      isConnecting = false;
      scheduleReconnect();
      return;
    }

    ws.onopen = function () {
      isConnecting = false;
      currentReconnectDelay = RECONNECT_DELAY; // Reset reconnect delay on success
      console.info('WarungioWS: Connected');
      emit('connected', {});

      // Start periodic ping
      if (pingInterval) clearInterval(pingInterval);
      pingInterval = setInterval(function () {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, PING_INTERVAL);
    };

    ws.onmessage = function (event) {
      try {
        var data = JSON.parse(event.data);
        var msgType = data.type;

        if (msgType === 'pong') return; // Ignore pong responses

        // Emit specific event
        if (msgType) {
          emit(msgType, data);
        }

        // Also emit generic 'message' event
        emit('message', data);
      } catch (e) {
        console.warn('WarungioWS: Failed to parse message:', e);
      }
    };

    ws.onclose = function (event) {
      isConnecting = false;
      console.info('WarungioWS: Disconnected (code: ' + event.code + ')');
      emit('disconnected', { code: event.code });
      if (pingInterval) { clearInterval(pingInterval); pingInterval = null; }
      scheduleReconnect();
    };

    ws.onerror = function (error) {
      isConnecting = false;
      console.warn('WarungioWS: Error:', error);
      emit('error', { error: error });
    };
  };

  /**
   * Disconnect from the WebSocket server.
   */
  WS.disconnect = function () {
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null; }
    if (pingInterval) { clearInterval(pingInterval); pingInterval = null; }
    currentReconnectDelay = RECONNECT_DELAY;

    if (ws) {
      ws.onclose = null; // Prevent reconnect
      ws.close(1000, 'Client disconnect');
      ws = null;
    }
    isConnecting = false;
    emit('disconnected', { code: 1000 });
  };

  /**
   * Send data through the WebSocket.
   * @param {object} data - Data to send (will be JSON.stringify'd)
   */
  WS.send = function (data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
      return true;
    }
    console.warn('WarungioWS: Cannot send — WebSocket not connected');
    return false;
  };

  /**
   * Check if WebSocket is currently connected.
   * @returns {boolean}
   */
  WS.isConnected = function () {
    return ws && ws.readyState === WebSocket.OPEN;
  };

  // ── Reconnect Logic ──

  function scheduleReconnect() {
    if (reconnectTimer) return; // Already scheduled

    reconnectTimer = setTimeout(function () {
      reconnectTimer = null;
      console.info('WarungioWS: Reconnecting in ' + currentReconnectDelay + 'ms...');
      WS.connect();
      // Exponential backoff with cap
      currentReconnectDelay = Math.min(currentReconnectDelay * 1.5, MAX_RECONNECT_DELAY);
    }, currentReconnectDelay);
  }

  // ── Auto-connect on page load if authenticated ──

  function tryAutoConnect() {
    var isAuth = window.WarungioAuth && (
      (typeof window.WarungioAuth.isAuthenticated === 'function' && window.WarungioAuth.isAuthenticated()) ||
      window.WarungioAuth.token
    );
    if (isAuth) {
      // Small delay to ensure auth is fully initialized
      setTimeout(function () { WS.connect(); }, 500);
    }
  }

  // Auto-connect when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', tryAutoConnect);
  } else {
    tryAutoConnect();
  }

  // Also try after a short delay in case auth loads later
  setTimeout(tryAutoConnect, 1500);

  // ── Expose globally ──

  window.WarungioWS = WS;
  console.info('WarungioWS: Client initialized');

  // Set Snap JS URL from backend payment config (NOT hardcoded)
  // Loads dynamically based on MIDTRANS_IS_PRODUCTION env var from backend.
  // Falls back to protocol-based detection if backend is unreachable.
  if (window.WarungioAPI && typeof window.WarungioAPI.getPaymentConfig === 'function') {
    window.WarungioAPI.getPaymentConfig().then(function(config) {
      if (config && config.snap_js_url) {
        window.WARUNGIO_SNAP_JS_URL = config.snap_js_url;
        window.WARUNGIO_SNAP_BASE_URL = config.snap_url;
      }
    }).catch(function() {
      // Fallback: default to production (safe default for production deployments)
      window.WARUNGIO_SNAP_BASE_URL = 'https://app.midtrans.com';
    });
  } else {
    window.WARUNGIO_SNAP_BASE_URL = 'https://app.midtrans.com';
  }
})();
