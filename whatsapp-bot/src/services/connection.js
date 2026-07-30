'use strict';

/**
 * ─────────────────────────────────────────────────────────────
 * ConnectionManager — WhatsApp Socket Lifecycle (Baileys v6.7.x)
 * ─────────────────────────────────────────────────────────────
 *
 * PRODUCTION-READY DESIGN PRINCIPLES:
 *
 * 1. MultiFileAuthState FIRST — Baileys manages ALL session files
 *    internally (creds.json, pre-key.json, sender-key.json, etc.).
 *    We do NOT validate, rename, or delete individual files.
 *    We let Baileys handle them atomically via useMultiFileAuthState.
 *
 * 2. Session VALID by default — If creds.json can be loaded by
 *    useMultiFileAuthState, the session is considered valid.
 *    The WhatsApp server decides true validity when we connect.
 *
 * 3. DELETE session ONLY on loggedOut — DisconnectReason.loggedOut
 *    is the ONLY reason to delete the session folder. All other
 *    disconnect reasons (restartRequired, connectionClosed,
 *    connectionLost, timedOut, badSession, streamErrored, etc.)
 *    are transient — just create a new socket with the SAME auth.
 *
 * 4. No recursive start() — start() is guarded by a mutex. Only
 *    one instance runs at a time. _scheduleReconnect() uses
 *    setTimeout → start() as a clean chain, not recursion.
 *
 * 5. QR only when NEEDED — QR is displayed only when:
 *    - No session folder exists, OR
 *    - Session files exist but creds.registered is false
 *    Once QR is scanned and CONNECTED, QR never shows again
 *    even across restarts, VPS reboots, or Docker rebuilds.
 *
 * 6. State Machine:
 *    INITIALIZING → CONNECTING → WAITING_FOR_QR → CONNECTED
 *                                 → AUTHENTICATING → CONNECTED
 *                    ↓ (close)
 *                    RECONNECTING → CONNECTING (same auth)
 *                    LOGGED_OUT → (delete session → INITIALIZING → QR)
 *                    SHUTDOWN (terminal)
 * ───────────────────────────────────────────────────────────── */

const {
  DisconnectReason,
  makeWASocket,
  useMultiFileAuthState,
  fetchLatestBaileysVersion,
} = require('@whiskeysockets/baileys');
const qrcode = require('qrcode-terminal');
const fs = require('fs');
const path = require('path');
const pino = require('pino');
const config = require('../config');
const appLogger = require('../utils/logger');
const { handleMessage } = require('../handler');
const { extractMessageContent } = require('./whatsapp');

/* ════════════════════════════════════════════════════════════
   STATE MACHINE
   ════════════════════════════════════════════════════════════ */

const State = Object.freeze({
  INITIALIZING:   'INITIALIZING',
  CONNECTING:     'CONNECTING',
  WAITING_FOR_QR: 'WAITING_FOR_QR',
  AUTHENTICATING: 'AUTHENTICATING',
  CONNECTED:      'CONNECTED',
  RECONNECTING:   'RECONNECTING',
  DISCONNECTED:   'DISCONNECTED',
  LOGGED_OUT:     'LOGGED_OUT',
  SHUTDOWN:       'SHUTDOWN',
});

/* ════════════════════════════════════════════════════════════
   CONNECTION MANAGER
   ════════════════════════════════════════════════════════════ */

class ConnectionManager {
  constructor() {
    /* ── Singleton socket ── */
    this.sock = null;
    this.authState = null;    // used to check creds.registered status
    this.saveCreds = null;    // bound creds.update handler

    /* ── State machine ── */
    this.state = State.INITIALIZING;
    this.reconnectAttempts = 0;
    this.reconnectTimer = null;

    /* ── Heartbeat (backup health check) ── */
    this.heartbeatTimer = null;
    this._heartbeatIntervalMs = config.heartbeatIntervalMs || 30000;
    this._maxReconnectAttempts = config.maxReconnectAttempts || 50;

    /* ── Baileys logger: raw pino instance with child() ── */
    this._baileysLogger = pino({ level: 'silent' });

    /* ── Mutex: prevents concurrent start() calls ── */
    this._locked = false;
    this._queue = [];


  }

  /* ════════════════════════════════════════════════════════════
     MUTEX
     ════════════════════════════════════════════════════════════ */

  _acquire() {
    return new Promise((resolve) => {
      if (!this._locked) {
        this._locked = true;
        resolve();
      } else {
        this._queue.push(resolve);
      }
    });
  }

  _release() {
    if (this._queue.length > 0) {
      const next = this._queue.shift();
      next();
    } else {
      this._locked = false;
    }
  }

  /* ════════════════════════════════════════════════════════════
     SESSION — MINIMAL. Baileys manages files via MultiFileAuthState.
     We ONLY delete the session folder on LOGGED_OUT.
     ════════════════════════════════════════════════════════════ */

  _getSessionDir() {
    return path.resolve(config.sessionDir);
  }

  /**
   * Quick check: does the session folder + creds.json exist?
   * Baileys' useMultiFileAuthState will load everything from here.
   */
  _sessionExists() {
    const dir = this._getSessionDir();
    if (!fs.existsSync(dir)) return false;
    return fs.existsSync(path.join(dir, 'creds.json'));
  }

  /**
   * DELETE session folder — ONLY called on DisconnectReason.loggedOut.
   * After deletion, the next start() will create fresh auth → new QR.
   */
  _deleteSession() {
    const dir = this._getSessionDir();
    if (!fs.existsSync(dir)) return;
    try {
      const files = fs.readdirSync(dir);
      for (const f of files) {
        try { fs.unlinkSync(path.join(dir, f)); } catch (_) { /* best effort */ }
      }
      appLogger.info('Session deleted — fresh QR will be generated');
    } catch (err) {
      appLogger.warn('Could not fully clear session: ' + err.message);
    }
  }

  /* ════════════════════════════════════════════════════════════
     SOCKET LIFECYCLE
     ════════════════════════════════════════════════════════════ */

  _countListeners() {
    if (!this.sock || !this.sock.ev) return 0;
    try {
      const events = ['connection.update', 'messages.upsert', 'creds.update', 'messages.error'];
      let total = 0;
      for (const ev of events) {
        if (typeof this.sock.ev.listenerCount === 'function') {
          total += this.sock.ev.listenerCount(ev);
        }
      }
      return total;
    } catch (_) {
      return -1;
    }
  }

  /**
   * COMPLETE socket destruction — guarantees no memory leak or
   * duplicate event listeners on the new socket.
   *
   * Order:
   *   1. Remove ALL event listeners
   *   2. Close WebSocket connection
   *   3. Call end() on the socket
   *   4. Null the reference
   */
  _cleanupSocket() {
    if (!this.sock) return;
    try {
      const prevCount = this._countListeners();
      if (prevCount > 0) {
        appLogger.info('Cleanup socket (' + prevCount + ' listeners)');
      }

      this.sock.ev.removeAllListeners('connection.update');
      this.sock.ev.removeAllListeners('messages.upsert');
      this.sock.ev.removeAllListeners('creds.update');
      this.sock.ev.removeAllListeners('messages.error');

      try { if (this.sock.ws && typeof this.sock.ws.close === 'function') this.sock.ws.close(); } catch (_) {}
      try { this.sock.end(); } catch (_) {}
      this.sock = null;
    } catch (err) {
      appLogger.warn('Socket cleanup (non-critical): ' + err.message);
      this.sock = null;
    }
  }

  /* ════════════════════════════════════════════════════════════
     BACKOFF & DISCONNECT HANDLING
     ════════════════════════════════════════════════════════════ */

  _getBackoffDelay() {
    // Exponential backoff: 1s, 2s, 4s, 8s... capped at 60s
    const base = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 60000);
    // Add ±250ms jitter to prevent thundering herd
    return base + Math.floor(Math.random() * 500);
  }

  _getReasonName(code) {
    const map = {};
    map[DisconnectReason.loggedOut]               = '401 LOGGED_OUT';
    map[DisconnectReason.connectionLost]          = 'CONNECTION_LOST';
    map[DisconnectReason.connectionClosed]        = 'CONNECTION_CLOSED';
    map[DisconnectReason.restartRequired]         = '428 RESTART_REQUIRED (conflict/515)';
    map[DisconnectReason.timedOut]                = 'TIMED_OUT (408)';
    map[DisconnectReason.badSession]              = 'BAD_SESSION';
    map[DisconnectReason.connectionReplaced]      = '440 CONNECTION_REPLACED';
    map[DisconnectReason.multideviceNotSupported] = '403 MULTIDEVICE_NOT_SUPPORTED';
    return map[code] || ('UNKNOWN (' + (code ?? 'null') + ')');
  }

  /**
   * DECISION: Should we reconnect?
   *
   * CRITICAL RULE (Baileys v6.7.x best practice):
   * - loggedOut (401) = session is DEAD. Server rejected it.
   *   We MUST NOT reconnect. Delete session → fresh QR.
   * - EVERYTHING ELSE = transient. Keep auth files, create new socket.
   */
  _shouldReconnect(statusCode) {
    return statusCode !== DisconnectReason.loggedOut;
  }

  _setState(newState) {
    const prev = this.state;
    if (prev !== newState) {
      this.state = newState;
      appLogger.info('State: ' + prev + ' → ' + newState);
    }
  }

  _logDisconnect(update) {
    const { lastDisconnect } = update;
    const err = lastDisconnect?.error;
    const statusCode = err?.output?.statusCode;
    const reasonName = this._getReasonName(statusCode);
    appLogger.info('=== DISCONNECT ===');
    appLogger.info('  Reason: ' + reasonName);
    appLogger.info('  State:  ' + this.state);
    appLogger.info('  Attempt: ' + this.reconnectAttempts + '/' + this._maxReconnectAttempts);
    if (err?.message) appLogger.info('  Error:  ' + err.message);
  }

  /* ════════════════════════════════════════════════════════════
     HEARTBEAT (backup health monitor)
     ════════════════════════════════════════════════════════════ */

  _startHeartbeat() {
    this._stopHeartbeat();
    this.heartbeatTimer = setInterval(() => this._performHealthCheck(), this._heartbeatIntervalMs);
    if (this.heartbeatTimer && this.heartbeatTimer.unref) {
      this.heartbeatTimer.unref();
    }
  }

  _stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  _performHealthCheck() {
    if (this.state === State.SHUTDOWN || this.state === State.LOGGED_OUT) return;

    // Socket null but state says connected → anomaly
    if (!this.sock && this.state === State.CONNECTED) {
      appLogger.warn('Heartbeat: socket=null but state=CONNECTED — reconnecting');
      this._setState(State.DISCONNECTED);
      this._scheduleReconnect();
      return;
    }

    // WebSocket in closing/closed state → anomaly
    if (this.sock && this.sock.ws && this.state === State.CONNECTED) {
      try {
        const wsState = this.sock.ws.readyState;
        if (wsState === 2 || wsState === 3) { // CLOSING or CLOSED
          appLogger.warn('Heartbeat: WS readyState=' + wsState + ' but state=CONNECTED — reconnecting');
          this._setState(State.DISCONNECTED);
          this._scheduleReconnect();
        }
      } catch (_) {}
    }
  }

  /* ════════════════════════════════════════════════════════════
     RECONNECT SCHEDULER (centralized)
     ════════════════════════════════════════════════════════════

     This is the ONLY place reconnectTimer is set. Prevents
     multiple overlapping reconnect timers.
     ════════════════════════════════════════════════════════════ */

  _scheduleReconnect() {
    // Cancel existing timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.state === State.SHUTDOWN || this.state === State.LOGGED_OUT) return;

    if (this.reconnectAttempts >= this._maxReconnectAttempts) {
      this._setState(State.DISCONNECTED);
      appLogger.error('Max reconnect attempts (' + this._maxReconnectAttempts + ') — giving up');
      return;
    }

    this._setState(State.RECONNECTING);
    this.reconnectAttempts++;
    const delayMs = this._getBackoffDelay();
    const sec = Math.round(delayMs / 1000);

    appLogger.info('Reconnect in ' + sec + 's (attempt ' + this.reconnectAttempts + ')');

    this.reconnectTimer = setTimeout(async () => {
      this.reconnectTimer = null;
      if (this.state === State.SHUTDOWN || this.state === State.LOGGED_OUT) return;
      await this.start();
    }, delayMs);
  }

  /* ════════════════════════════════════════════════════════════
     MAIN START (mutex-guarded, non-recursive)
     ════════════════════════════════════════════════════════════ */

  async start() {
    if (this.state === State.SHUTDOWN) return;

    await this._acquire();
    try {
      // Re-check state after acquiring mutex
      if (this.state === State.SHUTDOWN) return;
      if (this.state === State.CONNECTED) {
        appLogger.info('Already connected — skipping start()');
        return;
      }
      if (this.state === State.LOGGED_OUT) {
        appLogger.info('Logged out — waiting for fresh start after QR');
        return;
      }

      // Cancel any pending reconnect
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }

      // Stop heartbeat (restarted after connection)
      this._stopHeartbeat();

      // Destroy old socket before creating new one
      if (this.sock) this._cleanupSocket();

      this._setState(State.CONNECTING);

      appLogger.info('=== Warungio WhatsApp Bot v' + config.botVersion + ' ===');
      appLogger.info('  AI:      ' + (config.aiEnabled ? 'ON' : 'OFF'));
      appLogger.info('  Session: ' + this._getSessionDir());

      // Quick check for logging purposes only — Baileys manages all auth files
      const hadSession = this._sessionExists();

      // ── Fetch latest WA version ──
      let waVersion;
      try {
        const { version } = await fetchLatestBaileysVersion();
        waVersion = version;
        appLogger.info('  WA:      v' + waVersion.join('.'));
      } catch (_) {
        appLogger.warn('  WA:      failed to fetch version — using default');
      }

      // ── Load MultiFileAuthState (Baileys manages all files) ──
      // useMultiFileAuthState atomically reads/writes all auth files.
      // If creds.json exists and is valid, it loads the registered session.
      // If not, it creates fresh empty auth state (which will need QR).
      const { state: authState, saveCreds } = await useMultiFileAuthState(config.sessionDir);
      this.authState = authState;
      this.saveCreds = saveCreds;

      // ── Is the user already registered? ──
      // creds.registered is set to true by Baileys after successful QR scan.
      // If false, the session is NEW and needs QR authentication.
      const isRegistered = authState.creds && authState.creds.registered === true;

      if (hadSession && isRegistered) {
        appLogger.info('  Auth:    valid session loaded — will resume without QR');
      } else if (hadSession && !isRegistered) {
        appLogger.info('  Auth:    session exists but NOT registered — QR needed');
      } else {
        appLogger.info('  Auth:    new session — QR needed');
      }

      // ── Wrap saveCreds with error handling ──
      const safeSaveCreds = async () => {
        try {
          await saveCreds();
        } catch (err) {
          appLogger.error('Failed to save credentials: ' + err.message);
        }
      };

      // ── Create socket ──
      this.sock = makeWASocket({
        version: waVersion,
        auth: authState,
        printQRInTerminal: false,
        defaultQueryTimeoutMs: 30000,
        keepAliveIntervalMs: 25000,
        logger: this._baileysLogger,
        markOnlineOnConnect: false,
        syncFullHistory: false,
        emitOwnEvents: false,
        browser: ['Warungio Bot', 'Chrome', config.botVersion],
      });

      /* ── Event: creds.update — save credentials on every change ── */
      this.sock.ev.on('creds.update', safeSaveCreds);

      /* ── Event: connection.update — core lifecycle handler ── */
      this.sock.ev.on('connection.update', async (update) => {
        try {
          await this._onConnectionUpdate(update);
        } catch (err) {
          appLogger.error('connection.update error: ' + err.message);
        }
      });

      /* ── Event: messages.upsert — incoming messages ── */
      this.sock.ev.on('messages.upsert', async (msgEvent) => {
        try {
          if (this.state === State.SHUTDOWN) return;
          for (const msg of msgEvent.messages) {
            await this._processMessage(this.sock, msg);
          }
        } catch (err) {
          appLogger.error('messages.upsert error: ' + err.message);
        }
      });

      /* ── Event: messages.error — stream error (just log) ── */
      this.sock.ev.on('messages.error', (error) => {
        appLogger.error('Stream error: ' + (error?.message || 'unknown'));
        // DO NOT call start() from here. Let connection.update 'close'
        // or heartbeat handle the recovery.
      });

    } catch (err) {
      appLogger.error('start() failed: ' + err.message);
      if (this.state !== State.SHUTDOWN && this.state !== State.LOGGED_OUT) {
        this._scheduleReconnect();
      }
    } finally {
      this._release();
    }
  }

  /* ════════════════════════════════════════════════════════════
     CONNECTION UPDATE HANDLER
     ════════════════════════════════════════════════════════════

     Decision matrix:
     ┌──────────────────────┬────────────────────────────────────┐
     │ Event               │ Action                             │
     ├──────────────────────┼────────────────────────────────────┤
     │ qr received         │ Show QR (unless already registered)│
     │ connection='open'   │ Set CONNECTED, reset attempts      │
     │ connection='close'  │ Check DisconnectReason:            │
     │  + 401 (loggedOut)  │ Delete session → INITIALIZING → QR │
     │  + restartRequired  │ Reconnect immediately (0 delay)    │
     │  + other            │ Reconnect with exponential backoff │
     └──────────────────────┴────────────────────────────────────┘
     ════════════════════════════════════════════════════════════ */

  async _onConnectionUpdate(update) {
    const { connection, lastDisconnect, qr } = update;

    /* ── QR Code ──────────────────────────────────────────── */
    if (qr) {
      // CRITICAL: Only show QR when NOT already registered.
      // Baileys may emit qr events even during reconnect — we
      // must NOT show QR if the user is already authenticated.
      if (this.authState && this.authState.creds && this.authState.creds.registered === true) {
        // User is already authenticated — ignore QR
        if (this.state !== State.CONNECTED) {
          this._setState(State.AUTHENTICATING);
        }
        return;
      }

      // No valid registration — show QR
      this._setState(State.WAITING_FOR_QR);
      this.reconnectAttempts = 0;
      appLogger.info('=== QR CODE ===');
      qrcode.generate(qr, { small: true });
      appLogger.info('Scan QR with WhatsApp > Linked Devices > Link a Device');
      return;
    }

    /* ── Connected ────────────────────────────────────────── */
    if (connection === 'open') {
      this._setState(State.CONNECTED);
      this.reconnectAttempts = 0;
      this._startHeartbeat();

      const userJid = this.sock?.user?.id || 'unknown';
      const mem = (process.memoryUsage().heapUsed / 1024 / 1024).toFixed(1);
      appLogger.success('Connected as ' + userJid.split(':')[0]);
      appLogger.info('  Memory: ' + mem + 'MB | Listeners: ' + this._countListeners());
      return;
    }

    /* ── Connection closed ────────────────────────────────── */
    if (connection === 'close') {
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      this._logDisconnect(update);
      this._stopHeartbeat();

      /* ── LOGGED OUT (401) — session permanently invalid ── */
      if (!this._shouldReconnect(statusCode)) {
        this._setState(State.LOGGED_OUT);
        appLogger.error('Session rejected by WhatsApp — LOGGED_OUT');

        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer);
          this.reconnectTimer = null;
        }
        this.reconnectAttempts = 0;

        // Clean up socket
        this._cleanupSocket();

        // Delete entire session folder — forces fresh QR
        this._deleteSession();

        // Reset to INITIALIZING so next start() proceeds past LOGGED_OUT check
        this._setState(State.INITIALIZING);
        appLogger.info('Session cleaned — starting fresh in 1s');
        setTimeout(() => this.start(), 1000);
        return;
      }

      /* ── RESTART REQUIRED (515/conflict) — reconnect immediately ── */
      if (statusCode === DisconnectReason.restartRequired) {
        appLogger.info('Restart required — reconnecting immediately');
        // Clean socket but KEEP auth files (session is still valid)
        this._cleanupSocket();
        this.reconnectAttempts = 0; // don't count restartRequired as failure
        this._setState(State.RECONNECTING);
        setTimeout(() => this.start(), 100);
        return;
      }

      /* ── TRANSIENT ERROR — reconnect with backoff ────────── */
      // Keep session files intact — only the socket needs recreating.
      // This handles: connectionClosed, connectionLost, timedOut,
      // connectionReplaced, badSession, streamErrored, etc.
      this._scheduleReconnect();
      return;
    }
  }

  /* ════════════════════════════════════════════════════════════
     MESSAGE PROCESSING
     ════════════════════════════════════════════════════════════ */

  async _processMessage(socket, msg) {
    try {
      if (!msg.key) return;
      const { remoteJid, fromMe, id } = msg.key;
      if (fromMe) return;
      if (remoteJid === 'status@broadcast') return;
      if (remoteJid.endsWith('@g.us')) return;
      if (id && id.includes('broadcast')) return;

      const content = extractMessageContent(msg);
      if (!content || !content.text) return;

      appLogger.info('Message [' + content.type + '] from ' + remoteJid.split('@')[0] + ': ' + content.text.substring(0, 80));
      await handleMessage(socket, remoteJid, content.text, content);
    } catch (err) {
      appLogger.error('Process message error: ' + err.message);
    }
  }

  /* ════════════════════════════════════════════════════════════
     GRACEFUL SHUTDOWN
     ════════════════════════════════════════════════════════════

     Clean shutdown WITHOUT deleting session files — the session
     survives restarts, VPS reboots, and Docker container restarts.
     ════════════════════════════════════════════════════════════ */

  shutdown() {
    if (this.state === State.SHUTDOWN) return;
    this._setState(State.SHUTDOWN);
    appLogger.info('Shutting down...');

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this._stopHeartbeat();
    this._cleanupSocket();

    appLogger.info('Session preserved — will resume on next start');
    process.exit(0);
  }

  /* ════════════════════════════════════════════════════════════
     STATUS
     ════════════════════════════════════════════════════════════ */

  getStatus() {
    return {
      state: this.state,
      connected: this.state === State.CONNECTED,
      reconnectAttempts: this.reconnectAttempts,
      socketExists: this.sock !== null,
      listenerCount: this._countListeners(),
      sessionExists: this._sessionExists(),
      sessionDir: this._getSessionDir(),
      isRegistered: this.authState?.creds?.registered === true,
      memoryMB: (process.memoryUsage().heapUsed / 1024 / 1024).toFixed(1),
      uptimeSec: process.uptime().toFixed(0),
    };
  }
}

module.exports = { ConnectionManager, State };
