'use strict';

const { DisconnectReason, makeWASocket, useMultiFileAuthState, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const qrcode = require('qrcode-terminal');
const fs = require('fs');
const path = require('path');
const config = require('./config');
const appLogger = require('./utils/logger');
const { sleep } = require('./utils/delay');
const { handleMessage } = require('./handler');
const { extractMessageContent } = require('./services/whatsapp');

/* ────────────────────────────────────────────────────────────
   SEPARATE BAILEYS LOGGER (raw pino) from APP LOGGER (pino-pretty)
   Baileys v6.7.24 internally calls logger.child() which is ONLY
   available on real pino instances.
   ──────────────────────────────────────────────────────────── */
const pino = require('pino');
const baileysLogger = pino({ level: 'silent' });

/* ── Connection State Machine ───────────────────────────────
   State transitions must be EXACTLY one path — no ambiguous states.

   States:
     INITIALIZING  → bot is starting up
     CONNECTING    → makeWASocket created, waiting for connection
     CONNECTED     → connection === 'open' (session valid)
     DISCONNECTED  → connection closed temporarily (will reconnect)
     LOGGED_OUT    → received 401 — session invalid, must re-auth
     RECONNECTING  → exponential backoff in progress
     WAITING_FOR_QR → awaiting user to scan QR code
     SHUTTING_DOWN → process exit requested
   ──────────────────────────────────────────────────────────── */
const State = Object.freeze({
  INITIALIZING:  'INITIALIZING',
  CONNECTING:    'CONNECTING',
  CONNECTED:     'CONNECTED',
  DISCONNECTED:  'DISCONNECTED',
  LOGGED_OUT:    'LOGGED_OUT',
  RECONNECTING:  'RECONNECTING',
  WAITING_FOR_QR: 'WAITING_FOR_QR',
  SHUTTING_DOWN: 'SHUTTING_DOWN',
});

/* ── Singleton state ──────────────────────────────────────── */
let sock = null;
let state = State.INITIALIZING;
let reconnectAttempts = 0;
let reconnectTimer = null;  // track setTimeout for cleanup on logout

const MAX_RECONNECT_ATTEMPTS = 50;

/* ── Mutex: only one socket creation at a time ────────────── */
const reconnectMutex = (() => {
  let locked = false;
  let queue = [];
  return {
    acquire() {
      return new Promise((resolve) => {
        if (!locked) { locked = true; resolve(); }
        else { queue.push(resolve); }
      });
    },
    release() {
      if (queue.length > 0) queue.shift()();
      else locked = false;
    },
  };
})();

/* ── Session helpers ──────────────────────────────────────── */

function getSessionDir() {
  return path.resolve(config.sessionDir);
}

/**
 * Check if session files exist (for QR vs reconnect decision).
 * NOTE: This only checks FILE EXISTENCE, NOT session validity.
 * The server decides if a session is valid when we connect.
 */
function sessionFilesExist() {
  const dir = getSessionDir();
  if (!fs.existsSync(dir)) return false;
  const credsPath = path.join(dir, 'creds.json');
  return fs.existsSync(credsPath);
}

/**
 * Delete entire session directory. Called on 401/loggedOut.
 * This forces a fresh QR scan on next startBot().
 */
function deleteSession() {
  const dir = getSessionDir();
  if (!fs.existsSync(dir)) return;
  try {
    const files = fs.readdirSync(dir);
    for (const f of files) {
      fs.unlinkSync(path.join(dir, f));
    }
    appLogger.info('Folder session berhasil dibersihkan');
  } catch (err) {
    appLogger.warn('Gagal membersihkan session: ' + err.message);
  }
}

/* ── Socket lifecycle ─────────────────────────────────────── */

function countListeners() {
  if (!sock || !sock.ev) return 0;
  try {
    const events = ['connection.update', 'messages.upsert', 'creds.update', 'messages.error'];
    let total = 0;
    for (const evName of events) {
      if (typeof sock.ev.listenerCount === 'function') {
        total += sock.ev.listenerCount(evName);
      }
    }
    return total;
  } catch (_) {
    return -1;
  }
}

function cleanupSocket() {
  if (!sock) return;
  try {
    const prevCount = countListeners();
    appLogger.info('Cleanup socket (listeners: ' + prevCount + ')...');

    sock.ev.removeAllListeners('connection.update');
    sock.ev.removeAllListeners('messages.upsert');
    sock.ev.removeAllListeners('creds.update');
    sock.ev.removeAllListeners('messages.error');

    try { if (sock.ws && typeof sock.ws.close === 'function') sock.ws.close(); } catch (_) {}
    sock.end();
    appLogger.info('Socket berhasil dibersihkan');
  } catch (err) {
    appLogger.warn('Cleanup non-critical: ' + err.message);
  } finally {
    sock = null;
  }
}

/* ── Backoff ──────────────────────────────────────────────── */
function getBackoffDelay() {
  const base = Math.min(1000 * Math.pow(2, reconnectAttempts), 60000);
  return base + Math.random() * 500;
}

/* ── Disconnect reason helpers ────────────────────────────── */

function getReasonName(code) {
  const map = {};
  map[DisconnectReason.loggedOut]                 = '401 LOGGED_OUT';
  map[DisconnectReason.connectionLost]            = '408 CONNECTION_LOST';
  map[DisconnectReason.connectionClosed]          = '200 CONNECTION_CLOSED';
  map[DisconnectReason.restartRequired]           = '428 RESTART_REQUIRED';
  map[DisconnectReason.timedOut]                  = '408 TIMED_OUT';
  map[DisconnectReason.badSession]                = '500 BAD_SESSION';
  map[DisconnectReason.connectionReplaced]        = '440 CONNECTION_REPLACED';
  map[DisconnectReason.multideviceNotSupported]   = '403 MULTIDEVICE_NOT_SUPPORTED';
  return map[code] || ('UNKNOWN (' + (code ?? 'null') + ')');
}

/**
 * Decides whether to RECONNECT or LOGOUT based on DisconnectReason.
 *
 * CRITICAL RULE:
 * - `loggedOut` (401) from WhatsApp server ALWAYS means the session is
 *   permanently invalid on the server side. We MUST NOT reconnect.
 *   creds.json on disk is irrelevant — the server has rejected it.
 * - Other status codes are transient errors → safe to reconnect.
 */
function shouldReconnect(statusCode) {
  // 401 = server says this session is dead. Period. No reconnect.
  if (statusCode === DisconnectReason.loggedOut) return false;
  // All other codes: connectionClosed, restartRequired, timedOut,
  // connectionLost, badSession, connectionReplaced, etc. → reconnect
  return true;
}

function logDisconnect(update) {
  const { lastDisconnect } = update;
  const err = lastDisconnect?.error;
  const statusCode = err?.output?.statusCode;
  appLogger.info('=== DISCONNECT ===');
  appLogger.info('  State before: ' + state);
  appLogger.info('  Status code: ' + (statusCode ?? 'unknown'));
  appLogger.info('  Reason:      ' + getReasonName(statusCode));
  appLogger.info('  Attempt:     ' + reconnectAttempts + '/' + MAX_RECONNECT_ATTEMPTS);
}

/* ── Main bot starter ────────────────────────────────────── */

async function startBot() {
  if (state === State.SHUTTING_DOWN) return;

  await reconnectMutex.acquire();
  try {
    if (state === State.SHUTTING_DOWN) return;
    if (state === State.LOGGED_OUT) {
      appLogger.info('State=LOGGED_OUT — melewatkan reconnect hingga user scan QR ulang');
      return;
    }

    // Cancel any pending reconnect timer
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }

    // Clean up old socket (if any)
    if (sock) cleanupSocket();

    state = State.CONNECTING;
    appLogger.info('=== Warungio WhatsApp Bot v' + config.botVersion + ' ===');
    appLogger.info('State: ' + state + ' | AI: ' + (config.aiEnabled ? 'ON' : 'OFF'));
    appLogger.info('Session: ' + getSessionDir());

    const hasSessionFiles = sessionFilesExist();

    // ── Fetch WA version ──
    let waVersion;
    try {
      const versionInfo = await fetchLatestBaileysVersion();
      waVersion = versionInfo.version;
      appLogger.info('WA version: ' + waVersion.join('.'));
    } catch (_) {
      appLogger.warn('Gagal fetch WA version — pakai default');
    }

    const { state: authState, saveCreds } = await useMultiFileAuthState(config.sessionDir);

    sock = makeWASocket({
      version: waVersion,
      auth: authState,
      printQRInTerminal: false,
      defaultQueryTimeoutMs: 30000,
      keepAliveIntervalMs: 25000,
      logger: baileysLogger,
      markOnlineOnConnect: false,
      syncFullHistory: false,
      emitOwnEvents: false,
      browser: ['Warungio Bot', 'Chrome', config.botVersion],
    });

    /* ── Event: creds.update → persist credentials ──────── */
    sock.ev.on('creds.update', saveCreds);

    /* ── Event: connection.update ───────────────────────── */
    sock.ev.on('connection.update', async (update) => {
      const { connection, lastDisconnect, qr } = update;

      // ── QR Code (only when NOT yet connected) ──
      if (qr && state !== State.CONNECTED) {
        state = State.WAITING_FOR_QR;
        reconnectAttempts = 0;
        appLogger.info('=== QR CODE — Scan dengan WhatsApp Anda ===');
        qrcode.generate(qr, { small: true });
        appLogger.info('Menu > Perangkat Tertaut > Tautkan Perangkat');
      }

      // ── Connected successfully ──
      if (connection === 'open') {
        state = State.CONNECTED;
        reconnectAttempts = 0;
        const userJid = sock?.user?.id || 'unknown';
        const mem = (process.memoryUsage().heapUsed / 1024 / 1024).toFixed(1);
        appLogger.success('✓ Bot terhubung! (' + userJid.split(':')[0] + ')');
        appLogger.info('  Memory: ' + mem + 'MB | Listeners: ' + countListeners());
        return;
      }

      // ── Connection closed ──
      if (connection === 'close') {
        const statusCode = lastDisconnect?.error?.output?.statusCode;
        logDisconnect(update);

        /* ── DECISION: LOGOUT or RECONNECT? ────────────── */
        if (!shouldReconnect(statusCode)) {
          // ── LOGGED OUT (401) — permanent server rejection ──
          state = State.LOGGED_OUT;
          appLogger.error('✗ LOGGED OUT (401) — Session ditolak server WhatsApp.');
          appLogger.info('  Menghapus session lama dan siapkan QR baru...');

          // Cancel any pending reconnect
          if (reconnectTimer) {
            clearTimeout(reconnectTimer);
            reconnectTimer = null;
          }
          reconnectAttempts = 0;

          // Clean socket
          cleanupSocket();

          // Delete entire session directory (forces fresh login)
          deleteSession();

          // Reset state so the deferred startBot() proceeds past the LOGGED_OUT check
          state = State.INITIALIZING;

          appLogger.info('  Session dibersihkan. Memulai sesi baru dengan QR...');
          // Auto-start new session — no session files means QR will generate
          setTimeout(() => startBot(), 500);
          return;
        }

        // ── TRANSIENT ERROR → reconnect with backoff ──
        state = State.RECONNECTING;
        if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
          state = State.DISCONNECTED;
          appLogger.error('✗ Gagal reconnect setelah ' + MAX_RECONNECT_ATTEMPTS + ' percobaan.');
          return;
        }

        // Clear bad session files before reconnect (500)
        if (statusCode === DisconnectReason.badSession) {
          appLogger.warn('  BAD_SESSION — membersihkan session...');
          deleteSession();
        }

        reconnectAttempts++;
        const delayMs = getBackoffDelay();
        const sec = Math.round(delayMs / 1000);
        appLogger.info('  Reconnect in ' + sec + 's (attempt ' + reconnectAttempts + '/' + MAX_RECONNECT_ATTEMPTS + ')');

        reconnectTimer = setTimeout(async () => {
          reconnectTimer = null;
          if (state === State.SHUTTING_DOWN || state === State.LOGGED_OUT) return;
          // Only reconnect if not logged out
          await startBot();
        }, delayMs);
        return;
      }
    });

    /* ── Event: messages.upsert ─────────────────────────── */
    sock.ev.on('messages.upsert', async (msgEvent) => {
      if (state === State.SHUTTING_DOWN) return;
      for (const msg of msgEvent.messages) {
        await processIncomingMessage(sock, msg);
      }
    });

    /* ── Event: messages.error (stream errored / 515) ──── */
    sock.ev.on('messages.error', (error) => {
      appLogger.error('Stream error: ' + (error?.message || 'unknown'));
      if (state === State.CONNECTED && !reconnectTimer && state !== State.SHUTTING_DOWN && state !== State.LOGGED_OUT) {
        appLogger.info('  Stream error — reconnect...');
        // startBot() handles cleanupSocket() internally — no need to call it here
        setTimeout(() => startBot(), 0);
      }
    });

  } catch (err) {
    appLogger.error('Fatal error: ' + err.message);
    appLogger.error(err.stack);

    if (state === State.LOGGED_OUT || state === State.SHUTTING_DOWN) return;

    if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
      reconnectAttempts++;
      const delayMs = getBackoffDelay();
      appLogger.info('  Retry in ' + Math.round(delayMs / 1000) + 's (attempt ' + reconnectAttempts + ')');
      reconnectTimer = setTimeout(() => startBot(), delayMs);
    } else {
      state = State.DISCONNECTED;
      appLogger.error('✗ Gagal setelah ' + MAX_RECONNECT_ATTEMPTS + ' percobaan.');
    }
  } finally {
    reconnectMutex.release();
  }
}

/* ── Message processing ──────────────────────────────────── */

async function processIncomingMessage(socket, msg) {
  try {
    if (!msg.key) return;
    const { remoteJid, fromMe, id } = msg.key;
    if (fromMe) return;
    if (remoteJid === 'status@broadcast') return;
    if (remoteJid.endsWith('@g.us')) return;
    if (id && id.includes('broadcast')) return;

    const content = extractMessageContent(msg);
    if (!content || !content.text) return;

    const preview = content.text.substring(0, 100);
    appLogger.info('Pesan [' + content.type + '] dari ' + remoteJid.split('@')[0] + ': ' + preview);
    await handleMessage(socket, remoteJid, content.text, content);
  } catch (err) {
    appLogger.error('Error processing message: ' + err.message);
  }
}

/* ── Global error handlers ── */

process.on('uncaughtException', (err) => {
  appLogger.error('Uncaught: ' + err.message);
  appLogger.error(err.stack);
});

process.on('unhandledRejection', (reason) => {
  appLogger.error('Unhandled rejection: ' + reason);
});

/* ── Graceful shutdown ── */
function shutdown() {
  if (state === State.SHUTTING_DOWN) return;
  state = State.SHUTTING_DOWN;
  appLogger.info('Shutdown...');

  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  cleanupSocket();
  process.exit(0);
}

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

/* ── Start ── */
startBot().catch((err) => {
  appLogger.error('Start fatal: ' + err.message);
  process.exit(1);
});
