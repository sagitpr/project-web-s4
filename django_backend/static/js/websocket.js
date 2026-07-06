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

  var API_BASE = window.API_BASE_URL || '/api';
  var WS_BASE = API_BASE.replace(/^http/, 'ws').replace(/\/api$/, '/ws');
  var RECONNECT_DELAY = 3000;
  var MAX_RECONNECT_ATTEMPTS = 10;
  var PING_INTERVAL = 30000;

  function WarungioWebSocket() {
    this.socket = null;
    this.listeners = {};
    this.reconnectAttempts = 0;
    this.reconnectTimer = null;
    this.pingTimer = null;
    this.connected = false;
    this._destroyed = false;
  }

  WarungioWebSocket.prototype.connect = function () {
    var self = this;
    if (!window.WarungioAuth || !window.WarungioAuth.isAuthenticated()) {
      return this;
    }
    var token = window.WarungioAuth.getAccessToken();
    if (!token) return this;

    self._destroyed = false;
    var url = WS_BASE + '/notifications/?token=' + encodeURIComponent(token);

    try {
      self.socket = new WebSocket(url);
    } catch (e) {
      self._scheduleReconnect();
      return this;
    }

    self.socket.onopen = function () {
      self.connected = true;
      self.reconnectAttempts = 0;
      self._emit('connected', {});
      self._startPing();
    };

    self.socket.onclose = function (event) {
      self.connected = false;
      self._stopPing();
      self._emit('disconnected', { code: event.code });
      if (!self._destroyed && event.code !== 1000) {
        self._scheduleReconnect();
      }
    };

    self.socket.onerror = function () {
      self._emit('error', {});
    };

    self.socket.onmessage = function (event) {
      try {
        var data = JSON.parse(event.data);
        var msgType = data.type || 'unknown';
        self._emit(msgType, data);
        self._emit('message', data);
      } catch (e) {}
    };

    return this;
  };

  WarungioWebSocket.prototype.disconnect = function () {
    this._destroyed = true;
    this._stopReconnect();
    this._stopPing();
    if (this.socket) {
      this.socket.close(1000, 'Client disconnect');
      this.socket = null;
    }
    this.connected = false;
  };

  WarungioWebSocket.prototype.on = function (event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
    var self = this;
    return function () { self.off(event, callback); };
  };

  WarungioWebSocket.prototype.off = function (event, callback) {
    if (!this.listeners[event]) return;
    this.listeners[event] = this.listeners[event].filter(function (cb) { return cb !== callback; });
  };

  WarungioWebSocket.prototype.send = function (data) {
    if (this.socket && this.connected) {
      this.socket.send(JSON.stringify(data));
    }
  };

  WarungioWebSocket.prototype.ping = function () {
    this.send({ type: 'ping' });
  };

  WarungioWebSocket.prototype._emit = function (event, data) {
    if (!this.listeners[event]) return;
    for (var i = 0; i < this.listeners[event].length; i++) {
      try { this.listeners[event][i](data); } catch (e) {}
    }
  };

  WarungioWebSocket.prototype._scheduleReconnect = function () {
    var self = this;
    if (self._destroyed) return;
    if (self.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      self._emit('max_reconnect', {});
      return;
    }
    self.reconnectAttempts++;
    var delay = RECONNECT_DELAY * Math.min(self.reconnectAttempts, 5);
    self.reconnectTimer = setTimeout(function () { self.connect(); }, delay);
  };

  WarungioWebSocket.prototype._stopReconnect = function () {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  };

  WarungioWebSocket.prototype._startPing = function () {
    var self = this;
    self._stopPing();
    self.pingTimer = setInterval(function () { self.ping(); }, PING_INTERVAL);
  };

  WarungioWebSocket.prototype._stopPing = function () {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  };

  var wsInstance = new WarungioWebSocket();
  window.WarungioWS = wsInstance;

  document.addEventListener('DOMContentLoaded', function () {
    if (window.WarungioAuth && window.WarungioAuth.isAuthenticated()) {
      wsInstance.connect();
    }
  });
})();
