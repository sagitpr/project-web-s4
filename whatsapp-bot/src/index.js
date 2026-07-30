'use strict';

/**
 * ────────────────────────────────────────────────────────────
 * Warungio WhatsApp Bot — Entry Point
 * ────────────────────────────────────────────────────────────
 *
 * This file is intentionally THIN. All socket lifecycle logic
 * has been extracted into ConnectionManager (services/connection.js).
 *
 * Responsibilities of THIS file:
 *   1. Import ConnectionManager singleton
 *   2. Register global error handlers (uncaughtException, unhandledRejection)
 *   3. Register process signal handlers (SIGINT, SIGTERM)
 *   4. Start the bot
 * ──────────────────────────────────────────────────────────── */

const { ConnectionManager } = require('./services/connection');
const appLogger = require('./utils/logger');

/* ── Singleton connection manager ─────────────────────────── */
const manager = new ConnectionManager();

/* ── Global error handlers ────────────────────────────────── */

process.on('uncaughtException', (err) => {
  appLogger.error('UNCAUGHT EXCEPTION: ' + err.message);
  appLogger.error(err.stack);
});

process.on('unhandledRejection', (reason) => {
  appLogger.error('UNHANDLED REJECTION: ' + reason);
});

/* ── Graceful shutdown ───────────────────────────────────── */

process.on('SIGINT', manager.shutdown.bind(manager));
process.on('SIGTERM', manager.shutdown.bind(manager));

/* ── Start ────────────────────────────────────────────────── */

manager.start().catch((err) => {
  appLogger.error('FATAL: Bot failed to start: ' + err.message);
  appLogger.error(err.stack);
  process.exit(1);
});
