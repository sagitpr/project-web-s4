/**
 * Warungio WebSocket Client
 * Real-time notifications via Django Channels.
 * Handles auto-reconnect, JWT auth, and event callbacks.
 *
 * Usage:
 *   const ws = WarungioWS.connect();
 *   ws.on('order_update', (data) => { ... });
 *   ws.on('notification', (data) => { ... });
 *   ws.on('unread_count', (data) => { ... });
 */
(function () {
  'use strict';

  // Derive WebSocket URL from API_BASE used by WarungioAuth
  const API_BASE = window.API_BASE_URL || '/api';
  const WS_BASE = API_BASE.replace(/^http/, 'ws').replace(/\/api$/, '/ws');
  const RECONNECT_DELAY = 3000;
  const MAX_RECONNECT_ATTEMPTS = 10;
  const PING_INTERVAL = 30000;

  class WarungioWebSocket {
    constructor() {
      this.socket = null;
      this.listeners = {};
      this.reconnectAttempts = 0;
      this.reconnectTimer = null;
      this.pingTimer = null;
      this.connected = false;
      this._destroyed = false;
    }

    /**
     * Connect to the notification WebSocket.
     * @returns {WarungioWebSocket} this instance for chaining
     */
    connect() {
      if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
        console.warn('WarungioWS: User not authenticated, skipping WebSocket connection.');
        return this;
      }

      const token = window.WarungioAuth.getAccessToken();
      if (!token) return this;

      this._destroyed = false;
      const url = `${WS_BASE}/notifications/?token=${encodeURIComponent(token)}`;

      try {
        this.socket = new WebSocket(url);
      } catch (e) {
        console.error('WarungioWS: Failed to create WebSocket:', e);
        this._scheduleReconnect();
        return this;
      }

      this.socket.onopen = () => {
        console.info('WarungioWS: Connected');
        this.connected = true;
        this.reconnectAttempts = 0;
        this._emit('connected', {});
        this._startPing();
      };

      this.socket.onclose = (event) => {
        console.info('WarungioWS: Disconnected (code:', event.code, ')');
        this.connected = false;
        this._stopPing();
        this._emit('disconnected', { code: event.code });

        if (!this._destroyed && event.code !== 1000) {
          this._scheduleReconnect();
        }
      };

      this.socket.onerror = (error) => {
        console.error('WarungioWS: Error:', error);
        this._emit('error', { error });
      };

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const msgType = data.type || 'unknown';

          // Emit specific type AND generic catch-all
          this._emit(msgType, data);
          this._emit('message', data);
        } catch (e) {
          console.warn('WarungioWS: Failed to parse message:', e);
        }
      };

      return this;
    }

    /**
     * Disconnect and clean up.
     */
    disconnect() {
      this._destroyed = true;
      this._stopReconnect();
      this._stopPing();
      if (this.socket) {
        this.socket.close(1000, 'Client disconnect');
        this.socket = null;
      }
      this.connected = false;
    }

    /**
     * Register an event listener.
     * @param {string} event - Event type (order_update, notification, unread_count, etc.)
     * @param {Function} callback - Handler function
     * @returns {Function} unsubscribe function
     */
    on(event, callback) {
      if (!this.listeners[event]) {
        this.listeners[event] = [];
      }
      this.listeners[event].push(callback);
      return () => this.off(event, callback);
    }

    /**
     * Remove an event listener.
     */
    off(event, callback) {
      if (!this.listeners[event]) return;
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }

    /**
     * Send a message to the server.
     */
    send(data) {
      if (this.socket && this.connected) {
        this.socket.send(JSON.stringify(data));
      }
    }

    /**
     * Send a ping to keep connection alive.
     */
    ping() {
      this.send({ type: 'ping' });
    }

    // ── Private ──

    _emit(event, data) {
      if (!this.listeners[event]) return;
      this.listeners[event].forEach(cb => {
        try { cb(data); } catch (e) { console.warn('WarungioWS: Listener error:', e); }
      });
    }

    _scheduleReconnect() {
      if (this._destroyed) return;
      if (this.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        console.warn('WarungioWS: Max reconnect attempts reached.');
        this._emit('max_reconnect', {});
        return;
      }
      this.reconnectAttempts++;
      const delay = RECONNECT_DELAY * Math.min(this.reconnectAttempts, 5);
      console.info(`WarungioWS: Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
      this.reconnectTimer = setTimeout(() => this.connect(), delay);
    }

    _stopReconnect() {
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
    }

    _startPing() {
      this._stopPing();
      this.pingTimer = setInterval(() => this.ping(), PING_INTERVAL);
    }

    _stopPing() {
      if (this.pingTimer) {
        clearInterval(this.pingTimer);
        this.pingTimer = null;
      }
    }
  }

  // Singleton instance
  const instance = new WarungioWebSocket();

  // Expose globally
  window.WarungioWS = instance;

  // Auto-connect on page load if user is logged in
  document.addEventListener('DOMContentLoaded', () => {
    if (window.WarungioAuth && window.WarungioAuth.isAuthenticated()) {
      instance.connect();
    }
  });
})();
